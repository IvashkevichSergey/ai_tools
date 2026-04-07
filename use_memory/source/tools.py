# Инструменты работают с долгосрочной памятью пользователя через runtime.store.

from dataclasses import dataclass

from langchain.tools import ToolRuntime, tool


# Контекст хранит идентификатор пользователя, который передаётся при вызове агента.
@dataclass
class UserContext:
    user_id: str


# Возвращаем сохранённые сведения о пользователе из long-term memory.
@tool
def get_user_info(runtime: ToolRuntime[UserContext]) -> dict:
    """Вернуть сохранённые сведения о пользователе из long-term memory."""

    store = runtime.store
    user_id = runtime.context.user_id

    if store is None:
        return {
            "status": "error",
            "message": "Хранилище long-term memory не настроено.",
        }

    user_info = store.get(("users",), user_id)
    if user_info is None:
        return {
            "status": "not_found",
            "message": "Сведения о пользователе пока не сохранены.",
        }

    return {
        "status": "ok",
        **user_info.value,
    }


# Сохраняем сведения о пользователе в long-term memory.
@tool
def save_user_info(
    name: str,
    preferred_segment: str,
    preferred_term_months: int,
    runtime: ToolRuntime[UserContext],
) -> dict:
    """Сохранить сведения о пользователе в long-term memory."""
    store = runtime.store
    user_id = runtime.context.user_id

    if store is None:
        return {
            "status": "error",
            "message": "Хранилище long-term memory не настроено.",
        }

    user_info = {
        "name": name,
        "preferred_segment": preferred_segment,
        "preferred_term_months": preferred_term_months,
    }
    store.put(("users",), user_id, user_info)

    return {
        "status": "ok",
        "message": "Сведения о пользователе сохранены.",
        **user_info,
    }

