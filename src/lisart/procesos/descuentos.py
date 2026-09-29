"""Quién tiene descuento y de cuánto.

El catálogo `descuentos` dice qué descuentos existen. Lo que no existía en
ningún lado es **a quién se le aplica cuál**: no viene de Jotform, no viene del
Excel de la escuela, no se puede deducir de nada. Lo decide la administración
caso por caso, así que la única fuente posible es una persona escribiéndolo.

De ahí la forma de `alumnos_descuentos`: es la única tabla del sistema pensada
para abrirse en Excel y editarse a mano.

    lisart descuentos              # mantiene el archivo y avisa de lo que no cuadra
    lisart descuentos --revisar    # solo revisa, no escribe

Cómo se usa
-----------
El archivo lista a **todos** los alumnos inscritos, uno por renglón. Los que
tienen descuento quedan arriba —los renglones con la celda vacía se van al
final al ordenar—, así que se abre y lo primero que se ve es a quién se le está
descontando y por qué.

* **Dar de alta un descuento**: escribir su nombre en la celda `descuento` del
  alumno. El nombre tiene que ser uno del catálogo.
* **Quitarlo**: borrar esa celda.
* **Un segundo descuento**: duplicar el renglón del alumno y cambiarle el
  descuento. El `alumno_descuento_id` se puede dejar vacío; se asigna solo.

Después de editar, correr `lisart descuentos`: rellena los nombres, resuelve la
clave del catálogo, siembra el porcentaje, da de alta a los alumnos nuevos y
**reporta lo que no cuadra en vez de arreglarlo por su cuenta**. Un descuento
mal escrito no se corrige adivinando: se avisa y no se escribe nada.

Las dos decisiones que hay detrás
---------------------------------
1. **El porcentaje se guarda en puntos** (5 es 5%, 100 es beca completa). El
   catálogo de la escuela mezcla unidades en la misma columna —0.05 para un 5%,
   100.00 para una beca— y aplicar eso tal cual cobraría mal. Aquí se traduce a
   una sola unidad, y el archivo es justo el lugar donde una persona lo confirma
   antes de que toque un cobro.

2. **Manda la celda, no el catálogo.** El porcentaje se siembra del catálogo
   pero se puede ajustar por alumno, para pactar un caso particular sin inventar
   una entrada de catálogo. El precio de esa libertad es que subir el descuento
   familiar del 5% al 7% obliga a tocar los renglones que lo tengan: el catálogo
   cambia, esta columna no se entera. Por eso `lisart descuentos` avisa cuando
   una fila se separó del catálogo.

Varios descuentos se **suman** (5% + 10% = 15%), con tope en 100%. Es lo más
fácil de verificar a mano contra un recibo; si la escuela los aplica en cascada,
lo que hay que cambiar es `total_de()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from lisart import backup, io
from lisart.ids import ahora, next_ids, nombre_completo, normalizar_nombre
from lisart.tables import ALUMNOS_DESCUENTOS

TABLA = ALUMNOS_DESCUENTOS.name

# Un alumno cuenta para el archivo mientras esté en la escuela.
ESTATUS_VIGENTES = ("inscrito", "activo")

PORCENTAJE_MAXIMO = 100.0

# Lo que la gente escribe para decir "ninguno". El catálogo de la escuela trae
# un descuento llamado "No" —herencia de una lista desplegable de Excel—, y
# tratarlo como descuento del 0% llenaría el archivo de filas que no dicen nada.
SIN_DESCUENTO = {"no", "ninguno", "ninguna", "n a", "na", "sin descuento", "0"}


@dataclass
class Reporte:
    """Qué pasó al refrescar el archivo. Lo imprime el comando."""

    filas: int = 0
    alumnos: int = 0
    con_descuento: int = 0
    agregados: list[str] = field(default_factory=list)
    retirados: list[str] = field(default_factory=list)
    conservados: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
    escrito: bool = False

    def resumen(self) -> str:
        lineas = [
            f"{self.filas} renglón(es) para {self.alumnos} alumno(s) inscritos.",
            f"  {self.con_descuento} con descuento, {self.alumnos - self.con_descuento} sin.",
        ]
        if self.agregados:
            lineas.append(f"  {len(self.agregados)} alumno(s) nuevos en el archivo.")
        if self.retirados:
            lineas.append(f"  {len(self.retirados)} renglón(es) retirados (ya no inscritos).")
        return "\n".join(lineas)


# --- El catálogo -------------------------------------------------------


def porcentaje_de_catalogo(valor) -> float | None:
    """`descuentos.valor_porcentual` traducido a puntos: 0.05 -> 5, 100.0 -> 100.

    La columna del Excel mezcla las dos unidades. La regla que las separa es
    que **nadie da un descuento de 1% o menos**: lo que viene por debajo de 1
    es una fracción y se multiplica por cien.

    El único valor que quedaría mal interpretado es un 1.00 que quisiera decir
    "1%", y por eso el porcentaje termina escrito en el archivo que una persona
    revisa: si alguna vez existe, ahí se ve y ahí se corrige.
    """
    if valor is None or pd.isna(valor):
        return None
    numero = float(valor)
    return numero * 100 if 0 < numero <= 1 else numero


def _catalogo() -> tuple[dict[str, dict], dict[str, dict]]:
    """(por nombre normalizado, por clave). Las entradas de 'ninguno' se ignoran."""
    por_nombre: dict[str, dict] = {}
    por_clave: dict[str, dict] = {}
    for _, fila in io.read_table("descuentos", strict=False).iterrows():
        nombre = "" if pd.isna(fila["nombre"]) else str(fila["nombre"]).strip()
        clave = normalizar_nombre(nombre)
        if clave is None or clave in SIN_DESCUENTO:
            continue
        entrada = {
            "descuento_id": str(fila["descuento_id"]),
            "nombre": nombre,
            "porcentaje": porcentaje_de_catalogo(fila["valor_porcentual"]),
        }
        por_nombre[clave] = entrada
        por_clave[entrada["descuento_id"]] = entrada
    return por_nombre, por_clave


# --- El padrón de alumnos ----------------------------------------------


def _alumnos_vigentes() -> tuple[dict[str, str], dict[str, list[str]], set[str]]:
    """(persona_id -> nombre, nombre normalizado -> id(s), todos los alumnos).

    El tercero incluye a los dados de baja: hace falta para distinguir "este
    alumno ya no esta inscrito" de "esta clave no es de ningun alumno", que se
    tratan distinto.
    """
    alumnos = io.read_table("alumnos", strict=False)
    personas = io.read_table("personas", strict=False)
    if alumnos.empty:
        return {}, {}, set()

    todos = set(alumnos["persona_id"].astype(str))
    vigentes = set(
        alumnos[alumnos["estatus"].isin(ESTATUS_VIGENTES)]["persona_id"].astype(str)
    )
    nombres: dict[str, str] = {}
    por_nombre: dict[str, list[str]] = {}
    for _, persona in personas.iterrows():
        persona_id = str(persona["persona_id"])
        if persona_id not in vigentes:
            continue
        completo = nombre_completo(
            persona["nombre"], persona["apellido_paterno"], persona["apellido_materno"]
        )
        nombres[persona_id] = completo
        clave = normalizar_nombre(completo)
        if clave:
            por_nombre.setdefault(clave, []).append(persona_id)
    return nombres, por_nombre, todos


# --- Mantenimiento del archivo -----------------------------------------


def _texto(valor) -> str:
    return "" if valor is None or pd.isna(valor) else str(valor).strip()


def refrescar(*, escribir: bool = True) -> Reporte:
    """Pone al día `alumnos_descuentos` y reporta lo que no cuadra.

    Nunca inventa un descuento ni corrige un nombre mal escrito: eso sería
    decidir por la administración sobre dinero. Rellena lo derivable (nombre del
    alumno, clave del catálogo, porcentaje sugerido, identificadores) y para lo
    demás avisa.
    """
    reporte = Reporte()
    por_nombre, por_clave = _catalogo()
    nombres, alumnos_por_nombre, todos_los_alumnos = _alumnos_vigentes()
    reporte.alumnos = len(nombres)

    if not nombres:
        reporte.problemas.append(
            "No hay alumnos inscritos. Correr `lisart procesar inscripciones` primero."
        )
        return reporte
    if not por_nombre:
        reporte.problemas.append(
            "El catálogo `descuentos` está vacío. Correr `lisart ingest catalogos` primero."
        )
        return reporte

    actual = io.read_table(TABLA, strict=False)
    momento = ahora()
    filas: list[dict] = []
    vistos: dict[tuple[str, str], int] = {}  # (alumno, descuento) -> renglón del CSV

    for posicion, original in actual.iterrows():
        linea = io._fila_csv(posicion)
        fila = {c: original.get(c) for c in ALUMNOS_DESCUENTOS.column_names}
        persona_id = _texto(fila["persona_id"])
        escrito_a_mano = _texto(fila["alumno"])

        # Quien agrega un renglón a mano puede poner solo el nombre. Se resuelve
        # si no hay ambigüedad; si dos alumnos se llaman igual, se pregunta.
        if not persona_id and escrito_a_mano:
            candidatos = alumnos_por_nombre.get(normalizar_nombre(escrito_a_mano) or "", [])
            if len(candidatos) == 1:
                persona_id = candidatos[0]
            elif not candidatos:
                reporte.problemas.append(
                    f"fila {linea}: no hay ningún alumno inscrito que se llame "
                    f"'{escrito_a_mano}'. Revisar el nombre o poner el persona_id."
                )
                continue
            else:
                reporte.problemas.append(
                    f"fila {linea}: '{escrito_a_mano}' corresponde a {len(candidatos)} "
                    f"alumnos ({', '.join(candidatos)}). Hay que poner el persona_id."
                )
                continue

        if not persona_id:
            reporte.problemas.append(f"fila {linea}: sin alumno. Falta persona_id o el nombre.")
            continue

        if persona_id not in todos_los_alumnos:
            reporte.problemas.append(
                f"fila {linea}: {persona_id} no es ningún alumno. Un descuento sobre "
                "alguien que no está en la escuela no se puede cobrar a nadie."
            )
            continue

        if persona_id not in nombres:
            # Ya no está inscrito. Si el renglón no dice nada, se va; si dice
            # algo, se conserva: perder por qué alguien tenía beca es peor que
            # cargar con un renglón de más.
            if _texto(fila["descuento"]) or _texto(fila["notas"]):
                reporte.conservados.append(persona_id)
            else:
                reporte.retirados.append(persona_id)
                continue
        else:
            fila["alumno"] = nombres[persona_id]

        fila["persona_id"] = persona_id
        nombre_descuento = _texto(fila["descuento"])
        clave = normalizar_nombre(nombre_descuento)

        if clave is None or clave in SIN_DESCUENTO:
            fila["descuento"] = pd.NA
            fila["descuento_id"] = pd.NA
            fila["porcentaje"] = pd.NA
            clave = ""
        else:
            entrada = por_nombre.get(clave)
            if entrada is None:
                conocidos = ", ".join(sorted(e["nombre"] for e in por_nombre.values()))
                reporte.problemas.append(
                    f"fila {linea} ({fila['alumno']}): '{nombre_descuento}' no está en el "
                    f"catálogo de descuentos. Los que hay son: {conocidos}."
                )
                continue
            fila["descuento"] = entrada["nombre"]  # se escribe como lo dice el catálogo
            fila["descuento_id"] = entrada["descuento_id"]
            fila["porcentaje"] = _resolver_porcentaje(fila, entrada, linea, reporte)

        anterior = vistos.get((persona_id, clave))
        if anterior is not None:
            que = f"el descuento '{fila['descuento']}'" if clave else "un renglón vacío"
            reporte.problemas.append(
                f"fila {linea}: {fila['alumno']} ya tiene {que} en la fila {anterior}. "
                "Un descuento repetido se cobraría dos veces."
            )
            continue
        vistos[(persona_id, clave)] = linea

        if pd.isna(fila["creado_en"]):
            fila["creado_en"] = momento
        fila["actualizado_en"] = momento
        if not _texto(fila["fuente"]):
            fila["fuente"] = "manual"
        filas.append(fila)

    # Alumnos que todavía no aparecen en el archivo: entran con la celda vacía,
    # que es lo que permite darles un descuento sin tener que crear el renglón.
    ya_estan = {clave[0] for clave in vistos}
    for persona_id, nombre in nombres.items():
        if persona_id in ya_estan:
            continue
        reporte.agregados.append(persona_id)
        filas.append({
            "alumno_descuento_id": pd.NA,
            "persona_id": persona_id,
            "alumno": nombre,
            "descuento": pd.NA,
            "descuento_id": pd.NA,
            "porcentaje": pd.NA,
            "notas": pd.NA,
            "creado_en": momento,
            "actualizado_en": momento,
            "fuente": "manual",
        })

    filas = _quitar_vacias_de_quien_ya_tiene(filas, reporte)
    _avisar_sumas_altas(filas, reporte)

    tabla = pd.DataFrame(filas, columns=ALUMNOS_DESCUENTOS.column_names)
    tabla["porcentaje"] = pd.to_numeric(tabla["porcentaje"], errors="coerce").astype("Float64")
    tabla = _asignar_identificadores(tabla)

    reporte.filas = len(tabla)
    if len(tabla):
        reporte.con_descuento = int(
            tabla.loc[tabla["descuento"].notna(), "persona_id"].nunique()
        )

    if reporte.problemas:
        reporte.avisos.append(
            "No se escribió nada: primero hay que corregir lo de arriba en el archivo."
        )
        return reporte

    if escribir:
        try:
            backup.guardar_con_respaldo(TABLA, tabla, motivo="descuentos")
        except io.DataError as error:
            # No debería pasar: lo de arriba ya revisó lo que este archivo puede
            # traer mal. Si pasa, se reporta como cualquier otro problema en vez
            # de dejar caer un traceback encima de quien solo editó un CSV.
            reporte.problemas.append(str(error))
        else:
            reporte.escrito = True
    return reporte


def _resolver_porcentaje(fila: dict, entrada: dict, linea: int, reporte: Reporte) -> float | None:
    """El porcentaje de una fila: el que trae, o el del catálogo si viene vacío."""
    del_catalogo = entrada["porcentaje"]
    valor = fila["porcentaje"]

    if valor is None or pd.isna(valor):
        if del_catalogo is None:
            reporte.avisos.append(
                f"fila {linea} ({fila['alumno']}): '{entrada['nombre']}' no trae porcentaje "
                "en el catálogo. Hay que escribirlo a mano en la columna `porcentaje`."
            )
        return del_catalogo

    numero = float(valor)
    if not 0 <= numero <= PORCENTAJE_MAXIMO:
        reporte.problemas.append(
            f"fila {linea} ({fila['alumno']}): porcentaje {numero:g}. Va en puntos, "
            f"de 0 a {PORCENTAJE_MAXIMO:g} (5 es 5%, 100 es beca completa)."
        )
    elif del_catalogo is not None and abs(numero - del_catalogo) > 1e-9:
        reporte.avisos.append(
            f"fila {linea} ({fila['alumno']}): {numero:g}% en vez del {del_catalogo:g}% "
            f"que dice el catálogo para '{entrada['nombre']}'. Se respeta lo escrito; "
            "conviene dejar dicho en `notas` por qué."
        )
    return numero


def _quitar_vacias_de_quien_ya_tiene(filas: list[dict], reporte: Reporte) -> list[dict]:
    """Si un alumno tiene un descuento, su renglón vacío sobra y confunde."""
    con_descuento = {_texto(f["persona_id"]) for f in filas if _texto(f["descuento"])}
    limpias = [
        f for f in filas
        if _texto(f["descuento"]) or _texto(f["persona_id"]) not in con_descuento
    ]
    if len(limpias) != len(filas):
        reporte.avisos.append(
            f"{len(filas) - len(limpias)} renglón(es) vacíos de alumnos que sí tienen "
            "descuento se quitaron, para que cada alumno aparezca una sola vez sin él."
        )
    return limpias


def _avisar_sumas_altas(filas: list[dict], reporte: Reporte) -> None:
    """Dos descuentos que juntos pasan del 100% dejarían a la escuela pagando."""
    suma: dict[str, float] = {}
    nombre: dict[str, str] = {}
    for f in filas:
        valor = f["porcentaje"]
        if valor is None or pd.isna(valor):
            continue
        persona_id = _texto(f["persona_id"])
        suma[persona_id] = suma.get(persona_id, 0.0) + float(valor)
        nombre[persona_id] = _texto(f["alumno"])
    for persona_id, total in suma.items():
        if total > PORCENTAJE_MAXIMO:
            reporte.avisos.append(
                f"{nombre[persona_id]} suma {total:g}% entre sus descuentos. Se le aplica "
                f"{PORCENTAJE_MAXIMO:g}% (no paga), pero revisar si de verdad lleva los dos."
            )


def _asignar_identificadores(tabla: pd.DataFrame) -> pd.DataFrame:
    """Le pone ALD-#### a los renglones que llegaron sin él (los agregados a mano)."""
    if tabla.empty:
        return tabla
    faltan = tabla["alumno_descuento_id"].isna()
    if not faltan.any():
        return tabla

    # `next_ids` arranca despues del mayor que hay en el archivo, asi que los
    # nuevos no chocan con los que ya estaban.
    tabla.loc[faltan, "alumno_descuento_id"] = next_ids(TABLA, int(faltan.sum()))
    return tabla


