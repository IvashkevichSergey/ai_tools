# Агент 03: ReAct-агент со структурированным выводом (Structured Output).
# Демонстрирует Model Context: агент возвращает ответ в строго определённом JSON-формате
# согласно Pydantic-схеме, что гарантирует корректность и валидацию данных.


import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из demo_env.env
PROJECT_DIR = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_DIR / "config" / "demo_env.env")

# LangChain: основные компоненты для работы с LLM и агентами
from langchain_gigachat import GigaChat
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# Инструменты для работы с базой данных задач
from source.tools import add_task, list_tasks, update_task_status, delete_task

# TaskAgentResponse: Pydantic-модель для структурированного ответа агента
# Новый импорт на шаге 8: гарантирует, что агент вернёт данные в виде валидного JSON
# с полями explanation (текстовое объяснение) и tasks (список задач)
from source.context import TaskAgentResponse

# Код инициализации модели и создания агента добавляется на шаге 8
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2"),
    verify_ssl_certs=False,
    temperature=0.1,
)

checkpointer = InMemorySaver()

agent_structured = create_agent(
    model=llm,
    tools=[add_task, list_tasks, update_task_status, delete_task],
    response_format=TaskAgentResponse,  # ключевое отличие
    checkpointer=checkpointer,
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "tasks-structured-demo"}}

    res = agent_structured.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Добавь задачу 'Сделать бэкап БД' со статусом todo и приоритетом 4, "
                        "а затем выведи список задач."
                    ),
                }
            ]
        },
        config,
    )

    print("=== Сообщения (как обычно) ===")
    for m in res["messages"]:
        m.pretty_print()


