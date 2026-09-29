"""Pruebas de los roles.

Lo delicado no es marcar una casilla: es lo que pasa al **quitar** un rol. Si se
borrara la fila, después no habría forma de entender por qué una clase de marzo
estaba asignada a alguien que "nunca fue profesor". Y si al devolvérselo se
creara una segunda fila, se empezaría a contar doble.
"""

from datetime import date

import pandas as pd
import pytest

from lisart import io
from lisart.ids import ahora
from lisart.procesos import roles

MARCA = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}
HOY = date(2026, 8, 17)


def persona(persona_id, nombre, apellido="Ruiz"):
    return {
        "persona_id": persona_id, "nombre": nombre, "apellido_paterno": apellido,
        "apellido_materno": None, "nombre_normalizado": f"{nombre.lower()} {apellido.lower()}",
        "fecha_nacimiento": None, "telefono": "+5218711234567", "correo": None,
        "domicilio": None, "activo": True, **MARCA,
    }


def rol(persona_id, cual, desde=None, hasta=None):
    return {
        "persona_id": persona_id, "rol": cual,
        "vigente_desde": desde, "vigente_hasta": hasta, **MARCA,
    }


@pytest.fixture
def escuela():
    io.write_table("personas", pd.DataFrame([
        persona("PER-0001", "Ana"), persona("PER-0002", "Beto"), persona("PER-0003", "Cami"),
    ]))
    io.write_table("personas_roles", pd.DataFrame([
        rol("PER-0001", "alumno"),
        rol("PER-0002", "tutor"),
        rol("PER-0002", "profesor"),
    ]))


# --- Consultar ---------------------------------------------------------


def test_los_roles_salen_del_esquema():
    """Si mañana se agrega un rol en tables.py, aparece solo en la pantalla."""
    from lisart.tables import PERSONAS_ROLES

    assert roles.ROLES == PERSONAS_ROLES.column("rol").choices


def test_de_persona_devuelve_los_vigentes_en_orden_del_catalogo(escuela):
    # El orden es el del catálogo, no el del archivo: tutor va antes que profesor.
    assert roles.de_persona("PER-0002") == ["tutor", "profesor"]
    assert roles.de_persona("PER-0003") == []


def test_el_directorio_trae_nombres_no_claves(escuela):
    gente = roles.por_rol("tutor")
    assert list(gente["nombre"]) == ["Beto Ruiz"]
    assert gente.iloc[0]["telefono"] == "+5218711234567"
    assert gente.iloc[0]["otros_roles"] == "profesor"


def test_el_conteo_cubre_todos_los_roles(escuela):
    cuenta = roles.conteo()
    assert cuenta["alumno"] == 1
    assert cuenta["tutor"] == 1
    assert cuenta["empleado"] == 0        # los que nadie tiene salen en cero


# --- Cambiar -----------------------------------------------------------


def test_agregar_un_rol_nuevo(escuela):
    cambios = roles.sincronizar("PER-0003", ["empleado"], hoy=HOY)
    assert cambios.agregados == ["empleado"]
    fila = io.read_table("personas_roles").set_index(["persona_id", "rol"]).loc[
        ("PER-0003", "empleado")
    ]
    assert fila["vigente_desde"] == HOY
    assert pd.isna(fila["vigente_hasta"])


def test_quitar_un_rol_lo_cierra_pero_no_lo_borra(escuela):
    """Borrarlo haría imposible saber quién dio clase el semestre pasado."""
    cambios = roles.sincronizar("PER-0002", ["tutor"], hoy=HOY)
    assert cambios.cerrados == ["profesor"]

    tabla = io.read_table("personas_roles")
    fila = tabla.set_index(["persona_id", "rol"]).loc[("PER-0002", "profesor")]
    assert fila["vigente_hasta"] == HOY          # sigue ahí
    assert roles.de_persona("PER-0002") == ["tutor"]
    assert len(tabla) == 3                        # no se perdió ninguna fila


def test_devolver_un_rol_reabre_la_misma_fila(escuela):
    """Dos filas para la misma (persona, rol) es como se empieza a contar doble."""
    roles.sincronizar("PER-0002", ["tutor"], hoy=HOY)
    cambios = roles.sincronizar("PER-0002", ["tutor", "profesor"], hoy=HOY)

    assert cambios.reabiertos == ["profesor"]
    tabla = io.read_table("personas_roles")
    del_par = tabla[(tabla["persona_id"] == "PER-0002") & (tabla["rol"] == "profesor")]
    assert len(del_par) == 1
    assert pd.isna(del_par.iloc[0]["vigente_hasta"])


def test_sin_cambios_no_escribe_ni_respalda(escuela):
    from lisart import backup

    cambios = roles.sincronizar("PER-0002", ["tutor", "profesor"], hoy=HOY)
    assert not cambios
    assert backup.listar("personas_roles") == []


def test_un_rol_que_no_existe_se_ignora(escuela):
    """La pantalla ofrece solo los del catálogo; esto cubre el resto de llamadas."""
    cambios = roles.sincronizar("PER-0003", ["inventado"], hoy=HOY)
    assert not cambios
    assert roles.de_persona("PER-0003") == []


def test_el_directorio_puede_incluir_a_los_cerrados(escuela):
    roles.sincronizar("PER-0002", ["tutor"], hoy=HOY)
    assert roles.por_rol("profesor").empty
    con_cerrados = roles.por_rol("profesor", incluir_cerrados=True)
    assert list(con_cerrados["nombre"]) == ["Beto Ruiz"]
    assert con_cerrados.iloc[0]["vigente_hasta"] == HOY


def test_quitar_todos_los_roles_deja_a_la_persona_sin_ninguno(escuela):
    """Es un estado legítimo: 78 personas de la base solo son contacto de emergencia."""
    roles.sincronizar("PER-0001", [], hoy=HOY)
    assert roles.de_persona("PER-0001") == []
    assert len(io.read_table("personas_roles")) == 3
