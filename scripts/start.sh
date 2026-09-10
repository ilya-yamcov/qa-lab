#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "ERROR: .env not found"
    echo "Create it first:"
    echo "cp .env.example .env"
    exit 1
fi

echo "Starting QA Lab..."

docker compose up -d --build

echo
docker compose ps
