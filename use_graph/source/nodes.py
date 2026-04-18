# Узлы графа состояний: chat, router, get_digital_twin, retrieve_credits.
# LLM и ретривер передаются при вызове графа через context (Runtime).
# Состояние графа хранит сообщения отдельно от служебных полей маршрутизации и контекста.

from dataclasses import dataclass
import re
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import NotRequired

from langgraph.graph import MessagesState
from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage, SystemMessage

from graph_demo.data.client_profiles import CLIENT_PROFILES
from graph_demo.source.tools import get_digital_twin


@dataclass
class ContextSchema:
    llm: object
    retriever: object


class GraphState(MessagesState):
    """Состояние графа: messages — только переписка; внутренние данные пайплайна в отдельных полях."""
    route: NotRequired[Literal["simple", "consultation"] | None]
    client_id: NotRequired[str | None]
    client_profile_json: NotRequired[str | None]
    retrieved_docs_text: NotRequired[str | None]
    credit_params_summary: NotRequired[str | None]
    needs_clarification: NotRequired[bool | None]


def _last_user_content(messages) -> str:
    """Текст последнего сообщения пользователя в списке сообщений."""
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage) and getattr(m, "content", None):
            return (m.content or "").strip()
    return ""


def _build_context_parts(state: GraphState) -> list[str]:
    """Собирает блоки контекста из полей state (профиль, документы, саммари) для промпта."""
    parts = []
    if state.get("client_profile_json"):
        parts.append(f"Профиль клиента:\n{state.get('client_profile_json')}")
    if state.get("retrieved_docs_text"):
        parts.append(f"Условия по документам:\n{state.get('retrieved_docs_text')}")
    if state.get("credit_params_summary"):
        parts.append(state["credit_params_summary"])
    return parts


def chat(state: GraphState, runtime: Runtime[ContextSchema]) -> dict:
    """Узел графа: формирует итоговый ответ модели с учётом уже собранного контекста."""
    llm = runtime.context.llm
    if not llm:
        return {"messages": []}

    messages = state["messages"]
    context_parts = _build_context_parts(state)
    question = _last_user_content(messages)

    if context_parts and question:
        context = "\n\n".join(context_parts)
        prompt = (
            "Ответь на вопрос на основе предоставленного контекста.\n\n"
            "Используй только сведения из контекста. "
            "Не добавляй markdown-заголовки и декоративное оформление.\n\n"
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {question}\nОтвет:"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
    else:
        system = SystemMessage(
            content=(
                "Ты внутрибанковский консультант по кредитным продуктам. "
                "Отвечай формально, по существу и без декоративного оформления."
            )
        )
        response = llm.invoke([system, *messages])

    return {"messages": [response]}


class RouteDecision(BaseModel):
    """Структурированный результат роутера."""
    route: Literal["simple", "consultation"] = Field(
        description="Маршрут обработки запроса"
    )


def router_node(state: GraphState, runtime: Runtime[ContextSchema]) -> dict:
    """Узел: определяет маршрут запроса и записывает его в state."""
    llm = runtime.context.llm
    question = _last_user_content(state.get("messages") or [])

    if not llm or not question:
        return {"route": "consultation"}

    router_llm = llm.with_structured_output(RouteDecision)

    decision = router_llm.invoke([
        SystemMessage(
            content=(
                "Определи маршрут запроса.\n"
                "Верни route='consultation', если запрос связан с кредитной консультацией, "
                "подбором кредитного продукта, лимита, условий, предложением для клиента, "
                "анализом клиента, client_id или профилем клиента.\n"
                "Верни route='simple', если это обычный разговор, приветствие, small talk "
                "или нейтральный вопрос без явного запроса на кредитную консультацию.\n"
                "Верни только structured output по схеме."
            )
        ),
        HumanMessage(content=question),
    ])

    route = decision.route if decision.route in ("simple", "consultation") else "consultation"
    return {"route": route}


def route_query(state: GraphState) -> Literal["simple", "consultation"]:
    """Читает уже вычисленный маршрут из state для conditional edge."""
    route = state.get("route")
    if route in ("simple", "consultation"):
        return route
    return "consultation"


def _format_docs(docs):
    """Склеивает найденные документы в единый текстовый блок для ответа модели."""
    return "\n\n".join(d.page_content for d in docs)


def get_digital_twin_node(state: GraphState) -> dict:
    """Узел графа: извлекает ID клиента из запроса и получает профиль клиента."""
    content = _last_user_content(state.get("messages") or []).lower().replace(" ", "")
    match = re.search(r"client_\d{2}", content)
    client_id = match.group(0) if match else None

    if client_id and client_id not in CLIENT_PROFILES:
        client_id = None

    if not client_id:
        return {
            "client_id": None,
            "client_profile_json": None,
            "needs_clarification": True,
            "credit_params_summary": (
                "В запросе не указан идентификатор клиента. "
                "Нужно уточнить client_id перед персональной консультацией."
            ),
        }

    profile_output = get_digital_twin.invoke({"client_id": client_id})
    return {
        "client_id": client_id,
        "client_profile_json": profile_output,
        "needs_clarification": False,
    }


def retrieve_credits(state: GraphState, runtime: Runtime[ContextSchema]) -> dict:
    """Узел графа: по запросу пользователя и профилю клиента подбирает релевантные условия кредитования, заполняет retrieved_docs_text."""
    retriever = runtime.context.retriever
    if not retriever:
        return {"retrieved_docs_text": "Ретривер не передан в context."}

    if state.get("needs_clarification"):
        return {"retrieved_docs_text": None}

    user_question = _last_user_content(state.get("messages") or [])[:300]
    client_profile = (state.get("client_profile_json") or "").strip()[:500]
    query = f"{user_question} {client_profile}".strip() or "условия потребительского кредита ставка срок сумма"
    docs = retriever.invoke(query)
    formatted = _format_docs(docs)
    return {"retrieved_docs_text": formatted}
