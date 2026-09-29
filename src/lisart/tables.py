"""El modelo de datos de Lisart: UNA sola fuente de verdad.

Este archivo es el centro del proyecto. De aqui salen la validacion, la
documentacion (`lisart docs`) y el formato de los CSV. Si una tabla no esta
aqui, para el sistema no existe.

Que hay hoy (el esqueleto):

    personas ................. la columna vertebral: una fila por ser humano
    personas_roles ........... que es cada quien (alumno, profesor, tutor...)
    alumnos .................. lo que solo aplica a un alumno
    alumnos_instrumentos ..... que estudia cada alumno
    disponibilidad ........... cuando puede cada persona (semana tipo)
    clases ................... que dia y a que hora es cada clase
    clases_profesores ........ quien da cada clase (uno o mas)
    clases_alumnos ........... quien la toma
    relaciones ............... quien es de quien (tutor, quien recoge, quien paga)
    identificadores_externos . el mismo humano en Kydemy / Jotform / WhatsApp
    respuestas_inscripcion ... lo que llega de Jotform, aplanado (capa interim)
    espacios ................. aulas, auditorio, bodega, recepcion, cocina
    instrumentos ............. catalogo de instrumentos
    conceptos ................ catalogo de cobros y sus montos
    programas ................ programas de aprendizaje y su precio mensual
    descuentos ............... descuentos que reconoce la escuela
    alumnos_descuentos ....... a que alumno se le aplica cual (se edita a mano)

Que sigue (cuando se elija la primera rebanada de negocio):

    inscripciones, clases, pagos, proyeccion_pagos,
    plantillas_mensajes, envios, disponibilidad

Dos decisiones que conviene entender antes de agregar tablas:

1. Una persona es una persona. Un profesor que ademas es tutor de su hija es
   UNA fila en `personas` con dos roles, no dos personas. Duplicar humanos es
   lo que rompe despues la conciliacion de pagos.

2. Las tablas que extienden a `personas` (como `alumnos`) usan `persona_id`
   como llave primaria. No inventamos un `alumno_id` aparte: dos llaves para
   la misma persona es garantia de que un dia dejan de coincidir.
"""

from __future__ import annotations

from lisart.fuentes import jotform
from lisart.schema import Column, ForeignKey, Registry, Table

REGISTRY = Registry()


def _auditoria() -> tuple[Column, ...]:
    """Columnas de rastro que llevan todas las tablas que escribe el codigo.

    Sin esto, cuando un dato se ve raro no hay forma de saber de donde salio.
    """
    return (
        Column("creado_en", "datetime", "Cuando se creo la fila."),
        Column("actualizado_en", "datetime", "Ultima modificacion de la fila."),
        Column(
            "fuente",
            "string",
            "De donde salio el dato.",
            choices=("jotform", "kydemy", "whatsapp", "manual", "migracion", "demo"),
        ),
    )


# --- Columna vertebral -------------------------------------------------

PERSONAS = REGISTRY.add(
    Table(
        name="personas",
        layer="master",
        ownership="managed",
        description=(
            "Una fila por ser humano relacionado con la escuela, sin importar "
            "su rol. Alumnos, tutores, profesores y empleados viven todos aqui."
        ),
        primary_key=("persona_id",),
        sort_by=("persona_id",),
        columns=(
            Column("persona_id", "string", "Identificador estable, formato PER-0001.", unique=True),
            Column("nombre", "string", "Nombre(s) de pila."),
            Column("apellido_paterno", "string", "Apellido paterno.", required=False),
            Column("apellido_materno", "string", "Apellido materno.", required=False),
            Column(
                "nombre_normalizado",
                "string",
                "Nombre completo sin acentos, en minusculas. Se calcula solo "
                "(ids.normalizar_nombre) y sirve para cruzar fuentes que "
                "escriben el mismo nombre distinto.",
            ),
            Column("fecha_nacimiento", "date", "Fecha de nacimiento.", required=False),
            Column(
                "telefono",
                "string",
                "Telefono en formato E.164, ej. +5215512345678. Es la llave "
                "natural para WhatsApp.",
                required=False,
            ),
            Column("correo", "string", "Correo electronico.", required=False),
            Column("domicilio", "string", "Domicilio en una sola linea.", required=False),
            Column("activo", "bool", "Si sigue vinculada a la escuela."),
            *_auditoria(),
        ),
    )
)

