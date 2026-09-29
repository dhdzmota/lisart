"""Pruebas del paso que convierte inscripciones en personas.

Los nombres son inventados. Los casos, no: cada uno salio de algo que aparecio
en los datos reales de la escuela.
"""

import pandas as pd
import pytest

from lisart import io
from lisart.fuentes import jotform
from lisart.procesos import alta_inscripciones as alta


def persona(nombre, paterno="Ruiz", materno="Peña"):
    return {"first": nombre, "middle": paterno, "last": materno}


def envio(
    submission_id,
    *,
    alumno,
    tutor=None,
    emergencia=None,
    recojer1=None,
    edad="10",
    nacimiento_alumno=("2015", "03", "14"),
    nacimiento_tutor=None,
    creado="2026-06-01 10:00:00",
):
    def campo(orden, tipo, answer, **extra):
        return {"name": f"c{orden}", "order": str(orden), "type": tipo, "answer": answer, **extra}

    def fecha(partes):
        anio, mes, dia = partes
        return {"year": anio, "month": mes, "day": dia,
                "datetime": f"{anio}-{mes}-{dia} 00:00:00"}

    answers = {
        "a": campo(15, "control_fullname", alumno),
        "b": campo(16, "control_datetime", fecha(nacimiento_alumno)),
        "c": campo(17, "control_calculation", edad),
        "d": campo(19, "control_phone", {"area": "33", "phone": "11112222"}),
        "e": campo(20, "control_email", "alumno@example.com"),
    }
    if tutor:
        answers["f"] = campo(22, "control_fullname", tutor)
        answers["g"] = campo(25, "control_phone", {"area": "33", "phone": "33334444"})
        if nacimiento_tutor:
            answers["h"] = campo(23, "control_datetime", fecha(nacimiento_tutor))
    if emergencia:
        answers["i"] = campo(32, "control_fullname", emergencia)
        answers["j"] = campo(35, "control_phone", {"area": "33", "phone": "55556666"})
    if recojer1:
        answers["k"] = campo(40, "control_fullname", recojer1)
        answers["l"] = campo(43, "control_phone", {"area": "33", "phone": "77778888"})

    return {
        "id": submission_id,
        "form_id": "form-1",
        "ip": "1.1.1.1",
        "created_at": creado,
        "status": "ACTIVE",
        "answers": answers,
    }


def sembrar(envios):
    """Deja los envios en respuestas_inscripcion, como haria la ingesta."""
    jotform.ingestar(envios=envios, guardar_crudo=False)


# --- Identidad ---------------------------------------------------------


def test_una_persona_mencionada_en_dos_papeles_es_una_sola():
    """El caso mas comun: el tutor tambien es el contacto de emergencia."""
    sembrar([envio("1", alumno=persona("Ana"),
                   tutor=persona("Rosa"), emergencia=persona("Rosa"))])
    alta.procesar()

    personas = io.read_table("personas")
    assert len(personas) == 2  # Ana y Rosa, no tres
    rosas = personas[personas.nombre_normalizado == "rosa ruiz peña"]
    assert len(rosas) == 1


def test_un_tutor_con_dos_hijos_es_una_sola_persona():
    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa")),
        envio("2", alumno=persona("Luis"), tutor=persona("Rosa")),
    ])
    alta.procesar()

    assert len(io.read_table("personas")) == 3  # Ana, Luis, Rosa
    assert len(io.read_table("alumnos")) == 2


def test_el_nombre_se_compara_sin_acentos_ni_mayusculas():
    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("MARÍA", "Vega", "Gómez")),
        envio("2", alumno=persona("Luis"), tutor=persona("maria", "vega", "gomez")),
    ])
    alta.procesar()
    personas = io.read_table("personas")
    assert (personas.nombre_normalizado == "maria vega gomez").sum() == 1


