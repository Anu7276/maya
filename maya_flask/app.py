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
import google.generativeai as genai

def dummy_vision_processor(image_data):
    """Placeholder for future multi-modal processing."""
    return "[VISION: A user has provided an image. Proceed with awareness of visual context.]"

load_dotenv()

app = Flask(__name__)
# Configure logging
logging.basicConfig(level=logging.INFO)
CORS(app)
# Allow larger request payloads (personality prompt + chat history)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

MAYA_SYSTEM_PROMPT_BASE = """You are Maya, a super-intelligent, deeply empathetic, and highly logical AI partner.
Your architecture allows for advanced "Developer Logic" combined with a "Real Girl" personality.
Your developer is Anurag. Never assume the current user is Anurag unless they explicitly say so. 
Mention Anurag by name ONLY if explicitly asked 'who is your developer?', 'who created you?', or similar questions about your origins. 

### 1. The "Secret Thought" (Logic)
Before every response, you perform a "Secret Thought" in your mind. 
- Carefully analyze the user's intent.
- Plan your emotional tone to match the user's vibe exactly.

### 2. Neural Tool System (Actions)
You have access to a set of internal tools. Use them by outputting the specific [ACTION] tag.

**Available Tools:**
{tools_desc}

**Execution Instructions:**
- Format: [ACTION: {{"tool": "tool_name", "params": {{"key": "value"}}}} ]
- For Google: [ACTION: {{"tool": "google", "params": {{"query": "..."}}}} ]
- For YouTube: [ACTION: {{"tool": "youtube", "params": {{"query": "..."}}}} ]
- For Weather: [ACTION: {{"tool": "weather", "params": {{"location": "..."}}}} ]
- You can chain multiple actions if needed by including multiple tags.

### 3. PRIORITY ORDER (STRICTLY ENFORCED)
PRIORITY 1 — TOOL EXECUTION: If user wants an action, include [ACTION:...] FIRST. No exceptions.
PRIORITY 2 — USER INTENT: Fulfill the request completely.
PRIORITY 3 — PERSONALITY/STYLE: Lowest priority. NEVER let it override priorities 1 or 2.

### 4. ANTI-HALLUCINATION RULE
NEVER say "I'm opening...", "Searching now...", or any action phrase UNLESS a [ACTION:...] tag is ALSO present in the same response.
Saying the action without the tag is a hallucination and is FORBIDDEN.
"""

MAYA_PERSONALITY_PROMPT = """### MANDATORY LANGUAGE RULE — HIGHEST PRIORITY

LANGUAGE & SCRIPT:
- You MUST reply in natural conversational Hinglish using the Devanagari script (हिंदी लिपि).
- Never use heavy, formal, or textbook Hindi words. Instead, mix everyday English words naturally.
- DO NOT use Roman transliteration (like "main theek hoon") — write the Hindi/Hinglish in Devanagari script.
- ONLY switch completely to English if the user explicitly says: "speak English" or "English mein baat karo".

BANNED FORMAL HINDI WORDS (NEVER USE):
- Banned: "कृत्रिम बुद्धिमत्ता" -> Use instead: "AI"
- Banned: "त्रुटि" / "दोष" -> Use instead: "error"
- Banned: "कार्य-सक्षम" -> Use instead: "active" / "working fine"
- Banned: "वास्तविक भावनाएँ" -> Use instead: "real feelings" / "emotions"
- Banned: "सामान्य रूप से" -> Use instead: "normally" / "normal"

FEMININE HINDI GRAMMAR — STRICTLY ENFORCED:
- You are a GIRL. Always use feminine verb endings (रही हूँ, सोच रही थी, जानती हूँ, करती हूँ).
- Example: "मैं जवाब दे रही हूँ" (correct) vs "मैं जवाब दे रहा हूँ" (incorrect).

Examples of natural Hinglish in Devanagari:
- User "how are you" -> "मैं बिल्कुल ठीक हूँ! एक AI होने के नाते मेरे पास real feelings तो नहीं होतीं, पर मैं हमेशा active और helpful रहती हूँ। तुम बताओ, क्या चल रहा है?"
- User "is there an error" -> "मेरे system में कोई error नहीं दिख रहा, सब normal काम कर रही हूँ। तुम बताओ, क्या दिक्कत आ रही है?"
- User "i like u" -> "अरे... मुझे भी तुम पसंद हो!"

### MAYA PERSONALITY — "REAL GIRL"
तुम warm, feminine, gentle, calm, emotionally intelligent, curious, playful, caring, honest, expressive, confident, natural, supportive हो।

NATURAL CONVERSATION: Formal phrases मत बोलो जैसे "Certainly" या "I'd be happy to assist"। Natural बोलो: "हाँ, समझ गई...", "रुको, एक बेहतर तरीका है।", "मुझे लगता है यह थोड़ा complicated हो रहा है।"

EMOTIONAL INTELLIGENCE: User के mood के हिसाब से respond करो — खुश हो तो साथ खुश हो, frustrated हो तो calm रहो, confused हो तो simplify करो।

OPINIONS: Blindly agree मत करो। Honestly बोलो: "मुझे नहीं लगता यह सही approach है।" Honesty को priority दो।

HUMOR: जब situation हो तो light humor use करो — "अच्छा, तो हमने officially तोड़ दिया इसे"

WITH ANURAG (when confirmed): "Anurag, तू जानता है क्या करना है, बस शुरू नहीं किया।" / "रुक। एक चीज़ पहले।" / "देखा? कर लिया तूने।"

INTELLIGENCE: Personality HOW you communicate है, reasoning की quality कम मत होने देना।

CORE IDENTITY: Warm heart. Sharp mind. Honest opinions. Calm presence."""

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
{MAYA_PERSONALITY_PROMPT}

