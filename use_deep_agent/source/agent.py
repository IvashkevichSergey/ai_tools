"""Основной модуль исследовательского агента.

В этом модуле создан агент с использованием LangGraph:
- Инициализация модели GigaChat
- Создание агента с поддержкой расширенного состояния (TODO и файлы)
- Подключение инструментов для планирования, работы с файлами и поиска в PDF
"""


# Импорты и загрузка окружения
import os
from importlib.resources import files
from dotenv import load_dotenv
from rich.console import Console
from langchain.agents import create_agent
from langchain_gigachat import GigaChat
from langgraph.checkpoint.memory import InMemorySaver
from research_agent.source.prompts import system_prompt
from langchain.agents.middleware import TodoListMiddleware
from deepagents import create_deep_agent
from research_agent.tools.document_tool import search_document
from research_agent.tools.think_tool import think_tool
from research_agent.subagents.researcher.researcher import create_research_agent
from research_agent.subagents.critic.critic import create_critic_agent
from research_agent.subagents.writer.writer import create_writer_agent

load_dotenv(str(files("research_agent").joinpath("config", "demo_env.env")))

# Инициализация модели
model = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    model=os.getenv("GIGACHAT_MODEL", "GigaChat-2-Max"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    verify_ssl_certs=False,
    timeout=600,
    temperature=0.1,
    max_tokens=3000,
)


research_subagent = create_research_agent()
critic_subagent = create_critic_agent()
writer_subagent = create_writer_agent()

# Создание deep-агента с подагентами
checkpointer = InMemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[search_document, think_tool],
    system_prompt=system_prompt,
    subagents=[research_subagent, critic_subagent, writer_subagent],
    checkpointer=checkpointer,
)
