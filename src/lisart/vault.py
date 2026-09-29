"""Genera un vault de Obsidian para ver el sistema como grafo.

Por que existe: el modelo de datos ya esta descrito en `tables.py`, pero leer
diez tablas y sus llaves foraneas en codigo no da la foto completa. Un grafo si:
se ve de un vistazo que `personas` es el centro de todo, y se ve que los
proyectos de pagos y mensajeria todavia cuelgan del aire.

Como esta partido:

* `Tablas/` se **genera** desde el registro. Se borra y se reescribe en cada
  corrida. No editar a mano: se pierde.
* `Fuentes/`, `Documentos/` y `Proyectos/` se siembran una sola vez y despues
  son tuyos. `lisart vault` no los pisa salvo que se le pase `--forzar`.

Un detalle util del grafo de Obsidian: los enlaces a notas que no existen
aparecen como circulos huecos. Como los proyectos ya enlazan a `[[pagos]]` o
`[[envios]]`, que todavia no se construyen, esos huecos son literalmente el
mapa de lo que falta.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from lisart.config import PROJECT_ROOT
from lisart.schema import Table
from lisart.tables import REGISTRY

VAULT_PATH = PROJECT_ROOT / "vault"

AVISO = (
    "> [!warning] Nota generada\n"
    "> La escribe `lisart vault` desde `src/lisart/tables.py`. "
    "Si la editas a mano, se pierde en la siguiente corrida.\n"
)

QUIEN_EDITA = {"managed": "codigo", "hand_edited": "a mano"}


# --- Notas de tablas (generadas) ---------------------------------------


def _refs_entrantes(tabla: Table) -> list[tuple[str, str, str]]:
    """Quien apunta a esta tabla: (tabla origen, columna origen, columna destino)."""
    entrantes = []
    for otra in REGISTRY:
        for fk in otra.foreign_keys:
            if fk.ref_table == tabla.name:
                entrantes.append((otra.name, fk.column, fk.ref_column))
    return sorted(entrantes)


def _nota_tabla(tabla: Table) -> str:
    lineas = [
        "---",
        "tipo: tabla",
        f"capa: {tabla.layer}",
        f"edicion: {QUIEN_EDITA[tabla.ownership]}",
        f"tags: [tabla, {tabla.layer}]",
        "---",
        "",
        AVISO,
        f"# {tabla.name}",
        "",
        " ".join(tabla.description.split()),
        "",
        f"**Archivo:** `data/{tabla.layer}/{tabla.name}.csv`",
        f"**Llave primaria:** {', '.join(f'`{c}`' for c in tabla.primary_key)}",
        f"**La edita:** {QUIEN_EDITA[tabla.ownership]}",
        "",
        "## Columnas",
        "",
        "| Columna | Tipo | Oblig. | Reglas |",
        "| --- | --- | --- | --- |",
    ]
    for col in tabla.columns:
        reglas = []
        if col.name in tabla.primary_key:
            reglas.append("PK")
        if col.unique:
            reglas.append("unica")
        if col.choices:
            reglas.append("uno de: " + ", ".join(f"`{c}`" for c in col.choices))
        for fk in tabla.foreign_keys:
            if fk.column == col.name:
                reglas.append(f"apunta a [[{fk.ref_table}]]")
        lineas.append(
            f"| `{col.name}` | {col.dtype} | {'si' if col.required else 'no'} | "
            f"{'; '.join(reglas)} |"
        )

    if tabla.foreign_keys:
        lineas += ["", "## Apunta a", ""]
        for fk in tabla.foreign_keys:
            lineas.append(f"- [[{fk.ref_table}]] — por `{fk.column}` → `{fk.ref_column}`")

    entrantes = _refs_entrantes(tabla)
    if entrantes:
        lineas += ["", "## Le apuntan", ""]
        for origen, col_origen, col_destino in entrantes:
            lineas.append(f"- [[{origen}]] — por `{col_origen}` → `{col_destino}`")

    lineas += ["", "---", "", "Volver a [[Lisart]] · [[Modelo de datos]]", ""]
    return "\n".join(lineas)


def _diagrama_er() -> str:
    """Diagrama entidad-relacion en mermaid. Obsidian lo dibuja solo."""
    lineas = ["```mermaid", "erDiagram"]
    for tabla in sorted(REGISTRY, key=lambda t: t.name):
        for fk in tabla.foreign_keys:
            etiqueta = fk.column.replace("_", " ")
            lineas.append(f'    {fk.ref_table} ||--o{{ {tabla.name} : "{etiqueta}"')
    # Los catalogos no tienen llaves foraneas todavia, asi que sin esto no
    # aparecerian en el diagrama. Se dibujan con su llave primaria.
    sueltas = [
        t for t in sorted(REGISTRY, key=lambda t: t.name)
        if not t.foreign_keys and not _refs_entrantes(t)
    ]
    for tabla in sueltas:
        lineas.append(f"    {tabla.name} {{")
        for nombre_col in tabla.primary_key:
            lineas.append(f"        {tabla.column(nombre_col).dtype} {nombre_col} PK")
        lineas.append("    }")
    lineas.append("```")
    return "\n".join(lineas)


def _nota_indice() -> str:
    por_capa: dict[str, list[Table]] = {}
    for tabla in REGISTRY.in_dependency_order():
        por_capa.setdefault(QUIEN_EDITA[tabla.ownership], []).append(tabla)

    lineas = [
        "---",
        "tipo: indice",
        "tags: [indice]",
        "---",
        "",
        AVISO,
        "# Lisart",
        "",
        "Sistema administrativo de la escuela de musica Lisart. Esta nota es la",
        "puerta de entrada; abre la **vista de grafo** de Obsidian para ver todo junto.",
        "",
        "> [!tip] Como leer el grafo",
        "> Los circulos **huecos** son notas que no existen todavia. Como los",
        "> proyectos ya enlazan a tablas que faltan (`[[pagos]]`, `[[envios]]`,",
        "> `[[clases]]`), esos huecos son el mapa de lo que falta construir.",
        "",
        "## El modelo de datos",
        "",
        _diagrama_er(),
        "",
        "## Tablas",
        "",
    ]
    for quien, tablas in por_capa.items():
        encabezado = "**Las escribe el codigo:**" if quien == "codigo" else "**Se editan a mano:**"
        lineas.append(encabezado)
        lineas.append("")
        for tabla in tablas:
            lineas.append(f"- [[{tabla.name}]] — {' '.join(tabla.description.split())[:90]}...")
        lineas.append("")

    lineas += [
        "## Los cuatro proyectos",
        "",
        "- [[Proyecto 1 - Mensajes automaticos]]",
        "- [[Proyecto 2 - Segmentacion de alumnos]]",
        "- [[Proyecto 3 - Centralizacion de pagos]]",
        "- [[Proyecto 4 - Calendarizacion]]",
        "",
        "## De donde salen los datos",
        "",
        "- [[Jotform]] · [[Kydemy]] · [[WhatsApp]]",
        "",
        "## Documentos que se manejan",
        "",
        "- [[Formulario de inscripcion]]",
        "- [[Politicas y reglamento]]",
        "- [[Proyeccion de pago]]",
        "- [[Comprobante de pago]]",
        "- [[Documento de reembolso]]",
        "",
        "## Como funciona por dentro",
        "",
        "- [[Modelo de datos]] — las capas y las reglas",
        "- [[Identidad]] — por que una persona es una sola fila",
        "",
    ]
    return "\n".join(lineas)


def _nota_modelo_de_datos() -> str:
    return f"""---
