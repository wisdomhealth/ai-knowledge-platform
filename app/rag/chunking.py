from llama_index.core.node_parser import TokenTextSplitter


def chunk_text(text: str, *, max_chars: int = 1600, overlap: int = 200) -> list[str]:
    if max_chars < 1 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Require 0 <= overlap < max_chars.")
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    # Character tokenizer preserves the existing size units and avoids downloading
    # token vocabularies. LlamaIndex owns split/overlap construction.
    splitter = TokenTextSplitter(chunk_size=max_chars, chunk_overlap=overlap, tokenizer=list)
    return splitter.split_text(cleaned)
