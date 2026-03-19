"""
IntentClassifier — Pre-LLM Hard Logic Layer
Determines if the user's input requires a tool call BEFORE the LLM is invoked.
This guarantees tool execution regardless of model behavior.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class IntentResult:
    is_action: bool = False
    tool: Optional[str] = None
    params: dict = field(default_factory=dict)
    forced_tag: Optional[str] = None  # The [ACTION:...] string to inject if LLM skips it

class IntentClassifier:
    """
    Hard-logic intent classifier. Maps keyword patterns to tool names.
    Runs BEFORE the LLM to set force_tool_mode.
    """

    # Map of (keywords) -> (tool_name, param_key)
    INTENT_MAP = [
        # YouTube
        {
            "keywords": ["open youtube", "youtube kholo", "youtube chalao", "youtube open", 
                         "play youtube", "search youtube", "youtube pe search", "youtube search",
                         "यूट्यूब खोलो", "यूट्यूब चलाओ", "यूट्यूब ओपन", "ओपन यूट्यूब", "युटुब"],
            "tool": "youtube",
            "param_extraction": None
        },
        # YouTube with search query
        {
            "keywords": ["play ", "search for video", "video search", "find video", "video dhundho",
                         "youtube par", "youtube mein", "चलाओ", "बजाओ", "दिखाओ", "खोजो", 
                         "यूट्यूब पर", "यूट्यूब में"],
            "tool": "youtube",
            "param_extraction": "query"
        },
        # Google Search
        {
            "keywords": ["search google", "google karo", "google pe search", "google search",
                         "open google", "google kholo", "google chalao", "google on",
                         "गूगल खोलो", "गूगल चलाओ", "गूगल पर", "खोजो"],
            "tool": "google",
            "param_extraction": None
        },
        # Google with query
        {
            "keywords": ["search for ", "dhundho ", "find me ", "look up ", "google for ",
                         "के बारे में", "क्या है", "कौन है"],
            "tool": "google",
            "param_extraction": "query"
        },
        # Weather
        {
            "keywords": ["weather", "mausam", "temperature", "how is the weather", 
                         "barish", "aaj ka mausam", "mausam kaisa hai",
                         "मौसम", "तापमान", "बारिश", "कैसा है मौसम"],
            "tool": "weather",
            "param_extraction": "location"
        },
    ]

    def classify(self, user_input: str) -> IntentResult:
        """Returns an IntentResult with tool info if action intent is detected."""
        text = user_input.lower().strip()

        for intent in self.INTENT_MAP:
            for keyword in intent["keywords"]:
                if keyword in text:
                    tool = intent["tool"]
                    params = {}

                    # Try to extract a parameter (query or location)
                    if intent["param_extraction"] == "query":
                        # Extract anything after the trigger keyword
                        idx = text.find(keyword)
                        after = text[idx + len(keyword):].strip(" \"'?.!")
                        
                        # Special handling for "and", "or" in compound queries
                        # e.g., "open youtube and play song"
                        if " and " in after:
                            after = after.split(" and ")[0].strip()
                        elif " और " in after:
                            after = after.split(" और ")[0].strip()
                            
                        if after:
                            params["query"] = after
                            
                    elif intent["param_extraction"] == "location":
                        # Try to extract city (everything after "weather in/for")
                        for loc_trigger in ["in ", "at ", "for ", "ka ", "mein ", "me ", 
                                            "में ", "में", "पर ", "का ", "के लिए "]:
                            if loc_trigger in text:
                                loc_idx = text.rfind(loc_trigger)
                                location = text[loc_idx + len(loc_trigger):].strip(" \"'?.!")
                                if location:
                                    params["location"] = location
                                break

                    # Build the forced ACTION tag to inject if LLM misses it
                    forced_data = {"tool": tool, "params": params}
                    forced_tag = f"[ACTION: {json.dumps(forced_data)}]"

                    return IntentResult(
                        is_action=True,
                        tool=tool,
                        params=params,
                        forced_tag=forced_tag
                    )

        return IntentResult(is_action=False)


# Global singleton
classifier = IntentClassifier()
