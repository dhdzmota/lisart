---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# clases_alumnos

Quien toma cada clase.

**Archivo:** `data/master/clases_alumnos.csv`
**Llave primaria:** `clase_id`, `persona_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `clase_id` | string | si | PK; apunta a [[clases]] |
| `persona_id` | string | si | PK; apunta a [[alumnos]] |
| `vigente_desde` | date | no |  |
| `vigente_hasta` | date | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[clases]] — por `clase_id` → `clase_id`
- [[alumnos]] — por `persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
