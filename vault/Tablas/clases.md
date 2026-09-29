---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# clases

Una clase en la semana tipo: que dia, a que hora, en que espacio. Quien la da y quien la toma van en tablas aparte porque una clase puede tener varios profesores y varios alumnos.

**Archivo:** `data/master/clases.csv`
**Llave primaria:** `clase_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `clase_id` | string | si | PK; unica |
| `nombre` | string | no |  |
| `instrumento_id` | string | no | apunta a [[instrumentos]] |
| `espacio_id` | string | no | apunta a [[espacios]] |
| `dia` | string | si | uno de: `L`, `M`, `Mi`, `J`, `V`, `S`, `D` |
| `hora_inicio` | time | si |  |
| `hora_fin` | time | si |  |
| `cupo` | int | no |  |
| `activa` | bool | si |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[instrumentos]] — por `instrumento_id` → `instrumento_id`
- [[espacios]] — por `espacio_id` → `espacio_id`

## Le apuntan

- [[clases_alumnos]] — por `clase_id` → `clase_id`
- [[clases_profesores]] — por `clase_id` → `clase_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
