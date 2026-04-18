"""Главный модуль для взаимодействия с агентом исследования."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from rich.console import Console

from research_agent.source.agent import agent

console = Console()
PROJECT_DIR = Path(__file__).resolve().parent
PROFILES_DIR = PROJECT_DIR / "profiles"


def _pick_profile() -> tuple[str, str]:
    profiles = sorted(PROFILES_DIR.glob("*.txt"))
    if not profiles:
        raise FileNotFoundError(f"В папке профилей нет файлов: {PROFILES_DIR}")

    while True:
        console.print("[bold]Доступные профили:[/bold]")
        for i, p in enumerate(profiles, 1):
            console.print(f"  {i}. {p.stem}")

        raw = console.input("\nВыберите профиль (номер): ").strip()
        if raw.lower() in {"выход", "exit", "quit"}:
            raise KeyboardInterrupt
        if not raw.isdigit():
            console.print("[yellow]Введите номер профиля из списка.[/yellow]\n")
            continue

        idx = int(raw) - 1
        if not (0 <= idx < len(profiles)):
            console.print("[yellow]Такого номера нет в списке профилей.[/yellow]\n")
            continue

        profile_path = profiles[idx]
        return profile_path.stem, profile_path.read_text(encoding="utf-8")


def _build_profiled_request(profile_name: str, profile_text: str, user_query: str) -> str:
    """Собирает итоговый пользовательский запрос для финального сценария."""
    return (
        f"Контекст адресата ({profile_name}):\n"
        f"{profile_text}\n\n"
        "Документ уже загружен и проиндексирован в системе.\n"
        f"Задача:\n{user_query}\n\n"
        "Если задача связана с письмом по документу, сначала собери факты, затем критически проверь текст, затем оформи финальный вариант.\n"
        "Контекст адресата используйте только для тона, формы обращения и ожидаемого уровня детализации.\n"
        "Фактическое содержание берите из документа и найденных по нему фрагментов.\n"
        "Верните только готовый текст письма без примечаний после него.\n"
        "Если данных для подписи недостаточно, завершите письмо нейтрально без вымышленных реквизитов и без заглушек."
    )


def chat() -> None:
    """Запускает финальный сценарий с выбором профиля и одним пользовательским запросом."""
    console.print("[bold cyan]Финальный сценарий: письмо руководителю[/bold cyan]\n")

    try:
        profile_name, profile_text = _pick_profile()
    except KeyboardInterrupt:
        console.print("[yellow]Выход без запуска сценария.[/yellow]")
        return
    console.print(f"\n[dim]Выбран профиль:[/dim] [bold]{profile_name}[/bold]\n")

    user_query = console.input("Введите задачу для агента: ").strip()
    if user_query.lower() in {"выход", "exit", "quit"}:
        console.print("[yellow]Выход без запуска сценария.[/yellow]")
        return
    if not user_query:
        console.print("[yellow]Пустой запрос — выходим.[/yellow]")
        return

    prompt = _build_profiled_request(profile_name, profile_text, user_query)

    config = {"configurable": {"thread_id": f"chat_{uuid4().hex[:8]}"}}

    try:
        with console.status("[dim]Агент готовит письмо...[/dim]", spinner="dots"):
            response = agent.invoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config=config,
            )
    except Exception as exc:
        console.print(f"\n[bold red]Ошибка:[/bold red] {exc}")
        return

    messages = response.get("messages") or []
    answer = getattr(messages[-1], "content", "") if messages else ""
    if isinstance(answer, list):
        answer = "".join(getattr(block, "text", str(block)) for block in answer)

    console.print("\n[bold]Ответ агента:[/bold]\n")
    console.print(answer.strip() if answer else "[dim]Нет текстового ответа[/dim]")


if __name__ == "__main__":
    chat()

def _build_profiled_request(profile_name: str, profile_text: str, user_query: str) -> str:
    return (
        f"Контекст адресата ({profile_name}):\n"
        f"{profile_text}\n\n"
        "Документ уже загружен и проиндексирован в системе.\n"
        f"Задача:\n{user_query}\n\n"
        "Если задача связана с письмом по документу, сначала собери факты, затем критически проверь текст, затем оформи финальный вариант.\n"
        "Контекст адресата используйте только для тона, формы обращения и ожидаемого уровня детализации.\n"
        "Фактическое содержание берите из документа и найденных по нему фрагментов.\n"
        "Верните только готовый текст письма без примечаний после него.\n"
        "Если данных для подписи недостаточно, завершите письмо нейтрально без вымышленных реквизитов и без заглушек."
    )
