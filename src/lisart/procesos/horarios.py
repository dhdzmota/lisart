"""Horarios: quién puede cuándo, y a qué hora se puede reponer una clase.

Los tres estados
----------------
Una hora de una persona está en uno de tres estados:

    disponible      puede dar o tomar clase
    bloqueado       está ocupado: una clase, o un bloqueo personal
    no_disponible   ni lo uno ni lo otro

**Solo se guardan los dos primeros.** El tercero es la ausencia de fila, tal
como lo definió la escuela: "simplemente no está ni bloqueado ni disponible".
Guardarlo sería tener dos formas de decir lo mismo —una fila que dice "nada" y
la falta de fila— y tarde o temprano las dos se contradicen.

A cambio, `estado_en()` sí devuelve los tres: el modelo de datos guarda lo
mínimo y la API contesta lo que se pregunta.

Bloqueado le gana a disponible
------------------------------
Los rangos pueden traslaparse: un profesor disponible de 9 a 14 con un bloqueo
de 11 a 12. La regla es que **bloqueado gana**, porque el costo de equivocarse
no es simétrico: ofrecer una hora ocupada manda a un alumno a una clase que no
existe; no ofrecer una hora libre solo desperdicia un hueco.

La reposición
-------------
Cuando un alumno no puede asistir, `opciones_de_reposicion()` cruza tres cosas:

1. las clases del alumno, y de ahí **sus profesores** (una clase puede tener
   más de uno),
2. cuándo está disponible cada uno de esos profesores,
3. cuándo está disponible el alumno.

Lo que sale es la lista de huecos donde los dos coinciden. Sin el paso 3 se
propondrían horas en las que el alumno tampoco puede, que es exactamente el
problema que se quería resolver.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

import pandas as pd

from lisart import io
from lisart.tables import DIAS

ESTADOS = ("disponible", "bloqueado", "no_disponible")

# Orden de los días para poder ordenar y comparar.
ORDEN_DIA = {dia: i for i, dia in enumerate(DIAS)}

NOMBRE_DIA = {
    "L": "lunes", "M": "martes", "Mi": "miércoles", "J": "jueves",
    "V": "viernes", "S": "sábado", "D": "domingo",
}


@dataclass(frozen=True)
class Hueco:
    """Un rango libre donde podría caber una reposición."""

    dia: str
    inicio: time
    fin: time
    profesor_id: str
    profesor: str
    clase_id: str

    @property
    def minutos(self) -> int:
        return _a_minutos(self.fin) - _a_minutos(self.inicio)

    def __str__(self) -> str:
        return (
            f"{NOMBRE_DIA.get(self.dia, self.dia)} {self.inicio:%H:%M}–{self.fin:%H:%M} "
            f"con {self.profesor}"
        )


def _a_minutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def _de_minutos(minutos: int) -> time:
    return time(minutos // 60, minutos % 60)


def _vigente(fila: pd.Series, cuando: date) -> bool:
    desde, hasta = fila.get("vigente_desde"), fila.get("vigente_hasta")
    if isinstance(desde, date) and cuando < desde:
        return False
    return not (isinstance(hasta, date) and cuando > hasta)


def _rangos(persona_id: str, estado: str, cuando: date) -> dict[str, list[tuple[int, int]]]:
    """Rangos de una persona en un estado, por día, en minutos."""
    tabla = io.read_table("disponibilidad")
    if tabla.empty:
        return {}
    mias = tabla[
        (tabla["persona_id"].astype(str) == persona_id) & (tabla["estado"] == estado)
    ]
    por_dia: dict[str, list[tuple[int, int]]] = {}
    for _, fila in mias.iterrows():
        if not _vigente(fila, cuando):
            continue
        if not isinstance(fila["hora_inicio"], time) or not isinstance(fila["hora_fin"], time):
            continue
        por_dia.setdefault(str(fila["dia"]), []).append(
            (_a_minutos(fila["hora_inicio"]), _a_minutos(fila["hora_fin"]))
        )
    return por_dia


def _unir(rangos: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Junta rangos que se tocan o se traslapan."""
    unidos: list[tuple[int, int]] = []
    for inicio, fin in sorted(rangos):
        if unidos and inicio <= unidos[-1][1]:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], fin))
        else:
            unidos.append((inicio, fin))
    return unidos