PERSONAS_ROLES = REGISTRY.add(
    Table(
        name="personas_roles",
        layer="master",
        ownership="managed",
        description=(
            "Que papel juega cada persona. Una persona puede tener varios "
            "roles a la vez y puede cambiarlos con el tiempo."
        ),
        primary_key=("persona_id", "rol"),
        columns=(
            Column("persona_id", "string", "Persona a la que aplica el rol."),
            Column(
                "rol",
                "string",
                "Papel que juega en la escuela.",
                choices=("alumno", "tutor", "profesor", "empleado", "director", "proveedor"),
            ),
            Column("vigente_desde", "date", "Desde cuando tiene el rol.", required=False),
            Column(
                "vigente_hasta",
                "date",
                "Hasta cuando lo tuvo. Vacio = sigue vigente.",
                required=False,
            ),
            *_auditoria(),
        ),
        foreign_keys=(ForeignKey("persona_id", "personas", "persona_id"),),
    )
)

ALUMNOS = REGISTRY.add(
    Table(
        name="alumnos",
        layer="master",
        ownership="managed",
        description=(
            "Datos que solo tienen sentido para un alumno. Es una extension de "
            "`personas`: la llave es la misma persona_id, no una nueva."
        ),
        primary_key=("persona_id",),
        columns=(
            Column("persona_id", "string", "El alumno, como persona.", unique=True),
            Column(
                "estatus",
                "string",
                "Situacion actual del alumno.",
                choices=("prospecto", "inscrito", "activo", "baja", "egresado"),
            ),
            Column("fecha_alta", "date", "Primer dia en la escuela.", required=False),
            Column("fecha_baja", "date", "Ultimo dia. Vacio = sigue activo.", required=False),
            Column(
                "requiere_tutor",
                "bool",
                "Verdadero si es menor de edad y necesita tutor responsable.",
            ),
            Column(
                "programa",
                "string",
                "Programa de aprendizaje contratado (el 'PDA' del formulario).",
                required=False,
            ),
            Column("notas", "string", "Observaciones libres.", required=False),
            *_auditoria(),
        ),
        foreign_keys=(ForeignKey("persona_id", "personas", "persona_id"),),
    )
)

ALUMNOS_INSTRUMENTOS = REGISTRY.add(
    Table(
        name="alumnos_instrumentos",
        layer="master",
        ownership="managed",
        description=(
            "Que instrumento estudia cada alumno. Es de muchos a muchos: hay "
            "quien lleva dos. Separarla de `alumnos` en vez de meter una "
            "columna con valores pegados por comas es lo que permite preguntar "
            "'quien mas toca piano' sin partir texto."
        ),
        primary_key=("persona_id", "instrumento_id"),
        columns=(
            Column("persona_id", "string", "El alumno."),
            Column("instrumento_id", "string", "El instrumento del catalogo."),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("persona_id", "alumnos", "persona_id"),
            ForeignKey("instrumento_id", "instrumentos", "instrumento_id"),
        ),
    )
)

RELACIONES = REGISTRY.add(
    Table(
        name="relaciones",
        layer="master",
        ownership="managed",
        description=(
            "Vinculos entre personas. Cubre el tutor legal, el contacto de "
            "emergencia, quien puede recoger al alumno y quien paga por el "
            "(el caso de 'Sofi paga por mi', que de otro modo rompe la "
            "conciliacion de pagos)."
        ),
        primary_key=("relacion_id",),
        columns=(
            Column("relacion_id", "string", "Identificador, formato REL-0001.", unique=True),
            Column("alumno_persona_id", "string", "El alumno del que se habla."),
            Column("relacionado_persona_id", "string", "La otra persona del vinculo."),
            Column(
                "tipo",
                "string",
                "Naturaleza del vinculo.",
                choices=(
                    "tutor", "emergencia", "autorizado_recoger",
                    "paga_por", "hermano", "profesor",
                ),
            ),
            Column(
                "parentesco",
                "string",
                "Como lo dijo la familia: madre, padre, abuela, tio...",
                required=False,
            ),
            Column("vigente", "bool", "Si el vinculo sigue vigente."),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("alumno_persona_id", "alumnos", "persona_id"),
            ForeignKey("relacionado_persona_id", "personas", "persona_id"),
        ),
    )
)

