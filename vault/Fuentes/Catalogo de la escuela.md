---
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
  completa, en la misma columna. Se guarda tal cual; aplicarlo asi cobraria mal.
- **Jarana** la eligieron alumnos y no esta en `oferta_clases`.
- **Bajo Electrico** y **La Musica es un Juego** estan en el catalogo y nadie los
  eligio.
