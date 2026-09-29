---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# alumnos_instrumentos

Que instrumento estudia cada alumno. Es de muchos a muchos: hay quien lleva dos. Separarla de `alumnos` en vez de meter una columna con valores pegados por comas es lo que permite preguntar 'quien mas toca piano' sin partir texto.

**Archivo:** `data/master/alumnos_instrumentos.csv`
**Llave primaria:** `persona_id`, `instrumento_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `persona_id` | string | si | PK; apunta a [[alumnos]] |
| `instrumento_id` | string | si | PK; apunta a [[instrumentos]] |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[alumnos]] — por `persona_id` → `persona_id`
- [[instrumentos]] — por `instrumento_id` → `instrumento_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
