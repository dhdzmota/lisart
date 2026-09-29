"""Rutas y constantes del proyecto.

Todo el codigo pide las rutas aqui en vez de escribirlas a mano. Asi el dia que
los datos se muevan (a un disco compartido, a Drive, a una base de datos real)
se cambia un solo lugar.
"""

from __future__ import annotations

import os
from pathlib import Path

# Raiz del repo: .../lisart2.0/src/lisart/config.py -> .../lisart2.0
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_PATH = PROJECT_ROOT / ".env"


def cargar_env(path: Path | None = None) -> dict[str, str]:
    """Lee `.env` y mete lo que falte en las variables de entorno.

    Son doce lineas en vez de una dependencia mas (python-dotenv). Lo que ya
    este definido en el entorno real **gana**: asi se puede sobreescribir una
    llave sin editar el archivo.
    """
    archivo = path or ENV_PATH
    leidas: dict[str, str] = {}
    if not archivo.exists():
        return leidas
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave, valor = clave.strip(), valor.strip().strip("\"'")
        leidas[clave] = valor
        os.environ.setdefault(clave, valor)
    return leidas


def secreto(nombre: str, *, requerido: bool = True) -> str | None:
    """Devuelve una llave del entorno (o de `.env`), con un error que explica."""
    cargar_env()
    valor = os.environ.get(nombre)
    if not valor and requerido:
        raise RuntimeError(
            f"Falta {nombre}. Ponlo en el archivo .env de la raiz del proyecto "
            f"(hay una plantilla en .env.example). Nunca lo escribas en el codigo."
        )
    return valor or None


def data_dir() -> Path:
    """Carpeta raiz de datos. Se puede mover con la variable LISART_DATA_DIR."""
    override = os.environ.get("LISART_DATA_DIR")
    return Path(override).expanduser().resolve() if override else PROJECT_ROOT / "data"


def ruta_corta(ruta: Path) -> str:
    """La ruta relativa al repo si esta adentro, y completa si no.

    Existe porque `data/` puede vivir fuera del repo (`LISART_DATA_DIR`), que es
    lo que hace quien no quiere datos de menores en una carpeta sincronizada.
    Recortar sin preguntar reventaba con `ValueError` **despues** de haber
    escrito el archivo: el trabajo hecho y aun asi un error en pantalla.
    """
    try:
        return str(ruta.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(ruta)


# Las cuatro capas de datos. La regla de oro es que el flujo va siempre hacia
# abajo en esta lista y nunca al reves:
#
#   raw      -> lo que llego de afuera, tal cual llego. NUNCA se edita.
#               (descargas de Jotform, exportaciones de Kydemy, zip de WhatsApp)
#   interim  -> pasos intermedios y cache. Es desechable: se puede borrar todo
#               y reconstruirlo corriendo los scripts otra vez.
#   master   -> la verdad de la escuela. Las tablas del modelo de datos.
#               Es lo unico que se respalda.
#   exports  -> lo que sale para humanos u otros sistemas (Excel, reportes).
#               Desechable tambien: se regenera desde master.
LAYERS = ("raw", "interim", "master", "exports")


def layer_dir(layer: str) -> Path:
    if layer not in LAYERS:
        raise ValueError(f"Capa desconocida: {layer!r}. Validas: {', '.join(LAYERS)}")
    return data_dir() / layer


# --- Convenciones de formato de los CSV --------------------------------
# Se fijan aqui para que TODOS los archivos se lean y escriban igual.
CSV_SEP = ","
CSV_LINE_TERMINATOR = "\n"  # LF siempre, aunque estemos en Windows
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M"  # 24 horas: "5:00 pm" se ordena mal y se compara peor

# Excel en español no abre bien UTF-8 sin BOM: parte los acentos. Por eso los
# archivos que edita gente a mano se guardan con BOM, y los que solo toca el
# codigo se guardan en UTF-8 limpio.
ENCODING_MANAGED = "utf-8"
ENCODING_HAND_EDITED = "utf-8-sig"
