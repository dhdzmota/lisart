---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# personas

Una fila por ser humano relacionado con la escuela, sin importar su rol. Alumnos, tutores, profesores y empleados viven todos aqui.

**Archivo:** `data/master/personas.csv`
**Llave primaria:** `persona_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `persona_id` | string | si | PK; unica |
| `nombre` | string | si |  |
| `apellido_paterno` | string | no |  |
| `apellido_materno` | string | no |  |
| `nombre_normalizado` | string | si |  |
| `fecha_nacimiento` | date | no |  |
| `telefono` | string | no |  |
| `correo` | string | no |  |
| `domicilio` | string | no |  |
| `activo` | bool | si |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Le apuntan

- [[alumnos]] — por `persona_id` → `persona_id`
- [[clases_profesores]] — por `persona_id` → `persona_id`
- [[disponibilidad]] — por `persona_id` → `persona_id`
- [[identificadores_externos]] — por `persona_id` → `persona_id`
- [[personas_roles]] — por `persona_id` → `persona_id`
- [[relaciones]] — por `relacionado_persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
