import json
from types import SimpleNamespace

import pytest

from backend import search
from backend.search import (
    build_citations,
    build_grounded_messages,
    build_search_text,
    retrieve,
)


def make_datasource(**overrides):
    values = {
        "content_columns": None,
        "title_column": None,
        "url_column": None,
        "filename_column": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_search_text_uses_last_user_message():
    messages = [{"role": "user", "content": "  ContractStateActivityAllocation  "}]
    assert build_search_text(messages) == "ContractStateActivityAllocation"


def test_build_search_text_repeated_question_matches_first_question():
    first = [{"role": "user", "content": "ContractStateActivityAllocation"}]
    repeated = first + [
        {"role": "assistant", "content": "I could not find anything about that in the AdInsure documentation."},
        {"role": "user", "content": "ContractStateActivityAllocation"},
    ]
    assert build_search_text(repeated) == build_search_text(first)


def test_build_search_text_adds_previous_question_for_follow_up():
    messages = [
        {"role": "user", "content": "What is a product configuration?"},
        {"role": "assistant", "content": "It is ..."},
        {"role": "user", "content": "How do I deploy it?"},
    ]
    assert build_search_text(messages) == "What is a product configuration?\nHow do I deploy it?"


def test_build_search_text_without_user_message():
    assert build_search_text([{"role": "assistant", "content": "Hi"}]) is None


def test_build_citations_defaults():
    documents = [
        {"chunk": "first chunk", "title": "a/_index.md"},
        {"chunk": "second chunk", "title": "b.md"},
    ]
    citations = build_citations(documents, make_datasource())

    assert [c["content"] for c in citations] == ["first chunk", "second chunk"]
    assert [c["title"] for c in citations] == ["a/_index.md", "b.md"]
    assert [c["filepath"] for c in citations] == ["a/_index.md", "b.md"]
    assert [c["id"] for c in citations] == ["1", "2"]
    assert citations[0]["url"] is None


def test_build_citations_configured_columns():
    documents = [{"body": "text", "heading": "Title", "link": "https://x/doc.md", "path": "doc.md"}]
    datasource = make_datasource(
        content_columns=["body"], title_column="heading", url_column="link", filename_column="path"
    )
    citation = build_citations(documents, datasource)[0]

    assert citation["content"] == "text"
    assert citation["title"] == "Title"
    assert citation["url"] == "https://x/doc.md"
    assert citation["filepath"] == "doc.md"


def test_build_grounded_messages_numbers_documents():
    citations = [
        {"title": "A", "content": "alpha"},
        {"title": "B", "content": "beta"},
    ]
    messages = [{"role": "user", "content": "question"}]
    result = build_grounded_messages("System prompt.", citations, messages)

    assert result[0]["role"] == "system"
    assert result[0]["content"].startswith("System prompt.")
    assert "[doc1] A\nalpha" in result[0]["content"]
    assert "[doc2] B\nbeta" in result[0]["content"]
    assert result[1:] == messages


def test_build_grounded_messages_without_documents():
    result = build_grounded_messages("System prompt.", [], [{"role": "user", "content": "q"}])
    assert "No documents were found." in result[0]["content"]


@pytest.mark.asyncio
async def test_retrieve_returns_citations_and_intent(monkeypatch):
    calls = []

    async def fake_search_documents(openai_client, app_settings, search_text):
        calls.append(search_text)
        return [{"chunk": "content", "title": "doc.md"}]

    monkeypatch.setattr(search, "search_documents", fake_search_documents)
    app_settings = SimpleNamespace(datasource=make_datasource())

    context = await retrieve(None, app_settings, [{"role": "user", "content": "question"}])

    assert calls == ["question"]
    assert json.loads(context["intent"]) == ["question"]
    assert context["citations"][0]["content"] == "content"
