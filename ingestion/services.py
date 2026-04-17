"""
Document processing service — extracts text from PDFs, chunks, and stores in Pinecone.
"""
import logging
from django.utils import timezone
from pypdf import PdfReader
from agents.chunking import chunk_document
from agents.vector_store import upsert_vectors

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.pdf'}


def process_document(document) -> None:
    """
    Process an uploaded document:
      1. Extract text from PDF
      2. Chunk the text
      3. Generate embeddings and store in Pinecone
      4. Update document status
    """
    from ingestion.models import Document

    document.status = 'processing'
    document.error_message = ''
    document.save(update_fields=['status', 'error_message'])

    try:
        file_path = document.file.path
        ext = '.' + file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Only PDF files are supported.")

        # Extract text from PDF
        reader = PdfReader(file_path)
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)

        if not pages_text:
            raise ValueError("Could not extract any text from the PDF.")

        full_text = "\n\n".join(pages_text)
        document.total_pages = len(reader.pages)

        # Compute page character offsets for chunk-to-page mapping
        page_char_offsets = []
        offset = 0
        for i, page_text in enumerate(pages_text):
            page_char_offsets.append({
                "page": i + 1,
                "start": offset,
                "end": offset + len(page_text),
            })
            offset += len(page_text) + 2  # +2 for the "\n\n" separator

        # Chunk the document
        chunks = chunk_document(
            text=full_text,
            document_id=str(document.id),
            source=document.title,
            page_char_offsets=page_char_offsets,
        )

        if not chunks:
            raise ValueError("Document produced no chunks after splitting.")

        document.total_chunks = len(chunks)

        # Upsert to Pinecone (non-blocking: document succeeds even if vector store is unavailable)
        try:
            upsert_vectors(chunks)
            document.embedding_status = 'completed'
            logger.info(f"Document '{document.title}' vectors upserted successfully")
        except Exception as vec_err:
            logger.warning(f"Vector upsert failed for '{document.title}': {vec_err}")
            document.embedding_status = 'failed'
            document.error_message = f"Document processed but vector storage failed: {vec_err}"

        document.status = 'completed'
        document.processed_at = timezone.now()
        document.save(update_fields=['status', 'total_pages', 'total_chunks', 'processed_at', 'embedding_status', 'error_message'])

        logger.info(f"Document '{document.title}' processed: {len(chunks)} chunks, {len(reader.pages)} pages")

    except Exception as e:
        logger.error(f"Error processing document '{document.title}': {e}")
        document.status = 'failed'
        document.error_message = str(e)
        document.save(update_fields=['status', 'error_message'])

        # Generate ingestion failure alert
        try:
            from dashboard.alert_engine import alert_ingestion_failure
            alert_ingestion_failure(document)
        except Exception as alert_err:
            logger.error(f"Alert generation failed: {alert_err}")