IDENTIFICADORES_EXTERNOS = REGISTRY.add(
    Table(
        name="identificadores_externos",
        layer="master",
        ownership="managed",
        description=(
            "Puente entre nuestra persona_id y como la llama cada sistema de "
            "afuera. Es la pieza que permite cruzar Kydemy, Jotform y WhatsApp "
            "sin adivinar por nombre cada vez."
        ),
        primary_key=("sistema", "id_externo"),
        columns=(
            Column(
                "sistema",
                "string",
                "Sistema externo.",
                choices=("kydemy", "jotform", "whatsapp", "odoo", "banco"),
            ),
            Column("id_externo", "string", "El identificador tal como lo usa ese sistema."),
            Column("persona_id", "string", "A quien corresponde aqui."),
            Column("notas", "string", "Aclaraciones del cruce.", required=False),
            *_auditoria(),
        ),
        foreign_keys=(ForeignKey("persona_id", "personas", "persona_id"),),
    )
)


# --- Catalogo comercial (viene del Excel de la escuela) ----------------

PROGRAMAS = REGISTRY.add(
    Table(
        name="programas",
        layer="master",
        ownership="managed",
        description=(
            "Los programas de aprendizaje y su precio mensual. Sale del Excel "
            "`data/catalogos_lisart.xlsx` que mantiene la escuela; se ingesta "
            "con `lisart ingest catalogos`, no se edita aqui."
        ),
        primary_key=("programa_id",),
        sort_by=("programa_id",),
        columns=(
            Column("programa_id", "string", "Clave del catalogo, ej. PDA_001.", unique=True),
            Column("modalidad", "string", "Presencial, en linea...", required=False),
            Column("nombre", "string", "Familia del programa, ej. 'Somos Musica'."),
            Column("categoria", "string", "A quien va dirigido: Adultos, Ninos, Bebes.",
                   required=False),
            Column("caracteristica", "string", "Que trabaja el programa.", required=False),
            Column("arquetipo", "string", "Nivel: Esencial, Integral, Especial, Completo.",
                   required=False),
            Column("descripcion", "string", "Texto largo.", required=False),
            Column("precio", "float", "Cuota mensual en pesos."),
            Column("activo", "bool", "Si se ofrece hoy."),
            *_auditoria(),
        ),
    )
)

DESCUENTOS = REGISTRY.add(
    Table(
        name="descuentos",
        layer="master",
        ownership="managed",
        description=(
            "Descuentos que la escuela reconoce. Sale del mismo Excel. **Todavia "
            "no se sabe quien tiene cual**, asi que no se aplican a la "
            "proyeccion: falta la tabla que ligue alumno con descuento."
        ),
        primary_key=("descuento_id",),
        columns=(
            Column("descuento_id", "string", "Clave del catalogo.", unique=True),
            Column("nombre", "string", "Como se le dice."),
            Column("descripcion", "string", "Cuando aplica.", required=False),
            Column(
                "valor_porcentual",
                "float",
                "OJO: en el Excel esta columna mezcla unidades — 0.05 para un 5% "
                "y 100.00 para una beca completa. Se guarda tal cual llego; la "
                "unidad se resuelve al pasar a `alumnos_descuentos`, donde una "
                "persona la confirma.",
            ),
            *_auditoria(),
        ),
    )
)

