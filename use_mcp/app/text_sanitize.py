# Среда выполнения (Linux-терминал) чувствительна к некорректным байтам UTF-8 в тексте сообщений.
# Модуль устраняет невалидные последовательности до передачи в API и в чекпоинты, чтобы избежать ошибок сериализации.

from typing import Any


def sanitize_text(text: str) -> str:
    """Удаляет из строки байты, не являющиеся валидным UTF-8 (чтобы не ломать API и чекпоинты)."""
    if not isinstance(text, str):
        return text
    return text.encode("utf-8", errors="ignore").decode("utf-8")


def sanitize_message_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Очищает поля content во всех сообщениях payload — для безопасной передачи в модель и в память агента."""
    cleaned = dict(payload)

    messages = cleaned.get("messages")
    if isinstance(messages, list):
        new_messages = []
        for message in messages:
            if isinstance(message, dict):
                new_message = dict(message)
                content = new_message.get("content")
                if isinstance(content, str):
                    new_message["content"] = sanitize_text(content)
                new_messages.append(new_message)
            else:
                new_messages.append(message)
        cleaned["messages"] = new_messages

    return cleaned
