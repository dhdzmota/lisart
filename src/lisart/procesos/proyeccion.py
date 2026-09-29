"""Proyección de pago: cuánto debería entrar al mes y de quién.

Es un desarrollo **independiente**: lee las tablas y escribe un reporte a
`data/exports/`. No toca ninguna pantalla ni escribe en `master`. Si mañana se
integra a la app, será conectándole esta función; hoy vive sola.

    lisart proyeccion

Cómo se calcula
---------------
Cada alumno inscrito paga la cuota mensual de **su programa**. Eso es todo el
cálculo. Lo difícil no es la multiplicación: es amarrar el programa que el
alumno escribió en el formulario con el del catálogo de precios.

El puente entre el formulario y el catálogo
-------------------------------------------
El formulario ofrece etiquetas como "Somos música (Adulto) Esencial"; el
catálogo tiene esa misma cosa partida en tres columnas (nombre, categoría,
arquetipo). No hay ninguna llave común, así que la correspondencia se escribe
aquí, explícita y a la vista, en vez de adivinarse con parecidos de texto: una
proyección de dinero no se construye sobre coincidencias aproximadas.

**Si cambia el texto del formulario, este diccionario es lo que hay que tocar.**

Los descuentos
--------------
Se aplican los que diga `alumnos_descuentos`, que se edita a mano (ver
`procesos/descuentos.py`). Cada alumno lleva su precio de lista y su precio
neto, y el resumen dice cuánto se está descontando en total: un descuento es
dinero que la escuela decidió no cobrar, y merece verse, no desaparecer dentro
de la cifra final.

Si ese archivo está vacío, la proyección es **bruta** y lo declara.

Lo que el catálogo todavía no resuelve
--------------------------------------
**"Individual (1xsemana)" no tiene precio.** Son 17 de 115 alumnos, el 15%. No
se inventa una cifra: esos alumnos salen listados aparte como "sin precio", y el
total dice explícitamente que le faltan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from lisart import io
from lisart.config import layer_dir
from lisart.procesos import descuentos

# Del texto del formulario al programa del catálogo. Escrito a mano a propósito.
DEL_FORMULARIO: dict[str, str] = {
    "Somos música (Adulto) Esencial": "PDA_001",
    "Somos música (Adulto) Integral": "PDA_002",
    "Somos música (Adulto) Especial": "PDA_003",
    "Somos música (Niñ@s) Esencial": "PDA_004",
    "Somos música (Niñ@s) Integral": "PDA_005",
    "Somos música (Niñ@s) Especial": "PDA_006",
    "Somos música (Bebes/Estimulación Musical Temprana) Esencial": "PDA_007",
    "Somos música (Bebes/Estimulación Musical Temprana) Completo": "PDA_008",
    "La música es un Juego": "PDA_010",
}

# "Sesión suelta" cuesta distinto según la edad, así que se resuelve al vuelo.
SESION_SUELTA = {"Bebés": "PDA_013", "Niñ@s": "PDA_012", "Adultos": "PDA_011"}
ETIQUETA_SESION = "Sesión suelta"

EDAD_BEBE, MAYORIA_DE_EDAD = 4, 18


@dataclass
class Proyeccion:
    detalle: pd.DataFrame
    sin_precio: pd.DataFrame
    total_mensual: float = 0.0
    """Lo que se espera cobrar: ya con los descuentos aplicados."""
    total_lista: float = 0.0
    """Lo que costaría sin descuentos. La diferencia es lo que se está dejando de cobrar."""
    alumnos_cobrables: int = 0
    alumnos_totales: int = 0
    alumnos_con_descuento: int = 0
    avisos: list[str] = field(default_factory=list)

    @property
    def cobertura(self) -> float:
        return self.alumnos_cobrables / self.alumnos_totales if self.alumnos_totales else 0.0

    @property
    def total_descuentos(self) -> float:
        return self.total_lista - self.total_mensual

    def resumen(self) -> str:
        lineas = [
            f"Proyección mensual: ${self.total_mensual:,.2f}",
            f"  sobre {self.alumnos_cobrables} de {self.alumnos_totales} alumnos "
            f"({self.cobertura:.0%})",
        ]
        if self.total_descuentos:
            lineas.append(
                f"  lista ${self.total_lista:,.2f} − descuentos "
                f"${self.total_descuentos:,.2f} a {self.alumnos_con_descuento} alumno(s)"
            )
        if len(self.sin_precio):
            perdidos = self.sin_precio["programa"].value_counts()
            lineas.append(f"  {len(self.sin_precio)} alumno(s) SIN precio en el catálogo:")
            lineas += [f"    · {prog} ({n})" for prog, n in perdidos.items()]
        return "\n".join(lineas)


def _categoria_por_edad(fecha_nacimiento, requiere_tutor) -> str:
    """A qué categoría del catálogo pertenece un alumno, para 'Sesión suelta'."""
    if isinstance(fecha_nacimiento, date):
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )
        if edad < EDAD_BEBE:
            return "Bebés"
        return "Niñ@s" if edad < MAYORIA_DE_EDAD else "Adultos"
    # Sin fecha, el único dato que queda es si necesita tutor.
    return "Niñ@s" if requiere_tutor is True else "Adultos"


def calcular(*, solo_activos: bool = True) -> Proyeccion:
    """Arma la proyección. No escribe nada."""
    alumnos = io.read_table("alumnos")
    personas = io.read_table("personas")
    programas = io.read_table("programas")

    avisos: list[str] = []
    if programas.empty:
        avisos.append(
            "No hay programas con precio. Correr `lisart ingest catalogos` primero."
        )
        vacio = pd.DataFrame(
            columns=["persona_id", "alumno", "programa", "precio_lista", "precio"]
        )
        return Proyeccion(vacio, vacio, avisos=avisos)

    if solo_activos and not alumnos.empty:
        antes = len(alumnos)
        alumnos = alumnos[alumnos["estatus"].isin(("inscrito", "activo"))]
        if antes - len(alumnos):
            avisos.append(f"{antes - len(alumnos)} alumno(s) dados de baja quedaron fuera.")

    precio = dict(zip(programas["programa_id"].astype(str), programas["precio"], strict=False))
    nombres = dict(
        zip(
            personas["persona_id"].astype(str),
            (
                personas["nombre"].fillna("").astype(str) + " "
                + personas["apellido_paterno"].fillna("").astype(str) + " "
                + personas["apellido_materno"].fillna("").astype(str)
            ).str.replace(r"\s+", " ", regex=True).str.strip(),
            strict=False,
        )
    )
    nacimiento = dict(
        zip(personas["persona_id"].astype(str), personas["fecha_nacimiento"], strict=False)
    )
    rebajas = descuentos.por_alumno()

    filas, huerfanos = [], []
    for _, alumno in alumnos.iterrows():
        persona_id = str(alumno["persona_id"])
        etiqueta = alumno["programa"]
        etiqueta = None if pd.isna(etiqueta) else str(etiqueta).strip()

        programa_id = DEL_FORMULARIO.get(etiqueta or "")
        if etiqueta == ETIQUETA_SESION:
            categoria = _categoria_por_edad(
                nacimiento.get(persona_id), alumno.get("requiere_tutor")
            )
            programa_id = SESION_SUELTA.get(categoria)

        base = {
            "persona_id": persona_id,
            "alumno": nombres.get(persona_id, persona_id),
            "programa": etiqueta or "(sin programa)",
        }
        if programa_id is None or programa_id not in precio:
            huerfanos.append({**base, "motivo": "el catálogo no tiene precio para ese programa"})
            continue

        lista = float(precio[programa_id])
        rebaja = rebajas.get(persona_id, {"porcentaje": 0.0, "descuentos": []})
        porcentaje = float(rebaja["porcentaje"])
        # Se redondea a centavos aquí y no al imprimir: el número que sale del
        # reporte tiene que ser el mismo que se cobra.
        descontado = round(lista * porcentaje / 100, 2)
        filas.append({
            **base,
            "programa_id": programa_id,
            "precio_lista": lista,
            "descuento": " + ".join(rebaja["descuentos"]),
            "descuento_pct": porcentaje,
            "descuento_pesos": descontado,
            "precio": lista - descontado,
        })

    detalle = pd.DataFrame(filas)
    sin_precio = pd.DataFrame(huerfanos)

    if len(sin_precio):
        faltantes = ", ".join(sorted(sin_precio["programa"].unique()))
        avisos.append(
            f"{len(sin_precio)} alumno(s) no se pudieron costear porque su programa no "
            f"está en el catálogo: {faltantes}. Agregarlo al Excel y volver a ingestar."
        )
    if not rebajas and not io.read_table("descuentos").empty:
        avisos.append(
            "La proyección es BRUTA: no se aplicó ningún descuento porque "
            "`alumnos_descuentos` no dice que alguien tenga uno. Correr "
            "`lisart descuentos` y llenar el archivo."
        )
    sin_alumno = set(rebajas) - set(detalle["persona_id"]) if len(detalle) else set(rebajas)
    if sin_alumno:
        avisos.append(
            f"{len(sin_alumno)} alumno(s) con descuento no entraron a la proyección "
            "(sin precio o dados de baja), así que ese descuento no se refleja."
        )

    return Proyeccion(
        detalle=detalle.sort_values("alumno").reset_index(drop=True) if len(detalle) else detalle,
        sin_precio=sin_precio,
        total_mensual=float(detalle["precio"].sum()) if len(detalle) else 0.0,
        total_lista=float(detalle["precio_lista"].sum()) if len(detalle) else 0.0,
        alumnos_cobrables=len(detalle),
        alumnos_totales=len(alumnos),
        alumnos_con_descuento=int((detalle["descuento_pct"] > 0).sum()) if len(detalle) else 0,
        avisos=avisos,
    )


def por_programa(proyeccion: Proyeccion) -> pd.DataFrame:
    """Cuánto aporta cada programa. Es la vista que contesta 'de dónde sale el dinero'.

    Se agrupa por programa y no por (programa, precio): con descuentos, dos
    alumnos del mismo programa pagan distinto, y partir el renglón por cada
    monto convertiría la vista en otro detalle por alumno.
    """
    columnas = ["programa", "alumnos", "precio", "bruto", "descuento", "subtotal"]
    if proyeccion.detalle.empty:
        return pd.DataFrame(columns=columnas)
    agrupado = (
        proyeccion.detalle.groupby("programa")
        .agg(
            alumnos=("persona_id", "size"),
            precio=("precio_lista", "max"),
            bruto=("precio_lista", "sum"),
            descuento=("descuento_pesos", "sum"),
            subtotal=("precio", "sum"),
        )
        .reset_index()
    )
    return agrupado.sort_values("subtotal", ascending=False).reset_index(drop=True)


def exportar(proyeccion: Proyeccion, nombre: str | None = None) -> list:
    """Escribe el reporte a `data/exports/`. Es capa desechable: se regenera."""
    destino = layer_dir("exports")
    destino.mkdir(parents=True, exist_ok=True)
    sello = nombre or date.today().isoformat()

    escritos = []
    for etiqueta, datos in (
        ("detalle", proyeccion.detalle),
        ("por_programa", por_programa(proyeccion)),
        ("sin_precio", proyeccion.sin_precio),
    ):
        if datos.empty:
            continue
        ruta = destino / f"proyeccion_{sello}_{etiqueta}.csv"
        # Excel en español necesita el BOM para no romper los acentos.
        datos.to_csv(ruta, index=False, encoding="utf-8-sig", lineterminator="\n")
        escritos.append(ruta)
    return escritos
