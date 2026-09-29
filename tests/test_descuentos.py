"""Pruebas del archivo de descuentos por alumno.

Es la única tabla que se edita a mano, así que lo que hay que probar no es la
aritmética: es que **el archivo aguante lo que una persona le escriba**. Un
nombre mal escrito no se corrige adivinando, un descuento repetido no se cobra
dos veces, y un alumno que ya no está no se lleva consigo la razón por la que
tenía beca.
"""

import pandas as pd
import pytest

from lisart import io
from lisart.ids import ahora
from lisart.procesos import descuentos as desc
from lisart.procesos import proyeccion as proy

MARCA = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}


def persona(persona_id, nombre, apellido="Ruiz"):
    return {
        "persona_id": persona_id, "nombre": nombre, "apellido_paterno": apellido,
        "apellido_materno": None, "nombre_normalizado": f"{nombre.lower()} {apellido.lower()}",
        "fecha_nacimiento": None, "telefono": None, "correo": None,
        "domicilio": None, "activo": True, **MARCA,
    }


def alumno(persona_id, estatus="inscrito", programa="Somos música (Adulto) Esencial"):
    return {
        "persona_id": persona_id, "estatus": estatus, "fecha_alta": None,
        "fecha_baja": None, "requiere_tutor": False, "programa": programa,
        "notas": None, **MARCA,
    }


def catalogo(descuento_id, nombre, valor):
    return {
        "descuento_id": descuento_id, "nombre": nombre, "descripcion": None,
        "valor_porcentual": valor, **MARCA,
    }


def renglon(**campos):
    """Un renglón como el que dejaría una persona editando el CSV."""
    base = dict.fromkeys(
        ("alumno_descuento_id", "persona_id", "alumno", "descuento",
         "descuento_id", "porcentaje", "notas"), None
    )
    return {**base, **MARCA, **campos}


@pytest.fixture
def escuela():
    io.write_table("personas", pd.DataFrame([
        persona("PER-0001", "Ana"), persona("PER-0002", "Beto"), persona("PER-0003", "Cami"),
    ]))
    io.write_table("alumnos", pd.DataFrame([
        alumno("PER-0001"), alumno("PER-0002"), alumno("PER-0003"),
    ]))
    io.write_table("descuentos", pd.DataFrame([
        catalogo("descuento_001", "No", 0.0),
        catalogo("descuento_002", "Familiar", 0.05),
        catalogo("descuento_003", "Beca Completa", 100.0),
        catalogo("descuento_006", "Círculo Nuclear A", 0.10),
    ]))


# --- Las unidades del catálogo -----------------------------------------


def test_traduce_las_dos_unidades_del_catalogo():
    """0.05 y 100.00 viven en la misma columna del Excel y significan 5% y 100%."""
    assert desc.porcentaje_de_catalogo(0.05) == 5.0
    assert desc.porcentaje_de_catalogo(0.15) == 15.0
    assert desc.porcentaje_de_catalogo(100.0) == 100.0
    assert desc.porcentaje_de_catalogo(None) is None


# --- El archivo se mantiene solo ---------------------------------------


def test_lista_a_todos_los_alumnos_inscritos(escuela):
    """El archivo no sirve si hay que crear el renglón antes de poder editarlo."""
    reporte = desc.refrescar()
    tabla = io.read_table(desc.TABLA)
    assert reporte.escrito
    assert set(tabla["persona_id"]) == {"PER-0001", "PER-0002", "PER-0003"}
    assert tabla["descuento"].isna().all()
    assert tabla["alumno_descuento_id"].str.startswith("ALD-").all()
    assert list(tabla["alumno"]) == ["Ana Ruiz", "Beto Ruiz", "Cami Ruiz"]


def test_el_de_prueba_no_se_repite_al_correrlo_dos_veces(escuela):
    desc.refrescar()
    primero = io.read_table(desc.TABLA)["alumno_descuento_id"].tolist()
    desc.refrescar()
    assert io.read_table(desc.TABLA)["alumno_descuento_id"].tolist() == primero


def test_escribir_el_nombre_basta_para_dar_de_alta_un_descuento(escuela):
    desc.refrescar()
    tabla = io.read_table(desc.TABLA)
    tabla.loc[tabla["persona_id"] == "PER-0002", "descuento"] = "familiar"  # como lo escriben
    io.write_table(desc.TABLA, tabla)

    reporte = desc.refrescar()
    assert not reporte.problemas
    fila = io.read_table(desc.TABLA).set_index("persona_id").loc["PER-0002"]
    assert fila["descuento"] == "Familiar"        # se normaliza al texto del catálogo
    assert fila["descuento_id"] == "descuento_002"
    assert fila["porcentaje"] == 5.0
    assert reporte.con_descuento == 1


