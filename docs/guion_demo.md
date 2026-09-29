# Guion de demo

> Documento **de trabajo**, no documentación del sistema. Es para tener abierto
> en una segunda pantalla mientras presentas. Se puede tirar o rehacer para la
> siguiente demo. Preparado para el **17 de agosto de 2026**.

Duración estimada: **20–25 minutos** con preguntas.

---

## Antes de empezar

Cinco minutos, y **no lo saltes**. Corre esto una hora antes, no enfrente de la
gente:

```bash
cd /mnt/c/Users/52333/Documents/projects/lisart2.0
source .venv/bin/activate

make check                      # que nada esté roto (~2 min)
lisart proyeccion --excel       # regenera el Excel del mes
```

- [ ] `make check` terminó sin errores
- [ ] Existe `data/exports/proyeccion_2026_08.xlsx`
- [ ] **La pantalla ya está abierta** (`lisart ui`) y le diste clic a **Grafo**
      una vez, para que quede cargado
- [ ] Tienes abiertos, en pestañas del navegador o del explorador:
      el Excel, `docs/guia_de_uso.pdf`, y el CSV de los que no tienen precio
- [ ] Ensayaste el paso 4 (el de guardar desde Excel)

Para encontrar el CSV del día:

```bash
ls -t data/exports/ | head -5
```

---

## 1. La base de datos existe, y son ustedes

```bash
lisart validate
```

> **17 tablas, todo en orden.**

En la pantalla, sección **Personas**: avanza con las flechas ◀ ▶.

> 243 personas, 115 alumnos. Nombres reales, salidos del formulario de
> inscripción. Nadie capturó esto a mano.

Pasa a **Relaciones**, que no dice `PER-0042 → PER-0117` sino
"Ana Torres Ruiz — tutor → Luis Torres Mena".

> El sistema sabe quién es tutor de quién, quién puede recoger a un menor y
> **quién paga por quién** — el caso de "Sofi paga por mí", que es justo lo que
> rompe cualquier cruce de pagos hecho a mano.

Pasa a **Roles**, que es un directorio:

> Se elige un rol y sale la lista completa. **54 tutores** con su teléfono y su
> correo, ordenable por cualquier columna y lista para copiar a Excel.

Cambia entre `alumno · 115` y `tutor · 54` — es instantáneo. Y con el botón del
final abres la ficha de esa persona.

> Y al revés: en la ficha de cualquiera se marca qué es —puede ser varias cosas
> a la vez, como la mamá que además toma clases—. Quitar un rol **no lo borra**:
> lo cierra con fecha, para que dentro de un año se pueda saber quién daba clase
> este semestre.

Números que puedes soltar si preguntan:

| Dato | Cifra |
| --- | --- |
| Personas | 243 |
| Alumnos | 115 (59 menores, 56 mayores) |
| Familias con hermanos | 10 |
| Menores con tutor registrado | los 59 |

---

## 2. El número — este es el momento fuerte

```bash
lisart proyeccion
```

> **$148,655 al mes**, y el desglose de dónde sale, programa por programa.

Ahora abre `data/exports/proyeccion_2026_08.xlsx`.

> Y esto es **su propio formato**, el que ya usan. Las mismas 38 columnas, los
> totales arriba, las columnas de cobranza donde siempre. No tienen que
> aprender nada nuevo: el archivo se abre igual y se filtra igual.

---

## 3. Y dice lo que todavía no sabe

Esto genera más confianza que el número, y de paso les pide algo concreto.

> De 115 alumnos calcula 98. Los otros **17 llevan "Individual (1xsemana)", que
> no tiene precio en su Excel**. No inventé una cifra: salen listados aparte, y
> el total dice en voz alta sobre cuántos se calculó.

Abre el CSV `..._sin_precio.csv` y enseña los 17 nombres.

> En cuanto le pongan precio, esto cubre el 100%.

---

## 4. Los descuentos — lo nuevo de esta semana

```bash
lisart descuentos --revisar
```