def _restar(base: list[tuple[int, int]], quitar: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Le saca a `base` lo que cubre `quitar`. Así gana lo bloqueado."""
    resultado = list(base)
    for corte_ini, corte_fin in _unir(quitar):
        siguiente: list[tuple[int, int]] = []
        for inicio, fin in resultado:
            if corte_fin <= inicio or corte_ini >= fin:
                siguiente.append((inicio, fin))
                continue
            if inicio < corte_ini:
                siguiente.append((inicio, corte_ini))
            if corte_fin < fin:
                siguiente.append((corte_fin, fin))
        resultado = siguiente
    return resultado


def _intersectar(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> list[tuple[int, int]]:
    comunes = []
    for ini_a, fin_a in a:
        for ini_b, fin_b in b:
            ini, fin = max(ini_a, ini_b), min(fin_a, fin_b)
            if ini < fin:
                comunes.append((ini, fin))
    return _unir(comunes)


def libre(persona_id: str, cuando: date | None = None) -> dict[str, list[tuple[int, int]]]:
    """Lo realmente libre de una persona: lo disponible menos lo bloqueado."""
    cuando = cuando or date.today()
    disponible = _rangos(persona_id, "disponible", cuando)
    bloqueado = _rangos(persona_id, "bloqueado", cuando)
    return {
        dia: _restar(_unir(rangos), bloqueado.get(dia, []))
        for dia, rangos in disponible.items()
    }


def estado_en(persona_id: str, dia: str, hora: time, cuando: date | None = None) -> str:
    """Qué pasa con esa persona ese día a esa hora. Devuelve uno de `ESTADOS`.

    Aquí sí aparecen los tres, aunque solo se guarden dos: `no_disponible` es
    lo que se contesta cuando no hay ninguna fila que cubra esa hora.
    """
    cuando = cuando or date.today()
    minuto = _a_minutos(hora)

    for inicio, fin in _rangos(persona_id, "bloqueado", cuando).get(dia, []):
        if inicio <= minuto < fin:
            return "bloqueado"
    for inicio, fin in _rangos(persona_id, "disponible", cuando).get(dia, []):
        if inicio <= minuto < fin:
            return "disponible"
    return "no_disponible"


def profesores_de(alumno_persona_id: str) -> list[tuple[str, str]]:
    """(clase_id, persona_id del profesor) de las clases del alumno.

    Una clase puede tener más de un profesor, así que esto devuelve una pareja
    por cada combinación, no una por clase.
    """
    inscritos = io.read_table("clases_alumnos")
    docentes = io.read_table("clases_profesores")
    if inscritos.empty or docentes.empty:
        return []

    mis_clases = set(
        inscritos[inscritos["persona_id"].astype(str) == alumno_persona_id]["clase_id"].astype(str)
    )
    return sorted(
        (str(f["clase_id"]), str(f["persona_id"]))
        for _, f in docentes.iterrows()
        if str(f["clase_id"]) in mis_clases
    )


def opciones_de_reposicion(
    alumno_persona_id: str,
    *,
    minutos_minimos: int = 30,
    cruzar_con_el_alumno: bool = True,
    cuando: date | None = None,
) -> list[Hueco]:
    """Dónde podría reponer este alumno. Ordenado por día y hora.

    Con `cruzar_con_el_alumno=False` devuelve todos los huecos del profesor, sin
    mirar si el alumno puede: sirve cuando el alumno va a decir él mismo cuándo
    le acomoda.
    """
    cuando = cuando or date.today()
    personas = io.read_table("personas")
    nombres = dict(
        zip(
            personas["persona_id"].astype(str),
            (
                personas["nombre"].fillna("").astype(str)
                + " " + personas["apellido_paterno"].fillna("").astype(str)
            ).str.strip(),
            strict=False,
        )
    )

    del_alumno = libre(alumno_persona_id, cuando) if cruzar_con_el_alumno else None

    huecos: list[Hueco] = []
    for clase_id, profesor_id in profesores_de(alumno_persona_id):
        for dia, rangos in libre(profesor_id, cuando).items():
            comunes = rangos if del_alumno is None else _intersectar(
                rangos, del_alumno.get(dia, [])
            )
            for inicio, fin in comunes:
                if fin - inicio < minutos_minimos:
                    continue
                huecos.append(
                    Hueco(
                        dia=dia,
                        inicio=_de_minutos(inicio),
                        fin=_de_minutos(fin),
                        profesor_id=profesor_id,
                        profesor=nombres.get(profesor_id, profesor_id),
                        clase_id=clase_id,
                    )
                )

    return sorted(huecos, key=lambda h: (ORDEN_DIA.get(h.dia, 99), h.inicio, h.profesor))


def bloqueado_por_los_alumnos(clase_id: str, cuando: date | None = None) -> pd.DataFrame:
    """Las horas que los alumnos de una clase ya tienen marcadas.

    **Es una aproximacion, y la escuela lo sabe.** Un alumno marca cuando PUEDE
    venir, no cuando tiene clase; tomar eso como "el profesor esta ocupado"
    sobra horas. Se usa igual porque hoy es lo unico que hay y se acerca: donde
    hay alumnos de esa clase disponibles, es razonable suponer que el profesor
    esta con ellos.

    **No se guarda.** Es un calculo, no un hecho: guardarlo obligaria a
    recalcularlo cada vez que un alumno cambie su horario, y tarde o temprano
    quedaria desfasado. Se muestra aparte de los bloqueos que alguien capturo a
    mano, que esos si son un hecho.
    """
    cuando = cuando or date.today()
    inscritos = io.read_table("clases_alumnos")
    if inscritos.empty:
        return pd.DataFrame(columns=["dia", "hora_inicio", "hora_fin", "estado"])

    alumnos = inscritos[inscritos["clase_id"].astype(str) == str(clase_id)]
    por_dia: dict[str, list[tuple[int, int]]] = {}
    for persona_id in alumnos["persona_id"].astype(str):
        for dia, rangos in _rangos(persona_id, "disponible", cuando).items():
            por_dia.setdefault(dia, []).extend(rangos)

    filas = [
        {
            "dia": dia,
            "orden": ORDEN_DIA.get(dia, 99),
            "hora_inicio": _de_minutos(ini),
            "hora_fin": _de_minutos(fin),
            "estado": "por_alumnos",
        }
        for dia, rangos in por_dia.items()
        for ini, fin in _unir(rangos)
    ]
    if not filas:
        return pd.DataFrame(columns=["dia", "hora_inicio", "hora_fin", "estado"])
    return (
        pd.DataFrame(filas)
        .sort_values(["orden", "hora_inicio"])
        .drop(columns="orden")
        .reset_index(drop=True)
    )


def agenda(persona_id: str, cuando: date | None = None) -> pd.DataFrame:
    """La semana de una persona, lista para mostrar."""
    cuando = cuando or date.today()
    filas = []
    for estado in ("disponible", "bloqueado"):
        for dia, rangos in _rangos(persona_id, estado, cuando).items():
            for inicio, fin in _unir(rangos):
                filas.append({
                    "dia": dia,
                    "orden": ORDEN_DIA.get(dia, 99),
                    "hora_inicio": _de_minutos(inicio),
                    "hora_fin": _de_minutos(fin),
                    "estado": estado,
                })
    if not filas:
        return pd.DataFrame(columns=["dia", "hora_inicio", "hora_fin", "estado"])
    return (
        pd.DataFrame(filas)
        .sort_values(["orden", "hora_inicio"])
        .drop(columns="orden")
        .reset_index(drop=True)
    )
