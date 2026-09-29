"""Sistema administrativo de la escuela de musica Lisart.

Uso tipico desde un notebook o un script:

    from lisart import read_table, write_table
    from lisart.tables import REGISTRY

    alumnos = read_table("alumnos")
"""

from lisart.io import DataError, empty_frame, read_table, upsert, write_table
from lisart.validate import validate_all, validate_table

__version__ = "0.1.0"

__all__ = [
    "DataError",
    "empty_frame",
    "read_table",
    "upsert",
    "validate_all",
    "validate_table",
    "write_table",
]
