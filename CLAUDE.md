# Lisart

Sistema administrativo de la escuela de música Lisart. La base de datos son
archivos CSV; el paquete `lisart` es la capa que les pone tipos, llaves,
integridad referencial y escritura atómica.

## Antes que nada

El estado del proyecto, lo ya construido, las decisiones tomadas y los
pendientes abiertos están en la bitácora de abajo. **Leerla antes de proponer
o hacer cualquier cosa**, y actualizarla al cerrar la sesión.

@.claude/estado-del-proyecto.md

## Comandos

```bash
lisart init                    # crea carpetas y CSV vacíos
lisart validate [tabla]        # revisa los datos contra el esquema (sale 1 si hay errores)
lisart describe [tabla]        # muestra el esquema
lisart docs                    # regenera docs/modelo_de_datos.md
make docs                      # regenera ESO y el vault, para que no se desfasen
lisart vault                   # regenera el vault de Obsidian
lisart ingest jotform          # baja inscripciones nuevas (semanal)
lisart ingest catalogos        # lee el Excel de programas, precios y descuentos
lisart ingest jotform --desde-raw   # rehace la tabla sin llamar a la API
lisart procesar inscripciones  # inscripciones -> personas, alumnos, relaciones
lisart ui                      # abre la pantalla principal
lisart ui --profesores         # abre la agenda de profesores (app aparte)
lisart backup [tabla]          # respalda la capa master
lisart demo [--limpiar]        # datos de prueba, marcados con fuente='demo'
lisart proyeccion              # proyección de pago mensual -> data/exports/
lisart descuentos [--revisar]  # mantiene el archivo de quién tiene qué descuento
lisart guia [doc] [--check]    # regenera los PDF de docs/ desde su markdown
```

## Reglas de trabajo en este repo

- **Nunca `pd.read_csv` ni `df.to_csv` sobre `data/`.** Todo pasa por
  `read_table` / `write_table` / `upsert` de `lisart.io`. Ahí viven los tipos,
  la validación y la garantía de no dejar un archivo a medias.
- **Las tablas se definen solo en `src/lisart/tables.py`.** Después de tocarlo:
  `make docs` (regenera `docs/modelo_de_datos.md` **y** el vault) y
  `lisart validate`.
- `docs/modelo_de_datos.md` y `vault/Tablas/` son **generados**. No editarlos a
  mano. El resto del vault (`Fuentes/`, `Documentos/`, `Proyectos/`) es humano y
  no se pisa.
- **Los catálogos no se llenan desde el código.** `espacios`, `instrumentos` y
  `conceptos` los mantiene una persona. Si un dato de fuera no está en el
  catálogo, se **avisa**; darlo de alta solo llenaría el catálogo de variantes
  mal escritas sin que nadie lo note. Lo mismo vale para `alumnos_descuentos`:
  un descuento mal escrito se reporta y **no se escribe nada**.
- **`alumnos_descuentos` se edita a mano, en Excel.** Es la única. Por eso sus
  dos llaves aceptan quedar vacías: el renglón nuevo se completa corriendo
  `lisart descuentos`, no tecleando un ID. El porcentaje va **en puntos**
  (5 = 5%, 100 = beca completa) y manda sobre el catálogo.
- **Nada se sobrescribe sin respaldo.** La pantalla guarda con
  `backup.guardar_con_respaldo`, que valida, copia el estado anterior a
  `data/backups/` y luego escribe.
- Antes de dar por bueno un cambio: `make check`
  (ruff + pytest sin las de pantalla + `lisart docs --check` + `lisart validate`).
  Las pruebas de pantalla llevan marcador `ui` porque tardan ~5 min:
  `make test-todo` las incluye.
- **Nunca evaluar una celda de pandas como booleano directo.** `if fila["x"]`
  con una celda vacía lanza "boolean value of NA is ambiguous". Usar
  `ui.app.tiene_valor()` o `pd.isna()`.
- Las convenciones de datos y su porqué están en `docs/convenciones_datos.md`.
- **La guía de uso se mantiene al día, y con ella su PDF.** Cualquier cambio que
  altere *cómo se usa* el sistema —un comando nuevo, un flujo distinto, una
  tabla que ahora se edita a mano, un aviso nuevo que hay que atender— no está
  terminado hasta que está en `docs/guia_de_uso.md` **y** se corrió
  `lisart guia` para regenerar `docs/guia_de_uso.pdf`. Si además cambia *qué es*
  el sistema —una tabla nueva, un proceso nuevo, un pendiente que se cerró—, lo
  mismo aplica a `docs/documentacion_general.md`, que es el documento que lee
  quien no va a abrir el código; y si cambia la **estructura del código** —un
  módulo nuevo, uno que cambia de nivel, lógica de datos que se sale de `ui/`—,
  a `docs/mapa_del_codigo.md`, que es el documento de entrega; y si cambia el
  **proceso de delegación** —quién se queda con qué, qué es "terminado"—, a
  `docs/guia_de_entrega.md`. El PDF es la copia que lee la escuela; el `.md`
  es el original y lo único que se edita. `make check` corre
  `lisart guia --check` y truena si alguno se desfasó.
  Los cuatro están escritos **con acentos**, y todos menos el mapa para gente no
  técnica: son los únicos documentos del repo con ese público. Los cuatro
  cierran con un glosario que traduce el vocabulario.

## Trampas de este entorno (comprobadas, no supuestas)

- **Ninguna librería de gráficas de Streamlit dibuja nada aquí**: plotly, altair
  y hasta los gráficos nativos salen vacíos, sin error. Comprobado con una app
  mínima. Por eso el grafo y el pentagrama son **SVG en línea**.
- `st.html` **sanea el SVG hasta borrarlo**. `components.html` lo pinta rápido
  pero su iframe va en sandbox y **bloquea la navegación de la página padre**,
  o sea mata el clic en los nodos. La única vía que conserva el clic es
  `st.markdown(..., unsafe_allow_html=True)`.
- La primera pintada de la app tarda; correr `AppTest` o esperar a un selector
  concreto es más fiable que dormir unos segundos.
- **Antes de concluir que un elemento "no se pinta", mirar
  `[data-testid='stStatusWidget']`.** Si dice "Stop", el script sigue corriendo
  y lo que falta todavía no se ha producido. Una sección puede tardar ~30 s en
  aparecer completa; capturar a los 6 s hace creer que Streamlit se comió el
  bloque. Se perdieron horas por esto.
- `pkill -f "streamlit run"` **se mata a sí mismo** porque el patrón aparece en
  su propia línea de comando. Usar `fuser -k 8501/tcp`.

## Privacidad

Los datos incluyen nombres, domicilios, teléfonos, firmas e identificaciones de
**menores de edad**. `data/**` está en `.gitignore` salvo los catálogos, que no
llevan datos personales. Las llaves de API van en `.env`. Antes de compartir
cualquier archivo de `exports/`, revisar qué columnas lleva.

## Idioma

Vocabulario de dominio en español (alumno, tutor, salón, colegiatura),
infraestructura en inglés. Comentarios, docstrings y documentación en español.
