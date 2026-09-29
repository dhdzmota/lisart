"""Vocabulario para describir una tabla.

Aqui NO hay tablas concretas, solo las piezas para definirlas. Las tablas
reales viven en `tables.py`.

La idea de fondo: una tabla se describe UNA vez, y de esa descripcion salen
gratis la lectura, la escritura, la validacion y la documentacion. Si el
esquema y el codigo se separan, el esquema siempre pierde.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Tipos que aceptamos en una columna. Se mapean a los dtypes "nullable" de
# pandas (Int64, boolean, string con mayuscula) en vez de los de numpy porque
# esos si distinguen "vacio" de 0 / False, y no convierten enteros a decimales
# en cuanto aparece un nulo.
DType = Literal["string", "int", "float", "bool", "date", "time", "datetime"]

PANDAS_DTYPES: dict[str, str] = {
    "string": "string",
    "int": "Int64",
    "float": "Float64",
    "bool": "boolean",
    "date": "object",  # se guarda como datetime.date, ver io.py
    "time": "object",  # datetime.time, en 24 horas
    "datetime": "datetime64[ns]",
}

Ownership = Literal["managed", "hand_edited"]
#   managed     -> la escribe el codigo. Nadie la abre en Excel.
#   hand_edited -> la mantiene una persona a mano. El codigo la lee y la valida,
#                  pero evita reescribirla sin necesidad.


@dataclass(frozen=True)
class Column:
    """Una columna: como se llama, que guarda y que se le permite."""

    name: str
    dtype: DType
    description: str = ""
    required: bool = True
    """required=True significa 'no puede venir vacia'."""
    unique: bool = False
    choices: tuple[str, ...] | None = None
    """Si se define, el valor tiene que ser uno de estos (catalogo cerrado)."""

    @property
    def pandas_dtype(self) -> str:
        return PANDAS_DTYPES[self.dtype]


@dataclass(frozen=True)
class ForeignKey:
    """`column` de esta tabla tiene que existir en `ref_table.ref_column`.

    Es lo que evita el clasico "pago del alumno 47" cuando el alumno 47 no
    existe. Los CSV no lo checan solos, asi que lo checamos nosotros.
    """

    column: str
    ref_table: str
    ref_column: str
    required: bool = True
    """required=False permite dejarla vacia (relacion opcional)."""


@dataclass(frozen=True)
class Table:
    """La definicion completa de una tabla."""

    name: str
    layer: str
    ownership: Ownership
    primary_key: tuple[str, ...]
    columns: tuple[Column, ...]
    description: str = ""
    foreign_keys: tuple[ForeignKey, ...] = ()
    sort_by: tuple[str, ...] = ()
    """Orden en que se guardan las filas. Por omision, la llave primaria.

    Guardar siempre ordenado hace que los diffs de git sean legibles: cambia
    la linea que cambio y nada mas.
    """

    def __post_init__(self) -> None:
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            raise ValueError(f"{self.name}: columnas repetidas")
        for key in self.primary_key:
            if key not in names:
                raise ValueError(f"{self.name}: la llave primaria usa columna inexistente {key!r}")
        for fk in self.foreign_keys:
            if fk.column not in names:
                raise ValueError(
                    f"{self.name}: la llave foranea usa columna inexistente {fk.column!r}"
                )

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def order_by(self) -> tuple[str, ...]:
        return self.sort_by or self.primary_key

    def column(self, name: str) -> Column:
        for col in self.columns:
            if col.name == name:
                return col
        raise KeyError(f"{self.name}: no existe la columna {name!r}")

    @property
    def encoding(self) -> str:
        from lisart.config import ENCODING_HAND_EDITED, ENCODING_MANAGED

        return ENCODING_HAND_EDITED if self.ownership == "hand_edited" else ENCODING_MANAGED

    @property
    def path(self):
        from lisart.config import layer_dir

        return layer_dir(self.layer) / f"{self.name}.csv"


@dataclass
class Registry:
    """El catalogo de todas las tablas conocidas."""

    tables: dict[str, Table] = field(default_factory=dict)

    def add(self, table: Table) -> Table:
        if table.name in self.tables:
            raise ValueError(f"Tabla duplicada: {table.name}")
        self.tables[table.name] = table
        return table

    def get(self, name: str) -> Table:
        try:
            return self.tables[name]
        except KeyError:
            conocidas = ", ".join(sorted(self.tables))
            raise KeyError(f"Tabla desconocida: {name!r}. Conocidas: {conocidas}") from None

    def __iter__(self):
        return iter(self.tables.values())

    def __len__(self) -> int:
        return len(self.tables)

    def in_dependency_order(self) -> list[Table]:
        """Tablas ordenadas de forma que una tabla salga despues de aquellas a
        las que apunta. Sirve para cargar o validar en el orden correcto."""
        pending = dict(self.tables)
        ordered: list[Table] = []
        while pending:
            libres = [
                t
                for t in pending.values()
                if all(
                    fk.ref_table not in pending or fk.ref_table == t.name
                    for fk in t.foreign_keys
                )
            ]
            if not libres:  # ciclo entre tablas; mejor fallar que colgarse
                ordered.extend(pending.values())
                break
            for t in sorted(libres, key=lambda t: t.name):
                ordered.append(t)
                del pending[t.name]
        return ordered
