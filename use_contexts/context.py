# Модуль для классов контекста и структурированных данных.
# Содержит AgentContext (режимы работы агента), UserContext (данные пользователя)
# и Pydantic-модели для структурированного ответа (TaskInfo, TaskAgentResponse).

from dataclasses import dataclass

from pydantic import BaseModel, Field
from typing import List, Literal


@dataclass
class AgentContext:
    """Контекст агента.

    mode:
        "plan"  — режим планирования (не менять БД).
        "apply" — режим применения (можно менять БД).
    """
    mode: str = "apply"


class TaskInfo(BaseModel):
    """Сведение по одной задаче из БД после шага агента."""
    id: int = Field(description="ID задачи из таблицы tasks")
    title: str = Field(description="Название задачи")
    status: Literal["todo", "in_progress", "done"] = Field(
        description="Текущий статус задачи"
    )
    priority: int = Field(description="Приоритет задачи (чем больше, тем важнее)")
    due_date: str = Field(
        description="Дедлайн в формате YYYY-MM-DD или пустая строка, если дедлайн не задан"
    )


class TaskAgentResponse(BaseModel):
    """Структурированный ответ агента по задачам."""
    explanation: str = Field(
        description="Краткое человеческое объяснение того, что сделал агент"
    )
    tasks: List[TaskInfo] = Field(
        description="Список задач после выполнения запроса пользователя"
    )


@dataclass
class Context:
    user_id: str

