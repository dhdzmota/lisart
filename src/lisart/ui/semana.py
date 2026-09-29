"""La semana de una persona, dibujada.

Por qué una línea de tiempo y no una cuadrícula
-----------------------------------------------
Un horario aquí se guarda como **rangos** ("lunes de 9 a 14"), no como casillas
de media hora. Dibujarlo como cuadrícula obligaría a partir cada rango en veinte
celdas y a volverlas a juntar con la vista — trabajo de más para que se lea
peor. Como línea de tiempo, un rango es una barra: una cosa en los datos, una
cosa en la pantalla.

Tiene además una ventaja práctica que ya se pagó cara en el grafo: una semana
completa son ~40 elementos SVG en vez de los ~140 de una cuadrícula, y el
saneador de Markdown de Streamlit se atraganta con los SVG grandes.

Los colores dicen el estado, y no solos
---------------------------------------
    disponible   oro   (el acento cálido de Lisart)
    bloqueado    vino  (el lápiz rojo: donde ya hay algo)
    no disponible        nada, papel vacío

Cada barra lleva además su etiqueta dentro cuando cabe, y siempre su texto al
pasar el ratón: el color nunca es lo único que distingue un estado.
"""

from __future__ import annotations

from datetime import time

import pandas as pd

from lisart.procesos.horarios import NOMBRE_DIA, ORDEN_DIA, _a_minutos
from lisart.tables import DIAS

ANCHO, ALTO_DIA, MARGEN_IZQ, MARGEN_SUP = 1000, 34, 96, 26
DESDE_DEFECTO, HASTA_DEFECTO = 8, 21  # horas que se dibujan si no hay datos

ESTILOS = """
.sem { font-family: 'IBM Plex Sans', system-ui, sans-serif; }
.sem .hora { fill: #948C84; font-size: 11px; text-anchor: middle; }
.sem .dia { fill: #131211; font-size: 12px; font-weight: 600; text-anchor: end; }
.sem .rejilla { stroke: #EDE8DE; stroke-width: 1; }
.sem .rejilla--fuerte { stroke: #DDD6C8; }
.sem .carril { fill: #FCFBF8; }
.sem .barra { rx: 3; }
.sem .barra--disponible { fill: #FDF3D4; stroke: #D9A400; stroke-width: 1.5; }
.sem .barra--bloqueado { fill: #F8E5E7; stroke: #B33844; stroke-width: 1.5; }
/* Lo derivado de los alumnos: mismo vino, pero rayado y sin relleno, para
   que no se confunda con un bloqueo que alguien capturo de verdad. */
.sem .barra--por_alumnos { fill: url(#rayas); stroke: #C98490; stroke-width: 1.2;
  stroke-dasharray: 4 3; }
.sem .texto { font-size: 11px; font-weight: 600; pointer-events: none; }
.sem .texto--disponible { fill: #6B5000; }
.sem .texto--bloqueado { fill: #8E2A34; }
.sem .texto--por_alumnos { fill: #A8626E; }
"""


def _rango_horario(bloques: pd.DataFrame) -> tuple[int, int]:
    """Las horas que se dibujan. La ventana es FIJA a proposito.

    Ajustarla a lo que tiene cada quien parecia listo, pero hacia que la semana
    de alguien con un bloque se dibujara de 16 a 18 y la de otro de 9 a 20: dos
    semanas del mismo horario que no se pueden comparar de un vistazo. Con una
    ventana fija, un bloque a la misma hora cae en el mismo sitio siempre.
    """
    desde, hasta = DESDE_DEFECTO, HASTA_DEFECTO
    if bloques.empty:
        return desde, hasta
    horas = [h.hour for h in bloques["hora_inicio"] if isinstance(h, time)]
    horas += [h.hour + (1 if h.minute else 0) for h in bloques["hora_fin"] if isinstance(h, time)]
    if not horas:
        return desde, hasta
    # Solo se amplia si algo se sale de la ventana; nunca se encoge.
    return min(desde, min(horas)), max(hasta, max(horas))


