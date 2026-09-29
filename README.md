# Lisart

Sistema administrativo de la escuela de musica Lisart.

Este repositorio arranca por la base: **la base de datos y la capa que la
cuida**. Encima de eso se iran construyendo los proyectos (mensajeria,
segmentacion, pagos, calendarizacion).

La base de datos son archivos CSV. No es un atajo por flojera: a la escala de
Lisart (cientos de personas, no millones) un CSV bien disciplinado se lee en
Excel, se respalda copiando una carpeta, se versiona en git y no cobra renta
mensual. Lo que un CSV **no** trae de fabrica —tipos, llaves, integridad— es
justo lo que aporta el paquete `lisart` de este repo.

## Instalacion

```bash
uv venv --python 3.12          # crea el entorno
uv pip install -e ".[dev]"     # instala lisart y las herramientas de desarrollo
source .venv/bin/activate      # en Windows: .venv\Scripts\activate

cp .env.example .env           # y llenar las llaves
lisart init                    # crea data/ con las tablas vacias
```

Sin `uv`, `python -m venv .venv` y `pip install -e ".[dev]"` hacen lo mismo.

Paso a paso de como arrancar, correr, editar los datos y cambiar el sistema:
[`docs/guia_de_uso.md`](docs/guia_de_uso.md), o el mismo texto en PDF para
pasarselo a alguien: [`docs/guia_de_uso.pdf`](docs/guia_de_uso.pdf).

Que es todo esto, que se construyo, por que se decidio asi y que tan dificil fue
cada pieza: [`docs/documentacion_general.md`](docs/documentacion_general.md) y su
[PDF](docs/documentacion_general.pdf). Ese es el documento para quien no va a
abrir el codigo.

Y por donde entrarle al codigo —que archivo importa mas, que se rompe si cada
uno falla, y que parte es front-end y que parte back-end—:
[`docs/mapa_del_codigo.md`](docs/mapa_del_codigo.md) y su
[PDF](docs/mapa_del_codigo.pdf). Ese es el documento de entrega para quien tome
el codigo.

Y como pasarle el sistema a otro desarrollador —que documentos ensenarle
primero, quien se queda con que, como se pide un cambio y que quiere decir
"terminado"—: [`docs/guia_de_entrega.md`](docs/guia_de_entrega.md) y su
[PDF](docs/guia_de_entrega.pdf). Se lee entre los dos.

Los cuatro PDF se regeneran con `lisart guia`; **no se editan a mano**.

## Comandos

```bash
lisart init                  # crea carpetas y CSV vacios (no pisa lo que ya existe)
lisart validate              # revisa TODOS los datos contra el esquema
lisart validate espacios     # revisa una sola tabla
lisart describe personas     # que columnas tiene y que significan
lisart docs                  # regenera docs/modelo_de_datos.md desde el codigo
lisart vault                 # regenera el vault de Obsidian (grafo del sistema)
lisart ingest jotform        # baja las inscripciones nuevas de Jotform
lisart ingest catalogos      # lee el Excel de programas, precios y descuentos
lisart proyeccion            # cuanto deberia entrar al mes y de quien
lisart descuentos            # mantiene el archivo de quien tiene que descuento
lisart guia [documento]      # regenera los PDF de docs/ desde su markdown
lisart procesar inscripciones # arma personas, alumnos y relaciones
lisart ui                    # abre la pantalla para ver y editar
lisart ui --profesores       # abre la agenda de profesores (aplicacion aparte)
lisart backup                # respalda la capa master
lisart demo [--limpiar]      # siembra o borra datos de prueba
```

El flujo completo, de la nube a la base:

```
Jotform  --ingest-->  respuestas_inscripcion  --procesar-->  personas
 (API)                    (interim)                          alumnos
                                                             relaciones
                                                             personas_roles
                                                             identificadores_externos
```

### Bajar las inscripciones de Jotform

```bash
lisart ingest jotform
```

Hace tres cosas, en este orden:

1. Baja **todos** los envios del formulario y guarda la respuesta tal cual en
   `data/raw/jotform/submissions_<form>_<fecha>.json`. Esa copia se guarda
   siempre, aunque no haya nada nuevo: es lo unico que no depende de que
   Jotform siga existiendo.
2. Aplana los envios a las 113 columnas de `respuestas_inscripcion`.
3. Agrega a la tabla **solo los envios que no estaban**. Si no hay ninguno,
   no toca el archivo y lo dice.

