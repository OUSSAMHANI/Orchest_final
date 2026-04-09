"""
Kafka Consumer
Listens for incoming tickets from Kafka and triggers the orchestrator.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from kafka import KafkaConsumer
from kafka.errors import KafkaError, NoBrokersAvailable

from ..graph.builder import run_orchestrator


logger = logging.getLogger(__name__)


# =========================
# SIMPLE KAFKA CONSUMER
# =========================

class OrchestratorConsumer:
    """
    Kafka consumer for receiving tickets.
    Runs in background thread and calls orchestrator.
    """
    
    def __init__(
        self,
        bootstrap_servers: List[str],
        topic: str = "gitlab-tickets",
        consumer_group: str = "orchestrator-group",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.consumer_group = consumer_group
        self.consumer: Optional[KafkaConsumer] = None
        self._running = False
    
    def start(self) -> None:
        """Start consuming messages."""
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            )
            self._running = True
            logger.info(f"Consumer started on topic: {self.topic}")
            self._consume()
        except NoBrokersAvailable:
            logger.error(f"No Kafka brokers at {self.bootstrap_servers}")
            raise
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            raise
    
    def _consume(self) -> None:
        """Main consume loop."""
        for message in self.consumer:
            if not self._running:
                break
            
            try:
                ticket_data = message.value
                logger.info(f"Received ticket: {ticket_data.get('event_id', 'unknown')}")
                
                # Run orchestrator
                result = run_orchestrator(ticket_data)
                
                logger.info(f"Orchestrator result: {result.get('status')}")
                
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
    
    def stop(self) -> None:
        """Stop consumer."""
        self._running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer stopped")


# =========================
# CONVENIENCE FUNCTION
# =========================

def start_kafka_consumer(
    bootstrap_servers: List[str],
    topic: str = "gitlab-tickets",
    consumer_group: str = "orchestrator-group",
) -> OrchestratorConsumer:
    """
    Start Kafka consumer with given configuration.
    """
    consumer = OrchestratorConsumer(
        bootstrap_servers=bootstrap_servers,
        topic=topic,
        consumer_group=consumer_group,
    )
    consumer.start()
    return consumer