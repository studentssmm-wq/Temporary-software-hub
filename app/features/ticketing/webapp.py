import os
from urllib.parse import urlencode
from app.features.ticketing.logic import BookingError


def venue_url(venue_type, **query):
    setting = {"organ_hall":"WEB_APP_URL_ORGAN_HALL", "assembly_hall":"WEB_APP_URL_ASSEMBLY_HALL", "opera_house":"WEB_APP_URL_OPERA_HOUSE"}.get(venue_type)
    url = os.getenv(setting, "") if setting else ""
    if not url or not url.startswith("https://"):
        raise BookingError("Організатор ще не налаштував HTTPS-адресу схеми цього залу")
    return url.rstrip("/") + "/?" + urlencode(query)


def use_inline_picker():
    from app.core.config import IS_DEVELOPMENT
    return IS_DEVELOPMENT
