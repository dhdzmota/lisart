"""Pruebas del PDF de la guia.

Lo que importa aqui no es que el PDF "se vea bien" —eso se revisa mirandolo—
sino las dos promesas que sostienen el flujo: que el PDF se puede generar **sin
internet**, y que **avisa cuando se quedo atras** del markdown. Sin la segunda,
la guia impresa y la guia real se separan sin que nadie se entere.
"""

import pytest

from lisart import guia

markdown = pytest.importorskip("markdown", reason="`lisart guia` necesita el extra [docs]")


EJEMPLO = """# Guia de prueba

Un subtitulo que en el markdown viene
partido en dos renglones.

Un parrafo de entrada.

## 1. Primera seccion

Contenido.

## 2. Segunda seccion

| a | b |
| --- | --- |
| 1 | 2 |
"""


def test_el_subtitulo_es_el_parrafo_completo():
    """Regresion: tomar solo la primera linea dejaba la portada a medias."""
    titulo, subtitulo, resto = guia._partir_titulo(EJEMPLO)
    assert titulo == "Guia de prueba"
    assert subtitulo == "Un subtitulo que en el markdown viene partido en dos renglones."
    assert resto.lstrip().startswith("Un parrafo de entrada.")


def test_el_html_no_pide_nada_por_internet():
    """Todo va incrustado: el PDF sale igual sin red, hoy y en un año."""
    html = guia.a_html(EJEMPLO)
    assert "https://" not in html
    assert "data:font/woff2;base64," in html


def test_el_indice_lista_las_secciones():
    html = guia.a_html(EJEMPLO)
    assert "1. Primera seccion" in html
    assert "2. Segunda seccion" in html


def test_lo_que_va_antes_de_la_primera_seccion_sube_al_indice():
    """Si no, ese parrafo se lleva una hoja entera para dos renglones."""
    html = guia.a_html(EJEMPLO)
    entrada = html.split('class="entrada"')[1].split("</section>")[0]
    assert "Un parrafo de entrada." in entrada


def test_las_tablas_del_markdown_llegan_como_tablas():
    assert "<table>" in guia.a_html(EJEMPLO)


def test_avisa_cuando_el_pdf_se_quedo_atras(tmp_path):
    doc = guia.Documento("prueba", "Documento de prueba", tmp_path / "doc.md")
    doc.md.write_text(EJEMPLO, encoding="utf-8")
    doc.pdf.write_bytes(b"%PDF-1.4")

    assert not guia.esta_al_dia(doc)          # todavia no hay huella

    doc.huella.write_text(guia.huella_de(EJEMPLO), encoding="utf-8")
    assert guia.esta_al_dia(doc)

    doc.md.write_text(EJEMPLO + "\nUna linea nueva.\n", encoding="utf-8")
    assert not guia.esta_al_dia(doc)


def test_cada_documento_tiene_su_pdf_y_su_huella():
    """El PDF se deriva del .md: no hay forma de apuntar uno al archivo del otro."""
    for clave, doc in guia.DOCUMENTOS.items():
        assert doc.clave == clave
        assert doc.md.suffix == ".md"
        assert doc.pdf.stem == doc.md.stem
        assert doc.huella.stem == doc.md.stem
    assert {d.pdf for d in guia.DOCUMENTOS.values()}.__len__() == len(guia.DOCUMENTOS)


def test_los_documentos_del_repo_existen():
    """Si alguien borra o renombra un .md, `lisart guia` no falla en silencio."""
    for doc in guia.DOCUMENTOS.values():
        assert doc.md.exists(), f"falta {doc.md}"


def test_la_portada_dice_de_donde_sale_cada_documento():
    html = guia.a_html(EJEMPLO, guia.GENERAL)
    assert "docs/documentacion_general.md" in html
    assert "lisart guia general" in html
