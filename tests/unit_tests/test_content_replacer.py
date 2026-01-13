import copy

from app import ContentReplacer


def test_content_replacer_flush_preserves_metadata_and_content_reassembly():
    replacer = ContentReplacer({".md": "", "_index/": ""})

    original_chunk = {
        "id": "chunk-id",
        "model": "test-model",
        "apim-request-id": "req-123",
        "history_metadata": {"conversation_id": "conv-1"},
        "choices": [
            {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "file.md _index/path",
                    }
                ]
            }
        ],
    }

    processed_chunk = replacer.process_chunk(copy.deepcopy(original_chunk))
    last_template = processed_chunk
    remaining = replacer.flush()

    final_chunk = copy.deepcopy(last_template)
    final_chunk = replacer._apply_to_content(final_chunk, remaining)

    # Metadata should be preserved on the flushed chunk
    assert final_chunk["id"] == original_chunk["id"]
    assert final_chunk["model"] == original_chunk["model"]
    assert final_chunk.get("apim-request-id") == original_chunk.get("apim-request-id")
    assert final_chunk.get("history_metadata") == original_chunk.get("history_metadata")

    # Content should be reconstructed with replacements applied
    part1 = replacer._extract_content(processed_chunk) or ""
    part2 = replacer._extract_content(final_chunk) or ""
    assert part1 + part2 == "file path"


def test_content_replacer_applies_replacements_without_empty_keys():
    # Ensure that replacements operate as expected when only explicit keys are provided.
    replacer = ContentReplacer({".md": ""})
    chunk = {
        "choices": [
            {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "docs.md",
                    }
                ]
            }
        ]
    }

    processed = replacer.process_chunk(copy.deepcopy(chunk))
    remaining = replacer.flush()
    combined = (replacer._extract_content(processed) or "") + (remaining or "")
    assert combined == "docs"