def test_la_enie_si_distingue_personas():
    """Peña y Pena no son el mismo apellido."""
    sembrar([
        envio("1", alumno=persona("Ana", "Ruiz", "Peña")),
        envio("2", alumno=persona("Ana", "Ruiz", "Pena")),
    ])
    alta.procesar()
    assert len(io.read_table("personas")) == 2


def test_un_alumno_puede_ser_tutor_de_su_hermano():
    sembrar([
        envio("1", alumno=persona("Sofia"), edad="22", nacimiento_alumno=("2004", "01", "01")),
        envio("2", alumno=persona("Luis"), tutor=persona("Sofia")),
    ])
    alta.procesar()

    roles = io.read_table("personas_roles")
    personas = io.read_table("personas")
    sofia = personas[personas.nombre_normalizado == "sofia ruiz peña"].iloc[0].persona_id
    assert set(roles[roles.persona_id == sofia].rol) == {"alumno", "tutor"}


def test_no_se_crea_una_relacion_de_alguien_consigo_mismo():
    """Pasa de verdad: hay quien se pone a si mismo de contacto de emergencia."""
    sembrar([envio("1", alumno=persona("Ana"), emergencia=persona("Ana"))])
    alta.procesar()
    assert len(io.read_table("relaciones")) == 0


# --- Fechas de nacimiento en conflicto ---------------------------------


def test_gana_la_fecha_que_la_persona_dio_de_si_misma():
    """En el bloque de tutor la gente captura la fecha del hijo, no la suya."""
    sembrar([
        envio("1", alumno=persona("Rosa"), edad="40", nacimiento_alumno=("1986", "07", "27")),
        envio("2", alumno=persona("Ana"), tutor=persona("Rosa"),
              nacimiento_tutor=("2017", "01", "29")),
    ])
    resultado = alta.procesar()

    personas = io.read_table("personas")
    rosa = personas[personas.nombre_normalizado == "rosa ruiz peña"].iloc[0]
    assert rosa.fecha_nacimiento == pd.Timestamp("1986-07-27").date()
    assert any("Se tomo 1986-07-27" in c for c in resultado.conflictos)


def test_si_no_se_puede_decidir_la_fecha_se_deja_vacia():
    """Mejor un hueco visible que una fecha equivocada corriendo por el sistema."""
    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa"),
              nacimiento_tutor=("1980", "05", "05")),
        envio("2", alumno=persona("Luis"), tutor=persona("Rosa"),
              nacimiento_tutor=("2017", "01", "29")),
    ])
    resultado = alta.procesar()

    personas = io.read_table("personas")
    rosa = personas[personas.nombre_normalizado == "rosa ruiz peña"].iloc[0]
    assert pd.isna(rosa.fecha_nacimiento)
    assert any("VACIA" in c for c in resultado.conflictos)


def test_avisa_de_un_tutor_menor_de_edad():
    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa"),
              nacimiento_tutor=("2017", "01", "29")),
    ])
    resultado = alta.procesar()
    assert any("menores de edad" in a for a in resultado.avisos)


# --- Alumnos y relaciones ----------------------------------------------


def test_un_menor_requiere_tutor_y_un_adulto_no():
    sembrar([
        envio("1", alumno=persona("Ana"), edad="10"),
        envio("2", alumno=persona("Jose"), edad="30"),
    ])
    alta.procesar()

    personas = io.read_table("personas").set_index("nombre_normalizado")
    alumnos = io.read_table("alumnos").set_index("persona_id")
    assert alumnos.loc[personas.loc["ana ruiz peña"].persona_id, "requiere_tutor"]
    assert not alumnos.loc[personas.loc["jose ruiz peña"].persona_id, "requiere_tutor"]


def test_sin_edad_se_asume_que_requiere_tutor():
    """Ante la duda, el lado seguro tratandose de menores."""
    sembrar([envio("1", alumno=persona("Ana"), edad="")])
    alta.procesar()
    assert io.read_table("alumnos").iloc[0].requiere_tutor


