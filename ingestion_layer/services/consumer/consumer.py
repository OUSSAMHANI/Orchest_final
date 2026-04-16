import asyncio
import json
import logging
import os
import uuid
from datetime import datetime

import httpx
from aiokafka import AIOKafkaConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("consumer")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = "events.normalized"
GROUP_ID = "orchestrator-consumer"

ORCHESTRATOR_URL = os.getenv(
    "ORCHESTRATOR_URL",
    "http://orchestrator-api:8000/ticket/sync",
)

TRACKED_ACTIONS = {"open", "update"}


async def create_consumer():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    for attempt in range(10):
        try:
            await consumer.start()
            logger.info("Connected to Kafka")
            return consumer
        except Exception as e:
            logger.warning(f"Kafka not ready ({attempt+1}/10): {e}")
            await asyncio.sleep(5)

    raise RuntimeError("Kafka unavailable")


def build_payload(event: dict) -> dict:
    issue_id = event.get("issue_id")
    namespace = event.get("path_with_namespace")

    workspace_path = None
    if namespace:
        workspace_path = f"/workspaces/ticket-{issue_id}"

    return {
        "event_id": str(uuid.uuid4()),
        "issue_id": issue_id,
        "project": event.get("project"),
        "title": event.get("title", ""),
        "intent": event.get("intent") or "fix",
        "scope": event.get("scope"),
        "summary": event.get("summary") or event.get("title", "")[:100],
        "description": event.get("description", ""),
        "context": event.get("context"),
        "acceptance_criteria": event.get("acceptance_criteria", []),
        "constraints": event.get("constraints"),
        "non_goals": event.get("non_goals"),
        "priority": event.get("priority") or "normal",
        "hinted_scope": event.get("hinted_scope", []),
        "depends_on": event.get("depends_on", []),
        "branch": event.get("branch"),
        "routing_key": event.get(
            "routing_key",
            f"{event.get('intent','fix')}.{event.get('priority','normal')}.{event.get('action')}",
        ),
        "action": event.get("action"),
        "labels": event.get("labels", []),
        "author": event.get("author"),
        "url": event.get("url"),
        "created_at": datetime.utcnow().isoformat(),
        "received_at": datetime.utcnow().isoformat(),
        "updated_at": event.get("updated_at"),
        "workspace_path": workspace_path,
    }


async def process_message(client: httpx.AsyncClient, event: dict):
    issue_id = event.get("issue_id")
    action = event.get("action")

    if action not in TRACKED_ACTIONS:
        logger.info(f"Skipping #{issue_id} action={action}")
        return

    payload = build_payload(event)

    try:
        resp = await client.post(ORCHESTRATOR_URL, json=payload)
        resp.raise_for_status()

        data = resp.json()
        logger.info(f"Queued ticket_id={data.get('ticket_id')} (issue #{issue_id})")

    except httpx.HTTPStatusError as e:
        logger.error(f"Orchestrator rejected #{issue_id}: {e.response.text}")

    except httpx.RequestError as e:
        logger.error(f"Network error for #{issue_id}: {e}")


async def consume():
    consumer = await create_consumer()

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            async for msg in consumer:
                asyncio.create_task(process_message(client, msg.value))

        finally:
            await consumer.stop()
            logger.info("Consumer stopped")


if __name__ == "__main__":
    asyncio.run(consume())