tipo: concepto
tags: [concepto]
---

{AVISO}
# Modelo de datos

La base de datos son **archivos CSV**. Es una decision consciente: a escala de
cientos de personas, un CSV disciplinado se abre en Excel, se respalda copiando
una carpeta y no cobra renta. Lo que un CSV no trae de fabrica —tipos, llaves,
integridad— lo pone el paquete `lisart`.

## Las cuatro capas

```mermaid
flowchart LR
    raw["raw<br/>como llego<br/>inmutable"] --> interim
    interim["interim<br/>pasos intermedios<br/>desechable"] --> master
    master["master<br/>la verdad<br/>SE RESPALDA"]
    master --> exports["exports<br/>reportes<br/>desechable"]
```

El flujo **nunca** va al reves. Si se borra `interim/` y `exports/`, se
reconstruyen. Si se borra `master/`, se perdio informacion.

Aparte de las cuatro capas esta `data/backups/`, que no es parte del flujo sino
una red de seguridad: cada vez que se guarda desde la pantalla ([[Pantalla]]),
el estado anterior queda ahi.

Entran por [[Jotform]], [[Kydemy]] y [[WhatsApp]]; salen como
[[Proyeccion de pago]] y [[Comprobante de pago]].

## Quien escribe cada tabla

| Tipo | Quien | Codificacion |
| --- | --- | --- |
| `managed` | Solo el codigo | UTF-8 |
| `hand_edited` | Una persona, en Excel | UTF-8 con BOM |

