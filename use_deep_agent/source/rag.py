"""Вспомогательные функции для работы с PDF-документами с использованием RAG.

Этот модуль:
- извлекает и форматирует текст из PDF;
- разбивает текст на чанки;
- строит или загружает индекс Chroma;
- сохраняет служебное состояние индекса в SQLite.
"""

import hashlib
import os
import re
from importlib.resources import files
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_gigachat import GigaChatEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from research_agent.storage.index_state_db import get_state, upsert_state


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 350
INDEX_METADATA_VERSION = 3

PROJECT_DIR = files("research_agent").joinpath("config").parent  # .../research_agent
load_dotenv(PROJECT_DIR / "config" / "demo_env.env")

embeddings = GigaChatEmbeddings(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    verify_ssl_certs=False,
)

def clean_line(line: str) -> str:
    """Удаляет лишние пробелы и символы по краям строки."""
    return line.strip()


def is_header(line: str) -> bool:
    """Эвристика: строка выглядит как заголовок (в основном прописные буквы)."""
    return bool(re.match(r"^[A-Z\u0401-\u042F\s]+$", line)) and len(line) > 3


def format_extracted_text(text: str) -> str:
    """Форматирует извлечённый текст из PDF в Markdown-подобный вид."""
    lines = text.split("\n")
    formatted_lines: list[str] = []
    inside_header = False

    for line in lines:
        line = clean_line(line)
        if is_header(line):
            formatted_lines.append(f"\n# {line}\n\n")
            inside_header = True
            continue

        if not line:
            continue

        numbered_match = re.match(r"^(\d+\.\s)(.+)", line)
        if numbered_match:
            formatted_lines.append(f"{numbered_match.group(1)}{numbered_match.group(2)}\n")
            inside_header = False
            continue

        if re.match(r"^[•·]\s", line):
            formatted_lines.append(f"- {line[2:]}\n")
            inside_header = False
            continue

        if inside_header:
            formatted_lines.append(f"\n{line}\n")
            inside_header = False
        else:
            formatted_lines.append(f"{line} ")

    return "".join(formatted_lines)


def process_pdf_to_text(pdf_path: str) -> str:
    """Парсит PDF-файл и преобразует его в текст (с форматированием)."""
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content += format_extracted_text(text)
    return text_content


def _source_key(pdf_path_obj: Path) -> str:
    """Уникальный ключ источника (относительный путь от PROJECT_DIR)."""
    try:
        return str(pdf_path_obj.resolve().relative_to(PROJECT_DIR))
    except ValueError:
        return pdf_path_obj.name


def _collection_name(pdf_path_obj: Path) -> str:
    """Имя коллекции Chroma на основе имени PDF файла."""
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", pdf_path_obj.stem[:50])
    return name.strip("_") or "doc"


