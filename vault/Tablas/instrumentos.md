---
tipo: tabla
capa: master
edicion: a mano
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# instrumentos

Instrumentos que se ensenan. Los nombres deben coincidir con los del formulario de inscripcion.

**Archivo:** `data/master/instrumentos.csv`
**Llave primaria:** `instrumento_id`
**La edita:** a mano

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `instrumento_id` | string | si | PK; unica |
| `nombre` | string | si |  |
| `familia` | string | no |  |
| `code` | string | no |  |
| `descripcion` | string | no |  |
| `activo` | bool | si |  |

## Le apuntan

- [[alumnos_instrumentos]] — por `instrumento_id` → `instrumento_id`
- [[clases]] — por `instrumento_id` → `instrumento_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
