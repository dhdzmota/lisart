---
tipo: fuente
tags: [fuente]
---

# WhatsApp

Dos usos distintos que conviene no confundir.

## Como fuente de datos

La conversacion **"Pagos Lisart"** dice quien ya pago y con que comprobante.
Es el punto de partida para armar la [[Proyeccion de pago]].

- Se identifica en [[identificadores_externos]] con `sistema = whatsapp`
- La llave natural es el telefono en E.164 (`+525512345678`)

## Como canal de salida

Hoy es **monodireccional**: se envia, no se recibe. El mensaje ya se puede
hiperpersonalizar y calendarizar. Para leer respuestas haria falta pedir la
API key de WhatsApp.

Alimenta al [[Proyecto 1 - Mensajes automaticos]].
