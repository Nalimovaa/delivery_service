from confluent_kafka import Consumer


import json

from django.conf import settings

from delivery.kafka.topics import KafkaTopic
from delivery.tasks.order import check_cdek_order_status


class KafkaConsumer:

    def __init__(self):
        self.consumer = Consumer({
            "bootstrap.servers": (
                f"{settings.KAFKA_HOST}:{settings.KAFKA_PORT}"
            ),
            "group.id": "delivery-service",
            "auto.offset.reset": "earliest",
        })

        self.consumer.subscribe([
            KafkaTopic.CDEK_ORDER_ACCEPTED,
        ])

    def run(self):
        print("KAFKA CONSUMER STARTED")

        while True:
            message = self.consumer.poll(1.0)

            if message is None:
                continue

            print("MESSAGE RECEIVED")

            if message.error():
                print("KAFKA ERROR:", message.error())
                continue

            data = json.loads(
                message.value().decode("utf-8")
            )
            print("DATA:", data)

            check_cdek_order_status.apply_async(
                args=[
                    data["cdek_delivery_id"],
                ],
                countdown=30,
            )
            print("CELERY TASK SENT")