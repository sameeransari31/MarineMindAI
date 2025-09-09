from langchain.schema import Document, BaseRetriever
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from typing import List, Optional, Any, Dict, Tuple
from datetime import datetime
import logging
import re
import math

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        vectorstore: Any,
        llm: Optional[Any] = None,
        enable_debug: bool = False,
        strategy: Optional[Dict[str, bool]] = None,
    ):
        """
        strategy: configure which retrieval functions to use
        Example:
        strategy = {
            'similarity': True,
            'hybrid': True,
            'weighted': True,
            'mmr': False,
            'contextual': False,
            'semantic_expansion': True
        }
        """
        self.vectorstore = vectorstore
        self.llm = llm
        self.enable_debug = enable_debug
        self.strategy = strategy or {
            'similarity': True,
            'hybrid': True,
            'weighted': True,
            'mmr': True,
            'contextual': False,
            'semantic_expansion': True
        }

    def _get_relevant_documents(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        docs = self.multi_stage_search(query, k=k)
        if run_manager:
            run_manager.on_retriever_end(docs)
        return docs


    def similarity_search(self, query: str, k: int = 5, score_threshold: Optional[float] = None, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        final_results = []
        for doc, score in results:
            if score_threshold and score < score_threshold:
                continue
            if filters and not all(doc.metadata.get(k) == v for k, v in filters.items()):
                continue
            if self.enable_debug:
                logging.info(f"[SIMILARITY] Score={score:.4f}, Metadata={doc.metadata}")
            final_results.append(doc)
        return final_results

    def max_marginal_relevance_search(self, query: str, k: int = 5, lambda_mult: float = 0.5) -> List[Document]:
        return self.vectorstore.max_marginal_relevance_search(query, k=k, lambda_mult=lambda_mult)

    def hybrid_search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        vector_results = self.vectorstore.similarity_search_with_score(query, k=k * 2)
        keywords = set(re.findall(r"\w+", query.lower()))
        ranked = []
        for doc, vec_score in vector_results:
            doc_tokens = set(re.findall(r"\w+", doc.page_content.lower()))
            keyword_overlap = len(keywords & doc_tokens) / (len(keywords) + 1e-5)
            final_score = 0.7 * vec_score + 0.3 * keyword_overlap
            ranked.append((doc, final_score))
        ranked = sorted(ranked, key=lambda x: x[1], reverse=True)
        self.log_results(ranked[:k], label="HYBRID")
        return ranked[:k]

    def weighted_search(self, query: str, k: int = 5, weights: Dict[str, float] = None) -> List[Tuple[Document, float]]:
        weights = weights or {"similarity": 0.7, "recency": 0.2, "priority": 0.1}
        results = self.vectorstore.similarity_search_with_score(query, k=k * 2)
        scored = []
        for doc, sim_score in results:
            recency_score = self._temporal_decay(doc.metadata.get("date", ""))
            priority_score = float(doc.metadata.get("priority", 0))
            final_score = (
                weights["similarity"] * sim_score
                + weights["recency"] * recency_score
                + weights["priority"] * priority_score
            )
            scored.append((doc, final_score))
        scored = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
        self.log_results(scored, label="WEIGHTED")
        return scored

    def contextual_weighted_search(self, query: str, k: int = 5, metadata_weights: Dict[str, float] = None) -> List[Tuple[Document, float]]:
        metadata_weights = metadata_weights or {}
        results = self.vectorstore.similarity_search_with_score(query, k=k * 2)
        scored = []
        for doc, sim_score in results:
            meta_score = sum(
                metadata_weights.get(key, 0) * float(doc.metadata.get(key, 0))
                for key in metadata_weights
            )
            final_score = sim_score + meta_score
            scored.append((doc, final_score))
        scored = sorted(scored, key=lambda x: x[1], reverse=True)[:k]
        self.log_results(scored, label="CONTEXTUAL")
        return scored


    def semantic_expansion(self, query: str, k: int = 5) -> List[Document]:
        if not self.llm:
            logging.warning("[LLM Expansion Skipped] No LLM instance set.")
            return self.query_expansion(query, expansions=[], k=k)
        prompt = PromptTemplate.from_template("Expand this query for better search: {query}")
        try:
            response = self.llm.invoke(prompt.format(query=query))
            expansions = response.content.split(",") if hasattr(response, "content") else str(response).split(",")
        except Exception as e:
            logging.warning(f"[LLM Expansion Failed] {e}")
            expansions = []
        return self.query_expansion(query, expansions=expansions, k=k)

    def query_expansion(self, query: str, expansions: Optional[List[str]] = None, k: int = 5) -> List[Document]:
        queries = [query] + (expansions or [])
        results = []
        for q in queries:
            results.extend(self.vectorstore.similarity_search(q, k=k))
        seen, unique = set(), []
        for doc in results:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique.append(doc)
        if self.enable_debug:
            logging.info(f"[EXPANSION] Queries: {queries}")
        return unique[:k]


    def multi_stage_search(self, query: str, k: int = 5) -> List[Document]:
        stages = []

        if self.strategy.get('semantic_expansion'):
            stages.extend(self.semantic_expansion(query, k=k))
        if self.strategy.get('hybrid'):
            stages.extend([doc for doc, _ in self.hybrid_search(query, k=k)])
        if self.strategy.get('weighted'):
            stages.extend([doc for doc, _ in self.weighted_search(query, k=k)])
        if self.strategy.get('similarity'):
            stages.extend(self.similarity_search(query, k=k))
        if self.strategy.get('mmr'):
            stages.extend(self.max_marginal_relevance_search(query, k=k))
        if self.strategy.get('contextual'):
            stages.extend([doc for doc, _ in self.contextual_weighted_search(query, k=k)])


        combined = {}
        for doc in stages:
            combined[doc.page_content] = doc

        final_docs = list(combined.values())[:k]
        if self.enable_debug:
            logging.info(f"[MULTI-STAGE] Final count: {len(final_docs)}")
        return final_docs


    def _temporal_decay(self, date_str: str, half_life_days: int = 180) -> float:
        try:
            doc_date = datetime.strptime(date_str, "%Y-%m-%d")
            age_days = (datetime.now() - doc_date).days
            return math.exp(-age_days / half_life_days)
        except Exception:
            return 0.0

    def log_results(self, results: List[Tuple[Document, float]], label: str = "RESULTS"):
        if self.enable_debug:
            logging.info(f"[{label}] Top {len(results)} documents:")
            for i, (doc, score) in enumerate(results):
                logging.info(f"  {i+1}. Score={score:.4f}, Metadata={doc.metadata}")