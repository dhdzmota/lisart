---
tipo: proyecto
estado: no iniciado
tags: [proyecto]
---

# Proyecto 1 — Mensajes automaticos

Recordatorios de pago e inscripcion a alumnos y profesores. Maximo ~15 mensajes
distintos; algunos son condicionales. Hoy se copia y pega un comando para enviar.

## Que necesita

- Existentes: [[personas]], [[alumnos]], [[personas_roles]]
- Por construir: `[[plantillas_mensajes]]`, `[[calendario_mensajes]]`, `[[envios]]`
- Canal: [[WhatsApp]] (hoy solo de salida)

## Estado

El mensaje ya se puede hiperpersonalizar (nombre, monto que debe) y calendarizar.
Ya hay un chatbot funcionando, pero **le faltan politicas** para que no conteste
cualquier cosa.

Pendiente: revisar Facebook para comunicacion de dos vias.

`envios` debe ser un registro append-only: sin el, no hay forma de saber si a
alguien ya se le mando el recordatorio y se le manda dos veces.
