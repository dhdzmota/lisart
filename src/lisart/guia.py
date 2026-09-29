"""Los documentos del repo, en PDF.

Son tres, y los tres siguen la misma regla: se escriben en markdown dentro de
`docs/` y de ahi salen en PDF, que es la version que se le pasa a alguien que no
vive en una terminal: se abre con doble clic, se imprime, se manda por correo y
se lee en el telefono.

    docs/guia_de_uso.md ............ como se usa el sistema (operativo)
    docs/documentacion_general.md .. que se construyo y por que (para direccion)
    docs/mapa_del_codigo.md ........ jerarquia y reparto de los modulos (entrega)

    lisart guia            # regenera los PDF que hagan falta
    lisart guia general    # solo ese
    lisart guia --check    # avisa si algun PDF se quedo atras de su .md

**Un solo original.** El texto se escribe UNA vez, en el markdown. El PDF nunca
se edita: se regenera. Dos documentos que se editan por separado se contradicen
en la segunda semana, y el que este equivocado va a ser justo el que alguien
tenga impreso.

Como se hace
------------
markdown -> HTML -> Chromium (Playwright) -> PDF.

Chromium porque ya estaba instalado para revisar la pantalla, porque pagina bien
y porque es lo unico que no obliga a instalar LaTeX. Las fuentes y el logo van
**incrustados** en el HTML como data URI: el PDF se genera igual sin internet, y
sale identico hoy que en un ano.

Como se sabe si el PDF quedo viejo
----------------------------------
Al generarlo se guarda junto al PDF, en un `.sha256`, la huella del markdown que
lo produjo. `lisart guia --check` la vuelve a calcular y compara. Eso corre
dentro de `make check`, asi que editar el .md y olvidar el PDF **truena la
revision** en vez de pasar inadvertido.
"""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lisart.config import PROJECT_ROOT

DIR_DOCS = PROJECT_ROOT / "docs"

DIR_FUENTES = PROJECT_ROOT / "assets" / "fuentes"
LOGO = PROJECT_ROOT / "assets" / "imagenes" / "lisart_wordmark.png"

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# Las mismas de la pantalla (`assets/estilo.css`), por la misma razon: quien
# recibe el PDF y quien usa el sistema tienen que sentir que son la misma cosa.
TIPOGRAFIAS = (
    # (familia, archivo, peso)
    ("Bodoni Moda", "BodoniModa-600.woff2", 600),
    ("IBM Plex Sans", "IBMPlexSans-400.woff2", 400),
    ("IBM Plex Sans", "IBMPlexSans-600.woff2", 600),
    ("IBM Plex Mono", "IBMPlexMono-400.woff2", 400),
)


class FaltaDependencia(RuntimeError):
    """No estan instaladas las piezas para generar el PDF."""


@dataclass(frozen=True)
class Documento:
    """Un documento que se escribe en markdown y se entrega en PDF.

    El PDF y la huella **se derivan** del nombre del markdown en vez de
    escribirse aparte: tres rutas sueltas por documento es como se termina
    generando el PDF de uno con el texto del otro.
    """

    clave: str      # como se pide en la linea de comandos
    nombre: str     # como se llama en el pie de pagina
    md: Path

    @property
    def pdf(self) -> Path:
        return self.md.with_suffix(".pdf")

    @property
    def huella(self) -> Path:
        return self.md.with_suffix(".sha256")

    @property
    def comando(self) -> str:
        return f"lisart guia {self.clave}"


# El nombre lleva acentos porque sale impreso en el pie de cada pagina.
GUIA = Documento("guia", "Guía de uso", DIR_DOCS / "guia_de_uso.md")
GENERAL = Documento(
    "general", "Documentación general", DIR_DOCS / "documentacion_general.md"
)
CODIGO = Documento("codigo", "Mapa del código", DIR_DOCS / "mapa_del_codigo.md")
ENTREGA = Documento("entrega", "Guía de entrega", DIR_DOCS / "guia_de_entrega.md")