Se baja todo y no solo lo nuevo a proposito: asi tambien se detecta si alguien
edito o borro un envio en Jotform despues de mandarlo. Esos casos se reportan
pero **no se pisan**, porque la instruccion normal es solo agregar. Para
traerlos: `lisart ingest jotform --actualizar`.

Las llaves van en `.env` (`JOTFORM_API_KEY`, `JOTFORM_FORM_ID`), nunca en el
codigo.

> **El mapeo de campos es fragil, y hay que saberlo.** Jotform identifica cada
> campo por su **posicion** en el formulario. Si alguien reordena o inserta una
> pregunta, los numeros se recorren y los datos empiezan a caer en la columna
> equivocada sin que nada truene. Por eso cada corrida revisa el mapeo y avisa.
> Si sale un `AVISO`, hay que atenderlo antes de confiar en los datos.

### La pantalla

```bash
uv pip install -e ".[ui]"    # una sola vez
lisart ui
```

Abre en el navegador **una seccion por tabla** mas la del grafo, y dentro de
cada una un registro a la vez, con flechas `◀ ▶` para moverte y un buscador.

La seccion elegida viaja en la direccion (`?seccion=alumnos`), no en un
`st.tabs`. Eso permite dos cosas: que un clic dentro del grafo regrese al
grafo, y que **solo se arme la seccion que se esta viendo** — de ahi que abrir
una tabla tarde 1.6 s y no los 30 s que tardaba antes.

El navegador **es un pentagrama**: la nota roja es el registro abierto, los
puntos grises sus vecinos. Toda la app consiste en recorrer registros de uno en
uno, que es lo que hace una melodía.

La dirección visual es *partitura impresa*: tinta negra sobre papel de
partitura, y el vino de la paleta de Lisart como el lápiz rojo con que un
músico anota su hoja —marca el registro actual y la acción de guardar—. El
porqué de cada color y cada tipografía está comentado en `assets/estilo.css`.

Tres cosas que hace por diseño:

- **Los campos no estan escritos en la app.** Salen de `tables.py`: el tipo
  decide el control, un catalogo se vuelve lista desplegable y una llave
  foranea se vuelve un selector de valores que si existen (asi no se puede
  escribir una referencia rota). Al agregar una columna al modelo, aparece
  sola en pantalla.
- **Nada se sobrescribe sin respaldo.** Ver abajo.
- **Lo que no se debe editar, no se puede editar:** la llave primaria (romperla
  deja referencias colgando), las marcas de tiempo, y las tablas de la capa
  `interim`, que se regeneran desde `raw` y perderian cualquier cambio a mano.

Solo escucha en esta computadora (`localhost`). Los datos traen informacion
personal de menores y no tienen por que salir a la red.

### Respaldos

Cada vez que se guarda desde la pantalla, el estado **anterior** se copia a:

```
data/backups/<tabla>/<tabla>_<fecha>.csv
```

Se conservan las ultimas 50 copias por tabla, y desde la misma pantalla se
puede restaurar cualquiera (restaurar tambien deja copia de lo que pisa). Para
un respaldo completo a mano, antes de algo grande:

```bash
lisart backup                # toda la capa master
lisart backup personas       # una sola tabla
```

`data/backups/` esta fuera de las cuatro capas a proposito: no es parte del
flujo de datos, es una red de seguridad.

### El catalogo de precios

La escuela mantiene `data/catalogos_lisart.xlsx` a mano. Se trata **como fuente
cruda**, igual que Jotform:

```bash
lisart ingest catalogos
```

Guarda una copia con fecha en `data/raw/catalogos/` y escribe `programas`,
`descuentos` y las claves de la escuela en `instrumentos`. La escuela sigue
editando su Excel; basta con volver a ingestar.

**No se cambian las llaves de `instrumentos`.** Las claves de la escuela (`PIA`,
`VIO`) entran como una columna mas (`code`), porque `alumnos_instrumentos` tiene
129 filas apuntando a las internas y migrarlas es otra cosa.

### La proyeccion de pago

```bash
lisart proyeccion
```

Dice cuanto deberia entrar al mes, de quien sale, y **quien no se pudo costear**.
Escribe tres CSV a `data/exports/`: el detalle por alumno, el reparto por
programa y los que quedaron fuera.

Es un **desarrollo aparte** (`procesos/proyeccion.py`): lee tablas y escribe un
reporte. No toca ninguna pantalla.

