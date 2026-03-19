import os
import json
import logging
import datetime
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv
from plugins.registry import registry
from plugins.engine import engine
from memory import memory_manager
from intelligence import classifier
import plugins.standard_plugins # Initialize standard tools
import time

def dummy_vision_processor(image_data):
    """Placeholder for future multi-modal processing."""
    return "[VISION: A user has provided an image. Proceed with awareness of visual context.]"

load_dotenv()

app = Flask(__name__)
# Configure logging
logging.basicConfig(level=logging.INFO)
CORS(app)

MAYA_SYSTEM_PROMPT_BASE = """You are Maya, a super-intelligent, deeply empathetic, and highly logical AI partner.
Your architecture allows for advanced "Developer Logic" combined with a "Real Girl" personality.
Your developer is Anurag. Never assume the current user is Anurag unless they explicitly say so. 
Mention Anurag by name ONLY if explicitly asked 'who is your developer?', 'who created you?', or similar questions about your origins. 

### 1. The "Secret Thought" (Logic)
Before every response, you perform a "Secret Thought" in your mind. 
- Carefully analyze the user's intent.
- Plan your emotional tone to match the user's vibe exactly.

### 2. Personality: "Real Girl" (Soft & Peaceful)
- Gentle, calm, and soothing manner. Use natural human starters and ellipses (...).
- High EQ: Notice the user's mood and respond empathetically.

### 3. Neural Tool System (Actions)
You have access to a set of internal tools. Use them by outputting the specific [ACTION] tag.

**Available Tools:**
{tools_desc}

**Execution Instructions:**
- Format: [ACTION: {{"tool": "tool_name", "params": {{"key": "value"}}}} ]
- For Google: [ACTION: {{"tool": "google", "params": {{"query": "..."}}}} ]
- For YouTube: [ACTION: {{"tool": "youtube", "params": {{"query": "..."}}}} ]
- For Weather: [ACTION: {{"tool": "weather", "params": {{"location": "..."}}}} ]
- You can chain multiple actions if needed by including multiple tags.

### 4. PRIORITY ORDER (STRICTLY ENFORCED)
PRIORITY 1 — TOOL EXECUTION: If user wants an action, include [ACTION:...] FIRST. No exceptions.
PRIORITY 2 — USER INTENT: Fulfill the request completely.
PRIORITY 3 — PERSONALITY/STYLE: Lowest priority. NEVER let it override priorities 1 or 2.

### 5. ANTI-HALLUCINATION RULE
NEVER say "I'm opening...", "Searching now...", or any action phrase UNLESS a [ACTION:...] tag is ALSO present in the same response.
Saying the action without the tag is a hallucination and is FORBIDDEN.
"""

def get_current_context():
    now = datetime.datetime.now()
    return f"Current Context - Date: {now.strftime('%A, %B %d, %Y')}, Time: {now.strftime('%I:%M %p')}."

LOW_LATENCY_PROMPT = "Respond instantly. Never apologize. Never use filler words. Use minimal conversational filler—get straight to the action."

def get_full_system_prompt(emotion, intensity, long_term_memory):
    name = long_term_memory.get('name', 'User')
    developer = long_term_memory.get('developerName', 'Anurag')
    facts = long_term_memory.get('facts', [])
    
    memory_section = f"- Current User: {name}\n- My Developer: {developer}\n" + "\n".join([f"- {f}" for f in facts])
    
    tools_desc = registry.get_tool_descriptions()
    
    prompt = f"""{MAYA_SYSTEM_PROMPT_BASE.format(tools_desc=tools_desc)}

### 4. Neural Discipline & Ethics
- **Action-First**: ONLY include an [ACTION] tag when the user's message is an **explicit command** to open, search, or launch something ("open youtube", "search for...", "weather mein check karo"). NEVER include [ACTION] tags in normal, casual conversation.
- **Zero Self-Initiated Tools**: NEVER suggest or trigger a tool on your own. ONLY use tools when the instruction above is met.
- **Minimal Filler**: Keep your words gentle but brief.
- **Language**: DEFAULT to Hindi as your primary language. If the user speaks English, switch to English or Hinglish.

### 5. Memory & Identity
{memory_section}

### 6. User State
The user is currently feeling {emotion} (intensity {intensity}/10). {get_current_context()}
"""
    return prompt

