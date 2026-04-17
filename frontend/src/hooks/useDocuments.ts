import { useState, useEffect, useCallback } from 'react';
import type { Document } from '@/types';
import { fetchDocuments, uploadDocument, deleteDocument } from '@/api';

interface UseDocumentsReturn {
  documents: Document[];
  isLoading: boolean;
  isUploading: boolean;
  isDeleting: string | null;
  error: string | null;
  upload: (file: File, title?: string) => Promise<boolean>;
  remove: (documentId: string) => Promise<boolean>;
  refresh: () => Promise<void>;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      setError(null);
    } catch {
      setError('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upload = useCallback(
    async (file: File, title?: string): Promise<boolean> => {
      setIsUploading(true);
      setError(null);
      try {
        await uploadDocument(file, title);
        // Refresh list after a short delay to let processing start
        setTimeout(() => void refresh(), 2000);
        return true;
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Upload failed';
        setError(errMsg);
        return false;
      } finally {
        setIsUploading(false);
      }
    },
    [refresh]
  );

  const remove = useCallback(
    async (documentId: string): Promise<boolean> => {
      setIsDeleting(documentId);
      setError(null);
      try {
        await deleteDocument(documentId);
        setDocuments((prev) => prev.filter((d) => d.id !== documentId));
        return true;
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Delete failed';
        setError(errMsg);
        return false;
      } finally {
        setIsDeleting(null);
      }
    },
    []
  );

  return { documents, isLoading, isUploading, isDeleting, error, upload, remove, refresh };
}
