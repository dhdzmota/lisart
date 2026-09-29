---
tipo: tabla
capa: master
edicion: codigo
tags: [tabla, master]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# identificadores_externos

Puente entre nuestra persona_id y como la llama cada sistema de afuera. Es la pieza que permite cruzar Kydemy, Jotform y WhatsApp sin adivinar por nombre cada vez.

**Archivo:** `data/master/identificadores_externos.csv`
**Llave primaria:** `sistema`, `id_externo`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `sistema` | string | si | PK; uno de: `kydemy`, `jotform`, `whatsapp`, `odoo`, `banco` |
| `id_externo` | string | si | PK |
| `persona_id` | string | si | apunta a [[personas]] |
| `notas` | string | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

## Apunta a

- [[personas]] — por `persona_id` → `persona_id`

---

Volver a [[Lisart]] · [[Modelo de datos]]
