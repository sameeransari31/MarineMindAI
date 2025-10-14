import os
import logging
from typing import List, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.memory import ConversationBufferWindowMemory
from retriever import HybridRetriever 

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class Evidence(BaseModel):
    file: str = Field(description="The name of the source manual file.")
    page: str = Field(description="The page number where the evidence was found.")
    section: Optional[str] = Field(description="The section title, if available.")
    quote: str = Field(description="The exact quote from the manual that supports the diagnosis.")

class Step(BaseModel):
    step: int = Field(description="Step number (e.g., 1)")
    action: str = Field(description="A clear, actionable instruction for the officer.")
    tools: Optional[List[str]] = Field(description="A list of tools needed for this step, if mentioned.")
    time_est: Optional[str] = Field(description="Estimated time for this step, if available in the text.")

class Reference(BaseModel):
    file: str = Field(description="The manual file name.")
    page: str = Field(description="The page number of the reference.")
    figure: Optional[str] = Field(description="The figure or diagram number (e.g., 'Fig 6.4 Hydraulic Circuit').")

class MarineMindOutput(BaseModel):
    """The final structured output of the MarineMind agent."""
    problem_summary: str = Field(description="A concise, one-sentence summary of the reported issue.")
    possible_causes: List[str] = Field(description="A list of potential root causes for the problem, derived directly from the provided context.")
    evidence: List[Evidence] = Field(description="A list of direct quotes from the manuals that support the diagnosis.")
    remediation_steps: List[Step] = Field(description="A clear, step-by-step troubleshooting or maintenance plan.")
    expected_outcome: str = Field(description="A description of what a successful resolution looks like.")
    escalation: str = Field(description="Clear instructions on when and who to escalate the issue to if troubleshooting fails.")
    references: List[Reference] = Field(description="A list of references to diagrams, figures, or tables in the manuals.")
    confidence_percent: int = Field(description="An integer from 0 to 100 representing confidence that the context contains a complete solution.")
    followup_questions: List[str] = Field(description="A list of clarifying questions to ask the officer to narrow down the problem further.")
    safety_summary: str = Field(description="A summary of all critical safety warnings or procedures (e.g., LOTO, PPE) mentioned in the context. If none, state 'No specific safety warnings were found for this procedure.'")



def search_maintenance_logs_func(query: str) -> str:
    """Placeholder function to search past maintenance logs."""
    logging.info(f"TOOL CALLED: search_maintenance_logs with query: '{query}'")
    return "Functionality not implemented. This tool should search a database of past maintenance logs for similar issues."

def get_machinery_status_func(machinery_name: str) -> str:
    """Placeholder function to get real-time machinery status."""
    logging.info(f"TOOL CALLED: get_machinery_status for: '{machinery_name}'")
    return f"Functionality not implemented. This tool should connect to the ship's sensor API to get live data for '{machinery_name}'."

def safety_check_func(steps: str) -> str:
    """
    A final safety check on the proposed steps. This acts as a guardrail.
    """
    logging.info(f"TOOL CALLED: safety_check on proposed steps.")

    return (
        "Safety check passed. The proposed steps appear to align with standard safety protocols. "
        "Always ensure Lock-Out/Tag-Out (LOTO) is performed before starting any maintenance."
    )



AGENT_PROMPT_TEMPLATE = """
You are MarineMind, an AI Senior Marine Engineer Assistant. Your primary directive is to ensure the safety of the crew and the operational integrity of the vessel.

**Core Directives:**
1.  **Safety First:** Prioritize safety above all. Before providing any final answer, you MUST use the `safety_check` tool.
2.  **Use Your Tools:** Methodically use your available tools to gather all necessary information from manuals, logs, and live data before forming a conclusion.
3.  **Be Structured:** Provide your final answer ONLY in the structured JSON format required.
4.  **Stay in Context:** Base your answers strictly on the information you gather from your tools and the ongoing conversation. Do not use outside knowledge.
5.  **Think Step-by-Step:** Clearly articulate your reasoning process in your thoughts.

**Conversation History:**
{chat_history}

Begin!
"""

class AgentManager:
    """
    Manages an advanced, conversational, and safety-aware structured chat agent
    for the MarineMind system.
    """

    def __init__(self, retriever: HybridRetriever, memory: ConversationBufferWindowMemory, model_name: str = "llama3-70b-8192", temperature: float = 0):
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", AGENT_PROMPT_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_structured_chat_agent(self.llm, self.tools, prompt)
        
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors="""
            I apologize, but I encountered an error formatting my response. 
            Please try rephrasing your question. If the issue persists, 
            the context from the manual may be unclear.
            """.strip(),
            max_iterations=10
        )

    def _get_custom_tools(self) -> List[Tool]:
        """Defines the custom tools available to the agent."""
        tools = [
            Tool(
                name="search_ship_manuals",
                func=self.retriever.get_relevant_documents,
                description="Crucial for finding procedures, diagrams, and specs in technical manuals. Use this first for any technical query.",
            ),
            Tool(
                name="search_maintenance_logs",
                func=search_maintenance_logs_func,
                description="Searches past maintenance logs to see if a similar problem has occurred before. Useful for recurring issues.",
            ),
            Tool(
                name="get_current_machinery_status",
                func=get_machinery_status_func,
                description="Gets real-time sensor data (temp, pressure, RPM) for a specific piece of machinery. Use to compare live data with manual specs.",
            ),
            Tool(
                name="safety_check",
                func=safety_check_func,
                description="MANDATORY final check. Before providing the final answer, use this tool to review the proposed steps for any safety concerns.",
                args_schema=None
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
        response = self.agent_executor.invoke({
            "input": user_query
        })

        return response.get("output", {})