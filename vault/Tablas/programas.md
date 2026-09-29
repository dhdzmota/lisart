---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# programas

Los programas de aprendizaje y su precio mensual. Sale del Excel `data/catalogos_lisart.xlsx` que mantiene la escuela; se ingesta con `lisart ingest catalogos`, no se edita aqui.

**Archivo:** `data/master/programas.csv`
**Llave primaria:** `programa_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `programa_id` | string | si | PK; unica |
| `modalidad` | string | no |  |
| `nombre` | string | si |  |
| `categoria` | string | no |  |
| `caracteristica` | string | no |  |
| `arquetipo` | string | no |  |
| `descripcion` | string | no |  |
| `precio` | float | si |  |
| `activo` | bool | si |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

---

Volver a [[Lisart]] · [[Modelo de datos]]
