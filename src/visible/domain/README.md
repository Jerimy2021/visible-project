# domain

Núcleo del negocio: entidades, value objects y reglas de puntaje crediticio.

Python puro, sin dependencias de AWS ni de frameworks. No conoce Twilio,
DynamoDB ni Bedrock; se expresa en términos del problema (ventas, ingresos,
evidencias, perfil de crédito).

El motor de reglas de puntaje vive aquí: recibe hechos financieros normalizados
y devuelve un puntaje + justificación, de forma determinista y testeable.

Depende de nada. Todo lo demás depende de este paquete.
