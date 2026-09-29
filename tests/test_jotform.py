"""Pruebas del conector de Jotform.

Los datos son inventados a proposito: las respuestas reales traen nombres,
domicilios y firmas de menores, y eso no tiene por que estar en el repo.
"""

import json

import pandas as pd
import pytest

from lisart import io
from lisart.fuentes import jotform


def respuesta(orden, tipo, answer, **extra):
    return {"name": f"campo{orden}", "order": str(orden), "type": tipo, "answer": answer, **extra}


def envio(submission_id="500001", *, status="ACTIVE", nombre_alumno="Ana", **cambios):
    """Un envio de Jotform sintetico, con un campo de cada tipo relevante."""
    answers = {
        "1": respuesta(3, "control_fullname",
                       {"first": "Rosa", "middle": "Ruiz", "last": "Peña"}),
        "2": respuesta(5, "control_inline", "MANIFIESTO DE ENTERADO(A) 2026"),
        "3": respuesta(9, "control_checkbox", ["Acepto"]),
        "4": respuesta(12, "control_datetime",
                       {"month": "06", "day": "01", "year": "2026",
                        "hour": "10", "min": "30", "datetime": "2026-06-01 10:30:00"}),
        "5": respuesta(15, "control_fullname",
                       {"first": nombre_alumno, "middle": "Ruiz", "last": "Peña"}),
        "6": respuesta(16, "control_datetime",
                       {"month": "03", "day": "14", "year": "2013",
                        "datetime": "2013-03-14 00:00:00"}),
        "7": respuesta(17, "control_calculation", "13"),
        "8": respuesta(18, "control_address",
                       {"addr_line1": "Calle Falsa 123", "addr_line2": "Int 4",
                        "city": "Guadalajara", "state": "Jalisco", "postal": "44100"}),
        "9": respuesta(19, "control_phone", {"area": "33", "phone": "12345678"}),
        "10": respuesta(20, "control_email", "rosa@example.com"),
        "11": respuesta(28, "control_fileupload", ["https://ejemplo/ine.pdf"]),
        "12": respuesta(54, "control_checkbox", ["Piano", "Guitarra"]),
        "13": respuesta(56, "control_matrix",
                        [["", "x", "", "", "", ""], ["x", "", "", "", "", "x"]],
                        mcolumns="L|M|Mi|J|V|S", mrows="9:00 Am|10:00 Am"),
        "14": respuesta(59, "control_checkbox", []),
    }
    base = {
        "id": submission_id,
        "form_id": "253627726378065",
        "ip": "189.0.0.1",
        "created_at": "2026-06-01 10:31:00",
        "status": status,
        "answers": answers,
    }
    base.update(cambios)
    return base


# --- Aplanado ----------------------------------------------------------


def test_el_nombre_se_abre_en_partes_y_en_texto_junto():
    df, _ = jotform.aplanar([envio()])
    fila = df.iloc[0]
    assert fila["alumno__nombre_completo___nombre"] == "Ana"
    assert fila["alumno__nombre_completo___apellido_paterno"] == "Ruiz"
    assert fila["alumno__nombre_completo___apellido_materno"] == "Peña"
    assert fila["alumno__nombre_completo___txt"] == "Ana Ruiz Peña"


def test_el_texto_se_guarda_como_llego():
    """El notebook hacia .title() sobre todo; aqui no, para no inventar."""
    entrada = envio(nombre_alumno="ANA DE LA O")
    df, _ = jotform.aplanar([entrada])
    assert df.iloc[0]["alumno__nombre_completo___nombre"] == "ANA DE LA O"


def test_domicilio_y_telefono_se_abren_en_columnas():
    fila = jotform.aplanar([envio()])[0].iloc[0]
    assert fila["alumno__domicilio___ciudad"] == "Guadalajara"
    assert fila["alumno__domicilio___codigo_postal"] == "44100"
    assert fila["alumno__telefono___area"] == "33"
    assert fila["alumno__telefono___telefono"] == "12345678"


def test_las_fechas_quedan_como_fecha_y_como_fecha_hora():
    fila = jotform.aplanar([envio()])[0].iloc[0]
    assert fila["alumno__fecha_nacimiento"] == pd.Timestamp("2013-03-14").date()
    assert fila["fechayhora_llenado"] == pd.Timestamp("2026-06-01 10:30:00")


def test_las_casillas_se_vuelven_si_no():
    fila = jotform.aplanar([envio()])[0].iloc[0]
    assert bool(fila["acepta_reglamento"]) is True
    assert bool(fila["aviso_de_privacidad"]) is False  # lista vacia = no marco


def test_las_opciones_multiples_se_guardan_separadas_por_barra():
    assert jotform.aplanar([envio()])[0].iloc[0]["instrumentos"] == "Piano|Guitarra"


def test_el_horario_se_vuelve_una_columna_por_dia():
    fila = jotform.aplanar([envio()])[0].iloc[0]
    assert fila["horario___L"] == "10:00 Am"
    assert fila["horario___M"] == "9:00 Am"
    assert fila["horario___S"] == "10:00 Am"
    assert fila["horario___J"] is None


def test_un_campo_ausente_no_rompe_nada():
    entrada = envio()
    del entrada["answers"]["9"]  # se va el telefono
    df, _ = jotform.aplanar([entrada])
    assert pd.isna(df.iloc[0]["alumno__telefono___telefono"])


