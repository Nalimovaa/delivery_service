from confluent_kafka import Consumer


import json

from django.conf import settings

from delivery.kafka.topics import KafkaTopic
from delivery.tasks.order import check_cdek_order_status, check_cdek_order_deletion


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
            KafkaTopic.CDEK_ORDER_DELETE_ACCEPTED,
        ])

    def run(self):
        print("KAFKA CONSUMER STARTED")

        while True:
            message = self.consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                print("KAFKA ERROR:", message.error())
                continue

            data = json.loads(
                message.value().decode("utf-8")
            )

            print("DATA:", data)

            if message.topic() == KafkaTopic.CDEK_ORDER_ACCEPTED:
                check_cdek_order_status.apply_async(
                    args=[
                        data["cdek_delivery_id"],
                    ],
                    countdown=30,
                )

            elif (
                    message.topic()
                    == KafkaTopic.CDEK_ORDER_DELETE_ACCEPTED
            ):
                check_cdek_order_deletion.apply_async(
                    args=[
                        data["cdek_delivery_id"],
                    ],
                    countdown=30,
                )