---
tipo: proyecto
estado: urge, sin empezar
tags: [proyecto]
---

# Punto de venta

Pedido aparte de los cuatro proyectos, marcado como **urgente**. Hoy se llena a
mano dia con dia, con todos los movimientos.

## El desafio real

Hoy solo se relaciona la **venta con el producto**. Falta:

1. Relacionar el platillo/servicio con el **cliente**.
2. Generar automaticamente **a quien le representa un pago** — el musico como
   proveedor.

Es decir: venta → servicio → cliente → proveedor, en una sola cadena.

## Que necesita

- Existentes: [[personas]] (el musico ya cabe con el rol `proveedor`)
- Por construir: `[[ventas]]`, `[[productos]]`, `[[proveedores_pagos]]`

Se conecta con el ideal a futuro: reporte automatico de ingresos y egresos y el
[[Documento de reembolso]].
