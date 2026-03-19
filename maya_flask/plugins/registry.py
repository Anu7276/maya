from typing import Dict, Type, List
from .base import BasePlugin

class PluginRegistry:
    """A central registry for managing and discovering Maya plugins."""
    
    _instance = None
    _plugins: Dict[str, BasePlugin] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, plugin: BasePlugin):
        """Registers a plugin instance."""
        self._plugins[plugin.name] = plugin
        print(f"Plugin Registered: {plugin.name}")

    def get_plugin(self, name: str) -> BasePlugin:
        """Retrieves a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[BasePlugin]:
        """Returns a list of all registered plugins."""
        return list(self._plugins.values())

    def get_tool_descriptions(self) -> str:
        """Generates a formatted string of tool descriptions for the AI system prompt."""
        descriptions = []
        for plugin in self._plugins.values():
            params_str = " ".join([f'{k}="..."' for k in plugin.parameters.keys()])
            descriptions.append(f"- [ACTION:{plugin.name} {params_str}]: {plugin.description}")
        return "\n".join(descriptions)

# Global registry instance
registry = PluginRegistry()
