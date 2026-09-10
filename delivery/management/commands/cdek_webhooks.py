"""
1. Подписаться:
python manage.py cdek_webhooks --subscribe --url=https://example.com/api/delivery/webhooks/cdek/order-status/
2. Проверить существующие подписки:
python manage.py cdek_webhooks --list
3. Получить конкретную подписку по UUID:
python manage.py cdek_webhooks --get --uuid=<UUID>
4. Удалить подписку по UUID:
python manage.py cdek_webhooks --delete --uuid=<UUID>
"""

from django.core.management.base import BaseCommand, CommandError
from delivery.adapters.cdek import CDEKAdapter


class Command(BaseCommand):
    help = "Manage CDEK webhook subscriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--subscribe",
            action="store_true",
            help="Subscribe to ORDER_STATUS webhooks.",
        )

        parser.add_argument(
            "--list",
            action="store_true",
            help="List all CDEK webhook subscriptions.",
        )

        parser.add_argument(
            "--get",
            action="store_true",
            help="Get webhook subscription by UUID.",
        )

        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete webhook subscription by UUID.",
        )

        parser.add_argument(
            "--url",
            type=str,
            help="Public URL for CDEK webhook.",
        )

        parser.add_argument(
            "--uuid",
            type=str,
            help="Webhook subscription UUID.",
        )

    def handle(self, *args, **options):

        adapter = CDEKAdapter()

        if options["subscribe"]:
            self.subscribe(
                adapter=adapter,
                url=options.get("url"),
            )
            return

        if options["list"]:
            self.list_webhooks(adapter)
            return

        if options["get"]:
            self.get_webhook(
                adapter=adapter,
                uuid=options.get("uuid"),
            )
            return

        if options["delete"]:
            self.delete_webhook(
                adapter=adapter,
                uuid=options.get("uuid"),
            )
            return

        raise CommandError(
            "Укажите одну из операций: "
            "--subscribe, --list, --get или --delete."
        )

    def subscribe(
        self,
        *,
        adapter: CDEKAdapter,
        url: str | None,
    ):
        if not url:
            raise CommandError(
                "--url обязателен для --subscribe."
            )

        self.stdout.write(
            f"Подписка на ORDER_STATUS: {url}"
        )

        response = adapter.subscribe_to_order_status_webhook(
            url=url,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Подписка создана: {response}"
            )
        )

    def list_webhooks(
        self,
        adapter: CDEKAdapter,
    ):
        webhooks = adapter.get_all_webhooks()

        if not webhooks:
            self.stdout.write(
                "Активных подписок нет."
            )
            return

        for webhook in webhooks:
            self.stdout.write(
                f"UUID: {webhook.uuid}\n"
                f"Type: {webhook.type}\n"
                f"URL: {webhook.url}\n"
            )

    def get_webhook(
        self,
        *,
        adapter: CDEKAdapter,
        uuid: str | None,
    ):
        if not uuid:
            raise CommandError(
                "--uuid обязателен для --get."
            )

        response = adapter.get_webhook(
            uuid=uuid,
        )

        self.stdout.write(
            str(response)
        )

    def delete_webhook(
        self,
        *,
        adapter: CDEKAdapter,
        uuid: str | None,
    ):
        if not uuid:
            raise CommandError(
                "--uuid обязателен для --delete."
            )

        response = adapter.delete_webhook(
            uuid=uuid,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Подписка удалена: {response}"
            )
        )

