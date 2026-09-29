"""Jotform: formularios de inscripcion.

Portado del notebook `projects/data_mechanism/respuestas_inscripcion_forms.ipynb`.

Como Jotform identifica los campos
-----------------------------------
Cada respuesta trae un numero de `order` (la posicion del campo en el
formulario) y su tipo de control. El notebook mapeaba `order -> nombre de
columna`, y aqui se conserva ese mapeo en `CAMPOS`.

**Es un mapeo fragil y hay que saberlo:** si alguien reordena o inserta un
campo en Jotform, los numeros se recorren y los datos empiezan a caer en la
columna equivocada **sin que nada truene**. Por eso `revisar_mapeo()` compara
lo que llego contra lo que se espera y avisa. Correrlo es barato; descubrir a
los tres meses que los telefonos estan en la columna de correos, no.

Tres diferencias a proposito contra el notebook
------------------------------------------------
1. El notebook hacia `.strip().lower().title()` sobre todos los valores. Aqui
   el texto se guarda **como llego** (solo se recortan espacios). Convertir
   "MARIA" en "Maria" esta bien, pero tambien convierte "DE LA O" en "De La O"
   y eso ya es inventar. La normalizacion es trabajo del paso que mapea a
   `personas`, donde vive `ids.normalizar_nombre`.
2. El notebook comparaba el manifiesto contra el texto exacto de **2026**. Eso
   se rompe solo el proximo ciclo escolar, asi que aqui se guarda el texto tal
   cual y la interpretacion se deja para despues.
3. En el notebook `name_dict` tenia la llave `71` repetida
   (`uso_imagen__nombre_completo_alumno` y `..._tutor`), asi que el campo 70 se
   perdia completo. Son dos campos distintos: el **70** lo firma el alumno
   mayor de edad y el **71** lo firma el tutor de un menor. Confirmado contra
   los datos reales por la edad y por que casilla de autorizacion marcan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from lisart.schema import Column

BASE_URL = "https://api.jotform.com"
LIMITE_POR_PAGINA = 1000  # el maximo que acepta la API

TipoCampo = Literal[
    "texto", "nombre", "domicilio", "telefono", "fecha", "fecha_hora",
    "opciones", "horario", "archivo", "si_no", "firma",
]


@dataclass(frozen=True)
class Campo:
    """Un campo del formulario y como se guarda."""

    orden: int
    nombre: str
    tipo: TipoCampo
    descripcion: str = ""


# Las partes en que se abre un campo compuesto de Jotform.
PARTES: dict[str, tuple[str, ...]] = {
    "nombre": ("nombre", "apellido_paterno", "apellido_materno"),
    "domicilio": ("calle1", "calle2", "ciudad", "estado", "codigo_postal"),
    "telefono": ("area", "telefono"),
}

# Las columnas de la matriz de horario, como las nombra el formulario.
DIAS_HORARIO: tuple[str, ...] = ("L", "M", "Mi", "J", "V", "S")

# El mapeo orden -> campo. Sale de `name_dict` del notebook.
CAMPOS: tuple[Campo, ...] = (
    # Ojo: en el formulario real este es un textbox libre, no un campo de
    # nombre estructurado. Por eso es "texto" y no "nombre".
    Campo(3, "politicas_de_servicio__nombre_completo", "texto", "Quien firma las politicas."),
    Campo(4, "politicas_de_servicio__firma", "firma", "Firma de las politicas de servicio."),
    Campo(5, "politicas_de_servicio__manifiesto", "texto", "Texto del manifiesto de conformidad."),
    Campo(9, "acepta_reglamento", "si_no", "Si acepto el reglamento."),
    Campo(12, "fechayhora_llenado", "fecha_hora", "Cuando se lleno el formulario."),
    # Alumno
    Campo(15, "alumno__nombre_completo", "nombre", "Nombre del alumno."),
    Campo(16, "alumno__fecha_nacimiento", "fecha", "Fecha de nacimiento del alumno."),
    Campo(17, "alumno__edad", "texto", "Edad calculada por el formulario."),
    Campo(18, "alumno__domicilio", "domicilio", "Domicilio del alumno."),
    Campo(19, "alumno__telefono", "telefono", "Telefono del alumno."),
    Campo(20, "alumno__correo", "texto", "Correo del alumno."),
    # Tutor
    Campo(22, "tutor__nombre_completo", "nombre", "Nombre del tutor."),
    Campo(23, "tutor__fecha_nacimiento", "fecha", "Fecha de nacimiento del tutor."),
    Campo(24, "tutor__domicilio", "domicilio", "Domicilio del tutor."),
    Campo(25, "tutor__telefono", "telefono", "Telefono del tutor."),
    Campo(26, "tutor__correo", "texto", "Correo del tutor."),
    Campo(28, "documento_path", "archivo", "Identificacion subida por el tutor."),
    Campo(29, "comprobante_domicilio", "archivo", "Comprobante de domicilio (no mayor a 3 meses)."),
    # Contacto de emergencia
    Campo(32, "emergencia__nombre_completo", "nombre", "Contacto de emergencia."),
    Campo(33, "emergencia__fecha_nacimiento", "fecha", "Fecha de nacimiento del contacto."),
    Campo(34, "emergencia__domicilio", "domicilio", "Domicilio del contacto de emergencia."),
    Campo(35, "emergencia__telefono", "telefono", "Telefono del contacto de emergencia."),
    Campo(36, "emergencia__correo", "texto", "Correo del contacto de emergencia."),
    # Quien mas puede recoger al alumno
    Campo(39, "recojer_adicional", "texto", "Si autoriza a otras personas a recoger."),
    Campo(40, "recojer1__nombre_completo", "nombre", "Primera persona autorizada a recoger."),
    Campo(41, "recojer1__fecha_nacimiento", "fecha", "Fecha de nacimiento."),
    Campo(42, "recojer1__domicilio", "domicilio", "Domicilio."),
    Campo(43, "recojer1__telefono", "telefono", "Telefono."),
    Campo(44, "recojer1__correo", "texto", "Correo."),
    Campo(45, "recojer1__id_oficial", "archivo", "Identificacion oficial."),
    Campo(46, "recojer2__nombre_completo", "nombre", "Segunda persona autorizada a recoger."),
    Campo(47, "recojer2__fecha_nacimiento", "fecha", "Fecha de nacimiento."),
    Campo(48, "recojer2__domicilio", "domicilio", "Domicilio."),
    Campo(49, "recojer2__telefono", "telefono", "Telefono."),
    Campo(50, "recojer2__correo", "texto", "Correo."),
    Campo(51, "recojer2__id_oficial", "archivo", "Identificacion oficial."),
    # Informacion de la escuela
    Campo(54, "instrumentos", "opciones", "Instrumentos elegidos, separados por |."),
    Campo(55, "pda", "texto", "Programa de desarrollo artistico."),
    Campo(56, "horario", "horario", "Matriz de disponibilidad por dia y hora."),
    # Consentimientos
    Campo(59, "aviso_de_privacidad", "si_no", "Si acepto el aviso de privacidad."),
    Campo(67, "uso_imagen__autorizo_mayor", "si_no", "Autoriza uso de imagen (mayor de edad)."),
    Campo(68, "uso_imagen__autorizo_menor", "si_no", "Autoriza uso de imagen (menor de edad)."),
    # 70 y 71 son dos campos distintos, no uno. Se confirmo con los datos
    # reales: los 55 envios que llenan el 70 son todos mayores de edad y
    # marcan "autorizo_mayor"; los 59 que llenan el 71 son todos menores y
    # marcan "autorizo_menor". El notebook tenia la llave 71 repetida y por
    # eso perdia el 70 completo.
    Campo(70, "uso_imagen__nombre_completo_alumno", "nombre",
          "Alumno mayor de edad que firma por si mismo el uso de imagen."),
    Campo(71, "uso_imagen__nombre_completo_tutor", "nombre",
          "Tutor que firma el uso de imagen de un menor."),
    Campo(72, "uso_imagen__firma", "firma", "Firma del uso de imagen."),
    Campo(73, "uso_imagen__no_autorizo_mayor", "si_no", "NO autoriza uso de imagen (mayor)."),
    Campo(74, "uso_imagen__no_autorizo_menor", "si_no", "NO autoriza uso de imagen (menor)."),
)

# Datos que no vienen de una pregunta sino del envio mismo.
COLUMNAS_META: tuple[Column, ...] = (
    Column("form__submission_id", "string", "Id del envio en Jotform. Es la llave.", unique=True),
    Column("form__id", "string", "Id del formulario.", required=False),
    Column("form__ip", "string", "IP desde donde se envio.", required=False),
    Column("form__created_at", "datetime", "Cuando lo registro Jotform.", required=False),
    Column(
        "form__status",
        "string",
        "Estado en Jotform. Solo ACTIVE cuenta como envio vigente.",
        required=False,
    ),
)


def columnas_campo(campo: Campo) -> list[Column]:
    """Las columnas de la tabla que produce un campo del formulario."""
    if campo.tipo in PARTES:
        cols = [
            Column(f"{campo.nombre}___{parte}", "string", campo.descripcion, required=False)
            for parte in PARTES[campo.tipo]
        ]
        cols.append(
            Column(
                f"{campo.nombre}___txt",
                "string",
                f"{campo.descripcion} Todas las partes juntas.",
                required=False,
            )
        )
        return cols

    if campo.tipo == "horario":
        return [
            Column(
                f"{campo.nombre}___{dia}",
                "string",
                f"Horas marcadas el dia {dia}, separadas por |.",
                required=False,
            )
            for dia in DIAS_HORARIO
        ]

    dtype = {"fecha": "date", "fecha_hora": "datetime", "si_no": "bool"}.get(campo.tipo, "string")
    return [Column(campo.nombre, dtype, campo.descripcion, required=False)]


def columnas_tabla() -> tuple[Column, ...]:
    """Todas las columnas de `respuestas_inscripcion`, derivadas de `CAMPOS`.

    Se generan en vez de escribirse a mano: son mas de cien y mantenerlas
    sincronizadas con el formulario a pulso seria cuestion de tiempo.
    """
    columnas: list[Column] = []
    for campo in CAMPOS:
        columnas.extend(columnas_campo(campo))
    columnas.extend(COLUMNAS_META)
    return tuple(columnas)


# --- Aplanado de una respuesta -----------------------------------------


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _juntar(partes: list[str | None]) -> str | None:
    llenas = [p for p in partes if p]
    return " ".join(llenas) if llenas else None


def _fecha(valor: Any, con_hora: bool) -> date | datetime | None:
    """Jotform manda las fechas como diccionario de piezas."""
    if not isinstance(valor, dict):
        return None
    # Si trae la fecha ya armada, se usa: evita adivinar con AM/PM.
    completa = valor.get("datetime")
    if completa:
        try:
            momento = datetime.strptime(str(completa).strip(), "%Y-%m-%d %H:%M:%S")
            return momento if con_hora else momento.date()
        except ValueError:
            pass
    anio, mes, dia = valor.get("year"), valor.get("month"), valor.get("day")
    if not (anio and mes and dia):
        return None
    try:
        dia_solo = date(int(anio), int(mes), int(dia))
        if not con_hora:
            return dia_solo
        return datetime(dia_solo.year, dia_solo.month, dia_solo.day,
                        int(valor.get("hour") or 0), int(valor.get("min") or 0))
    except (TypeError, ValueError):
        return None


def _horario(respuesta: dict | None) -> tuple[dict[str, str | None], list[str]]:
    """Convierte la matriz de disponibilidad en una columna por dia.

    La matriz trae los dias como columnas y las horas como renglones; una celda
    no vacia significa "puedo a esa hora ese dia".
    """
    resultado: dict[str, str | None] = {dia: None for dia in DIAS_HORARIO}
    avisos: list[str] = []
    if not respuesta:
        return resultado, avisos

    valor = respuesta.get("answer")
    columnas = [c.strip() for c in str(respuesta.get("mcolumns") or "").split("|") if c.strip()]
    renglones = [r.strip() for r in str(respuesta.get("mrows") or "").split("|") if r.strip()]
    if not (isinstance(valor, list) and columnas and renglones):
        return resultado, avisos

    for j, dia in enumerate(columnas):
        marcadas = [
            renglones[i]
            for i, fila in enumerate(valor)
            if i < len(renglones)
            and isinstance(fila, (list, tuple))
            and j < len(fila)
            and str(fila[j]).strip()
        ]
        if dia not in resultado:
            avisos.append(
                f"El horario trae el dia '{dia}', que no esta en DIAS_HORARIO "
                f"({', '.join(DIAS_HORARIO)}). Esa columna se esta perdiendo."
            )
            continue
        resultado[dia] = "|".join(marcadas) or None
    return resultado, avisos


def _aplanar_campo(campo: Campo, respuesta: dict | None) -> tuple[dict[str, Any], list[str]]:
    valor = respuesta.get("answer") if respuesta else None
    avisos: list[str] = []

    if campo.tipo == "horario":
        horario, avisos = _horario(respuesta)
        return {f"{campo.nombre}___{dia}": val for dia, val in horario.items()}, avisos

    if campo.tipo in PARTES:
        llaves_jotform = {
            "nombre": ("first", "middle", "last"),
            "domicilio": ("addr_line1", "addr_line2", "city", "state", "postal"),
            "telefono": ("area", "phone"),
        }[campo.tipo]
        partes = PARTES[campo.tipo]
        fila: dict[str, Any] = {}
        valores: list[str | None] = []
        for parte, llave in zip(partes, llaves_jotform, strict=True):
            texto = _texto(valor.get(llave)) if isinstance(valor, dict) else None
            fila[f"{campo.nombre}___{parte}"] = texto
            valores.append(texto)
        fila[f"{campo.nombre}___txt"] = _juntar(valores)
        return fila, avisos

    if campo.tipo in ("fecha", "fecha_hora"):
        return {campo.nombre: _fecha(valor, con_hora=campo.tipo == "fecha_hora")}, avisos

    if campo.tipo == "si_no":
        # Una casilla marcada llega como lista con un elemento; sin marcar,
        # como lista vacia o ausente.
        return {campo.nombre: bool(valor) if valor is not None else None}, avisos

    if campo.tipo in ("opciones", "archivo"):
        if isinstance(valor, list):
            juntos = "|".join(_texto(v) or "" for v in valor if _texto(v))
            return {campo.nombre: juntos or None}, avisos
        return {campo.nombre: _texto(valor)}, avisos

    return {campo.nombre: _texto(valor)}, avisos


def _por_orden(submission: dict) -> dict[int, dict]:
    indice: dict[int, dict] = {}
    for respuesta in (submission.get("answers") or {}).values():
        if not isinstance(respuesta, dict):
            continue
        try:
            indice[int(respuesta["order"])] = respuesta
        except (KeyError, TypeError, ValueError):
            continue
    return indice


def aplanar(submissions: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """Convierte los envios crudos de Jotform en una tabla.

    Devuelve la tabla y la lista de avisos (cosas raras que conviene mirar,
    pero que no justifican tirar todo el proceso).
    """
    filas: list[dict[str, Any]] = []
    avisos: list[str] = []

    for submission in submissions:
        indice = _por_orden(submission)
        fila: dict[str, Any] = {}
        for campo in CAMPOS:
            valores, avisos_campo = _aplanar_campo(campo, indice.get(campo.orden))
            fila.update(valores)
            avisos.extend(avisos_campo)

        fila["form__submission_id"] = _texto(submission.get("id"))
        fila["form__id"] = _texto(submission.get("form_id"))
        fila["form__ip"] = _texto(submission.get("ip"))
        fila["form__status"] = _texto(submission.get("status"))
        creado = _texto(submission.get("created_at"))
        fila["form__created_at"] = pd.to_datetime(creado, errors="coerce") if creado else None
        filas.append(fila)

    columnas = [c.name for c in columnas_tabla()]
    df = pd.DataFrame(filas, columns=columnas) if filas else pd.DataFrame(columns=columnas)
    return df, sorted(set(avisos))


def revisar_mapeo(submissions: list[dict]) -> list[str]:
    """Avisa si el formulario dejo de cuadrar con `CAMPOS`.

    El mapeo va por numero de orden. Si alguien mueve un campo en Jotform, los
    datos empiezan a caer en la columna equivocada sin ningun error. Esto es lo
    unico que lo detecta.
    """
    if not submissions:
        return []

    avisos: list[str] = []
    esperados = {campo.orden for campo in CAMPOS}
    vistos: set[int] = set()
    for submission in submissions:
        vistos |= set(_por_orden(submission))

    faltantes = sorted(esperados - vistos)
    if faltantes:
        nombres = ", ".join(
            f"{c.orden} ({c.nombre})" for c in CAMPOS if c.orden in faltantes
        )
        avisos.append(
            f"Estos campos no llegaron en ningun envio: {nombres}. "
            "O se quitaron del formulario, o se movieron de lugar."
        )

    # Un campo de nombre que llega como texto plano suele ser la senal de que
    # los ordenes se recorrieron.
    for submission in submissions[:20]:
        indice = _por_orden(submission)
        for campo in CAMPOS:
            respuesta = indice.get(campo.orden)
            if not respuesta:
                continue
            tipo_control = respuesta.get("type", "")
            esperado = {
                "nombre": "control_fullname",
                "domicilio": "control_address",
                "telefono": "control_phone",
                "fecha": "control_datetime",
                "fecha_hora": "control_datetime",
                "horario": "control_matrix",
            }.get(campo.tipo)
            if esperado and tipo_control and tipo_control != esperado:
                avisos.append(
                    f"El campo {campo.orden} ({campo.nombre}) deberia ser {esperado} "
                    f"pero llego como {tipo_control}. Revisar el formulario: "
                    "es probable que los ordenes se hayan recorrido."
                )
    return sorted(set(avisos))


# --- Bajar de la API ---------------------------------------------------


def descargar(
    api_key: str,
    form_id: str,
    *,
    limite_por_pagina: int = LIMITE_POR_PAGINA,
    sesion: Any = None,
) -> list[dict]:
    """Baja TODOS los envios del formulario, paginando hasta que se acaben.

    Se bajan todos y no solo los nuevos a proposito: asi tambien se detectan
    los envios que alguien edito o borro en Jotform despues de mandarlos.
    A escala de cientos de registros es barato.
    """
    import requests

    http = sesion or requests
    envios: list[dict] = []
    offset = 0

    while True:
        respuesta = http.get(
            f"{BASE_URL}/form/{form_id}/submissions",
            params={"apiKey": api_key, "limit": limite_por_pagina, "offset": offset},
            timeout=60,
        )
        respuesta.raise_for_status()
        pagina = respuesta.json().get("content") or []
        envios.extend(pagina)
        if len(pagina) < limite_por_pagina:
            break
        offset += limite_por_pagina

    return envios


TABLA = "respuestas_inscripcion"


@dataclass
class ResultadoIngesta:
    """Que paso en una corrida. Son conteos, nunca datos de personas."""

    descargados: int
    nuevos: int
    cambiados: int
    actualizados: int
    archivo_raw: Path | None
    avisos: list[str]
    escribio: bool

    def resumen(self) -> str:
        if not self.escribio:
            return f"{self.descargados} envio(s) en Jotform, ninguno nuevo. No se toco la tabla."
        partes = [f"{self.nuevos} envio(s) nuevo(s) agregado(s)"]
        if self.actualizados:
            partes.append(f"{self.actualizados} actualizado(s)")
        return ", ".join(partes) + f" (de {self.descargados} en Jotform)."


def _columnas_comparables() -> list[str]:
    """Las columnas de datos, sin las de rastro (que cambian en cada corrida)."""
    return [c.name for c in columnas_tabla()]


def ingestar(
    *,
    api_key: str | None = None,
    form_id: str | None = None,
    actualizar: bool = False,
    envios: list[dict] | None = None,
    guardar_crudo: bool = True,
) -> ResultadoIngesta:
    """Baja lo que hay en Jotform y agrega a la tabla solo lo que no estaba.

    Si no hay nada nuevo, no se escribe el archivo. Reescribirlo sin cambios
    solo ensucia el historial y la fecha de modificacion.

    `envios` permite pasar los datos ya descargados (lo usan las pruebas).
    """
    from lisart import io
    from lisart.config import secreto
    from lisart.ids import ahora

    if envios is None:
        api_key = api_key or secreto("JOTFORM_API_KEY")
        form_id = form_id or secreto("JOTFORM_FORM_ID")
        envios = descargar(api_key, form_id)

    archivo_raw = guardar_raw(envios, form_id or "desconocido") if guardar_crudo else None

    avisos = revisar_mapeo(envios)
    entrantes, avisos_aplanado = aplanar(envios)
    avisos = sorted(set(avisos + avisos_aplanado))

    momento = ahora()
    entrantes["creado_en"] = momento
    entrantes["actualizado_en"] = momento
    entrantes["fuente"] = "jotform"

    actuales = io.read_table(TABLA, strict=False)
    ids_actuales = set(actuales["form__submission_id"].dropna().astype(str))

    llegando = entrantes["form__submission_id"].astype(str)
    filas_nuevas = entrantes[~llegando.isin(ids_actuales)].copy()

    # Envios que ya estaban pero cambiaron en Jotform (una edicion, o un
    # borrado que cambia el status). Se reportan siempre; solo se reescriben
    # si se pide, porque la instruccion normal es unicamente agregar.
    cambiados = _detectar_cambios(actuales, entrantes)

    escribio = False
    actualizados = 0
    if len(filas_nuevas) or (actualizar and len(cambiados)):
        resultado = actuales
        if actualizar and len(cambiados):
            ids_cambiados = set(cambiados["form__submission_id"].astype(str))
            conservadas = resultado[
                ~resultado["form__submission_id"].astype(str).isin(ids_cambiados)
            ]
            resultado = pd.concat([conservadas, cambiados], ignore_index=True)
            actualizados = len(cambiados)
        if len(filas_nuevas):
            resultado = pd.concat([resultado, filas_nuevas], ignore_index=True)
        io.write_table(TABLA, resultado)
        escribio = True

    return ResultadoIngesta(
        descargados=len(envios),
        nuevos=len(filas_nuevas),
        cambiados=len(cambiados),
        actualizados=actualizados,
        archivo_raw=archivo_raw,
        avisos=avisos,
        escribio=escribio,
    )


def leer_raw(carpeta: Path | None = None) -> list[dict]:
    """Junta todos los envios guardados en `data/raw/jotform/`.

    Si un envio aparece en varias descargas, gana el de la descarga mas
    reciente (los archivos van con la fecha en el nombre).
    """
    from lisart.config import layer_dir

    origen = carpeta or (layer_dir("raw") / "jotform")
    por_id: dict[str, dict] = {}
    for archivo in sorted(origen.glob("submissions_*.json")):
        for envio in json.loads(archivo.read_text(encoding="utf-8")):
            if envio.get("id"):
                por_id[str(envio["id"])] = envio
    return list(por_id.values())


def reconstruir_desde_raw(carpeta: Path | None = None) -> ResultadoIngesta:
    """Rehace la tabla completa desde los JSON crudos, sin tocar la API.

    Es la razon de ser de la capa `raw`: cuando se corrige como se interpreta
    un campo, no hace falta volver a pedirle nada a Jotform. Se vuelve a leer
    lo que ya se tenia guardado y se reinterpreta.

    Conserva el `creado_en` de las filas que ya existian: la fila no se creo
    de nuevo, solo se volvio a leer.
    """
    from lisart import io
    from lisart.ids import ahora

    envios = leer_raw(carpeta)
    avisos = revisar_mapeo(envios)
    entrantes, avisos_aplanado = aplanar(envios)
    avisos = sorted(set(avisos + avisos_aplanado))

    momento = ahora()
    entrantes["actualizado_en"] = momento
    entrantes["fuente"] = "jotform"

    anteriores = io.read_table(TABLA, strict=False)
    if len(anteriores):
        nacimiento = anteriores.set_index(anteriores["form__submission_id"].astype(str))
        creado = entrantes["form__submission_id"].astype(str).map(nacimiento["creado_en"])
        creado = pd.to_datetime(creado).fillna(pd.Timestamp(momento))
    else:
        creado = pd.Series([momento] * len(entrantes), index=entrantes.index)
    entrantes["creado_en"] = creado

    io.write_table(TABLA, entrantes)
    return ResultadoIngesta(
        descargados=len(envios),
        nuevos=len(entrantes),
        cambiados=0,
        actualizados=0,
        archivo_raw=None,
        avisos=avisos,
        escribio=True,
    )


def _detectar_cambios(actuales: pd.DataFrame, entrantes: pd.DataFrame) -> pd.DataFrame:
    """Filas que ya existian y ahora llegan distintas.

    La comparacion se hace sobre el texto que se escribiria en el CSV, para no
    confundir un cambio real con una diferencia de tipos de pandas.
    """
    from lisart import io

    if actuales.empty or entrantes.empty:
        return entrantes.iloc[0:0]

    columnas = _columnas_comparables()
    viejo = io.format_for_csv(TABLA, actuales)
    viejo = viejo.set_index(actuales["form__submission_id"].astype(str))
    nuevo = io.format_for_csv(TABLA, entrantes)
    nuevo = nuevo.set_index(entrantes["form__submission_id"].astype(str))

    comunes = viejo.index.intersection(nuevo.index)
    if not len(comunes):
        return entrantes.iloc[0:0]

    izq = viejo.loc[comunes, columnas].fillna("")
    der = nuevo.loc[comunes, columnas].fillna("")
    distintos = comunes[(izq != der).any(axis=1)]
    return entrantes[entrantes["form__submission_id"].astype(str).isin(set(distintos))]


def guardar_raw(envios: list[dict], form_id: str, carpeta: Path | None = None) -> Path:
    """Guarda la descarga tal cual en `data/raw/jotform/`.

    Se guarda siempre, aunque no haya nada nuevo. `raw` es la unica copia que
    no depende de que Jotform siga existiendo ni de que nadie borre un envio.
    """
    from lisart.config import layer_dir

    destino = carpeta or (layer_dir("raw") / "jotform")
    destino.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%dT%H%M%S")
    archivo = destino / f"submissions_{form_id}_{sello}.json"
    archivo.write_text(
        json.dumps(envios, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return archivo
