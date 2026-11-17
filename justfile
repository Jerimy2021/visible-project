set shell := ["bash", "-euo", "pipefail", "-c"]

profile := "visible"
region  := "us-east-1"
stack   := "visible"

# Lista las recetas
default:
    @just --list

# Login SSO (credenciales temporales, sin access keys)
login:
    aws login --profile {{profile}}

# Identidad activa
whoami:
    aws sts get-caller-identity --profile {{profile}} --output table

# Construye artefactos SAM
build:
    sam build -t infra/template.yaml

# Despliega (parámetros en samconfig.toml).
# SAM trae su propio botocore sin CRT y no resuelve el proveedor `login`;
# exportamos las credenciales ya resueltas por awscli y desactivamos AWS_PROFILE.
deploy: build
    eval "$(aws configure export-credentials --profile {{profile}} --format env)" && \
        env -u AWS_PROFILE sam deploy

# Construye el panel con VITE_API_URL del stack, lo sube a S3 e invalida CloudFront
web:
    #!/usr/bin/env bash
    set -euo pipefail
    salida() { aws cloudformation describe-stacks --stack-name {{stack}} --region {{region}} \
        --profile {{profile}} --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
    API=$(salida ApiBaseUrl); BUCKET=$(salida WebBucketName); DIST=$(salida WebDistributionId)
    KEY=$(aws ssm get-parameter --name /visible/brigada/api_key --with-decryption \
        --profile {{profile}} --region {{region}} --query Parameter.Value --output text)
    echo "API=$API  BUCKET=$BUCKET  DIST=$DIST"
    ( cd web && npm install --no-audit --no-fund --silent && VITE_API_URL="$API" VITE_API_KEY="$KEY" npm run build )
    aws s3 sync web/dist "s3://$BUCKET" --delete --region {{region}} --profile {{profile}}
    aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" --profile {{profile}} --output text

# Imprime los outputs del stack
url:
    aws cloudformation describe-stacks --stack-name {{stack}} --region {{region}} --profile {{profile}} \
        --query "Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}" --output table

# Tail de logs de una función: just logs fn=import-process (import-process|import-api)
logs fn:
    aws logs tail /aws/lambda/{{stack}}-{{fn}} --follow --format short \
        --region {{region}} --profile {{profile}}

# Carga inicial de las listas desde data/raw a DynamoDB (solo arranque del piloto)
import:
    eval "$(aws configure export-credentials --profile {{profile}} --format env)" && \
        env -u AWS_PROFILE uv run --with boto3 python scripts/import_inicial.py

# Tests
test:
    uv run pytest -q

# Lint
lint:
    ruff check .
    cfn-lint infra/template.yaml

# Formateo
fmt:
    ruff format .
    ruff check --fix .

# Limpia artefactos locales
clean:
    rm -rf .aws-sam .pytest_cache .ruff_cache **/__pycache__
