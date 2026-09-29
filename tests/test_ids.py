import pandas as pd
import pytest

from lisart import io
from lisart.ids import (
    ahora,
    next_ids,
    nombre_completo,
    normalizar_correo,
    normalizar_nombre,
    normalizar_telefono,
)


def test_next_ids_empieza_en_uno_con_tabla_vacia():
    assert next_ids("personas", 3) == ["PER-0001", "PER-0002", "PER-0003"]


def test_next_ids_continua_despues_del_maximo():
    io.write_table(
        "personas",
        pd.DataFrame(
            [{
                "persona_id": "PER-0007", "nombre": "Maria", "apellido_paterno": None,
                "apellido_materno": None, "nombre_normalizado": "maria",
                "fecha_nacimiento": None, "telefono": None, "correo": None,
                "domicilio": None, "activo": True, "creado_en": ahora(),
                "actualizado_en": ahora(), "fuente": "manual",
            }]
        ),
    )
    assert next_ids("personas") == ["PER-0008"]


def test_next_ids_rechaza_tablas_sin_prefijo():
    with pytest.raises(ValueError, match="identificadores"):
        next_ids("espacios")


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("  María  José   Hernández-López ", "maria jose hernandez lopez"),
        ("MARIA JOSE HERNANDEZ LOPEZ", "maria jose hernandez lopez"),
        ("Ma. José Hernández López", "ma jose hernandez lopez"),
        (None, None),
        ("", None),
    ],
)
def test_normalizar_nombre(entrada, esperado):
    assert normalizar_nombre(entrada) == esperado


def test_la_enie_sobrevive_a_la_normalizacion():
    """Quitar la ñ cambia la palabra: Peña y Pena no son el mismo apellido."""
    assert normalizar_nombre("Peña") == "peña"


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("5512345678", "+525512345678"),
        ("55 1234 5678", "+525512345678"),
        ("(55) 1234-5678", "+525512345678"),
        ("15512345678", "+525512345678"),
        ("0445512345678", "+525512345678"),
        ("+52 55 1234 5678", "+525512345678"),
        ("1234", None),
        (None, None),
    ],
)
def test_normalizar_telefono(entrada, esperado):
    assert normalizar_telefono(entrada) == esperado


def test_nombre_completo_ignora_partes_vacias():
    assert nombre_completo("Maria", None, "Lopez") == "Maria Lopez"
    assert nombre_completo("Maria", "Hernandez", "Lopez") == "Maria Hernandez Lopez"


def test_nombre_completo_aguanta_celdas_vacias_de_pandas():
    """Regresion: `if celda` con pd.NA revienta con 'boolean value of NA is ambiguous'.

    Pasa siempre que el nombre viene de una fila leida con `read_table`, que es
    justo como lo usan los procesos.
    """
    assert nombre_completo("Maria", pd.NA, "Lopez") == "Maria Lopez"
    assert nombre_completo("Maria", pd.NA, pd.NA) == "Maria"


def test_normalizar_correo():
    assert normalizar_correo("  Maria@Example.COM ") == "maria@example.com"
    assert normalizar_correo("no-es-correo") is None
