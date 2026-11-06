# adapters/inbound

Puntos de entrada que traducen el mundo externo a casos de uso.

- Handler del webhook de Twilio (valida X-Twilio-Signature, responde <3s,
  invoca async la Lambda `procesar`).
- Handler de la Lambda `procesar` (consume el evento asíncrono).

Traducen eventos Lambda / HTTP a llamadas de `application`. Sin reglas de
negocio aquí.