# El orden importa: es el que sigue `lisart guia` sin argumentos.
DOCUMENTOS: dict[str, Documento] = {
    d.clave: d for d in (GUIA, GENERAL, CODIGO, ENTREGA)
}


@dataclass
class Resultado:
    documento: Documento
    pdf: Path
    paginas: int = 0
    huella: str = ""


# --- Huella -------------------------------------------------------------


def huella_de(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def esta_al_dia(doc: Documento = GUIA) -> bool:
    """Si el PDF corresponde al markdown que hay hoy."""
    if not doc.pdf.exists() or not doc.huella.exists():
        return False
    return doc.huella.read_text(encoding="utf-8").strip() == huella_de(
        doc.md.read_text(encoding="utf-8")
    )


def desactualizados() -> list[Documento]:
    """Los documentos cuyo PDF se quedo atras de su markdown."""
    return [d for d in DOCUMENTOS.values() if not esta_al_dia(d)]


# --- De markdown a HTML -------------------------------------------------


def _incrustar(ruta: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def _caras() -> str:
    """Las @font-face con la letra incrustada, para no depender de internet."""
    reglas = []
    for familia, archivo, peso in TIPOGRAFIAS:
        ruta = DIR_FUENTES / archivo
        if not ruta.exists():
            continue
        reglas.append(
            f"@font-face{{font-family:'{familia}';font-style:normal;font-weight:{peso};"
            f"src:url({_incrustar(ruta, 'font/woff2')}) format('woff2');}}"
        )
    return "\n".join(reglas)


def _portada(titulo: str, subtitulo: str, doc: Documento) -> str:
    hoy = date.today()
    marca = (
        f'<img class="marca" src="{_incrustar(LOGO, "image/png")}" alt="Lisart">'
        if LOGO.exists()
        else '<p class="marca-texto">LISART</p>'
    )
    ruta = doc.md.relative_to(PROJECT_ROOT).as_posix()
    return f"""
<section class="portada">
  {marca}
  <h1 class="portada__t">{titulo}</h1>
  <p class="portada__s">{subtitulo}</p>
  <p class="portada__f">Actualizada el {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}</p>
  <p class="portada__n">Este documento se genera desde <code>{ruta}</code>.
  No se edita a mano: se regenera con <code>{doc.comando}</code>.</p>
</section>
"""


def _partir_titulo(texto: str) -> tuple[str, str, str]:
    """(titulo, subtitulo, resto) — el H1 y el parrafo que le sigue van a la portada.

    El subtitulo es el parrafo **completo**, no su primera linea: en markdown un
    parrafo se escribe repartido en varios renglones y cortarlo por el primero
    deja la portada con una frase a medias.
    """
    lineas = texto.splitlines()
    titulo, inicio = "Documento", 0
    for numero, linea in enumerate(lineas):
        if linea.startswith("# "):
            titulo = linea[2:].strip()
            inicio = numero + 1
            break

    while inicio < len(lineas) and not lineas[inicio].strip():
        inicio += 1
    parrafo: list[str] = []
    while inicio < len(lineas) and lineas[inicio].strip():
        parrafo.append(lineas[inicio].strip())
        inicio += 1

    return titulo, " ".join(parrafo), "\n".join(lineas[inicio:])


def _tabla_de_contenido(html: str) -> str:
    """Indice de las secciones de primer nivel, con su numero."""
    entradas = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', html, flags=re.S)
    if not entradas:
        return ""
    filas = "".join(
        f'<li><a href="#{ancla}">{re.sub("<[^>]+>", "", texto).strip()}</a></li>'
        for ancla, texto in entradas
    )
    return f'<nav class="indice"><h2 class="indice__t">Contenido</h2><ol>{filas}</ol></nav>'


def a_html(markdown_texto: str, doc: Documento = GUIA) -> str:
    """El HTML completo, con todo incrustado. Separado para poder probarlo."""
    try:
        import markdown as md
    except ModuleNotFoundError as error:  # pragma: no cover - depende del entorno
        raise FaltaDependencia(
            "Falta la libreria 'markdown'. Instalar con: uv pip install -e \".[docs]\""
        ) from error

    titulo, subtitulo, cuerpo = _partir_titulo(markdown_texto)
    convertidor = md.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"],
        extension_configs={"toc": {"permalink": False}},
    )
    contenido = convertidor.convert(cuerpo)

    # Lo que va antes de la primera seccion sube a la pagina del indice: cada
    # seccion empieza en pagina nueva, y dejar ahi ese parrafo suelto gastaba
    # una hoja entera para dos renglones.
    corte = contenido.find("<h2")
    entrada, cuerpo_html = (contenido[:corte], contenido[corte:]) if corte > 0 else ("", contenido)

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{titulo} · Lisart</title>
<style>
{_caras()}
{ESTILO}
</style></head>
<body>
{_portada(titulo, subtitulo, doc)}
<section class="entrada">{entrada}</section>
{_tabla_de_contenido(contenido)}
<main>{cuerpo_html}</main>
</body></html>"""


# --- El diseño ----------------------------------------------------------
#
# Impreso, no en pantalla: la letra es serif para el cuerpo largo, las tablas
# llevan filete fino y cada seccion empieza en pagina nueva para poder decir
# "esta en la 4". El oro NO se reparte: vive en la portada y en nada mas.

ESTILO = """
:root{
  --tinta:#131211; --tinta-2:#3F3B37; --tinta-3:#7C736E;
  --papel:#FFFFFF; --regla:#E6E1D8; --superficie:#F7F5F1;
  --lapiz:#B33844; --oro:#FDBB02;
}
@page{ size:A4; margin:19mm 17mm 16mm; }
*{ box-sizing:border-box; }
body{
  margin:0; color:var(--tinta); background:var(--papel);
  font-family:'IBM Plex Sans',system-ui,sans-serif;
  font-size:10.2pt; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}

/* --- Portada --- */
.portada{
  height:247mm; display:flex; flex-direction:column; justify-content:center;
  break-after:page; text-align:left;
}
.portada .marca{ width:52mm; height:auto; margin-bottom:14mm; }
.marca-texto{
  font-family:'Bodoni Moda',serif; font-size:24pt;
  letter-spacing:.22em; margin:0 0 14mm;
}
.portada__t{
  font-family:'Bodoni Moda',Georgia,serif; font-weight:600;
  font-size:40pt; line-height:1.05; margin:0; letter-spacing:-.01em;
}
.portada__t::after{
  content:""; display:block; width:26mm; height:3pt;
  background:var(--oro); margin-top:7mm;
}
.portada__s{ font-size:13pt; color:var(--tinta-2); margin:8mm 0 0; max-width:120mm; }
.portada__f{ font-size:9.5pt; color:var(--tinta-3); margin:22mm 0 0; }
.portada__n{ font-size:8.6pt; color:var(--tinta-3); margin:2mm 0 0; max-width:110mm; }

/* --- Entrada e indice --- */
.entrada{ margin-bottom:9mm; font-size:10.6pt; color:var(--tinta-2); }
.entrada hr{ display:none; }
.indice{ break-after:page; }
.indice__t{ border:0; padding:0; margin:0 0 6mm; break-before:avoid; }
.indice ol{ list-style:none; counter-reset:s; padding:0; margin:0; }
.indice li{ counter-increment:s; border-bottom:1px solid var(--regla); padding:2.6mm 0; }
.indice a{ color:var(--tinta); text-decoration:none; font-size:11pt; }

/* --- Titulos --- */
h2,h3,h4{ font-family:'Bodoni Moda',Georgia,serif; font-weight:600; color:var(--tinta); }
h2{
  font-size:21pt; line-height:1.15; margin:0 0 6mm;
  padding-bottom:2.5mm; border-bottom:1.6pt solid var(--tinta);
  break-before:page; break-after:avoid;
}
h3{ font-size:13.5pt; margin:8mm 0 2.5mm; break-after:avoid; }
h4{ font-size:11pt; margin:6mm 0 2mm; break-after:avoid; }
p{ margin:0 0 3.2mm; }
strong{ font-weight:600; }
a{ color:var(--lapiz); text-decoration:none; }

/* --- Listas --- */
ul,ol{ margin:0 0 3.5mm; padding-left:5.5mm; }
li{ margin-bottom:1.4mm; }
li::marker{ color:var(--tinta-3); }

/* --- Codigo --- */
code{
  font-family:'IBM Plex Mono',ui-monospace,monospace; font-size:8.8pt;
  background:var(--superficie); padding:.4mm 1.1mm; border-radius:1.5pt;
  color:var(--tinta);
}
pre{
  background:var(--superficie); border-left:2.2pt solid var(--lapiz);
  padding:3.2mm 4mm; margin:0 0 4mm; border-radius:2pt;
  break-inside:avoid; white-space:pre-wrap; word-break:break-word;
}
pre code{ background:none; padding:0; font-size:8.6pt; line-height:1.5; }

/* --- Tablas --- */
table{
  width:100%; border-collapse:collapse; margin:0 0 4.5mm;
  font-size:9.2pt; break-inside:avoid;
}
/* Una tabla corta no se parte: se pasa entera a la hoja siguiente. Una larga
   NO cabe en ninguna hoja, y forzarla a no partirse desperdicia una plana en
   blanco antes de partirla igual. De ocho filas para arriba se deja partir,
   con el encabezado repetido en cada hoja y sin cortar ninguna fila. */
table:has(tbody tr:nth-child(8)){ break-inside:auto; }
thead{ display:table-header-group; }
tr{ break-inside:avoid; }
th{
  text-align:left; font-weight:600; font-size:7.6pt; letter-spacing:.09em;
  text-transform:uppercase; color:var(--tinta-3);
  border-bottom:1.2pt solid var(--tinta); padding:2mm 2.5mm 1.6mm;
}
td{ border-bottom:1px solid var(--regla); padding:2.1mm 2.5mm; vertical-align:top; }
td code{ font-size:8.2pt; white-space:nowrap; }
tr:nth-child(even) td{ background:#FBFAF8; }

/* --- Citas --- */
blockquote{
  margin:0 0 4mm; padding:3mm 4mm; background:#FBF0F1;
  border-left:2.2pt solid var(--lapiz); border-radius:2pt;
}
blockquote p:last-child{ margin-bottom:0; }

/* Los `---` del markdown separan secciones, y aqui eso ya lo hace el salto de
   pagina. Dejarlos ademas pinta una raya suelta al final de cada hoja. */
hr{ display:none; }
"""

# El pie: numero de pagina a la derecha, nombre del documento a la izquierda.
def _pie(doc: Documento) -> str:
    return f"""
<div style="width:100%;font-family:sans-serif;font-size:7pt;color:#7C736E;
     padding:0 17mm;display:flex;justify-content:space-between;">
  <span>Lisart · {doc.nombre}</span>
  <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>
"""


# --- Generar ------------------------------------------------------------


def generar(doc: Documento = GUIA, salida: Path | None = None) -> Resultado:
    """Escribe el PDF y guarda la huella del markdown que lo produjo."""
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as error:  # pragma: no cover - depende del entorno
        raise FaltaDependencia(
            "Falta Playwright. Instalar con: uv pip install -e \".[docs]\" "
            "&& playwright install chromium"
        ) from error

    texto = doc.md.read_text(encoding="utf-8")
    destino = salida or doc.pdf
    destino.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page()
        pagina.set_content(a_html(texto, doc), wait_until="load")
        pagina.emulate_media(media="print")
        pagina.pdf(
            path=str(destino),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=_pie(doc),
            margin={"top": "19mm", "bottom": "16mm", "left": "17mm", "right": "17mm"},
        )
        navegador.close()

    firma = huella_de(texto)
    if destino == doc.pdf:
        doc.huella.write_text(firma + "\n", encoding="utf-8")
    return Resultado(documento=doc, pdf=destino, paginas=_paginas(destino), huella=firma)


def _paginas(pdf: Path) -> int:
    """Cuantas paginas quedaron. Se lee del propio PDF, sin librerias."""
    crudo = pdf.read_bytes()
    marcas = re.findall(rb"/Type\s*/Page[^s]", crudo)
    return len(marcas)
