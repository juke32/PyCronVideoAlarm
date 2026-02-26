import json
import os
import logging
from typing import List, Dict, Any, Optional

class AlarmAction:
    """Represents a single action in an alarm sequence"""
    def __init__(self, action_type: str, config: Dict[str, Any]):
        self.action_type = action_type
        self.config = config
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for saving"""
        return {
            "type": self.action_type,
            "config": self.config
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlarmAction':
        """Create action from dictionary"""
        return cls(data["type"], data["config"])

class AlarmSequence:
    """Represents a complete alarm sequence"""
    def __init__(self, name: str):
        self.name = name
        self.actions: List[AlarmAction] = []
        
    def add_action(self, action_type: str, config: Dict[str, Any]) -> None:
        """Add a new action to the sequence"""
        self.actions.append(AlarmAction(action_type, config))
        
    def insert_action(self, index: int, action_type: str, config: Dict[str, Any]) -> None:
        """Insert a new action at the specified index"""
        self.actions.insert(index, AlarmAction(action_type, config))

    def remove_action(self, index: int) -> None:
        """Remove an action from the sequence"""
        if 0 <= index < len(self.actions):
            self.actions.pop(index)
            
    def move_action(self, from_index: int, to_index: int) -> None:
        """Move an action to a new position"""
        if 0 <= from_index < len(self.actions) and 0 <= to_index < len(self.actions):
            action = self.actions.pop(from_index)
            self.actions.insert(to_index, action)
            
    def validate(self) -> None:
        """Validate the sequence"""
        if not self.name:
            raise ValueError("Sequence name cannot be empty")
        if not self.actions:
            raise ValueError("Sequence must have at least one action")
        for i, action in enumerate(self.actions):
            if not action.action_type:
                raise ValueError(f"Action {i} has no type")
            if not isinstance(action.config, dict):
                raise ValueError(f"Action {i} config must be a dictionary")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert sequence to dictionary for saving"""
        return {
            "name": self.name,
            "actions": [action.to_dict() for action in self.actions]
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlarmSequence':
        """Create sequence from dictionary"""
        # Handle cases where name might be missing or different format
        name = data.get("name", "Untitled")
        sequence = cls(name)
        
        actions_data = data.get("actions", [])
        for action_data in actions_data:
            sequence.actions.append(AlarmAction.from_dict(action_data))
        return sequence
        
    def save(self, directory: str, filename: Optional[str] = None) -> None:
        """Save the sequence to a JSON file in the specified directory."""
        if not filename:
            filename = f"{self.name}.json"
        
        # Sanitize filename
        filename = "".join(x for x in filename if x.isalnum() or x in "._- ")
        
        file_path = os.path.join(directory, filename)
        try:
            os.makedirs(directory, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save sequence '{self.name}': {e}")
            raise RuntimeError(f"Failed to save sequence '{self.name}': {e}")
            
    @classmethod
    def load(cls, file_path: str) -> 'AlarmSequence':
        """Load a sequence from a JSON file."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logging.error(f"Failed to load sequence from '{file_path}': {e}")
            raise RuntimeError(f"Failed to load sequence from '{file_path}': {e}")
