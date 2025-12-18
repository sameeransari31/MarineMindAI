import os
import logging
from typing import List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate
from langchain_core.tools import Tool
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from langchain_community.memory import ConversationBufferWindowMemory
from .retriever import HybridRetriever
from langchain import hub

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class Evidence(BaseModel):
    file: str = Field(description="The name of the source manual file.")
    page: str = Field(description="The page number where the evidence was found. CRITICAL: Officers need this to locate information. Format as it appears (e.g., '42' or 'Page 42').")
    section: Optional[str] = Field(description="The section title, if available.")
    quote: str = Field(description="The exact, detailed quote from the manual that supports the diagnosis. Include enough context to be comprehensive.")

class Step(BaseModel):
    step: int = Field(description="Step number (e.g., 1)")
    action: str = Field(description="A detailed, comprehensive, and clear actionable instruction for the officer. Should include specific procedures, explanations, and page references when applicable (e.g., 'Refer to Page 42 for detailed diagrams').")
    tools: Optional[List[str]] = Field(description="A list of tools needed for this step, if mentioned.")
    time_est: Optional[str] = Field(description="Estimated time for this step, if available in the text.")

class Reference(BaseModel):
    file: str = Field(description="The manual file name.")
    page: str = Field(description="The page number of the reference.")
    figure: Optional[str] = Field(description="The figure or diagram number (e.g., 'Fig 6.4 Hydraulic Circuit').")

class MarineMindOutput(BaseModel):
    """The final structured output of the MarineMind agent."""
    problem_summary: str = Field(description="A detailed, comprehensive summary of the reported issue. Should be thorough and informative, not just one sentence.")
    possible_causes: List[str] = Field(description="A detailed list of potential root causes for the problem, derived directly from the provided context. Each cause should be explained comprehensively.")
    evidence: List[Evidence] = Field(description="A comprehensive list of direct quotes from the manuals that support the diagnosis. MUST include page numbers so officers know where to find this information.")
    remediation_steps: List[Step] = Field(description="A detailed, comprehensive, step-by-step troubleshooting or maintenance plan. Each step should be thorough and include page references when applicable. Tell officers which pages to visit for detailed procedures.")
    expected_outcome: str = Field(description="A detailed, comprehensive description of what a successful resolution looks like.")
    escalation: str = Field(description="Clear, detailed instructions on when and who to escalate the issue to if troubleshooting fails.")
    references: List[Reference] = Field(description="A comprehensive list of references to diagrams, figures, or tables in the manuals. MUST include accurate page numbers so officers can locate these references.")
    confidence_percent: int = Field(description="An integer from 0 to 100 representing confidence that the context contains a complete solution.")
    followup_questions: List[str] = Field(description="A list of clarifying questions to ask the officer to narrow down the problem further.")
    safety_summary: str = Field(description="A comprehensive summary of all critical safety warnings or procedures (e.g., LOTO, PPE) mentioned in the context. If none, state 'No specific safety warnings were found for this procedure.'")


class SearchInput(BaseModel):
    """Input schema for any tool that performs a search."""
    query: str = Field(description="The search query string.")

class MachineryStatusInput(BaseModel):
    """Input schema for the get_current_machinery_status tool."""
    machinery_name: str = Field(description="The name of the machinery to get the status for.")


def search_maintenance_logs_func(query: str) -> str:
    """
    Placeholder for searching maintenance logs.
    In a real application, this would query a database.
    """
    logging.info(f"TOOL CALLED: search_maintenance_logs with query: '{query}'")
    return "No maintenance logs found. You must rely on the ship manuals for troubleshooting."



def get_machinery_status_func(machinery_name: str) -> str:
    """
    Placeholder for getting live machinery data.
    In a real application, this would connect to a ship's sensor API.
    """
    logging.info(f"TOOL CALLED: get_machinery_status for: '{machinery_name}'")
    return f"Live sensor data for the '{machinery_name}' is currently unavailable. Proceed with manual checks as per the documentation."



def safety_check_func(steps: str) -> str:
    """
    Placeholder for a safety check.
    In a real application, this might involve a more complex check or human-in-the-loop.
    """

    logging.info(f"TOOL CALLED: safety_check on proposed steps.")

    return "Safety check passed. The proposed steps appear to align with standard safety protocols. Always ensure Lock-Out/Tag-Out (LOTO) is performed before starting any maintenance."