def test_un_alumno_nuevo_aparece_sin_tocar_a_los_demas(escuela):
    desc.refrescar()
    tabla = io.read_table(desc.TABLA)
    tabla.loc[tabla["persona_id"] == "PER-0001", "descuento"] = "Beca Completa"
    io.write_table(desc.TABLA, tabla)

    io.upsert("personas", pd.DataFrame([persona("PER-0004", "Dani")]))
    io.upsert("alumnos", pd.DataFrame([alumno("PER-0004")]))
    reporte = desc.refrescar()

    assert reporte.agregados == ["PER-0004"]
    tabla = io.read_table(desc.TABLA).set_index("persona_id")
    assert tabla.loc["PER-0001", "porcentaje"] == 100.0
    assert pd.isna(tabla.loc["PER-0004", "descuento"])


def test_los_que_tienen_descuento_quedan_arriba(escuela):
    """Se abre el archivo y lo primero que se ve es a quién se le está descontando."""
    desc.refrescar()
    tabla = io.read_table(desc.TABLA)
    tabla.loc[tabla["persona_id"] == "PER-0003", "descuento"] = "Familiar"
    io.write_table(desc.TABLA, tabla)
    desc.refrescar()

    guardado = io.read_table(desc.TABLA)
    assert guardado.iloc[0]["persona_id"] == "PER-0003"
    assert guardado.iloc[1:]["descuento"].isna().all()


# --- Lo que no se corrige adivinando -----------------------------------


def test_un_descuento_que_no_existe_no_se_da_de_alta_solo(escuela):
    """Regla de la casa: los catálogos no se llenan desde el código."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001",
                descuento="Descuento del jefe"),
    ]))
    reporte = desc.refrescar()

    assert not reporte.escrito
    assert any("no está en el catálogo" in p for p in reporte.problemas)
    # El archivo se queda como estaba, para poder corregirlo ahí mismo.
    assert io.read_table(desc.TABLA).iloc[0]["descuento"] == "Descuento del jefe"


def test_el_mismo_descuento_dos_veces_es_un_error(escuela):
    """Se cobraría doble, y nadie lo notaría revisando el total."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001", descuento="Familiar"),
        renglon(alumno_descuento_id="ALD-0002", persona_id="PER-0001", descuento="Familiar"),
    ]))
    reporte = desc.refrescar()
    assert not reporte.escrito
    assert any("ya tiene" in p for p in reporte.problemas)


def test_un_porcentaje_fuera_de_rango_no_pasa(escuela):
    """0.05 en la celda querría decir 0.05%, no 5%. Se atrapa la unidad equivocada."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001",
                descuento="Familiar", porcentaje=150.0),
    ]))
    reporte = desc.refrescar()
    assert not reporte.escrito
    assert any("en puntos" in p for p in reporte.problemas)


def test_la_celda_manda_sobre_el_catalogo_pero_lo_avisa(escuela):
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001",
                descuento="Familiar", porcentaje=7.0, notas="pactado con dirección"),
    ]))
    reporte = desc.refrescar()
    assert reporte.escrito
    assert io.read_table(desc.TABLA).iloc[0]["porcentaje"] == 7.0
    assert any("en vez del" in a for a in reporte.avisos)


def test_se_puede_agregar_un_renglon_con_solo_el_nombre(escuela):
    """Quien edita en Excel duplica un renglón; no tiene por qué inventar un ID."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno="Cami Ruiz", descuento="Familiar"),
    ]))
    reporte = desc.refrescar()
    assert reporte.escrito
    fila = io.read_table(desc.TABLA).set_index("persona_id").loc["PER-0003"]
    assert fila["alumno_descuento_id"] == "ALD-0001"
    assert fila["descuento"] == "Familiar"


def test_un_nombre_ambiguo_se_pregunta_en_vez_de_elegir(escuela):
    io.upsert("personas", pd.DataFrame([persona("PER-0004", "Ana")]))
    io.upsert("alumnos", pd.DataFrame([alumno("PER-0004")]))
    io.write_table(desc.TABLA, pd.DataFrame([renglon(alumno="Ana Ruiz", descuento="Familiar")]))

    reporte = desc.refrescar()
    assert not reporte.escrito
    assert any("corresponde a 2 alumnos" in p for p in reporte.problemas)


