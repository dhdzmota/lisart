# Convenciones de datos

Las reglas de la casa. Son pocas a proposito: una convencion que nadie recuerda
no sirve. Casi todas estan forzadas por el codigo, no por disciplina.

---

## 1. Las cuatro capas

```
raw  ->  interim  ->  master  ->  exports
```

| Capa | Que es | Se puede borrar? |
| --- | --- | --- |
| `raw` | Lo que llego de afuera, **tal cual llego**: el JSON de Jotform, el Excel de Kydemy, el zip de WhatsApp. | No sin volver a descargarlo |
| `interim` | Pasos intermedios y cache. | Si, se reconstruye |
| `master` | La verdad de la escuela. Las tablas del modelo. | **No. Esto es lo que se respalda.** |
| `exports` | Reportes y Excel para gente. | Si, se regenera |

`raw` es **inmutable**. Si un dato llego mal, no se corrige ahi: se corrige en
el paso que lo transforma. Si no, se pierde para siempre la posibilidad de
volver a procesar desde cero y llegar al mismo lugar.

El flujo nunca va hacia atras. Nada en `master` se calcula leyendo `exports`.

---

## 2. Una tabla se define en un solo lugar

`src/lisart/tables.py`. De ahi salen la lectura, la escritura, la validacion y
la documentacion.

Para agregar una columna:

1. Se agrega el `Column(...)` en `tables.py`.
2. `lisart docs` para regenerar la documentacion.
3. `lisart validate` para ver que el dato existente sigue cumpliendo.

Si una columna nueva es obligatoria y ya hay filas guardadas, la validacion va
a reclamar. Es el comportamiento correcto: obliga a decidir que hacer con lo
viejo en vez de dejarlo a medias.

---

## 3. Nombres

- Todo en `snake_case` y sin acentos **en los nombres de columna**. Los
  acentos van en los datos, no en los encabezados.
- Los identificadores terminan en `_id`.
- Las fechas empiezan con `fecha_`; las marcas de tiempo terminan en `_en`
  (`creado_en`, `actualizado_en`).
- Los si/no se leen como afirmacion: `activo`, `vigente`, `requiere_tutor`.
  Nunca en negativo (`no_activo` obliga a pensar al reves cada vez).
- Vocabulario en español, el de la escuela: `alumno`, `tutor`, `salon`,
  `colegiatura`. Traducirlo solo agrega un diccionario mental de mas.

---

## 4. Tipos y formatos

| Tipo | Como se ve en el CSV | Ejemplo |
| --- | --- | --- |
| `date` | `AAAA-MM-DD` | `2026-08-08` |
| `datetime` | `AAAA-MM-DD HH:MM:SS` | `2026-08-08 15:41:05` |
| `bool` | `true` / `false` | `true` |
| `int` / `float` | punto decimal, sin separador de miles | `1250.00` |
| `string` | texto, se recortan los espacios de sobra | `María José` |

Al **leer**, tambien se aceptan los si/no que produce Excel en español
(`VERDADERO`, `FALSO`, `si`, `no`), porque hay tablas que se editan a mano. Al
**escribir** siempre sale `true` / `false`.

Dos detalles que evitan errores clasicos de CSV:

- Los telefonos y los IDs son **texto**, nunca numero. Un telefono leido como
  numero pierde el `+` y los ceros de adelante.
- Solo la celda vacia cuenta como nulo. El texto `NA` se conserva como texto
  (puede ser iniciales de alguien).

---

## 5. Quien edita cada tabla

| Tipo | Quien escribe | Codificacion |
| --- | --- | --- |
| `managed` | Solo el codigo | UTF-8 |
| `hand_edited` | Una persona, en Excel o LibreOffice | UTF-8 con BOM |

El BOM es lo que hace que Excel en español abra los acentos bien en vez de
mostrar `MarÃ­a`. Al guardar desde Excel hay que elegir **CSV UTF-8**.

Despues de editar un catalogo a mano, **siempre**:

```bash
lisart validate espacios
```

---

## 6. Identidad: una persona es una persona

Un profesor que ademas es tutor de su hija es **una** fila en `personas` con
dos roles. No dos personas.

Duplicar humanos es la causa raiz de casi todos los problemas que siguen:
pagos que no cuadran, mensajes enviados dos veces, un alumno que aparece como
inscrito y como prospecto al mismo tiempo.

- El nombre se guarda **tal como lo escribio la familia**. La version
  comparable (sin acentos, en minusculas) va aparte en `nombre_normalizado`, y
  se calcula con `ids.normalizar_nombre`.
- Los telefonos se guardan en E.164 (`+525512345678`), que es lo que entiende
  WhatsApp. `ids.normalizar_telefono` hace la conversion.
- Para saber como se llama esa misma persona en Kydemy o en Jotform se usa
  `identificadores_externos`, no el nombre. Cruzar por nombre es el ultimo
  recurso, no el primero.

---

## 7. Rastro

Toda tabla que escribe el codigo lleva `creado_en`, `actualizado_en` y
`fuente`. Cuando un dato se vea raro —y se va a ver raro— eso es lo que
permite contestar de donde salio sin adivinar.

---

## 8. Escribir es una operacion completa

`write_table` valida antes de escribir y escribe de forma atomica: primero a un
archivo temporal, luego lo mueve encima. Si algo falla a medio camino, el
archivo anterior queda intacto.

Por eso **nunca** se abre un CSV de `data/` con `pd.read_csv` o `df.to_csv`
directo. Se pierden los tipos, la validacion y la garantia de no dejar el
archivo a la mitad.

---

## 9. Respaldo

`data/master/` no esta en git (son datos personales). Necesita respaldo aparte:
copiar la carpeta a un disco o a la nube de la escuela, con fecha en el nombre.

Un respaldo que nunca se restauro no es un respaldo. Conviene probarlo una vez:
copiar `master/` a otro lado, apuntar `LISART_DATA_DIR` ahi y correr
`lisart validate`.

---

## 10. Cuando dejar los CSV

Los CSV aguantan bien mientras haya **un solo escritor a la vez**. Las señales
de que ya toca una base de datos de verdad (SQLite primero, que tambien es un
solo archivo y sigue siendo gratis):

- Dos personas o dos procesos escribiendo al mismo tiempo.
- Una tabla que pasa de ~100 mil filas y hace lento todo.
- Necesidad de historial de cambios fila por fila.

Mientras eso no pase, migrar solo agrega trabajo. Y como todo el acceso pasa
por `io.py`, la migracion se hace ahi y el resto del codigo ni se entera.
