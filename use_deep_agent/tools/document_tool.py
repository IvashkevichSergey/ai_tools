"""Инструменты для работы с PDF-документами."""

from pathlib import Path

import pdfplumber
from langchain_core.documents import Document
from langchain_core.tools import tool

from research_agent.source.rag import PROJECT_DIR, get_retriever


def _resolve_pdf_path(source_pdf: str | None = None) -> Path:
    if source_pdf is None:
        assets_dir = PROJECT_DIR / "assets"
        pdf_files = sorted(assets_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"В папке assets нет PDF: {assets_dir}")
        return pdf_files[0]

    pdf_path = PROJECT_DIR / source_pdf
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF не найден: {source_pdf}")
    return pdf_path


@tool(parse_docstring=True)
def search_document(query: str, k: int = 3) -> str:
    """Поиск по уже загруженному и проиндексированному PDF. Вызывай этот инструмент, когда пользователь спрашивает о содержании документа — документ уже в системе, ничего запрашивать у пользователя не нужно.

    Семантический поиск по векторному хранилищу (RAG), возвращает релевантные фрагменты с метаданными (страница, источник).

    Args:
        query: Поисковый запрос по содержанию документа
        k: Количество фрагментов в ответе

    Returns:
        Строка с найденными фрагментами и метаданными
    """
    docs: list[Document] = get_retriever(
        k=max(k, 3),
        search_type="mmr",
    ).invoke(query)

    results = []
    for i, doc in enumerate(docs):
        content = doc.page_content.strip()
        metadata = doc.metadata if hasattr(doc, 'metadata') else {}
        chunk_id = metadata.get('chunk_id', '?')
        source = metadata.get('source_pdf', 'unknown')
        page = metadata.get('page', '?')
        result_header = (
            f"[Фрагмент {i+1} | Страница: {page} | Чанк: {chunk_id} | Источник: {source}]"
        )

        results.append(f"{result_header}\n{content}\n")

    return "\n".join(results)


@tool(parse_docstring=True)
def read_document_pages(
    start_page: int = 1,
    end_page: int = 3,
    source_pdf: str | None = None,
) -> str:
    """Возвращает текст указанного диапазона страниц из уже загруженного PDF.

    Этот инструмент полезен, когда нужно понять структуру документа:
    например, посмотреть начало PDF, найти заголовок раздела или проверить,
    как устроено оглавление.

    Args:
        start_page: Номер первой страницы в диапазоне
        end_page: Номер последней страницы в диапазоне
        source_pdf: Относительный путь к PDF внутри проекта. Если не указан, берётся первый PDF из assets.

    Returns:
        Строка с текстом страниц и их номерами
    """
    pdf_path = _resolve_pdf_path(source_pdf)
    start_page = max(1, start_page)
    end_page = max(start_page, min(end_page, start_page + 4))

    blocks: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        page_from = min(start_page, total_pages)
        page_to = min(end_page, total_pages)

        for page_num in range(page_from, page_to + 1):
            text = pdf.pages[page_num - 1].extract_text() or ""
            text = " ".join(text.split())
            if not text:
                text = "[На странице нет извлекаемого текста]"
            blocks.append(f"[Страница {page_num}]\n{text}")

    return "\n\n".join(blocks)
