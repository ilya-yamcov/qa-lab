# QA Lab — Windows Student Edition

Учебный стенд Manual QA: TaskFlow → FastAPI → PostgreSQL / Kafka; логи через Fluent Bit → Elasticsearch → Kibana; метрики через Prometheus → Grafana.

## Подготовка Windows

1. Установите [Git for Windows](https://git-scm.com/download/win) и [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/).
2. В PowerShell администратора выполните `wsl --install`, перезагрузитесь при необходимости. Отдельная Linux VM не нужна.
3. Запустите Docker Desktop с WSL 2 engine и Linux containers. Проверьте `docker info` и `docker compose version`.
4. Для этого набора сервисов рекомендуется 16 GB RAM, 4+ CPU и минимум 40 GB свободного места для Docker. Репозиторий можно хранить на другом диске. В Docker Desktop проверьте Disk image location: образы и volumes могут занимать диск C, даже если проект на Z.

## Первый запуск

В обычном PowerShell перейдите на диск с достаточным местом:

```powershell
git clone -b student-windows https://github.com/ilya-yamcov/qa-lab.git
cd qa-lab
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
.\scripts\doctor.ps1
.\scripts\start.ps1
```

Учебный `.env` хранится в репозитории: `LAB_USERNAME=qaengineer`, `LAB_PASSWORD=123qa`, `POSTGRES_DB=qa_lab`, `KAFKA_EXTERNAL_HOST=localhost`. Credentials намеренно публичные. Используйте стенд для локального обучения. Текущий Compose публикует порты на всех интерфейсах; переменная BIND_ADDRESS пока не подключена к ports.

Первый запуск скачивает образы и собирает API. Скрипт ждёт API, затем настраивает Kibana и проверяет Grafana. Ошибка настройки прерывает запуск скрипта; уже запущенные контейнеры продолжают работать. После исправления повторите запуск.

## Адреса и вход

| Сервис | Адрес | Вход |
|---|---|---|
| TaskFlow | http://localhost:8080 | qaengineer / 123qa |
| Swagger | http://localhost:8000/docs | По требованиям конкретного API endpoint |
| Kafka UI | http://localhost:8081 | qaengineer / 123qa |
| Adminer | http://localhost:8082 | PostgreSQL, сервер postgres, БД qa_lab, qaengineer / 123qa |
| Grafana | http://localhost:3000/d/qa-lab-overview | qaengineer / 123qa |
| Kibana Discover | http://localhost:5601/app/discover | Без входа в текущей конфигурации |
| Prometheus | http://localhost:9090 | Без входа |
| Elasticsearch | http://localhost:9200 | Без входа |

Для DBeaver: PostgreSQL `localhost:5432`, БД `qa_lab`, qaengineer / 123qa. Kafka с Windows: `localhost:29092`.

## Автоматическая настройка логов и метрик

`start.ps1` вызывает `init-observability.ps1`. Он создаёт или обновляет Data View `qa-demo-*` с полем времени `@timestamp` и делает его основным. Существующий Data View с таким pattern используется повторно; остальные не удаляются. Индексы и логи сохраняются. Data View создаётся даже до появления первых логов.

Grafana читает datasource из `grafana/provisioning/datasources/datasource.yml`, а dashboard — из `grafana/provisioning/dashboards/json/qa-lab.json`. Используется внутренний адрес `http://prometheus:9090`. Dashboard расположен в папке QA Lab и использует datasource-переменную, поэтому не зависит от UID уже существующего Prometheus. Учебную копию dashboard можно сохранить под другим именем; исходный управляется файлами.

После обновления файлов в существующем стенде:

```powershell
docker compose restart grafana
.\scripts\init-observability.ps1
.\scripts\doctor.ps1 -CheckServices
```

Повторная настройка безопасна для данных. Она не сбрасывает пароль Grafana: существующий volume сохраняет прежний пароль администратора. Если credentials отличаются, восстановите доступ к Grafana отдельно; не удаляйте volumes ради provisioning.

## Проверка учеником

1. Войдите в TaskFlow, создайте и измените профиль.
2. В Kibana Discover выберите `qa-demo-*`, интервал Last 15 minutes и обновите данные. Фильтр: `event : "profile_created"`. Добавьте колонки event, level, profile_id, owner_email; колонка log не требуется для структурированных событий.
3. В Grafana откройте QA Lab Overview. Подождите около минуты для расчёта rate. API available должен быть 1; после действий изменятся счётчики профилей и запросы. Нулевая активность допустима; счётчики отражают период с последнего старта API.
4. Если графики пустые, проверьте http://localhost:9090/targets — demo-api должен быть UP. Логи появляются только после действий, создающих события.

## Управление и диагностика

```powershell
.\scripts\stop.ps1                 # остановка с сохранением данных
.\scripts\start.ps1                # запуск и настройка
.\scripts\doctor.ps1               # окружение, порты, контейнеры
.\scripts\doctor.ps1 -CheckServices # также проверка Data View и dashboard
.\scripts\init-observability.ps1    # повторить настройку без пересоздания контейнеров
docker compose logs --tail 100 kibana grafana fluent-bit demo-api
.\scripts\reset.ps1                # удаляет ВСЕ данные после ввода YES
```

После reset скрипт запускает стенд заново и восстанавливает настройку. Если Kibana ещё не готова, provisioning ждёт до 300 секунд; для медленного компьютера: `./scripts/init-observability.ps1 -TimeoutSeconds 600`. Если Elasticsearch не запускается, проверьте вывод настройки vm.max_map_count и логи контейнера. При занятом порте определите владельца: это может быть уже работающий QA Lab.

Описание механизмов: [Kibana Data Views API](https://www.elastic.co/docs/api/doc/kibana/operation/operation-createdataviewdefaultw), [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/).
