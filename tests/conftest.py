"""Configuracion comun de las pruebas.

Las pruebas NUNCA tocan data/ real: cada una corre contra una carpeta temporal
que se borra al terminar. Un test que puede borrar datos de produccion no es un
test, es un riesgo.
"""

import pytest


@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    """Apunta LISART_DATA_DIR a una carpeta temporal para toda la prueba."""
    monkeypatch.setenv("LISART_DATA_DIR", str(tmp_path))
    for capa in ("raw", "interim", "master", "exports"):
        (tmp_path / capa).mkdir()
    return tmp_path