def test_la_tabla_aplanada_cuadra_con_el_esquema():
    df, _ = jotform.aplanar([envio()])
    esperadas = [c.name for c in jotform.columnas_tabla()]
    assert list(df.columns) == esperadas


# --- Deteccion de que el formulario cambio -----------------------------


def test_avisa_si_un_campo_dejo_de_llegar():
    avisos = jotform.revisar_mapeo([envio()])
    assert any("no llegaron" in a for a in avisos)


def test_avisa_si_los_ordenes_se_recorrieron():
    """El error silencioso mas peligroso: los datos caen en otra columna."""
    entrada = envio()
    entrada["answers"]["5"]["type"] = "control_textbox"  # 15 deberia ser fullname
    avisos = jotform.revisar_mapeo([entrada])
    assert any("recorrido" in a for a in avisos)


# --- Ingesta incremental -----------------------------------------------


def test_la_primera_corrida_agrega_todo():
    resultado = jotform.ingestar(envios=[envio("1"), envio("2")], guardar_crudo=False)
    assert resultado.nuevos == 2
    assert resultado.escribio
    assert len(io.read_table(jotform.TABLA)) == 2


def test_si_no_hay_nada_nuevo_no_se_toca_el_archivo():
    envios = [envio("1"), envio("2")]
    jotform.ingestar(envios=envios, guardar_crudo=False)

    ruta = io._resolve(jotform.TABLA).path
    antes = ruta.read_bytes()

    resultado = jotform.ingestar(envios=envios, guardar_crudo=False)
    assert resultado.nuevos == 0
    assert not resultado.escribio
    assert ruta.read_bytes() == antes


def test_solo_se_agregan_los_envios_nuevos():
    jotform.ingestar(envios=[envio("1")], guardar_crudo=False)
    resultado = jotform.ingestar(envios=[envio("1"), envio("2")], guardar_crudo=False)

    assert resultado.nuevos == 1
    tabla = io.read_table(jotform.TABLA)
    assert set(tabla["form__submission_id"]) == {"1", "2"}


def test_un_envio_editado_se_reporta_pero_no_se_pisa():
    jotform.ingestar(envios=[envio("1", nombre_alumno="Ana")], guardar_crudo=False)
    resultado = jotform.ingestar(
        envios=[envio("1", nombre_alumno="Ana Maria")], guardar_crudo=False
    )

    assert resultado.cambiados == 1
    assert not resultado.escribio
    tabla = io.read_table(jotform.TABLA)
    assert tabla.iloc[0]["alumno__nombre_completo___nombre"] == "Ana"


def test_con_actualizar_si_se_pisa():
    jotform.ingestar(envios=[envio("1", nombre_alumno="Ana")], guardar_crudo=False)
    resultado = jotform.ingestar(
        envios=[envio("1", nombre_alumno="Ana Maria")], guardar_crudo=False, actualizar=True
    )

    assert resultado.actualizados == 1
    tabla = io.read_table(jotform.TABLA)
    assert len(tabla) == 1
    assert tabla.iloc[0]["alumno__nombre_completo___nombre"] == "Ana Maria"


def test_un_borrado_en_jotform_se_nota_por_el_status():
    jotform.ingestar(envios=[envio("1")], guardar_crudo=False)
    resultado = jotform.ingestar(envios=[envio("1", status="DELETED")], guardar_crudo=False)
    assert resultado.cambiados == 1


def test_lo_que_se_guarda_pasa_la_validacion():
    from lisart.validate import has_errors, validate_table

    jotform.ingestar(envios=[envio("1"), envio("2")], guardar_crudo=False)
    issues = validate_table(jotform.TABLA)
    assert not has_errors(issues), [str(i) for i in issues]


# --- Descarga ----------------------------------------------------------


class SesionFalsa:
    """Simula la API sin salir a internet."""

    def __init__(self, paginas):
        self.paginas = paginas
        self.offsets = []

    def get(self, url, params, timeout):
        self.offsets.append(params["offset"])
        contenido = self.paginas.pop(0) if self.paginas else []

        class R:
            @staticmethod
            def raise_for_status():
                return None

            @staticmethod
            def json():
                return {"content": contenido}

        return R()


def test_la_descarga_pagina_hasta_acabarse():
    sesion = SesionFalsa([[envio(str(i)) for i in range(3)], [envio("99")]])
    envios = jotform.descargar("llave", "form", limite_por_pagina=3, sesion=sesion)
    assert len(envios) == 4
    assert sesion.offsets == [0, 3]


def test_la_copia_cruda_se_guarda_completa(tmp_path):
    ruta = jotform.guardar_raw([envio("1")], "form-1", carpeta=tmp_path)
    assert ruta.exists()
    guardado = json.loads(ruta.read_text(encoding="utf-8"))
    assert guardado[0]["id"] == "1"


def test_pide_la_llave_con_un_mensaje_util(monkeypatch, tmp_path):
    monkeypatch.delenv("JOTFORM_API_KEY", raising=False)
    monkeypatch.setattr("lisart.config.ENV_PATH", tmp_path / "no-existe.env")
    with pytest.raises(RuntimeError, match=r"\.env"):
        jotform.ingestar()
