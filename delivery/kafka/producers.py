import json
import logging

from confluent_kafka import Producer

from django.conf import settings


logger = logging.getLogger(__name__)


class KafkaProducer:

    def __init__(self):
        self.producer = Producer(
            {
                "bootstrap.servers": (
                    f"{settings.KAFKA_HOST}:{settings.KAFKA_PORT}"
                ),
            }
        )

    def send(
        self,
        *,
        topic: str,
        message: dict,
    ) -> None:
        try:
            self.producer.produce(
                topic,
                json.dumps(
                    message,
                    ensure_ascii=False,
                ).encode("utf-8"),
            )
            self.producer.flush()

        except Exception:
            logger.exception(
                "Failed to send message to Kafka. "
                "topic=%s message=%s",
                topic,
                message,
            )
            raise