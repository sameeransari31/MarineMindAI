import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class SessionManager:
    """
    Manages chat sessions with metadata (title, timestamps, etc.)
    Similar to ChatGPT's chat history management.
    """
    
    def __init__(self, sessions_path: str = "conversations", metadata_file: str = "chat_sessions.json"):
        self.sessions_path = sessions_path
        self.metadata_file = os.path.join(sessions_path, metadata_file)
        
        if not os.path.exists(self.sessions_path):
            os.makedirs(self.sessions_path)
        
        # Load or initialize metadata
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load session metadata from file."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r") as f:
                    metadata = json.load(f)
                    logging.info(f"Loaded session metadata: {len(metadata.get('sessions', {}))} sessions")
                    return metadata
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading metadata: {e}")
        
        return {"sessions": {}}
    
    def _save_metadata(self):
        """Save session metadata to file."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
            logging.info(f"Saved session metadata")
        except Exception as e:
            logging.error(f"Error saving metadata: {e}")
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific session."""
        return self.metadata.get("sessions", {}).get(session_id)
    
    def _load_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Load conversation history for a session."""
        file_path = os.path.join(self.sessions_path, f"{session_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading history for session {session_id}: {e}")
        return []
    
    def _get_last_message_preview(self, session_id: str) -> str:
        """Get a preview of the last message in a conversation."""
        history = self._load_conversation_history(session_id)
        if not history:
            return "No messages yet"
        
        # Get the last message
        for msg in reversed(history):
            if msg.get("type") == "human":
                content = msg.get("data", {}).get("content", "")
                if content:
                    return content[:100] + ("..." if len(content) > 100 else "")
            elif msg.get("type") == "ai":
                content = msg.get("data", {}).get("content", "")
                if content:
                    return content[:100] + ("..." if len(content) > 100 else "")
        
        return "No messages yet"
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with metadata."""
        sessions_list = []
        
        # Get all session files
        if os.path.exists(self.sessions_path):
            for filename in os.listdir(self.sessions_path):
                if filename.endswith(".json") and filename != "chat_sessions.json":
                    session_id = filename.replace(".json", "")
                    
                    # Get or create metadata
                    session_meta = self.metadata.get("sessions", {}).get(session_id, {})
                    
                    # Extract created_at from session_id if it's a timestamp-based ID
                    created_at = session_meta.get("created_at")
                    if not created_at and session_id.startswith("session_"):
                        try:
                            timestamp = int(session_id.replace("session_", ""))
                            created_at = datetime.fromtimestamp(timestamp / 1000).isoformat()
                        except:
                            created_at = datetime.now().isoformat()
                    
                    # Get file modification time as updated_at
                    file_path = os.path.join(self.sessions_path, filename)
                    updated_at = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    
                    # Get title (default to first message or session ID)
                    title = session_meta.get("title")
                    if not title:
                        history = self._load_conversation_history(session_id)
                        for msg in history:
                            if msg.get("type") == "human":
                                content = msg.get("data", {}).get("content", "")
                                if content:
                                    title = content[:50] + ("..." if len(content) > 50 else "")
                                    break
                        if not title:
                            title = f"Chat {session_id[:8]}"
                    
                    last_message = self._get_last_message_preview(session_id)
                    
                    sessions_list.append({
                        "session_id": session_id,
                        "title": title,
                        "created_at": created_at or datetime.now().isoformat(),
                        "updated_at": updated_at,
                        "last_message_preview": last_message
                    })
        
        # Sort by updated_at (most recent first)
        sessions_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions_list
    
    def create_session(self, session_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session with metadata."""
        if session_id not in self.metadata.get("sessions", {}):
            self.metadata.setdefault("sessions", {})[session_id] = {
                "title": title or f"New Chat",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self._save_metadata()
        
        return self.metadata["sessions"][session_id]
    
    def update_session(self, session_id: str, title: Optional[str] = None):
        """Update session metadata."""
        if session_id in self.metadata.get("sessions", {}):
            if title:
                self.metadata["sessions"][session_id]["title"] = title
            self.metadata["sessions"][session_id]["updated_at"] = datetime.now().isoformat()
            self._save_metadata()
        else:
            # Create if doesn't exist
            self.create_session(session_id, title)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its conversation history."""
        # Delete conversation file
        file_path = os.path.join(self.sessions_path, f"{session_id}.json")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Error deleting conversation file: {e}")
                return False
        
        # Delete vector index
        index_path = os.path.join("session_indexes", f"faiss_index_{session_id}")
        if os.path.exists(index_path):
            try:
                import shutil
                shutil.rmtree(index_path)
            except Exception as e:
                logging.error(f"Error deleting index: {e}")
        
        # Remove from metadata
        if session_id in self.metadata.get("sessions", {}):
            del self.metadata["sessions"][session_id]
            self._save_metadata()
        
        return True
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get formatted conversation history for frontend."""
        history = self._load_conversation_history(session_id)
        formatted_history = []
        
        for msg in history:
            msg_type = msg.get("type")
            content = msg.get("data", {}).get("content", "")
            
            if msg_type == "human":
                formatted_history.append({
                    "text": content,
                    "sender": "user"
                })
            elif msg_type == "ai":
                formatted_history.append({
                    "text": content,
                    "sender": "ai"
                })
        
        return formatted_history

