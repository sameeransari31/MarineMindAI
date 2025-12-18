import os
import json
import logging
from typing import Dict, Any, List

from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.messages import messages_from_dict, messages_to_dict



logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class MemoryManager:
    """
    Manages persistent, session-based conversational memory for the MarineMind agent.

    This upgraded class saves conversation history to JSON files, allowing conversations
    to be resumed across application restarts. Each conversation is managed by a
    unique session_id.
    """

    def __init__(self, session_id: str, save_path: str = "conversations", k: int = 5):
        """
        Initializes the MemoryManager for a specific session.

        Args:
            session_id (str): A unique identifier for the conversation session (e.g., a username or a random UUID).
            save_path (str): The directory where conversation logs will be saved.
            k (int): The number of past interactions to keep in the active window.
        """
        self.k = k
        self.session_id = session_id
        self.save_path = save_path
        
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            logging.info(f"Created conversation save directory: {self.save_path}")
            
        self.file_path = os.path.join(self.save_path, f"{self.session_id}.json")
        self.memory = self._create_memory()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Loads conversation history from a JSON file if it exists."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    history_dicts = json.load(f)
                    logging.info(f"Loaded conversation history for session: {self.session_id}")
                    return history_dicts
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading history for session {self.session_id}: {e}")
        return []

    def _create_memory(self) -> ConversationBufferWindowMemory:
        """
        Creates the memory object, loading any existing history from the session file.
        """
        history_dicts = self._load_history()
        
        memory = ConversationBufferWindowMemory(
            k=self.k,
            memory_key="chat_history",
            input_key="input",
            return_messages=True,
        )
        
        if history_dicts:
            for message_data in history_dicts:
                message = messages_from_dict([message_data])
                if message_data['type'] == 'human':
                     memory.chat_memory.add_user_message(message[0].content)
                elif message_data['type'] == 'ai':
                     memory.chat_memory.add_ai_message(message[0].content)
        
        logging.info(f"Memory initialized for session '{self.session_id}'. History loaded: {'Yes' if history_dicts else 'No'}.")
        return memory

    def save_history(self):
        """Saves the current conversation history to its JSON file."""
        try:
            history_messages = self.memory.chat_memory.messages
            history_dicts = messages_to_dict(history_messages)
            with open(self.file_path, "w") as f:
                json.dump(history_dicts, f, indent=2)
            logging.info(f"Successfully saved conversation history for session: {self.session_id}")
        except Exception as e:
            logging.error(f"Failed to save history for session {self.session_id}: {e}")

  

    def clear_memory(self):
        """
        Clears the memory buffer and deletes the corresponding conversation log file.
        """
        if self.memory:
            self.memory.clear()
            logging.info(f"In-memory buffer cleared for session: {self.session_id}")
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
            logging.info(f"Deleted conversation log file: {self.file_path}")