# QA Lab

Учебный стенд для практики Manual QA.

## Компоненты

- Demo API / Swagger
- PostgreSQL
- Adminer
- Kafka
- Kafka UI
- Prometheus
- Grafana
- Elasticsearch
- Kibana
- Fluent Bit

## Зависимости

- Linux
- Docker
- Docker Compose Plugin
- 4+ CPU
- 12+ GB RAM
- 80+ GB disk

Рекомендованные:

- 6 CPU
- 16 GB RAM
- 100+ GB SSD

## Первый старт

Клонируем репозиторий:

```bash
git clone <repository>
cd qa-lab

Создать конфигурацию:

cp .env.example .env
nano .env

###Start:

./scripts/start.sh

###Status:

./scripts/status.sh

###Logs:

./scripts/logs.sh

###Stop:

./scripts/stop.sh

###Complete reset:

./scripts/reset.sh

##Порты
Service	        Port
Demo API	8000
Grafana	        3000
Prometheus	9090
Kibana	        5601
Elasticsearch	9200
Kafka UI	8081
Adminer	        8082
PostgreSQL	5432
Kafka	        29092
```

