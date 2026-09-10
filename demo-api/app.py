import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response


app = FastAPI(
    title="QA Lab Demo API",
    version="1.0.0"
)


DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "qa_lab")
DB_USER = os.getenv("DB_USER", "qa_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "qa_password")

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:19092"
)

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "orders")

LOG_FILE = os.getenv(
    "LOG_FILE",
    "/app/logs/app.log"
)


producer = Producer({
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS
})


HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"]
)

ORDER_COUNTER = Counter(
    "orders_created_total",
    "Number of successfully created orders"
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"]
)


class OrderCreate(BaseModel):
    user_id: int
    amount: Decimal


def log_event(level: str, event: str, **fields):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        **fields
    }

    line = json.dumps(
        payload,
        ensure_ascii=False,
        default=str
    )

    print(line, flush=True)

    os.makedirs(
        os.path.dirname(LOG_FILE),
        exist_ok=True
    )

    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row
    )


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        duration = time.time() - start

        HTTP_REQUESTS.labels(
            request.method,
            request.url.path,
            str(status)
        ).inc()

        REQUEST_DURATION.labels(
            request.method,
            request.url.path
        ).observe(duration)

    return response


@app.get("/")
def root():
    return {
        "service": "qa-lab-demo-api",
        "status": "running"
    }


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

        return {
            "status": "UP",
            "database": "UP"
        }

    except Exception as error:
        log_event(
            "ERROR",
            "health_check_failed",
            error=str(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Database unavailable"
        )


@app.get("/users")
def users():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, created_at
                FROM users
                ORDER BY id
                """
            )

            return cursor.fetchall()


@app.post("/orders")
def create_order(order: OrderCreate):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO orders (user_id, amount)
                    VALUES (%s, %s)
                    RETURNING id,
                              user_id,
                              amount,
                              status,
                              created_at
                    """,
                    (
                        order.user_id,
                        order.amount
                    )
                )

                created_order = cursor.fetchone()

            conn.commit()

    except Exception as error:
        log_event(
            "ERROR",
            "database_error",
            error=str(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    kafka_event = {
        "event": "ORDER_CREATED",
        "order_id": created_order["id"],
        "user_id": created_order["user_id"],
        "amount": str(created_order["amount"]),
        "status": created_order["status"],
        "created_at": created_order["created_at"].isoformat()
    }

    try:
        producer.produce(
            KAFKA_TOPIC,
            key=str(created_order["id"]),
            value=json.dumps(kafka_event)
        )

        producer.flush(2)

    except Exception as error:
        log_event(
            "ERROR",
            "kafka_publish_failed",
            order_id=created_order["id"],
            error=str(error)
        )

    ORDER_COUNTER.inc()

    log_event(
        "INFO",
        "order_created",
        order_id=created_order["id"],
        user_id=created_order["user_id"],
        amount=str(created_order["amount"])
    )

    return created_order


@app.get("/orders/{order_id}")
def get_order(order_id: int):

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                SELECT id,
                       user_id,
                       amount,
                       status,
                       created_at
                FROM orders
                WHERE id = %s
                """,
                (order_id,)
            )

            order = cursor.fetchone()

    if not order:

        log_event(
            "WARNING",
            "order_not_found",
            order_id=order_id
        )

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order


@app.get("/error")
def generate_error():

    log_event(
        "ERROR",
        "manual_test_error",
        message="Error generated intentionally"
    )

    raise HTTPException(
        status_code=500,
        detail="Intentional QA test error"
    )


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
