"""Pruebas de la pantalla.

Se usa AppTest, que corre la app de verdad sin navegador. Lo que se prueba no
es el diseño sino lo que puede hacer perder datos: que las flechas se muevan,
y que lo que no se debe editar no se pueda editar.
"""

from datetime import time

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from lisart import io
from lisart.config import PROJECT_ROOT

APP = str(PROJECT_ROOT / "src" / "lisart" / "ui" / "app.py")

# Cada corrida ejecuta la app entera (9 tablas, ~200 controles). Son lentas:
# para el ciclo rapido, `pytest -m "not ui"`.
pytestmark = pytest.mark.ui

VACIAS = (
    "personas", "alumnos", "relaciones", "personas_roles",
    "identificadores_externos", "instrumentos", "conceptos",
    "respuestas_inscripcion",
)


def espacio(espacio_id, nombre, **cambios):
    fila = {
        "espacio_id": espacio_id, "nombre": nombre, "tipo": "aula",
        "piso": "planta_baja", "agendable": True, "capacidad": None,
        "equipamiento": None, "notas": None, "activo": True,
    }
    fila.update(cambios)
    return fila


def abrir(seccion: str = "espacios"):
    """Abre la app en una sección. Solo se arma la que se está viendo."""
    at = AppTest.from_file(APP, default_timeout=180).run()
    return at.radio(key="nav").set_value(seccion).run()


@pytest.fixture
def app():
    st.cache_data.clear()
    io.write_table("espacios", pd.DataFrame([
        espacio("AULA-1", "Aula uno"),
        espacio("AULA-2", "Aula dos"),
        espacio("AULA-3", "Aula tres"),
    ]))
    for tabla in VACIAS:
        io.write_table(tabla, io.empty_frame(tabla))
    return abrir("espacios")


def boton(at, clave):
    return next(b for b in at.button if b.key == clave)


def campo(widgets, tabla, columna):
    """Los controles llevan el registro en la llave: campo::tabla::PK::columna."""
    sufijo = f"::{columna}"
    return next(w for w in widgets if w.key and w.key.startswith(f"campo::{tabla}::")
                and w.key.endswith(sufijo))


def textos(at) -> str:
    return " ".join(str(m.value) for m in at.markdown)


def posicion(at) -> str:
    """'3 / 240' — se saca del indicador del pentagrama."""
    import re

    m = re.search(r'lis-pos__n">(\d+) <em>/ (\d+)', textos(at))
    return f"{m.group(1)} / {m.group(2)}" if m else "sin posicion"


def test_la_app_corre_sin_errores(app):
    assert not app.exception


def test_hay_una_seccion_por_tabla_mas_horarios_y_grafo(app):
    from lisart.tables import REGISTRY

    assert len(app.radio(key="nav").options) == len(REGISTRY) + 2


def test_las_vistas_van_al_final_despues_de_las_tablas(app):
    # AppTest devuelve la etiqueta que se muestra, no la clave interna.
    assert app.radio(key="nav").options[-2:] == ["Horarios", "Grafo"]


def test_arranca_en_el_primer_registro(app):
    assert posicion(app) == "1 / 3"


def test_la_flecha_derecha_avanza(app):
    despues = boton(app, "sig::espacios").click().run()
    assert not despues.exception
    assert posicion(despues) == "2 / 3"


def test_la_flecha_izquierda_regresa(app):
    at = boton(app, "sig::espacios").click().run()
    at = boton(at, "ant::espacios").click().run()
    assert posicion(at) == "1 / 3"


def test_no_se_puede_retroceder_desde_el_primero(app):
    assert boton(app, "ant::espacios").disabled


def test_no_se_puede_avanzar_desde_el_ultimo(app):
    at = boton(app, "sig::espacios").click().run()
    at = boton(at, "sig::espacios").click().run()
    assert posicion(at) == "3 / 3"
    assert boton(at, "sig::espacios").disabled


def test_la_busqueda_reduce_los_registros(app):
    at = app.text_input(key="buscar::espacios").set_value("dos").run()
    assert not at.exception
    assert posicion(at) == "1 / 1"


def test_la_llave_primaria_no_se_puede_editar(app):
    """Cambiarla dejaria referencias colgando en otras tablas."""
    control = campo(app.text_input, "espacios", "espacio_id")
    assert control.disabled


def test_un_catalogo_se_muestra_como_lista_desplegable(app):
    tipo = campo(app.selectbox, "espacios", "tipo")
    assert "aula" in tipo.options and "cocina" in tipo.options


def test_una_tabla_de_capa_interim_avisa_que_es_solo_lectura():
    """`respuestas_inscripcion` se regenera desde raw: editarla seria perder el rato."""
    from lisart.fuentes import jotform

    st.cache_data.clear()
    jotform.ingestar(
        envios=[{
            "id": "1", "form_id": "f", "ip": "1.1.1.1",
            "created_at": "2026-06-01 10:00:00", "status": "ACTIVE",
            "answers": {"a": {"name": "n", "order": "15", "type": "control_fullname",
                              "answer": {"first": "Ana", "middle": "R", "last": "P"}}},
        }],
        guardar_crudo=False,
    )
    at = abrir("respuestas_inscripcion")
    # El aviso es propio (los de Streamlit vienen en azul de sistema).
    assert "lis-aviso" in textos(at)
    assert "interim" in textos(at)


