"""Pantalla de profesores: la agenda de quien da clase.

Se corre con `lisart ui --profesores`. Es una aplicación **aparte** de `lisart ui` a
petición de la escuela, aunque comparte todo lo de abajo: el mismo modelo, la
misma capa de escritura con respaldo, el mismo dibujo de la semana y la misma
identidad visual. Lo que cambia es el camino: aquí se entra **por la clase**.

    clase  →  profesor de esa clase  →  su semana

Por qué por la clase y no por la persona
----------------------------------------
`lisart ui` ya deja ver la semana de cualquiera buscando por nombre. Quien
administra la docencia no piensa en personas sueltas: piensa en "el piano de los
jueves" y de ahí en quién lo da. Entrar por la clase pone la pregunta primero y
la persona después.

La aproximación de las horas ocupadas
-------------------------------------
Las horas que los alumnos de una clase marcaron como suyas se pintan como
**ocupadas para el profesor**, con trama rayada para no confundirlas con un
bloqueo capturado a mano.

La escuela pidió esta aproximación sabiendo que no es exacta: un alumno marca
cuándo *puede* venir, no cuándo tiene clase, así que sobra horas. No se guarda
en la base — es un cálculo, y guardarlo obligaría a recalcularlo cada vez que un
alumno cambie su horario.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lisart import backup, io
from lisart.ids import ahora, next_ids
from lisart.procesos import horarios
from lisart.tables import DIAS
from lisart.ui import iconos
from lisart.ui import semana as semana_mod
from lisart.ui.app import (
    _banda,
    _estilos,
    _seccion,
    nombres_de_personas,
    tiene_valor,
)


def _sin_datos(titulo: str, detalle: str) -> None:
    st.markdown(
        f'<div class="lis-vacio"><div class="lis-vacio__ic">'
        f'{iconos.svg("metronomo", 46)}</div>'
        f'<div class="lis-vacio__t">{titulo}</div>'
        f'<p class="lis-nota">{detalle}</p></div>',
        unsafe_allow_html=True,
    )


def _encabezado() -> None:
    st.markdown(
        '<div class="lis-enc">'
        f'<div class="lis-enc__ic">{iconos.svg("pisarron" if False else "metronomo", 24)}</div>'
        '<div><p class="lis-enc__n">Agenda de profesores</p>'
        '<p class="lis-enc__d">Se entra por la clase: primero cuál es, luego quién la da, '
        'y de ahí su semana. Las horas que sus alumnos ya marcaron aparecen como '
        'ocupadas.</p></div></div>',
        unsafe_allow_html=True,
    )


# --- Alta de lo que todavía no existe ----------------------------------


def _crear_clase() -> None:
    """Sin clases capturadas esta pantalla no tiene por dónde empezar."""
    espacios = io.read_table("espacios")
    instrumentos = io.read_table("instrumentos")
    horas = semana_mod.opciones_de_hora()

    with st.form("clase::alta"):
        c1, c2 = st.columns([2, 2])
        with c1:
            nombre = st.text_input("Nombre de la clase", placeholder="Piano de los jueves")
            instrumento = st.selectbox(
                "Instrumento", ["—"] + sorted(instrumentos["instrumento_id"].astype(str))
                if not instrumentos.empty else ["—"],
            )
        with c2:
            agendables = (
                espacios[espacios["agendable"]]["espacio_id"].astype(str).tolist()
                if not espacios.empty else []
            )
            espacio = st.selectbox("Espacio", ["—"] + sorted(agendables))
            dia = st.selectbox("Día", DIAS[:6], format_func=lambda d: horarios.NOMBRE_DIA[d])
        c3, c4 = st.columns(2)
        with c3:
            desde = st.selectbox("Desde", horas, index=horas.index("16:00"))
        with c4:
            hasta = st.selectbox("Hasta", horas, index=horas.index("17:00"))

        if st.form_submit_button("Crear clase", type="primary", use_container_width=True):
            if desde >= hasta:
                st.error("La hora de fin tiene que ser posterior a la de inicio.")
                return
            momento = ahora()
            fila = {
                "clase_id": next_ids("clases")[0],
                "nombre": nombre or None,
                "instrumento_id": None if instrumento == "—" else instrumento,
                "espacio_id": None if espacio == "—" else espacio,
                "dia": dia,
                "hora_inicio": _a_hora(desde), "hora_fin": _a_hora(hasta),
                "cupo": None, "activa": True,
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }
            actuales = io.read_table("clases")
            backup.guardar_con_respaldo(
                "clases", pd.concat([actuales, pd.DataFrame([fila])], ignore_index=True),
                motivo="alta",
            )
            st.success(f"Clase creada: {fila['clase_id']}.")
            st.rerun()


def _a_hora(texto: str):
    from datetime import time

    h, m = texto.split(":")
    return time(int(h), int(m))


def _asignar_profesor(clase_id: str, nombres: dict[str, str]) -> None:
    """Da de alta al profesor de la clase y le pone el rol si no lo tenía."""
    personas = io.read_table("personas")
    if personas.empty:
        st.markdown('<p class="lis-nota">No hay personas todavía.</p>', unsafe_allow_html=True)
        return

    ids = sorted(personas["persona_id"].astype(str), key=lambda p: nombres.get(p, p))
    izq, der = st.columns([3, 1])
    with izq:
        quien = st.selectbox(
            "Persona", ids, key=f"asig::{clase_id}",
            format_func=lambda p: f"{nombres.get(p, p)} · {p}",
        )
    with der:
        st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
        if st.button("Asignar", type="primary", use_container_width=True,
                     key=f"btn::{clase_id}"):
            momento = ahora()
            io.upsert("clases_profesores", pd.DataFrame([{
                "clase_id": clase_id, "persona_id": quien, "rol_en_clase": "titular",
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }]))
            # El rol se agrega aquí porque asignar a alguien a dar clase ES
            # convertirlo en profesor: dejarlo sin rol lo escondería del resto.
            io.upsert("personas_roles", pd.DataFrame([{
                "persona_id": quien, "rol": "profesor",
                "vigente_desde": None, "vigente_hasta": None,
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }]))
            st.success(f"{nombres.get(quien, quien)} quedó como profesor de la clase.")
            st.rerun()


def _inscribir_alumnos(clase_id: str, nombres: dict[str, str]) -> None:
    """Quién toma esta clase.

    Sin esto la clase no tiene alumnos, y sin alumnos no hay de dónde deducir
    las horas ocupadas del profesor: la función quedaría inalcanzable desde la
    pantalla.
    """
    alumnos = io.read_table("alumnos")
    if alumnos.empty:
        st.markdown(
            '<p class="lis-nota">No hay alumnos dados de alta.</p>', unsafe_allow_html=True
        )
        return

    inscritos_tabla = io.read_table("clases_alumnos")
    ya = (
        inscritos_tabla[inscritos_tabla["clase_id"].astype(str) == clase_id]["persona_id"]
        .astype(str).tolist()
        if not inscritos_tabla.empty else []
    )

    ids = sorted(alumnos["persona_id"].astype(str), key=lambda p: nombres.get(p, p))
    elegidos = st.multiselect(
        "Alumnos de la clase", ids, default=[a for a in ya if a in ids],
        key=f"insc::{clase_id}",
        format_func=lambda p: f"{nombres.get(p, p)} · {p}",
        help="Sus horarios son los que se pintan como ocupados para el profesor.",
    )

    if st.button("Guardar inscripción", type="primary", key=f"binsc::{clase_id}",
                 use_container_width=True):
        momento = ahora()
        otras = (
            inscritos_tabla[inscritos_tabla["clase_id"].astype(str) != clase_id]
            if not inscritos_tabla.empty else inscritos_tabla
        )
        nuevas = pd.DataFrame([
            {
                "clase_id": clase_id, "persona_id": persona_id,
                "vigente_desde": None, "vigente_hasta": None,
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }
            for persona_id in elegidos
        ])
        backup.guardar_con_respaldo(
            "clases_alumnos",
            pd.concat([otras, nuevas], ignore_index=True) if len(nuevas) else otras,
            motivo="edicion",
        )
        st.success(f"{len(elegidos)} alumno(s) en la clase.")
        st.rerun()


# --- La semana del profesor --------------------------------------------


def _semana_del_profesor(profesor_id: str, clase_id: str) -> None:
    propia = horarios.agenda(profesor_id)
    derivado = horarios.bloqueado_por_los_alumnos(clase_id)
    todo = pd.concat([propia, derivado], ignore_index=True) if not derivado.empty else propia

    st.markdown(
        f'<p class="lis-nota">{semana_mod.resumen(propia)}'
        + (f" · {len(derivado)} bloque(s) ocupados por sus alumnos" if not derivado.empty else "")
        + "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(semana_mod.dibujar(todo), unsafe_allow_html=True)
    st.markdown(
        '<div class="lis-leyenda">'
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--disponible"></i>'
        "Disponible</span>"
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--bloqueado"></i>'
        "Bloqueado a mano</span>"
        '<span class="lis-leyenda__i"><i class="lis-caja lis-caja--alumnos"></i>'
        "Ocupado por sus alumnos — deducido, no capturado</span></div>",
        unsafe_allow_html=True,
    )

    _seccion("Agregar un bloque a su semana")
    horas = semana_mod.opciones_de_hora()
    with st.form(f"prof::alta::{profesor_id}"):
        c1, c2, c3, c4 = st.columns([1.1, 1, 1, 1.1])
        with c1:
            dia = st.selectbox("Día", DIAS[:6], format_func=lambda d: horarios.NOMBRE_DIA[d])
        with c2:
            desde = st.selectbox("Desde", horas, index=horas.index("09:00"))
        with c3:
            hasta = st.selectbox("Hasta", horas, index=horas.index("14:00"))
        with c4:
            estado = st.selectbox("Estado", ["disponible", "bloqueado"])
        motivo = st.text_input("Motivo (opcional)", placeholder="Por qué está bloqueado")
        if st.form_submit_button("Agregar bloque", type="primary", use_container_width=True):
            if desde >= hasta:
                st.error("La hora de fin tiene que ser posterior a la de inicio.")
                return
            momento = ahora()
            actuales = io.read_table("disponibilidad")
            nueva = pd.DataFrame([{
                "disponibilidad_id": next_ids("disponibilidad")[0],
                "persona_id": profesor_id, "dia": dia,
                "hora_inicio": _a_hora(desde), "hora_fin": _a_hora(hasta),
                "estado": estado, "motivo": motivo or None,
                "vigente_desde": None, "vigente_hasta": None,
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }])
            backup.guardar_con_respaldo(
                "disponibilidad", pd.concat([actuales, nueva], ignore_index=True),
                motivo="edicion",
            )
            st.success(f"Agregado: {horarios.NOMBRE_DIA[dia]} de {desde} a {hasta}.")
            st.rerun()

    _bloques_guardados(profesor_id)


def _bloques_guardados(profesor_id: str) -> None:
    tabla = io.read_table("disponibilidad")
    mios = tabla[tabla["persona_id"].astype(str) == profesor_id].copy()
    if mios.empty:
        st.markdown(
            '<p class="lis-nota">Sin bloques capturados. Todas sus horas cuentan como '
            "no disponibles.</p>",
            unsafe_allow_html=True,
        )
        return

    _seccion(f"Bloques capturados · {len(mios)}")
    mios["orden"] = mios["dia"].map(semana_mod.orden_de_dia)
    for _, fila in mios.sort_values(["orden", "hora_inicio"]).iterrows():
        texto, boton = st.columns([6, 1])
        with texto:
            motivo = f" — {fila['motivo']}" if tiene_valor(fila.get("motivo")) else ""
            st.markdown(
                f'<p class="lis-bloque"><b>{horarios.NOMBRE_DIA[str(fila["dia"])]}</b> '
                f'{fila["hora_inicio"]:%H:%M}–{fila["hora_fin"]:%H:%M} '
                f'<span class="lis-etiq lis-etiq--{fila["estado"]}">{fila["estado"]}</span>'
                f'<span class="lis-nota">{motivo}</span></p>',
                unsafe_allow_html=True,
            )
        with boton:
            if st.button("Quitar", key=f"q::{fila['disponibilidad_id']}",
                         use_container_width=True):
                backup.guardar_con_respaldo(
                    "disponibilidad",
                    tabla[tabla["disponibilidad_id"] != fila["disponibilidad_id"]],
                    motivo="edicion",
                )
                st.rerun()


# --- Entrada -----------------------------------------------------------


def main() -> None:
    from lisart.ui.app import LOGO_ICONO

    st.set_page_config(
        page_title="Lisart · Profesores",
        page_icon=str(LOGO_ICONO) if LOGO_ICONO.exists() else "♪",
        layout="wide",
    )
    _estilos()
    _banda()
    _encabezado()

    clases = io.read_table("clases")
    nombres = nombres_de_personas()

    if clases.empty:
        _sin_datos(
            "Todavía no hay clases capturadas.",
            "La agenda de un profesor se ve a través de su clase. Crea la primera aquí abajo.",
        )
        _seccion("Crear una clase")
        _crear_clase()
        return

    def etiqueta(clase_id: str) -> str:
        fila = clases[clases["clase_id"].astype(str) == clase_id].iloc[0]
        cuando = f"{horarios.NOMBRE_DIA[str(fila['dia'])]} {fila['hora_inicio']:%H:%M}"
        return f"{fila['nombre'] or fila['clase_id']} · {cuando}"

    ids = clases.sort_values(["dia", "hora_inicio"])["clase_id"].astype(str).tolist()
    clase_id = st.selectbox("Clase", ids, format_func=etiqueta, key="prof::clase")

    docentes = io.read_table("clases_profesores")
    de_la_clase = (
        docentes[docentes["clase_id"].astype(str) == clase_id]["persona_id"].astype(str).tolist()
        if not docentes.empty else []
    )

    if not de_la_clase:
        st.markdown(
            '<div class="lis-aviso">Esta clase no tiene profesor asignado. '
            "Asigna uno para ver y editar su semana.</div>",
            unsafe_allow_html=True,
        )
        _seccion("Asignar profesor")
        _asignar_profesor(clase_id, nombres)

        _seccion("Alumnos de esta clase")
        _inscribir_alumnos(clase_id, nombres)
    else:
        # Una clase puede tener varios profesores: se elige de cuál se ve la semana.
        profesor_id = (
            de_la_clase[0]
            if len(de_la_clase) == 1
            else st.selectbox(
                "Profesor", de_la_clase, key="prof::quien",
                format_func=lambda p: f"{nombres.get(p, p)} · {p}",
            )
        )
        st.markdown(
            f'<div class="lis-reg"><p class="lis-reg__k">{profesor_id}</p>'
            f'<p class="lis-reg__t">{nombres.get(profesor_id, profesor_id)}</p>'
            f'<p class="lis-reg__p">da <b>{etiqueta(clase_id)}</b></p></div>',
            unsafe_allow_html=True,
        )
        _semana_del_profesor(profesor_id, clase_id)

        _seccion("Alumnos de esta clase")
        _inscribir_alumnos(clase_id, nombres)

        with st.expander("Asignar otro profesor a esta clase"):
            _asignar_profesor(clase_id, nombres)

    _seccion("Crear otra clase")
    with st.expander("Nueva clase"):
        _crear_clase()


if __name__ == "__main__":
    main()
