"""Интерактивная проверка подагентов и делегирования."""

import traceback
from uuid import uuid4

from rich.console import Console

console = Console()


def _msg_type(msg):
    if hasattr(msg, "type"):
        return getattr(msg, "type", None)
    return getattr(msg, "type", None) or (
        msg.__class__.__name__ if hasattr(msg, "__class__") else None
    )


def _check_subagent(factory, expected_name: str, label: str) -> bool:
    ok = True
    try:
        subagent = factory()
        if subagent.get("name") == expected_name:
            console.print(f"[green]OK[/green] {label}: создан")
        else:
            console.print(f"[red]FAIL[/red] {label}: неверное имя")
            ok = False
        if "system_prompt" in subagent and "model" in subagent:
            console.print(f"[green]OK[/green] {label}: конфигурация создана")
        else:
            console.print(f"[red]FAIL[/red] {label}: конфигурация неполная")
            ok = False
    except Exception as exc:
        console.print(f"[red]FAIL[/red] {label}: {exc}")
        ok = False
    return ok


def test_step7_subagents():
    """Запускает интерактивную проверку делегирования."""
    console.print("[bold cyan]Проверка шага 7: подагенты и делегирование[/bold cyan]\n")

    all_ok = True
    try:
        from research_agent.subagents.critic.critic import create_critic_agent
        from research_agent.subagents.researcher.researcher import create_research_agent
        from research_agent.subagents.writer.writer import create_writer_agent
        from research_agent.source.agent import agent
    except Exception as exc:
        console.print(f"[red]FAIL[/red] Ошибка импорта: {exc}")
        console.print(traceback.format_exc())
        return False

    console.print("[bold]Проверка фабрик подагентов:[/bold]")
    all_ok &= _check_subagent(create_research_agent, "researcher", "researcher")
    all_ok &= _check_subagent(create_critic_agent, "critic", "critic")
    all_ok &= _check_subagent(create_writer_agent, "writer", "writer")
    console.print()

    thread_id = f"test_step7_{uuid4().hex[:8]}"
    shown_messages_count = 0

    while True:
        user_query = console.input("[bold cyan]Введите запрос:[/bold cyan] ").strip()
        if user_query.lower() in {"выход", "exit", "quit"}:
            break
        if not user_query:
            continue

        try:
            with console.status("[dim]Агент распределяет подзадачи...[/dim]", spinner="dots"):
                response = agent.invoke(
                    {"messages": [{"role": "user", "content": user_query}]},
                    config={"configurable": {"thread_id": thread_id}},
                )
        except Exception as exc:
            console.print(f"[red]FAIL[/red] Ошибка вызова агента: {exc}")
            console.print(traceback.format_exc())
            console.print()
            continue

        messages = response.get("messages") or []
        new_messages = messages[shown_messages_count:]
        shown_messages_count = len(messages)

        tools_used: list[str] = []
        delegated_targets: list[str] = []
        step = 0

        console.print("[bold]Ход выполнения:[/bold]")
        for msg in new_messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                step += 1
                names = [tc.get("name", "?") for tc in msg.tool_calls]
                for name in names:
                    if name not in tools_used:
                        tools_used.append(name)
                console.print(f"  Шаг {step} -> вызваны: [green]{', '.join(names)}[/green]")

                for tc in msg.tool_calls:
                    if tc.get("name") != "task":
                        continue
                    args = tc.get("args") or {}
                    if isinstance(args, dict):
                        target = (
                            args.get("name")
                            or args.get("subagent")
                            or args.get("subagent_name")
                            or args.get("subagent_type")
                        )
                        if isinstance(target, str):
                            delegated_targets.append(target)

            t = _msg_type(msg)
            if t == "tool" or "ToolMessage" in str(type(msg).__name__):
                tool_name = getattr(msg, "name", None) or "tool"
                console.print(f"  <- результат от [green]{tool_name}[/green]")

        if delegated_targets:
            console.print(
                "[green]OK[/green] Делегирование замечено: {}".format(
                    ", ".join(dict.fromkeys(delegated_targets))
                )
            )
        else:
            console.print("[yellow]WARN[/yellow] Делегирование в этом запросе не распознано")

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

    if all_ok:
        console.print("[bold green]Проверка фабрик подагентов завершена без ошибок.[/bold green]")
    return all_ok


if __name__ == "__main__":
    test_step7_subagents()