El BOM es lo que evita que Excel en español muestre `MarÃ­a`.

## La regla innegociable

Nunca `pd.read_csv` ni `df.to_csv` sobre `data/`. Todo pasa por `read_table`,
`write_table` y `upsert`, que es donde viven los tipos, la validacion y la
escritura atomica.

Detalle completo en `docs/convenciones_datos.md`. Volver a [[Lisart]].
"""


def _nota_identidad() -> str:
    return f"""---
tipo: concepto
tags: [concepto]
---

{AVISO}
# Identidad

**Una persona es una persona.** Un profesor que ademas es tutor de su hija es
UNA fila en [[personas]] con dos roles en [[personas_roles]], no dos personas.

Duplicar humanos es la causa raiz de casi todo lo que se rompe despues: pagos
que no cuadran, mensajes enviados dos veces, un alumno inscrito y prospecto al
mismo tiempo.

## Como se conectan las piezas

```mermaid
flowchart TD
    P[personas<br/>una fila por humano]
    P --> R[personas_roles<br/>alumno, tutor, profesor...]
    P --> A[alumnos<br/>extiende a personas<br/>misma persona_id]
    P --> IE[identificadores_externos<br/>como le dice cada sistema]
    A --> REL[relaciones<br/>tutor, recoge, paga_por]
    P --> REL
    IE -.-> K[Kydemy]
    IE -.-> J[Jotform]
    IE -.-> W[WhatsApp]
```

## Los dos casos que obligaron a este diseño

**"Sofi paga por mi".** Quien paga no siempre es el alumno. Por eso
[[relaciones]] tiene el tipo `paga_por`: sin eso, cualquier cruce de pagos
ingenuo falla.

**El mismo humano con tres nombres.** [[Jotform]] dice "Ma. José Hernández",
[[Kydemy]] dice "MARIA JOSE HERNANDEZ" y [[WhatsApp]] solo trae un telefono.
Por eso existe [[identificadores_externos]]: el cruce se hace por identificador,
no por nombre. Cruzar por nombre es el ultimo recurso, no el primero.

Para eso sirven `ids.normalizar_nombre` (quita acentos, respeta la ñ) y
`ids.normalizar_telefono` (deja E.164, que es lo que entiende WhatsApp).

Volver a [[Lisart]].
"""


# --- Notas sembradas (se escriben una vez y despues son tuyas) ----------

SEMILLAS: dict[str, str] = {
    "Pantalla.md": """---
tipo: concepto
tags: [concepto]
---

# Pantalla

Se abre con `lisart ui`. Una **seccion por tabla** mas la del grafo, y dentro de
cada una un registro a la vez con flechas y buscador.

## Tres cosas que hace por diseno

1. **Los campos no estan escritos en la app.** Salen de `tables.py`: el tipo
   decide el control, un catalogo se vuelve lista desplegable y una llave
   foranea se vuelve un selector de valores que si existen. Al agregar una
   columna al modelo, aparece sola en pantalla.
2. **Nada se sobrescribe sin respaldo.** Guardar valida, copia el estado
   anterior a `data/backups/` y luego escribe. Restaurar esta en la misma
   pantalla, y restaurar tambien deja copia de lo que pisa.
3. **Lo que no se debe editar, no se puede editar:** la llave primaria (romperla
   deja referencias colgando), las marcas de tiempo, y las tablas de capa
   `interim`, que se regeneran desde `raw`.