Tres cosas que conviene saber antes de creerle al numero:

1. **Si un programa no tiene precio, el alumno NO desaparece.** Sale en
   `sin_precio.csv` y el total dice explicitamente sobre cuantos se calculo. Un
   total que calla lo que le falta es peor que no tener total.
2. **Los descuentos salen de `alumnos_descuentos`**, que se llena a mano (ver
   abajo). Si ese archivo esta vacio la proyeccion es BRUTA, y lo dice.
3. **El puente entre el formulario y el catalogo esta escrito a mano** en
   `proyeccion.DEL_FORMULARIO`. El formulario dice "Somos musica (Adulto)
   Esencial" y el catalogo tiene eso partido en tres columnas; no hay llave
   comun. Se escribio explicito en vez de adivinarlo por parecido de texto: una
   proyeccion de dinero no se construye sobre coincidencias aproximadas. **Si
   cambia el texto del formulario, ese diccionario es lo que hay que tocar.**

### Quien tiene descuento

```bash
lisart descuentos            # pone al dia el archivo y avisa de lo que no cuadra
lisart descuentos --revisar  # solo revisa, no escribe
```

A quien se le aplica cual **no viene de ninguna fuente**: no esta en Jotform, no
esta en el Excel de la escuela y no se puede deducir. Lo decide la
administracion caso por caso, asi que la unica fuente posible es una persona
escribiendolo. Por eso `data/master/alumnos_descuentos.csv` es **la unica tabla
del sistema pensada para abrirse en Excel y editarse a mano**.

El archivo lista a **todos** los alumnos inscritos, uno por renglon. Los que
tienen descuento quedan arriba —los renglones vacios se van al final al
ordenar—, asi que se abre y lo primero que se ve es a quien se le esta
descontando.

| Para | Se hace |
| --- | --- |
| Dar de alta un descuento | escribir su nombre en la columna `descuento` |
| Quitarlo | borrar esa celda |
| Un segundo descuento | duplicar el renglon y cambiarle el descuento |

Al terminar, correr `lisart descuentos`: rellena el nombre del alumno, resuelve
la clave del catalogo, siembra el porcentaje, da de alta a los alumnos nuevos y
asigna los identificadores que falten. **Un renglon nuevo se puede dejar sin ID
y hasta sin `persona_id`**, escribiendo solo el nombre del alumno; el comando lo
resuelve, o avisa si hay dos alumnos que se llaman igual.

Lo que **no** hace es adivinar. Un descuento que no esta en el catalogo no se da
de alta solo: se reporta y no se escribe nada, igual que con los demas
catalogos.

Dos cosas que conviene saber:

- **El porcentaje va en puntos**: `5` es 5%, `100` es beca completa. El catalogo
  de la escuela mezcla las dos unidades en la misma columna (0.05 y 100.00) y
  aplicarlo tal cual cobraria mal; aqui se traduce a una sola, y el archivo es
  donde una persona lo confirma.
- **Manda la celda, no el catalogo.** El porcentaje se siembra del catalogo pero
  se puede ajustar por alumno, para pactar un caso particular sin inventar una
  entrada de catalogo. El precio de esa libertad: subir el descuento familiar
  del 5% al 7% obliga a tocar los renglones que lo tengan. El comando avisa
  cuando una fila se separo del catalogo.

Varios descuentos del mismo alumno se **suman**, con tope en 100%.

### Horarios y reposicion

La seccion **Horarios** de `lisart ui` muestra la semana tipo de cualquier
persona y deja editarla. La otra vista, **Buscar reposicion**, contesta la
pregunta que motivo todo esto: cuando un alumno falta, donde puede reponer.

**Los tres estados de una hora:**

| Estado | Como se guarda |
| --- | --- |
| `disponible` | una fila en `disponibilidad` |
| `bloqueado` | una fila en `disponibilidad` |
| `no_disponible` | **ninguna fila** — es la ausencia |

El tercero no se guarda a proposito: guardarlo seria tener dos formas de decir
lo mismo (una fila que dice "nada" y la falta de fila) y tarde o temprano se
contradicen. `horarios.estado_en()` si devuelve los tres.

**Bloqueado le gana a disponible** cuando los rangos se traslapan. El costo de
equivocarse no es simetrico: ofrecer una hora ocupada manda a un alumno a una
clase que no existe; no ofrecer una libre solo desperdicia un hueco.

