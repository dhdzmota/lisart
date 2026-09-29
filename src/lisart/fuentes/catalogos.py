"""El catálogo comercial de la escuela, que vive en un Excel.

`data/catalogos_lisart.xlsx` lo mantiene la escuela a mano. Aquí se trata como
**fuente cruda**, igual que Jotform: se guarda una copia con fecha en
`data/raw/catalogos/` y de ahí se escriben las tablas. Así la escuela sigue
editando su Excel y basta con volver a ingestar.

    lisart ingest catalogos

Qué trae cada hoja
------------------
    programas_aprendizaje  -> `programas`     (con el PRECIO mensual)
    oferta_clases          -> enriquece `instrumentos` con su clave y descripción
    descuentos             -> `descuentos`
    clases, Sheet2         -> vacías, se ignoran

Lo que NO se toca
-----------------
`instrumentos` ya existe con sus propias claves (`PIANO`, `VIOLIN`), y
`alumnos_instrumentos` apunta a ellas con 129 filas. Cambiarlas por las de la
escuela (`PIA`, `VIO`) rompería esas referencias, así que la clave de la escuela
entra como una **columna más** (`code`) y las claves internas se quedan. Si
algún día se prefieren las de la escuela como llave, es una migración aparte.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from lisart import io
from lisart.config import PROJECT_ROOT, layer_dir
from lisart.ids import ahora, normalizar_nombre

EXCEL = PROJECT_ROOT / "data" / "catalogos_lisart.xlsx"

HOJAS = {
    "programas": "programas_aprendizaje",
    "instrumentos": "oferta_clases",
    "descuentos": "descuentos",
}


@dataclass
class Resultado:
    programas: int = 0
    descuentos: int = 0
    instrumentos_enriquecidos: int = 0
    copia_raw: Path | None = None
    avisos: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (
            f"{self.programas} programa(s) con precio, {self.descuentos} descuento(s), "
            f"{self.instrumentos_enriquecidos} instrumento(s) enriquecido(s)."
        )


def _guardar_raw(origen: Path) -> Path:
    """Copia el Excel con fecha. `raw` es la única copia que no depende de que
    nadie sobreescriba el archivo de trabajo."""
    destino = layer_dir("raw") / "catalogos"
    destino.mkdir(parents=True, exist_ok=True)
    copia = destino / f"catalogos_{datetime.now().strftime('%Y%m%dT%H%M%S')}.xlsx"
    shutil.copy2(origen, copia)
    return copia


def _texto(valor) -> str | None:
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def ingestar(ruta: Path | None = None, *, guardar_crudo: bool = True) -> Resultado:
    """Lee el Excel y escribe `programas`, `descuentos` e `instrumentos.code`."""
    origen = ruta or EXCEL
    if not origen.exists():
        raise FileNotFoundError(
            f"No se encontro {origen}. Es el Excel de catalogos que mantiene la escuela."
        )

    resultado = Resultado()
    if guardar_crudo:
        resultado.copia_raw = _guardar_raw(origen)

    hojas = pd.ExcelFile(origen).sheet_names
    momento = ahora()
    marca = {"creado_en": momento, "actualizado_en": momento, "fuente": "manual"}

    # --- Programas ------------------------------------------------------
    if HOJAS["programas"] in hojas:
        crudo = pd.read_excel(origen, sheet_name=HOJAS["programas"])
        filas = [
            {
                "programa_id": _texto(f["pda_id"]),
                "modalidad": _texto(f.get("modalidad")),
                "nombre": _texto(f.get("nombre")),
                "categoria": _texto(f.get("categoria")),
                "caracteristica": _texto(f.get("caracteristica")),
                "arquetipo": _texto(f.get("arquetipo")),
                "descripcion": _texto(f.get("descripcion")),
                "precio": float(f["precio"]),
                "activo": bool(f.get("activo", 1)),
                **marca,
            }
            for _, f in crudo.iterrows()
            if _texto(f.get("pda_id")) and pd.notna(f.get("precio"))
        ]
        if filas:
            io.upsert("programas", pd.DataFrame(filas))
            resultado.programas = len(filas)

    # --- Descuentos -----------------------------------------------------
    if HOJAS["descuentos"] in hojas:
        crudo = pd.read_excel(origen, sheet_name=HOJAS["descuentos"])
        filas = [
            {
                "descuento_id": _texto(f["descuento_id"]),
                "nombre": _texto(f.get("nombre")),
                "descripcion": _texto(f.get("descripcion")),
                "valor_porcentual": float(f["valor_porcentual"]),
                **marca,
            }
            for _, f in crudo.iterrows()
            if _texto(f.get("descuento_id")) and pd.notna(f.get("valor_porcentual"))
        ]
        if filas:
            io.upsert("descuentos", pd.DataFrame(filas))
            resultado.descuentos = len(filas)
            resultado.avisos.extend(_revisar_descuentos(pd.DataFrame(filas)))

    # --- Instrumentos: solo se enriquecen ------------------------------
    if HOJAS["instrumentos"] in hojas:
        crudo = pd.read_excel(origen, sheet_name=HOJAS["instrumentos"])
        resultado.instrumentos_enriquecidos, avisos = _enriquecer_instrumentos(crudo, momento)
        resultado.avisos.extend(avisos)

    return resultado


def _revisar_descuentos(descuentos: pd.DataFrame) -> list[str]:
    """El Excel mezcla unidades en la misma columna. Mejor decirlo que adivinar."""
    fracciones = descuentos[descuentos["valor_porcentual"].between(0.0001, 1)]
    porcentajes = descuentos[descuentos["valor_porcentual"] > 1]
    if len(fracciones) and len(porcentajes):
        return [
            "La columna `valor_porcentual` de los descuentos mezcla unidades: "
            f"{len(fracciones)} valor(es) parecen fracciones (0.05 = 5%) y "
            f"{len(porcentajes)} parecen porcentajes (100.00 = 100%). Se guardaron "
            "tal cual; hay que aclararlo con la escuela antes de aplicarlos a un cobro."
        ]
    return []


def _enriquecer_instrumentos(crudo: pd.DataFrame, momento) -> tuple[int, list[str]]:
    """Le pega la clave y la descripcion de la escuela a los instrumentos que ya
    existen. No da de alta ninguno: el catalogo lo manda una persona."""
    actuales = io.read_table("instrumentos")
    if actuales.empty:
        return 0, ["El catalogo de instrumentos esta vacio: no habia que enriquecer."]

    por_nombre = {
        normalizar_nombre(_texto(f.get("instrumento"))): (
            _texto(f.get("code")), _texto(f.get("descripcion"))
        )
        for _, f in crudo.iterrows()
        if _texto(f.get("instrumento"))
    }

    tocados, sin_catalogo = 0, []
    for i, fila in actuales.iterrows():
        clave = normalizar_nombre(str(fila["nombre"]))
        if clave not in por_nombre:
            sin_catalogo.append(str(fila["nombre"]))
            continue
        code, descripcion = por_nombre[clave]
        actuales.at[i, "code"] = code
        actuales.at[i, "descripcion"] = descripcion
        actuales.at[i, "actualizado_en"] = momento
        tocados += 1

    io.write_table("instrumentos", actuales)

    avisos = []
    if sin_catalogo:
        avisos.append(
            f"{len(sin_catalogo)} instrumento(s) que los alumnos eligieron no estan en la "
            f"hoja `oferta_clases`: {', '.join(sorted(sin_catalogo))}. O se agregan al "
            "Excel o se revisa el formulario."
        )
    del_excel = set(por_nombre)
    de_la_base = {normalizar_nombre(str(n)) for n in actuales["nombre"]}
    nadie = del_excel - de_la_base
    if nadie:
        nombres = sorted(
            _texto(f.get("instrumento"))
            for _, f in crudo.iterrows()
            if normalizar_nombre(_texto(f.get("instrumento"))) in nadie
        )
        avisos.append(
            f"{len(nombres)} instrumento(s) del catalogo que nadie eligio: "
            f"{', '.join(nombres)}. Es informacion, no un error."
        )
    return tocados, avisos
