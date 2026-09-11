import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException, Request, Header
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

PROFILE_CREATED = Counter(
    "profiles_created_total",
    "Number of successfully created profiles"
)

PROFILE_UPDATED = Counter(
    "profiles_updated_total",
    "Number of successfully updated profiles"
)

PROFILE_DELETED = Counter(
    "profiles_deleted_total",
    "Number of successfully deleted profiles"
)

class OrderCreate(BaseModel):
    user_id: int
    amount: Decimal

class ProfileData(BaseModel):
    name: str
    email: str
    phone: str | None = None
    website: str | None = None

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

def publish_kafka_event(topic: str, event: dict, key: str | None = None):
    try:
        producer.produce(
            topic,
            key=key,
            value=json.dumps(
                event,
                ensure_ascii=False,
                default=str
            )
        )

        producer.flush(2)

    except Exception as error:
        log_event(
            "ERROR",
            "kafka_publish_failed",
            topic=topic,
            error=str(error)
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

@app.get("/profiles")
def get_profiles(
    x_user_email: str = Header(..., alias="X-User-Email")
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    phone,
                    website,
                    created_at,
                    updated_at
                FROM profiles
                WHERE owner_email = %s
                ORDER BY id
                """,
                (x_user_email,)
            )

            profiles = cursor.fetchall()

    log_event(
        "INFO",
        "profiles_listed",
        owner_email=x_user_email,
        count=len(profiles)
    )

    return profiles

@app.post("/profiles", status_code=201)
def create_profile(
    profile: ProfileData,
    x_user_email: str = Header(..., alias="X-User-Email")
):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO profiles (
                        owner_email,
                        name,
                        email,
                        phone,
                        website
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING
                        id,
                        name,
                        email,
                        phone,
                        website,
                        created_at,
                        updated_at
                    """,
                    (
                        x_user_email,
                        profile.name,
                        profile.email,
                        profile.phone,
                        profile.website
                    )
                )

                created = cursor.fetchone()

            conn.commit()

    except Exception as error:
        log_event(
            "ERROR",
            "profile_create_failed",
            owner_email=x_user_email,
            email=profile.email,
            error=str(error)
        )

        raise HTTPException(
            status_code=409,
            detail="Profile could not be created"
        )

    event = {
        "event": "PROFILE_CREATED",
        "profile_id": created["id"],
        "owner_email": x_user_email,
        "profile": created,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    publish_kafka_event(
        "profiles-events",
        event,
        key=str(created["id"])
    )

    PROFILE_CREATED.inc()

    log_event(
        "INFO",
        "profile_created",
        profile_id=created["id"],
        owner_email=x_user_email,
        email=profile.email
    )

    return created

@app.put("/profiles/{profile_id}")
def update_profile(
    profile_id: int,
    profile: ProfileData,
    x_user_email: str = Header(..., alias="X-User-Email")
):
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                UPDATE profiles
                SET
                    name = %s,
                    email = %s,
                    phone = %s,
                    website = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND owner_email = %s
                RETURNING
                    id,
                    name,
                    email,
                    phone,
                    website,
                    created_at,
                    updated_at
                """,
                (
                    profile.name,
                    profile.email,
                    profile.phone,
                    profile.website,
                    profile_id,
                    x_user_email
                )
            )

            updated = cursor.fetchone()

        conn.commit()

    if not updated:
        log_event(
            "WARNING",
            "profile_not_found",
            profile_id=profile_id,
            owner_email=x_user_email
        )

        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    publish_kafka_event(
        "profiles-events",
        {
            "event": "PROFILE_UPDATED",
            "profile_id": profile_id,
            "owner_email": x_user_email,
            "profile": updated,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        key=str(profile_id)
    )

    PROFILE_UPDATED.inc()

    log_event(
        "INFO",
        "profile_updated",
        profile_id=profile_id,
        owner_email=x_user_email
    )

    return updated

@app.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: int,
    x_user_email: str = Header(..., alias="X-User-Email")
):
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM profiles
                WHERE id = %s
                  AND owner_email = %s
                RETURNING id, name, email
                """,
                (
                    profile_id,
                    x_user_email
                )
            )

            deleted = cursor.fetchone()

        conn.commit()

    if not deleted:
        log_event(
            "WARNING",
            "profile_delete_not_found",
            profile_id=profile_id,
            owner_email=x_user_email
        )

        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    publish_kafka_event(
        "profiles-events",
        {
            "event": "PROFILE_DELETED",
            "profile_id": profile_id,
            "owner_email": x_user_email,
            "profile": deleted,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        key=str(profile_id)
    )

    PROFILE_DELETED.inc()

    log_event(
        "INFO",
        "profile_deleted",
        profile_id=profile_id,
        owner_email=x_user_email
    )

    return {
        "status": "deleted",
        "id": profile_id
    }


