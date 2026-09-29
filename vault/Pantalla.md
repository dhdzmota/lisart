---
tipo: concepto
tags: [concepto]
---

# Pantalla

Se abre con `lisart ui`. Una **seccion por tabla** mas la del grafo, y dentro de
cada una un registro a la vez con flechas y buscador.

## Tres cosas que hace por diseno

1. **Los campos no estan escritos en la app.** Salen de `tables.py`: el tipo
   decide el control, un catalogo se vuelve lista desplegable y una llave
   foranea se vuelve un selector de valores que si existen. Al agregar una
   columna al modelo, aparece sola en pantalla.
2. **Nada se sobrescribe sin respaldo.** Guardar valida, copia el estado
   anterior a `data/backups/` y luego escribe. Restaurar esta en la misma
   pantalla, y restaurar tambien deja copia de lo que pisa.
3. **Lo que no se debe editar, no se puede editar:** la llave primaria (romperla
   deja referencias colgando), las marcas de tiempo, y las tablas de capa
   `interim`, que se regeneran desde `raw`.

## El grafo

Ultima seccion. Contesta *que alumnos se parecen*: los que estudian el mismo
instrumento se agrupan alrededor de el, los hermanos alrededor de su tutor.
Cada nodo es una figura musical — negra el alumno, corchea el tutor, redonda el
[[instrumentos|instrumento]] — y al hacer clic se abre su ficha.

No hay nodo de maestro: el formulario de [[Jotform]] no pregunta quien da la
clase. Cuando exista el dato entra como [[relaciones]] de tipo `profesor`
ligadas al alumno.

## Horarios y reposicion

La seccion **Horarios** muestra la semana tipo de cualquier persona, dibujada
como linea de tiempo por dia. Una hora esta en uno de tres estados —disponible,
bloqueado, no disponible— pero **solo se guardan dos**: el tercero es la
ausencia de fila en [[disponibilidad]].

La otra vista busca **reposicion**: cuando un alumno falta, cruza sus [[clases]]
con sus profesores ([[clases_profesores]], que es de muchos a muchos) y con su
propio horario.

## La agenda de profesores

Aplicacion aparte (`lisart ui --profesores`) con otro camino: se entra por la
clase, no por la persona. Las horas que los alumnos de esa clase marcaron se
pintan como ocupadas para el profesor —una aproximacion declarada, no un dato— y
no se guardan.

## Datos de prueba

`lisart demo` siembra profesores y clases marcados con `fuente = "demo"`, y
`lisart demo --limpiar` los borra sin tocar nada real. Sin ellos no habia forma
de ejercitar la agenda ni la reposicion.

## Identidad visual

Negro exacto del logo en la banda, mayusculas espaciadas como en "ACADEMIA DE
MUSICA", y el vino de la paleta como el lapiz rojo con que un musico anota su
partitura: marca el registro actual y la accion de guardar. El navegador de
registros **es un pentagrama**, y la altura de cada nota sale del Himno a la
Alegria.

Volver a [[Lisart]].
