# Агент 01: Базовый ReAct-агент с инструментами управления задачами.
# Демонстрирует основы работы агента: вызов инструментов, сохранение состояния через checkpointer.


import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из demo_env.env
PROJECT_DIR = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_DIR / "config" / "demo_env.env")

# LangChain: основные компоненты для работы с LLM и агентами
from langchain_gigachat import GigaChat  # Модель GigaChat для генерации
from langchain.agents import create_agent  # Функция создания ReAct-агента
from langgraph.checkpoint.memory import InMemorySaver  # Сохранение состояния диалога в памяти

# Инструменты для работы с базой данных задач
from source.tools import add_task, list_tasks, update_task_status, delete_task
from source.middleware import inject_db_schema

# Базовая модель без middleware
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2"),
    verify_ssl_certs=False,
    temperature=0.1,
)

checkpointer = InMemorySaver()

agent = create_agent(
    model=llm,
    tools=[add_task, list_tasks, update_task_status, delete_task],
    middleware=[inject_db_schema],  # добавляем middleware
    checkpointer=checkpointer,
)

config_tasks = {"configurable": {"thread_id": "tasks-demo"}}

# Код инициализации модели и создания агента добавляется на шаге 4
if __name__ == "__main__":
    res = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "У тебя есть инструменты для работы с базой задач. "
                        "Сделай следующее:\\n"
                        "1) Добавь три задачи:\\n"
                        "   - 'Подготовить отчёт по продажам за квартал' со статусом in_progress, приоритет 5, дедлайн 2025-12-01.\\n"
                        "   - 'Позвонить клиенту по продлению контракта' со статусом todo, приоритет 4, без дедлайна.\\n"
                        "   - 'Разобрать почту' со статусом todo, приоритет 1, без дедлайна.\\n"
                        "2) После этого выведи список всех задач из базы.\\n"
                        "Пожалуйста, сначала вызови нужные инструменты, а в финальном ответе "
                        "дай понятное резюме того, что ты сделал, и список задач."
                    ),
                }
            ]
        },
        config_tasks,
    )

    for msg in res["messages"]:
        msg.pretty_print()