## El grafo

Ultima seccion. Contesta *que alumnos se parecen*: los que estudian el mismo
instrumento se agrupan alrededor de el, los hermanos alrededor de su tutor.
Cada nodo es una figura musical — negra el alumno, corchea el tutor, redonda el
[[instrumentos|instrumento]] — y al hacer clic se abre su ficha.

No hay nodo de maestro: el formulario de [[Jotform]] no pregunta quien da la
clase. Cuando exista el dato entra como [[relaciones]] de tipo `profesor`
ligadas al alumno.

## Horarios y reposicion

La seccion **Horarios** muestra la semana tipo de cualquier persona, dibujada
como linea de tiempo por dia. Una hora esta en uno de tres estados —disponible,
bloqueado, no disponible— pero **solo se guardan dos**: el tercero es la
ausencia de fila en [[disponibilidad]].

La otra vista busca **reposicion**: cuando un alumno falta, cruza sus [[clases]]
con sus profesores ([[clases_profesores]], que es de muchos a muchos) y con su
propio horario.

## La agenda de profesores

Aplicacion aparte (`lisart ui --profesores`) con otro camino: se entra por la
clase, no por la persona. Las horas que los alumnos de esa clase marcaron se
pintan como ocupadas para el profesor —una aproximacion declarada, no un dato— y
no se guardan.

## Datos de prueba

`lisart demo` siembra profesores y clases marcados con `fuente = "demo"`, y
`lisart demo --limpiar` los borra sin tocar nada real. Sin ellos no habia forma
de ejercitar la agenda ni la reposicion.

## Identidad visual

Negro exacto del logo en la banda, mayusculas espaciadas como en "ACADEMIA DE
MUSICA", y el vino de la paleta como el lapiz rojo con que un musico anota su
partitura: marca el registro actual y la accion de guardar. El navegador de
registros **es un pentagrama**, y la altura de cada nota sale del Himno a la
Alegria.

Volver a [[Lisart]].
""",

    "Fuentes/Jotform.md": """---
tipo: fuente
tags: [fuente]
---

# Jotform

Formularios de inscripcion. Es por donde **entra** un alumno nuevo al sistema.

- Cae en: [[respuestas_inscripcion]] (capa interim)
- Despues alimentara: [[personas]], [[alumnos]], [[relaciones]]
- Se identifica en [[identificadores_externos]] con `sistema = jotform`
- Documento asociado: [[Formulario de inscripcion]]
- Codigo: `src/lisart/fuentes/jotform.py`

## Como se baja

```bash
lisart ingest jotform
```

Baja todos los envios, guarda la copia cruda en `data/raw/jotform/` y agrega a
la tabla **solo lo que no estaba**. Si no hay nada nuevo, no toca el archivo.
Se corre una vez por semana.

Las llaves (`JOTFORM_API_KEY`, `JOTFORM_FORM_ID`) van en `.env`, nunca en el
codigo.

> [!warning] El mapeo va por numero de orden
> Los campos se identifican por su posicion en el formulario. Si alguien
> reordena o inserta un campo en Jotform, los datos empiezan a caer en la
> columna equivocada **sin que nada truene**. `lisart ingest jotform` corre
> `revisar_mapeo()` en cada corrida y avisa. **Hacerle caso a esos avisos.**

> [!danger] Pendiente de seguridad
> La API key sigue siendo la que estuvo escrita en duro en el notebook
> `projects/data_mechanism/respuestas_inscripcion_forms.ipynb`. Ya vive en
> `.env`, pero **hay que rotarla en Jotform** antes del primer commit de git.

Trae datos de menores: domicilios, telefonos, firmas e identificaciones.
""",
    "Fuentes/Catalogo de la escuela.md": """---
tipo: fuente
tags: [fuente]
---

# Catalogo de la escuela

`data/catalogos_lisart.xlsx`, mantenido a mano por la escuela. Se trata **como
fuente cruda**, igual que [[Jotform]]: `lisart ingest catalogos` guarda copia con
fecha en `data/raw/catalogos/` y escribe las tablas.

