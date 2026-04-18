"""Модуль для работы с SQLite базой данных состояния индекса."""

import sqlite3
from pathlib import Path
from typing import Optional


def ensure_db(project_dir: Path) -> Path:
    """Создаёт папку, файл БД и таблицу. Возвращает путь к sqlite3.

    Args:
        project_dir: Путь к корню проекта (research_agent)

    Returns:
        Путь к файлу БД index_state.sqlite3
    """
    # База данных создаётся в папке storage, где находится этот скрипт
    storage_dir = Path(__file__).parent
    storage_dir.mkdir(parents=True, exist_ok=True)

    db_path = storage_dir / "index_state.sqlite3"

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_state (
                collection_name TEXT NOT NULL,
                source_pdf TEXT NOT NULL,
                pdf_hash TEXT NOT NULL,
                total_chunks INTEGER NOT NULL,
                chunk_size INTEGER NOT NULL,
                chunk_overlap INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (collection_name, source_pdf)
            )
        """)
        conn.commit()

    return db_path


def get_state(
        project_dir: Path,
        collection_name: str,
        source_pdf: str
) -> Optional[dict]:
    """Возвращает состояние индекса или None.

    Args:
        project_dir: Путь к корню проекта (research_agent)
        collection_name: Имя коллекции
        source_pdf: Имя PDF файла

    Returns:
        Словарь с полями состояния или None, если запись не найдена
    """
    ensure_db(project_dir)
    # База данных находится в папке storage, где находится этот скрипт
    db_path = Path(__file__).parent / "index_state.sqlite3"

    if not db_path.exists():
        return None

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                collection_name,
                source_pdf,
                pdf_hash,
                total_chunks,
                chunk_size,
                chunk_overlap,
                updated_at
            FROM index_state
            WHERE collection_name = ? AND source_pdf = ?
        """, (collection_name, source_pdf))

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def upsert_state(project_dir: Path, state_dict: dict) -> None:
    """Вставляет или обновляет запись состояния индекса.

    Args:
        project_dir: Путь к корню проекта (research_agent)
        state_dict: Словарь с полями:
            - collection_name: str
            - source_pdf: str
            - pdf_hash: str
            - total_chunks: int
            - chunk_size: int
            - chunk_overlap: int
    """
    ensure_db(project_dir)
    # База данных находится в папке storage, где находится этот скрипт
    db_path = Path(__file__).parent / "index_state.sqlite3"

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO index_state (
                collection_name,
                source_pdf,
                pdf_hash,
                total_chunks,
                chunk_size,
                chunk_overlap,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(collection_name, source_pdf) DO UPDATE SET
                pdf_hash = excluded.pdf_hash,
                total_chunks = excluded.total_chunks,
                chunk_size = excluded.chunk_size,
                chunk_overlap = excluded.chunk_overlap,
                updated_at = datetime('now')
        """, (
            state_dict["collection_name"],
            state_dict["source_pdf"],
            state_dict["pdf_hash"],
            state_dict["total_chunks"],
            state_dict["chunk_size"],
            state_dict["chunk_overlap"],
        ))
        conn.commit()


if __name__ == "__main__":
    # Файл находится в storage/, база данных создаётся в той же папке
    PROJECT_DIR = Path(__file__).resolve().parents[1]  # research_agent/
    db_path = ensure_db(PROJECT_DIR)
    if db_path.exists():
        print(f"OK: created/exists - {db_path}")
    else:
        print(f"ERROR: failed to create {db_path}")
        exit(1)
