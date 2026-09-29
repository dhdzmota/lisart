"""Pruebas de la proyección de pago.

Lo que importa probar no es la multiplicación: es que un alumno que no se pueda
costear **no desaparezca del reporte**, porque un total que calla lo que le
falta es peor que no tener total.
"""

from datetime import date

import pandas as pd
import pytest

from lisart import io
from lisart.ids import ahora
from lisart.procesos import proyeccion as proy

MARCA = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}


def persona(persona_id, nombre, nacimiento=None):
    return {
        "persona_id": persona_id, "nombre": nombre, "apellido_paterno": "Ruiz",
        "apellido_materno": None, "nombre_normalizado": f"{nombre.lower()} ruiz",
        "fecha_nacimiento": nacimiento, "telefono": None, "correo": None,
        "domicilio": None, "activo": True, **MARCA,
    }


def alumno(persona_id, programa, estatus="inscrito", requiere_tutor=False):
    return {
        "persona_id": persona_id, "estatus": estatus, "fecha_alta": None,
        "fecha_baja": None, "requiere_tutor": requiere_tutor, "programa": programa,
        "notas": None, **MARCA,
    }


def programa(programa_id, precio, nombre="Somos Música"):
    return {
        "programa_id": programa_id, "modalidad": "presencial", "nombre": nombre,
        "categoria": None, "caracteristica": None, "arquetipo": None,
        "descripcion": None, "precio": precio, "activo": True, **MARCA,
    }


@pytest.fixture
def escuela():
    io.write_table("personas", pd.DataFrame([
        persona("PER-0001", "Ana"), persona("PER-0002", "Beto"), persona("PER-0003", "Cami"),
    ]))
    io.write_table("programas", pd.DataFrame([
        programa("PDA_001", 1365.0), programa("PDA_003", 2460.0),
        programa("PDA_011", 375.0), programa("PDA_012", 375.0), programa("PDA_013", 405.0),
    ]))


def test_suma_la_cuota_de_cada_alumno(escuela):
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Somos música (Adulto) Esencial"),
        alumno("PER-0002", "Somos música (Adulto) Especial"),
    ]))
    r = proy.calcular()
    assert r.total_mensual == 1365 + 2460
    assert r.alumnos_cobrables == 2
    assert r.cobertura == 1.0


def test_un_programa_sin_precio_no_se_calla(escuela):
    """El total tiene que decir en voz alta lo que le falta."""
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Somos música (Adulto) Esencial"),
        alumno("PER-0002", "Individual (1xsemana)"),
    ]))
    r = proy.calcular()
    assert r.total_mensual == 1365
    assert len(r.sin_precio) == 1
    assert r.sin_precio.iloc[0]["programa"] == "Individual (1xsemana)"
    assert r.cobertura == 0.5
    assert any("no se pudieron costear" in a for a in r.avisos)
    assert "SIN precio" in r.resumen()


def test_no_se_inventa_un_precio_cuando_no_lo_hay(escuela):
    io.write_table("alumnos", pd.DataFrame([alumno("PER-0001", "Programa inexistente")]))
    r = proy.calcular()
    assert r.total_mensual == 0.0
    assert r.detalle.empty


def test_la_sesion_suelta_cuesta_segun_la_edad(escuela):
    """Es el unico programa cuyo precio depende de quien lo toma."""
    io.write_table("personas", pd.DataFrame([
        persona("PER-0001", "Bebe", date(2024, 1, 1)),
        persona("PER-0002", "Nino", date(2016, 1, 1)),
        persona("PER-0003", "Adulta", date(1990, 1, 1)),
    ]))
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Sesión suelta"),
        alumno("PER-0002", "Sesión suelta"),
        alumno("PER-0003", "Sesión suelta"),
    ]))
    detalle = proy.calcular().detalle
    precios = dict(zip(detalle["persona_id"], detalle["precio"], strict=True))
    assert precios["PER-0001"] == 405.0   # bebé
    assert precios["PER-0002"] == 375.0   # niñ@
    assert precios["PER-0003"] == 375.0   # adulto


def test_sin_fecha_de_nacimiento_se_usa_si_requiere_tutor(escuela):
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Sesión suelta", requiere_tutor=True),
    ]))
    assert proy.calcular().detalle.iloc[0]["precio"] == 375.0


def test_los_dados_de_baja_no_cuentan(escuela):
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Somos música (Adulto) Esencial"),
        alumno("PER-0002", "Somos música (Adulto) Esencial", estatus="baja"),
    ]))
    r = proy.calcular()
    assert r.total_mensual == 1365
    assert any("baja" in a for a in r.avisos)


def test_sin_catalogo_lo_dice_en_vez_de_dar_cero(escuela):
    io.write_table("programas", io.empty_frame("programas"))
    io.write_table("alumnos", pd.DataFrame([alumno("PER-0001", "Somos música (Adulto) Esencial")]))
    r = proy.calcular()
    assert any("ingest catalogos" in a for a in r.avisos)


def test_avisa_que_la_proyeccion_es_bruta(escuela):
    io.write_table("descuentos", pd.DataFrame([{
        "descuento_id": "d1", "nombre": "Familiar", "descripcion": None,
        "valor_porcentual": 0.05, **MARCA,
    }]))
    io.write_table("alumnos", pd.DataFrame([alumno("PER-0001", "Somos música (Adulto) Esencial")]))
    assert any("BRUTA" in a for a in proy.calcular().avisos)


def test_el_reparto_por_programa_cuadra_con_el_total(escuela):
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001", "Somos música (Adulto) Esencial"),
        alumno("PER-0002", "Somos música (Adulto) Esencial"),
        alumno("PER-0003", "Somos música (Adulto) Especial"),
    ]))
    r = proy.calcular()
    reparto = proy.por_programa(r)
    assert reparto["subtotal"].sum() == r.total_mensual
    assert int(reparto[reparto.programa.str.contains("Esencial")]["alumnos"].iloc[0]) == 2


def test_el_reporte_se_escribe_donde_se_regenera(escuela, tmp_path):
    """`exports` es capa desechable: nunca es la fuente de nada."""
    io.write_table("alumnos", pd.DataFrame([alumno("PER-0001", "Somos música (Adulto) Esencial")]))
    escritos = proy.exportar(proy.calcular(), nombre="prueba")
    assert escritos and all(r.parent.name == "exports" for r in escritos)
    assert all(r.exists() for r in escritos)
