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

# Imprime el verify token de Meta (para pegarlo en la config del webhook)
verify-token:
    aws ssm get-parameter --name /visible/meta/verify_token --with-decryption \
        --profile {{profile}} --region {{region}} --query Parameter.Value --output text

# Imprime el output WebhookUrl del stack desplegado
url:
    aws cloudformation describe-stacks --stack-name {{stack}} --region {{region}} --profile {{profile}} \
        --query "Stacks[0].Outputs[?OutputKey=='WebhookUrl'].OutputValue" --output text

# Tail de logs de una función: just logs fn=procesar
logs fn:
    sam logs --stack-name {{stack}} --name {{fn}} --region {{region}} --profile {{profile}} --tail

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
