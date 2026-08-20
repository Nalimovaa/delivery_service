"""
Модуль с константами маршрутов внешнего API CDEK.
"""

BASE_URL_TEST = "https://api.edu.cdek.ru/v2"
BASE_URL_PROD = "https://api.cdek.ru/v2"

OAUTH_TOKEN = "/oauth/token"

HEADERS_GET_TOKEN = {
    "Content-Type": "application/x-www-form-urlencoded"
}

HEADERS_API = {
    "Content-Type": "application/json",
}

CALCULATOR_TARIFF = "/calculator/tariff"
CALCULATOR_TARIFF_LIST = "/calculator/tariffAndService"
CALCULATOR_ALL_TARIFFS = "/calculator/alltariffs"

DELIVERY_POINTS = "/deliverypoints"

ORDERS = "/orders"
ORDER = "/orders/{uuid}"
CITIES_SUGGEST = "/location/suggest/cities"

ORDER_CLIENT_RETURN = "/orders/{uuid}/clientReturn"
ORDER_REFUSAL = "/orders/{uuid}/refusal"

CDEK_CITIES = "/location/cities"