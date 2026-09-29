---
tipo: tabla
capa: master
edicion: a mano
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# espacios

Todos los espacios fisicos de la escuela, no solo las aulas: tambien recepcion, cocina y bodega. Base del proyecto de calendarizacion. Se llama 'espacios' y no 'salones' porque la cocina no es un salon y la calendarizacion nunca debe ofrecerla para dar clase.

**Archivo:** `data/master/espacios.csv`
**Llave primaria:** `espacio_id`
**La edita:** a mano

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `espacio_id` | string | si | PK; unica |
| `nombre` | string | si |  |
| `tipo` | string | si | uno de: `aula`, `auditorio`, `bodega`, `recepcion`, `cocina`, `otro` |
| `piso` | string | si | uno de: `planta_baja`, `planta_alta` |
| `agendable` | bool | si |  |
| `capacidad` | int | no |  |
| `equipamiento` | string | no |  |
| `notas` | string | no |  |
| `activo` | bool | si |  |

## Le apuntan

- [[clases]] — por `espacio_id` → `espacio_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
