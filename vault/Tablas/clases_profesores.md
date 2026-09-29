---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# clases_profesores

Quien da cada clase. Es de muchos a muchos a proposito: una clase puede tener mas de un profesor, y un profesor da varias clases.

**Archivo:** `data/master/clases_profesores.csv`
**Llave primaria:** `clase_id`, `persona_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `clase_id` | string | si | PK; apunta a [[clases]] |
| `persona_id` | string | si | PK; apunta a [[personas]] |
| `rol_en_clase` | string | no | uno de: `titular`, `apoyo`, `suplente` |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[clases]] — por `clase_id` → `clase_id`
- [[personas]] — por `persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
