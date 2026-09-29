---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# disponibilidad

Cuando puede cada persona, semana tipo. Vale para profesores y para alumnos: el alumno declara su horario al inscribirse y el profesor el suyo al dar de alta. Cruzar las dos es lo que permite proponer una reposicion que le sirva a los dos.

**Archivo:** `data/master/disponibilidad.csv`
**Llave primaria:** `disponibilidad_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `disponibilidad_id` | string | si | PK; unica |
| `persona_id` | string | si | apunta a [[personas]] |
| `dia` | string | si | uno de: `L`, `M`, `Mi`, `J`, `V`, `S`, `D` |
| `hora_inicio` | time | si |  |
| `hora_fin` | time | si |  |
| `estado` | string | si | uno de: `disponible`, `bloqueado` |
| `motivo` | string | no |  |
| `vigente_desde` | date | no |  |
| `vigente_hasta` | date | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[personas]] — por `persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
