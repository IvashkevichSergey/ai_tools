# Точка входа: граф состояний на LangGraph.
# В шаге 2 здесь собирается минимальный граф с одним узлом chat.
# В шаге 3 граф расширяется роутером, консультационной веткой и интерактивной проверкой.

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
from langgraph.graph import END, START, StateGraph
from rich.console import Console

from graph_demo.source.debug_runner import run_graph_debug
# Подключаем все узлы и схемы, которые нужны для полной сборки графа.
from graph_demo.source.nodes import ContextSchema, GraphState, chat, get_digital_twin_node, retrieve_credits, route_query, router_node
from graph_demo.source.retriever import retriever

# Загружаем учебные переменные окружения из demo_env.env.
load_dotenv(Path(__file__).resolve().parents[1] / "config" / "demo_env.env")
console = Console()

# Инициализируем модель GigaChat для узлов графа.
llm = GigaChat(
    credentials=os.getenv("GIGACHAT_ACCESS_TOKEN"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    model=os.getenv("GIGACHAT_MODEL"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    verify_ssl_certs=False,  # только для учебной среды без проверки SSL
    timeout=120,
)

# Собираем полный граф с роутером и консультационной веткой.
builder = StateGraph(GraphState, context_schema=ContextSchema)
builder.add_node("router", router_node)
builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    route_query,
    {"simple": "chat", "consultation": "get_digital_twin"},
)
builder.add_node("chat", chat)
builder.add_node("get_digital_twin", get_digital_twin_node)
builder.add_node("retrieve_credits", retrieve_credits)
builder.add_edge("get_digital_twin", "retrieve_credits")
builder.add_edge("retrieve_credits", "chat")
builder.add_edge("chat", END)
graph = builder.compile()

# Запускаем интерактивную проверку двух маршрутов графа.
# Выводим описание графа в формате Mermaid в терминал.
console.print("[bold cyan]Скопируйте описание графа ниже целиком:[/bold cyan]")
console.print(graph.get_graph().draw_mermaid())
