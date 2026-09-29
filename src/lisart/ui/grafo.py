"""El grafo de relaciones: quién se parece a quién.

Para qué sirve
--------------
La pregunta que contesta es "¿qué alumnos se parecen entre sí?". La respuesta
no está en ninguna columna: está en **con qué comparten conexión**. Dos alumnos
que estudian violín aparecen juntos alrededor del mismo nodo; dos hermanos
aparecen juntos alrededor de su tutor.

Por qué no se dibuja todo junto
-------------------------------
Un grafo con las 240 personas, sus 194 relaciones y sus 129 instrumentos es una
maraña: se ve impresionante y no se puede leer nada. Por eso hay **lentes**, y
cada una responde una pregunta distinta con el mínimo de nodos que hace falta.

Por qué SVG y no una librería de gráficas
-----------------------------------------
En este equipo **ninguna** librería de gráficas de Streamlit dibuja nada:
plotly, altair y hasta los gráficos nativos salen vacíos, sin error. Se
comprobó con una app mínima. Así que el grafo se dibuja como SVG en línea, que
es lo mismo que hace el pentagrama del navegador y funciona sin depender de
nada. De paso queda con la tipografía y los colores de la casa, cosa que con
una librería costaría pelear.

El clic funciona con un enlace y parámetros en la dirección
(`?seccion=grafo&nodo=PER-0001`), no con JavaScript. La sección viaja junto al
nodo para que la recarga devuelva al usuario justo donde estaba.

Color y forma
-------------
Tres tipos de nodo, con la paleta validada contra daltonismo y contraste
(`scripts/validate_palette.js` del skill de visualización, las cinco
comprobaciones en PASS sobre el papel `#FCFBF8`):

    alumno       #B33844   negra     (cabeza llena + plica)
    persona      #1F6FB2   corchea   (cabeza llena + plica + corchete) — tutor, contacto
    instrumento  #A87200   redonda   (cabeza hueca, sin plica)

No hay nodo de maestro: el formulario de inscripcion no pregunta quien da la
clase (se revisaron sus 77 campos), asi que dibujarlo seria prometer algo que
el dato no sostiene. Cuando exista —probablemente desde Kydemy— entra como
`relaciones` de tipo `profesor` ligadas AL ALUMNO, no al instrumento.

Cada nodo es una **figura musical**, y la figura va además del color: la
identidad de un nodo nunca debe depender solo del color. La elección no es
caprichosa: el instrumento es una redonda —la figura que más dura, la que
sostiene— y el alumno una negra, la figura de todos los días.

La paleta pasa las cinco comprobaciones del validador sobre el papel `#FCFBF8`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import networkx as nx
import pandas as pd

from lisart import io

# Paleta categórica validada. No cambiar sin volver a correr el validador.
COLORES = {"alumno": "#B33844", "persona": "#1F6FB2", "instrumento": "#A87200"}
FIGURA = {"alumno": "negra", "persona": "corchea", "instrumento": "redonda"}
ETIQUETA_TIPO = {
    "alumno": "Alumno · negra",
    "persona": "Tutor o contacto · corchea",
    "instrumento": "Instrumento · redonda",
}

ANCHO, ALTO = 1000, 560

# Estilos incrustados en el propio SVG: así se ve igual aunque se exporte
# suelto, fuera de la aplicación.
_ESTILOS = """
body { margin: 0; background: #FFFFFF; font-family: 'IBM Plex Sans', system-ui, sans-serif; }
.lis-grafo svg { display: block; width: 100%; height: auto; }
.arista { fill: none; stroke: #E7E1D6; stroke-width: 1; }
.arista--viva { stroke: #B33844; stroke-width: 1.6; }
.nodo { cursor: pointer; }
.blanco { fill: transparent; pointer-events: all; }
.cabeza { stroke: #FFFFFF; stroke-width: 1.4; }
.cabeza--hueca { stroke-width: 2.6; }
.plica, .corchete { fill: none; stroke-width: 1.8; stroke-linecap: round; }
.n--alumno { fill: #B33844; }
.n--persona { fill: #1F6FB2; }
.n--instrumento { fill: #A87200; }
.cabeza--hueca.n--instrumento { fill: #FFFFFF; stroke: #A87200; }
.plica.n--alumno, .corchete.n--alumno { stroke: #B33844; }
.plica.n--persona, .corchete.n--persona { stroke: #1F6FB2; }
.es--elegido.cabeza { stroke: #131211; stroke-width: 3; }
.es--lejos { opacity: .2; }
.nodo:hover .cabeza { stroke: #131211; stroke-width: 2.4; }
.nodo:focus-visible .cabeza { stroke: #131211; stroke-width: 3; outline: none; }
.rotulo { font-size: 12px; font-weight: 600; fill: #131211; text-anchor: middle;
  pointer-events: none; paint-order: stroke; stroke: #FFFFFF; stroke-width: 3.5; }
"""

PAPEL = "#FCFBF8"
LINEA = "#DDD6C8"
TINTA = "#131211"
TINTA_3 = "#948C84"

LENTES = {
    "instrumentos": "Alumnos por instrumento",
    "familias": "Familias: alumnos y sus tutores",
    "todo": "Todo junto: instrumentos y familias",
}


@dataclass
class Nodo:
    id: str
    etiqueta: str
    tipo: str
    grado: int = 0
    resumen: str = ""
    """Lo que se ve al pasar el ratón: quién es y qué lo conecta."""


def _nombre_visible(personas: pd.DataFrame) -> dict[str, str]:
    if personas.empty:
        return {}
    completo = (
        personas["nombre"].fillna("").astype(str)
        + " " + personas["apellido_paterno"].fillna("").astype(str)
        + " " + personas["apellido_materno"].fillna("").astype(str)
    ).str.replace(r"\s+", " ", regex=True).str.strip()
    return dict(zip(personas["persona_id"].astype(str), completo, strict=False))


def construir(lente: str, instrumento: str | None = None) -> tuple[nx.Graph, dict[str, Nodo]]:
    """Arma el grafo de la lente pedida. Devuelve (grafo, nodos por id)."""
    personas = io.read_table("personas")
    nombres = _nombre_visible(personas)
    grafo = nx.Graph()
    nodos: dict[str, Nodo] = {}

    def agregar(id_: str, etiqueta: str, tipo: str) -> str:
        if id_ not in nodos:
            nodos[id_] = Nodo(id_, etiqueta, tipo)
            grafo.add_node(id_)
        return id_

    if lente in ("instrumentos", "todo"):
        catalogo = io.read_table("instrumentos").set_index("instrumento_id")
        ligas = io.read_table("alumnos_instrumentos")
        if instrumento:
            ligas = ligas[ligas["instrumento_id"] == instrumento]
        for _, fila in ligas.iterrows():
            ins, alu = str(fila["instrumento_id"]), str(fila["persona_id"])
            nombre_ins = (
                str(catalogo.loc[ins, "nombre"]) if ins in catalogo.index else ins
            )
            agregar(ins, nombre_ins, "instrumento")
            agregar(alu, nombres.get(alu, alu), "alumno")
            grafo.add_edge(ins, alu)

    if lente in ("familias", "todo"):
        relaciones = io.read_table("relaciones")
        relaciones = relaciones[relaciones["tipo"] == "tutor"]
        if instrumento:
            ligas = io.read_table("alumnos_instrumentos")
            del_instrumento = set(
                ligas[ligas["instrumento_id"] == instrumento]["persona_id"].astype(str)
            )
            relaciones = relaciones[
                relaciones["alumno_persona_id"].astype(str).isin(del_instrumento)
            ]
        for _, fila in relaciones.iterrows():
            alu, tut = str(fila["alumno_persona_id"]), str(fila["relacionado_persona_id"])
            agregar(alu, nombres.get(alu, alu), "alumno")
            agregar(tut, nombres.get(tut, tut), "persona")
            grafo.add_edge(alu, tut)

    for id_, nodo in nodos.items():
        nodo.grado = grafo.degree(id_)

    # La frase del hover: quién es el nodo y con qué está conectado. Sin esto
    # el grafo obliga a hacer clic para saber a quién se está mirando.
    sustantivo = {"alumno": "alumno", "persona": "tutor o contacto"}
    for id_, nodo in nodos.items():
        con = sorted(
            nodos[v].etiqueta for v in grafo.neighbors(id_) if nodos[v].tipo != "alumno"
        )
        if nodo.tipo == "instrumento":
            plural = "alumno" if nodo.grado == 1 else "alumnos"
            nodo.resumen = f"{nodo.etiqueta} · instrumento · {nodo.grado} {plural}"
        elif nodo.tipo == "persona":
            plural = "alumno" if nodo.grado == 1 else "alumnos"
            nodo.resumen = (
                f"{nodo.etiqueta} · {sustantivo[nodo.tipo]} de {nodo.grado} {plural}"
            )
        else:
            cola = " · ".join(con) if con else "sin instrumento registrado"
            nodo.resumen = f"{nodo.etiqueta} · alumno · {cola}"

    return grafo, nodos


def _posiciones(grafo: nx.Graph, nodos: dict[str, Nodo]) -> dict[str, tuple[float, float]]:
    """Coloca los nodos en racimos legibles.

    Un `spring_layout` sobre estos datos no sirve: como cada instrumento con
    sus alumnos es casi un componente aparte, el algoritmo los repele hasta los
    bordes y deja el centro apelmazado. Se ve disperso y apretado a la vez.

    Aquí el acomodo es explícito y en dos pasos:

    1. Los **centros** (el instrumento, o el tutor según la lente) se colocan
       con spring_layout sobre un grafo reducido donde dos centros se unen si
       comparten alumnos. Así los instrumentos que comparten gente quedan
       cerca, que es información de verdad y no azar.
    2. Los **alumnos** se reparten en un anillo alrededor de su centro. El que
       estudia dos instrumentos se coloca entre los dos: en el dibujo se ve
       literalmente como un puente, que es justo lo que es.

    La escala se ajusta para que ningún anillo invada al vecino.
    """
    if not len(grafo):
        return {}

    centros = [n.id for n in nodos.values() if n.tipo in ("instrumento", "persona")]
    if not centros:
        return _posiciones_libres(grafo)

    # Radio del anillo de cada centro, según cuántos cuelgan de él.
    miembros = {c: [v for v in grafo.neighbors(c) if nodos[v].tipo == "alumno"] for c in centros}
    radio = {c: 26 + 5.0 * max(len(m), 1) ** 0.62 for c, m in miembros.items()}

    # Grafo reducido: dos centros se tocan si comparten algún alumno.
    reducido = nx.Graph()
    reducido.add_nodes_from(centros)
    for a in centros:
        for b in centros:
            if a < b and set(miembros[a]) & set(miembros[b]):
                reducido.add_edge(a, b)

    crudas = nx.spring_layout(reducido, seed=7, k=1.0, iterations=300)
    pos_centros = _separar(_escalar(crudas, radio), radio)

    pos: dict[str, tuple[float, float]] = dict(pos_centros)
    colocados: set[str] = set()

    for c in centros:
        exclusivos = [m for m in miembros[c] if grafo.degree(m) == 1]
        cx, cy = pos_centros[c]
        for i, alumno in enumerate(sorted(exclusivos)):
            angulo = 2 * math.pi * i / max(len(exclusivos), 1) - math.pi / 2
            r = radio[c] * (0.72 if i % 2 else 1.0)
            pos[alumno] = (cx + math.cos(angulo) * r, cy + math.sin(angulo) * r)
            colocados.add(alumno)

    # Los que cuelgan de varios centros van entre ellos: son los puentes.
    for nodo in nodos.values():
        if nodo.tipo != "alumno" or nodo.id in colocados:
            continue
        suyos = [v for v in grafo.neighbors(nodo.id) if v in pos_centros]
        if not suyos:
            pos[nodo.id] = (ANCHO / 2, ALTO / 2)
            continue
        x = sum(pos_centros[s][0] for s in suyos) / len(suyos)
        y = sum(pos_centros[s][1] for s in suyos) / len(suyos)
        # Un pelo de dispersión para que dos puentes iguales no se encimen.
        giro = (hash(nodo.id) % 360) * math.pi / 180
        pos[nodo.id] = (x + math.cos(giro) * 16, y + math.sin(giro) * 16)

    for id_ in grafo.nodes():
        pos.setdefault(id_, (ANCHO / 2, ALTO / 2))
    return pos


def _escalar(crudas: dict, radio: dict) -> dict[str, tuple[float, float]]:
    """Lleva las posiciones al lienzo dejando aire suficiente entre anillos."""
    ids = list(crudas)
    xs = [crudas[i][0] for i in ids]
    ys = [crudas[i][1] for i in ids]
    ancho_x = (max(xs) - min(xs)) or 1
    ancho_y = (max(ys) - min(ys)) or 1

    mayor = max(radio.values())
    margen = mayor + 26
    util_x, util_y = ANCHO - 2 * margen, ALTO - 2 * margen
    return {
        i: (
            margen + (crudas[i][0] - min(xs)) / ancho_x * util_x,
            margen + (crudas[i][1] - min(ys)) / ancho_y * util_y,
        )
        for i in ids
    }


def _separar(pos: dict[str, tuple[float, float]], radio: dict) -> dict[str, tuple[float, float]]:
    """Empuja los centros hasta que ningún anillo invada al de al lado.

    El spring_layout no sabe de los anillos que vamos a dibujar encima, así que
    deja centros a trece píxeles y los racimos se encimarían. Esto es un
    empujón repetido: mientras dos se solapen, se apartan por su eje.
    """
    ids = list(pos)
    lugar = {i: list(pos[i]) for i in ids}
    aire = 22

    for _ in range(400):
        movio = False
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                dx = lugar[b][0] - lugar[a][0]
                dy = lugar[b][1] - lugar[a][1]
                dist = (dx * dx + dy * dy) ** 0.5 or 0.01
                minima = radio[a] + radio[b] + aire
                if dist >= minima:
                    continue
                empuje = (minima - dist) / 2
                ux, uy = dx / dist, dy / dist
                lugar[a][0] -= ux * empuje
                lugar[a][1] -= uy * empuje
                lugar[b][0] += ux * empuje
                lugar[b][1] += uy * empuje
                movio = True
        if not movio:
            break

    # Volver a encuadrar en el lienzo después de los empujones.
    xs = [lugar[i][0] for i in ids]
    ys = [lugar[i][1] for i in ids]
    mayor = max(radio.values())
    margen = mayor + 24
    escala = min(
        (ANCHO - 2 * margen) / ((max(xs) - min(xs)) or 1),
        (ALTO - 2 * margen) / ((max(ys) - min(ys)) or 1),
    )
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    return {
        i: (
            ANCHO / 2 + (lugar[i][0] - cx) * escala,
            ALTO / 2 + (lugar[i][1] - cy) * escala,
        )
        for i in ids
    }


def _posiciones_libres(grafo: nx.Graph) -> dict[str, tuple[float, float]]:
    crudas = nx.spring_layout(grafo, seed=7, k=1.1 / max(len(grafo) ** 0.5, 1), iterations=200)
    return _escalar(crudas, dict.fromkeys(crudas, 24))


def _figura(x: float, y: float, radio: float, tipo: str, clase: str, titulo: str) -> str:
    """Dibuja el nodo como figura musical: cabeza (neuma) y plica.

    negra    cabeza llena + plica          alumno
    corchea  cabeza llena + plica + corchete   tutor o contacto
    blanca   cabeza hueca + plica          profesor
    redonda  cabeza hueca, sin plica       instrumento
    """
    figura = FIGURA.get(tipo, "negra")
    hueca = figura in ("blanca", "redonda")
    # La redonda es más ancha que alta, como en la notación real.
    rx = radio * (1.25 if figura == "redonda" else 1.0)
    ry = radio * 0.78

    cabeza = (
        f'<ellipse class="cabeza {clase}" cx="{x:.0f}" cy="{y:.0f}" '
        f'rx="{rx:.0f}" ry="{ry:.0f}" transform="rotate(-20 {x:.0f} {y:.0f})"/>'
    )
    if hueca:
        cabeza = cabeza.replace('class="cabeza', 'class="cabeza cabeza--hueca')

    # Blanco invisible sobre la cabeza: sin él, el centro del enlace cae en el
    # hueco entre la cabeza y la plica y el clic no agarra. (Se quitó un rato
    # por rendimiento; el cuello de botella resultó ser otro.)
    blanco = f'<circle class="blanco" cx="{x:.0f}" cy="{y:.0f}" r="{max(radio * 1.6, 12):.0f}"/>'
    partes = [blanco, cabeza]
    if figura != "redonda":
        largo = radio * 3.4
        px, py = x + rx * 0.92, y - ry * 0.35
        partes.append(
            f'<line class="plica {clase}" x1="{px:.0f}" y1="{py:.0f}" '
            f'x2="{px:.0f}" y2="{py - largo:.0f}"/>'
        )
        if figura == "corchea":
            # El corchete: la curva que cuelga del extremo de la plica.
            partes.append(
                f'<path class="corchete {clase}" d="M{px:.0f} {py - largo:.0f} '
                f'q{radio * 1.5:.0f} {radio * 0.7:.0f} {radio * 0.2:.0f} {radio * 1.9:.0f}"/>'
            )
    # El <title> va como primer hijo de un <g>: así el navegador lo muestra al
    # pasar por encima de cualquier parte de la figura, no solo de la cabeza.
    return f'<g><title>{titulo}</title>' + "".join(partes) + "</g>"


def _partir(texto: str, ancho: int) -> list[str]:
    """Parte un rótulo largo en renglones sin cortar palabras."""
    renglones, actual = [], ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > ancho:
            renglones.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        renglones.append(actual)
    return renglones


def _arista(a: tuple[float, float], b: tuple[float, float], clase: str) -> str:
    """Une dos nodos con un arco, no con una recta.

    Cuarenta y un alumnos colgando del mismo instrumento con líneas rectas se
    ven como un abanico macizo. Curvándolas un poco, cada una se distingue de
    su vecina y el racimo respira.
    """
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    largo = (dx * dx + dy * dy) ** 0.5 or 1
    # Punto de control desplazado perpendicularmente al segmento.
    cx, cy = mx - dy / largo * largo * 0.11, my + dx / largo * largo * 0.11
    return (
        f'<path class="{clase}" d="M{a[0]:.0f} {a[1]:.0f} '
        f'Q{cx:.0f} {cy:.0f} {b[0]:.0f} {b[1]:.0f}"/>'
    )


def svg(grafo: nx.Graph, nodos: dict[str, Nodo], seleccionado: str | None = None) -> str:
    """El grafo dibujado. Devuelve el `<svg>` listo para insertar."""
    if not len(grafo):
        return ""

    pos = _posiciones(grafo, nodos)
    vecinos = set(grafo.neighbors(seleccionado)) if seleccionado in grafo else set()

    lineas = [
        _arista(pos[a], pos[b], "arista arista--viva" if seleccionado in (a, b) else "arista")
        for a, b in grafo.edges()
    ]

    marcas = []
    for nodo in sorted(nodos.values(), key=lambda n: n.grado):
        x, y = pos[nodo.id]
        radio = max(5.5, min(6 + nodo.grado * 0.7, 20))
        if nodo.id == seleccionado:
            estado = " es--elegido"
        elif seleccionado and nodo.id in vecinos:
            estado = " es--vecino"
        elif seleccionado:
            estado = " es--lejos"
        else:
            estado = ""
        clase = f"n--{nodo.tipo}{estado}"
        figura = _figura(x, y, radio, nodo.tipo, clase, nodo.resumen or nodo.etiqueta)
        marcas.append(
            f'<a class="nodo" href="?seccion=grafo&nodo={nodo.id}" target="_self" '
            f'aria-label="{nodo.resumen or nodo.etiqueta}">{figura}</a>'
        )

    # Solo los instrumentos llevan nombre: son pocos y son las anclas del mapa.
    # Etiquetar a los 115 alumnos sería ilegible.
    etiquetas = []
    for n in nodos.values():
        if n.tipo != "instrumento":
            continue
        x, y = pos[n.id]
        base = y + max(5.5, min(6 + n.grado * 0.7, 20)) + 15
        # "Estimulación Musical Temprana" en un renglón se come al vecino.
        renglones = _partir(n.etiqueta, 18)
        etiquetas += [
            f'<text class="rotulo" x="{x:.0f}" y="{base + i * 13:.0f}">{linea}</text>'
            for i, linea in enumerate(renglones)
        ]

    return (
        f"<style>{_ESTILOS}</style>"
        f'<div class="lis-grafo"><svg viewBox="0 0 {ANCHO} {ALTO}" '
        'role="img" aria-label="Grafo de relaciones">'
        + "".join(lineas) + "".join(marcas) + "".join(etiquetas) + "</svg></div>"
    )


# --- Qué se sabe de un nodo --------------------------------------------


def detalle(id_: str, tipo: str) -> dict[str, object]:
    """Lo que hay que saber del nodo, listo para mostrar."""
    if tipo == "instrumento":
        return _detalle_instrumento(id_)
    return _detalle_persona(id_)


def _detalle_instrumento(instrumento_id: str) -> dict[str, object]:
    catalogo = io.read_table("instrumentos").set_index("instrumento_id")
    ligas = io.read_table("alumnos_instrumentos")
    personas = io.read_table("personas")
    nombres = _nombre_visible(personas)

    alumnos = [str(p) for p in ligas[ligas["instrumento_id"] == instrumento_id]["persona_id"]]
    fila = catalogo.loc[instrumento_id] if instrumento_id in catalogo.index else None
    return {
        "titulo": str(fila["nombre"]) if fila is not None else instrumento_id,
        "subtitulo": f"{len(alumnos)} alumno(s)",
        "datos": {
            "Clave": instrumento_id,
            "Familia": (str(fila["familia"]) if fila is not None and pd.notna(fila["familia"])
                        else "—"),
        },
        "listas": {"Quiénes lo estudian": sorted(nombres.get(a, a) for a in alumnos)},
    }


def _detalle_persona(persona_id: str) -> dict[str, object]:
    personas = io.read_table("personas")
    nombres = _nombre_visible(personas)
    fila = personas[personas["persona_id"].astype(str) == persona_id]
    if fila.empty:
        return {"titulo": persona_id, "subtitulo": "", "datos": {}, "listas": {}}
    fila = fila.iloc[0]

    roles = io.read_table("personas_roles")
    mis_roles = sorted(roles[roles["persona_id"].astype(str) == persona_id]["rol"].astype(str))

    alumnos = io.read_table("alumnos")
    mi_alumno = alumnos[alumnos["persona_id"].astype(str) == persona_id]

    datos: dict[str, str] = {
        "Identificador": persona_id,
        "Roles": ", ".join(mis_roles) or "sin rol",
        "Teléfono": _o_raya(fila.get("telefono")),
        "Correo": _o_raya(fila.get("correo")),
    }
    listas: dict[str, list[str]] = {}

    if not mi_alumno.empty:
        alu = mi_alumno.iloc[0]
        datos["Estatus"] = _o_raya(alu.get("estatus"))
        datos["Programa"] = _o_raya(alu.get("programa"))
        datos["Requiere tutor"] = "sí" if alu.get("requiere_tutor") else "no"

        catalogo = io.read_table("instrumentos").set_index("instrumento_id")
        ligas = io.read_table("alumnos_instrumentos")
        mios = ligas[ligas["persona_id"].astype(str) == persona_id]["instrumento_id"]
        listas["Instrumentos"] = [
            str(catalogo.loc[i, "nombre"]) if i in catalogo.index else str(i) for i in mios
        ]

    relaciones = io.read_table("relaciones")
    vinculos = []
    for _, r in relaciones.iterrows():
        alu, otro, tipo = (
            str(r["alumno_persona_id"]), str(r["relacionado_persona_id"]), str(r["tipo"])
        )
        if alu == persona_id:
            vinculos.append(f"{tipo}: {nombres.get(otro, otro)}")
        elif otro == persona_id:
            vinculos.append(f"{tipo} de {nombres.get(alu, alu)}")
    if vinculos:
        listas["Vínculos"] = sorted(vinculos)

    return {
        "titulo": nombres.get(persona_id, persona_id),
        "subtitulo": ", ".join(mis_roles) or "sin rol en la escuela",
        "datos": datos,
        "listas": listas,
    }


def _o_raya(valor) -> str:
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return "—"
    texto = str(valor).strip()
    return texto or "—"


def parecidos(persona_id: str, limite: int = 8) -> list[tuple[str, str]]:
    """Alumnos que comparten instrumento o tutor con este. (nombre, por qué)

    Es la pregunta que motivó el grafo, contestada también en texto: mirar un
    dibujo está bien para explorar, pero para actuar hace falta una lista.
    """
    personas = io.read_table("personas")
    nombres = _nombre_visible(personas)
    ligas = io.read_table("alumnos_instrumentos")
    relaciones = io.read_table("relaciones")
    catalogo = io.read_table("instrumentos").set_index("instrumento_id")

    razones: dict[str, set[str]] = {}

    mios = set(ligas[ligas["persona_id"].astype(str) == persona_id]["instrumento_id"].astype(str))
    for ins in mios:
        etiqueta = str(catalogo.loc[ins, "nombre"]) if ins in catalogo.index else ins
        for otro in ligas[ligas["instrumento_id"].astype(str) == ins]["persona_id"].astype(str):
            if otro != persona_id:
                razones.setdefault(otro, set()).add(etiqueta)

    tutores = relaciones[relaciones["tipo"] == "tutor"]
    mis_tutores = set(
        tutores[tutores["alumno_persona_id"].astype(str) == persona_id][
            "relacionado_persona_id"
        ].astype(str)
    )
    for tutor in mis_tutores:
        hermanos = tutores[tutores["relacionado_persona_id"].astype(str) == tutor]
        for otro in hermanos["alumno_persona_id"].astype(str):
            if otro != persona_id:
                razones.setdefault(otro, set()).add("misma familia")

    ordenados = sorted(razones.items(), key=lambda kv: (-len(kv[1]), nombres.get(kv[0], kv[0])))
    return [
        (nombres.get(pid, pid), " · ".join(sorted(motivos)))
        for pid, motivos in ordenados[:limite]
    ]


def leyenda() -> str:
    """La leyenda dibuja las figuras reales, no puntos de color: así se
    reconoce el nodo en el grafo por su forma y no solo por su tono."""
    piezas = []
    for tipo, etiqueta in ETIQUETA_TIPO.items():
        figura = _figura(11, 20, 6, tipo, f"n--{tipo}", etiqueta)
        piezas.append(
            f'<span class="lis-leyenda__i">'
            f'<svg class="lis-grafo" width="24" height="30" viewBox="0 0 24 30">{figura}</svg>'
            f"{etiqueta}</span>"
        )
    return "".join(piezas)
