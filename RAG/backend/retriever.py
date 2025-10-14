from langchain.schema import Document, BaseRetriever
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from typing import List, Optional, Any, Dict, Tuple
from datetime import datetime
import logging
import re
import math
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        vectorstore: Any,
        llm: Optional[Any] = None,
        enable_debug: bool = False,
        doc_sample: Optional[List[Document]] = None,
    ):
        """
        HybridRetriever:
        - Auto-selects strategies based on document metadata and length
        - Multi-stage retrieval
        - Normalized, weighted merging of results
        - Automatic stage weight tuning based on dataset
        """
        self.vectorstore = vectorstore
        self.llm = llm
        self.enable_debug = enable_debug
        self.strategy = self.auto_select_strategy(doc_sample or [])


        self.stage_weights = {
            'semantic_expansion': 0.2,
            'hybrid': 0.4,
            'weighted': 0.3,
            'similarity': 0.1,
            'mmr': 0.1,
            'contextual': 0.2
        }

        self.tune_stage_weights(doc_sample or [])


    def auto_select_strategy(self, docs: List[Document]) -> Dict[str, bool]:
        if not docs:
            return {
                'similarity': True,
                'hybrid': True,
                'weighted': True,
                'mmr': False,
                'contextual': False,
                'semantic_expansion': True
            }

        metadata_keys = set()
        avg_doc_length = 0
        for doc in docs:
            metadata_keys.update(doc.metadata.keys())
            avg_doc_length += len(doc.page_content)
        avg_doc_length /= max(len(docs),1)

        strategy = {
            'similarity': True,
            'hybrid': True,
            'weighted': 'date' in metadata_keys or 'priority' in metadata_keys,
            'contextual': any(k for k in metadata_keys if k not in ['date','priority']),
            'semantic_expansion': avg_doc_length < 300,
            'mmr': True
        }

        if self.enable_debug:
            logging.info(f"[AUTO-STRATEGY] Selected strategies: {strategy}")
        return strategy


    def tune_stage_weights(self, docs: List[Document]):
        if not docs:
            return

        stage_scores = defaultdict(float)
        total_docs = len(docs)


        stage_funcs = {
            'semantic_expansion': lambda q,k: self.semantic_expansion(q,k),
            'hybrid': lambda q,k: [doc for doc,_ in self.hybrid_search(q,k)],
            'weighted': lambda q,k: [doc for doc,_ in self.weighted_search(q,k)],
            'similarity': lambda q,k: self.similarity_search(q,k),
            'mmr': lambda q,k: self.max_marginal_relevance_search(q,k),
            'contextual': lambda q,k: [doc for doc,_ in self.contextual_weighted_search(q,k)]
        }

        for stage, func in stage_funcs.items():
            if not self.strategy.get(stage, False):
                continue
            count = 0
            for doc in docs[:5]:
                res = func(doc.page_content, k=3)
                count += len(res)
            stage_scores[stage] = count / (total_docs * 3)


        total_score = sum(stage_scores.values()) + 1e-5
        for stage in stage_scores:
            self.stage_weights[stage] = stage_scores[stage] / total_score

        if self.enable_debug:
            logging.info(f"[AUTO-WEIGHTS] Stage weights: {self.stage_weights}")


    def _get_relevant_documents(
        self,
        query: str,
        k: int = 5,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> List[Document]:
        docs = self.multi_stage_search(query, k=k)
        if run_manager:
            run_manager.on_retriever_end(docs)
        return docs


    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        return self.vectorstore.similarity_search(query,k=k)

    def hybrid_search(self, query: str, k: int = 5) -> List[Tuple[Document,float]]:
        results = self.vectorstore.similarity_search_with_score(query,k=k*2)
        keywords = set(re.findall(r"\w+", query.lower()))
        ranked=[]
        for doc,score in results:
            tokens = set(re.findall(r"\w+", doc.page_content.lower()))
            overlap = len(tokens & keywords)/(len(keywords)+1e-5)
            ranked.append((doc, 0.7*score + 0.3*overlap))
        return sorted(ranked,key=lambda x:x[1],reverse=True)[:k]

    def weighted_search(self, query: str, k: int = 5) -> List[Tuple[Document,float]]:
        results=self.vectorstore.similarity_search_with_score(query,k=k*2)
        scored=[]
        for doc,sim_score in results:
            recency = self._temporal_decay(doc.metadata.get("date",""))
            priority = float(doc.metadata.get("priority",0))
            scored.append((doc, 0.7*sim_score + 0.2*recency + 0.1*priority))
        return sorted(scored,key=lambda x:x[1],reverse=True)[:k]

    def contextual_weighted_search(self, query: str, k: int = 5) -> List[Tuple[Document,float]]:
        results=self.vectorstore.similarity_search_with_score(query,k=k*2)
        scored=[]
        for doc,sim_score in results:
            meta_score = sum(float(doc.metadata.get(k,0)) for k in doc.metadata if k not in ['date','priority'])
            scored.append((doc,sim_score+meta_score))
        return sorted(scored,key=lambda x:x[1],reverse=True)[:k]

    def semantic_expansion(self, query: str, k: int = 5) -> List[Document]:
        if not self.llm:
            return self.vectorstore.similarity_search(query,k=k)
        prompt = PromptTemplate.from_template("Expand this query for better search: {query}")
        try:
            response = self.llm.invoke(prompt.format(query=query))
            expansions = response.content.split(",") if hasattr(response,"content") else str(response).split(",")
        except:
            expansions=[]
        queries=[query]+expansions
        results=[]
        for q in queries:
            results.extend(self.vectorstore.similarity_search(q,k=k))

        seen=set()
        unique=[]
        for doc in results:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique.append(doc)
        return unique[:k]

    def max_marginal_relevance_search(self, query: str, k: int = 5):
        return self.vectorstore.max_marginal_relevance_search(query,k=k)


    def multi_stage_search(self, query: str, k: int = 5) -> List[Document]:
        stage_results = defaultdict(float)
        stage_docs_map = defaultdict(list)

        stage_funcs = {
            'semantic_expansion': lambda: [(doc,1.0) for doc in self.semantic_expansion(query,k=k)],
            'hybrid': lambda: self.hybrid_search(query,k=k),
            'weighted': lambda: self.weighted_search(query,k=k),
            'similarity': lambda: [(doc,1.0) for doc in self.similarity_search(query,k=k)],
            'mmr': lambda: [(doc,1.0) for doc in self.max_marginal_relevance_search(query,k=k)],
            'contextual': lambda: self.contextual_weighted_search(query,k=k)
        }

        for stage, func in stage_funcs.items():
            if not self.strategy.get(stage, False):
                continue
            docs_scores = func()
            if not docs_scores:
                continue
            scores = [score for _,score in docs_scores]
            min_s,max_s = min(scores), max(scores)
            denom = max(max_s-min_s,1e-5)
            weight = self.stage_weights.get(stage,0.1)
            for doc,score in docs_scores:
                normalized = (score - min_s)/denom
                stage_results[doc.page_content] += normalized*weight
                stage_docs_map[doc.page_content] = doc


        combined = sorted(stage_results.items(), key=lambda x: x[1], reverse=True)
        final_docs = [stage_docs_map[content] for content,_ in combined[:k]]

        if self.enable_debug:
            logging.info(f"[SMART-MULTI-STAGE-SCORE] Top {len(final_docs)} docs ranked by combined score.")

        return final_docs


    def _temporal_decay(self, date_str:str, half_life_days:int=180)->float:
        try:
            doc_date = datetime.strptime(date_str,"%Y-%m-%d")
            age_days=(datetime.now()-doc_date).days
            return math.exp(-age_days/half_life_days)
        except:
            return 0.0