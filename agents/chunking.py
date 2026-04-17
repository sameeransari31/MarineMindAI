"""
Document chunking utilities for the RAG pipeline.
Uses LangChain text splitters for intelligent chunking of large documents.
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_document(text: str, document_id: str, source: str, chunk_size: int = 800, chunk_overlap: int = 200, page_char_offsets: list[dict] | None = None) -> list[dict]:
    """
    Split a document into chunks with metadata.
    
    Args:
        text: Full document text.
        document_id: Unique ID for the document.
        source: Source filename or identifier.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between consecutive chunks.
        page_char_offsets: Optional list of {"page": int, "start": int, "end": int}
                          for mapping chunk positions to page numbers.
    
    Returns:
        List of dicts with "text" and "metadata" keys.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    splits = splitter.split_text(text)

    # Build a simple index to find each split's start position in the original text
    split_positions = []
    search_start = 0
    for split_text in splits:
        pos = text.find(split_text, search_start)
        split_positions.append(pos if pos != -1 else search_start)
        if pos != -1:
            search_start = pos + 1

    chunks = []
    for i, split_text in enumerate(splits):
        meta = {
            "document_id": document_id,
            "source": source,
            "chunk_index": i,
            "total_chunks": len(splits),
        }

        # Resolve page number from character offset
        if page_char_offsets and i < len(split_positions):
            char_pos = split_positions[i]
            for page_info in page_char_offsets:
                if page_info["start"] <= char_pos < page_info["end"]:
                    meta["page"] = page_info["page"]
                    break

        chunks.append({
            "text": split_text,
            "metadata": meta,
        })

    return chunks
