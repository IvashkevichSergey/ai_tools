# Файл инициализирует окружение и общие зависимости для агента с памятью.

import os
from pathlib import Path
from uuid import uuid4
from rich.console import Console

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_gigachat.chat_models import GigaChat
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from memory_demo.source.prompts import SYSTEM_PROMPT
from memory_demo.source.text_sanitize import sanitize_message_payload, sanitize_text
from memory_demo.source.tools import UserContext, get_user_info, save_user_info

console = Console()
load_dotenv(Path(__file__).resolve().parents[1] / "config" / "demo_env.env")

# Инициализируем модель GigaChat.
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_ACCESS_TOKEN"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    model=os.getenv("GIGACHAT_MODEL"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    verify_ssl_certs=False,
    timeout=120,
)


# Фиксируем идентификатор пользователя для long-term memory.
USER_ID = "user-1"

# Генерируем идентификатор потока для short-term memory.
thread_id = str(uuid4())

# Подключаем short-term и long-term memory.
checkpointer = InMemorySaver()
store = InMemoryStore()


# Создаём агента с поддержкой short-term memory.
# Создаём агента с поддержкой short-term и long-term memory.
agent = create_agent(
    model=llm,
    tools=[get_user_info, save_user_info],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
    store=store,
    context_schema=UserContext,
)

if __name__ == "__main__":
    current_thread_id = thread_id

    while True:
        query = sanitize_text(console.input("[bold cyan]Введите запрос:[/bold cyan] ").strip())

        if query.lower() in ("выход", "exit"):
            break

        if query == "/thread":
            current_thread_id = str(uuid4())
            console.print(f"[bold magenta]thread:[/bold magenta] {current_thread_id}\n")
            continue

        if not query:
            continue

        config = {"configurable": {"thread_id": current_thread_id}}

        with console.status("[bold blue]Агент обрабатывает запрос...[/bold blue]", spinner="dots"):
            result = agent.invoke(
                sanitize_message_payload({"messages": [{"role": "user", "content": query}]}),
                config=config,
                context=UserContext(user_id=USER_ID),
            )
            state = agent.get_state(config)
            msgs = len(state.values.get("messages", []))
            answer = sanitize_text(result["messages"][-1].content)

        console.print("[bold green]Ответ агента:[/bold green]", answer)
        console.print(f"[dim]thread={current_thread_id} | user={USER_ID} | msgs={msgs}[/dim]\n")
