"""El vault se genera desde `tables.py`, asi que lo que se prueba es que el
grafo refleje el modelo y que no pise las notas que escribio una persona."""

import re

import pytest

from lisart.tables import REGISTRY
from lisart.vault import build_vault


@pytest.fixture
def vault(tmp_path):
    build_vault(tmp_path)
    return tmp_path


def enlaces(texto: str) -> set[str]:
    return set(re.findall(r"\[\[([^\]]+)\]\]", texto))


def test_hay_una_nota_por_tabla(vault):
    notas = {p.stem for p in (vault / "Tablas").glob("*.md")}
    assert notas == set(REGISTRY.tables)


def test_las_llaves_foraneas_se_vuelven_enlaces(vault):
    texto = (vault / "Tablas" / "relaciones.md").read_text(encoding="utf-8")
    assert {"alumnos", "personas"} <= enlaces(texto)


def test_los_enlaces_de_vuelta_tambien_estan(vault):
    """personas no sabe quien le apunta; la nota si tiene que decirlo."""
    texto = (vault / "Tablas" / "personas.md").read_text(encoding="utf-8")
    assert "## Le apuntan" in texto
    assert {"alumnos", "personas_roles", "identificadores_externos"} <= enlaces(texto)


def test_los_catalogos_aparecen_en_el_diagrama(vault):
    """Sin llaves foraneas quedarian fuera del ER y parecerian no existir."""
    diagrama = (vault / "Lisart.md").read_text(encoding="utf-8")
    assert "erDiagram" in diagrama
    for catalogo in ("espacios", "instrumentos", "conceptos"):
        assert catalogo in diagrama


def test_los_proyectos_enlazan_a_tablas_que_faltan(vault):
    """Esos enlaces rotos son a proposito: en el grafo marcan lo que falta."""
    texto = (vault / "Proyectos" / "Proyecto 3 - Centralizacion de pagos.md").read_text(
        encoding="utf-8"
    )
    pendientes = {"pagos", "inscripciones", "proyeccion_pagos"}
    assert pendientes <= enlaces(texto)
    assert not (vault / "Tablas" / "pagos.md").exists()


def test_no_pisa_las_notas_editadas_a_mano(vault):
    nota = vault / "Proyectos" / "Proyecto 1 - Mensajes automaticos.md"
    nota.write_text("# Mio\nLo escribi yo.\n", encoding="utf-8")

    build_vault(vault)
    assert "Lo escribi yo." in nota.read_text(encoding="utf-8")

    build_vault(vault, forzar=True)
    assert "Lo escribi yo." not in nota.read_text(encoding="utf-8")


def test_regenerar_borra_la_nota_de_una_tabla_que_ya_no_existe(vault):
    fantasma = vault / "Tablas" / "tabla_vieja.md"
    fantasma.write_text("# tabla_vieja\n", encoding="utf-8")

    build_vault(vault)
    assert not fantasma.exists()