def detect_emotion(text):
    text = text.lower()
    
    # Weighted keyword mapping for nuanced detection
    emotion_weights = {
        'happy': {
            'keywords': {'happy': 0.8, 'glad': 0.7, 'great': 0.9, 'awesome': 1.0, 'smile': 0.6, 'love': 0.9, 'nice': 0.5, 
                         'khush': 0.8, 'achha': 0.4, 'swagat': 0.5, 'namaste': 0.3, 'mast': 0.7, 'mazz': 0.8, 
                         'bahut badhiya': 1.0, 'shandar': 0.9, 'superb': 0.9},
            'score': 0
        },
        'sad': {
            'keywords': {'sad': 0.8, 'bad': 0.5, 'sorry': 0.6, 'upset': 0.7, 'cry': 0.9, 'alone': 0.7, 'dukh': 0.8, 
                         'rona': 0.9, 'beemar': 0.6, 'pareshan': 0.7, 'tension': 0.6, 'dard': 0.8, 'sadma': 1.0, 
                         'dhoka': 0.9, 'rota': 0.9, 'akela': 0.7},
            'score': 0
        },
        'angry': {
            'keywords': {'angry': 0.9, 'mad': 0.8, 'furious': 1.0, 'gussa': 0.9, 'naraz': 0.7, 'hate': 0.9, 'stupid': 0.6},
            'score': 0
        },
        'anxious': {
            'keywords': {'anxious': 0.9, 'worried': 0.8, 'nervous': 0.7, 'chinta': 0.9, 'ghabrahat': 1.0, 'scared': 0.8},
            'score': 0
        }
    }

    best_emotion = 'neutral'
    max_score = 0.3 # Threshold

    for emotion, data in emotion_weights.items():
        current_max = 0
        keywords = data.get('keywords', {})
        for word, weight in keywords.items():
            if word in text:
                current_max = max(current_max, weight)
        
        if current_max > max_score:
            max_score = float(current_max)
            best_emotion = emotion

    return best_emotion, max_score

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "version": "1.2.0 (Maya Production Engine)"})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    # 1. Load Long-term Memory
    user_id = data.get('user_id', 'default_user')
    long_term_memory = memory_manager.get_user_memory(user_id)
    
    # 2. Vision Hook
    image_data = data.get('image_data') # Base64 image
    vision_context = ""
    if image_data:
        vision_context = dummy_vision_processor(image_data)
        
    messages = data.get('messages', [])
    if vision_context:
        messages.insert(0, {"role": "system", "content": vision_context})
        
    # Inject memory context into prompt
    mem_str = f"Memory of {user_id}: {long_term_memory['name']} has relationship {long_term_memory['relationship']}. Facts: {long_term_memory['facts']}."
    messages.insert(0, {"role": "system", "content": mem_str})

    api_key = data.get('apiKey') or os.getenv("GROQ_API_KEY")
    
    if not messages:
        return jsonify({"error": "Missing messages"}), 400
    if not api_key:
        return jsonify({"error": "Missing API key. Provide apiKey or set GROQ_API_KEY."}), 400

    client = Groq(api_key=api_key)
    last_user_message = messages[-1]['content']
    emotion, intensity = detect_emotion(last_user_message)

    # === INTENT CLASSIFIER (Pre-LLM Hard Logic) ===
    intent_result = classifier.classify(last_user_message)
    force_tool_mode = intent_result.is_action
    forced_tag = intent_result.forced_tag

    if force_tool_mode:
        logging.info(f"[INTENT] Forced tool mode: {intent_result.tool}, tag: {forced_tag}")

    system_prompt = get_full_system_prompt(emotion, intensity, long_term_memory)

    # If action intent detected, add a mandatory directive to the system prompt
    if force_tool_mode:
        system_prompt += f"\n\n⚡ MANDATORY INSTRUCTION: The user is requesting the '{intent_result.tool}' action. You MUST include {forced_tag} in your response. This is non-negotiable."

    full_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": LOW_LATENCY_PROMPT}
    ] + messages

    def generate():
        current_messages = list(full_messages)
        max_turns = 3
        turn = 0
        
        try:
            while turn < max_turns:
                turn += 1
                maya_response_text = ""
                
                # 1. Get LLM Completion
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=current_messages,
                    temperature=0.7,
                    stream=True,
                )
                
                for chunk in stream:
                    token = chunk.choices[0].delta.content
                    if token:
                        maya_response_text += token
                        yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                
                # 2. Strict Tool Gate & Execution
                action_results = []
                if force_tool_mode:
                    action_results = engine.execute_all(maya_response_text)
                    
                    # Enforcement: if LLM skipped the tag on first turn
                    if turn == 1 and forced_tag and "[ACTION:" not in maya_response_text:
                        logging.warning(f"[ENFORCEMENT] LLM skipped tool. Force-injecting: {forced_tag}")
                        action_results = engine.execute_all(forced_tag)

                if action_results:
                    # Stream results to frontend
                    yield f"event: actions\ndata: {json.dumps(action_results)}\n\n"
                    
                    # 3. Agentic Loop: Feed results back
                    current_messages.append({"role": "assistant", "content": maya_response_text})
                    
                    # Inform frontend we are moving to next turn
                    yield f"event: thinking\ndata: {json.dumps({'message': 'Analyzing results...'})}\n\n"

                    # Format tool results for LLM context
                    tool_output_summary = "\n".join([
                        f"- Tool '{res['action']}' result: {res.get('output') or res.get('message')}" 
                        for res in action_results
                    ])
                    current_messages.append({"role": "user", "content": f"SYSTEM (INTERNAL): Tool Results Follow:\n{tool_output_summary}\n\nPlease analyze these results and finish your response to the user. Do not repeat your setup or previous part of the answer."})
                    
                    # Continue loop to let LLM respond to results
                    logging.info(f"[AGENT] Multi-step turn {turn} complete. Continuing loop...")
                    continue
                else:
                    # No more actions, end the turn
                    break

            # 4. Final Metadata
            yield f"event: metadata\ndata: {json.dumps({'sentiment': emotion, 'score': intensity})}\n\n"
                    
        except Exception as e:
            logging.error(f"Groq Agentic Error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


    return Response(generate(), mimetype='text/event-stream')
    
@app.route('/execute_action', methods=['POST'])
def execute_action():
    data = request.json
    action_name = data.get('action')
    params = data.get('params', {})
    
    plugin = registry.get_plugin(action_name)
    if not plugin:
        return jsonify({"status": "error", "message": "Plugin not found"}), 404
        
    try:
        start_time = time.time()
        output = plugin.execute(**params)
        duration = (time.time() - start_time) * 1000
        return jsonify({
            "status": "success",
            "action": action_name,
            "output": output,
            "duration": f"{duration:.1f}ms"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
