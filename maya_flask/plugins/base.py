from abc import ABC, abstractmethod
from typing import Any, Dict

class BasePlugin(ABC):
    def __init__(self, requires_permission: bool = False):
        self.requires_permission = requires_permission
    """Abstract base class for all Maya plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does (used by the AI to select the tool)."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """A dictionary defining the parameters this plugin accepts."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """The main execution logic of the plugin."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Returns a JSON-serializable representation of the plugin's metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
