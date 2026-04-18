"""Интерактивная проверка слоя RAG."""

from pathlib import Path

from rich.console import Console

from research_agent.source.rag import _collection_name, init_all_vectorstores
from research_agent.storage.index_state_db import get_state

console = Console()
PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_step5_rag():
    """Запускает интерактивную проверку чанков документа."""
    console.print("[bold cyan]Проверка шага 5: RAG и индекс документа[/bold cyan]\n")
    console.print("Инициализация векторных хранилищ для всех PDF...\n")

    vectorstores = init_all_vectorstores()
    if not vectorstores:
        console.print("[red]В папке assets не найдено PDF-файлов.[/red]")
        return False

    documents = list(vectorstores.items())
    console.print(f"[green]OK[/green] Инициализировано документов: {len(documents)}")

    while True:
        console.print("\n[bold]Доступные документы:[/bold]")
        for i, (source_key, _) in enumerate(documents, 1):
            pdf_path = PROJECT_DIR / source_key
            collection = _collection_name(pdf_path)
            state = get_state(PROJECT_DIR, collection, source_key)
            total_chunks = state["total_chunks"] if state else 0
            console.print(f"  {i}. {source_key} (чанков: {total_chunks})")

        doc_input = console.input(
            "\nВведите номер документа или 'выход': "
        ).strip()
        if doc_input.lower() in {"выход", "exit", "quit", "q"}:
            return True

        try:
            doc_index = int(doc_input) - 1
        except ValueError:
            console.print("[red]Введите номер документа или 'выход'.[/red]")
            continue

        if not (0 <= doc_index < len(documents)):
            console.print(f"[red]Номер должен быть от 1 до {len(documents)}.[/red]")
            continue

        source_key, vectorstore = documents[doc_index]
        pdf_path = PROJECT_DIR / source_key
        collection = _collection_name(pdf_path)
        state = get_state(PROJECT_DIR, collection, source_key)

        if not state:
            console.print(
                f"[red]Состояние индекса для документа {source_key} не найдено в БД.[/red]"
            )
            continue

        total_chunks = state["total_chunks"]
        console.print(f"\n[bold cyan]Документ: {source_key}[/bold cyan]")
        console.print(f"Коллекция: [bold]{collection}[/bold]")
        console.print(f"Количество чанков: [bold]{total_chunks}[/bold]\n")

        while True:
            user_input = console.input(
                f"Введите номер чанка (0..{total_chunks - 1}), 'назад' или 'выход': "
            ).strip()

            if user_input.lower() in {"выход", "exit", "quit", "q"}:
                return True
            if user_input.lower() in {"назад", "back", "b"}:
                break

            try:
                chunk_id = int(user_input)
            except ValueError:
                console.print(
                    "[red]Введите номер чанка, 'назад' или 'выход'.[/red]"
                )
                continue

            if not (0 <= chunk_id < total_chunks):
                console.print(
                    f"[red]Номер должен быть от 0 до {total_chunks - 1}.[/red]"
                )
                continue

            results = vectorstore.get(where={"chunk_id": str(chunk_id)})
            if not results or not results.get("documents"):
                console.print(f"[red]Чанк №{chunk_id} не найден.[/red]")
                continue

            content = results["documents"][0]
            metadata = results.get("metadatas", [{}])[0] if results.get("metadatas") else {}

            console.print(f"\n[bold cyan]Чанк №{chunk_id}[/bold cyan]")
            console.print(f"Страница: [yellow]{metadata.get('page', '?')}[/yellow]")
            console.print(f"Источник: [yellow]{metadata.get('source_pdf', '?')}[/yellow]")
            console.print("\n[bold]Содержимое:[/bold]")
            console.print(content)
            console.print()


if __name__ == "__main__":
    test_step5_rag()
