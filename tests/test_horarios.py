"""Pruebas de los horarios y de la reposición.

Lo que se prueba no es que el código corra, sino las reglas que la escuela dijo:
tres estados, que lo bloqueado gane sobre lo disponible, y que una reposición
solo se ofrezca cuando el profesor **y** el alumno pueden.
"""

from datetime import date, time

import pandas as pd
import pytest

from lisart import io
from lisart.ids import ahora
from lisart.procesos import horarios

MARCA = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}


def persona(persona_id, nombre):
    return {
        "persona_id": persona_id, "nombre": nombre, "apellido_paterno": "Ruiz",
        "apellido_materno": None, "nombre_normalizado": f"{nombre.lower()} ruiz",
        "fecha_nacimiento": None, "telefono": None, "correo": None,
        "domicilio": None, "activo": True, **MARCA,
    }


def bloque(id_, persona_id, dia, desde, hasta, estado="disponible", **extra):
    fila = {
        "disponibilidad_id": id_, "persona_id": persona_id, "dia": dia,
        "hora_inicio": time(*desde), "hora_fin": time(*hasta), "estado": estado,
        "motivo": None, "vigente_desde": None, "vigente_hasta": None, **MARCA,
    }
    fila.update(extra)
    return fila


def sembrar_disponibilidad(*bloques):
    io.write_table("disponibilidad", pd.DataFrame(list(bloques)))


@pytest.fixture
def escuela():
    """Un profesor, una alumna, y una clase que los une."""
    io.write_table("personas", pd.DataFrame([
        persona("PER-0001", "Ana"), persona("PER-0002", "Rosa"), persona("PER-0003", "Luis"),
    ]))
    io.write_table("alumnos", pd.DataFrame([{
        "persona_id": "PER-0001", "estatus": "inscrito", "fecha_alta": None,
        "fecha_baja": None, "requiere_tutor": False, "programa": None,
        "notas": None, **MARCA,
    }]))
    io.write_table("clases", pd.DataFrame([{
        "clase_id": "CLA-0001", "nombre": "Piano jueves", "instrumento_id": None,
        "espacio_id": None, "dia": "J", "hora_inicio": time(17, 0),
        "hora_fin": time(18, 0), "cupo": None, "activa": True, **MARCA,
    }]))
    io.write_table("clases_alumnos", pd.DataFrame([{
        "clase_id": "CLA-0001", "persona_id": "PER-0001",
        "vigente_desde": None, "vigente_hasta": None, **MARCA,
    }]))
    io.write_table("clases_profesores", pd.DataFrame([{
        "clase_id": "CLA-0001", "persona_id": "PER-0002",
        "rol_en_clase": "titular", **MARCA,
    }]))


# --- Los tres estados --------------------------------------------------


def test_una_hora_sin_fila_es_no_disponible():
    """El tercer estado no se guarda: es la ausencia de fila."""
    sembrar_disponibilidad(bloque("DIS-0001", "PER-0002", "L", (9, 0), (14, 0)))
    assert horarios.estado_en("PER-0002", "L", time(10, 0)) == "disponible"
    assert horarios.estado_en("PER-0002", "L", time(20, 0)) == "no_disponible"
    assert horarios.estado_en("PER-0002", "V", time(10, 0)) == "no_disponible"


def test_lo_bloqueado_le_gana_a_lo_disponible():
    """Ofrecer una hora ocupada manda a alguien a una clase que no existe."""
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "L", (9, 0), (14, 0)),
        bloque("DIS-0002", "PER-0002", "L", (11, 0), (12, 0), estado="bloqueado"),
    )
    assert horarios.estado_en("PER-0002", "L", time(11, 30)) == "bloqueado"
    assert horarios.libre("PER-0002")["L"] == [(9 * 60, 11 * 60), (12 * 60, 14 * 60)]


def test_el_estado_solo_puede_ser_uno_de_tres():
    assert horarios.ESTADOS == ("disponible", "bloqueado", "no_disponible")


