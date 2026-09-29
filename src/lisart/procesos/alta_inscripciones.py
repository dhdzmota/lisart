"""De `respuestas_inscripcion` a `personas`, `alumnos` y `relaciones`.

Este es el paso donde un formulario se vuelve gente.

El problema de fondo
--------------------
Cada envio del formulario menciona hasta **cinco** personas: el alumno, su
tutor, un contacto de emergencia y hasta dos autorizados a recoger. Pero muchas
de esas menciones son **la misma persona**:

* una mama con tres hijos inscritos aparece como tutora en tres envios,
* un tutor suele ser tambien el contacto de emergencia de su propio hijo,
* un alumno mayor de edad puede ser el tutor de su hermano menor.

Con los datos reales de la escuela: 282 menciones que corresponden a 240
personas. Sin deduplicar se crearian 42 humanos de mas, y con ellos pagos que
no cuadran y mensajes duplicados.

Como se decide que dos menciones son la misma persona
-----------------------------------------------------
Por el **nombre normalizado** (sin acentos, en minusculas, sin puntuacion), y
solo si nada mas las contradice: si dos menciones con el mismo nombre traen
fechas de nacimiento distintas, son dos personas distintas y se reporta el
conflicto en vez de mezclarlas.

Es una regla simple, adecuada a una escuela de cientos de personas. Si algun
dia hay dos "Juan Perez" de verdad, el reporte los saca a la luz y se resuelven
a mano. Cruzar por nombre es el ultimo recurso; en cuanto Kydemy entre al
sistema, la llave buena sera `identificadores_externos`.

Que se escribe
--------------
* `personas` .................. una fila por humano
* `personas_roles` ............ alumno y tutor (solo los roles que el formulario prueba)
* `alumnos` ................... estatus, fecha de alta, si necesita tutor
* `relaciones` ................ tutor / emergencia / autorizado_recoger
* `identificadores_externos` .. de que envio y en que papel salio cada persona

Correrlo dos veces no duplica nada: las personas se reconocen por nombre y las
relaciones por el trio (alumno, otra persona, tipo).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time

import pandas as pd

from lisart import io
from lisart.ids import (
    ahora,
    next_ids,
    nombre_completo,
    normalizar_correo,
    normalizar_nombre,
    normalizar_telefono,
)

MAYORIA_DE_EDAD = 18


@dataclass(frozen=True)
class Bloque:
    """Un grupo de columnas del formulario que describe a una persona."""

    prefijo: str
    """Prefijo de las columnas, ej. 'tutor' -> tutor__nombre_completo___nombre."""
    relacion: str | None
    """Como se relaciona con el alumno del envio. None = es el alumno."""
    rol: str | None = None
    """Rol en la escuela, si el formulario lo prueba."""


BLOQUES: tuple[Bloque, ...] = (
    Bloque("alumno", None, rol="alumno"),
    Bloque("tutor", "tutor", rol="tutor"),
    Bloque("emergencia", "emergencia"),
    Bloque("recojer1", "autorizado_recoger"),
    Bloque("recojer2", "autorizado_recoger"),
)


@dataclass
class Mencion:
    """Una persona tal como la menciona UN envio."""

    submission_id: str
    bloque: Bloque
    nombre: str | None
    apellido_paterno: str | None
    apellido_materno: str | None
    clave: str
    fecha_nacimiento: date | None = None
    telefono: str | None = None
    correo: str | None = None
    domicilio: str | None = None
    momento: pd.Timestamp | None = None


@dataclass
class Resultado:
    personas_nuevas: int = 0
    personas_actualizadas: int = 0
    alumnos_nuevos: int = 0
    relaciones_nuevas: int = 0
    menciones: int = 0
    personas_totales: int = 0
    instrumentos_ligados: int = 0
    bloques_horario: int = 0
    conflictos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        return (
            f"{self.menciones} mencion(es) en el formulario -> "
            f"{self.personas_totales} persona(s) distintas.\n"
            f"  personas nuevas: {self.personas_nuevas}, "
            f"actualizadas: {self.personas_actualizadas}\n"
            f"  alumnos nuevos: {self.alumnos_nuevos}, "
            f"relaciones nuevas: {self.relaciones_nuevas}\n"
            f"  alumno-instrumento: {self.instrumentos_ligados}, "
            f"bloques de horario: {self.bloques_horario}"
        )


def _valor(fila: pd.Series, columna: str) -> str | None:
    if columna not in fila.index:
        return None
    valor = fila[columna]
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def _domicilio(fila: pd.Series, prefijo: str) -> str | None:
    partes = [
        _valor(fila, f"{prefijo}__domicilio___{p}")
        for p in ("calle1", "calle2", "ciudad", "estado", "codigo_postal")
    ]
    llenas = [p for p in partes if p]
    return ", ".join(llenas) if llenas else None


def _telefono(fila: pd.Series, prefijo: str) -> str | None:
    """Jotform parte el telefono en lada y numero. Se prueban las dos formas."""
    area = _valor(fila, f"{prefijo}__telefono___area")
    numero = _valor(fila, f"{prefijo}__telefono___telefono")
    if not numero:
        return None
    return normalizar_telefono(f"{area or ''}{numero}") or normalizar_telefono(numero)


def _fecha(fila: pd.Series, columna: str) -> date | None:
    if columna not in fila.index:
        return None
    valor = fila[columna]
    if valor is None or (not isinstance(valor, date) and pd.isna(valor)):
        return None
    return valor if isinstance(valor, date) else None


def _mencion(fila: pd.Series, bloque: Bloque) -> Mencion | None:
    p = bloque.prefijo
    nombre = _valor(fila, f"{p}__nombre_completo___nombre")
    paterno = _valor(fila, f"{p}__nombre_completo___apellido_paterno")
    materno = _valor(fila, f"{p}__nombre_completo___apellido_materno")

    # El campo de politicas es un texto libre, no un nombre estructurado; para
    # el alumno siempre viene el nombre estructurado, asi que basta con este.
    clave = normalizar_nombre(nombre_completo(nombre, paterno, materno))
    if not clave:
        return None

    return Mencion(
        submission_id=str(fila["form__submission_id"]),
        bloque=bloque,
        nombre=nombre,
        apellido_paterno=paterno,
        apellido_materno=materno,
        clave=clave,
        fecha_nacimiento=_fecha(fila, f"{p}__fecha_nacimiento"),
        telefono=_telefono(fila, p),
        correo=normalizar_correo(_valor(fila, f"{p}__correo")),
        domicilio=_domicilio(fila, p),
        momento=fila.get("form__created_at"),
    )


def extraer_menciones(respuestas: pd.DataFrame) -> list[Mencion]:
    """Saca todas las personas mencionadas en los envios."""
    menciones: list[Mencion] = []
    for _, fila in respuestas.iterrows():
        for bloque in BLOQUES:
            mencion = _mencion(fila, bloque)
            if mencion:
                menciones.append(mencion)
    return menciones


def _mas_reciente_primero(menciones: list[Mencion]) -> list[Mencion]:
    return sorted(
        menciones,
        key=lambda m: (m.momento if m.momento is not None else pd.Timestamp.min),
        reverse=True,
    )


def _elegir_fecha_nacimiento(menciones: list[Mencion]) -> tuple[date | None, list[str]]:
    """Decide la fecha de nacimiento cuando las menciones no coinciden.

    Con los datos reales aparecio un patron: en el bloque del tutor la gente a
    veces captura la fecha de nacimiento **del hijo**, no la suya (4 de 65
    fechas de tutor darian menos de 18 anios, y en 5 envios la fecha del tutor
    es identica a la del alumno).

    Por eso no gana "el dato mas reciente": gana lo que la persona dijo **de si
    misma**, o sea el bloque donde aparece como alumno. Y si ni asi se puede
    decidir, se deja **vacia**. Una fecha vacia se nota y se corrige; una fecha
    equivocada se propaga a los recordatorios y a los tramites.
    """
    fechas = {m.fecha_nacimiento for m in menciones if m.fecha_nacimiento is not None}
    if len(fechas) <= 1:
        return next(iter(fechas), None), []

    clave = menciones[0].clave
    detalle = ", ".join(sorted(str(f) for f in fechas))
    propias = {
        m.fecha_nacimiento
        for m in menciones
        if m.bloque.prefijo == "alumno" and m.fecha_nacimiento is not None
    }
    if len(propias) == 1:
        elegida = propias.pop()
        return elegida, [
            f"'{clave}' aparece con {len(fechas)} fechas de nacimiento ({detalle}). "
            f"Se tomo {elegida}, que es la que dio de si misma como alumno. "
            "Las otras vienen del bloque de tutor, donde suelen capturar la del hijo."
        ]

    return None, [
        f"'{clave}' aparece con {len(fechas)} fechas de nacimiento ({detalle}) y ninguna "
        "es autodeclarada. Se dejo VACIA a proposito. Revisar a mano: puede ser un typo "
        "o pueden ser dos personas distintas con el mismo nombre."
    ]


def _consolidar(menciones: list[Mencion]) -> tuple[dict, list[str]]:
    """Junta varias menciones de la misma persona en un solo juego de datos.

    Para telefono, correo y domicilio gana el dato mas reciente que no venga
    vacio: si alguien actualizo su telefono en la ultima inscripcion, ese es el
    bueno. La fecha de nacimiento se decide aparte, ver arriba.
    """
    ordenadas = _mas_reciente_primero(menciones)
    principal = ordenadas[0]

    datos = {
        "nombre": principal.nombre,
        "apellido_paterno": principal.apellido_paterno,
        "apellido_materno": principal.apellido_materno,
        "nombre_normalizado": principal.clave,
    }
    for campo in ("telefono", "correo", "domicilio"):
        datos[campo] = next(
            (getattr(m, campo) for m in ordenadas if getattr(m, campo) is not None), None
        )

    datos["fecha_nacimiento"], conflictos = _elegir_fecha_nacimiento(menciones)
    return datos, conflictos


def procesar(*, solo_activos: bool = True) -> Resultado:
    """Lee las inscripciones y escribe personas, alumnos y relaciones."""
    respuestas = io.read_table("respuestas_inscripcion")
    resultado = Resultado()

    if solo_activos:
        antes = len(respuestas)
        respuestas = respuestas[respuestas["form__status"] == "ACTIVE"]
        descartados = antes - len(respuestas)
        if descartados:
            resultado.avisos.append(
                f"{descartados} envio(s) no estan ACTIVE en Jotform y se ignoraron."
            )

    menciones = extraer_menciones(respuestas)
    resultado.menciones = len(menciones)

    grupos: dict[str, list[Mencion]] = {}
    for mencion in menciones:
        grupos.setdefault(mencion.clave, []).append(mencion)
    resultado.personas_totales = len(grupos)

    momento = ahora()
    personas = io.read_table("personas")
    ya_conocidas = dict(
        zip(
            personas["nombre_normalizado"].astype(str),
            personas["persona_id"].astype(str),
            strict=False,
        )
    )

    claves_nuevas = [c for c in grupos if c not in ya_conocidas]
    ids_nuevos = next_ids("personas", len(claves_nuevas)) if claves_nuevas else []
    for clave, nuevo_id in zip(claves_nuevas, ids_nuevos, strict=True):
        ya_conocidas[clave] = nuevo_id

    filas_personas = []
    for clave, del_grupo in grupos.items():
        datos, conflictos = _consolidar(del_grupo)
        resultado.conflictos.extend(conflictos)
        filas_personas.append({
            "persona_id": ya_conocidas[clave],
            **datos,
            "activo": True,
            "creado_en": momento,
            "actualizado_en": momento,
            "fuente": "jotform",
        })

    resultado.personas_nuevas = len(claves_nuevas)
    resultado.personas_actualizadas = len(grupos) - len(claves_nuevas)
    if not filas_personas:
        # Sin inscripciones no hay nada que escribir, y un DataFrame vacio no
        # trae ni las columnas para intentarlo.
        return resultado
    io.upsert("personas", pd.DataFrame(filas_personas))

    _escribir_roles(grupos, ya_conocidas, momento)
    resultado.alumnos_nuevos = _escribir_alumnos(respuestas, grupos, ya_conocidas, momento)
    resultado.relaciones_nuevas = _escribir_relaciones(respuestas, ya_conocidas, momento)
    _escribir_identificadores(menciones, ya_conocidas, momento)
    resultado.instrumentos_ligados, avisos_inst = _escribir_instrumentos(
        respuestas, ya_conocidas, momento
    )
    resultado.avisos.extend(avisos_inst)
    resultado.bloques_horario = _escribir_disponibilidad(respuestas, ya_conocidas, momento)
    resultado.avisos.extend(_revisar_coherencia())

    return resultado


def _escribir_instrumentos(respuestas, ids_por_clave, momento) -> tuple[int, list[str]]:
    """Liga cada alumno con los instrumentos que estudia.

    El catalogo `instrumentos` lo mantiene una persona, asi que aqui **no se
    inventan instrumentos**: si el formulario trae uno que no esta en el
    catalogo, se avisa para que lo den de alta. Agregarlo solo desde el codigo
    llenaria el catalogo de variantes mal escritas sin que nadie lo note.
    """
    catalogo = io.read_table("instrumentos")
    if catalogo.empty:
        return 0, ["El catalogo de instrumentos esta vacio: no se ligo ninguno."]

    por_nombre = {
        normalizar_nombre(n): i
        for n, i in zip(catalogo["nombre"], catalogo["instrumento_id"], strict=False)
    }

    filas, desconocidos = [], set()
    for _, fila in respuestas.iterrows():
        alumno = _mencion(fila, BLOQUES[0])
        crudo = _valor(fila, "instrumentos")
        if not alumno or not crudo:
            continue
        for nombre in crudo.split("|"):
            clave = normalizar_nombre(nombre)
            if not clave:
                continue
            instrumento_id = por_nombre.get(clave)
            if instrumento_id is None:
                desconocidos.add(nombre.strip())
                continue
            filas.append({
                "persona_id": ids_por_clave[alumno.clave],
                "instrumento_id": instrumento_id,
                "creado_en": momento, "actualizado_en": momento, "fuente": "jotform",
            })

    avisos = []
    if desconocidos:
        avisos.append(
            f"{len(desconocidos)} instrumento(s) del formulario no estan en el catalogo "
            f"y no se ligaron: {', '.join(sorted(desconocidos))}. Agregarlos a "
            "data/master/instrumentos.csv."
        )
    if not filas:
        return 0, avisos

    tabla = pd.DataFrame(filas).drop_duplicates(subset=["persona_id", "instrumento_id"])
    io.upsert("alumnos_instrumentos", tabla)
    return len(tabla), avisos


DURACION_BLOQUE_MIN = 30
"""El formulario pide la hora de INICIO de la sesion, en medias horas."""


def _escribir_disponibilidad(respuestas, ids_por_clave, momento) -> int:
    """Convierte el horario que marco cada alumno en filas de `disponibilidad`.

    El formulario da una matriz de dias x horas de inicio ("3:30 pm"), que aqui
    se vuelve un rango por bloque. Bloques pegados se unen despues, al leer.

    Se escribe con `estado="disponible"`: lo que el alumno marco es cuando SI
    puede. Las horas que no marco no generan fila, que es exactamente lo que
    significa "no disponible".
    """
    filas = []
    existentes = io.read_table("disponibilidad")
    ya = set(
        zip(
            existentes["persona_id"].astype(str),
            existentes["dia"].astype(str),
            existentes["hora_inicio"].astype(str),
            strict=False,
        )
    )

    pendientes = []
    for _, fila in respuestas.iterrows():
        alumno = _mencion(fila, BLOQUES[0])
        if not alumno:
            continue
        persona_id = ids_por_clave[alumno.clave]
        for columna in [c for c in respuestas.columns if c.startswith("horario___")]:
            dia = columna.split("___", 1)[1]
            crudo = _valor(fila, columna)
            if not crudo:
                continue
            for etiqueta in crudo.split("|"):
                hora = _hora_del_formulario(etiqueta)
                if hora is None:
                    continue
                if (persona_id, dia, hora.strftime("%H:%M")) in ya:
                    continue
                pendientes.append((persona_id, dia, hora))

    if not pendientes:
        return 0

    ids = next_ids("disponibilidad", len(pendientes))
    for identificador, (persona_id, dia, hora) in zip(ids, pendientes, strict=True):
        fin_min = hora.hour * 60 + hora.minute + DURACION_BLOQUE_MIN
        filas.append({
            "disponibilidad_id": identificador,
            "persona_id": persona_id,
            "dia": dia,
            "hora_inicio": hora,
            "hora_fin": time(fin_min // 60, fin_min % 60),
            "estado": "disponible",
            "motivo": None,
            "vigente_desde": None,
            "vigente_hasta": None,
            "creado_en": momento, "actualizado_en": momento, "fuente": "jotform",
        })
    io.upsert("disponibilidad", pd.DataFrame(filas))
    return len(filas)


def _hora_del_formulario(etiqueta: str) -> time | None:
    """'3:30 pm' -> time(15, 30). El formulario usa 12 horas con am/pm."""
    texto = etiqueta.strip().lower().replace(".", "")
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(am|pm)$", texto)
    if not m:
        return None
    hora, minuto, meridiano = int(m.group(1)), int(m.group(2)), m.group(3)
    if meridiano == "pm" and hora != 12:
        hora += 12
    if meridiano == "am" and hora == 12:
        hora = 0
    return time(hora, minuto) if 0 <= hora <= 23 else None


def _revisar_coherencia() -> list[str]:
    """Cosas que, si pasan, casi seguro son un dato mal capturado."""
    avisos: list[str] = []
    personas = io.read_table("personas")
    relaciones = io.read_table("relaciones")
    if personas.empty or relaciones.empty:
        return avisos

    hoy = date.today()
    nacimiento = dict(
        zip(personas["persona_id"].astype(str), personas["fecha_nacimiento"], strict=False)
    )

    def edad(persona_id: str) -> int | None:
        f = nacimiento.get(persona_id)
        if not isinstance(f, date):
            return None
        return hoy.year - f.year - ((hoy.month, hoy.day) < (f.month, f.day))

    tutores = relaciones[relaciones["tipo"] == "tutor"]
    menores = {
        pid
        for pid in tutores["relacionado_persona_id"].astype(str).unique()
        if (e := edad(pid)) is not None and e < MAYORIA_DE_EDAD
    }
    if menores:
        avisos.append(
            f"{len(menores)} persona(s) figuran como tutor pero su fecha de nacimiento "
            "las hace menores de edad. Casi siempre es que capturaron la fecha del hijo "
            "en el campo del tutor. Personas: " + ", ".join(sorted(menores))
        )

    sin_tutor = _alumnos_menores_sin_tutor(relaciones, edad)
    if sin_tutor:
        avisos.append(
            f"{len(sin_tutor)} alumno(s) menores de edad no tienen ningun tutor registrado. "
            "Personas: " + ", ".join(sorted(sin_tutor))
        )
    return avisos


def _alumnos_menores_sin_tutor(relaciones: pd.DataFrame, edad) -> set[str]:
    alumnos = io.read_table("alumnos")
    if alumnos.empty:
        return set()
    con_tutor = set(
        relaciones[relaciones["tipo"] == "tutor"]["alumno_persona_id"].astype(str)
    )
    return {
        pid
        for pid in alumnos["persona_id"].astype(str)
        if pid not in con_tutor and (e := edad(pid)) is not None and e < MAYORIA_DE_EDAD
    }


def _escribir_roles(grupos, ids_por_clave, momento) -> None:
    filas = []
    for clave, menciones in grupos.items():
        roles = {m.bloque.rol for m in menciones if m.bloque.rol}
        for rol in sorted(roles):
            filas.append({
                "persona_id": ids_por_clave[clave],
                "rol": rol,
                "vigente_desde": None,
                "vigente_hasta": None,
                "creado_en": momento,
                "actualizado_en": momento,
                "fuente": "jotform",
            })
    if filas:
        io.upsert("personas_roles", pd.DataFrame(filas))


def _escribir_alumnos(respuestas, grupos, ids_por_clave, momento) -> int:
    """Un alumno por persona que aparecio como alumno en algun envio."""
    antes = len(io.read_table("alumnos"))

    # Edad y fecha de llenado del envio donde aparece cada alumno.
    contexto: dict[str, dict] = {}
    for _, fila in respuestas.iterrows():
        mencion = _mencion(fila, BLOQUES[0])
        if not mencion:
            continue
        edad = pd.to_numeric(fila.get("alumno__edad"), errors="coerce")
        llenado = fila.get("fechayhora_llenado") or fila.get("form__created_at")
        actual = contexto.get(mencion.clave)
        alta = llenado.date() if isinstance(llenado, pd.Timestamp) else None
        if actual is None or (alta and actual["fecha_alta"] and alta < actual["fecha_alta"]):
            contexto[mencion.clave] = {
                "edad": edad, "fecha_alta": alta, "programa": _valor(fila, "pda"),
            }

    filas = []
    for clave, datos in contexto.items():
        edad = datos["edad"]
        filas.append({
            "persona_id": ids_por_clave[clave],
            "estatus": "inscrito",
            "fecha_alta": datos["fecha_alta"],
            "fecha_baja": None,
            # Sin edad no se puede afirmar que es mayor: se asume que necesita
            # tutor, que es el lado seguro tratandose de menores.
            "requiere_tutor": True if pd.isna(edad) else bool(edad < MAYORIA_DE_EDAD),
            "programa": datos["programa"],
            "notas": None,
            "creado_en": momento,
            "actualizado_en": momento,
            "fuente": "jotform",
        })
    if filas:
        io.upsert("alumnos", pd.DataFrame(filas))
    return len(io.read_table("alumnos")) - antes


def _escribir_relaciones(respuestas, ids_por_clave, momento) -> int:
    """Vinculos entre el alumno de cada envio y las demas personas del envio."""
    existentes = io.read_table("relaciones")
    por_trio: dict[tuple[str, str, str], str] = {}
    for _, fila in existentes.iterrows():
        trio = (
            str(fila["alumno_persona_id"]),
            str(fila["relacionado_persona_id"]),
            str(fila["tipo"]),
        )
        por_trio[trio] = str(fila["relacion_id"])

    trios_nuevos: list[tuple[str, str, str]] = []
    for _, fila in respuestas.iterrows():
        alumno = _mencion(fila, BLOQUES[0])
        if not alumno:
            continue
        alumno_id = ids_por_clave[alumno.clave]
        for bloque in BLOQUES:
            if bloque.relacion is None:
                continue
            otra = _mencion(fila, bloque)
            if not otra:
                continue
            otro_id = ids_por_clave[otra.clave]
            # Alguien se puso a si mismo como contacto de emergencia: no es
            # un vinculo, es ruido.
            if otro_id == alumno_id:
                continue
            trio = (alumno_id, otro_id, bloque.relacion)
            if trio not in por_trio and trio not in trios_nuevos:
                trios_nuevos.append(trio)

    if not trios_nuevos:
        return 0

    ids = next_ids("relaciones", len(trios_nuevos))
    filas = [
        {
            "relacion_id": relacion_id,
            "alumno_persona_id": alumno_id,
            "relacionado_persona_id": otro_id,
            "tipo": tipo,
            "parentesco": None,  # el formulario no lo pregunta todavia
            "vigente": True,
            "creado_en": momento,
            "actualizado_en": momento,
            "fuente": "jotform",
        }
        for relacion_id, (alumno_id, otro_id, tipo) in zip(ids, trios_nuevos, strict=True)
    ]
    io.upsert("relaciones", pd.DataFrame(filas))
    return len(filas)


def _escribir_identificadores(menciones, ids_por_clave, momento) -> None:
    """Deja el rastro de que envio y que papel produjo cada persona.

    Jotform no tiene identificadores de persona, solo de envio. Guardar
    `<envio>#<papel>` es lo mas cercano y permite volver al origen de un dato.
    """
    filas = [
        {
            "sistema": "jotform",
            "id_externo": f"{m.submission_id}#{m.bloque.prefijo}",
            "persona_id": ids_por_clave[m.clave],
            "notas": None,
            "creado_en": momento,
            "actualizado_en": momento,
            "fuente": "jotform",
        }
        for m in menciones
    ]
    if filas:
        io.upsert("identificadores_externos", pd.DataFrame(filas))


# --- Consultas sobre la base ya construida -----------------------------


def familias() -> pd.DataFrame:
    """Alumnos que comparten tutor, es decir hermanos.

    No se guardan filas de 'hermano' en `relaciones` a proposito: la familia se
    deduce de que dos alumnos apunten al MISMO tutor, y eso no se puede quedar
    desactualizado. Una fila inferida y guardada, si.
    """
    relaciones = io.read_table("relaciones")
    personas = io.read_table("personas")
    tutores = relaciones[(relaciones["tipo"] == "tutor") & (relaciones["vigente"])]

    if tutores.empty:
        return pd.DataFrame(columns=["tutor_persona_id", "tutor", "alumnos", "alumno_persona_ids"])

    nombres = dict(
        zip(personas["persona_id"].astype(str), personas["nombre_normalizado"], strict=False)
    )
    grupos = (
        tutores.groupby("relacionado_persona_id")["alumno_persona_id"]
        .apply(lambda s: sorted(set(s.astype(str))))
        .reset_index()
    )
    grupos.columns = ["tutor_persona_id", "alumno_persona_ids"]
    grupos["alumnos"] = grupos["alumno_persona_ids"].apply(len)
    grupos["tutor"] = grupos["tutor_persona_id"].astype(str).map(nombres)
    return grupos.sort_values("alumnos", ascending=False).reset_index(drop=True)