def init_vectorstore(pdf_path: str) -> Chroma:
    """Инициализирует или загружает векторное хранилище для PDF.

    Логика:
    - считаем md5 хэш PDF;
    - сверяемся с SQLite состоянием индекса (hash + параметры чанкинга);
    - если индекс валиден и persisted хранилище есть на диске, просто загружаем;
    - иначе переиндексируем: парсим PDF, чанкуем, считаем эмбеддинги, пишем Chroma, обновляем состояние.
    """
    pdf_path_obj = Path(pdf_path)

    md5_hash = hashlib.md5()
    with open(pdf_path_obj, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    pdf_hash = md5_hash.hexdigest()

    persist_root = PROJECT_DIR / "storage" / "chroma"
    source_key = _source_key(pdf_path_obj)
    collection = _collection_name(pdf_path_obj)
    persist_dir = persist_root / collection
    persist_dir.mkdir(parents=True, exist_ok=True)
    version_file = persist_dir / "metadata_version.txt"

    state = get_state(PROJECT_DIR, collection, source_key)
    need_reindex = True
    if state is not None:
        stored_version = None
        if version_file.exists():
            try:
                stored_version = int(version_file.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                stored_version = None
        if (
            state["pdf_hash"] == pdf_hash
            and state["chunk_size"] == CHUNK_SIZE
            and state["chunk_overlap"] == CHUNK_OVERLAP
            and (persist_dir / "chroma.sqlite3").exists()
            and stored_version == INDEX_METADATA_VERSION
        ):
            need_reindex = False

    if not need_reindex:
        return Chroma(
            collection_name=collection,
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
        )

    # Переиндексация: очищаем persisted директорию коллекции.
    if persist_dir.exists():
        import shutil

        shutil.rmtree(persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

    documents: list[Document] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text:
                documents.append(
                    Document(
                        page_content=format_extracted_text(text),
                        metadata={"page": page_num, "source_pdf": source_key},
                    )
                )

    if not documents:
        raise ValueError(f"В PDF '{pdf_path_obj.name}' не найден извлекаемый текст.")

    separators = ["\n# ", "\n## ", "\n### ", "\n\n", "\n", ". ", "! ", "? ", ""]
    splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        keep_separator=True,
    )

    split_docs = splitter.split_documents(documents)

    for i, doc in enumerate(split_docs):
        doc.metadata["chunk_id"] = str(i)
        doc.metadata["total_chunks"] = len(split_docs)

    vectorstore = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    batch_size = 64
    for start in range(0, len(split_docs), batch_size):
        batch = split_docs[start : start + batch_size]
        vectorstore.add_documents(batch)

    version_file.write_text(str(INDEX_METADATA_VERSION), encoding="utf-8")

    upsert_state(
        PROJECT_DIR,
        {
            "collection_name": collection,
            "source_pdf": source_key,
            "pdf_hash": pdf_hash,
            "total_chunks": len(split_docs),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
        },
    )

    return vectorstore


def init_all_vectorstores() -> dict[str, Chroma]:
    """Инициализирует векторные хранилища для всех PDF из папки assets/."""
    assets_dir = PROJECT_DIR / "assets"
    vectorstores: dict[str, Chroma] = {}

    if not assets_dir.exists():
        return vectorstores

    for pdf_file in sorted(assets_dir.glob("*.pdf")):
        source_key = _source_key(pdf_file)
        vectorstore = init_vectorstore(str(pdf_file))
        vectorstores[source_key] = vectorstore

    return vectorstores


_vectorstores: dict[str, Chroma] = {}
_retrievers: dict[tuple[str, int, str], object] = {}


def get_vectorstore(source_pdf: str | None = None) -> Chroma:
    """Возвращает векторное хранилище для PDF с кэшированием в памяти."""
    global _vectorstores

    if source_pdf is None:
        assets_dir = PROJECT_DIR / "assets"
        pdf_files = sorted(assets_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"В папке assets нет PDF: {assets_dir}")
        source_pdf = _source_key(pdf_files[0])

    if source_pdf not in _vectorstores:
        pdf_path = PROJECT_DIR / source_pdf
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF не найден: {source_pdf}")
        _vectorstores[source_pdf] = init_vectorstore(str(pdf_path))

    return _vectorstores[source_pdf]


def get_retriever(
    source_pdf: str | None = None,
    k: int = 6,
    search_type: str = "mmr",
):
    """Возвращает retriever для поиска по векторному индексу с кэшированием."""
    global _retrievers

    if source_pdf is None:
        assets_dir = PROJECT_DIR / "assets"
        pdf_files = sorted(assets_dir.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"В папке assets нет PDF: {assets_dir}")
        source_pdf = _source_key(pdf_files[0])

    cache_key = (source_pdf, int(k), search_type)
    if cache_key in _retrievers:
        return _retrievers[cache_key]

    vectorstore = get_vectorstore(source_pdf=source_pdf)
    search_kwargs: dict[str, int] = {"k": int(k)}
    if search_type == "mmr":
        search_kwargs["fetch_k"] = max(20, int(k) * 3)

    retriever = vectorstore.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs,
    )
    _retrievers[cache_key] = retriever
    return retriever
