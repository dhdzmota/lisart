"""Pantalla de Lisart: una pestaña por tabla, un registro a la vez.

Se corre con `lisart ui`.

Decisiones de diseño
--------------------
La identidad sale del logo (`assets/LisartLogo2024`), no de un tema genérico:
banda superior en el **negro exacto** del archivo para que el wordmark no se vea
como un recuadro pegado, mayúsculas espaciadas como en "ACADEMIA DE MÚSICA", y
oro y vino como acento —una línea, un filete— nunca como relleno grande.

Los iconos son SVG musicales dibujados sobre una misma retícula
(`iconos.py`), no los PNG sueltos de `assets/iconos`: mezclar ilustraciones de
estilos distintos es lo que hace que una interfaz se vea armada con recortes.

Decisiones de comportamiento
----------------------------
1. **Los campos no están escritos aquí.** Cada control se genera desde
   `tables.py`: el tipo decide el widget, `choices` se vuelve lista desplegable
   y una llave foránea se vuelve un selector de valores que sí existen.
2. **Nada se sobrescribe sin respaldo** (`data/backups/`).
3. **Lo que no se debe editar, no se puede editar:** la llave primaria, las
   marcas de tiempo, y las tablas de capa `interim`, que se regeneran solas.
"""

from __future__ import annotations

import base64
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st

from lisart import backup, io
from lisart.config import PROJECT_ROOT, ruta_corta
from lisart.procesos import roles as roles_mod
from lisart.schema import Column, Table
from lisart.tables import REGISTRY
from lisart.ui import grafo as grafo_mod
from lisart.ui import iconos
from lisart.ui import semana as semana_mod

ASSETS = PROJECT_ROOT / "assets"
LOGO_BANDA = ASSETS / "imagenes" / "lisart_wordmark.png"  # wordmark recortado a su contenido
LOGO_ICONO = ASSETS / "imagenes" / "lisart_marca.png"     # las aves sobre el pentagrama
CSS = ASSETS / "estilo.css"

VACIO = "— vacío —"
SOLO_LECTURA = {"creado_en", "actualizado_en"}

# Como se llama cada tabla en pantalla, y en que orden salen las pestañas. Una
# tabla que no este aqui sale al final y con su nombre de archivo
# (`alumnos_descuentos`), que es justo lo que esta pantalla existe para evitar.
ETIQUETAS: dict[str, str] = {
    "personas": "Personas",
    "alumnos": "Alumnos",
    "personas_roles": "Roles",
    "relaciones": "Relaciones",
    "identificadores_externos": "Identificadores",
    "alumnos_instrumentos": "Estudia",
    "respuestas_inscripcion": "Inscripciones",
    "disponibilidad": "Disponibilidad",
    "clases": "Clases",
    "clases_profesores": "Quien da clase",
    "clases_alumnos": "Quien la toma",
    "programas": "Programas",
    "descuentos": "Descuentos",
    "alumnos_descuentos": "Quien tiene descuento",
    "espacios": "Espacios",
    "instrumentos": "Instrumentos",
    "conceptos": "Conceptos",
}

# Como se llama en pantalla cada bloque de columnas.
NOMBRES_GRUPO: dict[str, str] = {
    "alumno": "Alumno",
    "tutor": "Tutor",
    "emergencia": "Contacto de emergencia",
    "recojer1": "Autorizado a recoger · 1",
    "recojer2": "Autorizado a recoger · 2",
    "politicas_de_servicio": "Políticas de servicio",
    "uso_imagen": "Uso de imagen",
    "form": "Datos del envío",
    "horario": "Horario solicitado",
}

# Las columnas se nombran sin acentos (convención de datos), pero en pantalla
# las lee gente: "TELEFONO" en una interfaz en español se ve descuidado.
CON_ACENTO: dict[str, str] = {
    "telefono": "teléfono", "codigo": "código", "direccion": "dirección",
    "relacion": "relación", "identificacion": "identificación", "numero": "número",
    "politicas": "políticas", "inscripcion": "inscripción", "id": "ID",
    "ids": "IDs", "credito": "crédito", "musica": "música",
    "area": "lada",   # así se le dice en México al código de área
    "fechayhora": "fecha y hora", "pda": "PDA",
}


ULTIMO_TRAMO = {"id": "ID"}


def _etiqueta_campo(nombre: str, grupo: str | None = None) -> str:
    """Rótulo del campo, sin repetir lo que ya dice el título del grupo.

    En la sección ALUMNO, `alumno__nombre_completo___nombre` se rotula
    "nombre": poner "ALUMNO NOMBRE COMPLETO NOMBRE" en cada campo obliga a
    leer tres palabras de relleno antes de llegar a la que distingue.
    """
    corto = nombre
    if grupo and "__" in nombre:
        corto = nombre.split("__", 1)[1]
    if "___" in corto:
        padre, ultimo = corto.rsplit("___", 1)
        # `___txt` es "todas las partes juntas": se rotula con el nombre del
        # campo padre. Rotularlo "completo" haría que en un mismo bloque
        # hubiera tres campos llamados igual (nombre, domicilio y teléfono).
        corto = padre if ultimo == "txt" else ultimo
    corto = ULTIMO_TRAMO.get(corto, corto)
    return " ".join(CON_ACENTO.get(p, p) for p in corto.lstrip("_").split("_"))


IDENTIFICACION = {"nombre", "apellido_paterno", "apellido_materno", "nombre_normalizado"}
CONTACTO = {"telefono", "correo", "domicilio"}
AUDITORIA = {"creado_en", "actualizado_en", "fuente"}


# --- Carga -------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _cargar(nombre: str, _marca: float) -> pd.DataFrame:
    """Lee una tabla. `_marca` es la fecha del archivo: cuando cambia, la caché
    se invalida sola y la pantalla ve el dato nuevo."""
    return io.read_table(nombre, strict=False)


def cargar(tabla: Table) -> pd.DataFrame:
    marca = tabla.path.stat().st_mtime if tabla.path.exists() else 0.0
    return _cargar(tabla.name, marca)


def nombres_de_personas() -> dict[str, str]:
    """persona_id -> nombre legible. Sirve para que un registro no se lea
    'PER-0042 → PER-0117' sino con nombres de gente."""
    tabla = REGISTRY.get("personas")
    if not tabla.path.exists():
        return {}
    personas = cargar(tabla)
    if personas.empty:
        return {}
    completo = (
        personas["nombre"].fillna("").astype(str)
        + " " + personas["apellido_paterno"].fillna("").astype(str)
        + " " + personas["apellido_materno"].fillna("").astype(str)
    ).str.replace(r"\s+", " ", regex=True).str.strip()
    return dict(zip(personas["persona_id"].astype(str), completo, strict=False))


