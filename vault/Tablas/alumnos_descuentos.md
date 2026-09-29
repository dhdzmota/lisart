---
tipo: tabla
capa: master
edicion: a mano
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# alumnos_descuentos

Que descuento tiene cada alumno. **Es la unica tabla del sistema que se llena a mano abriendo el archivo**, porque el dato no vive en ninguna fuente: lo decide la administracion caso por caso. El archivo lista a TODOS los alumnos inscritos, no solo a los que tienen descuento. Los que si tienen quedan arriba (los renglones con `descuento` vacio se van al final al ordenar), asi que se abre y lo primero que se ve es a quien se le esta descontando. Dar de alta un descuento es escribir su nombre en el renglon del alumno; quitarlo es borrar esa celda. `lisart descuentos` es el mantenimiento: agrega a los alumnos nuevos, rellena nombre, clave y porcentaje, y avisa de lo que no cuadra. Correrlo despues de editar.

**Archivo:** `data/master/alumnos_descuentos.csv`
**Llave primaria:** `alumno_descuento_id`
**La edita:** a mano

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `alumno_descuento_id` | string | no | PK; unica |
| `persona_id` | string | no | apunta a [[alumnos]] |
| `alumno` | string | no |  |
| `descuento` | string | no |  |
| `descuento_id` | string | no | apunta a [[descuentos]] |
| `porcentaje` | float | no |  |
| `notas` | string | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[alumnos]] — por `persona_id` → `persona_id`
- [[descuentos]] — por `descuento_id` → `descuento_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
