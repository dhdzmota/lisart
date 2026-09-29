---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# descuentos

Descuentos que la escuela reconoce. Sale del mismo Excel. **Todavia no se sabe quien tiene cual**, asi que no se aplican a la proyeccion: falta la tabla que ligue alumno con descuento.

**Archivo:** `data/master/descuentos.csv`
**Llave primaria:** `descuento_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `descuento_id` | string | si | PK; unica |
| `nombre` | string | si |  |
| `descripcion` | string | no |  |
| `valor_porcentual` | float | si |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Le apuntan

- [[alumnos_descuentos]] — por `descuento_id` → `descuento_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
