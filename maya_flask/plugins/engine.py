import re
import json
import logging
import time
from typing import List, Dict, Any
from .registry import registry

class ExecutionEngine:
    """The Neural Execution Engine for parsing and executing AI actions."""

    def __init__(self):
        # Legacy Pattern: [ACTION:name param1=value1 param2="quoted value"]
        self.legacy_action_pattern = re.compile(r'\[ACTION:(\w+)\s*([^\]]*)\]')
        # JSON Pattern: [ACTION: { JSON_OBJECT }] - Matches until the LAST bracket of the tag
        self.json_action_pattern = re.compile(r'\[ACTION:\s*(\{[\s\S]*?\})\s*\]')
        self.param_pattern = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')

    def parse_actions(self, text: str) -> List[Dict[str, Any]]:
        """Parses [ACTION:...] tags (both legacy and JSON) from the AI response."""
        actions = []
        
        # 1. Try JSON Parsing first (New Standard)
        json_matches = self.json_action_pattern.finditer(text)
        for j_match in json_matches:
            try:
                action_data = json.loads(j_match.group(1))
                if isinstance(action_data, dict) and "tool" in action_data:
                    actions.append({
                        "name": action_data["tool"],
                        "params": action_data.get("params", {}),
                        "raw": j_match.group(0),
                        "format": "json"
                    })
                    logging.info(f"[ENGINE] Parsed JSON action: {action_data['tool']}")
            except json.JSONDecodeError:
                logging.warning(f"[ENGINE] Failed to decode potential JSON action: {j_match.group(1)}")

        # 2. Try Legacy Parsing (Backward Compatibility)
        legacy_matches = self.legacy_action_pattern.finditer(text)
        for l_match in legacy_matches:
            # Skip if this match was already handled by JSON (overlap check)
            if any(l_match.group(0) in a["raw"] for a in actions):
                continue
                
            name = l_match.group(1)
            raw_params = l_match.group(2)
            
            params = {}
            if raw_params:
                param_matches = self.param_pattern.finditer(raw_params)
                for p_match in param_matches:
                    key = p_match.group(1)
                    value = p_match.group(2) or p_match.group(3)
                    params[key] = value
            
            actions.append({
                "name": name, 
                "params": params, 
                "raw": l_match.group(0),
                "format": "legacy"
            })
            logging.info(f"[ENGINE] Parsed legacy action: {name}")
        
        return actions

    def execute_all(self, text: str) -> List[Dict[str, Any]]:
        """Parses and executes all actions found in the text."""
        parsed_actions = self.parse_actions(text)
        results = []

        for action in parsed_actions:
            plugin = registry.get_plugin(action['name'])
            if not plugin:
                results.append({
                    "action": action['name'],
                    "status": "error",
                    "message": f"Plugin '{action['name']}' not found."
                })
                continue

            if plugin.requires_permission:
                results.append({
                    "action": action['name'],
                    "status": "requires_permission",
                    "params": action['params'],
                    "message": f"Maya needs your permission to use {action['name']}."
                })
                continue

            try:
                # Basic validation
                logging.info(f"Executing plugin: {action['name']} with {action['params']}")
                start_time = time.time()
                output = plugin.execute(**action['params'])
                duration = (time.time() - start_time) * 1000 # ms
                
                results.append({
                    "action": action['name'],
                    "status": "success",
                    "output": output,
                    "duration": f"{duration:.1f}ms"
                })
            except Exception as e:
                logging.error(f"Error executing plugin {action['name']}: {e}")
                results.append({
                    "action": action['name'],
                    "status": "error",
                    "message": str(e)
                })

        return results

# Global engine instance
engine = ExecutionEngine()
