# Модуль для middleware функций агента.
# Содержит middleware для управления контекстом модели:
# inject_db_schema (добавление схемы БД), plan_apply_tools (управление инструментами),
# и middleware для Human-in-the-Loop (HumanInTheLoopMiddleware).
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
)
from typing import Callable
from langchain_core.messages import SystemMessage

DB_SCHEMA_TEXT = """
Ты работаешь с базой данных SQLite с одной таблицей tasks.

Структура таблицы tasks:
- id: INTEGER PRIMARY KEY AUTOINCREMENT — уникальный идентификатор задачи.
- title: TEXT — краткое название задачи.
- status: TEXT — строка со статусом, одно из значений: "todo", "in_progress", "done".
- priority: INTEGER — приоритет задачи, целое число (чем больше, тем важнее).
- due_date: TEXT или NULL — дата дедлайна в формате YYYY-MM-DD, либо отсутствие дедлайна.

Всегда считай, что реальные данные задач находятся в этой таблице, и любые операции
с задачами нужно выполнять через инструменты (add_task, list_tasks, update_task_status, delete_task).
Не выдумывай задачи, которых нет в базе.
""".strip()


@wrap_model_call
def inject_db_schema(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """На каждый вызов модели подмешивает описание схемы БД как системное сообщение."""
    schema_message = SystemMessage(DB_SCHEMA_TEXT)
    new_messages = [schema_message, *request.messages]

    print("\\n=== MESSAGES, которые пойдут в LLM (со схемой БД) ===")
    for i, m in enumerate(new_messages):
        print(f"{i}. {type(m)}: {str(m.content)[:80]!r}")

    new_request = request.override(messages=new_messages)
    return handler(new_request)


@wrap_model_call
def plan_apply_tools(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Динамически меняет список доступных тулов в зависимости от режима.

    - В режиме 'plan' оставляем только list_tasks.
    - В режиме 'apply' оставляем все тулы.

    Плюс подмешиваем короткое системное сообщение с пояснением режима.
    """
    ctx = getattr(request.runtime, "context", None)
    mode = getattr(ctx, "mode", "apply") if ctx is not None else "apply"

    tools = request.tools
    messages = list(request.messages)

    if mode == "plan":
        # только чтение — оставляем один тул list_tasks
        allowed_names = {"list_tasks"}
        tools = [t for t in tools if t.name in allowed_names]

        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Сейчас ты работаешь в режиме ПЛАНИРОВАНИЯ (plan).\\n"
                    "Ты НЕ должен изменять данные в БД. Не вызывай инструменты "
                    "для добавления, обновления или удаления задач.\\n"
                    "Используй list_tasks, чтобы посмотреть текущие задачи, "
                    "и давай рекомендации в текстовом виде."
                ),
            },
        )
    else:
        messages.insert(
            0,
            {
                "role": "system",
                "content": (
                    "Сейчас ты работаешь в режиме ПРИМЕНЕНИЯ (apply).\\n"
                    "Ты можешь вызывать инструменты add_task, update_task_status "
                    "и delete_task, если это логично по запросу пользователя.\\n"
                    "Если ранее был согласован план, следуй ему."
                ),
            },
        )

    new_request = request.override(messages=messages, tools=tools)
    return handler(new_request)