def test_la_tabla_solo_guarda_dos_estados():
    """Guardar 'no_disponible' seria tener dos formas de decir lo mismo."""
    from lisart.tables import REGISTRY

    assert REGISTRY.get("disponibilidad").column("estado").choices == (
        "disponible", "bloqueado",
    )


# --- Rangos ------------------------------------------------------------


def test_los_bloques_pegados_se_unen():
    """El formulario da medias horas sueltas; la agenda debe leerse en rangos."""
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "M", (15, 0), (15, 30)),
        bloque("DIS-0002", "PER-0002", "M", (15, 30), (16, 0)),
        bloque("DIS-0003", "PER-0002", "M", (16, 0), (16, 30)),
    )
    agenda = horarios.agenda("PER-0002")
    assert len(agenda) == 1
    assert (agenda.iloc[0].hora_inicio, agenda.iloc[0].hora_fin) == (time(15, 0), time(16, 30))


def test_un_bloque_fuera_de_vigencia_no_cuenta():
    """El horario cambia; cerrar el viejo conserva por que algo estaba donde estaba."""
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "L", (9, 0), (10, 0),
               vigente_hasta=date(2026, 1, 31)),
    )
    assert horarios.estado_en("PER-0002", "L", time(9, 30), date(2026, 1, 15)) == "disponible"
    assert horarios.estado_en("PER-0002", "L", time(9, 30), date(2026, 6, 1)) == "no_disponible"


# --- Reposición --------------------------------------------------------


def test_la_reposicion_cruza_al_profesor_con_el_alumno(escuela):
    """Sin cruzar, se propondrian horas en las que el alumno tampoco puede."""
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (14, 0)),   # profesora
        bloque("DIS-0002", "PER-0001", "V", (12, 0), (13, 0)),  # alumna
    )
    opciones = horarios.opciones_de_reposicion("PER-0001")
    assert len(opciones) == 1
    hueco = opciones[0]
    assert (hueco.dia, hueco.inicio, hueco.fin) == ("V", time(12, 0), time(13, 0))
    assert hueco.profesor.startswith("Rosa")


def test_sin_cruzar_devuelve_todo_el_hueco_del_profesor(escuela):
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (14, 0)),
        bloque("DIS-0002", "PER-0001", "V", (12, 0), (13, 0)),
    )
    opciones = horarios.opciones_de_reposicion("PER-0001", cruzar_con_el_alumno=False)
    assert (opciones[0].inicio, opciones[0].fin) == (time(9, 0), time(14, 0))


def test_lo_que_el_profesor_tiene_ocupado_no_se_ofrece(escuela):
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (14, 0)),
        bloque("DIS-0002", "PER-0002", "V", (12, 0), (13, 0), estado="bloqueado"),
        bloque("DIS-0003", "PER-0001", "V", (9, 0), (14, 0)),
    )
    rangos = [(h.inicio, h.fin) for h in horarios.opciones_de_reposicion("PER-0001")]
    assert rangos == [(time(9, 0), time(12, 0)), (time(13, 0), time(14, 0))]


def test_una_clase_puede_tener_varios_profesores(escuela):
    """Lo dijo la escuela: cada clase puede tener uno o mas."""
    io.upsert("clases_profesores", pd.DataFrame([{
        "clase_id": "CLA-0001", "persona_id": "PER-0003",
        "rol_en_clase": "apoyo", **MARCA,
    }]))
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (10, 0)),
        bloque("DIS-0002", "PER-0003", "S", (11, 0), (12, 0)),
        bloque("DIS-0003", "PER-0001", "V", (9, 0), (10, 0)),
        bloque("DIS-0004", "PER-0001", "S", (11, 0), (12, 0)),
    )
    assert len(horarios.profesores_de("PER-0001")) == 2
    opciones = horarios.opciones_de_reposicion("PER-0001")
    assert {h.profesor_id for h in opciones} == {"PER-0002", "PER-0003"}


