"""La proyección en el formato en que la escuela ya la lleva.

`proyeccion.py` calcula cuánto debería entrar. Este módulo lo escribe en el
Excel mensual que la escuela usa hoy (los ejemplos están en `data/examples/`),
para que quien lo recibe no tenga que reaprender nada: mismas 38 columnas, en
el mismo orden, con la fila de totales arriba y los mismos grupos de encabezado.

    lisart proyeccion --excel

Por qué copiar un formato ajeno
-------------------------------
Un reporte nuevo obliga a la administración a cambiar su manera de trabajar
antes de ver un solo beneficio. Copiando el formato, el sistema entra por donde
ya hay costumbre: el archivo se abre igual, se filtra igual y las columnas de
cobranza siguen ahí para llenarse a mano mientras no exista el mecanismo que
las llene solas.

Los dos ejemplos NO son iguales entre sí
----------------------------------------
Mayo trae `CH` y `MDP`; septiembre trae `Columna2`, `FDP` y `NOTAS2`. O sea que
el formato se mueve de un mes a otro. Se tomó **el de mayo**, que es el que
venía con datos, y es el que está reproducido aquí.

Lo que se llena y lo que no
---------------------------
Se llena lo que hoy es un hecho: quién es el alumno, su programa, su precio,
qué firmó y qué instrumento toca. **Se deja en blanco todo lo que sería
inventarlo** — la cobranza (`PAGADO`, `FECHA DE PAGO`, `MDP`), los comprobantes,
el registro en Kydemy y el horario de su clase. Un espacio vacío se llena; una
cifra inventada se cree. La lista completa, con su razón, está en `SIN_DATO`.

Las columnas de dinero van como **fórmula**, no como número, igual que en el
original: si la administración cambia un descuento, el archivo se recalcula
solo en vez de mentir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from lisart import io
from lisart.config import layer_dir
from lisart.ids import sin_acentos
from lisart.procesos.proyeccion import Proyeccion

# --- El formato ---------------------------------------------------------

MONEDA = '_-"$"* #,##0.00_-;\\-"$"* #,##0.00_-;_-"$"* "-"??_-;_-@_-'
FECHA = "dd/mm/yyyy"
HORA = "hh:mm"
PORCENTAJE = "0.00%"


@dataclass(frozen=True)
class Columna:
    """Una columna del formato de la escuela.

    `clave` es interna (el título se repite: hay dos `ARCHIVADO`). `titulo` es
    literalmente lo que dice el encabezado en el archivo de la escuela y no se
    corrige aunque traiga erratas: cambiarlo rompería la costumbre de quien lo
    lee.
    """

    clave: str
    titulo: str
    ancho: float
    formato: str = "General"
    grupo: str | None = None  # el encabezado de arriba, si pertenece a uno


COLUMNAS: tuple[Columna, ...] = (
    Columna("ch", "CH", 5.8),
    Columna("codigo", "CÓDIGO", 17.5),
    Columna("alumno", "ALUMNO", 53.5),
    Columna("rfc", "RFC", 10.8),
    Columna("status", "STATUS", 18.3),
    Columna("pda", "PDA", 48.3),
    Columna("precio", "PRECIO", 18.8, MONEDA),
    Columna("descuento", "DESCUENTO", 21.5),
    Columna("porcentaje", "%", 10.8, PORCENTAJE),
    Columna("descuento_pesos", "DESCUENTO EN $", 19.5, MONEDA),
    Columna("pago_ddd", "PAGO d.d.D.", 17.5, MONEDA),
    Columna("inscripcion", "INSCRIPCIÓN", 15.5, MONEDA),
    Columna("recargos", "RECARGOS", 14.0, MONEDA),
    Columna("a_favor", "A FAVOR", 12.8, MONEDA),
    Columna("en_contra", "EN CONTRA", 14.3, MONEDA),
    Columna("pago_real", "PAGO REAL", 18.8, MONEDA),
    Columna("pagado", "PAGADO", 12.3),
    Columna("fecha_pago", "FECHA DE PAGO", 17.2, FECHA),
    Columna("mdp", "MDP", 30.0),
    Columna("recibido", "RECIBIDO", 14.7, grupo="CDT / CDC / TDP"),
    Columna("qr", "QR", 14.7, grupo="CDT / CDC / TDP"),
    Columna("archivado_1", "ARCHIVADO", 16.8, grupo="CDT / CDC / TDP"),
    Columna("qa", "QA", 16.8, grupo="CDT / CDC / TDP"),
    Columna("hecho", "HECHO", 12.2, grupo="COMPROBANTE DE PAGO"),
    Columna("qh", "QH", 12.2, grupo="COMPROBANTE DE PAGO"),
    Columna("archivado_2", "ARCHIVADO", 14.0, grupo="COMPROBANTE DE PAGO"),
    Columna("qa2", "QA2", 16.3, grupo="COMPROBANTE DE PAGO"),
    Columna("debe_pagar", "Debe pagar?", 16.3, grupo="INSCRIPCIÓN 2025"),
    Columna("fecha_inscripcion", "Columna1", 18.2, FECHA, grupo="Fecha de inscripción"),
    Columna("politicas", "POLITICAS", 14.5, grupo="ACADÉMICO"),
    Columna("firma", "FIRMA INSC 2025", 18.3, grupo="ACADÉMICO"),
    Columna("cancelacion_1", "cancelacion 1", 14.8, grupo="KYDEMY"),
    Columna("cancelacion_2", "cancelacion 2", 38.5, grupo="KYDEMY"),
    Columna("registro", "REGISTRO", 21.0, grupo="KYDEMY"),
    Columna("sesion", "SESIÓN", 15.7),
    Columna("horario", "HORARIO", 26.5, HORA),
    Columna("liga_enviada", "LIGA ENVIADA", 38.5),
    Columna("notas", "NOTAS", 38.5),
)

# Columnas que hoy se dejan VACÍAS a propósito, y por qué. Esto no es
# documentación decorativa: `lisart proyeccion --excel` lo imprime, para que
# nadie crea que el archivo salió incompleto por un error.
SIN_DATO: dict[str, str] = {
    "CH": "marca de revisión, la pone a mano quien cobra",
    "RFC": "si el alumno pide factura; no se pregunta en el formulario",
    "PAGADO": "es la cobranza, y ese mecanismo todavía no existe",
    "FECHA DE PAGO": "ídem",
    "MDP": "medio de pago; ídem",
    "RECIBIDO": "control de comprobantes; ídem (y sus QR/QA)",
    "HECHO": "comprobante de pago; ídem (y sus QH/QA2)",
    "Debe pagar?": "el cobro de inscripción anual no está modelado",
    "cancelacion 1": "viene de Kydemy, que aún no se conecta",
    "REGISTRO": "el registro en Kydemy; ídem",
    "HORARIO": "es la hora de la clase asignada, no la que el alumno declaró "
    "en el formulario; llenarla con la declarada sería falsear el dato",
    "LIGA ENVIADA": "pertenece a la mensajería, otro de los proyectos",
}

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)

# Renglones fijos del archivo. La escuela pone los totales ARRIBA de la tabla,
# no abajo: se abre el archivo y lo primero que se ve es el número.
FILA_TITULO = 2
FILA_PENDIENTE = 3
FILA_PROMEDIO = 6
FILA_GRUPOS = 7
FILA_ENCABEZADO = 8
FILA_DATOS = 9

# Partículas que el código de alumno se salta: "Vivanco de La Rosa" -> VIRO.
PARTICULAS = {"de", "del", "la", "las", "los", "y", "san"}


def codigo_de_alumno(nombre_escuela: str, modalidad: str | None = None) -> str:
    """El código con el que la escuela identifica a un alumno: `PR-VIROMAES`.

    Dos letras por palabra del nombre —apellidos primero, como lo escribe la
    escuela—, saltándose las partículas, con el prefijo de la modalidad:
    `PR` presencial, `EL` en línea.

    La regla no estaba escrita en ningún lado: se dedujo de los ejemplos y se
    verificó contra los cinco casos que traían código. Si algún día la escuela
    genera uno que no coincide, es aquí donde se ajusta.
    """
    presencial = not (modalidad or "").lower().startswith(("en linea", "en línea"))
    palabras = [
        palabra
        for palabra in sin_acentos(nombre_escuela).split()
        if palabra.lower() not in PARTICULAS
    ]
    return ("PR-" if presencial else "EL-") + "".join(p[:2].upper() for p in palabras)


# --- Armar los renglones ------------------------------------------------


def _nombre_escuela(persona: pd.Series) -> str:
    """Apellidos primero, como lo escribe la escuela: `Alcaraz Solis Renata`."""
    partes = [
        persona.get("apellido_paterno"),
        persona.get("apellido_materno"),
        persona.get("nombre"),
    ]
    return " ".join(
        str(p).strip() for p in partes if p is not None and not pd.isna(p) and str(p).strip()
    )


def _pda(programa: pd.Series | None) -> str:
    """El texto de la columna PDA: `Presencial / ESENCIAL`."""
    if programa is None:
        return ""
    modalidad = str(programa.get("modalidad") or "").strip().capitalize()
    arquetipo = programa.get("arquetipo")
    if arquetipo is None or pd.isna(arquetipo):
        cola = str(programa.get("nombre") or "").strip()
    else:
        cola = str(arquetipo).strip()
    return f"{modalidad} / {cola.upper()}".strip(" /")


def _fecha(valor):
    """Excel guarda fechas, no textos. Lo que no sea fecha se va en blanco."""
    if valor is None or (not isinstance(valor, (date, datetime)) and pd.isna(valor)):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    return valor if isinstance(valor, date) else None


def _contexto() -> dict[str, dict]:
    """Todo lo que hace falta de otras tablas, en diccionarios por persona."""
    personas = io.read_table("personas")
    alumnos = io.read_table("alumnos")
    programas = io.read_table("programas")

    # Instrumentos: la columna SESIÓN de la escuela dice "Violin/ Viernes".
    # Aquí solo va el instrumento; el día es de la clase asignada, que no hay.
    nombres_instrumento = dict(
        zip(
            io.read_table("instrumentos")["instrumento_id"].astype(str),
            io.read_table("instrumentos")["nombre"].astype(str),
            strict=False,
        )
    )
    por_alumno: dict[str, list[str]] = {}
    for _, fila in io.read_table("alumnos_instrumentos").iterrows():
        clave = str(fila["persona_id"])
        instrumento = nombres_instrumento.get(str(fila["instrumento_id"]))
        if instrumento:
            por_alumno.setdefault(clave, []).append(instrumento)

    return {
        "personas": {str(f["persona_id"]): f for _, f in personas.iterrows()},
        "alumnos": {str(f["persona_id"]): f for _, f in alumnos.iterrows()},
        "programas": {str(f["programa_id"]): f for _, f in programas.iterrows()},
        "instrumentos": por_alumno,
        "firmas": _firmas(),
    }


def _firmas() -> dict[str, tuple[bool, bool]]:
    """(aceptó políticas, firmó) por persona, sacado del formulario.

    El puente es `identificadores_externos`: el envío de Jotform trae varias
    personas (alumno, tutor, emergencia) y el sufijo `#alumno` dice cuál de
    ellas es el alumno. Cruzar por nombre aquí sería volver a inventar el
    problema que esa tabla resuelve.
    """
    respuestas = io.read_table("respuestas_inscripcion", strict=False)
    if respuestas.empty:
        return {}

    del_alumno = {
        str(fila["id_externo"]).split("#")[0]: str(fila["persona_id"])
        for _, fila in io.read_table("identificadores_externos").iterrows()
        if str(fila["sistema"]) == "jotform" and str(fila["id_externo"]).endswith("#alumno")
    }

    def verdadero(valor) -> bool:
        return not pd.isna(valor) and str(valor).strip().lower() in ("true", "si", "sí", "1")

    firmas: dict[str, tuple[bool, bool]] = {}
    for _, fila in respuestas.iterrows():
        persona_id = del_alumno.get(str(fila["form__submission_id"]))
        if persona_id is None:
            continue
        firmas[persona_id] = (
            verdadero(fila.get("acepta_reglamento")),
            bool(fila.get("politicas_de_servicio__firma"))
            and not pd.isna(fila.get("politicas_de_servicio__firma")),
        )
    return firmas


def renglones(proyeccion: Proyeccion) -> list[dict]:
    """Un renglón por alumno, con las claves de `COLUMNAS`.

    **Van todos los alumnos**, también los que no tienen precio en el catálogo:
    el archivo de la escuela es su padrón, y desaparecer a 17 personas porque
    les falta un dato haría que el faltante pase inadvertido. Salen con PRECIO
    vacío y el motivo escrito en NOTAS.
    """
    ctx = _contexto()
    filas: list[dict] = []

    conocidos = proyeccion.detalle.to_dict("records") if len(proyeccion.detalle) else []
    faltantes = proyeccion.sin_precio.to_dict("records") if len(proyeccion.sin_precio) else []

    for registro in (*conocidos, *faltantes):
        persona_id = str(registro["persona_id"])
        persona = ctx["personas"].get(persona_id)
        if persona is None:
            continue
        alumno = ctx["alumnos"].get(persona_id)
        programa = ctx["programas"].get(str(registro.get("programa_id") or ""))
        acepto, firmo = ctx["firmas"].get(persona_id, (False, False))

        nombre = _nombre_escuela(persona)
        estatus = str(alumno["estatus"]).upper() if alumno is not None else ""
        nota = registro.get("motivo") or (
            "" if alumno is None or pd.isna(alumno.get("notas")) else str(alumno["notas"])
        )

        filas.append({
            "codigo": codigo_de_alumno(
                nombre, None if programa is None else programa.get("modalidad")
            ),
            "alumno": nombre,
            "status": "ACTIVO" if estatus == "INSCRITO" else estatus,
            "pda": _pda(programa),
            "precio": registro.get("precio_lista"),
            # La escuela escribe "No" cuando no hay descuento; se respeta. El
            # porcentaje va como fracción porque la celda tiene formato de
            # porcentaje: 0.05 se ve como 5.00%.
            "descuento": registro.get("descuento") or "No",
            "porcentaje": float(registro.get("descuento_pct") or 0) / 100,
            "inscripcion": 0,
            "recargos": 0,
            "a_favor": 0,
            "en_contra": 0,
            "fecha_inscripcion": _fecha(None if alumno is None else alumno.get("fecha_alta")),
            "politicas": acepto,
            "firma": firmo,
            "sesion": " / ".join(sorted(ctx["instrumentos"].get(persona_id, []))),
            "notas": nota,
        })

    return sorted(filas, key=lambda f: sin_acentos(f["alumno"]).lower())


# --- Escribir el Excel --------------------------------------------------


def _mes_de(cuando: date) -> tuple[str, str]:
    """(nombre de la hoja, título): `05. Mayo 2025` / `05. MAYO 2025`."""
    etiqueta = f"{cuando.month:02d}. {MESES[cuando.month - 1]} {cuando.year}"
    return etiqueta, etiqueta.upper()


def escribir_excel(
    proyeccion: Proyeccion,
    *,
    mes: date | None = None,
    ruta: Path | None = None,
) -> Path:
    """Escribe la proyección en el Excel de la escuela y devuelve la ruta.

    Va a `data/exports/`, que es capa desechable: este archivo se regenera
    cuando se quiera y nadie debe editarlo esperando que se conserve. Si la
    administración va a llenar a mano las columnas de cobranza, que trabaje
    sobre una copia suya.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    cuando = mes or date.today()
    hoja, titulo = _mes_de(cuando)
    filas = renglones(proyeccion)

    libro = Workbook()
    ws = libro.active
    ws.title = hoja

    tinta = "1F2430"
    encabezado = PatternFill("solid", fgColor=tinta)
    grupo = PatternFill("solid", fgColor="E8E4DC")
    resumen = PatternFill("solid", fgColor="F5F2EC")
    hueco = PatternFill("solid", fgColor="FAFAF8")  # lo que hoy no se puede llenar
    hairline = Side(style="thin", color="C9C4BA")
    marco = Border(left=hairline, right=hairline, top=hairline, bottom=hairline)
    centrado = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ultima = FILA_DATOS + len(filas) - 1 if filas else FILA_DATOS
    letra = {c.clave: get_column_letter(i) for i, c in enumerate(COLUMNAS, start=1)}
    vacias = {c.titulo for c in COLUMNAS if c.titulo in SIN_DATO} | {
        "QR", "QA", "ARCHIVADO", "QH", "QA2", "cancelacion 2",
    }

    # --- Encabezado del archivo ----------------------------------------
    ws.merge_cells(
        start_row=FILA_TITULO, start_column=3, end_row=FILA_PROMEDIO, end_column=3
    )
    celda = ws.cell(FILA_TITULO, 3, f"PROYECCIÓN DE PAGO\n{titulo}")
    celda.font = Font(name="Calibri", sz=18, bold=True, color="FFFFFF")
    celda.fill = PatternFill("solid", fgColor=tinta)
    celda.alignment = centrado

    pendiente = ws.cell(FILA_TITULO, 16, "INGRESO PENDIENTE")
    pendiente.font = Font(name="Calibri", sz=12, bold=True)
    pendiente.alignment = centrado
    columna_real, columna_pagado = letra["pago_real"], letra["pagado"]
    monto = ws.cell(
        FILA_PENDIENTE,
        16,
        f'=SUMIF({columna_pagado}{FILA_DATOS}:{columna_pagado}{ultima},'
        f'"<>SI",{columna_real}{FILA_DATOS}:{columna_real}{ultima})',
    )
    monto.number_format = MONEDA
    monto.font = Font(name="Calibri", sz=14, bold=True)
    monto.alignment = centrado
    for fila in (FILA_TITULO, FILA_PENDIENTE):
        ws.cell(fila, 16).fill = resumen

    # --- Promedios y totales, arriba de la tabla -----------------------
    for indice, columna in enumerate(COLUMNAS, start=1):
        if columna.formato != MONEDA and columna.clave != "porcentaje":
            continue
        ref = f"{letra[columna.clave]}{FILA_DATOS}:{letra[columna.clave]}{ultima}"
        if columna.clave in ("precio", "descuento_pesos", "pago_ddd", "pago_real"):
            promedio = ws.cell(FILA_PROMEDIO, indice, f'=IFERROR(AVERAGEIF({ref},">0"),"")')
            promedio.number_format = columna.formato
            promedio.fill = resumen
            promedio.font = Font(name="Calibri", sz=11, italic=True)
        total = ws.cell(FILA_GRUPOS, indice, f"=SUM({ref})")
        total.number_format = columna.formato
        total.fill = grupo
        total.font = Font(name="Calibri", sz=12, bold=True)

    # --- Los grupos de encabezado (los merges de la escuela) ------------
    inicio = 0
    while inicio < len(COLUMNAS):
        actual = COLUMNAS[inicio].grupo
        fin = inicio
        while fin + 1 < len(COLUMNAS) and COLUMNAS[fin + 1].grupo == actual:
            fin += 1
        if actual:
            if fin > inicio:
                ws.merge_cells(
                    start_row=FILA_GRUPOS, start_column=inicio + 1,
                    end_row=FILA_GRUPOS, end_column=fin + 1,
                )
            celda = ws.cell(FILA_GRUPOS, inicio + 1, actual)
            celda.font = Font(name="Calibri", sz=12, bold=True)
            celda.fill = grupo
            celda.alignment = centrado
        inicio = fin + 1

    # --- Encabezado de la tabla ----------------------------------------
    for indice, columna in enumerate(COLUMNAS, start=1):
        celda = ws.cell(FILA_ENCABEZADO, indice, columna.titulo)
        celda.font = Font(name="Calibri", sz=12, bold=True, color="FFFFFF")
        celda.fill = encabezado
        celda.alignment = centrado
        celda.border = marco
        ws.column_dimensions[get_column_letter(indice)].width = columna.ancho

    # --- Los alumnos ----------------------------------------------------
    for desplazamiento, fila in enumerate(filas):
        numero = FILA_DATOS + desplazamiento
        calculadas = {
            # El descuento y el pago se recalculan solos en Excel, igual que
            # en el archivo original: el que edita un porcentaje ve el efecto.
            "descuento_pesos": f"={letra['precio']}{numero}*{letra['porcentaje']}{numero}",
            "pago_ddd": f"={letra['precio']}{numero}-{letra['descuento_pesos']}{numero}",
            "pago_real": (
                f"={letra['pago_ddd']}{numero}+{letra['inscripcion']}{numero}"
                f"+{letra['recargos']}{numero}+{letra['en_contra']}{numero}"
                f"-{letra['a_favor']}{numero}"
            ),
        }
        sin_precio = fila.get("precio") is None or pd.isna(fila.get("precio"))
        for indice, columna in enumerate(COLUMNAS, start=1):
            valor = calculadas.get(columna.clave, fila.get(columna.clave))
            if sin_precio and columna.clave in calculadas:
                valor = None  # sin precio no hay nada que calcular
            celda = ws.cell(numero, indice, valor)
            celda.number_format = columna.formato
            celda.border = marco
            celda.font = Font(name="Calibri", sz=12)
            if columna.formato in (MONEDA, FECHA, HORA) or columna.clave in (
                "status", "porcentaje", "politicas", "firma"
            ):
                celda.alignment = Alignment(horizontal="center")
            if columna.titulo in vacias:
                celda.fill = hueco

    ws.freeze_panes = f"D{FILA_DATOS}"
    ws.auto_filter.ref = (
        f"A{FILA_ENCABEZADO}:{get_column_letter(len(COLUMNAS))}{ultima}"
    )
    ws.row_dimensions[FILA_ENCABEZADO].height = 30

    destino = ruta or (layer_dir("exports") / f"proyeccion_{cuando:%Y_%m}.xlsx")
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)
    return destino
