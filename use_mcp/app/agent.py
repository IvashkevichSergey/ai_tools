# Точка входа упражнения собирает агента LangChain поверх локального MCP-сервиса.
# На шаге 3 сюда добавятся модель GigaChat, клиент MCP и обработка пользовательских запросов.

import asyncio
import os
from pathlib import Path

from rich.console import Console
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_gigachat.chat_models import GigaChat
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_demo.app.prompts import SYSTEM_PROMPT
from mcp_demo.app.text_sanitize import sanitize_text

# Инициализируем консольный вывод для проверки сценария.
console = Console()

# Загружаем параметры подключения к GigaChat из env-файла упражнения.
load_dotenv(Path(__file__).resolve().parents[1] / "config" / "demo_env.env")

# Инициализируем модель GigaChat для выполнения сценария.
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_ACCESS_TOKEN"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    model=os.getenv("GIGACHAT_MODEL"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    verify_ssl_certs=False,  # В учебной среде проверка сертификатов отключена.
    timeout=120,
)


# Описываем уже запущенный локальный MCP-сервис.
MCP_SERVER_CONFIG = {
    "service_catalog": {
        "transport": "http",
        "url": "http://127.0.0.1:8085/mcp",
    }
}

# Создаём клиент LangChain для подключения к локальному MCP-сервису.
mcp_client = MultiServerMCPClient(MCP_SERVER_CONFIG)

# Загружаем опубликованные инструменты и сразу собираем агента.
tools = asyncio.run(mcp_client.get_tools())
agent = create_agent(model=llm, tools=tools, system_prompt=SYSTEM_PROMPT)

# Выполняем один запрос и выводим вызванные MCP-инструменты.
async def run_agent_query(query: str) -> str:
    final_answer = ""
    with console.status("[bold blue]Агент обрабатывает запрос...[/bold blue]", spinner="dots"):
        async for chunk in agent.astream({"messages": [{"role": "user", "content": query}]}, stream_mode="values"):
            message = chunk["messages"][-1]
            tool_calls = getattr(message, "tool_calls", []) or []

            if tool_calls:
                for tool_call in tool_calls:
                    console.print(f"[bold cyan]MCP-инструмент:[/bold cyan] {tool_call['name']} {tool_call['args']}")
            elif getattr(message, "type", "") == "tool":
                console.print("[dim]Результат инструмента:[/dim]", message.text)
            elif getattr(message, "type", "") == "ai":
                response_text = message.text
                if response_text:
                    final_answer = sanitize_text(response_text)
    return final_answer

# Запускаем интерактивную проверку.
async def main():
    while True:
        query = console.input("[bold cyan]Введите запрос клиента:[/bold cyan] ").strip()
        if query.lower() in ("выход", "exit"):
            break
        if query:
            console.print("[bold green]Ответ агента:[/bold green]", await run_agent_query(query))
            console.print()

# Запускаем сценарий проверки.
if __name__ == "__main__":
    asyncio.run(main())
