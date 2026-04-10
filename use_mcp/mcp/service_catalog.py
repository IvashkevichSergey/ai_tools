# Учебный каталог сервисных пакетов и операции, которые выполняет MCP-сервис.
# Агент не импортирует этот модуль напрямую: он доступен только на стороне MCP.

import json
from functools import lru_cache
from pathlib import Path


# Храним путь к локальному JSON-каталогу и состояние заявок в памяти процесса.
CATALOG_FILE = Path(__file__).with_name("service_catalog.json")
REQUESTS: dict[str, dict] = {}

# Задаем правила рекомендации пакета по профилю обслуживания клиента.
PROFILE_RECOMMENDATIONS = {
    "retail_basic": {
        "package_code": "family_plus",
        "reason": "соответствует сценарию контроля семейных расходов и регулярных платежей.",
    },
    "retail_priority": {
        "package_code": "family_plus",
        "reason": "соответствует премиальному клиенту с приоритетным профилем обслуживания.",
    },
    "retail_start": {
        "package_code": "student_plus",
        "reason": "соответствует стартовому профилю молодого клиента и не требует ежемесячной платы.",
    },
}


# Декоратор lru_cache оставляет каталог в памяти процесса после первого чтения файла.
@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    """Загружает учебный каталог сервисных пакетов из локального JSON-файла."""
    # Читаем JSON-каталог один раз за процесс, чтобы не открывать файл на каждом вызове MCP-инструмента.
    with CATALOG_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _require_client(client_id: str) -> dict:
    """Возвращает карточку клиента или поднимает ошибку, если клиента нет в каталоге."""
    # Проверяем, что клиент существует в учебном каталоге.
    client = _load_catalog()["clients"].get(client_id)
    if client is None:
        raise ValueError(f"Клиент не найден: {client_id}")
    return client


def _require_package(package_code: str) -> dict:
    """Возвращает карточку пакета или поднимает ошибку, если пакет не найден."""
    # Проверяем, что запрошенный пакет есть в каталоге сервисов.
    service_package = _load_catalog()["service_packages"].get(package_code)
    if service_package is None:
        raise ValueError(f"Сервисный пакет не найден: {package_code}")
    return service_package


def _build_package_summary(service_package: dict) -> dict:
    """Собирает краткую карточку пакета для ответа MCP-сервиса."""
    # Формируем компактное представление пакета для инструментального сценария.
    return {
        "package_code": service_package["package_code"],
        "name": service_package["name"],
        "monthly_fee": service_package["monthly_fee"],
    }


def _pick_recommended_package(client: dict, available_packages: list[dict]) -> dict | None:
    """Возвращает рекомендованный пакет для service_profile, если он доступен клиенту."""
    # Сначала ищем рекомендацию, заданную для профиля обслуживания.
    recommendation = PROFILE_RECOMMENDATIONS.get(client["service_profile"])
    if recommendation is not None:
        for service_package in available_packages:
            if service_package["package_code"] == recommendation["package_code"]:
                recommended_package = _build_package_summary(service_package)
                recommended_package["recommendation_reason"] = recommendation["reason"]
                return recommended_package

    # Если рекомендация не задана, выбираем первый доступный пакет как резервный вариант.
    if not available_packages:
        return None

    recommended_package = _build_package_summary(available_packages[0])
    recommended_package["recommendation_reason"] = "это первый доступный пакет из каталога."
    return recommended_package


def get_available_packages(client_id: str) -> dict:
    """Подбирает для клиента список доступных пакетов и явную рекомендацию сервиса."""
    # Отбираем только те пакеты, которые подходят клиенту по сегменту и ещё не подключены.
    client = _require_client(client_id)
    available_service_packages = []

    # Проходим по учебному каталогу и оставляем только релевантные варианты.
    for service_package in _load_catalog()["service_packages"].values():
        if client["segment"] not in service_package["segments"]:
            continue
        if service_package["package_code"] in client["active_packages"]:
            continue
        available_service_packages.append(service_package)

    # Определяем рекомендованный пакет на стороне MCP-сервиса.
    recommended_package = _pick_recommended_package(client, available_service_packages)
    recommended_code = recommended_package["package_code"] if recommended_package else None

    # Возвращаем полный список пакетов, размещая рекомендованный вариант первым.
    available_packages = [
        _build_package_summary(service_package)
        for service_package in sorted(
            available_service_packages,
            key=lambda service_package: (
                service_package["package_code"] != recommended_code,
                service_package["monthly_fee"],
                service_package["name"],
            ),
        )
    ]

    return {
        "client_id": client_id,
        "segment": client["segment"],
        "service_profile": client["service_profile"],
        "recommended_package": recommended_package,
        "available_packages": available_packages,
    }


def get_package_details(package_code: str) -> dict:
    """Возвращает полную карточку конкретного сервисного пакета."""
    # Возвращаем полную карточку пакета без дополнительной обработки.
    return _require_package(package_code)


def create_package_request(client_id: str, package_code: str, comment: str) -> dict:
    """Создаёт учебную заявку на подключение сервисного пакета."""
    # Создаём учебную заявку и сохраняем её в памяти процесса MCP-сервиса.
    _require_client(client_id)
    service_package = _require_package(package_code)

    # Формируем идентификатор и сохраняем заявку в памяти процесса MCP-сервиса.
    request_id = f"request_{len(REQUESTS) + 1:03d}"
    REQUESTS[request_id] = {
        "request_id": request_id,
        "client_id": client_id,
        "package_code": package_code,
        "package_name": service_package["name"],
        "comment": comment,
        "status": "created",
        "status_label": "создана",
    }
    return REQUESTS[request_id]


def get_package_request_status(request_id: str) -> dict:
    """Возвращает текущее состояние ранее созданной учебной заявки."""
    # Ищем ранее созданную заявку по её идентификатору.
    request = REQUESTS.get(request_id)
    if request is None:
        raise ValueError(f"Заявка не найдена: {request_id}")
    return request
