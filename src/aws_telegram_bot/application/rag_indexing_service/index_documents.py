import collections
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from aws_telegram_bot.config import settings
from aws_telegram_bot.infrastructure.clients.qdrant import get_qdrant_client

def generate_split_documents():
    loader = PyMuPDFLoader("./data/george_biography.pdf")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    docs = loader.load()
    all_splits = text_splitter.split_documents(docs)

    return all_splits

def index_documents():
    all_splits = generate_split_documents()
    embeddings = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL, api_key=settings.OPENAI_API_KEY)

    QdrantVectorStore.from_documents(
        documents=all_splits,
        embedding=embeddings,
        url=settings.QDRANT_URL,
        collection_name="aws_telegram_bot_collection"
    )

    logger.info("Documents indexed successfully.")