@lru_cache(maxsize=4)
def _tamano(ruta: Path) -> tuple[int, int]:
    """Ancho y alto reales del PNG, leídos de su cabecera."""
    cabecera = ruta.read_bytes()[16:24]
    return int.from_bytes(cabecera[:4], "big"), int.from_bytes(cabecera[4:], "big")


@lru_cache(maxsize=4)
def _imagen_incrustada(ruta: str) -> str:
    datos = base64.b64encode(Path(ruta).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{datos}"


# --- Marco de la página ------------------------------------------------


def _estilos() -> None:
    if CSS.exists():
        st.markdown(f"<style>{CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _banda() -> None:
    marca = ""
    if LOGO_BANDA.exists():
        # width/height explícitos: sin ellos el navegador no reserva el espacio
        # y la página da un salto al cargar la imagen.
        ancho, alto = _tamano(LOGO_BANDA)
        marca = (
            f'<div class="lis-banda__marca">'
            f'<img src="{_imagen_incrustada(str(LOGO_BANDA))}" alt="Lisart"'
            f' width="{ancho}" height="{alto}"></div>'
        )
    st.markdown(
        f'<div class="lis-banda">{marca}'
        '<div class="lis-banda__texto">'
        '<p class="lis-banda__titulo">Base de datos</p>'
        '<p class="lis-banda__sub">Sistema administrativo</p>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def _seccion(titulo: str) -> None:
    st.markdown(
        f'<div class="lis-sec"><span class="lis-sec__t">{titulo}</span>'
        '<span class="lis-sec__l"></span></div>',
        unsafe_allow_html=True,
    )


# --- Agrupar los campos ------------------------------------------------


def _grupo_de(tabla: Table, columna: str) -> str:
    if columna in AUDITORIA:
        return "Registro del sistema"
    if "__" in columna:
        prefijo = columna.split("__", 1)[0]
        return NOMBRES_GRUPO.get(prefijo, prefijo.replace("_", " ").capitalize())
    if columna in tabla.primary_key or columna in IDENTIFICACION:
        return "Identificación"
    if columna in CONTACTO:
        return "Contacto"
    return "Datos"


def _agrupar(tabla: Table, columnas: list[Column]) -> list[tuple[str, list[Column]]]:
    """Parte las columnas en secciones con nombre, en un orden estable.

    Una tabla de 113 columnas puestas en fila es ilegible; en bloques con
    título —Alumno, Tutor, Contacto de emergencia— se lee como una ficha.
    """
    grupos: dict[str, list[Column]] = {}
    for col in columnas:
        grupos.setdefault(_grupo_de(tabla, col.name), []).append(col)

    primeros = ["Identificación", "Contacto", "Datos", "Alumno", "Tutor"]
    ultimos = ["Datos del envío", "Registro del sistema"]

    def orden(nombre: str) -> tuple[int, str]:
        if nombre in primeros:
            return (0, f"{primeros.index(nombre):02d}")
        if nombre in ultimos:
            return (2, f"{ultimos.index(nombre):02d}")
        return (1, nombre)

    return [(g, grupos[g]) for g in sorted(grupos, key=orden)]


# --- Titulo legible de un registro -------------------------------------


def _texto(valor) -> str:
    return "" if _es_vacio(valor) else str(valor).strip()


def _titulo_registro(tabla: Table, fila: pd.Series, nombres: dict[str, str]) -> tuple[str, str]:
    """(titulo, pie) en lenguaje de personas, no de llaves."""

    def persona(columna: str) -> str:
        pid = _texto(fila.get(columna))
        return nombres.get(pid) or pid

    if tabla.name == "personas":
        completo = " ".join(
            p for p in (_texto(fila.get("nombre")), _texto(fila.get("apellido_paterno")),
                        _texto(fila.get("apellido_materno"))) if p
        )
        tel = _texto(fila.get("telefono"))
        return completo or _texto(fila["persona_id"]), (
            f'<span class="num">{tel}</span>' if tel else ""
        )

    if tabla.name == "alumnos":
        estatus = _texto(fila.get("estatus"))
        tutor = "requiere tutor" if fila.get("requiere_tutor") is True else "mayor de edad"
        return persona("persona_id"), f"<b>{estatus}</b> · {tutor}"

    if tabla.name == "personas_roles":
        return persona("persona_id"), f"rol: <b>{_texto(fila.get('rol'))}</b>"

    if tabla.name == "relaciones":
        return (
            persona("alumno_persona_id"),
            f"{_texto(fila.get('tipo'))} → <b>{persona('relacionado_persona_id')}</b>",
        )

    if tabla.name == "identificadores_externos":
        return (
            persona("persona_id"),
            f"{_texto(fila.get('sistema'))} · <code>{_texto(fila.get('id_externo'))}</code>",
        )

    if tabla.name == "alumnos_descuentos":
        descuento = _texto(fila.get("descuento"))
        porcentaje = fila.get("porcentaje")
        pie = "sin descuento"
        if descuento:
            cuanto = f" · <span class='num'>{float(porcentaje):g}%</span>" if tiene_valor(
                porcentaje
            ) else ""
            pie = f"<b>{descuento}</b>{cuanto}"
        return _texto(fila.get("alumno")) or persona("persona_id"), pie

    if tabla.name == "respuestas_inscripcion":
        titulo = _texto(fila.get("alumno__nombre_completo___txt")) or _texto(
            fila.get("form__submission_id")
        )
        return titulo, f"envío <code>{_texto(fila.get('form__submission_id'))}</code>"

    nombre = _texto(fila.get("nombre"))
    llave = " · ".join(_texto(fila[c]) for c in tabla.primary_key)
    return nombre or llave, llave if nombre else ""


# --- Controles ---------------------------------------------------------


def tiene_valor(valor) -> bool:
    """Si la celda trae algo. NO usar `if fila["x"]` con datos de pandas.

    Una celda vacia es `pd.NA`, y evaluarla como booleano lanza
    "boolean value of NA is ambiguous" a proposito: pandas se niega a adivinar
    si un dato faltante es verdadero o falso. Hay que preguntarlo explicito.
    """
    return not _es_vacio(valor)


def _es_vacio(valor) -> bool:
    if valor is None:
        return True
    if isinstance(valor, (list, tuple)):
        return len(valor) == 0
    try:
        return bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _opciones_fk(tabla: Table, columna: str, nombres: dict[str, str]) -> list[str] | None:
    for fk in tabla.foreign_keys:
        if fk.column != columna:
            continue
        try:
            destino = cargar(REGISTRY.get(fk.ref_table))
        except Exception:
            return None
        valores = sorted(destino[fk.ref_column].dropna().astype(str).unique())
        if fk.ref_table in ("personas", "alumnos"):
            return [f"{v} — {nombres.get(v, '')}".strip(" —") for v in valores]
        return valores
    return None


def _solo_id(valor: str | None) -> str | None:
    if not valor or valor == VACIO:
        return None
    return valor.split(" — ")[0].strip()


def _a_numero(texto: str, col: Column):
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return int(texto) if col.dtype == "int" else float(texto)
    except ValueError:
        st.error(f"'{texto}' no es un número válido para {col.name}.")
        return None


def _control(col: Column, valor, clave: str, opciones_fk: list[str] | None,
             bloqueado: bool, grupo: str | None = None):
    etiqueta = _etiqueta_campo(col.name, grupo)
    # Sin `help`: un icono de ayuda en cada uno de los campos es ruido. Lo que
    # significa cada columna esta en el encabezado de la tabla y en la
    # documentacion generada, que es donde se busca cuando de verdad hace falta.
    ayuda = None

    if bloqueado:
        st.text_input(etiqueta, value=_texto(valor), key=clave, disabled=True, help=ayuda)
        return valor

    if opciones_fk is not None:
        actual = _texto(valor)
        lista = ([] if col.required else [VACIO]) + opciones_fk
        indice = next((i for i, o in enumerate(lista) if o.split(" — ")[0] == actual), 0)
        return _solo_id(st.selectbox(etiqueta, lista, index=indice, key=clave, help=ayuda))

    if col.choices:
        lista = ([] if col.required else [VACIO]) + list(col.choices)
        actual = _texto(valor)
        indice = lista.index(actual) if actual in lista else 0
        elegido = st.selectbox(etiqueta, lista, index=indice, key=clave, help=ayuda)
        return None if elegido == VACIO else elegido

    if col.dtype == "bool":
        if col.required:
            return st.checkbox(etiqueta, value=bool(valor) if not _es_vacio(valor) else False,
                               key=clave, help=ayuda)
        lista = [VACIO, "sí", "no"]
        actual = VACIO if _es_vacio(valor) else ("sí" if bool(valor) else "no")
        elegido = st.selectbox(etiqueta, lista, index=lista.index(actual), key=clave, help=ayuda)
        return None if elegido == VACIO else (elegido == "sí")

    if col.dtype == "date":
        inicial = valor if isinstance(valor, date) and not isinstance(valor, datetime) else None
        return st.date_input(etiqueta, value=inicial, key=clave, help=ayuda, format="YYYY-MM-DD")

    if col.dtype in ("int", "float"):
        # Texto a propósito: un number_input no puede quedar vacío, y aquí
        # "sin dato" es distinto de "cero".
        return _a_numero(
            st.text_input(etiqueta, value=_texto(valor), key=clave, help=ayuda), col
        )

    if col.dtype == "datetime":
        st.text_input(etiqueta, value=_texto(valor), key=clave, disabled=True, help=ayuda)
        return valor

    actual = _texto(valor)
    if len(actual) > 80:
        return st.text_area(etiqueta, value=actual, key=clave, help=ayuda) or None
    return st.text_input(etiqueta, value=actual, key=clave, help=ayuda) or None


# --- Navegación --------------------------------------------------------


def _filtrar(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    texto = (texto or "").strip().lower()
    if not texto:
        return df
    columnas = df.select_dtypes(include=["string", "object"]).columns
    if not len(columnas):
        return df
    coincide = pd.Series(False, index=df.index)
    for columna in columnas:
        coincide |= df[columna].astype("string").str.lower().str.contains(texto, na=False)
    return df[coincide]


def _mover(clave: str, salto: int, total: int) -> None:
    """Cambia el registro actual. Va como callback a propósito: si la posición
    se cambiara después de dibujar el botón, el botón quedaría con el estado de
    la posición vieja y en el último registro '▶' se vería habilitado."""
    st.session_state[clave] = max(0, min(st.session_state.get(clave, 0) + salto, total - 1))


# Alturas en el pentagrama, contadas en grados desde la línea de abajo:
# 0 = mi (1ª línea), 1 = fa, 2 = sol, 3 = la, 4 = si (3ª línea), 5 = do, 6 = re...
GRADO_CENTRAL = 4  # la 3ª línea: a partir de ahí la plica se dibuja hacia abajo

# La primera frase del Himno a la Alegría (Beethoven, 1824), subida de octava
# para que quepa entera en el pentagrama sin líneas adicionales.
#
# Por qué esta y no otra: es de dominio público sin discusión, se mueve por
# grados conjuntos —que en el pentagrama se ve como una línea que respira, no
# como saltos sueltos— y es la pieza que un alumno principiante aprende
# primero. Para cambiarla por una de Lisart basta con editar esta tupla.
VENTANA = 15  # cuántos registros se ven a la vez en el pentagrama

MELODIA: tuple[int, ...] = (
    4, 4, 5, 6, 6, 5, 4, 3,   # si si do re · re do si la
    2, 2, 3, 4, 4, 3, 3,      # sol sol la si · si la la
)


def _pentagrama(posicion: int, total: int) -> str:
    """El navegador dibujado como un pentagrama.

    Es el elemento con el que se recuerda esta pantalla, y no es adorno: toda
    la app consiste en recorrer registros de uno en uno, que es exactamente lo
    que hace una melodía. La nota roja —el lápiz del músico— es el registro
    abierto; las notas grises son sus vecinos en la tabla; la posición
    horizontal dice qué tan adentro del conjunto estás.

    La ALTURA de cada nota sale de `MELODIA`, indexada por el número de
    registro. Es a propósito determinista y no aleatoria: si la altura se
    sorteara, la misma persona cambiaría de nota en cada refresco de Streamlit
    y se vería como un parpadeo. Así, avanzar por la tabla toca siempre la
    misma melodía.

    El pentagrama muestra una VENTANA de registros alrededor del actual, no la
    tabla entera: con 240 registros repartidos en el ancho de la pantalla las
    notas quedarían a cuatro píxeles unas de otras, encimadas, y la melodía no
    se leería. Con la ventana se lee como un pasaje de partitura y avanzar se
    siente como seguir la música. Qué tan adentro de la tabla estás lo dice el
    contador de abajo, que para eso es exacto.
    """
    ancho, alto, margen, sep = 1000, 56, 26, 8
    centro = alto / 2

    lineas = "".join(
        f'<line class="linea" x1="{margen}" y1="{centro + (i - 2) * sep:.1f}" '
        f'x2="{ancho - margen}" y2="{centro + (i - 2) * sep:.1f}"/>'
        for i in range(5)
    )

    # Ventana de registros visibles, centrada en el actual y pegada a los
    # extremos cuando estás al principio o al final de la tabla.
    ventana = min(VENTANA, total)
    inicio = max(0, min(posicion - ventana // 2, total - ventana))
    visibles = list(range(inicio, inicio + ventana))

    def x_de(indice: int) -> float:
        if ventana <= 1:
            return ancho / 2
        hueco = visibles.index(indice)
        return margen + (ancho - 2 * margen) * hueco / (ventana - 1)

    def y_de(indice: int) -> float:
        """Altura de la nota del registro `indice`, según la melodía."""
        grado = MELODIA[indice % len(MELODIA)]
        return centro + 2 * sep - grado * (sep / 2)

    def plica(x: float, y: float, grado: int, clase: str) -> str:
        """La plica va hacia abajo de la 3ª línea para arriba, como se escribe."""
        if grado >= GRADO_CENTRAL:
            return (f'<line class="{clase}" x1="{x - 6.1:.1f}" y1="{y + 1.6:.1f}" '
                    f'x2="{x - 6.1:.1f}" y2="{y + 22:.1f}"/>')
        return (f'<line class="{clase}" x1="{x + 6.1:.1f}" y1="{y - 1.6:.1f}" '
                f'x2="{x + 6.1:.1f}" y2="{y - 22:.1f}"/>')

    vecinos = ""
    for j in visibles:
        if j == posicion:
            continue
        xv, yv = x_de(j), y_de(j)
        vecinos += (
            f'<ellipse class="vecino" cx="{xv:.1f}" cy="{yv:.1f}" rx="4.4" ry="3.3" '
            f'transform="rotate(-20 {xv:.1f} {yv:.1f})"/>'
            + plica(xv, yv, MELODIA[j % len(MELODIA)], "plica-vecina")
        )

    x, y = x_de(posicion), y_de(posicion)
    nota = (
        f'<ellipse class="actual" cx="{x:.1f}" cy="{y:.1f}" rx="6.6" ry="5" '
        f'transform="rotate(-20 {x:.1f} {y:.1f})"/>'
        + plica(x, y, MELODIA[posicion % len(MELODIA)], "plica")
    )

    # Barras de compás en los extremos: cierran el pentagrama como en una
    # partitura de verdad, y dan a entender dónde empieza y acaba la tabla.
    alto_staff = 4 * sep
    barras = "".join(
        f'<line class="barra" x1="{x}" y1="{centro - alto_staff / 2:.1f}" '
        f'x2="{x}" y2="{centro + alto_staff / 2:.1f}"/>'
        for x in (margen, ancho - margen)
    )
    # Divisiones cada 10%: le dan ritmo al pentagrama y funcionan como regla
    # para calcular a ojo qué tan adentro de la tabla estás.
    compases = "".join(
        f'<line class="compas" x1="{margen + (ancho - 2 * margen) * i / 10:.1f}" '
        f'y1="{centro - alto_staff / 2:.1f}" '
        f'x2="{margen + (ancho - 2 * margen) * i / 10:.1f}" '
        f'y2="{centro + alto_staff / 2:.1f}"/>'
        for i in range(1, 10)
    )

    return (
        f'<div class="lis-staff"><svg viewBox="0 0 {ancho} {alto}" '
        f'role="img" aria-label="Registro {posicion + 1} de {total}">'
        f"{lineas}{compases}{barras}{vecinos}{nota}</svg></div>"
    )


def _navegador(tabla: Table, total: int) -> int:
    clave = f"idx::{tabla.name}"
    posicion = min(st.session_state.get(clave, 0), total - 1)
    st.session_state[clave] = posicion

    anterior, medio, siguiente = st.columns([1, 14, 1], vertical_alignment="center")
    with anterior:
        st.button("◀", key=f"ant::{tabla.name}", use_container_width=True,
                  disabled=posicion == 0, help="Registro anterior",
                  on_click=_mover, args=(clave, -1, total))
    with siguiente:
        st.button("▶", key=f"sig::{tabla.name}", use_container_width=True,
                  disabled=posicion >= total - 1, help="Registro siguiente",
                  on_click=_mover, args=(clave, 1, total))
    with medio:
        st.markdown(
            _pentagrama(posicion, total)
            + f'<div class="lis-pos"><span class="lis-pos__n">{posicion + 1}'
            f" <em>/ {total}</em></span>"
            '<div class="lis-pos__p">registro</div></div>',
            unsafe_allow_html=True,
        )
    return posicion


# --- Panel de una tabla ------------------------------------------------


def _realce(texto: str) -> str:
    """El markdown minimo de una descripcion: `**negritas**` y `codigo`.

    Las descripciones de `tables.py` estan escritas en markdown porque de ahi
    sale tambien `docs/modelo_de_datos.md`. Aqui van dentro de un `<p>`, donde
    markdown no se procesa, y los asteriscos y las comillas quedaban a la vista.
    """
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)


def _panel(tabla: Table, nombres: dict[str, str]) -> None:
    editable = tabla.layer == "master"

    clase, texto = ("ed", "Editable") if editable else ("ro", "Solo lectura")
    insignias = (
        f'<span class="lis-ins lis-ins--{clase}">{texto}</span>'
        f'<span class="lis-ins lis-ins--capa">{tabla.layer}</span>'
    )
    st.markdown(
        '<div class="lis-enc">'
        f'<div class="lis-enc__ic">{iconos.de_tabla(tabla.name, 24)}</div>'
        f'<div><p class="lis-enc__n">{ETIQUETAS.get(tabla.name, tabla.name)}'
        f"  {insignias}</p>"
        f'<p class="lis-enc__d">{_realce(" ".join(tabla.description.split()))}</p>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    if not tabla.path.exists():
        _vacio(tabla, "Esta tabla todavía no existe.", "Corre `lisart init` para crearla.")
        return

    df = cargar(tabla)
    if df.empty:
        _vacio(tabla, "Todavía no hay registros.", "Cuando los haya, aparecerán aquí.")
        return

    if not editable:
        st.markdown(
            '<div class="lis-aviso">'
            f'<b>{tabla.name}</b> vive en la capa <i>{tabla.layer}</i> y se reconstruye sola '
            "desde <code>data/raw/</code>. Se puede consultar, pero no editar: un cambio a "
            "mano se perdería en la próxima ingesta.</div>",
            unsafe_allow_html=True,
        )

    filtro = st.text_input(
        "Buscar", key=f"buscar::{tabla.name}", label_visibility="collapsed",
        placeholder="Buscar por nombre, teléfono, identificador…",
    )
    vista = _filtrar(df, filtro)
    if vista.empty:
        st.warning("Ningún registro coincide con la búsqueda.")
        return
    if filtro:
        st.markdown(
            f'<p class="lis-nota">{len(vista)} de {len(df)} registros coinciden.</p>',
            unsafe_allow_html=True,
        )
        st.session_state[f"idx::{tabla.name}"] = min(
            st.session_state.get(f"idx::{tabla.name}", 0), len(vista) - 1
        )

    # Llegar de otra sección con una persona ya elegida (`?ir=PER-0042`), que es
    # como el directorio de Roles manda a la ficha de alguien.
    ir_a = st.query_params.get("ir")
    if ir_a and len(tabla.primary_key) == 1:
        coincide = vista.index[vista[tabla.primary_key[0]].astype(str) == str(ir_a)]
        if len(coincide):
            st.session_state[f"idx::{tabla.name}"] = int(vista.index.get_loc(coincide[0]))
        del st.query_params["ir"]

    posicion = _navegador(tabla, len(vista))
    fila = vista.iloc[posicion]

    titulo, pie = _titulo_registro(tabla, fila, nombres)
    llave = " · ".join(_texto(fila[c]) for c in tabla.primary_key)
    st.markdown(
        f'<div class="lis-reg"><p class="lis-reg__k">{llave}</p>'
        f'<p class="lis-reg__t">{titulo or "—"}</p>'
        + (f'<p class="lis-reg__p">{pie}</p>' if pie else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    _formulario(tabla, df, fila, nombres, editable=editable)
    _panel_respaldos(tabla)


def _panel_roles() -> None:
    """El directorio: se elige un rol y sale la lista de quienes lo tienen.

    Reemplaza a la vista de tabla de `personas_roles`, que mostraba un registro
    a la vez —`PER-0042 · tutor`— y no contestaba ninguna pregunta que alguien
    se hiciera de verdad. Asignar el rol se hace desde la ficha de la persona,
    en **Personas**, que es donde uno la busca.

    La lista va en una tabla nativa y no en HTML propio: un directorio se lee en
    columnas, se ordena por cualquiera de ellas y se copia a Excel, y eso ya lo
    hace `st.dataframe` mejor de lo que lo haria una lista dibujada a mano.
    """
    st.markdown(
        '<div class="lis-enc">'
        f'<div class="lis-enc__ic">{iconos.de_tabla("personas_roles", 24)}</div>'
        '<div><p class="lis-enc__n">Roles'
        '<span class="lis-ins lis-ins--capa">directorio</span></p>'
        '<p class="lis-enc__d">Quién es qué en la escuela. Se elige un rol y sale la lista '
        'completa. Para <b>asignar</b> o quitar un rol se hace en la ficha de la persona, '
        "en <code>Personas</code>.</p></div></div>",
        unsafe_allow_html=True,
    )

    cuenta = roles_mod.conteo()
    elegido = st.radio(
        "Rol", list(roles_mod.ROLES),
        format_func=lambda r: f"{r} · {cuenta.get(r, 0)}",
        horizontal=True, key="rol_elegido", label_visibility="collapsed",
    )
    cerrados = st.toggle(
        "Incluir a quienes ya no lo tienen", value=False, key="roles_cerrados",
        help="Un rol que se quita no se borra: se cierra con la fecha de ese día.",
    )

    gente = roles_mod.por_rol(elegido, incluir_cerrados=cerrados)
    if gente.empty:
        st.markdown(
            f'<div class="lis-vacio"><div class="lis-vacio__t">Nadie tiene el rol '
            f"<i>{elegido}</i> todavía.</div>"
            '<p class="lis-nota">Se asigna desde la ficha de la persona, en Personas.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        return

    filtro = st.text_input(
        "Buscar", key="buscar::roles", label_visibility="collapsed",
        placeholder="Buscar por nombre, teléfono o correo…",
    )
    if filtro:
        aguja = filtro.strip().lower()
        columnas = ["nombre", "telefono", "correo", "persona_id"]
        junto = gente[columnas].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
        gente = gente[junto.str.contains(aguja, regex=False)]

    st.markdown(
        f'<p class="lis-nota">{len(gente)} persona(s) con el rol <b>{elegido}</b>. '
        "Se puede ordenar por cualquier columna y copiar a Excel.</p>",
        unsafe_allow_html=True,
    )

    st.dataframe(
        gente,
        use_container_width=True,
        hide_index=True,
        column_config={
            "nombre": st.column_config.TextColumn("Nombre", width="large"),
            "telefono": st.column_config.TextColumn("Teléfono"),
            "correo": st.column_config.TextColumn("Correo", width="medium"),
            "otros_roles": st.column_config.TextColumn("Otros roles"),
            "vigente_hasta": st.column_config.DateColumn("Lo tuvo hasta"),
            "persona_id": st.column_config.TextColumn("Clave", width="small"),
        },
        # La fecha de cierre solo se muestra cuando se piden los cerrados: si no,
        # es una columna llena de vacíos que no dice nada.
        column_order=(
            ("nombre", "telefono", "correo", "otros_roles", "vigente_hasta", "persona_id")
            if cerrados
            else ("nombre", "telefono", "correo", "otros_roles", "persona_id")
        ),
    )

    # Saltar a la ficha. Va por la direccion (`?seccion=personas&ir=...`), igual
    # que el clic en el grafo: es lo unico que sobrevive a un rerun de Streamlit.
    quien = st.selectbox(
        "Abrir la ficha de",
        list(gente["persona_id"]),
        format_func=lambda pid: str(
            gente.loc[gente["persona_id"] == pid, "nombre"].iloc[0]
        ),
        key="ficha::roles",
    )
    if st.button("Ver su ficha completa", key="ir::roles"):
        st.query_params.clear()
        st.query_params["seccion"] = "personas"
        st.query_params["ir"] = quien
        st.rerun()


def _vacio(tabla: Table, titulo: str, detalle: str) -> None:
    st.markdown(
        f'<div class="lis-vacio"><div class="lis-vacio__ic">'
        f'{iconos.de_tabla(tabla.name, 46)}</div>'
        f'<div class="lis-vacio__t">{titulo}</div>'
        f'<p class="lis-nota">{detalle}</p></div>',
        unsafe_allow_html=True,
    )


def _formulario(
    tabla: Table, df: pd.DataFrame, fila: pd.Series, nombres: dict[str, str], *, editable: bool
) -> None:
    solo_con_dato = False
    if len(tabla.columns) > 30:
        solo_con_dato = st.toggle(
            "Mostrar solo los campos con información", value=True,
            key=f"llenos::{tabla.name}",
            help="Esta tabla tiene muchas columnas y casi todas suelen venir vacías.",
        )

    visibles = [
        c for c in tabla.columns
        if not (solo_con_dato and _es_vacio(fila[c.name]) and c.name not in tabla.primary_key)
    ]

    # La llave del registro va DENTRO de la de cada control. Streamlit guarda
    # el estado de un widget por su `key`: si dos registros comparten llave, al
    # cambiar de registro los campos siguen mostrando —y guardando— los valores
    # del anterior. Es la diferencia entre editar a Sofía y sobrescribirla
    # con los datos de Ana.
    llave_registro = "::".join(str(fila[c]) for c in tabla.primary_key)

    with st.form(key=f"form::{tabla.name}::{llave_registro}"):
        capturado: dict[str, object] = {}
        for grupo, columnas in _agrupar(tabla, visibles):
            _seccion(grupo)
            rejilla = st.columns(2)
            for i, col in enumerate(columnas):
                bloqueado = (
                    not editable or col.name in tabla.primary_key or col.name in SOLO_LECTURA
                )
                with rejilla[i % 2]:
                    capturado[col.name] = _control(
                        col, fila[col.name],
                        f"campo::{tabla.name}::{llave_registro}::{col.name}",
                        _opciones_fk(tabla, col.name, nombres), bloqueado, grupo,
                    )

        # Los roles no son una columna de `personas` —una persona puede tener
        # varios— pero se piensan como parte de su ficha, no como otra tabla.
        # Por eso el control vive aquí y el guardado los sincroniza aparte.
        seleccion_roles = None
        if tabla.name == "personas" and editable:
            _seccion("Roles")
            actuales = roles_mod.de_persona(str(fila["persona_id"]))
            seleccion_roles = st.multiselect(
                "Qué es esta persona en la escuela",
                list(roles_mod.ROLES),
                default=actuales,
                key=f"roles::{llave_registro}",
                help=(
                    "Quitar un rol no borra nada: lo cierra con la fecha de hoy, para que "
                    "después se pueda saber quién dio clase el semestre pasado."
                ),
            )

        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        guardar = st.form_submit_button(
            "Guardar cambios", type="primary", disabled=not editable, use_container_width=True
        )

    if guardar:
        _guardar(tabla, df, fila, capturado, roles=seleccion_roles)


def _guardar(
    tabla: Table, df: pd.DataFrame, fila: pd.Series, capturado: dict, *, roles=None
) -> None:
    actualizado = df.copy()
    mascara = pd.Series(True, index=actualizado.index)
    for llave in tabla.primary_key:
        mascara &= actualizado[llave].astype(str) == str(fila[llave])

    if not mascara.any():
        st.error("No se encontró el registro en la tabla. Vuelve a cargar la pantalla.")
        return

    for nombre, valor in capturado.items():
        if nombre in SOLO_LECTURA or nombre in tabla.primary_key:
            continue
        actualizado.loc[mascara, nombre] = valor
    if "actualizado_en" in actualizado.columns:
        actualizado.loc[mascara, "actualizado_en"] = datetime.now().replace(microsecond=0)

    try:
        _, copia = backup.guardar_con_respaldo(tabla, actualizado, motivo="edicion")
    except io.DataError as error:
        st.error(f"No se guardó nada. {error}")
        return

    mensaje = "Cambios guardados."
    if roles is not None:
        try:
            cambios = roles_mod.sincronizar(str(fila["persona_id"]), roles)
        except io.DataError as error:
            # Los datos de la persona sí se guardaron; hay que decirlo, no dejar
            # creer que no se guardó nada.
            st.warning(f"Los datos se guardaron, pero los roles no: {error}")
            st.rerun()
        if cambios:
            mensaje += f" Roles: {cambios.resumen()}."

    st.success(mensaje)
    if copia:
        st.markdown(
            f'<p class="lis-nota">Respaldo del estado anterior: '
            f"<code>{ruta_corta(copia)}</code></p>",
            unsafe_allow_html=True,
        )
    st.rerun()


def _panel_respaldos(tabla: Table) -> None:
    copias = backup.listar(tabla)
    with st.expander(f"Respaldos · {len(copias)}"):
        if not copias:
            st.markdown(
                '<p class="lis-nota">Todavía no hay respaldos. Se crea uno solo cada vez '
                "que guardas.</p>",
                unsafe_allow_html=True,
            )
            return
        st.markdown(
            '<p class="lis-nota">Cada vez que se guarda, el estado anterior queda aquí. '
            f"Se conservan las últimas {backup.COPIAS_A_CONSERVAR} copias.</p>",
            unsafe_allow_html=True,
        )
        elegida = st.selectbox(
            "Copia", copias, key=f"copia::{tabla.name}", format_func=lambda p: p.name
        )
        if st.button("Restaurar esta copia", key=f"restaurar::{tabla.name}"):
            backup.restaurar(tabla, Path(elegida))
            st.success(f"Restaurado desde {Path(elegida).name}.")
            st.rerun()


# --- Entrada -----------------------------------------------------------


# --- Pestaña del grafo -------------------------------------------------


def _panel_horarios() -> None:
    from datetime import time

    from lisart.procesos import horarios
    from lisart.tables import DIAS

    st.markdown(
        '<div class="lis-enc">'
        f'<div class="lis-enc__ic">{iconos.svg("metronomo", 24)}</div>'
        '<div><p class="lis-enc__n">Horarios</p>'
        '<p class="lis-enc__d">La semana tipo de cada persona: cuándo puede dar o tomar '
        'clase, y qué tiene ocupado. Sirve para encontrar dónde reponer una clase '
        'perdida.</p></div></div>',
        unsafe_allow_html=True,
    )

    # `st.pills` y no otro radio: el radio de arriba va disfrazado de pestañas y
    # el disfraz se le pegaría a este también.
    vista = st.pills(
        "Vista", ["semana", "reposicion"], default="semana", key="hor::vista",
        label_visibility="collapsed",
        format_func=lambda v: "La semana de alguien" if v == "semana" else "Buscar reposición",
    ) or "semana"

    personas = cargar(REGISTRY.get("personas"))
    if personas.empty:
        _vacio(REGISTRY.get("personas"), "Todavía no hay personas.",
               "Corre `lisart procesar inscripciones` para darlas de alta.")
        return

    nombres = nombres_de_personas()
    ordenadas = sorted(nombres.items(), key=lambda kv: kv[1])

    if vista == "reposicion":
        _panel_reposicion(ordenadas, horarios)
        return

    # Se abre en alguien que sí tenga horario: una semana vacía como primera
    # impresión hace pensar que la pantalla no sirve.
    con_horario = set(io.read_table("disponibilidad")["persona_id"].astype(str))
    ids = sorted(
        (pid for pid, _ in ordenadas),
        key=lambda pid: (pid not in con_horario, nombres.get(pid, pid)),
    )
    elegida = st.selectbox(
        "Persona", ids, key="hor::persona",
        format_func=lambda pid: (
            f"{nombres.get(pid, pid)} · {pid}" + ("" if pid in con_horario else "  (sin horario)")
        ),
    )

    agenda = horarios.agenda(elegida)
    st.markdown(
        f'<p class="lis-nota">{semana_mod.resumen(agenda)}</p>', unsafe_allow_html=True
    )
    st.markdown(semana_mod.dibujar(agenda), unsafe_allow_html=True)
    st.markdown(
        '<div class="lis-leyenda">'
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--disponible"></i>'
        "Disponible</span>"
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--bloqueado"></i>'
        "Bloqueado</span>"
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--nada"></i>'
        "No disponible — una hora sin barra</span></div>",
        unsafe_allow_html=True,
    )

    _seccion("Agregar un bloque")
    horas = semana_mod.opciones_de_hora()
    with st.form(key=f"hor::alta::{elegida}"):
        c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1.1])
        with c1:
            dia = st.selectbox("Día", DIAS[:6], key="hor::dia",
                               format_func=lambda d: horarios.NOMBRE_DIA.get(d, d))
        with c2:
            desde = st.selectbox("Desde", horas, index=horas.index("09:00"), key="hor::desde")
        with c3:
            hasta = st.selectbox("Hasta", horas, index=horas.index("10:00"), key="hor::hasta")
        with c4:
            estado = st.selectbox("Estado", ["disponible", "bloqueado"], key="hor::estado")
        motivo = st.text_input(
            "Motivo (opcional)", key="hor::motivo",
            placeholder="Por qué está bloqueado, si lo está",
        )
        agregar = st.form_submit_button(
            "Agregar bloque", type="primary", use_container_width=True
        )

    if agregar:
        _agregar_bloque(elegida, dia, desde, hasta, estado, motivo, time)

    _lista_de_bloques(elegida, horarios)


def _agregar_bloque(persona_id, dia, desde, hasta, estado, motivo, time) -> None:
    from lisart import backup
    from lisart.ids import ahora, next_ids

    if desde >= hasta:
        st.error("La hora de fin tiene que ser posterior a la de inicio.")
        return

    def a_hora(texto: str):
        h, m = texto.split(":")
        return time(int(h), int(m))

    tabla = io.read_table("disponibilidad")
    momento = ahora()
    nueva = pd.DataFrame([{
        "disponibilidad_id": next_ids("disponibilidad")[0],
        "persona_id": persona_id, "dia": dia,
        "hora_inicio": a_hora(desde), "hora_fin": a_hora(hasta),
        "estado": estado, "motivo": motivo or None,
        "vigente_desde": None, "vigente_hasta": None,
        "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
    }])
    try:
        backup.guardar_con_respaldo(
            "disponibilidad", pd.concat([tabla, nueva], ignore_index=True), motivo="edicion"
        )
    except io.DataError as error:
        st.error(f"No se guardó nada. {error}")
        return
    st.success(f"Agregado: {horarios_nombre(dia)} de {desde} a {hasta}, {estado}.")
    st.rerun()


def horarios_nombre(dia: str) -> str:
    from lisart.procesos.horarios import NOMBRE_DIA

    return NOMBRE_DIA.get(dia, dia)


def _lista_de_bloques(persona_id: str, horarios) -> None:
    from lisart import backup

    tabla = io.read_table("disponibilidad")
    mios = tabla[tabla["persona_id"].astype(str) == persona_id].copy()
    if mios.empty:
        st.markdown(
            '<p class="lis-nota">Esta persona no tiene ningún bloque. Todas sus horas '
            "cuentan como no disponibles.</p>",
            unsafe_allow_html=True,
        )
        return

    _seccion(f"Bloques guardados · {len(mios)}")
    mios["orden"] = mios["dia"].map(semana_mod.orden_de_dia)
    for _, fila in mios.sort_values(["orden", "hora_inicio"]).iterrows():
        texto, boton = st.columns([6, 1])
        with texto:
            motivo = f" — {fila['motivo']}" if tiene_valor(fila.get("motivo")) else ""
            st.markdown(
                f'<p class="lis-bloque"><b>{horarios_nombre(str(fila["dia"]))}</b> '
                f'{fila["hora_inicio"]:%H:%M}–{fila["hora_fin"]:%H:%M} '
                f'<span class="lis-etiq lis-etiq--{fila["estado"]}">{fila["estado"]}</span>'
                f'<span class="lis-nota">{motivo}</span></p>',
                unsafe_allow_html=True,
            )
        with boton:
            if st.button("Quitar", key=f"quitar::{fila['disponibilidad_id']}",
                         use_container_width=True):
                backup.guardar_con_respaldo(
                    "disponibilidad",
                    tabla[tabla["disponibilidad_id"] != fila["disponibilidad_id"]],
                    motivo="edicion",
                )
                st.rerun()


def _panel_reposicion(ordenadas, horarios) -> None:
    alumnos = io.read_table("alumnos")
    if alumnos.empty:
        st.markdown(
            '<p class="lis-nota">No hay alumnos dados de alta.</p>', unsafe_allow_html=True
        )
        return

    de_alumno = {pid for pid in alumnos["persona_id"].astype(str)}
    opciones = [(pid, nombre) for pid, nombre in ordenadas if pid in de_alumno]
    ids = [pid for pid, _ in opciones]
    nombres = dict(opciones)

    izq, der = st.columns([3, 2])
    with izq:
        alumno = st.selectbox(
            "Alumno que faltó", ids, key="rep::alumno",
            format_func=lambda pid: f"{nombres.get(pid, pid)} · {pid}",
        )
    with der:
        cruzar = st.toggle(
            "Solo horas en las que el alumno también puede", value=True, key="rep::cruzar",
            help="Apágalo si el alumno va a decir él mismo cuándo le acomoda.",
        )

    huecos = horarios.opciones_de_reposicion(alumno, cruzar_con_el_alumno=cruzar)
    if not huecos:
        clases = horarios.profesores_de(alumno)
        motivo = (
            "Este alumno no está inscrito en ninguna clase todavía."
            if not clases
            else "Ninguno de sus profesores tiene horas libres que coincidan."
        )
        st.markdown(
            f'<div class="lis-aviso">Sin opciones de reposición. {motivo}</div>',
            unsafe_allow_html=True,
        )
        return

    _seccion(f"{len(huecos)} opción(es)")
    for hueco in huecos:
        st.markdown(
            f'<div class="lis-hueco"><span class="lis-hueco__cuando">{hueco}</span>'
            f'<span class="lis-nota">{hueco.minutos} min · clase {hueco.clase_id}</span></div>',
            unsafe_allow_html=True,
        )


def _panel_grafo() -> None:
    st.markdown(
        '<div class="lis-enc">'
        f'<div class="lis-enc__ic">{iconos.svg("ligadura", 24)}</div>'
        '<div><p class="lis-enc__n">Relaciones</p>'
        '<p class="lis-enc__d">Cada nodo es una entidad y cada línea un vínculo real. '
        'Sirve para ver <b>qué alumnos se parecen</b>: los que estudian el mismo '
        'instrumento se agrupan alrededor de él, y los hermanos alrededor de su tutor. '
        'Haz clic en un nodo para ver su ficha.</p></div></div>',
        unsafe_allow_html=True,
    )

    izq, der = st.columns([2, 3])
    with izq:
        lente = st.selectbox(
            "Lente", list(grafo_mod.LENTES), key="grafo::lente",
            format_func=lambda k: grafo_mod.LENTES[k],
        )
    with der:
        catalogo = cargar(REGISTRY.get("instrumentos"))
        opciones = ["Todos"]
        if not catalogo.empty:
            opciones += sorted(catalogo["nombre"].dropna().astype(str))
        elegido = st.selectbox("Filtrar por instrumento", opciones, key="grafo::instrumento")

    instrumento_id = None
    if elegido != "Todos" and not catalogo.empty:
        fila = catalogo[catalogo["nombre"].astype(str) == elegido]
        if not fila.empty:
            instrumento_id = str(fila.iloc[0]["instrumento_id"])

    red, nodos = grafo_mod.construir(lente, instrumento_id)
    if not len(red):
        st.markdown(
            '<div class="lis-vacio"><div class="lis-vacio__t">No hay nada que dibujar '
            "con este filtro.</div></div>", unsafe_allow_html=True,
        )
        return

    # El nodo elegido viaja en la dirección (?nodo=...). Es lo que permite que
    # un clic dentro del SVG llegue hasta Python sin JavaScript.
    seleccion = st.query_params.get("nodo")
    if seleccion not in nodos:
        seleccion = None

    st.markdown(
        '<div class="lis-leyenda">' + grafo_mod.leyenda()
        + f'<span class="lis-leyenda__n">{len(red)} nodos · {red.number_of_edges()} '
        "vínculos · el tamaño es el número de conexiones</span></div>",
        unsafe_allow_html=True,
    )
    # El SVG va por `st.markdown`, que es la única vía que conserva el clic.
    #
    # Se probaron las otras dos y no sirven:
    #   · `st.html` sanea el SVG hasta borrarlo entero.
    #   · `components.html` lo pinta al instante (1 s contra 60), pero su
    #     iframe va en modo sandbox y **bloquea la navegación de la página
    #     padre**: los enlaces de los nodos dejan de responder, que es
    #     justamente lo que hace útil al grafo.
    #
    # El precio es que el saneador de Markdown tarda cerca de un minuto en
    # procesar los ~600 elementos del SVG. Está anotado como pendiente.
    st.markdown(grafo_mod.svg(red, nodos, seleccion), unsafe_allow_html=True)

    if not seleccion:
        st.markdown(
            '<p class="lis-nota">Haz clic en un nodo para ver su ficha.</p>',
            unsafe_allow_html=True,
        )
        return

    if st.button("Quitar selección", key="grafo::limpiar"):
        st.query_params.clear()
        st.query_params["seccion"] = "grafo"
        st.rerun()

    _ficha_nodo(seleccion, nodos[seleccion].tipo)


def _ficha_nodo(id_: str, tipo: str) -> None:
    info = grafo_mod.detalle(id_, tipo)
    st.markdown(
        f'<div class="lis-reg"><p class="lis-reg__k">{id_}</p>'
        f'<p class="lis-reg__t">{info["titulo"]}</p>'
        f'<p class="lis-reg__p">{info["subtitulo"]}</p></div>',
        unsafe_allow_html=True,
    )

    columnas = st.columns(2)
    with columnas[0]:
        if info["datos"]:
            _seccion("Datos")
            filas = "".join(
                f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in info["datos"].items()
            )
            st.markdown(f'<table class="lis-tabla">{filas}</table>', unsafe_allow_html=True)
    with columnas[1]:
        for titulo, elementos in info["listas"].items():
            if not elementos:
                continue
            _seccion(titulo)
            st.markdown(
                '<ul class="lis-lista">'
                + "".join(f"<li>{e}</li>" for e in elementos)
                + "</ul>",
                unsafe_allow_html=True,
            )

    if tipo != "instrumento":
        similares = grafo_mod.parecidos(id_)
        if similares:
            _seccion("Se parecen a esta persona")
            st.markdown(
                '<ul class="lis-lista">'
                + "".join(f"<li>{n} <span class=\"lis-porque\">{p}</span></li>"
                          for n, p in similares)
                + "</ul>",
                unsafe_allow_html=True,
            )


def main() -> None:
    st.set_page_config(
        page_title="Lisart · Base de datos",
        page_icon=str(LOGO_ICONO) if LOGO_ICONO.exists() else "♪",
        layout="wide",
    )
    _estilos()
    _banda()

    tablas = sorted(
        REGISTRY.in_dependency_order(),
        key=lambda t: list(ETIQUETAS).index(t.name) if t.name in ETIQUETAS else 99,
    )
    secciones = [(t.name, ETIQUETAS.get(t.name, t.name)) for t in tablas]
    secciones.append(("horarios", "Horarios"))
    secciones.append(("grafo", "Grafo"))
    claves = [c for c, _ in secciones]
    rotulo = dict(secciones)

    # La sección viaja en la dirección, no en `st.tabs`.
    #
    # Con pestañas normales el grafo no podía ir al final: al hacer clic en un
    # nodo la página se recarga con `?nodo=...` y Streamlit volvía siempre a la
    # primera pestaña, escupiendo al usuario fuera del grafo. Guardando la
    # sección en la URL, la recarga vuelve justo donde estabas.
    #
    # De paso se arregla otra cosa: `st.tabs` ejecuta el contenido de TODAS las
    # pestañas en cada corrida. Así solo se arma la sección que se está viendo.
    actual = st.query_params.get("seccion")
    if actual not in claves:
        actual = claves[0]

    elegida = st.radio(
        "Sección", claves, index=claves.index(actual), horizontal=True,
        format_func=lambda c: rotulo[c], key="nav", label_visibility="collapsed",
    )
    if elegida != actual:
        # Cambiar de sección suelta el nodo elegido: pertenecía al grafo.
        st.query_params.clear()
        st.query_params["seccion"] = elegida
        st.rerun()

    if elegida == "horarios":
        _panel_horarios()
    elif elegida == "grafo":
        _panel_grafo()
    elif elegida == "personas_roles":
        # Esta tabla no se navega registro por registro: se consulta por rol.
        _panel_roles()
    else:
        _panel(REGISTRY.get(elegida), nombres_de_personas())


# Streamlit corre este archivo como script, así que aquí `__name__` vale
# "__main__". La guarda existe para que importar el módulo —desde una prueba, o
# solo para leer ETIQUETAS— no levante la pantalla entera.
if __name__ == "__main__":
    main()
