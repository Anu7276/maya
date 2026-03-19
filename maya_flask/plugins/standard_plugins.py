from .base import BasePlugin
from .registry import registry
import webbrowser

class YouTubePlugin(BasePlugin):
    def __init__(self):
        super().__init__(requires_permission=True)
    @property
    def name(self): return "youtube"
    @property
    def description(self): return "Opens YouTube or searches for a specific video."
    @property
    def parameters(self): return {"query": "Optional search term"}

    def execute(self, query=None):
        base_url = "https://www.youtube.com"
        if query:
            return {"url": f"{base_url}/results?search_query={query}", "type": "web_open"}
        return {"url": base_url, "type": "web_open"}

class GoogleSearchPlugin(BasePlugin):
    def __init__(self):
        super().__init__(requires_permission=True)
    @property
    def name(self): return "google"
    @property
    def description(self): return "Performs a Google search."
    @property
    def parameters(self): return {"query": "The search term"}

    def execute(self, query):
        return {"url": f"https://www.google.com/search?q={query}", "type": "web_open"}

class WeatherPlugin(BasePlugin):
    @property
    def name(self): return "weather"
    @property
    def description(self): return "Checks weather for a location."
    @property
    def parameters(self): return {"location": "City or area"}

    def execute(self, location="my location"):
        # Mock weather for now, production would use an API
        return {
            "location": location,
            "temp": "24°C",
            "condition": "Clear Sky",
            "type": "data_display"
        }

# Registering Standard Plugins
registry.register(YouTubePlugin())
registry.register(GoogleSearchPlugin())
registry.register(WeatherPlugin())
