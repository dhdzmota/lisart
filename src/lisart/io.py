"""Leer y escribir las tablas.

Ninguna otra parte del proyecto debe hacer `pd.read_csv` o `df.to_csv` sobre
`data/`. Todo pasa por aqui, porque aqui viven las garantias:

* los tipos siempre se interpretan igual (un telefono no se vuelve numero,
  un ID no pierde el cero de adelante),
* el archivo se escribe de forma atomica: o queda completo o no se toca. Si
  se corta la luz a media escritura, el CSV anterior sigue intacto,
* las filas y columnas salen siempre en el mismo orden, para que los cambios
  se puedan leer en git,
* leer una tabla que todavia no existe devuelve una tabla vacia bien formada,
  no una explosion.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lisart.config import (
    CSV_LINE_TERMINATOR,
    CSV_SEP,
    DATE_FORMAT,
    DATETIME_FORMAT,
    TIME_FORMAT,
)
from lisart.schema import Table
from lisart.tables import REGISTRY

# Como se escribe en el CSV lo verdadero y lo falso.
BOOL_TRUE, BOOL_FALSE = "true", "false"

# Como se lee. Incluye lo que escupe Excel en español (VERDADERO/FALSO) y lo
# que escribe la gente a mano (si/no), porque hay tablas que se editan a mano.
_BOOL_LECTURA = {
    "true": True, "1": True, "si": True, "sí": True, "yes": True,
    "verdadero": True, "v": True, "x": True,
    "false": False, "0": False, "no": False, "falso": False, "f": False,
}


class DataError(Exception):
    """Un dato guardado no se puede interpretar segun el esquema."""


@dataclass(frozen=True)
class CoercionError:
    """Un valor concreto que no pudo convertirse al tipo que dice el esquema."""

    table: str
    column: str
    row: int
    value: str
    expected: str

    def __str__(self) -> str:
        return (
            f"{self.table}.{self.column} fila {self.row}: {self.value!r} "
            f"no es un valor valido de tipo '{self.expected}'"
        )


def _resolve(table: str | Table) -> Table:
    return table if isinstance(table, Table) else REGISTRY.get(table)


# --- Lectura -----------------------------------------------------------


def read_raw(table: str | Table) -> pd.DataFrame:
    """Lee el CSV sin convertir nada: todo queda como texto.

    Es el paso previo a `coerce`. Se separa para que el validador pueda
    distinguir 'la celda venia vacia' de 'la celda tenia basura'.
    """
    tbl = _resolve(table)
    if not tbl.path.exists():
        return pd.DataFrame({c: pd.Series(dtype="string") for c in tbl.column_names})

    df = pd.read_csv(
        tbl.path,
        sep=CSV_SEP,
        dtype="string",
        encoding=tbl.encoding,
        keep_default_na=False,
        # Solo la celda vacia cuenta como nulo. Sin esto pandas convierte en
        # nulo textos legitimos como "NA" (iniciales) o "None".
        na_values=[""],
    )
    # Espacios de sobra al inicio o final: casi siempre son un dedo de mas al
    # capturar, y hacen que "Juan " nunca cruce con "Juan".
    for col in df.columns:
        df[col] = df[col].str.strip().replace("", pd.NA)
    return df


def coerce(table: str | Table, raw: pd.DataFrame) -> tuple[pd.DataFrame, list[CoercionError]]:
    """Convierte el texto crudo a los tipos del esquema.

    Devuelve el DataFrame convertido y la lista de valores que no se pudieron
    convertir (que quedan como nulos en el resultado).
    """
    tbl = _resolve(table)
    out = pd.DataFrame(index=raw.index)
    errors: list[CoercionError] = []

    for col in tbl.columns:
        if col.name in raw.columns:
            serie = raw[col.name]
        else:
            serie = pd.Series(pd.NA, index=raw.index, dtype="string")
        valores, malos = _coerce_series(serie.astype("string"), col.dtype)
        out[col.name] = valores
        for idx in malos:
            errors.append(
                CoercionError(tbl.name, col.name, _fila_csv(idx), serie.loc[idx], col.dtype)
            )

    # Columnas que estan en el archivo pero no en el esquema: se conservan para
    # no perder informacion. El validador las reporta aparte.
    for extra in raw.columns:
        if extra not in out.columns:
            out[extra] = raw[extra]
    return out, errors


def _coerce_series(serie: pd.Series, dtype: str) -> tuple[pd.Series, list]:
    """Convierte una columna. Devuelve (columna convertida, indices invalidos)."""
    lleno = serie.notna()

    if dtype == "string":
        return serie, []

    if dtype == "bool":
        conv = serie.str.lower().map(_BOOL_LECTURA).astype("boolean")
    elif dtype in ("int", "float"):
        numerico = pd.to_numeric(serie, errors="coerce")
        if dtype == "int":
            # Un decimal donde se espera un entero es un error, no un redondeo.
            entero = numerico.where(numerico.isna() | (numerico % 1 == 0))
            conv = entero.astype("Int64")
        else:
            conv = numerico.astype("Float64")
    elif dtype == "time":
        conv = pd.to_datetime(serie, format=TIME_FORMAT, errors="coerce")
        # Se guarda como datetime.time: una hora de clase no tiene fecha, y
        # arrastrar el 1900-01-01 que inventa pandas solo estorba al comparar.
        horas = conv.dt.time.astype("object").where(conv.notna(), None)
        invalidos = serie.index[lleno & pd.Series([v is None for v in horas], index=serie.index)]
        return horas, list(invalidos)
    elif dtype in ("date", "datetime"):
        fmt = DATE_FORMAT if dtype == "date" else DATETIME_FORMAT
        conv = pd.to_datetime(serie, format=fmt, errors="coerce")
        if dtype == "date":
            # Se guarda como datetime.date: una fecha de nacimiento no tiene
            # hora, y arrastrar 00:00:00 solo confunde al compararla.
            conv = conv.dt.date.astype("object").where(conv.notna(), None)
            invalidos = serie.index[lleno & pd.Series([v is None for v in conv], index=serie.index)]
            return conv, list(invalidos)
    else:
        raise ValueError(f"Tipo no soportado: {dtype}")

    invalidos = serie.index[lleno & conv.isna()]
    return conv, list(invalidos)


def _fila_csv(idx: int) -> int:
    """Indice de pandas -> numero de linea en el archivo (con encabezado)."""
    return int(idx) + 2


def read_table(table: str | Table, *, strict: bool = True) -> pd.DataFrame:
    """Lee una tabla ya convertida a sus tipos.

    Con strict=True (lo normal) truena si algun valor guardado no cuadra con el
    esquema, porque seguir trabajando con datos que ya sabemos que estan mal
    solo mueve el error mas adelante, donde cuesta mas encontrarlo.
    """
    tbl = _resolve(table)
    df, errors = coerce(tbl, read_raw(tbl))
    if errors and strict:
        detalle = "\n  ".join(str(e) for e in errors[:20])
        extra = f"\n  ... y {len(errors) - 20} mas" if len(errors) > 20 else ""
        raise DataError(f"{tbl.name}: {len(errors)} valor(es) invalido(s):\n  {detalle}{extra}")
    return df


# --- Escritura ---------------------------------------------------------


def format_for_csv(table: str | Table, df: pd.DataFrame) -> pd.DataFrame:
    """Convierte los tipos de vuelta a texto, como se veran en el archivo."""
    tbl = _resolve(table)
    out = pd.DataFrame(index=df.index)
    for col in tbl.columns:
        serie = df[col.name]
        if col.dtype == "bool":
            texto = serie.map({True: BOOL_TRUE, False: BOOL_FALSE}).astype("string")
        elif col.dtype == "date":
            texto = pd.Series(
                [
                    v.strftime(DATE_FORMAT) if v is not None and pd.notna(v) else pd.NA
                    for v in serie
                ],
                index=serie.index,
                dtype="string",
            )
        elif col.dtype == "time":
            texto = pd.Series(
                [
                    v.strftime(TIME_FORMAT) if v is not None and pd.notna(v) else pd.NA
                    for v in serie
                ],
                index=serie.index,
                dtype="string",
            )
        elif col.dtype == "datetime":
            texto = pd.to_datetime(serie).dt.strftime(DATETIME_FORMAT).astype("string")
        elif col.dtype == "int":
            texto = serie.astype("Int64").astype("string")
        elif col.dtype == "float":
            texto = serie.astype("Float64").astype("string")
        else:
            texto = serie.astype("string")
        out[col.name] = texto
    return out


def write_table(table: str | Table, df: pd.DataFrame, *, validate: bool = True) -> Path:
    """Guarda una tabla completa (reemplaza el archivo).

    Valida antes de escribir: es mucho mas barato rechazar un dato malo aqui
    que descubrirlo un mes despues en un reporte.
    """
    tbl = _resolve(table)

    faltantes = [c for c in tbl.column_names if c not in df.columns]
    if faltantes:
        raise DataError(f"{tbl.name}: faltan columnas al escribir: {', '.join(faltantes)}")

    df = df.loc[:, tbl.column_names].copy()

    if validate:
        from lisart.validate import validate_table

        issues = [i for i in validate_table(tbl, df) if i.severity == "error"]
        if issues:
            detalle = "\n  ".join(str(i) for i in issues[:20])
            raise DataError(f"No se escribio {tbl.name}, tiene errores:\n  {detalle}")

    orden = [c for c in tbl.order_by if c in df.columns]
    if orden:
        df = df.sort_values(orden, kind="stable", na_position="last").reset_index(drop=True)

    tbl.path.parent.mkdir(parents=True, exist_ok=True)
    texto = format_for_csv(tbl, df)
    _atomic_write_csv(texto, tbl.path, tbl.encoding)
    return tbl.path


def _atomic_write_csv(df: pd.DataFrame, path: Path, encoding: str) -> None:
    """Escribe a un temporal en la misma carpeta y luego lo mueve encima.

    Mover un archivo dentro del mismo disco es una operacion atomica del
    sistema: el archivo destino nunca queda a medias.
    """
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        df.to_csv(
            tmp,
            index=False,
            sep=CSV_SEP,
            encoding=encoding,
            lineterminator=CSV_LINE_TERMINATOR,
            na_rep="",
        )
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def upsert(table: str | Table, nuevas: pd.DataFrame, *, validate: bool = True) -> pd.DataFrame:
    """Inserta filas nuevas y actualiza las que ya existen, segun la llave primaria.

    Devuelve la tabla completa resultante, ya guardada.
    """
    tbl = _resolve(table)
    actuales = read_table(tbl, strict=False)
    pk = list(tbl.primary_key)

    faltantes = [c for c in pk if c not in nuevas.columns]
    if faltantes:
        raise DataError(f"{tbl.name}: upsert necesita la llave primaria ({', '.join(faltantes)})")

    for col in tbl.column_names:
        if col not in nuevas.columns:
            nuevas[col] = pd.NA
    nuevas = nuevas.loc[:, tbl.column_names]

    combinado = pd.concat([actuales, nuevas], ignore_index=True)
    combinado = combinado.drop_duplicates(subset=pk, keep="last").reset_index(drop=True)
    write_table(tbl, combinado, validate=validate)
    return combinado


def empty_frame(table: str | Table) -> pd.DataFrame:
    """Tabla vacia con las columnas y tipos correctos. Util para empezar."""
    tbl = _resolve(table)
    return coerce(tbl, pd.DataFrame({c: pd.Series(dtype="string") for c in tbl.column_names}))[0]
