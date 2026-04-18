"""Интерактивная проверка агента с инструментами шага 6."""

import json
import re
import traceback
from uuid import uuid4

from rich.console import Console

from research_agent.source.agent import agent
from research_agent.tools.document_tool import search_document
from research_agent.tools.think_tool import think_tool

console = Console()


def _msg_type(msg):
    if hasattr(msg, "type"):
        return getattr(msg, "type", None)
    return getattr(msg, "type", None) or (
        msg.__class__.__name__ if hasattr(msg, "__class__") else None
    )


def _compact(value, limit: int = 220) -> str:
    try:
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = str(value)
    except Exception:
        text = str(value)
    text = text.replace("\n", " ").strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def _extract_todos(args: dict) -> list[dict]:
    if not isinstance(args, dict):
        return []
    todos = args.get("todos")
    if isinstance(todos, list):
        return [t for t in todos if isinstance(t, dict)]
    return []


def _extract_fragment_headers(content: str) -> list[dict]:
    pattern = re.compile(
        r"\[Фрагмент\s+(?P<idx>\d+)\s+\|\s+Страница:\s+(?P<page>[^\|]+)\s+\|\s+Чанк:\s+(?P<chunk>[^\|]+)\s+\|\s+Источник:\s+(?P<source>[^\]]+)\]"
    )
    result = []
    for m in pattern.finditer(content):
        result.append(
            {
                "idx": m.group("idx").strip(),
                "page": m.group("page").strip(),
                "chunk": m.group("chunk").strip(),
                "source": m.group("source").strip(),
            }
        )
    return result


def test_step6_agent():
    """Запускает интерактивную проверку агента с инструментами."""
    console.print("[bold cyan]Проверка шага 6: агент с инструментами[/bold cyan]\n")

    try:
        graph = agent.get_graph()
        nodes = list(graph.nodes.keys())
        console.print("[green]OK[/green] Агент импортирован")
        console.print(f"[green]OK[/green] Граф создан: {', '.join(nodes)}")
        console.print("[green]OK[/green] Инструменты доступны: search_document, think_tool\n")
    except Exception as exc:
        console.print(f"[red]FAIL[/red] Не удалось подготовить агента: {exc}")
        console.print(traceback.format_exc())
        return False

    thread_id = f"test_step6_{uuid4().hex[:8]}"
    shown_messages_count = 0
    todo_status_by_content: dict[str, str] = {}

    while True:
        user_query = console.input("[bold cyan]Введите запрос:[/bold cyan] ").strip()
        if user_query.lower() in {"выход", "exit", "quit"}:
            break
        if not user_query:
            continue

        try:
            with console.status("[dim]Агент обрабатывает запрос...[/dim]", spinner="dots"):
                response = agent.invoke(
                    {"messages": [{"role": "user", "content": user_query}]},
                    config={"configurable": {"thread_id": thread_id}},
                )
        except Exception as exc:
            console.print(f"[red]FAIL[/red] Ошибка вызова агента: {exc}\n")
            continue

        messages = response.get("messages") or []
        new_messages = messages[shown_messages_count:]
        shown_messages_count = len(messages)

        tools_used: list[str] = []
        console.print("[bold]Ход выполнения:[/bold]")
        step = 0
        for msg in new_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                step += 1
                console.print(f"  Шаг {step}")
                for tc in msg.tool_calls:
                    name = tc.get("name", "?")
                    args = tc.get("args", {})
                    if name not in tools_used:
                        tools_used.append(name)
                    if name == "search_document":
                        console.print(
                            f"    - [green]{name}[/green] query={_compact(args.get('query', ''))}"
                        )
                    elif name == "think_tool":
                        console.print(
                            f"    - [green]{name}[/green] reflection={_compact(args.get('reflection', ''))}"
                        )
                    elif name == "write_todos":
                        todos = _extract_todos(args)
                        console.print(f"    - [green]{name}[/green] todos={len(todos)}")
                        for todo in todos:
                            content = str(todo.get("content", "")).strip()
                            status = str(todo.get("status", "")).strip()
                            if not content or not status:
                                continue
                            previous = todo_status_by_content.get(content)
                            if previous != status:
                                previous_label = previous if previous is not None else "—"
                                console.print(
                                    f"      TODO: {content} | {previous_label} -> {status}"
                                )
                                todo_status_by_content[content] = status
                    else:
                        console.print(f"    - [green]{name}[/green] args={_compact(args)}")

            t = _msg_type(msg)
            if t == "tool" or "ToolMessage" in str(type(msg).__name__):
                name = getattr(msg, "name", None) or "tool"
                content = getattr(msg, "content", "")
                if isinstance(content, list):
                    content = "".join(getattr(block, "text", str(block)) for block in content)
                if name == "search_document" and isinstance(content, str):
                    headers = _extract_fragment_headers(content)
                    if headers:
                        unique_chunks = sorted({h["chunk"] for h in headers})
                        unique_pages = sorted({h["page"] for h in headers})
                        console.print(
                            "    <- ToolMessage name={name}, fragments={frags}, chunks={chunks}, pages={pages}".format(
                                name=name,
                                frags=len(headers),
                                chunks="[" + ", ".join(unique_chunks) + "]",
                                pages="[" + ", ".join(unique_pages) + "]",
                            )
                        )
                    else:
                        console.print(f"    <- ToolMessage name={name}, content={_compact(content)}")
                elif name in {"write_todos", "think_tool"}:
                    console.print(f"    <- ToolMessage name={name}, ok")
                else:
                    console.print(f"    <- ToolMessage name={name}, content={_compact(content)}")

        answer = getattr(messages[-1], "content", "") if messages else ""
        if isinstance(answer, list):
            answer = "".join(getattr(block, "text", str(block)) for block in answer)

        console.print("\n[bold]Ответ агента:[/bold]")
        console.print(answer.strip() if answer else "[dim]Нет текстового ответа[/dim]")
        console.print(
            "\n[bold]Итог:[/bold] инструменты: [green]{}[/green]\n".format(
                ", ".join(tools_used) if tools_used else "—"
            )
        )

    return True


if __name__ == "__main__":
    test_step6_agent()