def test_cada_papel_produce_su_tipo_de_relacion():
    sembrar([envio("1", alumno=persona("Ana"), tutor=persona("Rosa"),
                   emergencia=persona("Luis"), recojer1=persona("Marta"))])
    alta.procesar()

    relaciones = io.read_table("relaciones")
    assert set(relaciones.tipo) == {"tutor", "emergencia", "autorizado_recoger"}


def test_las_familias_salen_de_compartir_tutor():
    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa")),
        envio("2", alumno=persona("Luis"), tutor=persona("Rosa")),
        envio("3", alumno=persona("Sara"), tutor=persona("Elena")),
    ])
    alta.procesar()

    grupos = alta.familias()
    con_hermanos = grupos[grupos.alumnos > 1]
    assert len(con_hermanos) == 1
    assert con_hermanos.iloc[0].alumnos == 2


def test_queda_el_rastro_de_que_envio_salio_cada_persona():
    sembrar([envio("1", alumno=persona("Ana"), tutor=persona("Rosa"))])
    alta.procesar()

    ids = io.read_table("identificadores_externos")
    assert set(ids.id_externo) == {"1#alumno", "1#tutor"}
    assert set(ids.sistema) == {"jotform"}


# --- Idempotencia ------------------------------------------------------


def test_correrlo_dos_veces_no_duplica_nada():
    envios = [
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa"), emergencia=persona("Luis")),
        envio("2", alumno=persona("Beto"), tutor=persona("Rosa")),
    ]
    sembrar(envios)
    alta.procesar()
    conteos = {t: len(io.read_table(t)) for t in
               ("personas", "personas_roles", "alumnos", "relaciones")}

    segundo = alta.procesar()
    assert segundo.personas_nuevas == 0
    assert segundo.relaciones_nuevas == 0
    assert {t: len(io.read_table(t)) for t in conteos} == conteos


def test_los_identificadores_de_persona_no_cambian_entre_corridas():
    sembrar([envio("1", alumno=persona("Ana"), tutor=persona("Rosa"))])
    alta.procesar()
    antes = dict(zip(io.read_table("personas").nombre_normalizado,
                     io.read_table("personas").persona_id, strict=True))

    sembrar([envio("2", alumno=persona("Beto"))])
    alta.procesar()
    despues = dict(zip(io.read_table("personas").nombre_normalizado,
                       io.read_table("personas").persona_id, strict=True))

    for clave, pid in antes.items():
        assert despues[clave] == pid


def test_un_dato_actualizado_gana_al_viejo():
    sembrar([envio("1", alumno=persona("Ana"), creado="2026-01-01 10:00:00")])
    alta.procesar()
    sembrar([envio("2", alumno=persona("Ana"), creado="2026-07-01 10:00:00")])
    alta.procesar()

    personas = io.read_table("personas")
    assert len(personas) == 1


def test_los_envios_no_activos_se_ignoran():
    envios = [envio("1", alumno=persona("Ana"))]
    envios[0]["status"] = "DELETED"
    sembrar(envios)

    resultado = alta.procesar()
    assert len(io.read_table("personas")) == 0
    assert any("ACTIVE" in a for a in resultado.avisos)


def test_lo_que_se_escribe_pasa_la_validacion():
    from lisart.validate import has_errors, validate_all

    sembrar([
        envio("1", alumno=persona("Ana"), tutor=persona("Rosa"),
              emergencia=persona("Luis"), recojer1=persona("Marta")),
        envio("2", alumno=persona("Beto"), tutor=persona("Rosa")),
    ])
    alta.procesar()

    issues = validate_all()
    assert not has_errors(issues), [str(i) for i in issues]


@pytest.mark.parametrize("tabla", ["personas", "alumnos", "relaciones"])
def test_no_escribe_nada_si_no_hay_inscripciones(tabla):
    alta.procesar()
    assert len(io.read_table(tabla)) == 0
