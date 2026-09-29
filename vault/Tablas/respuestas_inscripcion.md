---
tipo: tabla
capa: interim
edicion: codigo
tags: [tabla, interim]
---

> [!warning] Nota generada
> La escribe `lisart vault` desde `src/lisart/tables.py`. Si la editas a mano, se pierde en la siguiente corrida.

# respuestas_inscripcion

Una fila por envio del formulario de inscripcion de Jotform, ya aplanado a columnas. Vive en `interim` y no en `master` porque se puede reconstruir entero desde los JSON de `data/raw/jotform/`. Todavia NO es la verdad de la escuela: es materia prima para dar de alta personas y alumnos.

**Archivo:** `data/interim/respuestas_inscripcion.csv`
**Llave primaria:** `form__submission_id`
**La edita:** codigo

## Columnas

| Columna | Tipo | Oblig. | Reglas |
| --- | --- | --- | --- |
| `politicas_de_servicio__nombre_completo` | string | no |  |
| `politicas_de_servicio__firma` | string | no |  |
| `politicas_de_servicio__manifiesto` | string | no |  |
| `acepta_reglamento` | bool | no |  |
| `fechayhora_llenado` | datetime | no |  |
| `alumno__nombre_completo___nombre` | string | no |  |
| `alumno__nombre_completo___apellido_paterno` | string | no |  |
| `alumno__nombre_completo___apellido_materno` | string | no |  |
| `alumno__nombre_completo___txt` | string | no |  |
| `alumno__fecha_nacimiento` | date | no |  |
| `alumno__edad` | string | no |  |
| `alumno__domicilio___calle1` | string | no |  |
| `alumno__domicilio___calle2` | string | no |  |
| `alumno__domicilio___ciudad` | string | no |  |
| `alumno__domicilio___estado` | string | no |  |
| `alumno__domicilio___codigo_postal` | string | no |  |
| `alumno__domicilio___txt` | string | no |  |
| `alumno__telefono___area` | string | no |  |
| `alumno__telefono___telefono` | string | no |  |
| `alumno__telefono___txt` | string | no |  |
| `alumno__correo` | string | no |  |
| `tutor__nombre_completo___nombre` | string | no |  |
| `tutor__nombre_completo___apellido_paterno` | string | no |  |
| `tutor__nombre_completo___apellido_materno` | string | no |  |
| `tutor__nombre_completo___txt` | string | no |  |
| `tutor__fecha_nacimiento` | date | no |  |
| `tutor__domicilio___calle1` | string | no |  |
| `tutor__domicilio___calle2` | string | no |  |
| `tutor__domicilio___ciudad` | string | no |  |
| `tutor__domicilio___estado` | string | no |  |
| `tutor__domicilio___codigo_postal` | string | no |  |
| `tutor__domicilio___txt` | string | no |  |
| `tutor__telefono___area` | string | no |  |
| `tutor__telefono___telefono` | string | no |  |
| `tutor__telefono___txt` | string | no |  |
| `tutor__correo` | string | no |  |
| `documento_path` | string | no |  |
| `comprobante_domicilio` | string | no |  |
| `emergencia__nombre_completo___nombre` | string | no |  |
| `emergencia__nombre_completo___apellido_paterno` | string | no |  |
| `emergencia__nombre_completo___apellido_materno` | string | no |  |
| `emergencia__nombre_completo___txt` | string | no |  |
| `emergencia__fecha_nacimiento` | date | no |  |
| `emergencia__domicilio___calle1` | string | no |  |
| `emergencia__domicilio___calle2` | string | no |  |
| `emergencia__domicilio___ciudad` | string | no |  |
| `emergencia__domicilio___estado` | string | no |  |
| `emergencia__domicilio___codigo_postal` | string | no |  |
| `emergencia__domicilio___txt` | string | no |  |
| `emergencia__telefono___area` | string | no |  |
| `emergencia__telefono___telefono` | string | no |  |
| `emergencia__telefono___txt` | string | no |  |
| `emergencia__correo` | string | no |  |
| `recojer_adicional` | string | no |  |
| `recojer1__nombre_completo___nombre` | string | no |  |
| `recojer1__nombre_completo___apellido_paterno` | string | no |  |
| `recojer1__nombre_completo___apellido_materno` | string | no |  |
| `recojer1__nombre_completo___txt` | string | no |  |
| `recojer1__fecha_nacimiento` | date | no |  |
| `recojer1__domicilio___calle1` | string | no |  |
| `recojer1__domicilio___calle2` | string | no |  |
| `recojer1__domicilio___ciudad` | string | no |  |
| `recojer1__domicilio___estado` | string | no |  |
| `recojer1__domicilio___codigo_postal` | string | no |  |
| `recojer1__domicilio___txt` | string | no |  |
| `recojer1__telefono___area` | string | no |  |
| `recojer1__telefono___telefono` | string | no |  |
| `recojer1__telefono___txt` | string | no |  |
| `recojer1__correo` | string | no |  |
| `recojer1__id_oficial` | string | no |  |
| `recojer2__nombre_completo___nombre` | string | no |  |
| `recojer2__nombre_completo___apellido_paterno` | string | no |  |
| `recojer2__nombre_completo___apellido_materno` | string | no |  |
| `recojer2__nombre_completo___txt` | string | no |  |
| `recojer2__fecha_nacimiento` | date | no |  |
| `recojer2__domicilio___calle1` | string | no |  |
| `recojer2__domicilio___calle2` | string | no |  |
| `recojer2__domicilio___ciudad` | string | no |  |
| `recojer2__domicilio___estado` | string | no |  |
| `recojer2__domicilio___codigo_postal` | string | no |  |
| `recojer2__domicilio___txt` | string | no |  |
| `recojer2__telefono___area` | string | no |  |
| `recojer2__telefono___telefono` | string | no |  |
| `recojer2__telefono___txt` | string | no |  |
| `recojer2__correo` | string | no |  |
| `recojer2__id_oficial` | string | no |  |
| `instrumentos` | string | no |  |
| `pda` | string | no |  |
| `horario___L` | string | no |  |
| `horario___M` | string | no |  |
| `horario___Mi` | string | no |  |
| `horario___J` | string | no |  |
| `horario___V` | string | no |  |
| `horario___S` | string | no |  |
| `aviso_de_privacidad` | bool | no |  |
| `uso_imagen__autorizo_mayor` | bool | no |  |
| `uso_imagen__autorizo_menor` | bool | no |  |
| `uso_imagen__nombre_completo_alumno___nombre` | string | no |  |
| `uso_imagen__nombre_completo_alumno___apellido_paterno` | string | no |  |
| `uso_imagen__nombre_completo_alumno___apellido_materno` | string | no |  |
| `uso_imagen__nombre_completo_alumno___txt` | string | no |  |
| `uso_imagen__nombre_completo_tutor___nombre` | string | no |  |
| `uso_imagen__nombre_completo_tutor___apellido_paterno` | string | no |  |
| `uso_imagen__nombre_completo_tutor___apellido_materno` | string | no |  |
| `uso_imagen__nombre_completo_tutor___txt` | string | no |  |
| `uso_imagen__firma` | string | no |  |
| `uso_imagen__no_autorizo_mayor` | bool | no |  |
| `uso_imagen__no_autorizo_menor` | bool | no |  |
| `form__submission_id` | string | si | PK; unica |
| `form__id` | string | no |  |
| `form__ip` | string | no |  |
| `form__created_at` | datetime | no |  |
| `form__status` | string | no |  |
| `creado_en` | datetime | si |  |
| `actualizado_en` | datetime | si |  |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` |

---

Volver a [[Lisart]] · [[Modelo de datos]]
