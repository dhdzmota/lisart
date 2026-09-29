import pandas as pd

from lisart import io
from lisart.validate import has_errors, validate_all, validate_table

CAB_PERSONAS = (
    "persona_id,nombre,apellido_paterno,apellido_materno,nombre_normalizado,"
    "fecha_nacimiento,telefono,correo,domicilio,activo,creado_en,actualizado_en,fuente\n"
)


def escribir(tabla, texto, encoding="utf-8"):
    tbl = io._resolve(tabla)
    tbl.path.write_text(texto, encoding=encoding)


def reglas(issues):
    return {i.rule for i in issues}


def test_tabla_vacia_es_valida():
    io.write_table("personas", io.empty_frame("personas"))
    assert validate_table("personas") == []


def test_archivo_faltante_es_solo_aviso():
    issues = validate_table("personas")
    assert reglas(issues) == {"archivo_faltante"}
    assert not has_errors(issues)


def test_detecta_faltante_obligatorio():
    escribir("personas", CAB_PERSONAS + "PER-0001,,,,maria,,,,,true,,,manual\n")
    issues = validate_table("personas")
    assert "requerido" in reglas(issues)
    assert any(i.column == "nombre" for i in issues)


def test_detecta_llave_primaria_repetida():
    escribir(
        "personas",
        CAB_PERSONAS
        + "PER-0001,Maria,,,maria,,,,,true,,,manual\n"
        + "PER-0001,Jose,,,jose,,,,,true,,,manual\n",
    )
    assert "llave_primaria" in reglas(validate_table("personas"))


def test_detecta_valor_fuera_de_catalogo():
    escribir("personas", CAB_PERSONAS + "PER-0001,Maria,,,maria,,,,,true,,,facebook\n")
    issues = validate_table("personas")
    assert "catalogo" in reglas(issues)
    assert any(i.column == "fuente" for i in issues)


def test_detecta_fecha_invalida_y_apunta_a_la_linea():
    escribir(
        "personas",
        CAB_PERSONAS + "PER-0001,Maria,,,maria,04/03/2012,,,,true,,,manual\n",
    )
    issues = [i for i in validate_table("personas") if i.rule == "tipo_invalido"]
    assert issues and issues[0].column == "fecha_nacimiento"
    assert issues[0].rows == [2]  # linea 2 del archivo (la 1 es el encabezado)


def test_detecta_columna_desconocida_como_aviso():
    escribir(
        "personas",
        CAB_PERSONAS.rstrip("\n")
        + ",apodo\nPER-0001,Maria,,,maria,,,,,true,"
        + "2026-08-08 10:00:00,2026-08-08 10:00:00,manual,Mari\n",
    )
    issues = validate_table("personas")
    assert "columna_desconocida" in reglas(issues)
    assert not has_errors(issues)


def test_detecta_referencia_a_alumno_inexistente():
    """El caso que un CSV nunca detecta solo: un vinculo que apunta al vacio."""
    io.write_table("personas", io.empty_frame("personas"))
    io.write_table("alumnos", io.empty_frame("alumnos"))
    escribir(
        "relaciones",
        "relacion_id,alumno_persona_id,relacionado_persona_id,tipo,parentesco,vigente,"
        "creado_en,actualizado_en,fuente\n"
        "REL-0001,PER-9999,PER-8888,tutor,madre,true,,,manual\n",
    )
    issues = [i for i in validate_all() if i.table == "relaciones" and i.rule == "referencia"]
    assert {i.column for i in issues} == {"alumno_persona_id", "relacionado_persona_id"}


def test_validate_all_pasa_con_datos_coherentes():
    from lisart.ids import ahora

    audit = {"creado_en": ahora(), "actualizado_en": ahora(), "fuente": "manual"}
    io.write_table(
        "personas",
        pd.DataFrame(
            [
                {
                    "persona_id": "PER-0001", "nombre": "Maria", "apellido_paterno": "H",
                    "apellido_materno": None, "nombre_normalizado": "maria h",
                    "fecha_nacimiento": None, "telefono": None, "correo": None,
                    "domicilio": None, "activo": True, **audit,
                },
                {
                    "persona_id": "PER-0002", "nombre": "Sofia", "apellido_paterno": "H",
                    "apellido_materno": None, "nombre_normalizado": "sofia h",
                    "fecha_nacimiento": None, "telefono": None, "correo": None,
                    "domicilio": None, "activo": True, **audit,
                },
            ]
        ),
    )
    io.write_table(
        "alumnos",
        pd.DataFrame(
            [{
                "persona_id": "PER-0001", "estatus": "activo", "fecha_alta": None,
                "fecha_baja": None, "requiere_tutor": True, "programa": None,
                "notas": None, **audit,
            }]
        ),
    )
    io.write_table(
        "relaciones",
        pd.DataFrame(
            [{
                "relacion_id": "REL-0001", "alumno_persona_id": "PER-0001",
                "relacionado_persona_id": "PER-0002", "tipo": "paga_por",
                "parentesco": "hermana", "vigente": True, **audit,
            }]
        ),
    )
    otras = ("personas_roles", "identificadores_externos", "espacios", "instrumentos", "conceptos")
    for tabla in otras:
        io.write_table(tabla, io.empty_frame(tabla))

    issues = validate_all()
    assert not has_errors(issues), [str(i) for i in issues]
