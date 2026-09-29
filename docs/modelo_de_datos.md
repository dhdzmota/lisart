# Modelo de datos

> Archivo generado por `lisart docs`. **No editarlo a mano**: se sobrescribe.
> La fuente de verdad es `src/lisart/tables.py`.

## Tablas

| Tabla | Capa | Quien la edita | Descripcion |
| --- | --- | --- | --- |
| [`conceptos`](#conceptos) | master | a mano | Que se cobra y cuanto. Los montos se versionan por vigencia en vez de sobrescribirse, para que un pago viejo siga cuadrando con el precio que existia cuando se hizo. |
| [`descuentos`](#descuentos) | master | codigo | Descuentos que la escuela reconoce. Sale del mismo Excel. **Todavia no se sabe quien tiene cual**, asi que no se aplican a la proyeccion: falta la tabla que ligue alumno con descuento. |
| [`espacios`](#espacios) | master | a mano | Todos los espacios fisicos de la escuela, no solo las aulas: tambien recepcion, cocina y bodega. Base del proyecto de calendarizacion. Se llama 'espacios' y no 'salones' porque la cocina no es un salon y la calendarizacion nunca debe ofrecerla para dar clase. |
| [`instrumentos`](#instrumentos) | master | a mano | Instrumentos que se ensenan. Los nombres deben coincidir con los del formulario de inscripcion. |
| [`personas`](#personas) | master | codigo | Una fila por ser humano relacionado con la escuela, sin importar su rol. Alumnos, tutores, profesores y empleados viven todos aqui. |
| [`programas`](#programas) | master | codigo | Los programas de aprendizaje y su precio mensual. Sale del Excel `data/catalogos_lisart.xlsx` que mantiene la escuela; se ingesta con `lisart ingest catalogos`, no se edita aqui. |
| [`respuestas_inscripcion`](#respuestas_inscripcion) | interim | codigo | Una fila por envio del formulario de inscripcion de Jotform, ya aplanado a columnas. Vive en `interim` y no en `master` porque se puede reconstruir entero desde los JSON de `data/raw/jotform/`. Todavia NO es la verdad de la escuela: es materia prima para dar de alta personas y alumnos. |
| [`alumnos`](#alumnos) | master | codigo | Datos que solo tienen sentido para un alumno. Es una extension de `personas`: la llave es la misma persona_id, no una nueva. |
| [`clases`](#clases) | master | codigo | Una clase en la semana tipo: que dia, a que hora, en que espacio. Quien la da y quien la toma van en tablas aparte porque una clase puede tener varios profesores y varios alumnos. |
| [`disponibilidad`](#disponibilidad) | master | codigo | Cuando puede cada persona, semana tipo. Vale para profesores y para alumnos: el alumno declara su horario al inscribirse y el profesor el suyo al dar de alta. Cruzar las dos es lo que permite proponer una reposicion que le sirva a los dos. |
| [`identificadores_externos`](#identificadores_externos) | master | codigo | Puente entre nuestra persona_id y como la llama cada sistema de afuera. Es la pieza que permite cruzar Kydemy, Jotform y WhatsApp sin adivinar por nombre cada vez. |
| [`personas_roles`](#personas_roles) | master | codigo | Que papel juega cada persona. Una persona puede tener varios roles a la vez y puede cambiarlos con el tiempo. |
| [`alumnos_descuentos`](#alumnos_descuentos) | master | a mano | Que descuento tiene cada alumno. **Es la unica tabla del sistema que se llena a mano abriendo el archivo**, porque el dato no vive en ninguna fuente: lo decide la administracion caso por caso. El archivo lista a TODOS los alumnos inscritos, no solo a los que tienen descuento. Los que si tienen quedan arriba (los renglones con `descuento` vacio se van al final al ordenar), asi que se abre y lo primero que se ve es a quien se le esta descontando. Dar de alta un descuento es escribir su nombre en el renglon del alumno; quitarlo es borrar esa celda. `lisart descuentos` es el mantenimiento: agrega a los alumnos nuevos, rellena nombre, clave y porcentaje, y avisa de lo que no cuadra. Correrlo despues de editar. |
| [`alumnos_instrumentos`](#alumnos_instrumentos) | master | codigo | Que instrumento estudia cada alumno. Es de muchos a muchos: hay quien lleva dos. Separarla de `alumnos` en vez de meter una columna con valores pegados por comas es lo que permite preguntar 'quien mas toca piano' sin partir texto. |
| [`clases_alumnos`](#clases_alumnos) | master | codigo | Quien toma cada clase. |
| [`clases_profesores`](#clases_profesores) | master | codigo | Quien da cada clase. Es de muchos a muchos a proposito: una clase puede tener mas de un profesor, y un profesor da varias clases. |
| [`relaciones`](#relaciones) | master | codigo | Vinculos entre personas. Cubre el tutor legal, el contacto de emergencia, quien puede recoger al alumno y quien paga por el (el caso de 'Sofi paga por mi', que de otro modo rompe la conciliacion de pagos). |

## conceptos

Que se cobra y cuanto. Los montos se versionan por vigencia en vez de sobrescribirse, para que un pago viejo siga cuadrando con el precio que existia cuando se hizo.

- Archivo: `data/master/conceptos.csv`
- Llave primaria: `concepto_id`
- Quien la edita: a mano

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `concepto_id` | string | si | PK; unica | Clave del concepto, ej. COLEG-2026. |
| `nombre` | string | si |  | Nombre para mostrar en mensajes y recibos. |
| `tipo` | string | si | uno de: `inscripcion`, `colegiatura`, `material`, `examen`, `evento`, `otro` | Familia del cobro. |
| `monto` | float | si |  | Monto en pesos. |
| `periodicidad` | string | si | uno de: `unica`, `mensual`, `anual` | Cada cuando se cobra. |
| `vigente_desde` | date | si |  | Desde cuando aplica este monto. |
| `vigente_hasta` | date | no |  | Hasta cuando. Vacio = vigente. |
| `activo` | bool | si |  | Si se sigue cobrando. |

## descuentos

Descuentos que la escuela reconoce. Sale del mismo Excel. **Todavia no se sabe quien tiene cual**, asi que no se aplican a la proyeccion: falta la tabla que ligue alumno con descuento.

- Archivo: `data/master/descuentos.csv`
- Llave primaria: `descuento_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `descuento_id` | string | si | PK; unica | Clave del catalogo. |
| `nombre` | string | si |  | Como se le dice. |
| `descripcion` | string | no |  | Cuando aplica. |
| `valor_porcentual` | float | si |  | OJO: en el Excel esta columna mezcla unidades — 0.05 para un 5% y 100.00 para una beca completa. Se guarda tal cual llego; la unidad se resuelve al pasar a `alumnos_descuentos`, donde una persona la confirma. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## espacios

Todos los espacios fisicos de la escuela, no solo las aulas: tambien recepcion, cocina y bodega. Base del proyecto de calendarizacion. Se llama 'espacios' y no 'salones' porque la cocina no es un salon y la calendarizacion nunca debe ofrecerla para dar clase.

- Archivo: `data/master/espacios.csv`
- Llave primaria: `espacio_id`
- Quien la edita: a mano

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `espacio_id` | string | si | PK; unica | Clave corta, ej. AULA-GRANDE. |
| `nombre` | string | si |  | Como le dicen en la escuela. |
| `tipo` | string | si | uno de: `aula`, `auditorio`, `bodega`, `recepcion`, `cocina`, `otro` | Que es el espacio. |
| `piso` | string | si | uno de: `planta_baja`, `planta_alta` | En que nivel esta. Ojo: en la escuela le dicen 'primer piso' a la planta baja, por eso aqui se nombran los niveles y no se numeran. |
| `agendable` | bool | si |  | Si se puede reservar para una clase. Es lo que separa un aula de la cocina, y lo que permite que la bodega deje de serlo un dia sin tener que cambiar el modelo. |
| `capacidad` | int | no |  | Cuantas personas caben. Vacio = todavia no se ha medido. |
| `equipamiento` | string | no |  | Piano, bateria, atriles... |
| `notas` | string | no |  | Tamano relativo y observaciones. |
| `activo` | bool | si |  | Si se puede usar hoy. |

## instrumentos

Instrumentos que se ensenan. Los nombres deben coincidir con los del formulario de inscripcion.

- Archivo: `data/master/instrumentos.csv`
- Llave primaria: `instrumento_id`
- Quien la edita: a mano

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `instrumento_id` | string | si | PK; unica | Clave corta, ej. PIANO. |
| `nombre` | string | si |  | Nombre para mostrar. |
| `familia` | string | no |  | Cuerda, viento, percusion, voz, teoria. |
| `code` | string | no |  | Clave corta de la escuela (PIA, VIO...), del catalogo en Excel. |
| `descripcion` | string | no |  | Como se describe la clase. |
| `activo` | bool | si |  | Si se ofrece actualmente. |

## personas

Una fila por ser humano relacionado con la escuela, sin importar su rol. Alumnos, tutores, profesores y empleados viven todos aqui.

- Archivo: `data/master/personas.csv`
- Llave primaria: `persona_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `persona_id` | string | si | PK; unica | Identificador estable, formato PER-0001. |
| `nombre` | string | si |  | Nombre(s) de pila. |
| `apellido_paterno` | string | no |  | Apellido paterno. |
| `apellido_materno` | string | no |  | Apellido materno. |
| `nombre_normalizado` | string | si |  | Nombre completo sin acentos, en minusculas. Se calcula solo (ids.normalizar_nombre) y sirve para cruzar fuentes que escriben el mismo nombre distinto. |
| `fecha_nacimiento` | date | no |  | Fecha de nacimiento. |
| `telefono` | string | no |  | Telefono en formato E.164, ej. +5215512345678. Es la llave natural para WhatsApp. |
| `correo` | string | no |  | Correo electronico. |
| `domicilio` | string | no |  | Domicilio en una sola linea. |
| `activo` | bool | si |  | Si sigue vinculada a la escuela. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## programas

Los programas de aprendizaje y su precio mensual. Sale del Excel `data/catalogos_lisart.xlsx` que mantiene la escuela; se ingesta con `lisart ingest catalogos`, no se edita aqui.

- Archivo: `data/master/programas.csv`
- Llave primaria: `programa_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `programa_id` | string | si | PK; unica | Clave del catalogo, ej. PDA_001. |
| `modalidad` | string | no |  | Presencial, en linea... |
| `nombre` | string | si |  | Familia del programa, ej. 'Somos Musica'. |
| `categoria` | string | no |  | A quien va dirigido: Adultos, Ninos, Bebes. |
| `caracteristica` | string | no |  | Que trabaja el programa. |
| `arquetipo` | string | no |  | Nivel: Esencial, Integral, Especial, Completo. |
| `descripcion` | string | no |  | Texto largo. |
| `precio` | float | si |  | Cuota mensual en pesos. |
| `activo` | bool | si |  | Si se ofrece hoy. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## respuestas_inscripcion

Una fila por envio del formulario de inscripcion de Jotform, ya aplanado a columnas. Vive en `interim` y no en `master` porque se puede reconstruir entero desde los JSON de `data/raw/jotform/`. Todavia NO es la verdad de la escuela: es materia prima para dar de alta personas y alumnos.

- Archivo: `data/interim/respuestas_inscripcion.csv`
- Llave primaria: `form__submission_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `politicas_de_servicio__nombre_completo` | string | no |  | Quien firma las politicas. |
| `politicas_de_servicio__firma` | string | no |  | Firma de las politicas de servicio. |
| `politicas_de_servicio__manifiesto` | string | no |  | Texto del manifiesto de conformidad. |
| `acepta_reglamento` | bool | no |  | Si acepto el reglamento. |
| `fechayhora_llenado` | datetime | no |  | Cuando se lleno el formulario. |
| `alumno__nombre_completo___nombre` | string | no |  | Nombre del alumno. |
| `alumno__nombre_completo___apellido_paterno` | string | no |  | Nombre del alumno. |
| `alumno__nombre_completo___apellido_materno` | string | no |  | Nombre del alumno. |
| `alumno__nombre_completo___txt` | string | no |  | Nombre del alumno. Todas las partes juntas. |
| `alumno__fecha_nacimiento` | date | no |  | Fecha de nacimiento del alumno. |
| `alumno__edad` | string | no |  | Edad calculada por el formulario. |
| `alumno__domicilio___calle1` | string | no |  | Domicilio del alumno. |
| `alumno__domicilio___calle2` | string | no |  | Domicilio del alumno. |
| `alumno__domicilio___ciudad` | string | no |  | Domicilio del alumno. |
| `alumno__domicilio___estado` | string | no |  | Domicilio del alumno. |
| `alumno__domicilio___codigo_postal` | string | no |  | Domicilio del alumno. |
| `alumno__domicilio___txt` | string | no |  | Domicilio del alumno. Todas las partes juntas. |
| `alumno__telefono___area` | string | no |  | Telefono del alumno. |
| `alumno__telefono___telefono` | string | no |  | Telefono del alumno. |
| `alumno__telefono___txt` | string | no |  | Telefono del alumno. Todas las partes juntas. |
| `alumno__correo` | string | no |  | Correo del alumno. |
| `tutor__nombre_completo___nombre` | string | no |  | Nombre del tutor. |
| `tutor__nombre_completo___apellido_paterno` | string | no |  | Nombre del tutor. |
| `tutor__nombre_completo___apellido_materno` | string | no |  | Nombre del tutor. |
| `tutor__nombre_completo___txt` | string | no |  | Nombre del tutor. Todas las partes juntas. |
| `tutor__fecha_nacimiento` | date | no |  | Fecha de nacimiento del tutor. |
| `tutor__domicilio___calle1` | string | no |  | Domicilio del tutor. |
| `tutor__domicilio___calle2` | string | no |  | Domicilio del tutor. |
| `tutor__domicilio___ciudad` | string | no |  | Domicilio del tutor. |
| `tutor__domicilio___estado` | string | no |  | Domicilio del tutor. |
| `tutor__domicilio___codigo_postal` | string | no |  | Domicilio del tutor. |
| `tutor__domicilio___txt` | string | no |  | Domicilio del tutor. Todas las partes juntas. |
| `tutor__telefono___area` | string | no |  | Telefono del tutor. |
| `tutor__telefono___telefono` | string | no |  | Telefono del tutor. |
| `tutor__telefono___txt` | string | no |  | Telefono del tutor. Todas las partes juntas. |
| `tutor__correo` | string | no |  | Correo del tutor. |
| `documento_path` | string | no |  | Identificacion subida por el tutor. |
| `comprobante_domicilio` | string | no |  | Comprobante de domicilio (no mayor a 3 meses). |
| `emergencia__nombre_completo___nombre` | string | no |  | Contacto de emergencia. |
| `emergencia__nombre_completo___apellido_paterno` | string | no |  | Contacto de emergencia. |
| `emergencia__nombre_completo___apellido_materno` | string | no |  | Contacto de emergencia. |
| `emergencia__nombre_completo___txt` | string | no |  | Contacto de emergencia. Todas las partes juntas. |
| `emergencia__fecha_nacimiento` | date | no |  | Fecha de nacimiento del contacto. |
| `emergencia__domicilio___calle1` | string | no |  | Domicilio del contacto de emergencia. |
| `emergencia__domicilio___calle2` | string | no |  | Domicilio del contacto de emergencia. |
| `emergencia__domicilio___ciudad` | string | no |  | Domicilio del contacto de emergencia. |
| `emergencia__domicilio___estado` | string | no |  | Domicilio del contacto de emergencia. |
| `emergencia__domicilio___codigo_postal` | string | no |  | Domicilio del contacto de emergencia. |
| `emergencia__domicilio___txt` | string | no |  | Domicilio del contacto de emergencia. Todas las partes juntas. |
| `emergencia__telefono___area` | string | no |  | Telefono del contacto de emergencia. |
| `emergencia__telefono___telefono` | string | no |  | Telefono del contacto de emergencia. |
| `emergencia__telefono___txt` | string | no |  | Telefono del contacto de emergencia. Todas las partes juntas. |
| `emergencia__correo` | string | no |  | Correo del contacto de emergencia. |
| `recojer_adicional` | string | no |  | Si autoriza a otras personas a recoger. |
| `recojer1__nombre_completo___nombre` | string | no |  | Primera persona autorizada a recoger. |
| `recojer1__nombre_completo___apellido_paterno` | string | no |  | Primera persona autorizada a recoger. |
| `recojer1__nombre_completo___apellido_materno` | string | no |  | Primera persona autorizada a recoger. |
| `recojer1__nombre_completo___txt` | string | no |  | Primera persona autorizada a recoger. Todas las partes juntas. |
| `recojer1__fecha_nacimiento` | date | no |  | Fecha de nacimiento. |
| `recojer1__domicilio___calle1` | string | no |  | Domicilio. |
| `recojer1__domicilio___calle2` | string | no |  | Domicilio. |
| `recojer1__domicilio___ciudad` | string | no |  | Domicilio. |
| `recojer1__domicilio___estado` | string | no |  | Domicilio. |
| `recojer1__domicilio___codigo_postal` | string | no |  | Domicilio. |
| `recojer1__domicilio___txt` | string | no |  | Domicilio. Todas las partes juntas. |
| `recojer1__telefono___area` | string | no |  | Telefono. |
| `recojer1__telefono___telefono` | string | no |  | Telefono. |
| `recojer1__telefono___txt` | string | no |  | Telefono. Todas las partes juntas. |
| `recojer1__correo` | string | no |  | Correo. |
| `recojer1__id_oficial` | string | no |  | Identificacion oficial. |
| `recojer2__nombre_completo___nombre` | string | no |  | Segunda persona autorizada a recoger. |
| `recojer2__nombre_completo___apellido_paterno` | string | no |  | Segunda persona autorizada a recoger. |
| `recojer2__nombre_completo___apellido_materno` | string | no |  | Segunda persona autorizada a recoger. |
| `recojer2__nombre_completo___txt` | string | no |  | Segunda persona autorizada a recoger. Todas las partes juntas. |
| `recojer2__fecha_nacimiento` | date | no |  | Fecha de nacimiento. |
| `recojer2__domicilio___calle1` | string | no |  | Domicilio. |
| `recojer2__domicilio___calle2` | string | no |  | Domicilio. |
| `recojer2__domicilio___ciudad` | string | no |  | Domicilio. |
| `recojer2__domicilio___estado` | string | no |  | Domicilio. |
| `recojer2__domicilio___codigo_postal` | string | no |  | Domicilio. |
| `recojer2__domicilio___txt` | string | no |  | Domicilio. Todas las partes juntas. |
| `recojer2__telefono___area` | string | no |  | Telefono. |
| `recojer2__telefono___telefono` | string | no |  | Telefono. |
| `recojer2__telefono___txt` | string | no |  | Telefono. Todas las partes juntas. |
| `recojer2__correo` | string | no |  | Correo. |
| `recojer2__id_oficial` | string | no |  | Identificacion oficial. |
| `instrumentos` | string | no |  | Instrumentos elegidos, separados por |. |
| `pda` | string | no |  | Programa de desarrollo artistico. |
| `horario___L` | string | no |  | Horas marcadas el dia L, separadas por |. |
| `horario___M` | string | no |  | Horas marcadas el dia M, separadas por |. |
| `horario___Mi` | string | no |  | Horas marcadas el dia Mi, separadas por |. |
| `horario___J` | string | no |  | Horas marcadas el dia J, separadas por |. |
| `horario___V` | string | no |  | Horas marcadas el dia V, separadas por |. |
| `horario___S` | string | no |  | Horas marcadas el dia S, separadas por |. |
| `aviso_de_privacidad` | bool | no |  | Si acepto el aviso de privacidad. |
| `uso_imagen__autorizo_mayor` | bool | no |  | Autoriza uso de imagen (mayor de edad). |
| `uso_imagen__autorizo_menor` | bool | no |  | Autoriza uso de imagen (menor de edad). |
| `uso_imagen__nombre_completo_alumno___nombre` | string | no |  | Alumno mayor de edad que firma por si mismo el uso de imagen. |
| `uso_imagen__nombre_completo_alumno___apellido_paterno` | string | no |  | Alumno mayor de edad que firma por si mismo el uso de imagen. |
| `uso_imagen__nombre_completo_alumno___apellido_materno` | string | no |  | Alumno mayor de edad que firma por si mismo el uso de imagen. |
| `uso_imagen__nombre_completo_alumno___txt` | string | no |  | Alumno mayor de edad que firma por si mismo el uso de imagen. Todas las partes juntas. |
| `uso_imagen__nombre_completo_tutor___nombre` | string | no |  | Tutor que firma el uso de imagen de un menor. |
| `uso_imagen__nombre_completo_tutor___apellido_paterno` | string | no |  | Tutor que firma el uso de imagen de un menor. |
| `uso_imagen__nombre_completo_tutor___apellido_materno` | string | no |  | Tutor que firma el uso de imagen de un menor. |
| `uso_imagen__nombre_completo_tutor___txt` | string | no |  | Tutor que firma el uso de imagen de un menor. Todas las partes juntas. |
| `uso_imagen__firma` | string | no |  | Firma del uso de imagen. |
| `uso_imagen__no_autorizo_mayor` | bool | no |  | NO autoriza uso de imagen (mayor). |
| `uso_imagen__no_autorizo_menor` | bool | no |  | NO autoriza uso de imagen (menor). |
| `form__submission_id` | string | si | PK; unica | Id del envio en Jotform. Es la llave. |
| `form__id` | string | no |  | Id del formulario. |
| `form__ip` | string | no |  | IP desde donde se envio. |
| `form__created_at` | datetime | no |  | Cuando lo registro Jotform. |
| `form__status` | string | no |  | Estado en Jotform. Solo ACTIVE cuenta como envio vigente. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## alumnos

Datos que solo tienen sentido para un alumno. Es una extension de `personas`: la llave es la misma persona_id, no una nueva.

- Archivo: `data/master/alumnos.csv`
- Llave primaria: `persona_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `persona_id` | string | si | PK; unica; -> `personas.persona_id` | El alumno, como persona. |
| `estatus` | string | si | uno de: `prospecto`, `inscrito`, `activo`, `baja`, `egresado` | Situacion actual del alumno. |
| `fecha_alta` | date | no |  | Primer dia en la escuela. |
| `fecha_baja` | date | no |  | Ultimo dia. Vacio = sigue activo. |
| `requiere_tutor` | bool | si |  | Verdadero si es menor de edad y necesita tutor responsable. |
| `programa` | string | no |  | Programa de aprendizaje contratado (el 'PDA' del formulario). |
| `notas` | string | no |  | Observaciones libres. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## clases

Una clase en la semana tipo: que dia, a que hora, en que espacio. Quien la da y quien la toma van en tablas aparte porque una clase puede tener varios profesores y varios alumnos.

- Archivo: `data/master/clases.csv`
- Llave primaria: `clase_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `clase_id` | string | si | PK; unica | Identificador, formato CLA-0001. |
| `nombre` | string | no |  | Como se le dice a esta clase. |
| `instrumento_id` | string | no | -> `instrumentos.instrumento_id` | Instrumento que se trabaja. |
| `espacio_id` | string | no | -> `espacios.espacio_id` | Donde se da. |
| `dia` | string | si | uno de: `L`, `M`, `Mi`, `J`, `V`, `S`, `D` | Dia de la semana. |
| `hora_inicio` | time | si |  | Hora de inicio, 24 h. |
| `hora_fin` | time | si |  | Hora de fin, sin incluirla. |
| `cupo` | int | no |  | Cuantos alumnos caben. Vacio = sin limite. |
| `activa` | bool | si |  | Si se sigue dando. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## disponibilidad

Cuando puede cada persona, semana tipo. Vale para profesores y para alumnos: el alumno declara su horario al inscribirse y el profesor el suyo al dar de alta. Cruzar las dos es lo que permite proponer una reposicion que le sirva a los dos.

- Archivo: `data/master/disponibilidad.csv`
- Llave primaria: `disponibilidad_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `disponibilidad_id` | string | si | PK; unica | Identificador, formato DIS-0001. |
| `persona_id` | string | si | -> `personas.persona_id` | De quien es este horario. |
| `dia` | string | si | uno de: `L`, `M`, `Mi`, `J`, `V`, `S`, `D` | Dia de la semana. |
| `hora_inicio` | time | si |  | Desde que hora, en formato 24 h. |
| `hora_fin` | time | si |  | Hasta que hora, sin incluirla. |
| `estado` | string | si | uno de: `disponible`, `bloqueado` | Que pasa en ese rango. NO existe 'no disponible': una hora sin fila es una hora no disponible. Ver el modulo horarios. |
| `motivo` | string | no |  | Por que esta bloqueado, si lo esta. Util para distinguir una clase de un bloqueo personal. |
| `vigente_desde` | date | no |  | Desde cuando rige este bloque. Vacio = siempre. |
| `vigente_hasta` | date | no |  | Hasta cuando rigio. Vacio = sigue vigente. El horario cambia, y cerrar el viejo conserva por que una clase estaba donde estaba. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## identificadores_externos

Puente entre nuestra persona_id y como la llama cada sistema de afuera. Es la pieza que permite cruzar Kydemy, Jotform y WhatsApp sin adivinar por nombre cada vez.

- Archivo: `data/master/identificadores_externos.csv`
- Llave primaria: `sistema`, `id_externo`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `sistema` | string | si | PK; uno de: `kydemy`, `jotform`, `whatsapp`, `odoo`, `banco` | Sistema externo. |
| `id_externo` | string | si | PK | El identificador tal como lo usa ese sistema. |
| `persona_id` | string | si | -> `personas.persona_id` | A quien corresponde aqui. |
| `notas` | string | no |  | Aclaraciones del cruce. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## personas_roles

Que papel juega cada persona. Una persona puede tener varios roles a la vez y puede cambiarlos con el tiempo.

- Archivo: `data/master/personas_roles.csv`
- Llave primaria: `persona_id`, `rol`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `persona_id` | string | si | PK; -> `personas.persona_id` | Persona a la que aplica el rol. |
| `rol` | string | si | PK; uno de: `alumno`, `tutor`, `profesor`, `empleado`, `director`, `proveedor` | Papel que juega en la escuela. |
| `vigente_desde` | date | no |  | Desde cuando tiene el rol. |
| `vigente_hasta` | date | no |  | Hasta cuando lo tuvo. Vacio = sigue vigente. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## alumnos_descuentos

Que descuento tiene cada alumno. **Es la unica tabla del sistema que se llena a mano abriendo el archivo**, porque el dato no vive en ninguna fuente: lo decide la administracion caso por caso. El archivo lista a TODOS los alumnos inscritos, no solo a los que tienen descuento. Los que si tienen quedan arriba (los renglones con `descuento` vacio se van al final al ordenar), asi que se abre y lo primero que se ve es a quien se le esta descontando. Dar de alta un descuento es escribir su nombre en el renglon del alumno; quitarlo es borrar esa celda. `lisart descuentos` es el mantenimiento: agrega a los alumnos nuevos, rellena nombre, clave y porcentaje, y avisa de lo que no cuadra. Correrlo despues de editar.

- Archivo: `data/master/alumnos_descuentos.csv`
- Llave primaria: `alumno_descuento_id`
- Quien la edita: a mano

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `alumno_descuento_id` | string | no | PK; unica | Identificador de la fila, formato ALD-0001. Al agregar un renglon se puede dejar vacio: `lisart descuentos` lo asigna. |
| `persona_id` | string | no | -> `alumnos.persona_id` | El alumno. Se puede dejar vacio si se escribe su nombre completo en `alumno`; `lisart descuentos` lo resuelve. |
| `alumno` | string | no |  | Nombre del alumno. Se rellena solo. Esta aqui para que el archivo se pueda leer sin andar cruzando claves a mano. |
| `descuento` | string | no |  | **La celda que se edita.** El nombre del descuento tal como esta en el catalogo `descuentos`. Vacio = sin descuento. Un alumno con dos descuentos lleva dos renglones. |
| `descuento_id` | string | no | -> `descuentos.descuento_id` | Clave del catalogo. La resuelve `lisart descuentos` a partir del nombre; no hace falta escribirla. |
| `porcentaje` | float | no |  | Cuanto se le descuenta, EN PUNTOS: 5 es 5%, 100 es beca completa. Se siembra del catalogo pero manda lo que diga esta celda, para poder pactar un caso particular sin inventar una entrada de catalogo. Si se cambia el catalogo, esta columna NO se actualiza sola: eso es lo que se paga por poder ajustarla. |
| `notas` | string | no |  | Por que tiene ese descuento, desde cuando, con quien se pacto. Es lo que evita que dentro de un ano nadie sepa de donde salio. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## alumnos_instrumentos

Que instrumento estudia cada alumno. Es de muchos a muchos: hay quien lleva dos. Separarla de `alumnos` en vez de meter una columna con valores pegados por comas es lo que permite preguntar 'quien mas toca piano' sin partir texto.

- Archivo: `data/master/alumnos_instrumentos.csv`
- Llave primaria: `persona_id`, `instrumento_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `persona_id` | string | si | PK; -> `alumnos.persona_id` | El alumno. |
| `instrumento_id` | string | si | PK; -> `instrumentos.instrumento_id` | El instrumento del catalogo. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## clases_alumnos

Quien toma cada clase.

- Archivo: `data/master/clases_alumnos.csv`
- Llave primaria: `clase_id`, `persona_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `clase_id` | string | si | PK; -> `clases.clase_id` | La clase. |
| `persona_id` | string | si | PK; -> `alumnos.persona_id` | El alumno. |
| `vigente_desde` | date | no |  | Desde cuando la toma. |
| `vigente_hasta` | date | no |  | Hasta cuando. Vacio = sigue. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## clases_profesores

Quien da cada clase. Es de muchos a muchos a proposito: una clase puede tener mas de un profesor, y un profesor da varias clases.

- Archivo: `data/master/clases_profesores.csv`
- Llave primaria: `clase_id`, `persona_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `clase_id` | string | si | PK; -> `clases.clase_id` | La clase. |
| `persona_id` | string | si | PK; -> `personas.persona_id` | El profesor. |
| `rol_en_clase` | string | no | uno de: `titular`, `apoyo`, `suplente` | Que hace en la clase. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |

## relaciones

Vinculos entre personas. Cubre el tutor legal, el contacto de emergencia, quien puede recoger al alumno y quien paga por el (el caso de 'Sofi paga por mi', que de otro modo rompe la conciliacion de pagos).

- Archivo: `data/master/relaciones.csv`
- Llave primaria: `relacion_id`
- Quien la edita: codigo

| Columna | Tipo | Obligatoria | Reglas | Descripcion |
| --- | --- | --- | --- | --- |
| `relacion_id` | string | si | PK; unica | Identificador, formato REL-0001. |
| `alumno_persona_id` | string | si | -> `alumnos.persona_id` | El alumno del que se habla. |
| `relacionado_persona_id` | string | si | -> `personas.persona_id` | La otra persona del vinculo. |
| `tipo` | string | si | uno de: `tutor`, `emergencia`, `autorizado_recoger`, `paga_por`, `hermano`, `profesor` | Naturaleza del vinculo. |
| `parentesco` | string | no |  | Como lo dijo la familia: madre, padre, abuela, tio... |
| `vigente` | bool | si |  | Si el vinculo sigue vigente. |
| `creado_en` | datetime | si |  | Cuando se creo la fila. |
| `actualizado_en` | datetime | si |  | Ultima modificacion de la fila. |
| `fuente` | string | si | uno de: `jotform`, `kydemy`, `whatsapp`, `manual`, `migracion`, `demo` | De donde salio el dato. |
