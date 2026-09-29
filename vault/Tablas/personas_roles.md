---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# personas_roles

Que papel juega cada persona. Una persona puede tener varios roles a la vez y puede cambiarlos con el tiempo.

**Archivo:** `data/master/personas_roles.csv`
**Llave primaria:** `persona_id`, `rol`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `persona_id` | string | si | PK; apunta a [[personas]] |
| `rol` | string | si | PK; uno de: `alumno`, `tutor`, `profesor`, `empleado`, `director`, `proveedor` |
| `vigente_desde` | date | no |  |
| `vigente_hasta` | date | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[personas]] — por `persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
