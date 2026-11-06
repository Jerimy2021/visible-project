# adapters/outbound

Implementaciones de los puertos de `application` contra servicios reales.

- DynamoDB (historial financiero, perfiles).
- S3 (evidencias: fotos, capturas de Yape, audios).
- Bedrock (Claude multimodal: extracción).
- Transcribe (notas de voz).
- Twilio REST API (respuestas salientes de WhatsApp).
- SSM Parameter Store (secretos).

Aquí vive todo el acoplamiento a AWS y a terceros.