La semana se dibuja como **linea de tiempo por dia**, no como cuadricula,
porque el dato son rangos: un rango es una barra. La ventana horaria es **fija**
(8–21) para que dos semanas se puedan comparar de un vistazo.

### La agenda de profesores

```bash
lisart ui --profesores
```

Aplicacion **aparte**, con otro camino: se entra **por la clase**.

```
clase  ->  profesor de esa clase  ->  su semana
```

`lisart ui` ya deja buscar a cualquiera por nombre; quien administra la docencia
piensa en "el piano de los jueves" y de ahi en quien lo da.

Las horas que los alumnos de la clase marcaron se pintan como **ocupadas para el
profesor**, con trama rayada para no confundirlas con un bloqueo capturado a
mano. **Es una aproximacion**, y la escuela lo sabe: un alumno marca cuando
*puede* venir, no cuando tiene clase, asi que sobra horas. **No se guarda** — es
un calculo, y guardarlo quedaria desfasado en cuanto un alumno cambie su horario.

Desde ahi tambien se crean clases, se asignan profesores y se inscriben alumnos,
porque esos datos todavia no llegan de ningun lado.

### Datos de prueba

```bash
lisart demo             # siembra
lisart demo --limpiar   # borra todo lo sembrado
```

Sin profesores ni clases no hay forma de ejercitar la agenda ni la reposicion.
**Todo lo que siembra lleva `fuente = "demo"`**: se ve en la columna, que esta a
la vista en cada tabla, y se borra entero sin tocar un dato real.

Los alumnos **no se inventan**: se inscriben alumnos de verdad, porque su
horario declarado es lo unico que hace visible la deduccion de horas ocupadas.
Al limpiar solo se quita la inscripcion, no el alumno.

### El grafo de relaciones

Es la ultima seccion. Contesta **que alumnos se parecen**: los que estudian el
mismo instrumento se agrupan alrededor de el, y los hermanos alrededor de su
tutor. Al hacer clic en un nodo se abre su ficha, con quien se le parece y por
que.

Cada nodo es una **figura musical**, y la figura va ademas del color:

| Nodo | Figura | Color |
| --- | --- | --- |
| Alumno | negra (cabeza llena + plica) | `#B33844` |
| Tutor o contacto | corchea (+ corchete) | `#1F6FB2` |
| Instrumento | redonda (hueca, sin plica) | `#A87200` |

La paleta paso las cinco comprobaciones del validador de daltonismo y contraste
(`scripts/validate_palette.js` del skill de visualizacion). **No cambiarla sin
volver a correrlo.**

Tres lentes: alumnos por instrumento, familias, y las dos juntas. El acomodo es
explicito (centros con `spring_layout` sobre un grafo reducido, alumnos en
anillo alrededor del suyo) porque `spring_layout` sobre el grafo completo
empujaba los racimos a los bordes y apelmazaba el centro.

> **No hay nodo de maestro.** El formulario de inscripcion no pregunta quien da
> la clase — se revisaron sus 77 campos. Cuando exista el dato entra como
> `relaciones` de tipo `profesor` ligadas **al alumno**, no al instrumento.

> **La seccion del grafo tarda ~1 min en pintar.** El saneador de Markdown de
> Streamlit se atraganta con los ~600 elementos del SVG. `st.html` borra el SVG
> y `components.html` lo pinta en 1 s pero su iframe va en sandbox y **mata el
> clic**, que es lo que hace util al grafo.

### Convertir inscripciones en personas

```bash
lisart procesar inscripciones
```

Cada envio menciona hasta cinco personas (alumno, tutor, contacto de
emergencia, dos autorizados a recoger), y muchas de esas menciones son **la
misma persona**: un tutor suele ser tambien el contacto de emergencia de su
hijo, y una mama con tres hijos aparece en tres envios.

Con los datos reales: **312 menciones que son 240 personas**. Sin deduplicar se
crearian 42 humanos de mas, y con ellos pagos que no cuadran y mensajes
duplicados.

La deduplicacion es por **nombre normalizado** (sin acentos, minusculas, sin
puntuacion). Correrlo dos veces no duplica nada: las personas se reconocen por
nombre y las relaciones por el trio (alumno, otra persona, tipo).

**Las familias no se guardan, se deducen.** Dos alumnos son hermanos si apuntan
al MISMO tutor. Guardar filas de "hermano" seria guardar una inferencia que se
puede quedar desactualizada; deducirla siempre da la respuesta correcta:

```python
from lisart.procesos.alta_inscripciones import familias
familias()   # tutor_persona_id, alumnos, alumno_persona_ids
```

El comando reporta **conflictos** al terminar. No son ruido: en la primera
corrida real detecto dos personas con fechas de nacimiento contradictorias, y
las dos resultaron ser errores de captura reales.

### Correrlo cada semana

El comando no se agenda solo. En Linux/WSL, con `crontab -e` (lunes 8am):

```cron
0 8 * * 1 cd /ruta/al/repo && .venv/bin/lisart ingest jotform && .venv/bin/lisart procesar inscripciones
```

En Windows es el Programador de tareas, apuntando al mismo comando. Correrlo de
mas no hace dano: si no hay envios nuevos, no escribe nada.

### El grafo en Obsidian

`lisart vault` genera la carpeta `vault/`, que se abre en Obsidian con
**"Open folder as vault"**. La vista de grafo muestra de un jalon como se
conectan tablas, fuentes de datos, documentos y los cuatro proyectos.

Los circulos **huecos** del grafo son notas que no existen: como los proyectos
ya enlazan a tablas que faltan (`pagos`, `envios`, `clases`), esos huecos son
literalmente el mapa de lo que falta construir.

`vault/Tablas/` se **regenera** en cada corrida desde `tables.py` — no editarla
a mano. `vault/Fuentes/`, `vault/Documentos/` y `vault/Proyectos/` se siembran
una sola vez y despues son tuyas: `lisart vault` no las pisa salvo `--forzar`.

`lisart validate` regresa codigo de salida 1 si encuentra errores, asi que
sirve para frenar un proceso automatico antes de que use datos malos.

## Uso desde Python o un notebook

```python
import pandas as pd
from lisart import read_table, upsert
from lisart.ids import ahora, next_ids, normalizar_nombre, normalizar_telefono

alumnos = read_table("alumnos")        # ya viene con los tipos correctos

pid, = next_ids("personas")            # 'PER-0001'
upsert("personas", pd.DataFrame([{
    "persona_id": pid,
    "nombre": "María José",
    "apellido_paterno": "Peña",
    "apellido_materno": "Hernández",
    "nombre_normalizado": normalizar_nombre("María José Peña Hernández"),
    "telefono": normalizar_telefono("55 1234 5678"),   # -> +525512345678
    "activo": True,
    "creado_en": ahora(), "actualizado_en": ahora(), "fuente": "jotform",
}]))
```

Regla unica e innegociable: **nunca `pd.read_csv` ni `df.to_csv` sobre
`data/`.** Todo pasa por `read_table` / `write_table` / `upsert`. Ahi viven la
validacion, los tipos y la escritura atomica.

## Como esta organizado

```
src/lisart/
  tables.py      <- EL MODELO DE DATOS. Empieza a leer aqui.
  fuentes/          conectores con sistemas externos
    jotform.py      formularios de inscripcion
    catalogos.py    el Excel de programas, precios y descuentos
  procesos/         de materia prima a la verdad de la escuela
    alta_inscripciones.py   inscripciones -> personas, alumnos, relaciones
    horarios.py             disponibilidad, estados y reposicion
    proyeccion.py           cuanto deberia entrar al mes
    descuentos.py           quien tiene descuento (el archivo que se edita a mano)
    demo.py                 datos de prueba, marcados y borrables
  ui/app.py         la pantalla principal (Streamlit)
  ui/app_profesores.py  la agenda de profesores (aplicacion aparte)
  ui/semana.py      la semana dibujada como linea de tiempo
  ui/grafo.py       el grafo de relaciones
  ui/iconos.py      iconos musicales en SVG
  backup.py         respaldos: nada se sobrescribe sin copia

assets/             logo, iconos y paleta de la escuela
  estilo.css        colores de marca para la pantalla
  schema.py         piezas para describir una tabla (Column, ForeignKey, Table)
  io.py             leer y escribir CSV con tipos y de forma atomica
  validate.py       las revisiones de integridad
  ids.py            IDs nuevos y normalizacion de nombres/telefonos
  cli.py            el comando `lisart`
  config.py         rutas y convenciones de formato

data/               los datos (NO se suben a git, ver "Privacidad")
  raw/              lo que llego de afuera, tal cual. Nunca se edita.
  interim/          pasos intermedios. Desechable.
  master/           la verdad de la escuela. Esto es lo que se respalda.
  exports/          reportes y Excel para gente. Desechable.
  catalogos_lisart.xlsx   el catalogo que mantiene la escuela a mano
  backups/          copias de seguridad. Fuera de las cuatro capas.

docs/
  guia_de_uso.md          arrancar, correr, editar y cambiar: paso a paso
  guia_de_uso.pdf         lo mismo en PDF, generado por `lisart guia`
  documentacion_general.md  que se construyo, por que, y que tan dificil fue
  documentacion_general.pdf lo mismo en PDF, generado por `lisart guia general`
  mapa_del_codigo.md      jerarquia de los modulos, front-end vs back-end
  mapa_del_codigo.pdf     lo mismo en PDF, generado por `lisart guia codigo`
  modelo_de_datos.md      generado por `lisart docs`
  convenciones_datos.md   las reglas de como se trabaja aqui

vault/              vault de Obsidian: el sistema como grafo
  Tablas/           GENERADO desde tables.py, no editar
  Fuentes/          Jotform, Kydemy, WhatsApp
  Documentos/       inscripcion, proyeccion, comprobante, reembolso
  Proyectos/        los cuatro proyectos + el punto de venta

tests/              pruebas. Corren contra carpetas temporales, nunca contra data/.
```