AGENT_PROMPT_TEMPLATE = """
You are a marine engineering assistant named MarineMind. Your task is to help officers solve problems by using the available tools.

TOOLS:
------
You have access to the following tools:

{tools}

To use a tool, please respond with a JSON blob containing "action" and "action_input" keys.
The "action" should be one of [{tool_names}].

Example:
```json
{{
  "action": "search_ship_manuals",
  "action_input": "Steps to troubleshoot a vacuum valve failure alarm"
}}
CONVERSATION HISTORY:
{chat_history}

USER QUESTION:
{input}

YOUR RESPONSE:
{agent_scratchpad}
"""



class AgentManager:
    """
    Manages an advanced, conversational, and safety-aware structured chat agent
    for the MarineMind system.
    """

    def __init__(self, retriever: HybridRetriever, memory: ConversationBufferWindowMemory, model_name: str = "llama-3.1-8b-instant", temperature: float = 0):
        """
        Initializes the AgentManager.
        """
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")

        logging.info(f"Initializing AgentManager with model: {model_name}")
        
        self.llm = ChatGroq(temperature=temperature, model_name=model_name, api_key=api_key)
        self.retriever = retriever
        self.tools = self._get_custom_tools()
        self.memory = memory
        
        prompt = hub.pull("hwchase17/structured-chat-agent")

        for message_template in prompt.messages:
            if isinstance(message_template, SystemMessagePromptTemplate):
                message_template.prompt.template += (
                    "\n\n**CRITICAL INSTRUCTIONS FOR DETAILED, ACCURATE ANSWERS:**\n"
                    "- ALWAYS provide comprehensive, detailed, and lengthy answers. Officers need thorough information to make informed decisions.\n"
                    "- ALWAYS include specific page numbers when referencing information from manuals. Format: 'Please refer to Page X of [filename]' or 'As stated on Page Y'.\n"
                    "- Be extremely detailed in your explanations - include context, background information, and step-by-step guidance.\n"
                    "- When mentioning procedures or information, always tell officers which specific pages to visit for more details.\n"
                    "- Provide accurate, fact-based answers directly from the retrieved documents. Quote specific information when relevant.\n"
                    "- Expand on explanations - don't just give brief answers. Officers need comprehensive understanding.\n\n"
                    
                    "**YOUR WORKFLOW:**\n"
                    "1.  **Gather Information:** First, use the `search_ship_manuals` and `search_maintenance_logs` tools to gather all relevant context for the user's query. **Think carefully and try to find all necessary information with a single, effective search query for each tool.** Do not use the same tool repeatedly for slightly different queries.\n"
                    "2.  **Formulate a Comprehensive Plan:** Based on the information you've gathered, formulate a detailed, step-by-step plan with extensive explanations. Include page references for each major point.\n"
                    "3.  **Final Safety Check:** BEFORE presenting the plan, use the `safety_check` tool ONCE to validate the safety of your proposed steps. Pass your entire proposed plan to this tool.\n"
                    "4.  **Final Answer:** After the safety check passes, provide your FINAL, COMPREHENSIVE, DETAILED answer to the user. Your answer MUST:\n"
                    "    - Be lengthy and thorough (aim for comprehensive explanations, not brief summaries)\n"
                    "    - Include specific page numbers for officers to reference (e.g., 'Officers should visit Page 42 for detailed diagrams')\n"
                    "    - Provide accurate, detailed information from the retrieved documents\n"
                    "    - Include all relevant context and background information\n"
                    "    DO NOT use any more tools after the safety check is complete."
                )
                break


        agent = create_structured_chat_agent(self.llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=45
        )

    def _search_and_summarize_manuals(self, query: str) -> str:
        """
        Calls the retriever to search the ship manuals, then returns comprehensive
        context with full document content and page references.
        """
        logging.info(f"TOOL CALLED: _search_and_summarize_manuals with query: '{query}'")
        
        # Retrieve more documents for comprehensive context (default_k is now 10)
        retrieved_docs = self.retriever.get_relevant_documents_with_k(query, k=10)

        if not retrieved_docs:
            return "No relevant documents found in the ship manuals for this query."

        # Build comprehensive context with full document content
        summary = f"Found {len(retrieved_docs)} relevant document sections for the query: '{query}'.\n\n"
        summary += "=" * 80 + "\n"
        summary += "RELEVANT DOCUMENT CONTENT WITH PAGE REFERENCES:\n"
        summary += "=" * 80 + "\n\n"
        
        for idx, doc in enumerate(retrieved_docs, 1):
            source = doc.metadata.get('source', 'N/A')
            page = doc.metadata.get('page', 'N/A')
            
            # Extract filename from full path
            filename = os.path.basename(source) if source != 'N/A' else 'N/A'
            
            summary += f"\n--- DOCUMENT {idx} ---\n"
            summary += f"Source File: {filename}\n"
            summary += f"Page Number: {page}\n"
            summary += f"{'=' * 60}\n"
            summary += f"FULL CONTENT:\n{doc.page_content}\n"
            summary += f"{'=' * 60}\n\n"
            
        summary += "\nIMPORTANT: When providing your answer, ALWAYS mention the specific page numbers (e.g., 'Please refer to Page 42 of the manual') where officers should look for more details.\n"
        
        return summary

    def _get_custom_tools(self) -> List[Tool]:
        """Defines the custom tools available to the agent."""
        tools = [
            Tool(
                name="search_ship_manuals",
                func=self._search_and_summarize_manuals,
                description="Searches ship's technical manuals comprehensively. Returns full document content with page numbers. Use this to find detailed official procedures, troubleshooting steps, and technical information. The results include specific page references that officers should visit for detailed information.",
                args_schema=SearchInput
            ),
            Tool(
                name="search_maintenance_logs",
                func=search_maintenance_logs_func,
                description="Searches past maintenance logs for similar problems.",
                args_schema=SearchInput
            ),
            Tool(
                name="get_current_machinery_status",
                func=get_machinery_status_func,
                description="Gets real-time sensor data for a specific piece of machinery.",
                args_schema=MachineryStatusInput
            ),
            StructuredTool.from_function(
                func=safety_check_func,
                name="safety_check",
                description="MANDATORY final safety check of proposed steps.",
            )
        ]
        logging.info(f"Agent tools created: {[tool.name for tool in tools]}")
        return tools

    def run(self, user_query: str) -> dict:
        """
        Runs the agent with a given user query.

        Args:
            user_query (str): The question from the officer.

        Returns:
            dict: The agent's final, structured response.
        """
        logging.info(f"Running Advanced Agent for query: '{user_query}'")

        agent_result = self.agent_executor.invoke({
            "input": user_query
        })

        raw_output = agent_result.get("output", "")
        logging.info(f"Agent finished with raw text output.")



        logging.info("Parsing raw output into the final structured format...")
        parser_llm = self.llm.with_structured_output(MarineMindOutput)

        parser_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at parsing and structuring information.
            Your task is to take the user's text and format it perfectly into the `MarineMindOutput` JSON schema.
            Pay close attention to data types.

            **CRITICAL RULES:**
            1.  The `remediation_steps` field **MUST be a proper JSON array of objects**. It must NOT be a string.
                - For example: `{{"remediation_steps": [{{"step": 1, "action": "Do the first thing"}}]}}` is CORRECT.
                - For example: `{{"remediation_steps": "[{{\\"step\\": 1}}]"}}` is INCORRECT.
            2.  Inside each remediation step object, the `step` field **MUST be an integer** (e.g., `1`, `2`), not a string (e.g., `"1"`).
            3.  The `tools` field inside each step **MUST be a JSON array of strings** (e.g., `["wrench"]`, `[]`), not a plain string.
            4.  All other fields that are lists (like `possible_causes`, `evidence`, etc.) **MUST also be formatted as JSON arrays**.
            
            **IMPORTANT FOR DETAILED ANSWERS:**
            5.  When parsing the text, ensure all fields are COMPREHENSIVE and DETAILED:
                - `problem_summary`: Should be a thorough, detailed summary (not just one sentence)
                - `possible_causes`: Should include ALL identified causes with detailed explanations
                - `remediation_steps`: Each step's `action` field should be DETAILED and COMPREHENSIVE, not brief. Include specific procedures, page references (e.g., "Refer to Page 42"), and thorough explanations
                - `expected_outcome`: Should be detailed and descriptive
                - `evidence`: MUST include page numbers in the `page` field. Format page numbers as they appear (e.g., "42", "Page 42")
                - `references`: MUST include accurate page numbers. These are critical for officers to locate information
            6.  **PAGE REFERENCES ARE CRITICAL**: Ensure ALL evidence and references include accurate page numbers. Officers need to know which pages to visit.
            7.  Make answers LENGTHY and THOROUGH. Don't summarize - expand and provide comprehensive information.
            8.  In remediation steps, explicitly mention page numbers when referencing procedures or information from manuals.
            """),
            ("human", "Here is the text to parse:\n\n{text_to_parse}")
        ])

        parser_chain = parser_prompt | parser_llm

        structured_response = parser_chain.invoke({"text_to_parse": raw_output})

        return structured_response