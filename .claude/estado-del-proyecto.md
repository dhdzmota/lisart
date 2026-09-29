# Estado del proyecto Lisart

> Bitácora viva. Se lee al inicio de cada sesión (`CLAUDE.md` la importa) y se
> actualiza al final. **Última actualización: 2026-09-10 (sesión 14).**

---

## 1. Qué es esto

Sistema administrativo para la escuela de música **Lisart** (profesores,
directores, empleados y alumnos). El objetivo es quitarle trabajo manual a la
administración.

Restricciones que vienen del usuario, no negociables sin que él lo diga:

- **Gratis / open source.** Python de preferencia. Nada de servicios de paga.
- **La base de datos son CSV**, a propósito. Decisión consciente: a escala de
  cientos de personas, un CSV disciplinado se abre en Excel, se respalda
  copiando una carpeta y no cobra renta.
- El usuario es data scientist con **poca experiencia en data engineering**.
  Al meter un patrón nuevo, explicar *por qué* existe y qué falla sin él.
- Vocabulario de dominio en español (alumno, tutor, salón, colegiatura);
  infraestructura en inglés. Comentarios y docs en español.

---

## 2. Los cuatro proyectos que quiere la escuela

Este es el mapa completo. **Nada de esto está construido todavía**, solo la base.

1. **Automatización de mensajes** a alumnos y profesores (recordatorios de pago
   e inscripción). Máx. ~15 mensajes distintos, algunos condicionales. Hoy se
   copia/pega un comando para enviar.
2. **Segmentación de alumnos.** Centralizar requisitos vía Google Forms / QR.
   Clasificar cada petición o problemática en su propia "canasta" (bandeja de
   entrada por tipo). ~95% digital; falta plan para el 5% no digital (tablet).
3. **Centralización de pagos.** Que todo pago quede registrado y referenciado
   solo, por cualquier medio. **No se acepta pago de quien no esté en el
   sistema.** Salidas: cuántos pagos, cuánto entró, cuánto falta.
4. **Calendarización (2ª etapa).** Cotejar agenda de salones × músicos ×
   horarios oficiales de alumnos. Salida: qué aulas y qué músicos están libres.

**Urge aparte:** punto de venta que relacione venta–servicio–cliente–proveedor.
Hoy se llena a mano día con día. El reto: hoy solo se relaciona la venta con el
producto, no con el cliente, y hay que generar automáticamente a quién le
representa un pago (el músico como proveedor).

**Ideal a futuro:** reporte automático de ingresos y egresos, y llenado
automático del documento de reembolso.

---

## 3. Dónde está parado el trabajo real

### WhatsApp
- Hoy es **monodireccional**: se envía, no se recibe.
- El mensaje ya se puede hiperpersonalizar (nombre, monto que debe) y calendarizar.
- Para leer respuestas haría falta pedir **API key** de WhatsApp.
- Falta revisar Facebook para comunicación de dos vías.

### ChatGPT / chatbot
- Ya hay un chatbot funcionando (las pruebas salieron bien).
- Pendiente: ponerle **políticas/límites** para que no conteste cualquier cosa.

### Fuentes de datos que hay que cotejar
1. Proyección de pago
2. Kydemy
3. WhatsApp (conversación "Pagos Lisart" — hay un `.zip` que el usuario estaba analizando)

El método que traía el usuario: partir de la conversación de Pagos Lisart (dice
quién ya pagó, con comprobante), estructurar eso, verificar contra Kydemy, y al
final comparar contra la proyección. El caso que rompe el cruce ingenuo es
**"Sofi paga por mí"** (quien paga ≠ el alumno).

**Objetivo actual declarado:** automatizar la creación de la proyección de pago
y la generación en Kydemy de los comprobantes.

---

## 4. Lo que YA está construido (sesión 2026-08-08)

Se levantó el repo desde cero. Antes solo existía un notebook y carpetas vacías.

### Paquete `lisart` — la capa que cuida los CSV

| Archivo | Qué hace |
| --- | --- |
| `src/lisart/tables.py` | **El modelo de datos.** Fuente única de verdad. Empezar a leer aquí. |
| `src/lisart/schema.py` | Piezas para describir tablas: `Column`, `ForeignKey`, `Table`, `Registry`. |
| `src/lisart/io.py` | Lectura/escritura tipada y **atómica**. Nadie más toca `data/`. |
| `src/lisart/validate.py` | Revisiones: tipos, obligatorios, PK, catálogos, referencias. |
| `src/lisart/ids.py` | IDs nuevos (`PER-0001`) y normalización de nombres/teléfonos. |
| `src/lisart/cli.py` | Comando `lisart`: `init`, `validate`, `describe`, `docs`, `vault`. |
| `src/lisart/vault.py` | Genera el vault de Obsidian (el sistema como grafo). |
| `src/lisart/fuentes/jotform.py` | Conector de Jotform: descarga, aplanado e ingesta incremental. |
| `src/lisart/procesos/alta_inscripciones.py` | Inscripciones → personas, alumnos, relaciones. Aquí vive la deduplicación. |
| `src/lisart/ui/app.py` | La pantalla (Streamlit): pestañas, flechas ◀ ▶, edición. |
| `src/lisart/ui/iconos.py` | Iconos musicales en SVG, dibujados sobre una retícula común. |
| `assets/estilo.css` | El sistema de diseño. Ahí está el porqué de cada color. |
| `src/lisart/backup.py` | Respaldos. Nada se sobrescribe sin dejar copia. |
| `src/lisart/ui/grafo.py` | El grafo de relaciones: nodos como figuras musicales. |
| `src/lisart/ui/app_profesores.py` | **App aparte**: clase → profesor → su semana. |
| `src/lisart/ui/semana.py` | La semana dibujada como línea de tiempo. |
| `src/lisart/procesos/horarios.py` | Estados, rangos y reposición. |
| `src/lisart/procesos/demo.py` | Datos de prueba, marcados con `fuente='demo'`. |
| `src/lisart/config.py` | Rutas, convenciones de formato y lectura de `.env`. |

### Las 14 tablas que existen

`personas`, `personas_roles`, `alumnos`, `relaciones`,
`alumnos_instrumentos`, `identificadores_externos`, `respuestas_inscripcion`
(capa interim), y los catálogos `espacios`, `instrumentos`, `conceptos`.

**Cuántas filas tiene cada una hoy** (2026-08-11). Lo marcado *(demo)* es de
prueba y se borra con `lisart demo --limpiar`:

| Tabla | Filas | | Tabla | Filas |
| --- | --- | --- | --- | --- |
| `personas` | 243 *(3 demo)* | | `alumnos_instrumentos` | 129 |
| `personas_roles` | 172 *(3 demo)* | | `identificadores_externos` | 312 |
| `alumnos` | 115 | | `respuestas_inscripcion` | 115 |
| `relaciones` | 194 | | `espacios` | 10 |
| `instrumentos` | 15 | | **`conceptos`** | **0 ← vacía** |
| `disponibilidad` | 156 *(11 demo)* | | `clases` | 4 *(todas demo)* |
| `clases_alumnos` | 12 *(demo)* | | `clases_profesores` | 5 *(demo)* |
| `programas` | 13 | | `descuentos` | 7 |
| **`alumnos_descuentos`** | **115 ← todos sin descuento todavía** | | | |

Los **145 bloques reales** de `disponibilidad` son los horarios que declararon
los 115 alumnos en el formulario. Los profesores y las clases son **todos de
prueba**: no hay ni uno real todavía.

### Estructura física de la escuela (capturada 2026-08-08, sesión 2)

`data/master/espacios.csv` ya tiene los 10 espacios reales. **7 son agendables.**

| Planta baja (la escuela le dice "primer piso") | Planta alta ("arriba") |
| --- | --- |
| `AULA-GRANDE` Salón grande — el aula más grande | `AUDITORIO` Sala grande — se usa como auditorio |
| `AULA-CH-1/2/3` tres salones pequeños | `AULA-MEDIANA` Salón mediano |
| `RECEPCION` (no agendable) | `AULA-BATERIA` Salón de batería |
| `COCINA` (no agendable) | `BODEGA` (no agendable) |

Decisiones al capturar esto:

