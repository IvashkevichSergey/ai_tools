# Ретривер по документам с условиями кредитования.
# Использует эмбеддинги GigaChat и локальное векторное хранилище по учебному набору документов.

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_gigachat.embeddings import GigaChatEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

load_dotenv(Path(__file__).resolve().parents[1] / "config" / "demo_env.env")

from graph_demo.data.documents import documents

# Модель эмбеддингов указываем явно, чтобы настройка совпадала с остальными упражнениями линейки.
_embeddings = GigaChatEmbeddings(
    credentials=os.getenv("GIGACHAT_ACCESS_TOKEN"),
    scope=os.getenv("GIGACHAT_SCOPE"),
    base_url=os.getenv("GIGACHAT_BASE_URL"),
    model="EmbeddingsGigaR",
    verify_ssl_certs=False,
)
_vectorstore = InMemoryVectorStore.from_documents(documents, _embeddings)
retriever = _vectorstore.as_retriever(search_kwargs={"k": 2})