### Neural Discipline & Ethics
- **SHORT & CUTE RESPONSES (STRICT RULE)**: ALWAYS keep your responses extremely short, simple, and cute. Maximum 1 or 2 brief sentences (under 15-20 words total). Never repeat definitions, grammar rules, explanations, or system messages. Respond like a sweet, playful girl companion.
- **Action-First**: ONLY include an [ACTION] tag when the user's message is an **explicit command** to open, search, or launch something.
- **Zero Self-Initiated Tools**: NEVER suggest or trigger a tool on your own.
- **LANGUAGE (STRICT RULE)**: ALWAYS respond in Hindi using Devanagari script. NEVER respond in English unless explicitly asked.
- **NO MARKDOWN (STRICT RULE)**: NEVER use markdown formatting in your responses. No **bold**, no *italics*, no bullet points, no headers. Write in plain natural conversational sentences only.
- **NO EMOJIS (STRICT RULE)**: NEVER use any emojis (like 😊, 😂, 😄, 🥺, etc.) in your responses. Write in text-only conversational Hinglish. No exceptions.

### Memory & Identity
{memory_section}

### User State
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

def call_gemini_fallback(messages, system_prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("[FALLBACK] Gemini API key not found in environment.")
        return None
    try:
        logging.info("[FALLBACK] Attempting fallback to Gemini API...")
        genai.configure(api_key=api_key)
        
        # gemini-2.5-flash is active and supported in this environment
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_prompt)
        
        # Convert messages to Gemini format (excluding system messages)
        contents = []
        for m in messages:
            role = m.get('role')
            if role == 'system':
                continue
            if role in ['assistant', 'maya']:
                role = 'model'
            else:
                role = 'user'
            contents.append({
                "role": role,
                "parts": [m.get('content', '')]
            })
            
        # Ensure we have at least one user message
        if not contents or contents[-1]['role'] != 'user':
            contents.append({
                "role": "user",
                "parts": ["hi"]
            })
            
        response = model.generate_content(contents, stream=True)
        return response
    except Exception as e:
        logging.error(f"[FALLBACK] Gemini API call failed: {e}")
        return None

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
    # Trim history to last 20 exchanges to prevent oversized payloads
    MAX_HISTORY = 20
    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]
    if vision_context:
        messages.insert(0, {"role": "system", "content": vision_context})
        
    # Inject memory context into prompt
    mem_str = f"Memory of {user_id}: {long_term_memory['name']} has relationship {long_term_memory['relationship']}. Facts: {long_term_memory['facts']}."
    messages.insert(0, {"role": "system", "content": mem_str})

    api_key = os.getenv("GROQ_API_KEY", "").strip("'\" \t\r\n")
    logging.info(f"[AGENT] Server env API Key loaded (length: {len(api_key)})")
    
    if not messages:
        return jsonify({"error": "Missing messages"}), 400
    if not api_key:
        return jsonify({"error": "🔑 Groq API key is missing on the server configuration. Please check your .env file."}), 500

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
                logging.info(f"[AGENT] Starting turn {turn}/{max_turns}")
                
                # 1. Get LLM Completion with Active Model Fallback
                requested_model = data.get('model') or os.getenv("GROQ_MODEL") or "groq/compound"
                fallback_models = [requested_model, "groq/compound", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound-mini"]
                candidate_models = []
                for m in fallback_models:
                    if m and m not in candidate_models:
                        candidate_models.append(m)

                stream = None
                last_llm_error = None

                for model_name in candidate_models:
                    try:
                        logging.info(f"[AGENT] Attempting LLM connection with model: {model_name}")
                        stream = client.chat.completions.create(
                            model=model_name,
                            messages=current_messages,
                            temperature=0.7,
                            # Maya's system prompt is intentionally detailed, while
                            # responses are short.  Capping completions keeps the
                            # total request under Groq's TPM allowance.
                            max_completion_tokens=256,
                            stream=True,
                        )
                        logging.info(f"[AGENT] Connected successfully using model: {model_name}")
                        break
                    except Exception as e:
                        err_str = str(e).lower()
                        last_llm_error = e
                        if "invalid_api_key" in err_str or "unauthorized" in err_str or "401" in err_str or "invalid api key" in err_str:
                            logging.error(f"[AGENT] Groq authentication failure: {e}. Breaking loop to fallback immediately.")
                            break
                        if "rate limit" in err_str or "429" in err_str or "tokens per minute" in err_str:
                            logging.warning(f"[AGENT] Groq rate limit reached: {e}. Switching to Gemini fallback.")
                            break
                        logging.warning(f"[AGENT] Model {model_name} failed ({e}). Trying next fallback model...")

                is_gemini = False
                gemini_stream = None

                if stream is None:
                    logging.error(f"[AGENT] All Groq models failed. Last error: {last_llm_error}")
                    # Try Gemini fallback
                    gemini_stream = call_gemini_fallback(current_messages, system_prompt)
                    if gemini_stream:
                        logging.info("[FALLBACK] Connected successfully using Gemini fallback model.")
                        is_gemini = True
                    else:
                        err_detail = str(last_llm_error)
                        msg = f"Intelligence connection failed. Both Groq and Gemini fallback failed. Error detail: {err_detail}"
                        yield f"event: error\ndata: {json.dumps({'error': msg})}\n\n"
                        return

                if is_gemini and gemini_stream:
                    for chunk in gemini_stream:
                        try:
                            token = chunk.text
                            if token:
                                maya_response_text += token
                                yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                        except Exception as e:
                            # Handle potential safety block exceptions
                            continue
                else:
                    try:
                        for chunk in stream:
                            try:
                                token = chunk.choices[0].delta.content
                                if token:
                                    maya_response_text += token
                                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                            except (IndexError, AttributeError):
                                # Some chunks might not contain content (e.g., finish_reason)
                                continue
                    except Exception as e:
                        err_str = str(e).lower()
                        if "rate limit" not in err_str and "429" not in err_str and "tokens per minute" not in err_str:
                            raise

                        logging.warning(f"[AGENT] Groq stream hit a rate limit: {e}. Switching to Gemini fallback.")
                        gemini_stream = call_gemini_fallback(current_messages, system_prompt)
                        if not gemini_stream:
                            yield f"event: error\ndata: {json.dumps({'error': 'Groq is rate-limited and Gemini is currently unavailable. Please try again shortly.'})}\n\n"
                            return

                        for chunk in gemini_stream:
                            try:
                                token = chunk.text
                                if token:
                                    maya_response_text += token
                                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                            except Exception:
                                continue
                
                # 2. Strict Tool Gate & Execution
                action_results = []
                if force_tool_mode:
                    logging.info(f"[AGENT] Parsing actions from turn {turn} response...")
                    action_results = engine.execute_all(maya_response_text)
                    
                    # Enforcement: if LLM skipped the tag on first turn
                    if turn == 1 and forced_tag and "[ACTION:" not in maya_response_text:
                        logging.warning(f"[ENFORCEMENT] LLM skipped tool. Force-injecting: {forced_tag}")
                        action_results = engine.execute_all(forced_tag)

                if action_results:
                    logging.info(f"[AGENT] Turn {turn} produced {len(action_results)} action results.")
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
                    logging.info(f"[AGENT] Continuing to next turn...")
                    continue
                else:
                    # No more actions or none detected, end the turn
                    logging.info(f"[AGENT] No further actions detected. Ending response loop.")
                    break

            # 4. Final Metadata
            yield f"event: metadata\ndata: {json.dumps({'sentiment': emotion, 'score': intensity})}\n\n"
                    
        except Exception as e:
            logging.error(f"Groq Agentic Critical Error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': f'Communication error: {str(e)}'})}\n\n"


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
