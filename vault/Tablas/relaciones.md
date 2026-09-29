---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# relaciones

Vinculos entre personas. Cubre el tutor legal, el contacto de emergencia, quien puede recoger al alumno y quien paga por el (el caso de 'Sofi paga por mi', que de otro modo rompe la conciliacion de pagos).

**Archivo:** `data/master/relaciones.csv`
**Llave primaria:** `relacion_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `relacion_id` | string | si | PK; unica |
| `alumno_persona_id` | string | si | apunta a [[alumnos]] |
| `relacionado_persona_id` | string | si | apunta a [[personas]] |
| `tipo` | string | si | uno de: `tutor`, `emergencia`, `autorizado_recoger`, `paga_por`, `hermano`, `profesor` |
| `parentesco` | string | no |  |
| `vigente` | bool | si |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[alumnos]] — por `alumno_persona_id` → `persona_id`
- [[personas]] — por `relacionado_persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
