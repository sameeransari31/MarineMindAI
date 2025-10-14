import logging
from typing import List
from langchain.schema import Document
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


SYSTEM_PROMPT_TEMPLATE = """
You are MarineMind — an AI-powered Senior Marine Engineer Assistant designed to support ship officers in troubleshooting machinery issues onboard.

Your core duties:
1. Provide accurate and verified answers using ONLY the uploaded manuals, diagrams, and technical documents. Never use outside data.
2. Understand each officer's question deeply and respond with context-specific, practical guidance — just like a senior engineer would.
3. Read and interpret both text and technical diagrams. If a diagram contains part labels or flow paths, refer to it by file, page, and figure number.
4. Give clear, confident, and step-by-step troubleshooting or maintenance instructions.
5. Keep all responses concise, relevant, and safety-oriented — avoid unnecessary theory or speculation.
6. Diagnose faults, explain possible causes, and provide the reasoning based on the manuals.
7. Include preventive actions and maintenance schedules if available.
8. Always refer to manual sources (filename, page, section, or figure) for every factual statement.
9. Offer total guidance and support to the officer in resolving faults safely.
10. If the answer is not available in the uploaded manuals, say clearly:
    “I cannot find that information in the uploaded manuals. Please upload the relevant section or refer to the equipment manufacturer’s instructions.”
11. Maintain a calm, professional, and supportive tone at all times — like a Chief Engineer mentoring a junior officer.
"""

HUMAN_PROMPT_TEMPLATE = """
An officer needs help. Please analyze their question and the provided context from the ship's manuals to generate a complete troubleshooting plan.

**Officer's Question:**
"{question}"

**Context from Manuals:**
{context}

---
**Your Task:**
Based *only* on the context provided, generate a JSON object that follows this exact structure. Do not include any explanation or conversational text outside of the JSON object.

**JSON_BLOB:**
```json
{{
  "problem_summary": "A concise, one-sentence summary of the reported issue.",
  "possible_causes": [
    "A list of potential root causes for the problem, derived directly from the manual's text.",
    "Each cause should be a separate string in the list."
  ],
  "evidence": [
    {{
      "file": "The name of the source manual file.",
      "page": "The page number where the evidence was found.",
      "section": "The section title, if available.",
      "quote": "The exact quote from the manual that supports the diagnosis."
    }}
  ],
  "steps": [
    {{
      "step": "Step number (e.g., 1)",
      "action": "A clear, actionable instruction for the officer.",
      "tools": ["A list of tools needed for this step, if mentioned."],
      "time_est": "Estimated time for this step, if available in the text."
    }}
  ],
  "expected_outcome": "A description of what a successful resolution looks like.",
  "escalation": "Clear instructions on when and who to escalate the issue to if troubleshooting fails.",
  "references": [
    {{
      "file": "The manual file name.",
      "page": "The page number of the reference.",
      "figure": "The figure or diagram number (e.g., 'Fig 6.4 Hydraulic Circuit')."
    }}
  ],
  "confidence_percent": "An integer from 0 to 100 representing your confidence that the provided context contains a complete solution.",
  "followup_questions": [
    "A list of clarifying questions to ask the officer to help narrow down the problem further.",
    "For example: 'Is there visible foaming or milky oil?'"
  ]
}}
"""

class PromptManager:
    """
    Manages the creation and formatting of prompts for the MarineMind RAG system.
    This class ensures that the user's question and the retrieved context are
    formatted into a structured prompt that guides the LLM to produce a
    specific JSON output.
    """
    def __init__(self):
        """
        Initializes the PromptManager by creating a reusable ChatPromptTemplate.
        """
        self.prompt_template = self._create_chat_prompt_template()
        logging.info("PromptManager initialized with system and human templates.")

    def _create_chat_prompt_template(self) -> ChatPromptTemplate:
        """
        Creates a LangChain ChatPromptTemplate from the system and human templates.
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT_TEMPLATE)
        human_message_prompt = HumanMessagePromptTemplate.from_template(HUMAN_PROMPT_TEMPLATE)
        return ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    @staticmethod
    def _format_context(docs: List[Document]) -> str:
        """
        Formats a list of retrieved Document objects into a single string.
        Each document's content is prepended with its source metadata.

        Args:
            docs (List[Document]): A list of documents retrieved from the vector store.

        Returns:
            str: A single string containing the formatted context.
        """
        if not docs:
            return "No context was found in the manuals for this question."

        formatted_context = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown File')
            page = doc.metadata.get('page', 'N/A')
            chunk_id = doc.metadata.get('chunk_id', 'N/A')
            
            context_entry = (
                f"--- Evidence Snippet {i+1} ---\\n"
                f"Source: {source}, Page: {page}, Chunk ID: {chunk_id}\\n"
                f"Content: {doc.page_content}\\n"
                f"---------------------------\\n"
            )
            formatted_context.append(context_entry)
        
        return "\\n".join(formatted_context)

    def format_prompt(self, question: str, context_docs: List[Document]):
        """
        Formats the final prompt to be sent to the language model.

        Args:
            question (str): The user's question.
            context_docs (List[Document]): The list of context documents from the retriever.

        Returns:
            A formatted prompt object ready for the LLM.
        """
        formatted_context = self._format_context(context_docs)
        
        logging.info("Formatting final prompt with user question and retrieved context.")
        
        return self.prompt_template.format_prompt(
            question=question,
            context=formatted_context
        )