"""Conectores con los sistemas de afuera: Jotform, Kydemy, WhatsApp.

Cada modulo de aqui hace lo mismo en tres pasos:

1. **Baja** lo que hay en el sistema externo y lo guarda tal cual en `data/raw/`.
2. **Aplana** ese formato ajeno a una tabla con columnas y tipos.
3. **Agrega** a la tabla solo lo que no estaba antes.

El paso 1 se guarda siempre, aunque no haya nada nuevo, porque `raw` es la
unica copia que no depende de que el sistema externo siga existiendo.
"""
