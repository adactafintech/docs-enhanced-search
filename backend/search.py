"""Retrieval for the docs chat.

Azure OpenAI "On Your Data" (the `data_sources` parameter) has been retired,
so the app now searches Azure AI Search itself and passes the results to the
chat model as grounding. The search text is built from the user's own words
instead of an LLM-generated query, so the same question always retrieves the
same documents.
"""
import json
import logging
from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery

DEFAULT_CONTENT_COLUMN = "chunk"
DEFAULT_TITLE_COLUMN = "title"

GROUNDING_INSTRUCTIONS = (
    "Answer using only the documents below. Each document starts with its "
    "reference in square brackets, for example [doc1]. Cite every document you "
    "use by putting its reference right after the sentence it supports, for "
    "example [doc1][doc3]. Do not cite documents you did not use."
)


def build_search_text(messages: List[dict]) -> Optional[str]:
    """Return the text to search for, based on the user messages.

    The last user message is the question. When it is a follow-up, the
    previous user message is added so that short questions like "and how do I
    configure it?" still find the right topic.
    """
    user_messages = [
        m["content"] for m in messages
        if m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].strip()
    ]
    if not user_messages:
        return None

    question = user_messages[-1].strip()
    if len(user_messages) > 1:
        previous = user_messages[-2].strip()
        if previous.lower() != question.lower():
            return f"{previous}\n{question}"

    return question


def _first_value(document: dict, columns: List[str]) -> Optional[str]:
    for column in columns:
        value = document.get(column)
        if value:
            return value if isinstance(value, str) else str(value)
    return None


def _citation_columns(datasource):
    content_columns = datasource.content_columns or [DEFAULT_CONTENT_COLUMN]
    title_columns = [datasource.title_column or DEFAULT_TITLE_COLUMN]
    url_columns = [datasource.url_column] if datasource.url_column else []
    filepath_columns = [datasource.filename_column] if datasource.filename_column else []
    return content_columns, title_columns, url_columns, filepath_columns


def build_citations(documents: List[dict], datasource) -> List[dict]:
    """Map search documents to the citation shape the frontend expects."""
    content_columns, title_columns, url_columns, filepath_columns = _citation_columns(datasource)

    citations = []
    for index, document in enumerate(documents):
        content = "\n".join(
            str(document[column]) for column in content_columns if document.get(column)
        )
        title = _first_value(document, title_columns)
        url = _first_value(document, url_columns)
        filepath = _first_value(document, filepath_columns) or title
        citations.append({
            "content": content,
            "id": str(index + 1),
            "title": title,
            "filepath": filepath,
            "url": url,
            "metadata": None,
            "chunk_id": str(index),
        })

    return citations


def build_grounded_messages(system_message: str, citations: List[dict], messages: List[dict]) -> List[dict]:
    """Prepend the system message and the retrieved documents to the conversation."""
    if citations:
        documents = "\n\n".join(
            f"[doc{index + 1}] {citation['title'] or ''}\n{citation['content']}"
            for index, citation in enumerate(citations)
        )
    else:
        documents = "No documents were found."

    grounding = f"{system_message}\n\n{GROUNDING_INSTRUCTIONS}\n\nDocuments:\n{documents}"
    return [{"role": "system", "content": grounding}] + messages


async def _embed(openai_client, embedding_name: str, text: str, dimensions: Optional[int]) -> List[float]:
    kwargs = {"model": embedding_name, "input": text}
    if dimensions:
        kwargs["dimensions"] = dimensions
    response = await openai_client.embeddings.create(**kwargs)
    return response.data[0].embedding


async def search_documents(openai_client, app_settings, search_text: str) -> List[dict]:
    """Run the configured Azure AI Search query and return the raw documents."""
    datasource = app_settings.datasource
    query_type = datasource.query_type
    use_vector = query_type in ("vector", "vector_simple_hybrid", "vector_semantic_hybrid")
    use_text = query_type != "vector"
    use_semantic = query_type in ("semantic", "vector_semantic_hybrid")

    # Only fetch the fields used for citations, not the vectors
    select = list(dict.fromkeys(column for columns in _citation_columns(datasource) for column in columns))
    search_kwargs = {"top": datasource.top_k, "select": select}
    if datasource.filter:
        search_kwargs["filter"] = datasource.filter

    if use_vector:
        if not datasource.vector_columns:
            raise ValueError("AZURE_SEARCH_VECTOR_COLUMNS is required for vector queries")
        if not app_settings.azure_openai.embedding_name:
            raise ValueError("AZURE_OPENAI_EMBEDDING_NAME is required for vector queries")
        vector = await _embed(
            openai_client,
            app_settings.azure_openai.embedding_name,
            search_text,
            app_settings.search.vectorization_dimensions,
        )
        search_kwargs["vector_queries"] = [
            VectorizedQuery(
                vector=vector,
                k_nearest_neighbors=datasource.top_k,
                fields=",".join(datasource.vector_columns),
            )
        ]

    if use_semantic:
        search_kwargs["query_type"] = "semantic"
        search_kwargs["semantic_configuration_name"] = datasource.semantic_search_config

    if datasource.key:
        credential = AzureKeyCredential(datasource.key)
    else:
        credential = DefaultAzureCredential()

    try:
        async with SearchClient(datasource.endpoint, datasource.index, credential) as client:
            results = await client.search(search_text=search_text if use_text else None, **search_kwargs)
            documents = [document async for document in results]
    finally:
        if isinstance(credential, DefaultAzureCredential):
            await credential.close()

    logging.debug(f"SEARCH '{search_text}' returned {len(documents)} documents")
    return documents


async def retrieve(openai_client, app_settings, messages: List[dict]) -> dict:
    """Search for the conversation's question and return the tool context.

    The returned dict has the same shape On Your Data used for its `context`:
    `citations` for the frontend and `intent` with the search text that was used.
    """
    search_text = build_search_text(messages)
    if not search_text:
        return {"citations": [], "intent": "[]"}

    documents = await search_documents(openai_client, app_settings, search_text)
    citations = build_citations(documents, app_settings.datasource)
    return {"citations": citations, "intent": json.dumps([search_text])}
