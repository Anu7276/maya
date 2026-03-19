import json
import os
import logging

class MemoryManager:
    """Handles persistent storage and retrieval of user-specific context."""
    
    def __init__(self, storage_path="user_memories.json"):
        self.storage_path = storage_path
        self.memories = self._load_memories()

    def _load_memories(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load memory: {e}")
        return {}

    def save_memory(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.memories, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save memory: {e}")

    def get_user_memory(self, user_id):
        return self.memories.get(user_id, {
            "name": "User",
            "relationship": "Stranger",
            "facts": [],
            "preferences": {}
        })

    def update_user_memory(self, user_id, key, value):
        if user_id not in self.memories:
            self.memories[user_id] = self.get_user_memory(user_id)
        
        if key in ["preferences", "facts"] and isinstance(value, dict):
            self.memories[user_id][key].update(value)
        elif key == "facts" and isinstance(value, list):
             self.memories[user_id][key].extend(value)
             self.memories[user_id][key] = list(set(self.memories[user_id][key])) # Deduplicate
        else:
            self.memories[user_id][key] = value
        
        self.save_memory()

memory_manager = MemoryManager()
