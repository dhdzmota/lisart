"""Qué papel juega cada persona en la escuela.

`personas_roles` es una tabla de dos columnas y se lee fatal de frente: una
lista de `PER-0042 · tutor` no contesta ninguna pregunta que alguien se haga de
verdad. Las preguntas reales son dos, y van en direcciones opuestas:

    ¿quiénes son los tutores?        -> `por_rol()`, un directorio
    ¿qué es esta persona?            -> `de_persona()`, un campo de su ficha

Este módulo contesta las dos y, sobre todo, es el único lugar donde se **cambia**
un rol. La pantalla solo llama aquí.

Quitar un rol no lo borra
-------------------------
Cuando alguien deja de ser profesor, su fila no se elimina: se le pone
`vigente_hasta` con la fecha de hoy. Borrarla haría imposible entender después
por qué una clase de marzo estaba asignada a alguien que "nunca fue profesor".
Las columnas de vigencia existían desde el principio para esto; lo que faltaba
era que algo las usara.

Volver a darle el rol a alguien que lo tuvo **reabre la misma fila** (borra la
fecha de cierre) en vez de crear otra: la llave primaria es (persona, rol), y
tener dos filas para lo mismo es como se empieza a contar doble.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lisart import backup, io
from lisart.ids import ahora, nombre_completo
from lisart.tables import PERSONAS_ROLES

TABLA = PERSONAS_ROLES.name

#: Los roles que reconoce el modelo, en el orden en que conviene ofrecerlos.
#: Sale del esquema, no de una lista aparte: si mañana se agrega uno en
#: `tables.py`, aparece solo en la pantalla.
ROLES: tuple[str, ...] = PERSONAS_ROLES.column("rol").choices or ()


@dataclass
class Cambios:
    """Qué se movió al sincronizar. La pantalla lo usa para decirlo en palabras."""

    agregados: list[str] = field(default_factory=list)
    reabiertos: list[str] = field(default_factory=list)
    cerrados: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.agregados or self.reabiertos or self.cerrados)

    def resumen(self) -> str:
        partes = []
        if self.agregados:
            partes.append(f"se agregó {', '.join(self.agregados)}")
        if self.reabiertos:
            partes.append(f"se reactivó {', '.join(self.reabiertos)}")
        if self.cerrados:
            partes.append(f"se cerró {', '.join(self.cerrados)}")
        return "; ".join(partes) or "sin cambios en los roles"


# --- Consultar ---------------------------------------------------------


def esta_vigente(fila) -> bool:
    """Un rol vale mientras no tenga fecha de cierre."""
    valor = fila.get("vigente_hasta")
    return valor is None or pd.isna(valor)


def vigentes(tabla: pd.DataFrame | None = None) -> pd.DataFrame:
    """Solo los roles que la persona tiene hoy."""
    datos = io.read_table(TABLA, strict=False) if tabla is None else tabla
    if datos.empty:
        return datos
    return datos[datos["vigente_hasta"].isna()]


def de_persona(persona_id: str, tabla: pd.DataFrame | None = None) -> list[str]:
    """Los roles vigentes de una persona, en el orden del catálogo."""
    datos = vigentes(tabla)
    if datos.empty:
        return []
    suyos = set(datos[datos["persona_id"].astype(str) == str(persona_id)]["rol"].astype(str))
    return [rol for rol in ROLES if rol in suyos]


def por_rol(rol: str, *, incluir_cerrados: bool = False) -> pd.DataFrame:
    """Quiénes tienen ese rol. Devuelve nombre y datos de contacto, no claves.

    Es el directorio: la respuesta a "¿quiénes son los tutores?" tiene que poder
    leerse en voz alta, y `PER-0117` no se lee en voz alta.
    """
    columnas = ["persona_id", "nombre", "telefono", "correo", "otros_roles", "vigente_hasta"]
    todos = io.read_table(TABLA, strict=False)
    if todos.empty:
        return pd.DataFrame(columns=columnas)

    del_rol = todos[todos["rol"].astype(str) == rol]
    if not incluir_cerrados:
        del_rol = del_rol[del_rol["vigente_hasta"].isna()]
    if del_rol.empty:
        return pd.DataFrame(columns=columnas)

    personas = {
        str(p["persona_id"]): p
        for _, p in io.read_table("personas", strict=False).iterrows()
    }
    vig = vigentes(todos)
    otros_de = {
        persona_id: set(grupo["rol"].astype(str))
        for persona_id, grupo in vig.groupby(vig["persona_id"].astype(str))
    }

    filas = []
    for _, fila in del_rol.iterrows():
        persona_id = str(fila["persona_id"])
        persona = personas.get(persona_id)
        otros = [r for r in ROLES if r != rol and r in otros_de.get(persona_id, set())]
        filas.append({
            "persona_id": persona_id,
            "nombre": (
                nombre_completo(
                    persona["nombre"], persona["apellido_paterno"], persona["apellido_materno"]
                )
                if persona is not None
                else persona_id
            ),
            "telefono": None if persona is None else persona["telefono"],
            "correo": None if persona is None else persona["correo"],
            "otros_roles": ", ".join(otros),
            "vigente_hasta": fila["vigente_hasta"],
        })

    return (
        pd.DataFrame(filas, columns=columnas)
        .sort_values("nombre", key=lambda s: s.str.lower())
        .reset_index(drop=True)
    )


def conteo() -> dict[str, int]:
    """Cuántas personas tiene cada rol hoy. Para las etiquetas del directorio."""
    datos = vigentes()
    if datos.empty:
        return dict.fromkeys(ROLES, 0)
    cuenta = datos["rol"].astype(str).value_counts()
    return {rol: int(cuenta.get(rol, 0)) for rol in ROLES}


# --- Cambiar -----------------------------------------------------------


def aplicar(
    tabla: pd.DataFrame, persona_id: str, seleccion, *, hoy: date | None = None
) -> tuple[pd.DataFrame, Cambios]:
    """La tabla con los roles de esa persona puestos al día. **No escribe.**

    Separado de `sincronizar()` para poder probarlo sin tocar el disco, que es
    donde vive la parte delicada: reabrir en vez de duplicar, y cerrar en vez de
    borrar.
    """
    dia = hoy or date.today()
    momento = ahora()
    quiere = {r for r in seleccion if r in ROLES}
    cambios = Cambios()
    datos = tabla.copy()

    mio = datos["persona_id"].astype(str) == str(persona_id)
    tiene = {str(r) for r in datos.loc[mio, "rol"]}

    for rol in ROLES:
        fila = mio & (datos["rol"].astype(str) == rol)
        abierta = fila & datos["vigente_hasta"].isna()

        if rol in quiere and rol not in tiene:
            nueva = {
                "persona_id": str(persona_id), "rol": rol,
                "vigente_desde": dia, "vigente_hasta": None,
                "creado_en": momento, "actualizado_en": momento, "fuente": "manual",
            }
            datos = pd.concat([datos, pd.DataFrame([nueva])], ignore_index=True)
            cambios.agregados.append(rol)
            # `datos` cambió de tamaño: hay que rehacer las máscaras.
            mio = datos["persona_id"].astype(str) == str(persona_id)
        elif rol in quiere and not abierta.any():
            datos.loc[fila, "vigente_hasta"] = None
            datos.loc[fila, "actualizado_en"] = momento
            cambios.reabiertos.append(rol)
        elif rol not in quiere and abierta.any():
            datos.loc[abierta, "vigente_hasta"] = dia
            datos.loc[abierta, "actualizado_en"] = momento
            cambios.cerrados.append(rol)

    return datos, cambios


def sincronizar(persona_id: str, seleccion, *, hoy: date | None = None) -> Cambios:
    """Deja los roles de una persona como dice `seleccion`, y lo guarda.

    Como todo lo que escribe en `master`, pasa por `guardar_con_respaldo`: valida
    primero y deja copia del estado anterior.
    """
    tabla = io.read_table(TABLA, strict=False)
    actualizada, cambios = aplicar(tabla, persona_id, seleccion, hoy=hoy)
    if cambios:
        backup.guardar_con_respaldo(TABLA, actualizada, motivo="roles")
    return cambios
