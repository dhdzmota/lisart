---
tipo: fuente
tags: [fuente]
---

# Jotform

Formularios de inscripcion. Es por donde **entra** un alumno nuevo al sistema.

- Cae en: [[respuestas_inscripcion]] (capa interim)
- Despues alimentara: [[personas]], [[alumnos]], [[relaciones]]
- Se identifica en [[identificadores_externos]] con `sistema = jotform`
- Documento asociado: [[Formulario de inscripcion]]
- Codigo: `src/lisart/fuentes/jotform.py`

## Como se baja

```bash
lisart ingest jotform
```

Baja todos los envios, guarda la copia cruda en `data/raw/jotform/` y agrega a
la tabla **solo lo que no estaba**. Si no hay nada nuevo, no toca el archivo.
Se corre una vez por semana.

Las llaves (`JOTFORM_API_KEY`, `JOTFORM_FORM_ID`) van en `.env`, nunca en el
codigo.

> [!warning] El mapeo va por numero de orden
> Los campos se identifican por su posicion en el formulario. Si alguien
> reordena o inserta un campo en Jotform, los datos empiezan a caer en la
> columna equivocada **sin que nada truene**. `lisart ingest jotform` corre
> `revisar_mapeo()` en cada corrida y avisa. **Hacerle caso a esos avisos.**

> [!danger] Pendiente de seguridad
> La API key sigue siendo la que estuvo escrita en duro en el notebook
> `projects/data_mechanism/respuestas_inscripcion_forms.ipynb`. Ya vive en
> `.env`, pero **hay que rotarla en Jotform** antes del primer commit de git.

Trae datos de menores: domicilios, telefonos, firmas e identificaciones.
