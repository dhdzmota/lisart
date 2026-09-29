"""Respaldos de las tablas.

Regla de la casa: **nada se sobrescribe sin dejar copia**. Editar a mano es la
forma mas facil de perder informacion, y un CSV no tiene "deshacer".

Los respaldos viven en `data/backups/<tabla>/<tabla>_<fecha>.csv`, fuera de las
cuatro capas. No son parte del flujo de datos: son una red de seguridad.

Un respaldo no sirve si nadie lo puede encontrar, asi que el nombre lleva la
fecha y la hora, y restaurar es copiar un archivo encima del original (o usar
`restaurar()`).
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from lisart.config import data_dir
from lisart.schema import Table
from lisart.tables import REGISTRY

# Cuantas copias se conservan por tabla. Suficientes para deshacer una tarde de
# ediciones, y acotadas para no ir acumulando copias de datos personales para
# siempre.
COPIAS_A_CONSERVAR = 50

SELLO = "%Y%m%dT%H%M%S"


def backups_dir() -> Path:
    return data_dir() / "backups"


def _resolver(tabla: str | Table) -> Table:
    return tabla if isinstance(tabla, Table) else REGISTRY.get(tabla)


def respaldar(tabla: str | Table, *, motivo: str = "") -> Path | None:
    """Guarda una copia del CSV actual. Devuelve la ruta, o None si no existia.

    Se llama ANTES de escribir, no despues: lo que se quiere conservar es el
    estado previo, que es el que se puede perder.
    """
    tbl = _resolver(tabla)
    if not tbl.path.exists():
        return None

    destino = backups_dir() / tbl.name
    destino.mkdir(parents=True, exist_ok=True)

    sufijo = f"_{motivo}" if motivo else ""
    copia = destino / f"{tbl.name}_{datetime.now().strftime(SELLO)}{sufijo}.csv"
    shutil.copy2(tbl.path, copia)

    _podar(tbl)
    return copia


def _podar(tabla: Table) -> None:
    copias = sorted((backups_dir() / tabla.name).glob(f"{tabla.name}_*.csv"))
    for vieja in copias[:-COPIAS_A_CONSERVAR]:
        vieja.unlink()


def guardar_con_respaldo(
    tabla: str | Table, df: pd.DataFrame, *, motivo: str = ""
) -> tuple[Path, Path | None]:
    """Valida, respalda y guarda. Devuelve (archivo escrito, respaldo).

    El orden importa: primero se valida, y solo si el dato nuevo es bueno se
    hace el respaldo y se escribe. Asi un intento fallido no llena la carpeta
    de copias identicas.
    """
    from lisart import io
    from lisart.validate import validate_table

    tbl = _resolver(tabla)
    completo = df.loc[:, tbl.column_names]

    errores = [i for i in validate_table(tbl, completo) if i.severity == "error"]
    if errores:
        detalle = "\n  ".join(str(i) for i in errores[:10])
        raise io.DataError(f"No se guardo {tbl.name}:\n  {detalle}")

    copia = respaldar(tbl, motivo=motivo)
    ruta = io.write_table(tbl, completo)
    return ruta, copia


def listar(tabla: str | Table) -> list[Path]:
    """Respaldos de una tabla, del mas nuevo al mas viejo."""
    tbl = _resolver(tabla)
    carpeta = backups_dir() / tbl.name
    if not carpeta.exists():
        return []
    return sorted(carpeta.glob(f"{tbl.name}_*.csv"), reverse=True)


def restaurar(tabla: str | Table, copia: Path) -> Path:
    """Regresa una tabla a un respaldo anterior.

    Antes de pisar el archivo actual le hace su propio respaldo: deshacer una
    restauracion tiene que ser posible tambien.
    """
    from lisart import io

    tbl = _resolver(tabla)
    if not copia.exists():
        raise FileNotFoundError(f"No existe el respaldo {copia}")

    respaldar(tbl, motivo="antes-de-restaurar")
    shutil.copy2(copia, tbl.path)
    # Se relee para confirmar que lo restaurado se puede interpretar.
    io.read_table(tbl, strict=False)
    return tbl.path


def respaldar_todo(capa: str = "master") -> list[Path]:
    """Copia de golpe todas las tablas de una capa. Para antes de algo grande."""
    copias = []
    for tbl in REGISTRY:
        if tbl.layer != capa:
            continue
        copia = respaldar(tbl, motivo="snapshot")
        if copia:
            copias.append(copia)
    return copias