| Hoja | A donde va |
| --- | --- |
| `programas_aprendizaje` | [[programas]] — con la **cuota mensual** |
| `oferta_clases` | enriquece [[instrumentos]] con su clave y descripcion |
| `descuentos` | [[descuentos]] |

## Cosas que hay que aclarar con la escuela

- **"Individual (1xsemana)" no tiene precio** y lo llevan 17 alumnos, el 15%. Es
  lo unico que separa a la [[Proyeccion de pago]] de cubrir al 100%.
- **`valor_porcentual` mezcla unidades**: 0.05 para un 5% y 100.00 para una beca
  completa, en la misma columna. Se guarda tal cual y la unidad se resuelve al
  pasar a [[alumnos_descuentos]], que es donde una persona la confirma antes de
  que toque un cobro.
- **Jarana** la eligieron alumnos y no esta en `oferta_clases`.
- **Bajo Electrico** y **La Musica es un Juego** estan en el catalogo y nadie los
  eligio.
""",
    "Fuentes/Kydemy.md": """---
tipo: fuente
tags: [fuente]
---

# Kydemy

Plataforma donde hoy vive la informacion academica y donde se generan los
comprobantes de pago.

- Se identifica en [[identificadores_externos]] con `sistema = kydemy`
- Documento asociado: [[Comprobante de pago]]
- Sirve para **verificar** lo que se extrajo de [[WhatsApp]]

Objetivo declarado: automatizar la generacion de comprobantes aqui.
""",
    "Fuentes/WhatsApp.md": """---
tipo: fuente
tags: [fuente]
---

# WhatsApp

Dos usos distintos que conviene no confundir.

## Como fuente de datos

La conversacion **"Pagos Lisart"** dice quien ya pago y con que comprobante.
Es el punto de partida para armar la [[Proyeccion de pago]].

- Se identifica en [[identificadores_externos]] con `sistema = whatsapp`
- La llave natural es el telefono en E.164 (`+525512345678`)

## Como canal de salida

Hoy es **monodireccional**: se envia, no se recibe. El mensaje ya se puede
hiperpersonalizar y calendarizar. Para leer respuestas haria falta pedir la
API key de WhatsApp.

Alimenta al [[Proyecto 1 - Mensajes automaticos]].
""",
    "Documentos/Formulario de inscripcion.md": """---
tipo: documento
tags: [documento]
---

# Formulario de inscripcion

Se llena en [[Jotform]]. Es el documento que da de alta a un alumno.

Que captura: datos del alumno, del tutor, contacto de emergencia, quien puede
recoger, instrumentos, horario preferido, y las firmas de
[[Politicas y reglamento]].

De aqui salen filas en [[personas]], [[alumnos]] y [[relaciones]].
""",
    "Documentos/Politicas y reglamento.md": """---
tipo: documento
tags: [documento]
---

# Politicas y reglamento

Documentos que la familia acepta y firma al inscribirse, dentro del
[[Formulario de inscripcion]]:

- Politicas de servicio (con firma y manifiesto de conformidad)
- Reglamento
- Aviso de privacidad
- Autorizacion de uso de imagen (distinta para mayores y menores)

> [!note] Todavia no estan en el modelo
> No hay tabla que guarde estas aceptaciones. Cuando se necesite comprobar
> quien firmo que y cuando, hara falta una tabla `consentimientos`.
""",
    "Documentos/Proyeccion de pago.md": """---
tipo: documento
tags: [documento]
---

# Proyeccion de pago

Cuanto deberia entrar al mes y de quien. **Ya se calcula solo**:

```bash
lisart proyeccion
```

Sale de cruzar [[alumnos]] con [[programas]], que trae la cuota mensual. El
reporte se escribe en `data/exports/` como tres CSV: detalle por alumno, reparto
por programa, y **los que no se pudieron costear**.

## De donde salen los precios

Del Excel `data/catalogos_lisart.xlsx` que mantiene la escuela, ingestado con
`lisart ingest catalogos`. Ver [[Catalogo de la escuela]].

## Lo que el numero todavia no incluye

- **Un programa sin precio deja fuera a su alumno**, pero no lo esconde: sale
  listado aparte y el total dice sobre cuantos se calculo.
