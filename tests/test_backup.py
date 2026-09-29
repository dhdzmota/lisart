"""Pruebas de los respaldos.

Es la red de seguridad de la edicion a mano, asi que lo que importa probar es
que la copia existe ANTES de que el dato se pierda, y que restaurar funciona.
"""

import pandas as pd
import pytest

from lisart import backup, io


def espacio(espacio_id="AULA-1", nombre="Aula 1", **cambios):
    fila = {
        "espacio_id": espacio_id, "nombre": nombre, "tipo": "aula",
        "piso": "planta_baja", "agendable": True, "capacidad": None,
        "equipamiento": None, "notas": None, "activo": True,
    }
    fila.update(cambios)
    return fila


@pytest.fixture
def tabla_con_datos():
    io.write_table("espacios", pd.DataFrame([espacio(), espacio("AULA-2", "Aula 2")]))
    return "espacios"


def test_sin_archivo_no_hay_nada_que_respaldar():
    assert backup.respaldar("espacios") is None


def test_el_respaldo_guarda_el_estado_anterior(tabla_con_datos):
    copia = backup.respaldar(tabla_con_datos)
    assert copia is not None and copia.exists()
    assert copia.read_bytes() == io._resolve("espacios").path.read_bytes()


def test_guardar_respalda_lo_viejo_no_lo_nuevo(tabla_con_datos):
    """El punto entero: la copia tiene que servir para deshacer."""
    nuevo = pd.DataFrame([espacio(nombre="Aula renombrada"), espacio("AULA-2", "Aula 2")])
    _, copia = backup.guardar_con_respaldo(tabla_con_datos, nuevo)

    assert "Aula renombrada" in io._resolve("espacios").path.read_text(encoding="utf-8-sig")
    assert "Aula renombrada" not in copia.read_text(encoding="utf-8-sig")
    assert "Aula 1" in copia.read_text(encoding="utf-8-sig")


def test_un_guardado_invalido_no_escribe_ni_respalda(tabla_con_datos):
    antes = io._resolve("espacios").path.read_bytes()
    malo = pd.DataFrame([espacio(tipo="cafeteria")])  # fuera del catalogo

    with pytest.raises(io.DataError, match="catalogo"):
        backup.guardar_con_respaldo(tabla_con_datos, malo)

    assert io._resolve("espacios").path.read_bytes() == antes
    assert backup.listar("espacios") == []


def test_restaurar_regresa_el_contenido_anterior(tabla_con_datos):
    _, copia = backup.guardar_con_respaldo(
        tabla_con_datos, pd.DataFrame([espacio(nombre="Cambiado")])
    )
    assert len(io.read_table("espacios")) == 1

    backup.restaurar("espacios", copia)
    restaurada = io.read_table("espacios")
    assert len(restaurada) == 2
    assert set(restaurada.nombre) == {"Aula 1", "Aula 2"}


def test_restaurar_tambien_deja_copia_de_lo_que_pisa(tabla_con_datos):
    _, copia = backup.guardar_con_respaldo(
        tabla_con_datos, pd.DataFrame([espacio(nombre="Cambiado")])
    )
    antes = len(backup.listar("espacios"))

    backup.restaurar("espacios", copia)
    assert len(backup.listar("espacios")) == antes + 1


def test_los_respaldos_se_listan_del_mas_nuevo_al_mas_viejo(tabla_con_datos):
    import time

    for nombre in ("uno", "dos", "tres"):
        backup.guardar_con_respaldo(tabla_con_datos, pd.DataFrame([espacio(nombre=nombre)]))
        time.sleep(1.05)  # el sello va al segundo

    copias = backup.listar("espacios")
    assert len(copias) == 3
    assert copias == sorted(copias, reverse=True)


def test_no_se_acumulan_copias_para_siempre(tabla_con_datos, monkeypatch):
    monkeypatch.setattr(backup, "COPIAS_A_CONSERVAR", 3)
    carpeta = backup.backups_dir() / "espacios"
    carpeta.mkdir(parents=True, exist_ok=True)
    for i in range(10):
        (carpeta / f"espacios_2026010{i}T000000.csv").write_text("x", encoding="utf-8")

    backup.respaldar("espacios")
    assert len(backup.listar("espacios")) == 3


def test_respaldar_todo_cubre_la_capa_master(tabla_con_datos):
    io.write_table("personas", io.empty_frame("personas"))
    copias = backup.respaldar_todo("master")

    respaldadas = {c.parent.name for c in copias}
    assert {"espacios", "personas"} <= respaldadas
    assert "respuestas_inscripcion" not in respaldadas  # es capa interim


def test_los_respaldos_viven_fuera_de_las_cuatro_capas():
    """No son parte del flujo de datos: son una red de seguridad aparte."""
    from lisart.config import LAYERS, layer_dir

    assert backup.backups_dir().name == "backups"
    assert all(backup.backups_dir() != layer_dir(capa) for capa in LAYERS)