ALUMNOS_DESCUENTOS = REGISTRY.add(
    Table(
        name="alumnos_descuentos",
        layer="master",
        ownership="hand_edited",
        description=(
            "Que descuento tiene cada alumno. **Es la unica tabla del sistema "
            "que se llena a mano abriendo el archivo**, porque el dato no vive "
            "en ninguna fuente: lo decide la administracion caso por caso.\n\n"
            "El archivo lista a TODOS los alumnos inscritos, no solo a los que "
            "tienen descuento. Los que si tienen quedan arriba (los renglones "
            "con `descuento` vacio se van al final al ordenar), asi que se abre "
            "y lo primero que se ve es a quien se le esta descontando. Dar de "
            "alta un descuento es escribir su nombre en el renglon del alumno; "
            "quitarlo es borrar esa celda.\n\n"
            "`lisart descuentos` es el mantenimiento: agrega a los alumnos "
            "nuevos, rellena nombre, clave y porcentaje, y avisa de lo que no "
            "cuadra. Correrlo despues de editar."
        ),
        primary_key=("alumno_descuento_id",),
        # Ordenar por nombre de descuento agrupa a los que si tienen uno y manda
        # al final a los que no (los vacios se ordenan al final). Un archivo que
        # se edita a mano se ordena para que se lea, no para que se busque.
        sort_by=("descuento", "alumno"),
        columns=(
            # Las dos llaves se pueden dejar vacias, y es a proposito: este
            # archivo se edita en Excel, donde agregar un renglon es duplicar
            # el de arriba. Obligar a inventar un ID a mano es justo lo que
            # hace que un archivo asi se deje de usar. Quien las revisa es
            # `lisart descuentos`, que las rellena o dice por que no pudo.
            Column(
                "alumno_descuento_id",
                "string",
                "Identificador de la fila, formato ALD-0001. Al agregar un "
                "renglon se puede dejar vacio: `lisart descuentos` lo asigna.",
                required=False,
                unique=True,
            ),
            Column(
                "persona_id",
                "string",
                "El alumno. Se puede dejar vacio si se escribe su nombre "
                "completo en `alumno`; `lisart descuentos` lo resuelve.",
                required=False,
            ),
            Column(
                "alumno",
                "string",
                "Nombre del alumno. Se rellena solo. Esta aqui para que el "
                "archivo se pueda leer sin andar cruzando claves a mano.",
                required=False,
            ),
            Column(
                "descuento",
                "string",
                "**La celda que se edita.** El nombre del descuento tal como "
                "esta en el catalogo `descuentos`. Vacio = sin descuento. Un "
                "alumno con dos descuentos lleva dos renglones.",
                required=False,
            ),
            Column(
                "descuento_id",
                "string",
                "Clave del catalogo. La resuelve `lisart descuentos` a partir "
                "del nombre; no hace falta escribirla.",
                required=False,
            ),
            Column(
                "porcentaje",
                "float",
                "Cuanto se le descuenta, EN PUNTOS: 5 es 5%, 100 es beca "
                "completa. Se siembra del catalogo pero manda lo que diga esta "
                "celda, para poder pactar un caso particular sin inventar una "
                "entrada de catalogo. Si se cambia el catalogo, esta columna NO "
                "se actualiza sola: eso es lo que se paga por poder ajustarla.",
                required=False,
            ),
            Column(
                "notas",
                "string",
                "Por que tiene ese descuento, desde cuando, con quien se pacto. "
                "Es lo que evita que dentro de un ano nadie sepa de donde salio.",
                required=False,
            ),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("persona_id", "alumnos", "persona_id", required=False),
            ForeignKey("descuento_id", "descuentos", "descuento_id", required=False),
        ),
    )
)


# --- Horarios ----------------------------------------------------------
#
# Los dias se nombran como en el formulario de inscripcion, para que el horario
# que ya declararon los 115 alumnos entre sin traducir.
DIAS = ("L", "M", "Mi", "J", "V", "S", "D")

DISPONIBILIDAD = REGISTRY.add(
    Table(
        name="disponibilidad",
        layer="master",
        ownership="managed",
        description=(
            "Cuando puede cada persona, semana tipo. Vale para profesores y "
            "para alumnos: el alumno declara su horario al inscribirse y el "
            "profesor el suyo al dar de alta. Cruzar las dos es lo que permite "
            "proponer una reposicion que le sirva a los dos."
        ),
        primary_key=("disponibilidad_id",),
        sort_by=("persona_id", "dia", "hora_inicio"),
        columns=(
            Column("disponibilidad_id", "string", "Identificador, formato DIS-0001.", unique=True),
            Column("persona_id", "string", "De quien es este horario."),
            Column("dia", "string", "Dia de la semana.", choices=DIAS),
            Column("hora_inicio", "time", "Desde que hora, en formato 24 h."),
            Column("hora_fin", "time", "Hasta que hora, sin incluirla."),
            Column(
                "estado",
                "string",
                "Que pasa en ese rango. NO existe 'no disponible': una hora sin "
                "fila es una hora no disponible. Ver el modulo horarios.",
                choices=("disponible", "bloqueado"),
            ),
            Column(
                "motivo",
                "string",
                "Por que esta bloqueado, si lo esta. Util para distinguir una "
                "clase de un bloqueo personal.",
                required=False,
            ),
            Column(
                "vigente_desde",
                "date",
                "Desde cuando rige este bloque. Vacio = siempre.",
                required=False,
            ),
            Column(
                "vigente_hasta",
                "date",
                "Hasta cuando rigio. Vacio = sigue vigente. El horario cambia, "
                "y cerrar el viejo conserva por que una clase estaba donde estaba.",
                required=False,
            ),
            *_auditoria(),
        ),
        foreign_keys=(ForeignKey("persona_id", "personas", "persona_id"),),
    )
)

