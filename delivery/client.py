"""
Клиент для взаимодействия с внешним API службы доставки СДЭК.

Реализует:
- создание единственного экземпляра клиента (Singleton);
- управление HTTP-сессией через requests.Session;
- получение и обновление OAuth-токена;
- автоматическую проверку срока действия токена;
- формирование заголовков с авторизацией;
- выполнение HTTP-запросов GET, POST, DELETE;
- обработку ошибок API через пользовательские исключения.
"""

from abc import ABC, abstractmethod
import os
import requests
from datetime import timedelta, datetime

from delivery.exceptions import CDEKApiError
from delivery.routes.routes_cdek import OAUTH_TOKEN, HEADERS_GET_TOKEN, HEADERS_API


class BaseDeliveryClient(ABC):

    @abstractmethod
    def get(self, path: str, **kwargs):
        pass

    @abstractmethod
    def post(self, path: str, **kwargs):
        pass

    @abstractmethod
    def delete(self, path: str, **kwargs):
        pass


class CDEKClient(BaseDeliveryClient):
    """
    Клиент API СДЭК.

    Отвечает за:
    - установление подключения к API СДЭК;
    - хранение HTTP-сессии;
    - получение OAuth-токена;
    - обновление токена после истечения срока действия;
    - выполнение запросов к API;
    - обработку HTTP-ошибок через CDEKApiError.
    """
    _instance = None

    def __new__(cls):
        """ __new__ гарантирует, что объект будет создан один раз. """

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        self.client_id = os.environ.get('CDEK_CLIENT_ID')
        self.client_secret = os.environ.get('CDEK_CLIENT_SECRET')
        self.base_url = os.environ.get('CDEK_BASE_URL')

        self.session = requests.Session()

        self._access_token = None
        self._expires_at = None

    def _raise_api_error(self, response):
        response_data = response.json()

        errors = response_data.get("errors", [])
        warnings = response_data.get("warnings", [])

        code = None
        message = None

        if errors:
            code = errors[0].get("code")
            message = errors[0].get("message")

        raise CDEKApiError(
            status_code=response.status_code,
            code=code,
            message=message,
            warnings=warnings,
            response_data=response_data,
        )

    def _authenticate(self):
        """Получает токен доступа и устанавливает его в заголовки."""
        url = f"{self.base_url}{OAUTH_TOKEN}"

        response = self.session.post(
            url=url,
            headers=HEADERS_GET_TOKEN,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        response_data = response.json()

        if response.ok:
            self._access_token = response_data.get("access_token")
            # Чтобы не получить 401, если токен истек в момент отправки запроса
            self._expires_at = datetime.now() + timedelta(seconds=response_data.get("expires_in", 3600) - 30)
            return self._access_token

        self._raise_api_error(response)

    def _ensure_authenticated(self):
        """Проверяет, действителен ли токен, и при необходимости обновляет его."""
        if not self._access_token or datetime.now() >= self._expires_at:
            self._authenticate()

    def _build_headers(self):
        """Создаёт заголовки для запроса, включая токен доступа."""
        self._ensure_authenticated()

        headers = HEADERS_API.copy()
        headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    def get(self, path, params=None):
        """Отправляет GET-запрос."""
        url = f"{self.base_url}{path}"
        response = self.session.get(url, headers=self._build_headers(), params=params)
        # print("\n===== CDEK DEBUG =====")
        # print("URL:", response.url)
        # print("STATUS:", response.status_code)
        # print("HEADERS:", response.headers)
        # print("TEXT:", response.text)
        # print("======================\n")
        response_data = response.json()
        if response.ok:
            return response_data

        self._raise_api_error(response)

    def post(self, path, json=None):
        """Отправляет POST-запрос."""
        url = f"{self.base_url}{path}"
        response = self.session.post(url, headers=self._build_headers(), json=json)
        # print("\n===== CDEK DEBUG =====")
        # print("URL:", response.url)
        # print("STATUS:", response.status_code)
        # print("HEADERS:", response.headers)
        # print("TEXT:", response.text)
        # print("======================\n")
        response_data = response.json()
        if response.ok:
            return response_data

        self._raise_api_error(response)

    def delete(self, path, params=None):
        """Отправляет DELETE-запрос."""
        url = f"{self.base_url}{path}"
        response = self.session.delete(url, headers=self._build_headers(), params=params)
        response_data = response.json()
        if response.ok:
            return response_data

        self._raise_api_error(response)
