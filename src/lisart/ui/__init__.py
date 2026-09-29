"""Pantallas para ver y editar las tablas sin abrir un CSV.

Se corre con `lisart ui`. Por dentro es Streamlit, que es software libre y es
lo que un data scientist puede modificar sin pelearse con nada.

La app **no reimplementa** el modelo de datos: los campos, los tipos, los
catalogos y las referencias salen de `tables.py`. Al agregar una columna ahi,
aparece sola en la pantalla.
"""

APP = "lisart.ui.app"
