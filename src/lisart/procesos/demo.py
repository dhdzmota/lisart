"""Datos de prueba para poder ejercitar las pantallas antes de tener los reales.

El problema que resuelve
------------------------
La agenda de profesores y la reposición no se pueden probar sin profesores ni
clases, y esos datos todavía no existen (vendrán de Kydemy). Capturarlos a mano
para probar deja basura mezclada con los 240 registros reales de la escuela, y
al mes nadie recuerda cuál era de mentira.

La regla: todo lo que siembra este módulo lleva `fuente = "demo"`. Eso hace dos
cosas: se ve en la pantalla —la columna está a la vista en cada tabla— y se
puede borrar entero con una sola orden, sin tocar un solo dato real.

    lisart demo --sembrar
    lisart demo --limpiar

**Los alumnos NO se inventan.** Se inscriben alumnos de verdad a las clases de
prueba, porque el horario que ellos declararon es lo que hace que la deducción
de horas ocupadas del profesor tenga algo que enseñar. Al limpiar solo se borra
la inscripción, no el alumno.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import pandas as pd

from lisart import io
from lisart.ids import ahora, next_ids, normalizar_nombre

FUENTE = "demo"

# Tablas que toca, en orden de borrado (primero lo que apunta a otras cosas).
TABLAS = (
    "clases_alumnos",
    "clases_profesores",
    "disponibilidad",
    "clases",
    "personas_roles",
    "personas",
)


@dataclass(frozen=True)
class ProfesorDePrueba:
    nombre: str
    apellido: str
    semana: tuple[tuple[str, tuple[int, int], tuple[int, int], str], ...]


PROFESORES = (
    ProfesorDePrueba(
        "Ximena", "Alcántara",
        (
            ("L", (9, 0), (14, 0), "disponible"),
            ("Mi", (9, 0), (14, 0), "disponible"),
            ("V", (9, 0), (13, 0), "disponible"),
            ("Mi", (11, 0), (12, 0), "bloqueado"),
        ),
    ),
    ProfesorDePrueba(
        "Emiliano", "Rentería",
        (
            ("M", (15, 0), (20, 0), "disponible"),
            ("J", (15, 0), (20, 0), "disponible"),
            ("S", (10, 0), (14, 0), "disponible"),
        ),
    ),
    ProfesorDePrueba(
        "Ivonne", "Palomar",
        (
            ("L", (16, 0), (20, 0), "disponible"),
            ("Mi", (16, 0), (20, 0), "disponible"),
            ("V", (16, 0), (19, 0), "disponible"),
            ("L", (18, 0), (19, 0), "bloqueado"),
        ),
    ),
)

# (nombre, instrumento, día, inicio, fin, cuántos profesores)
CLASES = (
    ("Piano · matutino", "PIANO", "L", (10, 0), (11, 0), 1),
    ("Violín · vespertino", "VIOLIN", "M", (17, 0), (18, 0), 1),
    ("Canto · ensamble", "CANTO", "J", (18, 0), (19, 30), 2),
    ("Batería · sábados", "BATERIA", "S", (11, 0), (12, 0), 1),
)


def _marca(momento) -> dict:
    return {"creado_en": momento, "actualizado_en": momento, "fuente": FUENTE}


def hay_datos() -> bool:
    """Si ya hay algo sembrado. Sembrar dos veces duplicaría los profesores."""
    for tabla in TABLAS:
        datos = io.read_table(tabla, strict=False)
        if not datos.empty and (datos["fuente"] == FUENTE).any():
            return True
    return False


def sembrar() -> dict[str, int]:
    """Crea profesores, sus semanas, clases, asignaciones e inscripciones."""
    if hay_datos():
        raise RuntimeError(
            "Ya hay datos de prueba. Correr `lisart demo --limpiar` antes de volver a sembrar."
        )

    momento = ahora()
    cuenta: dict[str, int] = {}

    # --- Profesores -----------------------------------------------------
    ids = next_ids("personas", len(PROFESORES))
    personas, roles = [], []
    for persona_id, profe in zip(ids, PROFESORES, strict=True):
        personas.append({
            "persona_id": persona_id, "nombre": profe.nombre,
            "apellido_paterno": profe.apellido, "apellido_materno": None,
            "nombre_normalizado": normalizar_nombre(f"{profe.nombre} {profe.apellido}"),
            "fecha_nacimiento": None, "telefono": None, "correo": None,
            "domicilio": None, "activo": True, **_marca(momento),
        })
        roles.append({
            "persona_id": persona_id, "rol": "profesor",
            "vigente_desde": None, "vigente_hasta": None, **_marca(momento),
        })
    io.upsert("personas", pd.DataFrame(personas))
    io.upsert("personas_roles", pd.DataFrame(roles))
    cuenta["profesores"] = len(personas)

    # --- Sus semanas ----------------------------------------------------
    bloques = []
    total = sum(len(p.semana) for p in PROFESORES)
    for identificador, (persona_id, (dia, desde, hasta, estado)) in zip(
        next_ids("disponibilidad", total),
        [(pid, b) for pid, p in zip(ids, PROFESORES, strict=True) for b in p.semana],
        strict=True,
    ):
        bloques.append({
            "disponibilidad_id": identificador, "persona_id": persona_id,
            "dia": dia, "hora_inicio": time(*desde), "hora_fin": time(*hasta),
            "estado": estado,
            "motivo": "comida" if estado == "bloqueado" else None,
            "vigente_desde": None, "vigente_hasta": None, **_marca(momento),
        })
    io.upsert("disponibilidad", pd.DataFrame(bloques))
    cuenta["bloques de horario"] = len(bloques)

    # --- Clases ---------------------------------------------------------
    catalogo = set(io.read_table("instrumentos")["instrumento_id"].astype(str))
    espacios = io.read_table("espacios")
    agendables = sorted(espacios[espacios["agendable"]]["espacio_id"].astype(str)) or [None]

    clases, asignaciones = [], []
    for i, (clase_id, (nombre, instrumento, dia, desde, hasta, cuantos)) in enumerate(
        zip(next_ids("clases", len(CLASES)), CLASES, strict=True)
    ):
        clases.append({
            "clase_id": clase_id, "nombre": nombre,
            "instrumento_id": instrumento if instrumento in catalogo else None,
            "espacio_id": agendables[i % len(agendables)],
            "dia": dia, "hora_inicio": time(*desde), "hora_fin": time(*hasta),
            "cupo": None, "activa": True, **_marca(momento),
        })
        # Una clase con dos profesores, para que se vea que se puede.
        for j in range(cuantos):
            asignaciones.append({
                "clase_id": clase_id, "persona_id": ids[(i + j) % len(ids)],
                "rol_en_clase": "titular" if j == 0 else "apoyo", **_marca(momento),
            })
    io.upsert("clases", pd.DataFrame(clases))
    io.upsert("clases_profesores", pd.DataFrame(asignaciones))
    cuenta["clases"] = len(clases)
    cuenta["asignaciones de profesor"] = len(asignaciones)

    cuenta["alumnos inscritos"] = _inscribir_alumnos_reales(clases, momento)
    return cuenta


def _inscribir_alumnos_reales(clases: list[dict], momento) -> int:
    """Mete alumnos DE VERDAD a las clases de prueba.

    Se eligen los que tienen horario declarado: son los únicos que hacen visible
    la deducción de horas ocupadas del profesor. No se inventa ningún alumno.
    """
    disponibilidad = io.read_table("disponibilidad")
    alumnos = set(io.read_table("alumnos")["persona_id"].astype(str))
    con_horario = [
        persona_id
        for persona_id in disponibilidad["persona_id"].astype(str).unique()
        if persona_id in alumnos
    ]
    if not con_horario:
        return 0

    inscripciones = []
    for i, clase in enumerate(clases):
        for persona_id in con_horario[i * 3 : i * 3 + 3]:
            inscripciones.append({
                "clase_id": clase["clase_id"], "persona_id": persona_id,
                "vigente_desde": None, "vigente_hasta": None, **_marca(momento),
            })
    if not inscripciones:
        return 0
    io.upsert("clases_alumnos", pd.DataFrame(inscripciones))
    return len(inscripciones)


def limpiar() -> dict[str, int]:
    """Borra TODO lo sembrado y nada más. Se guía por `fuente == "demo"`."""
    from lisart import backup

    borrado: dict[str, int] = {}
    for tabla in TABLAS:
        datos = io.read_table(tabla, strict=False)
        if datos.empty:
            continue
        de_prueba = datos["fuente"] == FUENTE
        if not de_prueba.any():
            continue
        backup.guardar_con_respaldo(tabla, datos[~de_prueba], motivo="limpiar-demo")
        borrado[tabla] = int(de_prueba.sum())
    return borrado
