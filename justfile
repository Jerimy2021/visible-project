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
    sam build --template infra/template.yaml

# Despliega (usa configuración guardada de samconfig)
deploy: build
    sam deploy --stack-name {{stack}} --region {{region}} --profile {{profile}} \
        --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset

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