def test_el_no_del_catalogo_se_trata_como_sin_descuento(escuela):
    """La escuela escribe 'No' en su Excel; no es un descuento del 0%."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001", descuento="No"),
    ]))
    desc.refrescar()
    assert io.read_table(desc.TABLA)["descuento"].isna().all()


# --- Alumnos que se van ------------------------------------------------


def test_un_alumno_de_baja_sin_descuento_sale_del_archivo(escuela):
    desc.refrescar()
    io.upsert("alumnos", pd.DataFrame([alumno("PER-0002", estatus="baja")]))
    reporte = desc.refrescar()

    assert reporte.retirados == ["PER-0002"]
    assert "PER-0002" not in set(io.read_table(desc.TABLA)["persona_id"])


def test_un_alumno_de_baja_con_beca_conserva_su_renglon(escuela):
    """Perder por qué alguien tenía beca es peor que cargar un renglón de más."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0002",
                descuento="Beca Completa", notas="hermana de una maestra"),
    ]))
    io.upsert("alumnos", pd.DataFrame([alumno("PER-0002", estatus="baja")]))
    reporte = desc.refrescar()

    assert reporte.conservados == ["PER-0002"]
    fila = io.read_table(desc.TABLA).set_index("persona_id").loc["PER-0002"]
    assert fila["notas"] == "hermana de una maestra"


def test_el_renglon_vacio_de_quien_ya_tiene_descuento_se_quita(escuela):
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001"),
        renglon(alumno_descuento_id="ALD-0002", persona_id="PER-0001", descuento="Familiar"),
    ]))
    desc.refrescar()
    tabla = io.read_table(desc.TABLA)
    assert len(tabla[tabla["persona_id"] == "PER-0001"]) == 1


# --- Varios descuentos y el tope ---------------------------------------


def test_dos_descuentos_del_mismo_alumno_se_suman(escuela):
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001", descuento="Familiar"),
        renglon(alumno_descuento_id="ALD-0002", persona_id="PER-0001",
                descuento="Círculo Nuclear A"),
    ]))
    desc.refrescar()
    resultado = desc.por_alumno()["PER-0001"]
    assert resultado["porcentaje"] == 15.0
    assert resultado["descuentos"] == ["Círculo Nuclear A", "Familiar"]


def test_la_suma_no_pasa_del_cien_por_ciento(escuela):
    """Más del 100% sería la escuela pagándole al alumno."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001", descuento="Beca Completa"),
        renglon(alumno_descuento_id="ALD-0002", persona_id="PER-0001", descuento="Familiar"),
    ]))
    reporte = desc.refrescar()
    assert desc.por_alumno()["PER-0001"]["porcentaje"] == 100.0
    assert any("no paga" in a for a in reporte.avisos)


# --- Cómo lo usa la proyección -----------------------------------------


def test_la_proyeccion_aplica_el_descuento(escuela):
    io.write_table("programas", pd.DataFrame([{
        "programa_id": "PDA_001", "modalidad": "presencial", "nombre": "Somos Música",
        "categoria": None, "caracteristica": None, "arquetipo": None,
        "descripcion": None, "precio": 1000.0, "activo": True, **MARCA,
    }]))
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-0001", descuento="Familiar"),
    ]))
    desc.refrescar()

    resultado = proy.calcular()
    assert resultado.total_lista == 3000.0
    assert resultado.total_mensual == 2950.0     # a Ana se le descuenta el 5% de 1000
    assert resultado.total_descuentos == 50.0
    assert resultado.alumnos_con_descuento == 1
    assert "descuentos" in resultado.resumen()

    fila = resultado.detalle.set_index("persona_id").loc["PER-0001"]
    assert fila["precio_lista"] == 1000.0
    assert fila["descuento"] == "Familiar"
    assert fila["precio"] == 950.0

    reparto = proy.por_programa(resultado)
    assert reparto["subtotal"].sum() == resultado.total_mensual


def test_revisar_no_escribe_nada(escuela):
    reporte = desc.refrescar(escribir=False)
    assert not reporte.escrito
    assert reporte.filas == 3
    assert io.read_table(desc.TABLA).empty


def test_una_clave_que_no_es_de_ningun_alumno_se_reporta(escuela):
    """Un descuento sobre alguien que no está en la escuela no se cobra a nadie."""
    io.write_table(desc.TABLA, pd.DataFrame([
        renglon(alumno_descuento_id="ALD-0001", persona_id="PER-9999", descuento="Familiar"),
    ]))
    reporte = desc.refrescar()
    assert not reporte.escrito
    assert any("no es ningún alumno" in p for p in reporte.problemas)