def dibujar(bloques: pd.DataFrame, dias: tuple[str, ...] = DIAS[:6]) -> str:
    """La semana como líneas de tiempo. `bloques` es lo que da `horarios.agenda`."""
    desde, hasta = _rango_horario(bloques)
    minutos_totales = (hasta - desde) * 60
    util = ANCHO - MARGEN_IZQ - 16
    alto = MARGEN_SUP + len(dias) * ALTO_DIA + 10

    def x_de(minuto: int) -> float:
        return MARGEN_IZQ + (minuto - desde * 60) / minutos_totales * util

    # La trama de rayas para lo que se deduce de los alumnos.
    partes = [
        '<defs><pattern id="rayas" width="6" height="6" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)"><rect width="6" height="6" fill="#FFFFFF"/>'
        '<line x1="0" y1="0" x2="0" y2="6" stroke="#EFD8DC" stroke-width="3"/>'
        "</pattern></defs>"
    ]

    # Las horas en punto, arriba y como rejilla.
    for hora in range(desde, hasta + 1):
        x = x_de(hora * 60)
        fuerte = " rejilla--fuerte" if hora % 2 == 0 else ""
        partes.append(
            f'<line class="rejilla{fuerte}" x1="{x:.0f}" y1="{MARGEN_SUP - 6:.0f}" '
            f'x2="{x:.0f}" y2="{MARGEN_SUP + len(dias) * ALTO_DIA:.0f}"/>'
        )
        if hora % 2 == 0:
            partes.append(
                f'<text class="hora" x="{x:.0f}" y="{MARGEN_SUP - 12:.0f}">'
                f"{hora}:00</text>"
            )

    for i, dia in enumerate(dias):
        y = MARGEN_SUP + i * ALTO_DIA
        partes.append(
            f'<rect class="carril" x="{MARGEN_IZQ}" y="{y + 3:.0f}" '
            f'width="{util:.0f}" height="{ALTO_DIA - 8:.0f}"/>'
        )
        partes.append(
            f'<text class="dia" x="{MARGEN_IZQ - 12}" y="{y + ALTO_DIA / 2 + 1:.0f}">'
            f"{NOMBRE_DIA.get(dia, dia)}</text>"
        )

        del_dia = bloques[bloques["dia"] == dia] if not bloques.empty else bloques
        for _, fila in del_dia.iterrows():
            if not isinstance(fila["hora_inicio"], time):
                continue
            ini, fin = _a_minutos(fila["hora_inicio"]), _a_minutos(fila["hora_fin"])
            x1, x2 = x_de(ini), x_de(fin)
            estado = str(fila["estado"])
            etiqueta = f"{fila['hora_inicio']:%H:%M}–{fila['hora_fin']:%H:%M}"
            partes.append(
                f'<g><title>{NOMBRE_DIA.get(dia, dia)} {etiqueta} · {estado}</title>'
                f'<rect class="barra barra--{estado}" x="{x1:.0f}" y="{y + 5:.0f}" '
                f'width="{max(x2 - x1, 3):.0f}" height="{ALTO_DIA - 12:.0f}"/>'
            )
            if x2 - x1 > 62:
                partes.append(
                    f'<text class="texto texto--{estado}" x="{x1 + 7:.0f}" '
                    f'y="{y + ALTO_DIA / 2 + 3:.0f}">{etiqueta}</text>'
                )
            partes.append("</g>")

    return (
        f"<style>{ESTILOS}</style>"
        f'<div class="lis-semana"><svg class="sem" viewBox="0 0 {ANCHO} {alto:.0f}" '
        f'role="img" aria-label="Semana tipo">' + "".join(partes) + "</svg></div>"
    )


def resumen(bloques: pd.DataFrame) -> str:
    """Una línea con lo que suma la semana. Es lo que se quiere saber de un vistazo."""
    if bloques.empty:
        return "sin horario registrado"
    minutos = {"disponible": 0, "bloqueado": 0, "por_alumnos": 0}
    for _, fila in bloques.iterrows():
        if isinstance(fila["hora_inicio"], time):
            minutos[str(fila["estado"])] += _a_minutos(fila["hora_fin"]) - _a_minutos(
                fila["hora_inicio"]
            )
    partes = [f"{minutos['disponible'] / 60:.1f} h disponibles"]
    if minutos["bloqueado"]:
        partes.append(f"{minutos['bloqueado'] / 60:.1f} h bloqueadas")
    dias = bloques["dia"].nunique()
    partes.append(f"en {dias} día{'s' if dias != 1 else ''}")
    return " · ".join(partes)


def opciones_de_hora(paso_min: int = 30) -> list[str]:
    """Las horas que se pueden elegir al capturar, en formato 24 h."""
    return [
        f"{m // 60:02d}:{m % 60:02d}"
        for m in range(7 * 60, 22 * 60 + 1, paso_min)
    ]


def orden_de_dia(dia: str) -> int:
    return ORDEN_DIA.get(dia, 99)
