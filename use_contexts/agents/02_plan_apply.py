# Агент 02: ReAct-агент с динамическим управлением инструментами (Plan/Apply режим).
# Демонстрирует Model Context: middleware может изменять список доступных инструментов
# в зависимости от режима работы агента (plan — только просмотр, apply — изменение данных).


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

# Middleware: plan_apply_tools фильтрует инструменты в зависимости от режима (plan/apply)
from source.middleware import plan_apply_tools

# AgentContext: dataclass для передачи режима работы агента (mode: "plan" или "apply")
# Новый импорт на шаге 7: позволяет передавать дополнительный контекст при вызове агента
from source.context import AgentContext

# Код инициализации модели и создания агента добавляется на шаге 7
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2"),
    verify_ssl_certs=False,
    temperature=0.1,
)

checkpointer = InMemorySaver()

agent_plan_apply = create_agent(
    model=llm,
    tools=[add_task, list_tasks, update_task_status, delete_task],
    middleware=[plan_apply_tools],
    checkpointer=checkpointer,
    context_schema=AgentContext,
)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "plan-apply-demo"}}

    # Режим PLAN — только анализ
    print("=== РЕЖИМ PLAN ===")
    ctx_plan = AgentContext(mode="plan")

    res_plan = agent_plan_apply.invoke(
        {"messages": [{"role": "user", "content": "Удали последнюю задачу из списка задач"}]},
        config,
        context=ctx_plan,
    )

    print(res_plan["messages"][-1].content)

    # Режим APPLY — можно изменять БД
    print("\\n=== РЕЖИМ APPLY ===")
    ctx_apply = AgentContext(mode="apply")

    res_apply = agent_plan_apply.invoke(
        {"messages": [{"role": "user", "content": "Удали последнюю задачу из списка задач"}]},
        config,
        context=ctx_apply,
    )

    print(res_apply["messages"][-1].content)