- La tabla se llamaba `salones` y se **renombró a `espacios`**: recepción,
  cocina y bodega no son salones, y la calendarización nunca debe ofrecer la
  cocina para dar clase. Se hizo cuando la tabla estaba vacía, o sea gratis.
- Se agregaron las columnas `tipo`, `piso` y **`agendable`**. `agendable` es la
  que separa un aula de la cocina, y la que deja convertir la bodega en salón
  algún día sin tocar el modelo (el usuario dijo "pudiese ser otro salón pero
  en realidad no lo es").
- `piso` usa `planta_baja` / `planta_alta` en vez de números **a propósito**:
  en la escuela le dicen "primer piso" a la planta baja, y numerar garantizaba
  confusión.
- El auditorio es un espacio **aparte** del salón grande, y tanto él como la
  bodega están **arriba** (confirmado por el usuario, no inferido).

### Decisiones de diseño que condicionan todo lo demás

- **Una persona es una persona.** Un profesor que además es tutor de su hija es
  UNA fila en `personas` con dos roles. Duplicar humanos es la causa raíz de
  pagos que no cuadran y mensajes duplicados.
- **`alumnos` extiende a `personas`** usando el mismo `persona_id` como PK. No
  se inventó un `alumno_id` aparte: dos llaves para la misma persona terminan
  desincronizadas.
- **`identificadores_externos`** es el puente entre `persona_id` y el ID de
  Kydemy / Jotform / WhatsApp. Es la pieza diseñada para el cruce de las tres
  fuentes sin adivinar por nombre.
- **`relaciones` tiene el tipo `paga_por`** — resuelve el caso "Sofi paga por mí".
- **Catálogos vs. gestionadas.** `salones`, `instrumentos` y `conceptos` se
  editan a mano (UTF-8 **con BOM** para que Excel en español no rompa acentos;
  al leer acepta `VERDADERO`/`FALSO`/`si`/`no`). Las demás solo las escribe el
  código, en UTF-8 limpio. Esto salió de una decisión explícita del usuario:
  edición **mixta**.
- **Capas** `raw → interim → master → exports`, el flujo nunca va al revés.
  `raw` es inmutable. Solo `master` se respalda.
- Se descartó **pandera** a propósito: las reglas necesarias (PK, FK, enums,
  nulos) son simples, pandera no hace FK entre tablas de todos modos, y evita
  una dependencia con historial de cambios de API. Si algún día se necesita
  algo más rico, el cambio se hace solo en `validate.py`.

### Verificado (no solo escrito)

- 114 pruebas pasan (`pytest`), `ruff check` limpio. Las 13 de pantalla llevan
  marcador `ui` porque tardan ~4 min; el ciclo rápido es `pytest -m "not ui"`.
- `lisart init` / `validate` / `docs` / `describe` corren de verdad.
- Se rompieron datos a propósito y el validador detectó los 5 tipos de error
  con número de línea del archivo. `lisart validate` sale con código 1.
- Alta real de una persona + alumno vía `upsert`, con acentos y ñ intactos.

### Documentación

- `README.md` — instalación, comandos, uso, privacidad.
- `docs/convenciones_datos.md` — las 10 reglas de la casa, con el porqué.
- `docs/modelo_de_datos.md` — **generado** por `lisart docs`. No editar a mano.

### Vault de Obsidian (sesión 2) — cierra el pendiente #4

`lisart vault` genera `vault/`, que se abre en Obsidian con "Open folder as
vault". Es el grafo visual del sistema: tablas, fuentes, documentos y proyectos.

- **`vault/Tablas/` se regenera completo** desde `tables.py` en cada corrida
  (se borra y se reescribe, para que una tabla eliminada no deje nota huérfana).
- **`Fuentes/`, `Documentos/`, `Proyectos/` se siembran una vez** y después son
  del usuario. `lisart vault` no las pisa salvo `--forzar`. La regla: lo derivable
  se genera, lo que es conocimiento humano se respeta.
- `make docs` corre `lisart docs` **y** `lisart vault`, para que no se desfasen.
- Truco de diseño: los proyectos enlazan a tablas que **todavía no existen**
  (`[[pagos]]`, `[[envios]]`, `[[clases]]`). En el grafo salen como círculos
  huecos, así que el grafo mismo es el mapa de lo que falta construir.
- Lleva diagramas mermaid (ER del modelo, flujo de capas, identidad). Se generó
  y validó el texto; **no se vio renderizado en Obsidian**.

---

### Ingesta de Jotform (sesión 3) — el notebook ya es código

`lisart ingest jotform` reemplaza al notebook. Baja todo, guarda copia cruda en
`data/raw/jotform/`, aplana a las **113 columnas** de `respuestas_inscripcion`
y **solo agrega lo que no estaba**. Si no hay nada nuevo, no toca el archivo.

- La tabla vive en **`interim`, no en `master`**, porque se reconstruye entera
  desde los JSON crudos. No es todavía la verdad de la escuela: es materia
  prima para dar de alta personas y alumnos. Ese paso **falta**.
- Se baja todo cada vez (no solo lo nuevo) para detectar envíos **editados o
  borrados** en Jotform. Se reportan pero no se pisan; `--actualizar` los trae.
- Las 113 columnas **se generan** desde `jotform.CAMPOS`, no se escriben a mano.

**Tres cosas del notebook que NO se copiaron, a propósito:**

1. El `.strip().lower().title()` sobre todos los valores. Convertía "MARÍA" en
   "María" (bien) pero también "DE LA O" en "De La O" (inventar). En interim el
   texto se guarda **como llegó**; normalizar es trabajo del paso a `personas`.
2. La comparación del manifiesto contra el texto exacto de **2026**, que se
   rompía solo el siguiente ciclo. Se guarda el texto tal cual.
3. `process_am_pm` está roto en el notebook (la rama `Am` suma 12 horas y no
   retorna, siempre da `None`). Solo se usaba en celdas de exploración.

**Bug encontrado en el notebook:** `name_dict` tenía la llave `71` repetida
(`uso_imagen__nombre_completo_alumno` y `..._tutor`); la segunda ganaba y un
campo se perdía en silencio. Aquí quedó como un solo `uso_imagen__nombre_completo`.

> **El riesgo estructural:** Jotform identifica los campos por su **posición**
> en el formulario. Si alguien reordena o inserta una pregunta, los datos caen
> en la columna equivocada **sin que nada truene**. `revisar_mapeo()` corre en
> cada ingesta y avisa. Hay que hacerle caso a esos avisos.

---

### LA BASE YA EXISTE (sesión 4) — 115 alumnos reales cargados

Se corrió la API de verdad y se construyó la base. **Este es el estado real de
`data/master/` hoy**, no un ejemplo:

| Tabla | Filas | Nota |
| --- | --- | --- |
| `respuestas_inscripcion` | 115 | envíos de Jotform, todos ACTIVE |
| `personas` | 240 | 240 con teléfono, 225 con correo, 176 con fecha de nacimiento |
| `personas_roles` | 169 | 115 alumno + 54 tutor; **7 personas tienen los dos roles** |
| `alumnos` | 115 | **59 menores de edad, 56 mayores** (edades de 2 a 69) |
| `relaciones` | 194 | 113 emergencia, 64 tutor, 17 autorizado_recoger |
| `identificadores_externos` | 312 | rastro `<envío>#<papel>` de cada persona |

- **312 menciones → 240 personas.** Sin deduplicar entre roles se habrían
  creado 42 humanos de más. El 25% de los tutores es además contacto de
  emergencia, y 7 alumnos son además tutores de alguien.
- **10 familias con hermanos** (9 con 2 alumnos, 1 con 3), 21 alumnos en total.
- **Los 59 menores tienen tutor registrado.** 2 alumnos no tienen contacto de
  emergencia.
- 78 personas no tienen ningún rol: solo son contacto de emergencia o
  autorizado a recoger. Es correcto, no un hueco.

### Decisiones de esta sesión y por qué

- **Las familias NO se guardan, se deducen** (`familias()`): dos alumnos son
  hermanos si apuntan al mismo tutor. Guardar filas `hermano` sería materializar
  una inferencia que se queda desactualizada; deducirla siempre acierta.
- **La deduplicación es por nombre normalizado.** Es lo único que hay: Jotform
  no da IDs de persona. Cuando entre Kydemy, la llave buena será
  `identificadores_externos`.
- **La fecha de nacimiento en conflicto NO se resuelve por "el dato más
  reciente".** Se descubrió que en el bloque de tutor la gente captura la fecha
  del hijo (4 de 65 fechas de tutor dan menos de 18 años; en 5 envíos es
  idéntica a la del alumno). Regla nueva: gana la que la persona declaró **de
  sí misma** como alumno; si no se puede decidir, se deja **vacía**. Un hueco
  se nota y se corrige; una fecha equivocada se propaga.
- Se agregó `lisart ingest jotform --desde-raw`, que rehace la tabla desde los
  JSON guardados sin llamar a la API. Es la razón de ser de la capa `raw`, y se
  usó de verdad al corregir la especificación de campos.

### Lo que la corrida real enseñó del formulario

`revisar_mapeo()` disparó en la primera corrida y evitó datos mal colocados:

- El campo **3** es un `control_textbox`, no un nombre estructurado.
- Los campos **70 y 71 son dos cosas distintas**, no una. Se confirmó con los
  datos: los 55 que llenan el 70 son **todos mayores de edad** y marcan
  `autorizo_mayor`; los 59 que llenan el 71 son **todos menores** y marcan
  `autorizo_menor`. O sea 70 = alumno adulto firmando por sí mismo, 71 = tutor
  firmando por un menor. El notebook perdía el 70 completo.
- Existen los campos 29 (comprobante de domicilio) y 33 (fecha de nacimiento
  del contacto de emergencia), que el notebook ignoraba. Hoy nadie los llena.
- El formulario **no pregunta el parentesco** (madre/padre/abuela). Por eso
  `relaciones.parentesco` está vacío en las 194 filas.

---

### La pantalla (sesión 5)

`lisart ui` abre Streamlit: **una pestaña por tabla**, un registro a la vez,
flechas `◀ ▶`, buscador. Usa el logo, los iconos y la paleta real de `assets/`
(`#FDBB02` dorado, `#B33844` vino, `#7C736E` gris; salieron de
`assets/imagenes/lisart_assets_color_pallete.png`).

Decisiones y su porqué:

- **Los controles se generan desde `tables.py`.** El tipo decide el widget, un
  catálogo se vuelve lista desplegable y una llave foránea se vuelve un
  selector de valores existentes (imposible escribir una referencia rota). Al
  agregar una columna al modelo aparece sola en pantalla; la app no duplica el
  esquema.
- **No se puede editar lo que no se debe:** llave primaria (rompería
  referencias), marcas de tiempo, y **todas las tablas de capa `interim`**
  —`respuestas_inscripcion` se regenera desde `raw`, editarla sería trabajo
  perdido. La pantalla lo dice en un aviso.
- Los números se capturan como **texto**, no con `number_input`: ese control no
  puede quedar vacío y aquí "sin dato" es distinto de "cero".
- Las flechas usan `on_click` (callback) y no el valor de retorno del botón.
  Con el valor de retorno, el estado deshabilitado se calcula con la posición
  vieja y en el último registro `▶` se ve habilitado un render de más. **Ese
  bug lo encontró una prueba, no la vista.**
- La carga usa `st.cache_data` con la fecha del archivo como llave: al guardar
  cambia el mtime y la caché se invalida sola.

### Respaldos (sesión 5)

`data/backups/<tabla>/<tabla>_<fecha>.csv`, **fuera de las cuatro capas** a
propósito: no son parte del flujo, son red de seguridad.

- Se respalda el estado **anterior** justo antes de escribir, y solo si el dato
  nuevo pasó la validación (un intento fallido no llena la carpeta de copias).
- Se conservan las últimas **50** copias por tabla, para no acumular copias de
  datos personales para siempre.
- Restaurar está en la misma pantalla, y **restaurar también deja copia** de lo
  que pisa: deshacer una restauración tiene que ser posible.

---

### Rediseño de la pantalla (sesión 6)

La primera versión se veía genérica. El usuario lo dijo sin rodeos y tenía
razón. Se instalaron dos skills de diseño (`anthropics/skills@frontend-design`
y `vercel-labs/agent-skills@web-design-guidelines`) y se rehízo con criterio.

**El diagnóstico que lo destrabó:** la skill advierte que el diseño generado por
IA cae en tres clichés, y el primero es *fondo crema cálido + serif de alto
contraste + acento terracota*. Eso era exactamente lo que yo había hecho.

**La dirección nueva: partitura impresa.**

- **Color.** Tinta negra sobre papel de partitura. El vino `#B33844` de la
  paleta de Lisart es **el lápiz rojo con el que un músico anota su partitura**:
  marca el registro actual y la acción de guardar, o sea dónde se interviene la
  hoja. El oro `#FDBB02` **no se reparte**: vive en la banda de marca y en el
  subrayado de la pestaña activa.
- **Tipografía.** *Bodoni Moda* para títulos —la didona es la letra de los
  programas de concierto, no una serif editorial cualquiera—, *IBM Plex Sans*
  para la interfaz e *IBM Plex Mono* para todo lo que se lee dígito por dígito
  (IDs, teléfonos, fechas): en monoespaciada se alinean y se comparan.
- **Firma.** El navegador **es un pentagrama**: la nota roja es el registro
  abierto y las grises sus vecinos. Toda la app consiste en recorrer registros
  de uno en uno, que es lo que hace una melodía.
  - La **altura** de cada nota sale de `MELODIA` (primera frase del Himno a la
    Alegría, dominio público, subida de octava para que quepa sin líneas
    adicionales), indexada por número de registro. **Determinista, no
    aleatoria**: si se sorteara, la misma persona cambiaría de nota en cada
    refresco de Streamlit y se vería como un parpadeo. Para cambiarla por una
    pieza de Lisart basta editar esa tupla.
  - Las plicas van hacia abajo de la 3ª línea para arriba, como se escribe.
  - Muestra una **ventana de 15 registros**, no la tabla entera: con 240
    repartidos en el ancho las notas quedaban a cuatro píxeles, encimadas, y la
    melodía no se leía. La posición exacta la da el contador.
- **Iconos.** SVG musicales propios (`iconos.py`) sobre una retícula de 24×24 y
  un mismo grosor de trazo. Se **descartaron** los PNG de `assets/iconos`: son
  ilustraciones de estilos distintos y juntas se ven como recortes pegados.
  Cada icono dice algo: `relaciones` es una ligadura (el arco que une dos
  notas), `identificadores_externos` un diapasón (afinar dos sistemas entre sí).

**Comprensión, no solo estética:**

- Los registros se titulan en lenguaje de personas: `relaciones` ya no muestra
  `PER-0042 → PER-0117` sino "Ana Torres Ruiz — tutor → Luis Torres Mena".
- Las 113 columnas de `respuestas_inscripcion` se agrupan en secciones
  (Alumno, Tutor, Contacto de emergencia…) y los rótulos no repiten el grupo:
  dentro de ALUMNO el campo se llama "nombre", no "alumno nombre completo nombre".
- Los rótulos llevan acento aunque las columnas no (`telefono` → TELÉFONO), y
  `area` se rotula **lada**, que es como se dice en México.

**Cómo se verificó:** se instaló Playwright y se tomaron capturas reales en
cada iteración. Las tres primeras versiones tenían defectos que solo se ven
mirando: logo ilegible, CSS de pestañas que no aplicaba (Streamlit ya no usa
`data-baseweb="tab"` sino `data-testid="stTab"`), aviso azul de sistema
rompiendo la paleta, rótulos repetidos.

**Un bug de datos que solo salió al navegar con capturas:** los controles del
formulario se nombraban `campo::<tabla>::<columna>`, igual en todos los
registros. Streamlit guarda el estado de un widget por su `key`, así que al
avanzar la tarjeta mostraba a Sofía pero los campos seguían con los datos de
Ana — y guardar habría sobrescrito a una con la otra. La llave ahora incluye
la llave primaria del registro. Hay una prueba que lo cubre.

**La auditoría (`web-design-guidelines`) encontró y se corrigió:**
`transition: all` (antipatrón), falta de `:focus-visible` (no se podía navegar
con teclado), `<img>` sin `width`/`height` (salto al cargar), falta de
`color-scheme: light` (controles nativos oscuros en sistemas en modo oscuro) y
cifras sin `tabular-nums`.

---

### El grafo de relaciones (sesión 7)

Primera pestaña de la app. Contesta "¿qué alumnos se parecen?": los que estudian
el mismo instrumento se agrupan a su alrededor, los hermanos alrededor del tutor.

**Modelo nuevo que hizo falta:** el catálogo `instrumentos` estaba vacío. Se
sembró con los **15 instrumentos reales** del formulario y se creó
`alumnos_instrumentos` (**129 vínculos**, 115 alumnos). También se agregó
`alumnos.programa` (el PDA) y el tipo `profesor` a `relaciones`.

- Los instrumentos **no se inventan desde el código**: el catálogo lo mantiene
  una persona, así que si el formulario trae uno desconocido se avisa en vez de
  darlo de alta solo. Llenar un catálogo desde código lo llena de variantes mal
  escritas sin que nadie lo note.

**Cada nodo es una figura musical**, y la figura va además del color:

| | | |
| --- | --- | --- |
| Alumno | negra (cabeza llena + plica) | `#B33844` |
| Tutor o contacto | corchea (+ corchete) | `#1F6FB2` |
| Profesor | blanca (cabeza hueca + plica) | `#D07AB8` |
| Instrumento | redonda (hueca, sin plica) | `#A87200` |

La paleta se validó con el script del skill de visualización: **las cinco
comprobaciones pasan** (banda de luminosidad, croma, separación para daltonismo,
piso de visión normal, contraste). El rosa queda apenas bajo 3:1 de contraste,
lo que obliga a dar relieve por otro lado — por eso el grafo lleva **siempre**
leyenda con las figuras dibujadas y ficha de texto del nodo.

**Decisiones de dibujo:**

- **El acomodo es explícito, no `spring_layout`.** Como cada instrumento con sus
  alumnos es casi un componente aparte, el algoritmo los empujaba a los bordes y
  apelmazaba el centro: disperso y apretado a la vez. Ahora los centros se
  colocan con spring sobre un grafo reducido (dos instrumentos se tocan si
  comparten alumnos) y los alumnos van en anillo alrededor del suyo. Una
  relajación separa los anillos para que no se invadan.
- **Quien estudia dos instrumentos se coloca entre los dos:** en el dibujo se ve
  como el puente que es.
- **Las aristas son arcos, no rectas.** Cuarenta y un alumnos colgando del piano
  con líneas rectas se ven como un abanico macizo.

**Estado final del grafo (cierre de sesión 7):**

- **Tres figuras, no cuatro.** El nodo de maestro se quitó: se revisaron los 77
  campos del formulario y las 345 apariciones de "profe"/"titular" (todas texto
  legal repetido). **El dato no existe.** Cuando llegue, entra como `relaciones`
  de tipo `profesor` ligadas **al alumno**, no al instrumento.
- **Tres lentes:** por instrumento, familias, y las dos juntas (177 nodos).
- **El grafo es la última sección.**
- La navegación dejó de ser `st.tabs`: **la sección viaja en la dirección**
  (`?seccion=grafo&nodo=PER-0006`). Sin eso, con el grafo al final, un clic en
  un nodo recargaba y botaba al usuario a la primera pestaña. De paso solo se
  arma la sección visible: **las tablas bajaron de ~30 s a 1.6 s**.

### Trampas del entorno (comprobadas, no supuestas)

Están también en `CLAUDE.md` para no volver a tropezar:

- **Ninguna librería de gráficas de Streamlit dibuja nada en este equipo:**
  plotly, altair y hasta los gráficos nativos salen vacíos, sin error. Se
  comprobó con una app mínima. Por eso el grafo es SVG en línea, igual que el
  pentagrama. El clic viaja por la dirección (`?nodo=...`), sin JavaScript, y
  **por eso el grafo es la primera pestaña**: al recargar, Streamlit vuelve a la
  primera, que es justo donde se quiere caer.
- `st.html` **sanea el SVG hasta borrarlo**. `components.html` lo pinta en 1 s
  contra 60, pero su iframe va en **sandbox** y bloquea la navegación de la
  página padre: mata el clic en los nodos. La única vía que conserva el clic es
  `st.markdown(..., unsafe_allow_html=True)`, y su saneador es el que tarda.
- `pkill -f "streamlit run"` **se mata a sí mismo**: el patrón aparece en su
  propia línea de comando. Usar `fuser -k 8501/tcp`.
- Para verificar la pantalla, **tomar capturas**: se instaló Playwright y tres
  defectos de diseño y dos bugs reales solo se vieron mirando.

---

### Horarios y reposición (sesión 8)

Desarrollo independiente, pedido aparte. Cuatro tablas nuevas, un tipo de dato
nuevo y el módulo `procesos/horarios.py`.

| Tabla | Para qué |
| --- | --- |
| `disponibilidad` | Cuándo puede cada persona, semana tipo. **144 filas ya cargadas** |
| `clases` | Qué día y a qué hora es cada clase |
| `clases_profesores` | Quién la da. De muchos a muchos: **una clase puede tener varios** |
| `clases_alumnos` | Quién la toma |

**Decisiones y su porqué:**

- **Los tres estados, pero solo se guardan dos.** La escuela los definió como
  disponible / bloqueado / *"ni lo uno ni lo otro"*. Ese tercero **es la
  ausencia de fila**: guardarlo sería tener dos formas de decir lo mismo —una
  fila que dice "nada" y la falta de fila— y tarde o temprano se contradicen.
  `horarios.estado_en()` sí devuelve los tres: el almacenamiento guarda lo
  mínimo y la API contesta lo que se le pregunta.
- **Bloqueado le gana a disponible** cuando los rangos se traslapan. El costo de
  equivocarse no es simétrico: ofrecer una hora ocupada manda a un alumno a una
  clase que no existe; no ofrecer una hora libre solo desperdicia un hueco.
- **Rangos, no casillas.** "Lunes de 9 a 14" es una fila, no diez. Los bloques
  contiguos se unen al leer.
- **`disponibilidad` es por persona, no por profesor.** Así el horario que los
  115 alumnos ya declararon en el formulario entra sin inventar otra tabla — y
  la reposición puede cruzar al profesor **con el alumno**.
- **Tipo de dato `time` nuevo** en `schema.py`/`io.py`, en 24 horas: el
  formulario da "5:00 pm", que se ordena mal y se compara peor.
- `vigente_desde`/`vigente_hasta` porque el horario cambia: cerrar el viejo
  conserva por qué una clase estaba donde estaba.

**Dato real cargado:** los 115 alumnos declararon horario en el formulario y
estaba sin usar (era el pendiente E1). Ya son **144 bloques** de disponibilidad,
repartidos L 24 · M 30 · Mi 31 · J 22 · V 21 · S 16.

**La pantalla (sesión 8):** sección **Horarios**, con dos vistas —"La semana de
alguien" y "Buscar reposición"—.

- La semana se dibuja como **línea de tiempo por día**, no como cuadrícula: el
  dato son rangos, así que un rango es una barra. De paso son ~40 elementos SVG
  en vez de ~140, y el saneador de Streamlit se atraganta con los grandes.
- **La ventana horaria es fija (8–21).** Ajustarla a los datos parecía listo
  pero hacía que dos semanas del mismo horario no se pudieran comparar.
- Se edita con un formulario de rangos (día, desde, hasta, estado), no picando
  celdas: editar casillas pelearía contra el modelo, que guarda rangos.
- El interruptor de vista es `st.pills` y no otro radio, porque el radio de
  navegación va disfrazado de pestañas y el disfraz se le pegaba.

> **Bug que llevaba dos sesiones a la vista y nadie vio:** la navegación mostraba
> los círculos del radio. El CSS apuntaba a `label > div:first-child`, pero el
> primer hijo es un `<span>` y el círculo visible es un `<div>` anidado tres
> niveles adentro. Se arregló apuntando a `[data-testid="stRadioOption"]`.

> **Falta el otro lado.** No hay ni un profesor ni una clase en la base, así que
> `opciones_de_reposicion()` hoy devuelve vacío para todos. El modelo está
> probado con 21 pruebas, pero la reposición no se puede usar hasta que existan
> profesores (pendiente C1) y se capturen las clases.

---

### Pantalla de profesores (sesión 8) — aplicación aparte

`lisart ui --profesores`. **Es una app separada**, a petición de la escuela,
aunque comparte todo lo de abajo: el mismo modelo, la misma escritura con
respaldo, el mismo dibujo de semana y la misma identidad.

Lo que cambia es el camino: se entra **por la clase**, no por la persona.

    clase  →  profesor de esa clase  →  su semana

`lisart ui` ya deja buscar a cualquiera por nombre. Quien administra la docencia
no piensa en personas sueltas, piensa en "el piano de los jueves" y de ahí en
quién lo da.

**La aproximación que pidió la escuela:** las horas que los alumnos de una clase
marcaron se pintan como **ocupadas para el profesor**, con trama rayada para no
confundirlas con un bloqueo capturado a mano. La escuela sabe que no es exacta
—un alumno marca cuándo *puede* venir, no cuándo tiene clase, así que sobra
horas— y aun así sirve mientras no haya el dato real.

**No se guarda:** es un cálculo. Guardarlo obligaría a recalcularlo cada vez que
un alumno cambie su horario, y quedaría desfasado solo. Hay una prueba que
verifica que la tabla sigue teniendo solo los dos estados guardables.

**Como no hay clases ni profesores todavía, la app los da de alta:** crear una
clase y asignarle profesor desde ahí. Asignar a alguien a dar clase también le
pone el rol `profesor`, porque dejarlo sin rol lo escondería del resto del
sistema.

---

### Datos de prueba (sesión 8)

`lisart demo` / `lisart demo --limpiar`. Sin profesores ni clases no había forma
de ejercitar la agenda ni la reposición, y capturarlos a mano dejaba basura
mezclada con los 240 registros reales.

**La regla: todo lo sembrado lleva `fuente = "demo"`.** Se ve en la pantalla —la
columna está a la vista en cada tabla— y se borra entero con una orden, sin
tocar un dato real. Se agregó `"demo"` al catálogo de `fuente`.

Siembra 3 profesores con su semana (incluye bloqueos con motivo), 4 clases —una
con dos profesores— y **inscribe alumnos de verdad**, no inventados: su horario
declarado es lo único que hace visible la deducción de horas ocupadas. Al
limpiar solo se quita la inscripción, no el alumno.

Con esto la **reposición devuelve opciones reales** por primera vez.

### Un bug de pandas que hay que conocer

`if fila["motivo"]` con una celda vacía lanza **"boolean value of NA is
ambiguous"**: pandas se niega a adivinar si un dato faltante es verdadero o
falso. Estaba en las dos apps (copié el patrón). Se corrigió con
`ui.app.tiene_valor()` y hay prueba de regresión. **Nunca evaluar una celda de
pandas como booleano directo.**

---

### Catálogo de precios y proyección de pago (sesión 9)

La escuela entregó `data/catalogos_lisart.xlsx`. Se trata **como fuente cruda**,
igual que Jotform: `lisart ingest catalogos` guarda copia con fecha en
`data/raw/catalogos/` y escribe las tablas. La escuela sigue editando su Excel.

**Tablas nuevas:** `programas` (13 programas con su cuota mensual) y
`descuentos` (7). A `instrumentos` se le agregaron `code` y `descripcion` de la
hoja `oferta_clases` — **no se cambiaron sus llaves**: `alumnos_instrumentos`
tiene 129 filas apuntando a ellas y migrarlas sería otra cosa.

**La proyección es un desarrollo aparte** (`procesos/proyeccion.py` +
`lisart proyeccion`): lee tablas y escribe a `exports/`. No toca ninguna
pantalla. Integrarla será conectarle esa función.

#### El resultado de hoy

    Proyección mensual: $148,655.00  sobre 98 de 115 alumnos (85%)

#### Tres cosas que el catálogo todavía no resuelve

1. **"Individual (1xsemana)" no tiene precio: 17 alumnos, el 15%.** No se
   inventa una cifra — salen listados aparte y el total dice lo que le falta.
   Hay que agregarlo al Excel.
2. **Los descuentos no se aplican.** Existen en el catálogo pero no hay tabla
   que diga qué alumno tiene cuál. La proyección es **bruta** y lo declara.
3. **La columna `valor_porcentual` mezcla unidades**: 0.05 para un 5% y 100.00
   para una beca completa. Se guarda tal cual y se avisa; aplicarlo así cobraría
   mal.

#### Cómo se amarra el formulario con el catálogo

No hay llave común: el formulario dice "Somos música (Adulto) Esencial" y el
catálogo tiene eso partido en nombre/categoría/arquetipo. La correspondencia
está **escrita a mano** en `proyeccion.DEL_FORMULARIO`, a la vista, en vez de
adivinarse por parecido de texto: una proyección de dinero no se construye sobre
coincidencias aproximadas. Si cambia el texto del formulario, ese diccionario es
lo que hay que tocar.

"Sesión suelta" es el único cuyo precio depende de la edad (bebé $405, resto
$375), así que se resuelve al vuelo.

#### Diferencias entre catálogos que salieron a la luz

- **Jarana** la eligieron alumnos pero no está en `oferta_clases`.
- **Bajo Eléctrico** y **La Música es un Juego** están en el catálogo y nadie los eligió.

---

### Descuentos por alumno (sesión 10)

El catálogo decía qué descuentos existen; faltaba **a quién se le aplica cuál**.
Ese dato no está en Jotform, no está en el Excel de la escuela y no se deduce de
nada: lo decide la administración caso por caso. La única fuente posible es una
persona escribiéndolo.

**Tabla nueva `alumnos_descuentos`** (`ownership="hand_edited"`, UTF-8 con BOM):
es **la única tabla del sistema pensada para abrirse en Excel**. Lista a los 115
alumnos inscritos, uno por renglón; se escribe el nombre del descuento en su
celda y se corre `lisart descuentos`.

Decisiones y su porqué:

- **Un alumno puede llevar varios descuentos** (decisión del usuario): la
  identidad de la fila es un ALD-#### y no `(alumno, descuento)`, porque el
  archivo también tiene que listar a los que **no** tienen ninguno —si no, no
  hay dónde escribirlo— y esos dejan la celda vacía.
- **Las dos llaves aceptan quedar vacías**, a contrapelo del resto del modelo.
  En un archivo que se edita en Excel, agregar un renglón es duplicar el de
  arriba; obligar a inventar un ID a mano es lo que hace que un archivo así se
  deje de usar. Quien las revisa y las rellena es `lisart descuentos`. Se puede
  incluso escribir solo el **nombre** del alumno: se resuelve si no hay dos que
  se llamen igual, y si los hay se pregunta en vez de elegir.
- **El orden hace el trabajo de la interfaz.** `sort_by=("descuento", "alumno")`
  y `write_table` ordena con los vacíos al final: los que tienen descuento
  quedan arriba, agrupados por tipo, sin agregar una columna ni tocar `io.py`.
- **El porcentaje se guarda en puntos** (5 = 5%, 100 = beca completa). Resuelve
  el pendiente que traía el catálogo: `valor_porcentual` mezcla 0.05 y 100.00 en
  la misma columna. La regla que las separa es que **nadie da un descuento de 1%
  o menos**, y el resultado queda escrito en el archivo que una persona revisa.
- **Manda la celda, no el catálogo** (decisión del usuario): se puede pactar un
  caso particular sin inventar una entrada de catálogo. El costo, asumido y
  avisado: cambiar el descuento familiar del 5% al 7% obliga a tocar los
  renglones que lo tengan. El comando avisa cuando una fila se separó del
  catálogo.
- **Varios descuentos se suman**, con tope en 100%. Es lo que se puede verificar
  a mano contra un recibo. Si la escuela los aplica en cascada, se cambia
  `descuentos.total_de()` y nada más.
- **El comando no adivina.** Un descuento que no está en el catálogo se reporta
  y **no se escribe nada**, para poder corregirlo en el mismo archivo. Misma
  regla que los demás catálogos.
- Un alumno dado de baja **con** descuento o notas conserva su renglón; sin nada
  escrito, se retira. Perder por qué alguien tenía beca es peor que cargar con
  un renglón de más.

**La proyección ya no es bruta.** Cada alumno lleva `precio_lista`, `descuento`,
`descuento_pct` y precio neto, y el resumen dice cuánto se está dejando de
cobrar: un descuento es dinero que la escuela decidió no cobrar y merece verse,
no desaparecer dentro de la cifra final. El Excel del formato de la escuela ya
llena sus columnas DESCUENTO y % —estaban en el archivo desde el principio, en
duro con "No" y 0—, con el porcentaje como fracción porque esa celda tiene
formato de porcentaje.

**Bug real corregido:** `ids.nombre_completo()` evaluaba `if p and not
pd.isna(p)`; con una celda vacía de pandas revienta con *"boolean value of NA is
ambiguous"*. Es la trampa #1 del proyecto y estaba en una función que usan
varios procesos —no había salido porque hasta ahora se le pasaban valores de
Python, no filas leídas con `read_table`. Hay prueba de regresión.

`make check` corre ahora también `lisart descuentos --revisar`: es la revisión
que le toca a un archivo que edita una persona.

Verificado sobre datos reales: el archivo se generó con los 115 alumnos, y en
una copia se simuló la edición (dos descuentos a un alumno, un renglón nuevo
escrito solo con el nombre). Se resolvió todo y la proyección bajó de
$148,655.00 a $146,985.25 con el desglose correcto.

### La guía de uso, y su PDF (sesión 10)

`docs/guia_de_uso.md` — el paso a paso de arrancar, correr, editar y cambiar.
Y `docs/guia_de_uso.pdf`, generado con `lisart guia`.

**Regla que pidió el usuario, explícita:** todo cambio que valga la pena o que
altere el funcionamiento se incorpora **al `.md` y al PDF**. El markdown es el
original; el PDF es la copia que se le entrega a la escuela.

- **Cómo se hace el PDF:** markdown → HTML → Chromium (Playwright) → PDF.
  Chromium porque ya estaba instalado para revisar la pantalla, pagina bien y no
  obliga a instalar LaTeX. **Las fuentes y el logo van incrustados** como data
  URI (`assets/fuentes/`, 85 KB): el PDF sale igual sin internet y idéntico en un
  año. Hay prueba de que el HTML no contiene ni una URL remota.
- **Cómo se sabe si el PDF quedó viejo:** al generarlo se guarda en
  `docs/guia_de_uso.sha256` la huella del markdown que lo produjo.
  `lisart guia --check` la recalcula, y corre dentro de `make check`. Editar la
  guía y olvidar el PDF **truena la revisión** en vez de pasar inadvertido. Sin
  eso, la regla de arriba dependía de que alguien se acordara.
- **La guía va con acentos y para público no técnico**, a diferencia del resto
  de `docs/`. Es el único documento del repo cuyo lector no es programador: lleva
  una tabla de "qué sección es para quién" y un glosario que traduce terminal,
  CSV, capa, llave foránea, ingesta. Un documento impreso para la escuela sin
  acentos se lee como un borrador.
- El diseño es el de la pantalla (Bodoni Moda, IBM Plex, el oro solo en la
  portada), por la misma razón de siempre: quien recibe el PDF y quien usa el
  sistema tienen que sentir que son la misma cosa.

Se revisó **mirándolo**, no solo generándolo: `pdftoppm` a PNG y a los ojos. Así
salieron dos defectos —el subtítulo de la portada cortado a la mitad (tomaba
solo la primera línea del párrafo) y una página casi en blanco por el párrafo
suelto antes de la primera sección—. Los dos corregidos, el primero con prueba.

### Se corrió la guía entera, a ver si era cierta (sesión 10)

El usuario preguntó si todo lo que dice la guía funciona o si hay maqueta. Se
ejecutó comando por comando contra una **copia completa** de los datos
(`LISART_DATA_DIR` a un temporal) y se levantaron las dos pantallas de verdad,
con capturas. Todo lo que la guía dice que hace algo, lo hace. Salieron **tres
defectos reales**, ninguno de ellos visible desde las pruebas:

- **`lisart proyeccion` tronaba si `data/` vive fuera del repo.** Los prints
  hacían `ruta.relative_to(PROJECT_ROOT)` y reventaban con `ValueError`
  **después** de haber escrito los archivos: el trabajo hecho y aun así un
  traceback. Es justo lo que hace quien no quiere datos de menores en una
  carpeta sincronizada. Ahora hay `cli.corta()` y lo usan los cuatro comandos
  que imprimen rutas.
- **La pestaña de la tabla nueva se llamaba `alumnos_descuentos`.** El mapa
  `ETIQUETAS` de la pantalla se quedó en las 10 tablas de la sesión 5; las siete
  agregadas después salían con su nombre de archivo y al final, en orden
  arbitrario. Se completó el mapa, que además es el que define el orden.
- **Las descripciones mostraban los `**` y las comillas del markdown.** Se
  escriben así porque de ahí sale también `docs/modelo_de_datos.md`, pero en la
  pantalla van dentro de un `<p>`, donde markdown no se procesa. `ui.app._realce()`
  las convierte a `<b>` y `<code>`.

Lo único que **no** se pudo comprobar aquí: la llamada real a la API de Jotform
(se corrió `--desde-raw`, que ejercita todo menos la red) y que el cron esté
agendado —no lo está, sigue siendo el pendiente E2—.

### Los roles, de tabla a directorio (sesión 11)

Lo pidió el usuario: la pestaña `Roles` mostraba `PER-0042 · tutor` un registro a
la vez, que no es una pregunta que nadie se haga. Las preguntas reales son dos y
van en direcciones opuestas, así que ahora hay dos lugares:

    ¿quiénes son los tutores?   ->  seccion Roles, un directorio
    ¿qué es esta persona?       ->  seccion Personas, un campo de su ficha

**Módulo nuevo `procesos/roles.py`.** El cambio es de dominio, no de pantalla:
ahí viven `por_rol()`, `de_persona()`, `conteo()` y `sincronizar()`, y la
pantalla solo llama. Por eso se puede probar sin levantar Streamlit (11 pruebas
rápidas) y mañana lo usa el CLI si hace falta.

Decisiones:

- **Quitar un rol no lo borra: lo cierra** con `vigente_hasta`. Borrarlo haría
  imposible entender por qué una clase de marzo estaba asignada a alguien que
  "nunca fue profesor". Las columnas de vigencia existían desde el principio;
  lo que faltaba era que algo las usara. Volver a darlo **reabre la misma fila**,
  no crea otra: la llave es (persona, rol) y dos filas es como se cuenta doble.
- **El directorio va en tabla nativa** (`st.dataframe`), no en HTML propio. Un
  directorio se lee en columnas, se ordena y se copia a Excel; eso ya lo hace
  bien. El salto a la ficha va por la dirección (`?seccion=personas&ir=PER-0042`),
  igual que el clic del grafo.
- El catálogo de roles sale del esquema (`PERSONAS_ROLES.column("rol").choices`),
  no de una lista aparte: agregar un rol en `tables.py` lo hace aparecer solo.

**El bug de rutas era más grande de lo que parecía.** El `relative_to(PROJECT_ROOT)`
que reventaba `lisart proyeccion` con `LISART_DATA_DIR` fuera del repo también
estaba en la pantalla, al guardar. Lo encontró una prueba nueva. Ahora hay
`config.ruta_corta()` y lo usan el CLI y la pantalla.

**Se completó `ETIQUETAS`**: las siete tablas agregadas después de la sesión 5
salían con su nombre de archivo y al final, en orden arbitrario.

> **Trampa que costó horas, ya en `CLAUDE.md`:** una sección puede tardar ~30 s
> en pintarse completa. Capturar a los 6 s y ver que falta el bloque de abajo
> hace creer que Streamlit se lo comió. **Antes de diagnosticar, mirar
> `stStatusWidget`:** si dice "Stop", el script sigue corriendo. Se llegó a
> reescribir el panel entero por un diagnóstico equivocado —aunque la versión
> con tabla nativa terminó siendo mejor que la que se iba a dibujar a mano—.

### La documentación general, y el generador de PDF de dos cabezas (sesión 12)

El usuario tenía un documento propio —*Documentación General de Desarrollos y
Proyectos Operativos de Lisart*— que describe **todos** los frentes de la escuela
(formularios, WhatsApp, pagos, CRM, agendas) a nivel panorama. Pidió el
equivalente para **este** repo, con detalle y diciendo qué tan difícil fue cada
pieza. Salió `docs/documentacion_general.md` + su PDF (**27 páginas**).

**Qué es y para quién.** Es el documento que lee quien no va a abrir el código:
dirección, o alguien que llega nuevo. Contesta *qué se construyó y por qué*,
mientras que la guía contesta *cómo se usa*. Los dos son los únicos documentos
del repo escritos con acentos y para público no técnico, y los dos cierran con
glosario.

**La idea que lo hace útil: dos escalas separadas, no una.** Cada pieza lleva
*dificultad de construcción* y *facilidad para explicarla*, y son
independientes a propósito. El grafo fue dificilísimo de construir y se explica
señalando la pantalla; la escritura atómica fue relativamente fácil y es casi
imposible de explicar, porque su valor entero consiste en un desastre que nunca
ocurre. **Las piezas de dificultad alta y explicación baja son las que alguien
podría quitar por no verles el sentido**, y por eso son las que más necesitan
estar escritas. Esa es la razón de ser del documento, no el inventario.

Se ancló al documento del usuario en vez de repetirlo: lo cita, y contesta su
recomendación #2 —*definir una estructura central de datos*—, que era la que
bloqueaba a las demás. La sección 14 mapea los cinco frentes de aquel documento
contra lo que este sistema ya toca.

**El generador dejó de ser de un solo documento.** `guia.py` tenía tres rutas
sueltas en duro (`FUENTE_MD`, `SALIDA_PDF`, `HUELLA`). Ahora hay un
`Documento(clave, nombre, md)` y **el PDF y la huella se derivan del nombre del
markdown**: tres rutas sueltas por documento es exactamente como se termina
generando el PDF de uno con el texto del otro. `lisart guia` regenera los dos,
`lisart guia general` uno solo, y `--check` revisa todos —o sea que `make check`
protege los dos PDF sin tocar el Makefile—.

Verificado: 27 páginas revisadas **mirándolas** con `pdftoppm`, no solo
generadas. Así salieron dos detalles —la nota de portada con un espacio de más
antes del punto, y el pie sin acentos porque el nombre venía del código, que es
ASCII—. Los dos corregidos.

### El mapa del código, para entregarle el repo a alguien (sesión 13)

El usuario va a **delegar el mantenimiento**. Pidió dos cosas: la jerarquía de
los scripts —cuál importa más y cuál menos— y qué pasa en front-end y qué en
back-end en cada uno. Salió `docs/mapa_del_codigo.md` + PDF (**18 páginas**),
tercer documento del repo con su lector propio: quien recibe el código.

**La jerarquía se midió, no se opinó.** Se armó el grafo de importaciones real
del paquete y se contó de cuántos módulos depende cada archivo. Ese número está
impreso en la tabla, y es lo que sostiene el orden: `io.py` lo importan 17
módulos, `tables.py` 13, `config.py` 11, `cli.py` **1**. Siete niveles, del
cimiento al andamio.

**El criterio del orden, escrito para que se pueda discutir:** *cuánto del
sistema queda mal si este archivo está mal* — no cuánto se usa ni qué tan grande
es. De ahí salen dos conclusiones que no son intuitivas y que son el punto del
documento:

- **`cli.py` tiene un solo dependiente y es de lo que más se corre.** Pocos
  dependientes no es poca importancia: es estar *arriba* de todo en vez de
  *abajo*. Por eso también es el mejor lugar para el primer cambio de alguien
  nuevo: el error es ruidoso y no toca datos.
- **`ids.py` va antes que `validate.py`** dentro del nivel de garantías, porque
  el daño que hace es **silencioso**: dos filas de la misma persona son dos
  filas perfectamente válidas. Es el único lugar del sistema donde el error no
  tiene quién lo atrape.

**Front-end vs back-end: la respuesta ingenua es la carpeta `ui/`, y es falsa.**
Aquí no hay front-end clásico —ni JavaScript, ni API, ni app de navegador—, así
que las palabras se redefinieron: back-end es lo que decide *qué es verdad*,
front-end lo que decide *cómo se ve*. **La línea real es `io.py`**, no la
carpeta. La sección 6 nombra las funciones concretas de `ui/app.py` que escriben
en `master/` (`_guardar`, `_agregar_bloque`, `_filtrar`) y marca la costura
exacta de `ui/grafo.py` (acomodo = back, `_figura`/`_arista`/`svg` = front).
También queda dicho que **la terminal es un front-end** —lo que imprime `cli.py`
lo lee una persona cada semana— y que hay front-end que no corre frente a nadie
(`guia.py`, `vault.py`).

**Las pruebas quedaron fuera de la jerarquía a propósito**, con la razón escrita:
no son el sistema, son lo que impide que se rompa sin avisar. Ponerlas últimas
en una lista de importancia le manda el mensaje contrario a quien recibe el
repo.

**Bug de maquetación encontrado mirando el PDF:** con `break-inside: avoid`, una
tabla de 25 filas —que no cabe en ninguna hoja— se empujaba entera a la
siguiente y dejaba **una plana en blanco** antes de partirse igual. Ahora
`table:has(tbody tr:nth-child(8))` deja partir sólo las largas, con `thead` como
`table-header-group` para repetir el encabezado y `tr{break-inside:avoid}` para
no cortar una fila a la mitad. Las tablas cortas siguen sin partirse.

De paso, las opciones de `lisart guia` **salen del registro** (`tuple(DOCUMENTOS)`)
en vez de una lista escrita aparte: agregar un cuarto documento ya no obliga a
acordarse del `choices`.

### La guía de entrega: cómo delegar el mantenimiento (sesión 14)

El usuario le pasa el repo a otro desarrollador **hoy** y preguntó tres cosas:
qué documentos enseñarle primero, qué es front-end y back-end, y cómo delegar
de forma que los dos entiendan el mismo proceso. Lo primero y lo segundo ya
estaban escritos (mapa del código, secciones 4, 6, 8 y 12); lo que faltaba era
el **proceso**. Salió `docs/guia_de_entrega.md` + PDF (**15 páginas**), cuarto
documento del registro de `guia.py` (`lisart guia entrega`).

**A quién le habla:** a los dos a la vez, y lo dice en la primera tabla (qué
secciones lee cada uno). Es el único documento del repo con dos lectores, y la
sección 4 —el acuerdo— está pensada para leerse juntos en la reunión.

**Lo que aporta que no estaba en ningún lado:**

- **Sección 0: qué hay que hacer antes de mandar un archivo.** A1 y A2 dejan
  de ser pendientes y pasan a ser requisito: la llave de Jotform **sigue en
  claro dentro del notebook** (`projects/` no está en `.gitignore`, así que un
  `git init` hoy la metería al historial), y sin historial no hay forma de ver
  qué cambió el otro. Más una tabla de qué se entrega y qué no: entregar la
  carpeta copiada se lleva `.env`, `data/` y 643 MB de `.venv`. Los datos
  reales van por etapas: primera semana sin ellos (`init` + `demo` funciona con
  la base vacía, se comprobó en `demo.py`), después con acuerdo de
  confidencialidad y `LISART_DATA_DIR` fuera de la carpeta del código.
- **Quién se queda con qué** (sección 3): llaves, datos, catálogos, decisiones
  de negocio y prioridad no se delegan. Se escribió porque un desarrollador
  nuevo lo asume todo suyo si nadie lo dice.
- **El proceso** (sección 4): agenda de la reunión de entrega, primera semana
  con criterio de aceptación por día, plantilla de cuatro renglones para pedir
  un cambio (el último, "cómo sabré que quedó", es el que evita el "yo pensé
  que era otra cosa"), los siete puntos de "terminado" (los de `CLAUDE.md`,
  en lenguaje de la escuela), plantilla de entrega de vuelta, y ritmo semanal.
  **La escuela revisa leyendo la bitácora, no el código**: si la entrada dice
  el porqué, el trabajo está bien; si dice solo "se arregló", se devuelve.
- **Cómo revisar sin leer código** (sección 5): siete preguntas con respuesta
  buena y señal de alarma. Es lo que le da al usuario control sin volverse
  técnico.
- **Lo que el desarrollador va a querer cambiar** (sección 7): las ocho
  decisiones que alguien nuevo intenta revertir en la primera semana (SQLite,
  `pd.read_csv`, plotly, normalizar en interim, tabla de familias…), cada una
  con dónde está explicada. Es la bitácora convertida en lista de "no todavía".
- **Primer encargo** (sección 8): E2 (cron), luego F6, B1b, F2. **No** B2 ni C1
  como primeros: son los más valiosos y por eso necesitan conocer `io.py` e
  `ids.py` antes.

**Front-end y back-end para quien no programa** (sección 2): la analogía es
cocina/bodega contra menú/comedor, y la consecuencia práctica es que **al pedir
un cambio conviene decir de cuál mitad es**, porque la misma frase puede ser
una tarde o una semana según en cuál caiga.

De paso: `documentacion_general.md` sección 10 no listaba ni el mapa ni esta
guía (decía "cuatro documentos"); `guia_de_uso.md` sección 6 y el README decían
"tres PDF". Corregidos, y los cuatro PDF regenerados. Se revisó **mirando** el
PDF con `pdftoppm`: la portada mostraba `**los dos**` literal (el subtítulo no
pasa por markdown) y las casillas `- [ ]` salían como texto; y la sección 0
derramaba tres renglones a una hoja vacía. Los tres corregidos.

---

## 5. Pendientes, por prioridad

> Ordenados por lo que **desbloquea**, no por antigüedad. Revisado 2026-08-10.

### A. Riesgo abierto — antes que cualquier cosa

| # | Pendiente | Por qué es lo primero |
| --- | --- | --- |
| A1 | **Rotar la API key de Jotform.** Requisito de entrega (`guia_de_entrega.md`, sección 0). | Sigue siendo la misma llave que estuvo en duro en el notebook, y **ya se usaron para bajar datos de 115 menores**. El notebook todavía la contiene. Cada día que pasa es exposición, y no depende de nadie más. |
| A2 | **`git init` + primer commit.** Requisito de entrega: sin historial no se ve qué cambió el otro desarrollador. | Hoy no hay historial: un borrado accidental se lleva todo. El `.gitignore` ya está correcto. Depende de A1: si se commitea con la llave dentro, queda en el historial para siempre. |

### B. La rebanada declarada: la proyección de pago

El objetivo que planteó el usuario es *automatizar la proyección de pago y los
comprobantes en Kydemy*. La cadena para llegar ahí, en orden:

| # | Pendiente | Estado de la dependencia |
| --- | --- | --- |
| B1 | ~~Llenar los precios.~~ | **Hecho** (sesión 9): el Excel de la escuela, ingestado a `programas`. La proyección da **$148,655/mes sobre 98 de 115**. |
| B1b | **Falta el precio de "Individual (1xsemana)"** — 17 alumnos, el 15%. | Es lo único que separa la proyección de cubrir al 100%. Se agrega al Excel y se vuelve a ingestar. |
| B1c | ~~Ligar alumno con descuento.~~ | **Hecho** (sesión 10): `alumnos_descuentos`, que se edita a mano, y `lisart descuentos`. Lo que falta ahora es **capturarlos**: el archivo está con los 115 alumnos y las celdas vacías. Es trabajo de la administración, no de código. |
| B2 | **Tabla `pagos`** (ledger append-only) **y `proyeccion_pagos`.** | Diseño listo, sin escribir. Un pago nunca se edita ni se borra: se corrige con otro movimiento. |
| B3 | **De dónde salen los pagos reales.** | El `.zip` de la conversación "Pagos Lisart" y/o Kydemy. Es lo que convierte la proyección en conciliación. |

### C. Kydemy — una fuente que resuelve tres pendientes a la vez

| # | Pendiente | Qué desbloquea |
| --- | --- | --- |
| C1 | **Conector de Kydemy** (como el de Jotform). | (a) Los **profesores**, que hoy no existen en ningún lado; (b) la **verificación** de pagos del método que ya usaba el usuario; (c) la generación de **comprobantes**. Falta saber cómo se exporta: API, Excel o CSV. |

### D. Datos que solo la escuela puede dar (baratos, y frenan cosas)

| # | Pendiente | Nota |
| --- | --- | --- |
| D1 | **Nombres reales de los espacios.** | Hoy dicen "Salón pequeño 1". Esos nombres van a salir en mensajes y horarios. |
| D2 | **Capacidad de cada espacio.** | Sin ella la calendarización no sabe dónde cabe un ensamble y dónde solo una clase individual. |
| D3 | **2 tutores con fecha de nacimiento de menor** (`PER-0037`, `PER-0219`). | No hay dato autodeclarado con qué corregirlos. |
| D4 | **2 alumnos sin contacto de emergencia.** | Detectado al construir la base. |
| D5 | **`parentesco` vacío en las 194 relaciones.** | El formulario no pregunta si es madre, padre o abuela. Hay que agregarlo en Jotform. |

### E. Lo que ya está en los datos y no se usa

| # | Pendiente | Nota |
| --- | --- | --- |
| E1 | ~~El horario de los alumnos sin usar.~~ | **Hecho** (sesión 8): 144 bloques en `disponibilidad`. |
| E3 | **Capturar las clases y sus profesores DE VERDAD.** | Las 4 clases y los 3 profesores que hay son de prueba (`lisart demo`). El circuito completo ya funciona con ellos —la reposición devuelve opciones—, así que lo único que falta es sustituirlos por los reales. Depende de C1. |
| E2 | **Agendar la ingesta semanal.** | El comando existe; no se agendó nada. Hay una línea de cron lista en el README. |

### F. Deuda técnica (puede esperar)

| # | Pendiente | Nota |
| --- | --- | --- |
| F5 | **La reposición devuelve pocas opciones.** | Correcto, no es bug: cruza al profesor con el alumno, y los horarios declarados por los alumnos son bloques de media hora. El interruptor "Solo horas en las que el alumno también puede" lo apaga. Si en la práctica estorba, conviene revisar si conviene un margen de tolerancia. |
| F6 | **La app de profesores no permite quitar una clase ni desasignar un profesor.** | Solo crea y asigna. Borrar necesita revisar referencias antes (`clases_alumnos`, `clases_profesores`, `disponibilidad`). |
| F1 | **La sección del grafo tarda ~1 min en pintar.** | Causa identificada: el saneador de Markdown de Streamlit con los ~600 elementos del SVG. Las dos alternativas fallan: `st.html` borra el SVG; `components.html` va en sandbox y mata el clic. Las secciones de tablas ya bajaron de 30 s a 1.6 s. |
| F2 | **La pantalla no crea ni borra registros**, solo edita. | Crear necesita generar `persona_id` y decidir roles; borrar necesita revisar referencias antes. |
| F3 | **Políticas/límites al chatbot.** | Del mapa original, sin tocar. |
| F4 | **Facebook para comunicación bidireccional.** | Del mapa original, sin tocar. |

### Tablas que faltan (según la rebanada que se elija)

- **Pagos:** `inscripciones`, `pagos` (ledger append-only), `proyeccion_pagos`
- **Mensajería:** `plantillas_mensajes`, `calendario_mensajes`, `envios`
- ~~**Calendarización:** `clases`, `disponibilidad`~~ — **hechas** (sesión 8),
  junto con `clases_profesores` y `clases_alumnos`

Al agregarlas heredan validación y documentación gratis: solo se edita
`tables.py` y se corre `lisart docs`.

---

## 6. Cómo retomar

```bash
uv pip install -e ".[dev]"   # si el entorno no existe
make check                   # ruff + pytest + docs --check + validate
lisart describe              # ver todas las tablas
lisart vault                 # regenerar el grafo; abrir vault/ en Obsidian
lisart ingest jotform        # bajar inscripciones nuevas (semanal)
lisart ui                    # abrir la pantalla (requiere: uv pip install -e ".[ui]")
```

Regla innegociable al trabajar aquí: **nunca `pd.read_csv` ni `df.to_csv` sobre
`data/`.** Todo pasa por `read_table` / `write_table` / `upsert`, que es donde
viven los tipos, la validación y la escritura atómica.

---

## 7. Mantenimiento de este archivo

Al cerrar cada sesión: actualizar la fecha del encabezado, mover a la sección 4
lo que se haya construido y verificado, y ajustar los pendientes de la 5.
Registrar **decisiones y su porqué**, no narrar la conversación. Si algo se
puede leer del código o del README, no repetirlo aquí.
