import re


def normalize_phone(value: str) -> str:
    phone = re.sub(r"[\s\-()]", "", value)

    if phone.startswith("8"):
        phone = "+7" + phone[1:]
    elif phone.startswith("7"):
        phone = "+" + phone

    if not re.fullmatch(r"\+7\d{10}", phone):
        raise ValueError(
            "Введите корректный российский номер телефона."
        )

    return phone
