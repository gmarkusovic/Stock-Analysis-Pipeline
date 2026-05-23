#!/bin/bash
# Carga las variables y corre el pipeline.
# Uso:
#   ./run.sh --mock --dry-run       # test offline
#   ./run.sh --yfinance --dry-run   # datos reales, sin escribir al sheet
#   ./run.sh --yfinance --now       # datos reales → escribe al sheet

set -e

if [ ! -f .env ]; then
  echo "Error: falta el archivo .env"
  echo "Ejecutá: cp .env.example .env  y completá la ruta del JSON"
  exit 1
fi

set -a
source .env
set +a

if [ -z "$GOOGLE_SERVICE_ACCOUNT_JSON" ] || [ "$GOOGLE_SERVICE_ACCOUNT_JSON" = "/ruta/al/nuevo-archivo.json" ]; then
  echo "Error: GOOGLE_SERVICE_ACCOUNT_JSON no está configurado en .env"
  exit 1
fi

if [ ! -f "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then
  echo "Error: no existe el archivo $GOOGLE_SERVICE_ACCOUNT_JSON"
  exit 1
fi

python orchestrator.py "$@"
