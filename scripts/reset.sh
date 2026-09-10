#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

echo "WARNING: this will delete all QA Lab data."
read -r -p "Continue? [y/N]: " answer

if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

docker compose down -v --remove-orphans
docker compose up -d --build

docker compose ps
