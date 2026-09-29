"""Identificadores y normalizacion de datos de identidad.

Dos problemas distintos viven aqui:

1. Inventar identificadores nuevos (PER-0001) que sean estables y legibles.
   Legibles importa: alguien va a leer un ID en voz alta por telefono.

2. Normalizar nombres y telefonos. Es la unica forma de cruzar tres fuentes
   que escriben "Ma. José Hernández", "MARIA JOSE HERNANDEZ" y "maria jose
   hernandez" para referirse a la misma nina.

Sobre la normalizacion: NUNCA reemplaza al dato original. El nombre se guarda
tal como lo escribio la familia; la version normalizada va en una columna
aparte y solo sirve para comparar.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

import pandas as pd

from lisart.schema import Table
from lisart.tables import REGISTRY

# Prefijo del ID de cada tabla que genera identificadores propios.
ID_PREFIXES: dict[str, str] = {
    "personas": "PER",
    "relaciones": "REL",
    "disponibilidad": "DIS",
    "clases": "CLA",
    "alumnos_descuentos": "ALD",
}

ID_WIDTH = 4  # PER-0001. Alcanza para 9999; a partir de ahi crece solo.
_ID_RE = re.compile(r"^([A-Z]+)-(\d+)$")

# Lada de Mexico. Se usa para completar telefonos capturados sin codigo de pais.
LADA_DEFAULT = "52"


def ahora() -> datetime:
    """Marca de tiempo para las columnas creado_en / actualizado_en."""
    return datetime.now().replace(microsecond=0)


# --- Identificadores ---------------------------------------------------


def next_ids(table: str | Table, n: int = 1) -> list[str]:
    """Genera los siguientes `n` identificadores libres de una tabla.

    Lee la tabla para saber en cuanto va. Funciona porque estos CSV tienen un
    solo escritor a la vez; el dia que dos procesos escriban en paralelo, esto
    es lo primero que hay que cambiar (y la senal de que toca base de datos).
    """
    from lisart import io

    tbl = table if isinstance(table, Table) else REGISTRY.get(table)
    prefix = ID_PREFIXES.get(tbl.name)
    if prefix is None:
        raise ValueError(f"{tbl.name} no genera identificadores propios (ver ID_PREFIXES)")

    columna = tbl.primary_key[0]
    existentes = io.read_table(tbl, strict=False)[columna].dropna().astype(str)
    maximo = 0
    for valor in existentes:
        m = _ID_RE.match(valor)
        if m and m.group(1) == prefix:
            maximo = max(maximo, int(m.group(2)))

    return [f"{prefix}-{i:0{ID_WIDTH}d}" for i in range(maximo + 1, maximo + 1 + n)]


# --- Normalizacion -----------------------------------------------------


def sin_acentos(texto: str) -> str:
    """Quita acentos y diereses, pero respeta la ñ (no es un adorno: cambia la palabra)."""
    texto = texto.replace("ñ", "\x00").replace("Ñ", "\x01")
    descompuesto = unicodedata.normalize("NFD", texto)
    limpio = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return limpio.replace("\x00", "ñ").replace("\x01", "Ñ")


def normalizar_nombre(nombre: str | None) -> str | None:
    """Version comparable de un nombre: sin acentos, minusculas, sin puntuacion.

    >>> normalizar_nombre("  María  José   Hernández-López ")
    'maria jose hernandez lopez'
    """
    if nombre is None or (isinstance(nombre, float) and pd.isna(nombre)) or pd.isna(nombre):
        return None
    texto = sin_acentos(str(nombre)).lower()
    texto = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def nombre_completo(nombre, apellido_paterno=None, apellido_materno=None) -> str:
    """Arma el nombre completo saltandose las partes vacias.

    El `pd.isna` va ANTES de evaluar el valor: una celda vacia que viene de
    pandas es `pd.NA`, y preguntarle si es verdadera revienta con "boolean
    value of NA is ambiguous". Es la trampa numero uno de este proyecto.
    """
    partes = [
        p
        for p in (nombre, apellido_paterno, apellido_materno)
        if p is not None and not pd.isna(p) and str(p).strip()
    ]
    return " ".join(str(p).strip() for p in partes)


def normalizar_telefono(telefono: str | None, lada: str = LADA_DEFAULT) -> str | None:
    """Deja un telefono en formato E.164 (+5215512345678) o None si no se puede.

    En Mexico conviven celulares de 10 digitos, con el 1 de movil y con 044/045
    heredados. WhatsApp solo entiende E.164, asi que se guarda asi.

    >>> normalizar_telefono("55 1234 5678")
    '+525512345678'
    """
    if telefono is None or pd.isna(telefono):
        return None
    digitos = re.sub(r"\D", "", str(telefono))
    if not digitos:
        return None

    if digitos.startswith("044") or digitos.startswith("045"):
        digitos = digitos[3:]
    if len(digitos) == 10:
        digitos = lada + digitos
    elif len(digitos) == 11 and digitos.startswith("1"):
        digitos = lada + digitos[1:]

    # Un numero valido trae lada de pais + 10 digitos. Fuera de ese rango
    # preferimos devolver None a inventar un telefono.
    if not (11 <= len(digitos) <= 15):
        return None
    return "+" + digitos


def normalizar_correo(correo: str | None) -> str | None:
    """Minusculas y sin espacios. No valida que exista, solo que sea comparable."""
    if correo is None or pd.isna(correo):
        return None
    texto = str(correo).strip().lower()
    return texto if "@" in texto else None
