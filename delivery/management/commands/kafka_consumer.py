from django.core.management.base import BaseCommand

from delivery.kafka.consumers import KafkaConsumer


class Command(BaseCommand):
    help = "Run Kafka consumer"

    def handle(self, *args, **options):
        consumer = KafkaConsumer()
        consumer.run()