- **Los descuentos salen de [[alumnos_descuentos]]**, el unico archivo del
  sistema que se llena a mano (`lisart descuentos`). Si esta vacio, la
  proyeccion es BRUTA y lo dice.
- El caso "Sofi paga por mi" no afecta al monto —se debe lo mismo— pero si a
  quien se le cobra. Ver [[relaciones]] y su tipo `paga_por`.

## Lo que falta para la conciliacion

Comparar esto contra lo que de verdad entro necesita la tabla `[[pagos]]`, que
no existe, y una fuente de pagos reales: [[WhatsApp]] o [[Kydemy]]. Es el
[[Proyecto 3 - Centralizacion de pagos]].
""",

    "Documentos/Comprobante de pago.md": """---
tipo: documento
tags: [documento]
---

# Comprobante de pago

Se genera en [[Kydemy]]. Automatizar su generacion es parte del objetivo actual.

Para emitirlo hace falta saber **quien pago** y **por quien** — que no siempre
son la misma persona. Ver [[relaciones]] y su tipo `paga_por`.

Depende de la tabla `[[pagos]]`, que todavia no existe.
""",
    "Documentos/Documento de reembolso.md": """---
tipo: documento
tags: [documento]
---

# Documento de reembolso

Documento de ingresos y egresos del procedimiento de reembolso. Hoy se llena a
mano.

**Ideal a futuro:** que se llene solo, a partir del reporte automatico de
ingresos y egresos.

Depende de que exista el registro de pagos del
[[Proyecto 3 - Centralizacion de pagos]].
""",
    "Proyectos/Proyecto 1 - Mensajes automaticos.md": """---
tipo: proyecto
estado: no iniciado
tags: [proyecto]
---

# Proyecto 1 — Mensajes automaticos

Recordatorios de pago e inscripcion a alumnos y profesores. Maximo ~15 mensajes
distintos; algunos son condicionales. Hoy se copia y pega un comando para enviar.

## Que necesita

- Existentes: [[personas]], [[alumnos]], [[personas_roles]]
- Por construir: `[[plantillas_mensajes]]`, `[[calendario_mensajes]]`, `[[envios]]`
- Canal: [[WhatsApp]] (hoy solo de salida)

## Estado

El mensaje ya se puede hiperpersonalizar (nombre, monto que debe) y calendarizar.
Ya hay un chatbot funcionando, pero **le faltan politicas** para que no conteste
cualquier cosa.

Pendiente: revisar Facebook para comunicacion de dos vias.

`envios` debe ser un registro append-only: sin el, no hay forma de saber si a
alguien ya se le mando el recordatorio y se le manda dos veces.
""",
    "Proyectos/Proyecto 2 - Segmentacion de alumnos.md": """---
tipo: proyecto
estado: no iniciado
tags: [proyecto]
---

# Proyecto 2 — Segmentacion de alumnos

Centralizar los requisitos de los alumnos via formularios y codigo QR, y
clasificar cada peticion o problematica en su propia "canasta" (una bandeja de
entrada por tipo).

## Que necesita

- Existentes: [[personas]], [[alumnos]], [[Jotform]]
- Por construir: `[[solicitudes]]`, `[[tipos_de_solicitud]]`

## Lo que falta decidir

~95% de la gente es digital. **Falta el plan para el 5% que no lo es**: la idea
era una tablet en recepcion con el formulario abierto. Habria que definir el
hardware minimo.
""",
    "Proyectos/Proyecto 3 - Centralizacion de pagos.md": """---
tipo: proyecto
estado: es el candidato a arrancar
tags: [proyecto]
---

# Proyecto 3 — Centralizacion de pagos

Que todo pago quede registrado y referenciado solo, por cualquier medio de pago.

> [!important] La regla dura
> **No se acepta pago de quien no este en el sistema.** Eso obliga a que dar de
> alta a una persona sea lo primero, no un tramite posterior.

## Que necesita

- Existentes: [[personas]], [[alumnos]], [[relaciones]] (el `paga_por`),
  [[conceptos]], [[identificadores_externos]]
