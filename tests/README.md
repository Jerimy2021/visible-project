# tests

Pruebas con pytest. `pythonpath=src` está configurado en pyproject.toml.

Prioridad: tests unitarios del motor de reglas de puntaje (`domain`), que es
puro y determinista — rápido de cubrir y el corazón del producto.

Los adapters se prueban con dobles/fakes de los puertos; se evita llamar a
AWS real en la suite. Ejecutar con `just test`.