def test_los_huecos_muy_cortos_no_se_ofrecen(escuela):
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (9, 20)),
        bloque("DIS-0002", "PER-0001", "V", (9, 0), (9, 20)),
    )
    assert horarios.opciones_de_reposicion("PER-0001", minutos_minimos=30) == []
    assert len(horarios.opciones_de_reposicion("PER-0001", minutos_minimos=15)) == 1


def test_un_alumno_sin_clase_no_tiene_donde_reponer(escuela):
    io.write_table("clases_alumnos", io.empty_frame("clases_alumnos"))
    assert horarios.opciones_de_reposicion("PER-0001") == []


def test_las_opciones_salen_ordenadas_por_dia_y_hora(escuela):
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "S", (10, 0), (11, 0)),
        bloque("DIS-0002", "PER-0002", "L", (10, 0), (11, 0)),
        bloque("DIS-0003", "PER-0001", "S", (10, 0), (11, 0)),
        bloque("DIS-0004", "PER-0001", "L", (10, 0), (11, 0)),
    )
    assert [h.dia for h in horarios.opciones_de_reposicion("PER-0001")] == ["L", "S"]


def test_el_hueco_se_lee_en_castellano(escuela):
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "Mi", (16, 0), (17, 0)),
        bloque("DIS-0002", "PER-0001", "Mi", (16, 0), (17, 0)),
    )
    hueco = horarios.opciones_de_reposicion("PER-0001")[0]
    assert str(hueco).startswith("miércoles 16:00–17:00 con Rosa")
    assert hueco.minutos == 60


# --- Lo que llega del formulario ---------------------------------------


@pytest.mark.parametrize(
    "etiqueta,esperado",
    [
        ("9:00 am", time(9, 0)),
        ("12:00 pm", time(12, 0)),
        ("12:30 pm", time(12, 30)),
        ("1:00 pm", time(13, 0)),
        ("7:30 pm", time(19, 30)),
        ("no es hora", None),
    ],
)
def test_las_horas_del_formulario_pasan_a_24_horas(etiqueta, esperado):
    """El formulario usa 12 horas con am/pm; guardarlo asi se ordena mal."""
    from lisart.procesos.alta_inscripciones import _hora_del_formulario

    assert _hora_del_formulario(etiqueta) == esperado


def test_lo_que_se_escribe_pasa_la_validacion(escuela):
    from lisart.validate import has_errors, validate_all

    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0002", "V", (9, 0), (14, 0)),
        bloque("DIS-0002", "PER-0001", "V", (12, 0), (13, 0)),
    )
    issues = validate_all()
    assert not has_errors(issues), [str(i) for i in issues]


# --- La vista de la semana ---------------------------------------------


def _agenda(*filas):
    return pd.DataFrame(list(filas))


def test_la_ventana_horaria_es_fija_para_poder_comparar():
    """Ajustarla a los datos hacía incomparables dos semanas del mismo horario."""
    from lisart.ui import semana

    apretada = _agenda({"dia": "J", "hora_inicio": time(16, 30),
                        "hora_fin": time(17, 0), "estado": "disponible"})
    assert semana._rango_horario(apretada) == (semana.DESDE_DEFECTO, semana.HASTA_DEFECTO)


def test_la_ventana_se_amplia_si_algo_se_sale_pero_nunca_se_encoge():
    from lisart.ui import semana

    temprana = _agenda({"dia": "L", "hora_inicio": time(6, 0),
                        "hora_fin": time(7, 0), "estado": "disponible"})
    desde, hasta = semana._rango_horario(temprana)
    assert desde == 6
    assert hasta == semana.HASTA_DEFECTO