# --- Lo que consume la proyección --------------------------------------


def total_de(porcentajes) -> float:
    """Cuánto se le descuenta en total a un alumno. Se suman, con tope en 100%."""
    return min(float(sum(porcentajes)), PORCENTAJE_MAXIMO)


def por_alumno() -> dict[str, dict]:
    """persona_id -> {porcentaje, descuentos} con lo que hoy dice el archivo.

    Lee la tabla tal como está, sin refrescarla: la proyección informa sobre el
    dato guardado, no lo modifica de pasada. Los renglones sin descuento no
    aparecen aquí.
    """
    tabla = io.read_table(TABLA, strict=False)
    if tabla.empty:
        return {}

    agrupado: dict[str, dict] = {}
    for _, fila in tabla.iterrows():
        nombre = _texto(fila["descuento"])
        if not nombre:
            continue
        persona_id = _texto(fila["persona_id"])
        valor = fila["porcentaje"]
        entrada = agrupado.setdefault(persona_id, {"porcentajes": [], "descuentos": []})
        entrada["descuentos"].append(nombre)
        if valor is not None and not pd.isna(valor):
            entrada["porcentajes"].append(float(valor))

    return {
        persona_id: {
            "porcentaje": total_de(entrada["porcentajes"]),
            "descuentos": sorted(entrada["descuentos"]),
        }
        for persona_id, entrada in agrupado.items()
    }