> Un archivo con los 115 alumnos inscritos. Para dar un descuento **se escribe
> su nombre en una celda**; para quitarlo, se borra. Los que tienen quedan
> hasta arriba, así que se abre y lo primero que se ve es a quién se le está
> descontando.

Abre `data/master/alumnos_descuentos.csv`, escribe `Familiar` en la columna
`descuento` de alguien, y **guarda como CSV UTF-8**. Luego:

```bash
lisart descuentos
lisart proyeccion
```

> Y el total baja solo.

> **Ensáyalo hoy.** Es el único paso que depende de guardar desde Excel, y es
> donde una demo se atora. Si no te sientes seguro, solo enseña el archivo y
> explica cómo se llena: el resto se entiende igual.

Si preguntan por los porcentajes: van **en puntos** (5 es 5%, 100 es beca
completa), y manda lo que diga la celda, para poder pactar un caso particular.
Varios descuentos del mismo alumno se suman.

---

## 5. La agenda

```bash
fuser -k 8501/tcp          # cierra la pantalla anterior
lisart ui --profesores
```

Se entra **por la clase**, luego el profesor, y de ahí su semana dibujada. Las
horas rayadas son las que sus alumnos declararon como ocupadas.

> **Dilo en voz alta:** estos 3 profesores y 4 clases son **datos de prueba**.
> No hay ni un profesor real todavía porque ese dato vive en Kydemy. En cuanto
> lo tengamos, esto mismo funciona con los de verdad, sin cambiar nada.

---

## Cierre — el manual

Abre `docs/guia_de_uso.pdf`.

> Dieciséis páginas, con su logo, escrito para quien no es técnico: tiene una
> tabla de qué sección es para quién y un glosario. Y no lo escribí aparte —
> **se genera del mismo texto que la documentación del sistema**, así que no se
> puede desactualizar.

---

## Lo que pides al final

Tres cosas que solo ellos pueden dar, y que desbloquean todo lo demás:

1. **El precio de "Individual (1xsemana)"** — cierra el 15% que le falta a la
   proyección. Es agregar un renglón a su Excel.
2. **Cómo se exporta Kydemy** (¿API, Excel, CSV?) — trae los profesores, que hoy
   no existen en ningún lado, y los pagos reales para poder conciliar.
3. **Quién tiene descuento** — el archivo ya está listo para que lo llenen.

Si hay tiempo, la cuarta: **el parentesco en el formulario** (madre, padre,
abuela). Hoy no se pregunta, y por eso esa columna está vacía en las 194
relaciones.

---

## Tres trampas que te pueden arruinar la demo

| Trampa | Qué hacer |
| --- | --- |
| **Las dos pantallas usan el mismo puerto** (8501). No pueden estar abiertas a la vez. | `fuser -k 8501/tcp` antes de abrir la otra, o `lisart ui --profesores --puerto 8502` |
| **`pkill -f "streamlit run"` no la cierra**: el patrón aparece en su propia línea de comando y el comando se mata a sí mismo. | Siempre `fuser -k 8501/tcp` |
| **El Grafo tarda ~1 minuto en pintar**, y la primera pintada de la app también. | Ábrelos antes de la demo y déjalos cargados |

---

## Plan B

Todo lo que vas a enseñar **ya está en archivos**:

- `data/exports/proyeccion_2026_08.xlsx` — el Excel de la escuela
- `data/exports/proyeccion_*_detalle.csv` y `..._sin_precio.csv`
- `data/master/alumnos_descuentos.csv`
- `docs/guia_de_uso.pdf`

Si la terminal o la pantalla se traban, sigue con los archivos abiertos. La
historia se cuenta igual y nadie nota la diferencia.

---

## Lo que NO conviene enseñar

- **`make check`, las pruebas, `ruff`.** A la escuela no le dice nada y te mete
  en terreno técnico del que cuesta salir.
- **El vault de Obsidian y el grafo de tablas.** Son para ti, no para ellos.
  Salvo que pregunten "¿y cómo está hecho por dentro?".
- **Prometer fechas** de lo que depende de Kydemy. No sabemos todavía cómo se
  exporta.