CLASES = REGISTRY.add(
    Table(
        name="clases",
        layer="master",
        ownership="managed",
        description=(
            "Una clase en la semana tipo: que dia, a que hora, en que espacio. "
            "Quien la da y quien la toma van en tablas aparte porque una clase "
            "puede tener varios profesores y varios alumnos."
        ),
        primary_key=("clase_id",),
        sort_by=("dia", "hora_inicio", "clase_id"),
        columns=(
            Column("clase_id", "string", "Identificador, formato CLA-0001.", unique=True),
            Column("nombre", "string", "Como se le dice a esta clase.", required=False),
            Column("instrumento_id", "string", "Instrumento que se trabaja.", required=False),
            Column("espacio_id", "string", "Donde se da.", required=False),
            Column("dia", "string", "Dia de la semana.", choices=DIAS),
            Column("hora_inicio", "time", "Hora de inicio, 24 h."),
            Column("hora_fin", "time", "Hora de fin, sin incluirla."),
            Column("cupo", "int", "Cuantos alumnos caben. Vacio = sin limite.", required=False),
            Column("activa", "bool", "Si se sigue dando."),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("instrumento_id", "instrumentos", "instrumento_id", required=False),
            ForeignKey("espacio_id", "espacios", "espacio_id", required=False),
        ),
    )
)

CLASES_PROFESORES = REGISTRY.add(
    Table(
        name="clases_profesores",
        layer="master",
        ownership="managed",
        description=(
            "Quien da cada clase. Es de muchos a muchos a proposito: una clase "
            "puede tener mas de un profesor, y un profesor da varias clases."
        ),
        primary_key=("clase_id", "persona_id"),
        columns=(
            Column("clase_id", "string", "La clase."),
            Column("persona_id", "string", "El profesor."),
            Column(
                "rol_en_clase",
                "string",
                "Que hace en la clase.",
                choices=("titular", "apoyo", "suplente"),
                required=False,
            ),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("clase_id", "clases", "clase_id"),
            ForeignKey("persona_id", "personas", "persona_id"),
        ),
    )
)

CLASES_ALUMNOS = REGISTRY.add(
    Table(
        name="clases_alumnos",
        layer="master",
        ownership="managed",
        description="Quien toma cada clase.",
        primary_key=("clase_id", "persona_id"),
        columns=(
            Column("clase_id", "string", "La clase."),
            Column("persona_id", "string", "El alumno."),
            Column("vigente_desde", "date", "Desde cuando la toma.", required=False),
            Column("vigente_hasta", "date", "Hasta cuando. Vacio = sigue.", required=False),
            *_auditoria(),
        ),
        foreign_keys=(
            ForeignKey("clase_id", "clases", "clase_id"),
            ForeignKey("persona_id", "alumnos", "persona_id"),
        ),
    )
)


# --- Lo que llega de afuera --------------------------------------------

RESPUESTAS_INSCRIPCION = REGISTRY.add(
    Table(
        name="respuestas_inscripcion",
        layer="interim",
        ownership="managed",
        description=(
            "Una fila por envio del formulario de inscripcion de Jotform, ya "
            "aplanado a columnas. Vive en `interim` y no en `master` porque se "
            "puede reconstruir entero desde los JSON de `data/raw/jotform/`. "
            "Todavia NO es la verdad de la escuela: es materia prima para dar "
            "de alta personas y alumnos."
        ),
        primary_key=("form__submission_id",),
        sort_by=("form__created_at", "form__submission_id"),
        columns=(*jotform.columnas_tabla(), *_auditoria()),
    )
)


