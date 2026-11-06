# application

Casos de uso que orquestan el dominio: "procesar mensaje entrante",
"transcribir audio", "extraer venta de imagen", "recalcular perfil".

Define puertos (interfaces) que los adapters implementan: repositorio de
evidencias, almacén de historial, extractor multimodal, transcriptor,
notificador saliente.

Depende solo de `domain`. No importa boto3 ni ningún SDK; recibe las
implementaciones por inyección de dependencias.
