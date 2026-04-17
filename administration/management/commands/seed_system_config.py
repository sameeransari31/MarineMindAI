"""
Seed sensible default SystemConfig entries so admins can tune the RAG pipeline
from the admin panel without touching code or .env files.
"""
from django.core.management.base import BaseCommand
from administration.models import SystemConfig


DEFAULT_CONFIGS = [
    # Chunking
    {'key': 'chunk_size', 'value': '800', 'value_type': 'integer',
     'category': 'chunking', 'description': 'Target chunk size in characters for document splitting.'},
    {'key': 'chunk_overlap', 'value': '200', 'value_type': 'integer',
     'category': 'chunking', 'description': 'Overlap between consecutive chunks in characters.'},

    # Retrieval
    {'key': 'retrieval_top_k', 'value': '8', 'value_type': 'integer',
     'category': 'retrieval', 'description': 'Number of candidate chunks to retrieve per query.'},
    {'key': 'retrieval_final_top_k', 'value': '5', 'value_type': 'integer',
     'category': 'retrieval', 'description': 'Number of final chunks after reranking.'},
    {'key': 'max_query_expansions', 'value': '4', 'value_type': 'integer',
     'category': 'retrieval', 'description': 'Maximum number of expanded search queries in multi-query retrieval.'},

    # Reranking
    {'key': 'rerank_relevance_threshold', 'value': '0.1', 'value_type': 'float',
     'category': 'reranking', 'description': 'Minimum cross-encoder score to keep a chunk after reranking.'},

    # LLM Model
    {'key': 'llm_temperature', 'value': '0.3', 'value_type': 'float',
     'category': 'model', 'description': 'Default LLM sampling temperature for generation.'},
    {'key': 'llm_max_tokens', 'value': '1024', 'value_type': 'integer',
     'category': 'model', 'description': 'Maximum tokens in LLM response.'},
    {'key': 'guardrails_temperature', 'value': '0.0', 'value_type': 'float',
     'category': 'model', 'description': 'LLM temperature for guardrails classification (deterministic).'},
    {'key': 'router_temperature', 'value': '0.0', 'value_type': 'float',
     'category': 'model', 'description': 'LLM temperature for routing classification (deterministic).'},

    # Embedding
    {'key': 'embedding_model_name', 'value': 'all-MiniLM-L6-v2', 'value_type': 'string',
     'category': 'embedding', 'description': 'Sentence-transformers model used for document embeddings.'},
    {'key': 'embedding_dimension', 'value': '384', 'value_type': 'integer',
     'category': 'embedding', 'description': 'Vector dimension of the embedding model.'},

    # Reranking model
    {'key': 'reranker_model_name', 'value': 'cross-encoder/ms-marco-MiniLM-L-6-v2', 'value_type': 'string',
     'category': 'reranking', 'description': 'Cross-encoder model used for reranking retrieved chunks.'},

    # Search
    {'key': 'tavily_max_results', 'value': '5', 'value_type': 'integer',
     'category': 'search', 'description': 'Maximum number of results from Tavily internet search.'},
    {'key': 'tavily_search_depth', 'value': 'advanced', 'value_type': 'string',
     'category': 'search', 'description': 'Tavily search depth: basic or advanced.'},

    # General
    {'key': 'max_upload_size_mb', 'value': '50', 'value_type': 'integer',
     'category': 'general', 'description': 'Maximum file upload size in megabytes.'},
    {'key': 'max_query_length', 'value': '5000', 'value_type': 'integer',
     'category': 'general', 'description': 'Maximum user query length in characters.'},
]


class Command(BaseCommand):
    help = 'Seed default SystemConfig entries for the MarineMind admin panel.'

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for config in DEFAULT_CONFIGS:
            _, created = SystemConfig.objects.get_or_create(
                key=config['key'],
                defaults={
                    'value': config['value'],
                    'value_type': config['value_type'],
                    'category': config['category'],
                    'description': config['description'],
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created {created_count} config(s), skipped {skipped_count} existing.'
            )
        )
