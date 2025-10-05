# bot/rag/vector_store.py
import logging
from typing import List, Dict
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Путь к векторной БД
CHROMA_PATH = Path("chroma_db")

# Глобальные объекты
CHROMA_CLIENT = None
COLLECTION = None
MODEL = None

async def init_vector_store():
    """Инициализирует Chroma и модель эмбеддингов."""
    global CHROMA_CLIENT, COLLECTION, MODEL
    try:
        # Инициализация модели
        logger.info("Загрузка модели эмбеддингов...")
        MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("✅ Модель эмбеддингов загружена.")

        # Инициализация Chroma
        logger.info("Инициализация Chroma...")
        CHROMA_CLIENT = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        COLLECTION = CHROMA_CLIENT.get_or_create_collection(name="faq")
        logger.info("✅ Chroma инициализирована.")
    except Exception as e:
        logger.error(f"Ошибка инициализации векторной БД: {e}", exc_info=True)
        raise

def add_faq_entries(entries: List[Dict[str, str]]):
    """Добавляет записи FAQ в векторную БД."""
    if not COLLECTION or not MODEL:
        raise RuntimeError("Векторная БД не инициализирована.")

    ids = []
    texts = []
    metadatas = []
    for i, entry in enumerate(entries):
        q = entry.get("question", "").strip()
        a = entry.get("answer", "").strip()
        if not q or not a:
            continue
        ids.append(str(i))
        texts.append(q)
        metadatas.append({"question": q, "answer": a})

    if not ids:
        logger.warning("Нет корректных записей для добавления в векторную БД.")
        return

    # Получаем эмбеддинги
    embeddings = MODEL.encode(texts)
    COLLECTION.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
        documents=texts
    )
    logger.info(f"Добавлено {len(ids)} записей в векторную БД.")

def search_similar_questions(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """Ищет похожие вопросы в векторной БД."""
    if not COLLECTION or not MODEL:
        raise RuntimeError("Векторная БД не инициализирована.")

    # Получаем эмбеддинг запроса
    query_embedding = MODEL.encode([query])
    
    # Поиск
    results = COLLECTION.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k
    )

    # Формируем список результатов
    similar = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        similar.append({
            "question": meta["question"],
            "answer": meta["answer"],
            "distance": results["distances"][0][i]
        })
    
    return similar