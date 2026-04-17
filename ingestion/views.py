import json
import os
import logging
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from ingestion.models import Document
from ingestion.services import process_document

logger = logging.getLogger(__name__)


def upload_page(request):
    """Render the document upload page."""
    documents = Document.objects.all()[:50]
    return render(request, 'ingestion/upload.html', {'documents': documents})


@csrf_exempt
@require_http_methods(["POST"])
def api_upload(request):
    """
    Upload a PDF document for ingestion into the RAG pipeline.
    Processes in a background thread to avoid blocking.
    """
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    # Validate file extension
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext != '.pdf':
        return JsonResponse({"error": "Only PDF files are supported"}, status=400)

    # Validate file size (max 50MB)
    if uploaded_file.size > 50 * 1024 * 1024:
        return JsonResponse({"error": "File too large (max 50MB)"}, status=400)

    title = request.POST.get('title', uploaded_file.name)

    doc = Document.objects.create(
        title=title,
        file=uploaded_file,
        file_type=ext,
        file_size=uploaded_file.size,
    )

    # Process in background thread
    thread = threading.Thread(target=process_document, args=(doc,), daemon=True)
    thread.start()

    return JsonResponse({
        "message": "Document uploaded and processing started",
        "document_id": str(doc.id),
        "title": doc.title,
        "status": doc.status,
    })


@require_http_methods(["GET"])
def api_documents(request):
    """List all uploaded documents."""
    docs = Document.objects.all()[:50]
    data = [
        {
            "id": str(d.id),
            "title": d.title,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "total_pages": d.total_pages,
            "total_chunks": d.total_chunks,
            "status": d.status,
            "uploaded_at": d.uploaded_at.isoformat(),
        }
        for d in docs
    ]
    return JsonResponse({"documents": data})


@require_http_methods(["GET"])
def api_document_status(request, document_id):
    """Check processing status of a document."""
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found"}, status=404)

    return JsonResponse({
        "id": str(doc.id),
        "title": doc.title,
        "status": doc.status,
        "total_pages": doc.total_pages,
        "total_chunks": doc.total_chunks,
        "error_message": doc.error_message,
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_document(request, document_id):
    """
    Delete a document and remove its vectors from Pinecone.
    Also deletes the uploaded file from disk.
    """
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"error": "Document not found"}, status=404)

    doc_title = doc.title
    doc_id_str = str(doc.id)

    # Delete vectors from Pinecone
    vectors_deleted = 0
    try:
        from agents.vector_store import delete_vectors_by_document
        vectors_deleted = delete_vectors_by_document(doc_id_str)
    except Exception as e:
        logger.warning(f"Failed to delete vectors for {doc_id_str}: {e}")

    # Delete the physical file
    if doc.file:
        try:
            doc.file.delete(save=False)
        except Exception as e:
            logger.warning(f"Failed to delete file for {doc_id_str}: {e}")

    # Delete the database record
    doc.delete()

    return JsonResponse({
        "message": f"Document '{doc_title}' deleted successfully",
        "vectors_deleted": vectors_deleted,
    })
