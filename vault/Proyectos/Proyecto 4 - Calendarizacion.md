---
tipo: proyecto
estado: segunda etapa
tags: [proyecto]
---

# Proyecto 4 — Calendarizacion

Cotejar la agenda de **espacios x musicos x horarios oficiales de alumnos**.

Salida esperada: "tienes disponibles estas aulas con estos musicos, y todo lo
demas esta ocupado".

## Que necesita

- Existentes: [[espacios]] (ya con los 10 reales), [[personas]],
  [[personas_roles]] (rol `profesor`), [[instrumentos]]
- Por construir: `[[clases]]`, `[[disponibilidad]]`

## Lo que ya se resolvio

[[espacios]] distingue con la columna `agendable` un aula de la cocina: de los
10 espacios, **7 se pueden agendar**. Sin esa columna, la calendarizacion
acabaria ofreciendo la cocina para dar clase.

## Lo que falta antes de poder empezar

- Los **nombres reales** de los espacios (hoy dicen "Salon pequeño 1").
- La **capacidad** de cada uno: sin eso no se sabe donde cabe un ensamble y
  donde solo una clase individual.
