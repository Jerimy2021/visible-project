# infra

Infraestructura como código con AWS SAM (NO Serverless).

`template.yaml` (pendiente) definirá: funciones Lambda (webhook, procesar),
DynamoDB on-demand, bucket S3 (Block Public Access, SSE-S3, versionado),
parámetros SSM SecureString, IAM de mínimo privilegio por función y logs
con retención de 14 días.

Región us-east-1. Despliegue vía `just deploy`. No se crean Organizations
ni claves KMS administradas por el cliente.
