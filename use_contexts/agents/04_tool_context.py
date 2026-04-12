# Агент 04: ReAct-агент с Tool Context (передача скрытых параметров в инструменты).
# Демонстрирует Tool Context: инструменты получают доступ к дополнительным данным
# (user_id, роли, настройки из store) через ToolRuntime, без раскрытия этой информации модели.


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

# InMemoryStore: хранилище для долгосрочной памяти агента
# Новый импорт на шаге 9: позволяет сохранять настройки пользователей (роли, режимы)
# и передавать их в инструменты через runtime.store
from langgraph.store.memory import InMemoryStore

# Инструменты для работы с базой данных задач
from source.tools import add_task, list_tasks, update_task_status, delete_task

# Context: dataclass с user_id для передачи идентификатора пользователя
# Новый импорт на шаге 9: позволяет передавать контекст пользователя при вызове агента
from source.context import Context

# Код инициализации модели, создания store и агента добавляется на шаге 9
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2"),
    verify_ssl_certs=False,
    temperature=0.1,
)

# Создаём хранилище для данных пользователей
store = InMemoryStore()

# Создаём двух пользователей с разными правами
store.put(
    ("agent_settings",),  # namespace
    "user_123",  # key
    {"role": "admin", "mode": "plan"},
)

store.put(
    ("agent_settings",),
    "user_456",
    {"role": "user", "mode": "plan"},
)

checkpointer = InMemorySaver()

agent_tool_context = create_agent(
    model=llm,
    tools=[add_task, list_tasks, update_task_status, delete_task],
    store=store,
    context_schema=Context,
    checkpointer=checkpointer,
)

if __name__ == "__main__":
    # Тест 1: обычный пользователь
    print("=== ПОЛЬЗОВАТЕЛЬ (user_456) ===")
    config = {"configurable": {"thread_id": "user_456-demo"}}

    res = agent_tool_context.invoke(
        {"messages": [{"role": "user", "content": "Удали первую задачу из списка"}]},
        config,
        context=Context(user_id="user_456"),
    )
    print(res["messages"][-1].content)

    # Тест 2: администратор
    print("\\n=== АДМИНИСТРАТОР (user_123) ===")
    config = {"configurable": {"thread_id": "user_123-demo"}}

    res = agent_tool_context.invoke(
        {"messages": [{"role": "user", "content": "Удали первую задачу из списка"}]},
        config,
        context=Context(user_id="user_123"),
    )
    print(res["messages"][-1].content)


