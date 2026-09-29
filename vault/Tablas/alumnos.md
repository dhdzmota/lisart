---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# alumnos

Datos que solo tienen sentido para un alumno. Es una extension de `personas`: la llave es la misma persona_id, no una nueva.

**Archivo:** `data/master/alumnos.csv`
**Llave primaria:** `persona_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `persona_id` | string | si | PK; unica; apunta a [[personas]] |
| `estatus` | string | si | uno de: `prospecto`, `inscrito`, `activo`, `baja`, `egresado` |
| `fecha_alta` | date | no |  |
| `fecha_baja` | date | no |  |
| `requiere_tutor` | bool | si |  |
| `programa` | string | no |  |
| `notas` | string | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[personas]] — por `persona_id` → `persona_id`

## Le apuntan

- [[alumnos_descuentos]] — por `persona_id` → `persona_id`
- [[alumnos_instrumentos]] — por `persona_id` → `persona_id`
- [[clases_alumnos]] — por `persona_id` → `persona_id`
- [[relaciones]] — por `alumno_persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
