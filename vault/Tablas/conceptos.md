---
tipo: tabla
capa: master
edicion: a mano
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# conceptos

Que se cobra y cuanto. Los montos se versionan por vigencia en vez de sobrescribirse, para que un pago viejo siga cuadrando con el precio que existia cuando se hizo.

**Archivo:** `data/master/conceptos.csv`
**Llave primaria:** `concepto_id`
**La edita:** a mano

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `concepto_id` | string | si | PK; unica |
| `nombre` | string | si |  |
| `tipo` | string | si | uno de: `inscripcion`, `colegiatura`, `material`, `examen`, `evento`, `otro` |
| `monto` | float | si |  |
| `periodicidad` | string | si | uno de: `unica`, `mensual`, `anual` |
| `vigente_desde` | date | si |  |
| `vigente_hasta` | date | no |  |
| `activo` | bool | si |  |

---

Volver a [[Lisart]] · [[Modelo de datos]]