def test_las_marcas_de_tiempo_no_se_pueden_editar():
    io.write_table("personas", pd.DataFrame([{
        "persona_id": "PER-0001", "nombre": "Ana", "apellido_paterno": None,
        "apellido_materno": None, "nombre_normalizado": "ana",
        "fecha_nacimiento": None, "telefono": None, "correo": None,
        "domicilio": None, "activo": True,
        "creado_en": pd.Timestamp("2026-01-01"), "actualizado_en": pd.Timestamp("2026-01-01"),
        "fuente": "manual",
    }]))
    st.cache_data.clear()
    at = abrir("personas")
    control = campo(at.text_input, "personas", "creado_en")
    assert control.disabled


def test_una_llave_foranea_se_ofrece_como_lista_de_valores_validos():
    """Asi no se puede escribir a mano una referencia a alguien que no existe."""
    marca = pd.Timestamp("2026-01-01")
    persona = {
        "apellido_paterno": None, "apellido_materno": None,
        "fecha_nacimiento": None, "telefono": None, "correo": None,
        "domicilio": None, "activo": True, "creado_en": marca,
        "actualizado_en": marca, "fuente": "manual",
    }
    io.write_table("personas", pd.DataFrame([
        {"persona_id": "PER-0001", "nombre": "Ana", "nombre_normalizado": "ana ruiz", **persona},
        {"persona_id": "PER-0002", "nombre": "Rosa", "nombre_normalizado": "rosa ruiz", **persona},
    ]))
    io.write_table("alumnos", pd.DataFrame([{
        "persona_id": "PER-0001", "estatus": "inscrito", "fecha_alta": None,
        "fecha_baja": None, "requiere_tutor": True, "programa": None, "notas": None,
        "creado_en": marca, "actualizado_en": marca, "fuente": "manual",
    }]))
    io.write_table("relaciones", pd.DataFrame([{
        "relacion_id": "REL-0001", "alumno_persona_id": "PER-0001",
        "relacionado_persona_id": "PER-0002", "tipo": "tutor", "parentesco": None,
        "vigente": True, "creado_en": marca, "actualizado_en": marca, "fuente": "manual",
    }]))
    st.cache_data.clear()
    at = abrir("relaciones")

    selector = campo(at.selectbox, "relaciones", "relacionado_persona_id")
    assert any(o.startswith("PER-0002") for o in selector.options)
    # Muestra el nombre tal como se escribe, no el normalizado ni solo el id.
    assert any("Rosa" in o for o in selector.options)


def test_el_pentagrama_marca_la_posicion(app):
    """La nota roja es el registro actual; moverse la mueve por el pentagrama."""
    import re

    def x_de_la_nota(at) -> float:
        m = re.search(r'class="actual" cx="([\d.]+)"', textos(at))
        return float(m.group(1))

    inicio = x_de_la_nota(app)
    despues = boton(app, "sig::espacios").click().run()
    assert x_de_la_nota(despues) > inicio


def test_los_rotulos_no_repiten_el_nombre_del_grupo():
    """Dentro de la seccion ALUMNO, el campo no se llama 'alumno nombre ...'."""
    from lisart.ui.app import _etiqueta_campo

    assert _etiqueta_campo("alumno__nombre_completo___nombre", "Alumno") == "nombre"
    assert _etiqueta_campo("tutor__telefono___txt", "Tutor") == "teléfono"
    assert _etiqueta_campo("tutor__domicilio___txt", "Tutor") == "domicilio"
    # Sin grupo, el nombre completo de la columna
    assert _etiqueta_campo("telefono") == "teléfono"


def test_al_cambiar_de_registro_el_formulario_muestra_el_nuevo(app):
    """Bug real: Streamlit guarda el estado por `key`. Si dos registros comparten
    llave de widget, al avanzar los campos siguen mostrando —y guardando— los
    datos del registro anterior."""
    assert campo(app.text_input, "espacios", "nombre").value == "Aula uno"

    despues = boton(app, "sig::espacios").click().run()
    assert campo(despues.text_input, "espacios", "nombre").value == "Aula dos"


def test_el_grafo_dibuja_los_nodos_como_figuras_musicales():
    """Negra el alumno, corchea el tutor, redonda el instrumento. Sin maestro:
    el formulario no pregunta quien da la clase."""
    from lisart.ui import grafo

    assert set(grafo.ETIQUETA_TIPO) == {"alumno", "persona", "instrumento"}
    assert grafo.FIGURA["instrumento"] == "redonda"
    assert "profesor" not in grafo.COLORES


def test_la_lente_todo_junta_las_otras_dos():
    from lisart.ui import grafo

    assert "todo" in grafo.LENTES
    inst = grafo.construir("instrumentos")[0].number_of_edges()
    fam = grafo.construir("familias")[0].number_of_edges()
    assert grafo.construir("todo")[0].number_of_edges() == inst + fam


