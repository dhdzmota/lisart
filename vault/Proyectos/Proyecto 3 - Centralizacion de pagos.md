---
tipo: proyecto
estado: es el candidato a arrancar
tags: [proyecto]
---

# Proyecto 3 — Centralizacion de pagos

Que todo pago quede registrado y referenciado solo, por cualquier medio de pago.

> [!important] La regla dura
> **No se acepta pago de quien no este en el sistema.** Eso obliga a que dar de
> alta a una persona sea lo primero, no un tramite posterior.

## Que necesita

- Existentes: [[personas]], [[alumnos]], [[relaciones]] (el `paga_por`),
  [[conceptos]], [[identificadores_externos]]
- Por construir: `[[inscripciones]]`, `[[pagos]]`, `[[proyeccion_pagos]]`

`pagos` tiene que ser un **ledger append-only**: un pago nunca se edita ni se
borra, se corrige con otro movimiento. Es la unica forma de que el historial
cuadre con el banco.

## Salidas esperadas

Cuantos pagos entraron, cuanta lana entro, cuanto falta.
Documentos: [[Proyeccion de pago]], [[Comprobante de pago]].

## Por que es el candidato natural

Es el objetivo declarado del usuario, y obliga a que el modelo de identidad sea
real —lo que beneficia a los otros tres proyectos.
