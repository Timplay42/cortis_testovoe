import json
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_FILE = Path(__file__).resolve().parent / "api_clients.json"
EXPECTED_TOKEN = "Token"
REQUIRED_FIELDS = ["lastName", "firstName", "patrName", "birthDate", "status"]


def load_storage() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_storage(payload: list[dict[str, Any]]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


def parse_birth_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def calc_age(birth_dt: datetime) -> int:
    now = datetime.now()
    years = now.year - birth_dt.year
    if (now.month, now.day) < (birth_dt.month, birth_dt.day):
        years -= 1
    return max(years, 0)


def build_error(message: str, code: int):
    return (
        jsonify(
            {
                "status": "error",
                "code": code,
                "message": message,
            }
        ),
        code,
    )


@app.route("/client", methods=["POST"])
def create_or_update_client():
    auth_header = request.headers.get("Authorization", "")
    if auth_header != EXPECTED_TOKEN:
        return build_error("Неверный токен авторизации", 401)

    if not request.is_json:
        return build_error("Content-Type должен быть application/json", 400)

    client_data = request.get_json(silent=True)
    if not isinstance(client_data, dict):
        return build_error("Невалидный JSON", 400)

    missing_fields = [field for field in REQUIRED_FIELDS if field not in client_data]
    if missing_fields:
        return build_error(f"Отсутствуют поля: {', '.join(missing_fields)}", 400)

    last_name = client_data.get("lastName")
    first_name = client_data.get("firstName")
    patr_name = client_data.get("patrName")
    birth_date = client_data.get("birthDate")
    status = client_data.get("status")

    if not all(isinstance(v, str) and v.strip() for v in [last_name, first_name, patr_name, birth_date]):
        return build_error("Поля ФИО и birthDate должны быть непустыми строками", 400)

    if not isinstance(status, bool):
        return build_error("Поле status должно быть bool", 400)

    try:
        birth_dt = parse_birth_date(birth_date)
    except ValueError:
        return build_error("Неверный формат birthDate. Используйте YYYY-MM-DDTHH:MM:SS", 400)

    fio = f"{last_name} {first_name} {patr_name}".strip()

    storage = load_storage()
    existing_idx = next(
        (
            idx
            for idx, item in enumerate(storage)
            if item.get("lastName") == last_name
            and item.get("firstName") == first_name
            and item.get("patrName") == patr_name
            and item.get("birthDate") == birth_date
        ),
        None,
    )

    if existing_idx is None:
        entity = {
            "id": f"usr_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "lastName": last_name,
            "firstName": first_name,
            "patrName": patr_name,
            "birthDate": birth_date,
            "status": status,
            "FIO": fio,
            "age": calc_age(birth_dt),
        }
        storage.append(entity)
        save_storage(storage)

        return (
            jsonify(
                {
                    "status": "success",
                    "code": 201,
                    "message": "Данные успешно обработаны",
                    "data": {
                        "id": entity["id"],
                        "FIO": entity["FIO"],
                        "age": entity["age"],
                    },
                }
            ),
            201,
        )

    storage[existing_idx]["status"] = status
    save_storage(storage)

    entity = storage[existing_idx]
    return (
        jsonify(
            {
                "status": "success",
                "code": 200,
                "message": "Данные успешно обработаны",
                "data": {
                    "id": entity["id"],
                    "FIO": entity["FIO"],
                    "age": entity["age"],
                },
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
