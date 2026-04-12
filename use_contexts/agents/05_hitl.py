# Агент 05: ReAct-агент с Human-in-the-Loop (подтверждение действий пользователем).
# Демонстрирует Life-cycle Context: middleware прерывает выполнение агента перед
# вызовом критических инструментов и запрашивает подтверждение у пользователя.


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

# HumanInTheLoopMiddleware: middleware для подтверждения действий агента
# Новый импорт на шаге 10: прерывает выполнение агента перед вызовом указанных инструментов
# и позволяет пользователю одобрить (approve), отклонить (reject) или изменить (edit) действие
from langchain.agents.middleware import HumanInTheLoopMiddleware

# Command: используется для продолжения выполнения агента после прерывания
# Новый импорт на шаге 10: позволяет передавать решение пользователя (approve/reject) обратно агенту
from langgraph.types import Command

# Инструменты для работы с базой данных задач
from source.tools import add_task, list_tasks, update_task_status, delete_task

# Код инициализации модели, создания middleware и агента добавляется на шаге 10
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2"),
    verify_ssl_certs=False,
    temperature=0.1,
)
hitl_middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        # Для смены статуса всегда спрашиваем человека
        "update_task_status": {
            "allowed_decisions": ["approve", "reject"],
            "description": (
                "Модель хочет изменить статус задачи. "
                "Нужно решить, разрешить ли выполнение этого действия."
            ),
        },
        # Остальные инструменты считаем безопасными
        "add_task": False,
        "list_tasks": False,
        "delete_task": False,
    },
)
checkpointer = InMemorySaver()

agent_hitl = create_agent(
    model=llm,
    tools=[add_task, list_tasks, update_task_status, delete_task],
    middleware=[hitl_middleware],
    checkpointer=checkpointer,
)
if __name__ == "__main__":
    from langgraph.types import Command

    config = {"configurable": {"thread_id": "hitl-demo"}}

    # Первый запуск агента (ограничиваем до 3 задач для демонстрации)
    result = agent_hitl.invoke(
        {"messages": [{"role": "user", "content": "Сделай первые 3 задачи выполненными (done)."}]},
        config=config,
    )

    step = 1
    processed_tasks = 0  # Счетчик обработанных задач
    max_tasks = 3  # Ограничение на количество задач

    # Обработка прерываний
    while "__interrupt__" in result and processed_tasks < max_tasks:
        print(f"\\n=== ИНТЕРРАПТ #{step} ===")

        interrupt_list = result["__interrupt__"]
        hitl_req = interrupt_list[0].value if isinstance(interrupt_list, list) else interrupt_list.value

        action_requests = hitl_req["action_requests"]

        decisions = []

        for i, req in enumerate(action_requests, 1):
            # Ограничиваем количество обрабатываемых задач
            if processed_tasks >= max_tasks:
                print(
                    f"\\nДостигнут лимит в {max_tasks} задачи. Отклоняем оставшиеся {len(action_requests) - i + 1} действий.")
                # Отклоняем все оставшиеся действия (начиная с текущего)
                remaining = len(action_requests) - i + 1
                for _ in range(remaining):
                    decisions.append({
                        "type": "reject",
                        "message": "Достигнут лимит обработанных задач для демонстрации."
                    })
                break

            name = req.get("name")
            args = req.get("arguments") or req.get("args")
            desc = req.get("description")

            print(f"\\nДействие #{i}")
            print(f"  tool = {name}")
            print(f"  args = {args}")
            print(f"  описание: {desc}")

            # Запрос подтверждения
            while True:
                choice = input("Одобрить? (a = approve, r = reject): ").strip().lower()
                if choice in ("a", "r"):
                    break

            if choice == "a":
                decisions.append({"type": "approve"})
                processed_tasks += 1
            else:
                # При reject отправляем явное сообщение об ошибке, чтобы агент понял, что операция не выполнена
                msg = input("Комментарий (почему отклонено): ") or "Действие отклонено пользователем."
                decisions.append({
                    "type": "reject",
                    "message": f"ОШИБКА: Операция отклонена пользователем. {msg} Статус задачи НЕ изменен."
                })

        # Продолжаем выполнение с решениями
        result = agent_hitl.invoke(
            Command(resume={"decisions": decisions}),
            config=config
        )

        step += 1

    # Агент завершил работу
    print("\\n=== АГЕНТ ЗАВЕРШИЛ РАБОТУ ===")
    for msg in result["messages"]:
        msg.pretty_print()