# --- La pantalla de profesores (aplicación aparte) ---------------------


APP_PROFES = str(PROJECT_ROOT / "src" / "lisart" / "ui" / "app_profesores.py")


def test_la_pantalla_de_profesores_corre_sin_errores():
    st.cache_data.clear()
    for tabla in ("clases", "clases_profesores", "clases_alumnos", "disponibilidad"):
        io.write_table(tabla, io.empty_frame(tabla))
    at = AppTest.from_file(APP_PROFES, default_timeout=180).run()
    assert not at.exception


def test_sin_clases_invita_a_crear_la_primera():
    """Una pantalla vacía es una invitación a actuar, no un callejón."""
    st.cache_data.clear()
    io.write_table("clases", io.empty_frame("clases"))
    at = AppTest.from_file(APP_PROFES, default_timeout=180).run()
    texto = " ".join(str(m.value) for m in at.markdown)
    assert "no hay clases capturadas" in texto
    assert len(at.get("form")) == 1  # el de crear la clase


def test_un_bloque_sin_motivo_no_truena_al_listarse():
    """Regresión: `if fila["motivo"]` con pd.NA lanza 'boolean value of NA is
    ambiguous'. Pandas se niega a adivinar si un dato faltante es verdadero."""
    import pandas as pd

    from lisart.ids import ahora
    from lisart.ui.app import tiene_valor

    marca = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}
    io.write_table("personas", pd.DataFrame([{
        "persona_id": "PER-0001", "nombre": "Ana", "apellido_paterno": None,
        "apellido_materno": None, "nombre_normalizado": "ana",
        "fecha_nacimiento": None, "telefono": None, "correo": None,
        "domicilio": None, "activo": True, **marca,
    }]))
    io.write_table("disponibilidad", pd.DataFrame([{
        "disponibilidad_id": "DIS-0001", "persona_id": "PER-0001", "dia": "L",
        "hora_inicio": time(9, 0), "hora_fin": time(10, 0), "estado": "disponible",
        "motivo": None, "vigente_desde": None, "vigente_hasta": None, **marca,
    }]))

    leido = io.read_table("disponibilidad").iloc[0]
    assert tiene_valor(leido["motivo"]) is False   # y no revienta

    st.cache_data.clear()
    at = abrir("horarios")
    assert not at.exception


# --- Roles: directorio y ficha -----------------------------------------


def persona_min(persona_id, nombre):
    from lisart.ids import ahora
    marca = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}
    return {
        "persona_id": persona_id, "nombre": nombre, "apellido_paterno": "Ruiz",
        "apellido_materno": None, "nombre_normalizado": f"{nombre.lower()} ruiz",
        "fecha_nacimiento": None, "telefono": "+5218711234567", "correo": None,
        "domicilio": None, "activo": True, **marca,
    }


@pytest.fixture
def con_personas():
    from lisart.ids import ahora
    marca = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}
    st.cache_data.clear()
    for tabla in VACIAS:
        io.write_table(tabla, io.empty_frame(tabla))
    io.write_table("personas", pd.DataFrame([
        persona_min("PER-0001", "Ana"), persona_min("PER-0002", "Beto"),
    ]))
    io.write_table("personas_roles", pd.DataFrame([
        {"persona_id": "PER-0001", "rol": "tutor",
         "vigente_desde": None, "vigente_hasta": None, **marca},
    ]))


def test_el_directorio_de_roles_lista_a_las_personas(con_personas):
    at = abrir("personas_roles")
    assert not at.exception

    # Empieza en el primer rol del catálogo, que aquí no lo tiene nadie: en vez
    # de una tabla vacía, lo dice con palabras.
    assert not at.dataframe
    assert any("Nadie tiene el rol" in str(m.value) for m in at.markdown)

    at = at.radio(key="rol_elegido").set_value("tutor").run()
    assert "Ana Ruiz" in at.dataframe[0].value["nombre"].tolist()
    assert at.dataframe[0].value["telefono"].iloc[0] == "+5218711234567"


def test_los_roles_se_editan_desde_la_ficha_de_la_persona(con_personas):
    """El cambio va a `personas_roles`, aunque se haga en la pantalla de personas."""
    from lisart.procesos import roles

    at = abrir("personas")
    seleccion = next(m for m in at.multiselect if m.key.startswith("roles::"))
    assert seleccion.value == ["tutor"]

    seleccion.set_value(["tutor", "profesor"]).run()
    next(b for b in at.button if "Guardar" in str(b.label)).click().run()

    assert not at.exception
    assert roles.de_persona("PER-0001") == ["tutor", "profesor"]


def test_quitar_un_rol_desde_la_pantalla_lo_cierra(con_personas):
    from lisart.procesos import roles

    at = abrir("personas")
    seleccion = next(m for m in at.multiselect if m.key.startswith("roles::"))
    seleccion.set_value([]).run()
    next(b for b in at.button if "Guardar" in str(b.label)).click().run()

    assert not at.exception
    assert roles.de_persona("PER-0001") == []
    # La fila sigue ahí, cerrada: es lo que permite saber quién fue qué.
    assert len(io.read_table("personas_roles")) == 1
