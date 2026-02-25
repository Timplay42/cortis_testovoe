import json
import logging
from datetime import datetime
from pathlib import Path

import requests

API_URL = "http://127.0.0.1:5000/client"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Token",
}
TIMEOUT_SECONDS = 10

SOURCE_CLIENTS_FILE = Path(__file__).resolve().parent.parent / "clientList"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def split_fio(fio: str) -> tuple[str, str, str]:
    parts = fio.split()
    if len(parts) < 3:
        raise ValueError(f"Не удалось разделить ФИО на 3 части: '{fio}'")
    return parts[0], parts[1], " ".join(parts[2:])


def ddmmyyyy_to_iso(date_value: str) -> str:
    dt = datetime.strptime(date_value, "%d.%m.%Y")
    return dt.strftime("%Y-%m-%dT11:16:32")


def load_first_active_patient() -> dict:
    with SOURCE_CLIENTS_FILE.open("r", encoding="utf-8") as file:
        patients = json.load(file)

    for patient in patients:
        if patient.get("deleted", 0) != 1:
            return patient

    raise RuntimeError("В clientList нет пациентов с deleted != 1")


def log_response_readable(response_obj: dict) -> None:
    logger.info("Ответ сервера:")
    logger.info("  status:  %s", response_obj.get("status"))
    logger.info("  code:    %s", response_obj.get("code"))
    logger.info("  message: %s", response_obj.get("message"))

    data = response_obj.get("data")
    if data is None:
        logger.info("  data:    <отсутствует>")
        return

    logger.info("  data:")
    logger.info("    id:  %s", data.get("id"))
    logger.info("    FIO: %s", data.get("FIO"))
    logger.info("    age: %s", data.get("age"))


def main() -> None:
    patient = load_first_active_patient()
    last_name, first_name, patr_name = split_fio(patient["fio"])

    payload = {
        "lastName": last_name,
        "firstName": first_name,
        "patrName": patr_name,
        "birthDate": ddmmyyyy_to_iso(patient["birth_date"]),
        "status": True,
    }

    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        logger.error("Ошибка: превышено время ожидания ответа от сервера")
        return
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка: не удалось подключиться к серверу")
        return
    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка запроса: %s", exc)
        return

    if response.status_code not in (200, 201):
        logger.warning("Неожиданный статус-код: %s", response.status_code)

    try:
        response_json = response.json()
    except ValueError:
        logger.error("Ошибка: сервер вернул невалидный JSON")
        logger.error("Текст ответа: %s", response.text)
        return

    log_response_readable(response_json)


if __name__ == "__main__":
    main()
