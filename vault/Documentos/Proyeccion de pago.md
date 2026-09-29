---
tipo: documento
tags: [documento]
---

# Proyeccion de pago

Cuanto deberia entrar al mes y de quien. **Ya se calcula solo**:

```bash
lisart proyeccion
```

Sale de cruzar [[alumnos]] con [[programas]], que trae la cuota mensual. El
reporte se escribe en `data/exports/` como tres CSV: detalle por alumno, reparto
por programa, y **los que no se pudieron costear**.

## De donde salen los precios

Del Excel `data/catalogos_lisart.xlsx` que mantiene la escuela, ingestado con
`lisart ingest catalogos`. Ver [[Catalogo de la escuela]].

## Lo que el numero todavia no incluye

- **Un programa sin precio deja fuera a su alumno**, pero no lo esconde: sale
  listado aparte y el total dice sobre cuantos se calculo.
- **Es una proyeccion BRUTA**: no aplica [[descuentos]], porque no hay tabla que
  diga que alumno tiene cual.
- El caso "Sofi paga por mi" no afecta al monto —se debe lo mismo— pero si a
  quien se le cobra. Ver [[relaciones]] y su tipo `paga_por`.

## Lo que falta para la conciliacion

Comparar esto contra lo que de verdad entro necesita la tabla `[[pagos]]`, que
no existe, y una fuente de pagos reales: [[WhatsApp]] o [[Kydemy]]. Es el
[[Proyecto 3 - Centralizacion de pagos]].
