"""Iconos musicales en SVG, dibujados a mano sobre una retícula de 24×24.

Por que SVG y no los PNG de `assets/iconos`: esos son ilustraciones sueltas,
de estilos distintos y pensadas para otra cosa. Mezcladas en una interfaz se
ven como estampas pegadas. Estos comparten retícula, grosor de trazo (1.6) y
color (`currentColor`, o sea heredan el del texto), que es lo que hace que un
conjunto de iconos se lea como un sistema y no como un collage.

Todos son musicales a proposito, y cada uno dice algo de su tabla:

    pentagrama_aves  el motivo del logo de Lisart: aves sobre el pentagrama
    nota             una figura, una voz
    notas_ligadas    dos figuras unidas por el corchete: varios papeles
    ligadura         el arco que une dos notas: un vinculo entre personas
    diapason         el la de referencia: afinar dos sistemas entre si
    piano            teclado: los espacios donde se da clase
    guitarra         los instrumentos que se ensenan
    metronomo        el pulso: lo que se cobra y cada cuando
    partitura        la hoja que se llena: el formulario de inscripcion
"""

from __future__ import annotations

TRAZO = 1.6

_FORMAS: dict[str, str] = {
    # El motivo de la marca: tres aves posadas sobre el pentagrama.
    "pentagrama_aves": """
        <path d="M2 7h20M2 11h20M2 15h20M2 19h20"/>
        <path d="M6.6 7c0-1 .8-1.8 1.8-1.8.7 0 1.3.4 1.6 1l1.6.6-1.6.5c-.3.6-.9 1-1.6 1"
              fill="currentColor" stroke="none"/>
        <path d="M12.2 11c0-1 .8-1.8 1.8-1.8.7 0 1.3.4 1.6 1l1.6.6-1.6.5c-.3.6-.9 1-1.6 1"
              fill="currentColor" stroke="none"/>
        <path d="M4.4 15c0-1 .8-1.8 1.8-1.8.7 0 1.3.4 1.6 1l1.6.6-1.6.5c-.3.6-.9 1-1.6 1"
              fill="currentColor" stroke="none"/>
    """,
    "nota": """
        <ellipse cx="8" cy="17.2" rx="4.3" ry="3.2" transform="rotate(-22 8 17.2)"
                 fill="currentColor" stroke="none"/>
        <path d="M11.9 16.1V4.2"/>
    """,
    "notas_ligadas": """
        <ellipse cx="6.4" cy="17.4" rx="3.4" ry="2.5" transform="rotate(-22 6.4 17.4)"
                 fill="currentColor" stroke="none"/>
        <ellipse cx="17" cy="15.4" rx="3.4" ry="2.5" transform="rotate(-22 17 15.4)"
                 fill="currentColor" stroke="none"/>
        <path d="M9.4 16.6V5.4M20 14.6V3.4"/>
        <path d="M9.4 5.4 20 3.4v3.1L9.4 8.5z" fill="currentColor" stroke="none"/>
    """,
    "ligadura": """
        <ellipse cx="5.6" cy="17.6" rx="3.2" ry="2.4" transform="rotate(-22 5.6 17.6)"
                 fill="currentColor" stroke="none"/>
        <ellipse cx="18.4" cy="17.6" rx="3.2" ry="2.4" transform="rotate(-22 18.4 17.6)"
                 fill="currentColor" stroke="none"/>
        <path d="M8.4 16.6V6M21.2 16.6V6"/>
        <path d="M6.6 4.4C10 1.6 14 1.6 17.4 4.4"/>
    """,
    "diapason": """
        <path d="M8.2 3v8.4a3.8 3.8 0 0 0 7.6 0V3"/>
        <path d="M12 15.2V21"/>
        <path d="M9.6 21h4.8"/>
    """,
    "piano": """
        <rect x="2.6" y="5" width="18.8" height="14" rx="1.6"/>
        <path d="M8 5v8.4M12 5v8.4M16 5v8.4"/>
        <path d="M5.6 5h2.2v6H5.6zM10 5h2.2v6H10zM14.4 5h2.2v6h-2.2zM18.4 5h2.2v6h-2.2z"
              fill="currentColor" stroke="none"/>
    """,
    "guitarra": """
        <path d="M14.8 9.2 20.6 3.4"/>
        <path d="M19 1.8l3.2 3.2-1.6 1.6-3.2-3.2z"/>
        <path d="M12.4 11.6a4.6 4.6 0 0 0-6.5 0 4 4 0 0 0-.5 5 4 4 0 0 0 5 .5 4.6 4.6 0
                 0 0 2-5.5z"/>
        <circle cx="9.3" cy="14.7" r="1.5"/>
    """,
    "metronomo": """
        <path d="M9 3h6l3.6 18H5.4z"/>
        <path d="M12 19 16.2 6.6"/>
        <path d="M8.4 15.6h7.2"/>
    """,
    "partitura": """
        <path d="M5 2.6h9.6L19.4 7v14.4H5z"/>
        <path d="M14.2 2.6V7h4.8"/>
        <path d="M8 11.4h8M8 14h8M8 16.6h4.4"/>
        <ellipse cx="15.4" cy="17.4" rx="1.7" ry="1.3" transform="rotate(-22 15.4 17.4)"
                 fill="currentColor" stroke="none"/>
        <path d="M16.9 16.8v-3.6"/>
    """,
    # Auxiliares de la interfaz, con el mismo trazo para que no desentonen.
    "buscar": """
        <circle cx="10.6" cy="10.6" r="6.6"/>
        <path d="M15.4 15.4 21 21"/>
    """,
    "guardar": """
        <path d="M4.6 4.6h11l4 4v11h-15z"/>
        <path d="M8 4.6v5h6v-5M8 19.4v-5.6h8v5.6"/>
    """,
    "respaldo": """
        <path d="M21 12a9 9 0 1 1-2.6-6.4"/>
        <path d="M21 3v5.2h-5.2"/>
    """,
}

# Que icono le toca a cada tabla.
POR_TABLA: dict[str, str] = {
    "personas": "pentagrama_aves",
    "alumnos": "nota",
    "personas_roles": "notas_ligadas",
    "relaciones": "ligadura",
    "identificadores_externos": "diapason",
    "espacios": "piano",
    "instrumentos": "guitarra",
    "conceptos": "metronomo",
    "respuestas_inscripcion": "partitura",
}


def svg(nombre: str, tamano: int = 24, clase: str = "") -> str:
    """Devuelve el `<svg>` listo para insertar en la pagina."""
    formas = _FORMAS.get(nombre, _FORMAS["nota"])
    return (
        f'<svg class="lis-icono {clase}" width="{tamano}" height="{tamano}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{TRAZO}" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{formas}</svg>'
    )


def de_tabla(tabla: str, tamano: int = 24, clase: str = "") -> str:
    return svg(POR_TABLA.get(tabla, "nota"), tamano, clase)