- Por construir: `[[inscripciones]]`, `[[pagos]]`, `[[proyeccion_pagos]]`

`pagos` tiene que ser un **ledger append-only**: un pago nunca se edita ni se
borra, se corrige con otro movimiento. Es la unica forma de que el historial
cuadre con el banco.

## Salidas esperadas

Cuantos pagos entraron, cuanta lana entro, cuanto falta.
Documentos: [[Proyeccion de pago]], [[Comprobante de pago]].

## Por que es el candidato natural

Es el objetivo declarado del usuario, y obliga a que el modelo de identidad sea
real —lo que beneficia a los otros tres proyectos.
""",
    "Proyectos/Proyecto 4 - Calendarizacion.md": """---
tipo: proyecto
estado: segunda etapa
tags: [proyecto]
---

# Proyecto 4 — Calendarizacion

Cotejar la agenda de **espacios x musicos x horarios oficiales de alumnos**.

Salida esperada: "tienes disponibles estas aulas con estos musicos, y todo lo
demas esta ocupado".

## Que necesita

- Existentes: [[espacios]] (ya con los 10 reales), [[personas]],
  [[personas_roles]] (rol `profesor`), [[instrumentos]]
- Por construir: `[[clases]]`, `[[disponibilidad]]`

## Lo que ya se resolvio

[[espacios]] distingue con la columna `agendable` un aula de la cocina: de los
10 espacios, **7 se pueden agendar**. Sin esa columna, la calendarizacion
acabaria ofreciendo la cocina para dar clase.

## Lo que falta antes de poder empezar

- Los **nombres reales** de los espacios (hoy dicen "Salon pequeño 1").
- La **capacidad** de cada uno: sin eso no se sabe donde cabe un ensamble y
  donde solo una clase individual.
""",
    "Proyectos/Punto de venta.md": """---
tipo: proyecto
estado: urge, sin empezar
tags: [proyecto]
---

# Punto de venta

Pedido aparte de los cuatro proyectos, marcado como **urgente**. Hoy se llena a
mano dia con dia, con todos los movimientos.

## El desafio real

Hoy solo se relaciona la **venta con el producto**. Falta:

1. Relacionar el platillo/servicio con el **cliente**.
2. Generar automaticamente **a quien le representa un pago** — el musico como
   proveedor.

Es decir: venta → servicio → cliente → proveedor, en una sola cadena.

## Que necesita

- Existentes: [[personas]] (el musico ya cabe con el rol `proveedor`)
- Por construir: `[[ventas]]`, `[[productos]]`, `[[proveedores_pagos]]`

Se conecta con el ideal a futuro: reporte automatico de ingresos y egresos y el
[[Documento de reembolso]].
""",
}


# --- Generacion --------------------------------------------------------


def build_vault(destino: Path | None = None, forzar: bool = False) -> tuple[int, int]:
    """Escribe el vault. Devuelve (notas generadas, notas sembradas nuevas)."""
    raiz = destino or VAULT_PATH
    tablas_dir = raiz / "Tablas"

    # Tablas/ se regenera completo: si se borro una tabla del registro, su nota
    # tiene que desaparecer tambien.
    if tablas_dir.exists():
        shutil.rmtree(tablas_dir)
    tablas_dir.mkdir(parents=True, exist_ok=True)

    generadas = 0
    for tabla in REGISTRY:
        (tablas_dir / f"{tabla.name}.md").write_text(_nota_tabla(tabla), encoding="utf-8")
        generadas += 1

    for nombre, contenido in (
        ("Lisart.md", _nota_indice()),
        ("Modelo de datos.md", _nota_modelo_de_datos()),
        ("Identidad.md", _nota_identidad()),
    ):
        (raiz / nombre).write_text(contenido, encoding="utf-8")
        generadas += 1

    sembradas = 0
    for ruta_rel, contenido in SEMILLAS.items():
        destino_nota = raiz / ruta_rel
        if destino_nota.exists() and not forzar:
            continue
        destino_nota.parent.mkdir(parents=True, exist_ok=True)
        destino_nota.write_text(contenido, encoding="utf-8")
        sembradas += 1

    return generadas, sembradas
