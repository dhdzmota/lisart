import pandas as pd
import pytest

from lisart import io
from lisart.ids import ahora
from lisart.schema import Column, Table


def persona(persona_id="PER-0001", **kwargs):
    fila = {
        "persona_id": persona_id,
        "nombre": "Maria",
        "apellido_paterno": "Hernandez",
        "apellido_materno": "Lopez",
        "nombre_normalizado": "maria hernandez lopez",
        "fecha_nacimiento": pd.Timestamp("2012-03-04").date(),
        "telefono": "+525512345678",
        "correo": "maria@example.com",
        "domicilio": "Calle 1",
        "activo": True,
        "creado_en": ahora(),
        "actualizado_en": ahora(),
        "fuente": "manual",
    }
    fila.update(kwargs)
    return fila


def test_tabla_inexistente_devuelve_vacia_bien_formada():
    df = io.read_table("personas")
    assert len(df) == 0
    assert list(df.columns) == io._resolve("personas").column_names


def test_ida_y_vuelta_conserva_tipos_y_valores():
    original = pd.DataFrame([persona()])
    io.write_table("personas", original)

    leido = io.read_table("personas")
    assert len(leido) == 1
    fila = leido.iloc[0]
    assert fila["persona_id"] == "PER-0001"
    assert fila["activo"] is True or fila["activo"] == True  # noqa: E712
    assert fila["fecha_nacimiento"] == pd.Timestamp("2012-03-04").date()
    assert str(leido["persona_id"].dtype) == "string"
    assert str(leido["activo"].dtype) == "boolean"


def test_el_telefono_no_se_vuelve_numero():
    """El bug clasico de los CSV: un ID o telefono leido como numero pierde
    ceros a la izquierda y se vuelve 5.5e9."""
    io.write_table("personas", pd.DataFrame([persona(telefono="+525512345678")]))
    leido = io.read_table("personas")
    assert leido.loc[0, "telefono"] == "+525512345678"


def test_texto_NA_no_se_confunde_con_vacio():
    io.write_table("personas", pd.DataFrame([persona(apellido_materno="NA")]))
    leido = io.read_table("personas")
    assert leido.loc[0, "apellido_materno"] == "NA"


def test_espacios_de_sobra_se_recortan_al_leer():
    tbl = io._resolve("personas")
    tbl.path.write_text(
        "persona_id,nombre,apellido_paterno,apellido_materno,nombre_normalizado,"
        "fecha_nacimiento,telefono,correo,domicilio,activo,creado_en,actualizado_en,fuente\n"
        "PER-0001,  Maria  ,Hernandez,,maria,,,,,true,,,manual\n",
        encoding="utf-8",
    )
    assert io.read_table("personas").loc[0, "nombre"] == "Maria"


def test_lee_booleanos_de_excel_en_espanol():
    tbl = io._resolve("espacios")
    tbl.path.write_text(
        "espacio_id,nombre,tipo,piso,agendable,capacidad,equipamiento,notas,activo\n"
        "AULA-A,Aula A,aula,planta_baja,VERDADERO,8,Piano,,VERDADERO\n",
        encoding="utf-8-sig",
    )
    assert io.read_table("espacios").loc[0, "activo"]


def test_valor_invalido_truena_en_modo_estricto():
    tbl = io._resolve("espacios")
    tbl.path.write_text(
        "espacio_id,nombre,tipo,piso,agendable,capacidad,equipamiento,notas,activo\n"
        "AULA-A,Aula A,aula,planta_baja,true,ocho,Piano,,true\n",
        encoding="utf-8-sig",
    )
    with pytest.raises(io.DataError, match="capacidad"):
        io.read_table("espacios")
    # Sin strict devuelve el dato malo como nulo, para poder inspeccionarlo.
    assert pd.isna(io.read_table("espacios", strict=False).loc[0, "capacidad"])


def test_no_se_escribe_una_tabla_con_errores():
    mala = pd.DataFrame([persona(nombre=None)])  # nombre es obligatorio
    with pytest.raises(io.DataError, match="nombre"):
        io.write_table("personas", mala)
    assert not io._resolve("personas").path.exists()


def test_las_filas_se_guardan_ordenadas():
    io.write_table("personas", pd.DataFrame([persona("PER-0003"), persona("PER-0001")]))
    contenido = io._resolve("personas").path.read_text(encoding="utf-8")
    assert contenido.index("PER-0001") < contenido.index("PER-0003")


def test_upsert_actualiza_en_lugar_de_duplicar():
    io.write_table("personas", pd.DataFrame([persona()]))
    io.upsert("personas", pd.DataFrame([persona(nombre="Mariana")]))

    leido = io.read_table("personas")
    assert len(leido) == 1
    assert leido.loc[0, "nombre"] == "Mariana"


def test_las_tablas_editadas_a_mano_llevan_BOM_para_excel():
    io.write_table("espacios", io.empty_frame("espacios"))
    crudo = io._resolve("espacios").path.read_bytes()
    assert crudo.startswith(b"\xef\xbb\xbf")

    io.write_table("personas", io.empty_frame("personas"))
    assert not io._resolve("personas").path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_la_escritura_atomica_no_deja_basura():
    io.write_table("personas", pd.DataFrame([persona()]))
    temporales = list(io._resolve("personas").path.parent.glob(".*tmp"))
    assert temporales == []


def test_el_esquema_rechaza_definiciones_incoherentes():
    with pytest.raises(ValueError, match="llave primaria"):
        Table(
            name="mala",
            layer="master",
            ownership="managed",
            primary_key=("no_existe",),
            columns=(Column("id", "string"),),
        )