def test_la_semana_se_dibuja_con_pocos_elementos():
    """Un SVG grande tarda un minuto en pintar: por eso son rangos, no casillas."""
    from lisart.ui import semana

    dibujo = semana.dibujar(_agenda(
        {"dia": "L", "hora_inicio": time(9, 0), "hora_fin": time(14, 0),
         "estado": "disponible"},
        {"dia": "L", "hora_inicio": time(11, 0), "hora_fin": time(12, 0),
         "estado": "bloqueado"},
    ))
    assert dibujo.count("<rect") < 40
    assert 'barra--disponible' in dibujo and 'barra--bloqueado' in dibujo


def test_el_resumen_dice_lo_que_suma_la_semana():
    from lisart.ui import semana

    texto = semana.resumen(_agenda(
        {"dia": "L", "hora_inicio": time(9, 0), "hora_fin": time(14, 0),
         "estado": "disponible"},
        {"dia": "M", "hora_inicio": time(9, 0), "hora_fin": time(10, 0),
         "estado": "bloqueado"},
    ))
    assert "5.0 h disponibles" in texto
    assert "1.0 h bloqueadas" in texto
    assert "en 2 días" in texto


def test_una_semana_vacia_lo_dice_en_vez_de_mentir():
    from lisart.ui import semana

    assert semana.resumen(pd.DataFrame(columns=["dia", "hora_inicio", "hora_fin", "estado"])) == (
        "sin horario registrado"
    )


# --- Lo que se deduce de los alumnos -----------------------------------


def test_las_horas_de_los_alumnos_cuentan_como_ocupadas_del_profesor(escuela):
    """La escuela pidió esta aproximación sabiendo que no es exacta."""
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0001", "J", (17, 0), (18, 0)),  # la alumna de la clase
        bloque("DIS-0002", "PER-0003", "V", (9, 0), (10, 0)),   # alguien que no la toma
    )
    derivado = horarios.bloqueado_por_los_alumnos("CLA-0001")
    assert len(derivado) == 1
    fila = derivado.iloc[0]
    assert (fila.dia, fila.hora_inicio, fila.hora_fin) == ("J", time(17, 0), time(18, 0))
    assert fila.estado == "por_alumnos"


def test_lo_deducido_no_se_guarda_en_la_base(escuela):
    """Es un cálculo, no un hecho: guardarlo quedaría desfasado solo."""
    sembrar_disponibilidad(bloque("DIS-0001", "PER-0001", "J", (17, 0), (18, 0)))
    antes = len(io.read_table("disponibilidad"))
    horarios.bloqueado_por_los_alumnos("CLA-0001")
    assert len(io.read_table("disponibilidad")) == antes
    assert set(io.read_table("disponibilidad")["estado"]) <= {"disponible", "bloqueado"}


def test_las_horas_de_varios_alumnos_se_juntan(escuela):
    io.upsert("alumnos", pd.DataFrame([{
        "persona_id": "PER-0003", "estatus": "inscrito", "fecha_alta": None,
        "fecha_baja": None, "requiere_tutor": False, "programa": None,
        "notas": None, **MARCA,
    }]))
    io.upsert("clases_alumnos", pd.DataFrame([{
        "clase_id": "CLA-0001", "persona_id": "PER-0003",
        "vigente_desde": None, "vigente_hasta": None, **MARCA,
    }]))
    sembrar_disponibilidad(
        bloque("DIS-0001", "PER-0001", "J", (16, 0), (17, 0)),
        bloque("DIS-0002", "PER-0003", "J", (17, 0), (18, 0)),
    )
    derivado = horarios.bloqueado_por_los_alumnos("CLA-0001")
    assert len(derivado) == 1  # contiguos: se unen
    assert (derivado.iloc[0].hora_inicio, derivado.iloc[0].hora_fin) == (time(16, 0), time(18, 0))


def test_una_clase_sin_alumnos_no_ocupa_nada(escuela):
    io.write_table("clases_alumnos", io.empty_frame("clases_alumnos"))
    assert horarios.bloqueado_por_los_alumnos("CLA-0001").empty
