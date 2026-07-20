"""
python manage.py test delivery.tests.test_client
"""

from django.test import TestCase

from delivery.client import CDEKClient


class CDEKClientTest(TestCase):

    def test_singleton(self):
        client1 = CDEKClient()
        client2 = CDEKClient()

        self.assertIs(client1, client2)

    def test_authenticate(self):
        client = CDEKClient()

        token = client._authenticate()

        self.assertIsNotNone(token)
        self.assertIsNotNone(client._access_token)
        self.assertIsNotNone(client._expires_at)