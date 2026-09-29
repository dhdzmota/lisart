"""Verifica que los datos cumplan lo que promete el esquema.

Un CSV no sabe defenderse: acepta cualquier cosa que le escribas. Este modulo
es lo que compensa eso. La regla de trabajo es correr `lisart validate` antes
de confiar en cualquier reporte, y siempre despues de que alguien edito a mano
un catalogo.

Lo que se revisa:

  columnas ....... que esten todas y no sobre ninguna
  tipos .......... que cada valor se pueda interpretar (fechas, numeros, si/no)
  obligatorias ... que no haya vacios donde no se permite
  llave primaria . que no se repita ni venga vacia
  catalogo ....... que los valores esten dentro de la lista permitida
  referencias .... que lo que apunta a otra tabla exista de verdad
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from lisart import io
from lisart.schema import Registry, Table
from lisart.tables import REGISTRY

Severity = Literal["error", "warning"]

# Cuantas filas se listan por problema antes de resumir. Un catalogo mal
# guardado puede tener 400 filas malas y no sirve de nada imprimirlas todas.
MAX_FILAS_REPORTADAS = 10


@dataclass
class Issue:
    table: str
    rule: str
    message: str
    severity: Severity = "error"
    column: str | None = None
    rows: list[int] = field(default_factory=list)

    def __str__(self) -> str:
        donde = f"{self.table}.{self.column}" if self.column else self.table
        detalle = ""
        if self.rows:
            muestra = ", ".join(str(r) for r in self.rows[:MAX_FILAS_REPORTADAS])
            ocultas = len(self.rows) - MAX_FILAS_REPORTADAS
            resto = f" (+{ocultas})" if ocultas > 0 else ""
            detalle = f" [filas: {muestra}{resto}]"
        return f"{self.severity.upper()} {donde}: {self.message}{detalle}"


def _filas(index) -> list[int]:
    return [io._fila_csv(i) for i in index]


def validate_table(table: str | Table, df: pd.DataFrame | None = None) -> list[Issue]:
    """Revisa una tabla por si sola (todo menos las referencias a otras tablas).

    Si no se pasa `df`, se lee del disco.
    """
    tbl = table if isinstance(table, Table) else REGISTRY.get(table)
    issues: list[Issue] = []

    if df is None:
        raw = io.read_raw(tbl)
        if not tbl.path.exists():
            return [
                Issue(
                    tbl.name,
                    "archivo_faltante",
                    f"No existe {tbl.path}. Correr `lisart init` para crearlo vacio.",
                    severity="warning",
                )
            ]
        df, coercion_errors = io.coerce(tbl, raw)
        for col_name in {e.column for e in coercion_errors}:
            malos = [e for e in coercion_errors if e.column == col_name]
            issues.append(
                Issue(
                    tbl.name,
                    "tipo_invalido",
                    f"{len(malos)} valor(es) no son de tipo '{tbl.column(col_name).dtype}'. "
                    f"Ejemplo: {malos[0].value!r}",
                    column=col_name,
                    rows=[m.row for m in malos],
                )
            )
        sobrantes = [c for c in raw.columns if c not in tbl.column_names]
        if sobrantes:
            issues.append(
                Issue(
                    tbl.name,
                    "columna_desconocida",
                    "El archivo tiene columnas que no estan en el esquema: "
                    f"{', '.join(sobrantes)}. "
                    "O se agregan a tables.py o se quitan del archivo.",
                    severity="warning",
                )
            )

    faltantes = [c for c in tbl.column_names if c not in df.columns]
    if faltantes:
        issues.append(
            Issue(tbl.name, "columna_faltante", f"Faltan columnas: {', '.join(faltantes)}")
        )
        return issues

    for col in tbl.columns:
        serie = df[col.name]

        if col.required:
            vacios = serie[serie.isna()]
            if len(vacios):
                issues.append(
                    Issue(
                        tbl.name,
                        "requerido",
                        f"{len(vacios)} fila(s) sin valor en una columna obligatoria.",
                        column=col.name,
                        rows=_filas(vacios.index),
                    )
                )

        if col.unique:
            lleno = serie.dropna()
            repetidos = lleno[lleno.duplicated(keep=False)]
            if len(repetidos):
                ejemplo = repetidos.iloc[0]
                issues.append(
                    Issue(
                        tbl.name,
                        "unico",
                        f"{repetidos.nunique()} valor(es) repetidos, ej. {ejemplo!r}.",
                        column=col.name,
                        rows=_filas(repetidos.index),
                    )
                )

        if col.choices:
            lleno = serie.dropna().astype("string")
            fuera = lleno[~lleno.isin(col.choices)]
            if len(fuera):
                issues.append(
                    Issue(
                        tbl.name,
                        "catalogo",
                        f"Valores fuera del catalogo: {sorted(set(fuera))[:5]}. "
                        f"Permitidos: {', '.join(col.choices)}.",
                        column=col.name,
                        rows=_filas(fuera.index),
                    )
                )

    pk = list(tbl.primary_key)
    if all(c in df.columns for c in pk) and len(df):
        clave = df[pk].astype("string")
        completos = clave.notna().all(axis=1)
        repetidos = df[completos][clave[completos].duplicated(keep=False)]
        if len(repetidos):
            issues.append(
                Issue(
                    tbl.name,
                    "llave_primaria",
                    f"{len(repetidos)} fila(s) comparten llave primaria ({', '.join(pk)}). "
                    "Cada fila tiene que ser identificable de forma unica.",
                    rows=_filas(repetidos.index),
                )
            )

    return issues


def validate_foreign_keys(
    table: str | Table, frames: dict[str, pd.DataFrame]
) -> list[Issue]:
    """Revisa que las referencias a otras tablas apunten a algo que existe."""
    tbl = table if isinstance(table, Table) else REGISTRY.get(table)
    df = frames.get(tbl.name)
    issues: list[Issue] = []
    if df is None or not len(df):
        return issues

    for fk in tbl.foreign_keys:
        ref = frames.get(fk.ref_table)
        if ref is None:
            issues.append(
                Issue(
                    tbl.name,
                    "referencia",
                    f"No se pudo revisar: falta la tabla {fk.ref_table}.",
                    severity="warning",
                    column=fk.column,
                )
            )
            continue
        if fk.column not in df.columns or fk.ref_column not in ref.columns:
            continue

        valores = df[fk.column].astype("string")
        validos = set(ref[fk.ref_column].astype("string").dropna())
        rotos = valores[valores.notna() & ~valores.isin(validos)]
        if len(rotos):
            issues.append(
                Issue(
                    tbl.name,
                    "referencia",
                    f"{len(rotos)} valor(es) apuntan a {fk.ref_table}.{fk.ref_column} "
                    f"pero no existen alla, ej. {rotos.iloc[0]!r}.",
                    column=fk.column,
                    rows=_filas(rotos.index),
                )
            )
        if fk.required:
            vacios = valores[valores.isna()]
            if len(vacios):
                issues.append(
                    Issue(
                        tbl.name,
                        "referencia",
                        f"{len(vacios)} fila(s) sin referencia a {fk.ref_table}, y es obligatoria.",
                        column=fk.column,
                        rows=_filas(vacios.index),
                    )
                )
    return issues


def validate_all(registry: Registry | None = None) -> list[Issue]:
    """Valida todas las tablas y las relaciones entre ellas."""
    reg = registry or REGISTRY
    issues: list[Issue] = []
    frames: dict[str, pd.DataFrame] = {}

    for tbl in reg.in_dependency_order():
        raw = io.read_raw(tbl)
        df, _ = io.coerce(tbl, raw)
        frames[tbl.name] = df
        issues.extend(validate_table(tbl))

    for tbl in reg.in_dependency_order():
        issues.extend(validate_foreign_keys(tbl, frames))

    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