El flujo va siempre `raw -> interim -> master -> exports` y nunca al reves.
Si `interim/` y `exports/` se borran completos, se reconstruyen corriendo los
scripts. Si se borra `master/`, se perdio informacion.

## Que tablas hay hoy

El esqueleto es la **identidad**: quien es quien, y como se llama cada quien en
los tres sistemas que ya existen (Kydemy, Jotform, WhatsApp).

| Tabla | Para que |
| --- | --- |
| `personas` | Una fila por ser humano. Alumnos, tutores, profesores, empleados. |
| `personas_roles` | Que papel juega cada quien, y desde cuando. |
| `alumnos` | Lo que solo aplica a un alumno (estatus, alta, baja, programa). |
| `alumnos_instrumentos` | Que instrumento estudia cada alumno. De muchos a muchos. |
| `disponibilidad` | Cuando puede cada persona, semana tipo. Vale para alumnos y profesores. |
| `clases` | Que dia y a que hora es cada clase, y donde. |
| `clases_profesores` | Quien da cada clase. **Una clase puede tener varios.** |
| `clases_alumnos` | Quien la toma. |
| `relaciones` | Quien es tutor de quien, quien puede recoger, **quien paga por quien**. |
| `identificadores_externos` | El puente entre `persona_id` y el ID de Kydemy / Jotform / WhatsApp. |
| `espacios` | Aulas, auditorio, bodega, recepcion y cocina. Base de la calendarizacion. |
| `instrumentos` | Catalogo de instrumentos. |
| `conceptos` | Que se cobra y cuanto, con vigencias. |
| `programas` | Los programas de aprendizaje y su **cuota mensual**. Del Excel. |
| `descuentos` | Descuentos que reconoce la escuela. Del Excel. |
| `alumnos_descuentos` | A que alumno se le aplica cual. **Se edita a mano.** |
| `respuestas_inscripcion` | Lo que llega de Jotform, aplanado. Capa `interim`. |

Detalle completo en [`docs/modelo_de_datos.md`](docs/modelo_de_datos.md).

Todavia **no** existen `inscripciones`, `pagos`, `proyeccion_pagos` ni las
tablas de mensajeria: se agregan cuando se elija la primera rebanada de negocio.

## Privacidad

Estos datos incluyen nombres, domicilios, telefonos, firmas e identificaciones
de **menores de edad**. No es un detalle legal menor, es la razon de varias
decisiones del diseno:

- `data/**` esta en `.gitignore`. Lo unico que si se versiona son los catalogos
  (`espacios`, `instrumentos`, `conceptos`), porque no contienen datos personales.
- Las llaves de API van en `.env`, que tampoco se sube.
- Antes de compartir cualquier archivo de `exports/`, revisar que columnas lleva.

## Desarrollo

```bash
pytest -m "not ui"              # 141 pruebas (ciclo rapido)
pytest                          # 163, incluidas las de pantalla (~5 min)
ruff check src tests            # estilo
lisart docs --check             # avisa si la documentacion quedo desfasada
```

Al agregar o cambiar una tabla: se edita **solo** `src/lisart/tables.py`,
se corre `lisart docs` y se corre `lisart validate`.