# --- Catalogos (los mantiene una persona a mano) -----------------------

ESPACIOS = REGISTRY.add(
    Table(
        name="espacios",
        layer="master",
        ownership="hand_edited",
        description=(
            "Todos los espacios fisicos de la escuela, no solo las aulas: "
            "tambien recepcion, cocina y bodega. Base del proyecto de "
            "calendarizacion. Se llama 'espacios' y no 'salones' porque la "
            "cocina no es un salon y la calendarizacion nunca debe ofrecerla "
            "para dar clase."
        ),
        primary_key=("espacio_id",),
        columns=(
            Column("espacio_id", "string", "Clave corta, ej. AULA-GRANDE.", unique=True),
            Column("nombre", "string", "Como le dicen en la escuela."),
            Column(
                "tipo",
                "string",
                "Que es el espacio.",
                choices=("aula", "auditorio", "bodega", "recepcion", "cocina", "otro"),
            ),
            Column(
                "piso",
                "string",
                "En que nivel esta. Ojo: en la escuela le dicen 'primer piso' a "
                "la planta baja, por eso aqui se nombran los niveles y no se "
                "numeran.",
                choices=("planta_baja", "planta_alta"),
            ),
            Column(
                "agendable",
                "bool",
                "Si se puede reservar para una clase. Es lo que separa un aula "
                "de la cocina, y lo que permite que la bodega deje de serlo un "
                "dia sin tener que cambiar el modelo.",
            ),
            Column(
                "capacidad",
                "int",
                "Cuantas personas caben. Vacio = todavia no se ha medido.",
                required=False,
            ),
            Column("equipamiento", "string", "Piano, bateria, atriles...", required=False),
            Column("notas", "string", "Tamano relativo y observaciones.", required=False),
            Column("activo", "bool", "Si se puede usar hoy."),
        ),
    )
)

INSTRUMENTOS = REGISTRY.add(
    Table(
        name="instrumentos",
        layer="master",
        ownership="hand_edited",
        description=(
            "Instrumentos que se ensenan. Los nombres deben coincidir con los "
            "del formulario de inscripcion."
        ),
        primary_key=("instrumento_id",),
        columns=(
            Column("instrumento_id", "string", "Clave corta, ej. PIANO.", unique=True),
            Column("nombre", "string", "Nombre para mostrar."),
            Column("familia", "string", "Cuerda, viento, percusion, voz, teoria.", required=False),
            Column(
                "code",
                "string",
                "Clave corta de la escuela (PIA, VIO...), del catalogo en Excel.",
                required=False,
            ),
            Column("descripcion", "string", "Como se describe la clase.", required=False),
            Column("activo", "bool", "Si se ofrece actualmente."),
        ),
    )
)

CONCEPTOS = REGISTRY.add(
    Table(
        name="conceptos",
        layer="master",
        ownership="hand_edited",
        description=(
            "Que se cobra y cuanto. Los montos se versionan por vigencia en vez "
            "de sobrescribirse, para que un pago viejo siga cuadrando con el "
            "precio que existia cuando se hizo."
        ),
        primary_key=("concepto_id",),
        columns=(
            Column("concepto_id", "string", "Clave del concepto, ej. COLEG-2026.", unique=True),
            Column("nombre", "string", "Nombre para mostrar en mensajes y recibos."),
            Column(
                "tipo",
                "string",
                "Familia del cobro.",
                choices=("inscripcion", "colegiatura", "material", "examen", "evento", "otro"),
            ),
            Column("monto", "float", "Monto en pesos."),
            Column(
                "periodicidad",
                "string",
                "Cada cuando se cobra.",
                choices=("unica", "mensual", "anual"),
            ),
            Column("vigente_desde", "date", "Desde cuando aplica este monto."),
            Column("vigente_hasta", "date", "Hasta cuando. Vacio = vigente.", required=False),
            Column("activo", "bool", "Si se sigue cobrando."),
        ),
    )
)
