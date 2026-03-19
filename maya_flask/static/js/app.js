document.addEventListener('DOMContentLoaded', async () => {
    // --- 1. DOM Elements ---
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    const muteBtn = document.getElementById('mute-btn');
    const clearBtn = document.getElementById('clear-btn');
    const subtitlesContainer = document.getElementById('subtitles-container');
    const subtitlesText = document.getElementById('subtitles-text');
    const statusBadge = document.getElementById('status-badge');
    const emotionBadge = document.getElementById('emotion-badge');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-progress-text');
    const loadingProgressBar = document.getElementById('loading-bar-fill');
    const diagToggle = document.getElementById('diag-toggle');
    const diagPanel = document.getElementById('diag-panel');
    const diagEmotionInt = document.getElementById('diag-emotion-int');
    const diagState = document.getElementById('diag-state');
    const diagLatency = document.getElementById('diag-latency');
    const diagTokens = document.getElementById('diag-tokens');

    let messages = [];
    let isStreaming = false;
    let isMuted = false;
    let currentEmotion = 'neutral';
    
    // Config
    let GROQ_API_KEY = localStorage.getItem('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') || '';

    // --- 2. Animation System ---
    const STATE = {
        IDLE: "idle",
        LISTENING: "listening",
        THINKING: "thinking",
        SPEAKING: "speaking"
    };

    let currentState = STATE.IDLE;
    let currentAnimationFrames = [];
    let currentFrameIndex = 0;
    let animationTimer = 0;
    let lastAnimation = "";

    const app = new PIXI.Application();
    await app.init({
        background: '#030305',
        resizeTo: window,
        antialias: true,
        resolution: window.devicePixelRatio || 1
    });
    document.getElementById('pixi-container').appendChild(app.canvas);

    const mayaSprite = new PIXI.Sprite();
    mayaSprite.anchor.set(0.5);
    app.stage.addChild(mayaSprite);

    const textureCache = {};
    const animationFolders = ["idle", "happy", "sad", "drinking"];
    
    const patterns = {
        happy: { prefix: "grok-video-10c180fe-9d34-4328-8f33-ee0d6ea3fcb9_", suffix: "" },
        idle: { prefix: "grok-video-29dc076a-e964-448c-b62c-450d55722742_", suffix: "" },
        sad: { prefix: "grok-video-10c180fe-9d34-4328-8f33-ee0d6ea3fcb9 (1)_", suffix: "" },
        drinking: { prefix: "grok-video-29dc076a-e964-448c-b62c-450d55722742 (1)_", suffix: "" }
    };

    async function preloadAllAssets() {
        const total = animationFolders.length * 60;
        let loaded = 0;

        for (const folder of animationFolders) {
            const config = patterns[folder];
            if (loadingText) loadingText.textContent = `Optimizing ${folder} neural pathways...`;
            
            const loadPromises = [];
            for (let i = 0; i < 60; i++) {
                const num = i.toString().padStart(3, '0');
                const path = `/static/assets/animations/${folder}/${config.prefix}${num}${config.suffix}.jpg`;
                loadPromises.push(
                    PIXI.Assets.load(path).then(tex => {
                        loaded++;
                        const percent = Math.round((loaded / total) * 100);
                        if (loadingProgressBar) loadingProgressBar.style.width = `${percent}%`;
                        return { index: i, tex };
                    }).catch(e => {
                        console.warn(`Failed to load ${path}`);
                        return { index: i, tex: null };
                    })
                );
            }
            
            const results = await Promise.all(loadPromises);
            // Sort by index to ensure correct animation sequence
            textureCache[folder] = results
                .sort((a, b) => a.index - b.index)
                .map(r => r.tex)
                .filter(t => t !== null);
        }

        if (loadingText) loadingText.textContent = "All systems online.";
        setTimeout(() => {
            if (loadingOverlay) {
                loadingOverlay.style.opacity = '0';
                setTimeout(() => loadingOverlay.remove(), 1000);
            }
            transitionTo(STATE.IDLE);
        }, 800);
    }

    function playAnimation(frames, name) {
        if (lastAnimation === name) return;
        currentAnimationFrames = frames;
        currentFrameIndex = 0;
        lastAnimation = name;
        if (frames.length > 0) {
            mayaSprite.texture = frames[0];
        }
    }

    function resizeSprite() {
        if (!mayaSprite) return;
        mayaSprite.x = app.screen.width / 2;
        mayaSprite.y = app.screen.height / 2;
        const scaleH = (app.screen.height * 0.95) / 1024;
        const scaleW = (app.screen.width * 0.95) / 1536;
        const finalScale = Math.max(scaleH, scaleW);
        mayaSprite.scale.set(finalScale);
    }
    window.addEventListener('resize', resizeSprite);
    resizeSprite();

    app.ticker.add((ticker) => {
        if (currentAnimationFrames.length === 0) return;
        
        // Dynamic speed based on state and delta time for smoothness
        const baseSpeed = currentState === STATE.SPEAKING ? 1.5 : 4;
        animationTimer += ticker.deltaTime;

        if (animationTimer >= baseSpeed) {
            animationTimer = 0;
            currentFrameIndex = (currentFrameIndex + 1) % currentAnimationFrames.length;
            mayaSprite.texture = currentAnimationFrames[currentFrameIndex];
        }
    });

    async function transitionTo(state, emotion = "neutral") {
        currentState = state;
        updateStatus(state.charAt(0).toUpperCase() + state.slice(1));
        if (diagState) diagState.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        
        let folder = "idle";
        if (state === STATE.SPEAKING) {
            if (emotion === "happy") folder = "happy";
            else if (emotion === "sad") folder = "sad";
            else folder = "idle";
        } else if (state === "drinking") {
            folder = "drinking";
        }
        
        const frames = textureCache[folder] || [];
        if (frames.length > 0) playAnimation(frames, folder);
    }

    async function handleAIResponse(text, emotion) {
        await transitionTo(STATE.THINKING);
        
        // Multi-line robust regex
        const cleanText = text.replace(/\[ACTION:[\s\S]*?\]/g, '').trim();
        const speechDuration = cleanText.length * 90;

        setTimeout(async () => {
            await transitionTo(STATE.SPEAKING, emotion);
            speakText(text);

            if (cleanText.length > 80 && Math.random() > 0.4) {
                setTimeout(async () => {
                    if (currentState === STATE.SPEAKING) {
                        await transitionTo("drinking");
                        setTimeout(() => {
                            if (currentState !== STATE.IDLE) transitionTo(STATE.SPEAKING, emotion);
                        }, 3200);
                    }
                }, 4000);
            }

            setTimeout(() => {
                if (currentState === STATE.SPEAKING || currentState === "drinking") transitionTo(STATE.IDLE);
            }, speechDuration + 2000);
        }, 600);
    }

    preloadAllAssets();

    // --- 3. UI Helpers ---
    function updateStatus(status) {
        if (!statusBadge) return;
        statusBadge.textContent = status;
        statusBadge.className = `status-badge-mini ${status.toLowerCase()}`;
    }

    function appendMessage(role, content) {
        const rowDiv = document.createElement('div');
        rowDiv.className = `message-row-mini ${role}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble-mini';
        bubble.textContent = content;
        
        rowDiv.appendChild(bubble);
        chatMessages.appendChild(rowDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        const emptyState = chatMessages.querySelector('.empty-state-mini');
        if (emptyState) emptyState.remove();

        return bubble;
    }

    function showSubtitles(text) {
        subtitlesText.textContent = text;
        subtitlesContainer.style.display = 'block';
    }

    function hideSubtitles() {
        subtitlesContainer.style.display = 'none';
    }

    // --- 4. Voice Capabilities (Web Speech API) ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'hi-IN';

        recognition.onstart = () => {
            transitionTo(STATE.LISTENING);
            micBtn.classList.add('listening');
        };

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            chatInput.value = transcript;
            sendChat();
        };

        recognition.onend = () => {
            if (!isStreaming) transitionTo(STATE.IDLE);
            micBtn.classList.remove('listening');
        };
    }

    const synth = window.speechSynthesis;
    let voices = [];
    let subtitleTimeout = null;

    function loadVoices() {
        voices = synth.getVoices();
    }
    loadVoices();
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = loadVoices;
    }

    function speakText(text) {
        if (isMuted) return;
        
        // Ensure voices are loaded
        if (voices.length === 0) {
            voices = synth.getVoices();
        }

        synth.cancel();
        // Multi-line robust regex
        const cleanText = text.replace(/\[ACTION:[\s\S]*?\]/g, '').trim();
        console.log(`[TTS] Cleaning text for speech: "${cleanText}"`);
        if (!cleanText) {
            console.warn("[TTS] No speakable text found after cleaning.");
            return;
        }

        // Small delay to ensure synth.cancel() fully clears the audio buffer
        setTimeout(() => {
            const utterance = new SpeechSynthesisUtterance(cleanText);
            const isHindi = /[\u0900-\u097F]/.test(cleanText);
            
            let preferredVoice;
            if (isHindi) {
                // Priority: 1. Microsoft Neerja (Edge), 2. Any 'Natural'/ 'Online' Hindi, 3. Google Hindi
                preferredVoice = voices.find(v => v.lang.startsWith('hi') && v.name.toLowerCase().includes('neerja')) ||
                                 voices.find(v => v.lang.startsWith('hi') && (v.name.toLowerCase().includes('natural') || v.name.toLowerCase().includes('online'))) ||
                                 voices.find(v => v.lang.startsWith('hi') && v.name.includes('Google')) ||
                                 voices.find(v => v.lang.startsWith('hi')) ||
                                 voices[0];
                utterance.lang = 'hi-IN';
            } else {
                // Priority: 1. Microsoft Aria/Sonia (Natural), 2. Any 'Natural'/ 'Online' English
                preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.toLowerCase().includes('natural') || v.name.toLowerCase().includes('online'))) ||
                                 voices.find(v => v.lang.startsWith('en') && v.name.includes('Google')) ||
                                 voices.find(v => v.lang.startsWith('en')) ||
                                 voices[0];
                utterance.lang = 'en-US';
            }
            
            if (preferredVoice) {
                if (isHindi && !preferredVoice.name.toLowerCase().includes('neerja')) {
                    console.warn(`[VOICE] Neerja not found. Using fallback: ${preferredVoice.name}. Use Microsoft Edge for the best experience!`);
                } else {
                    console.log(`[VOICE] Selected: ${preferredVoice.name} (${preferredVoice.lang})`);
                }
                utterance.voice = preferredVoice;
            }
            
            // Soft & Natural Tuning
            utterance.pitch = 1.05; // Slightly higher for feminine/soft resonance
            utterance.rate = 0.88;  // Natural human pacing
            utterance.volume = 1.0;

            utterance.onstart = () => {
                showSubtitles(cleanText);
                clearTimeout(subtitleTimeout);
            };

            utterance.onerror = (e) => {
                console.error('TTS error:', e);
                transitionTo(STATE.IDLE);
            };

            utterance.onend = () => {
                subtitleTimeout = setTimeout(hideSubtitles, 3000);
                transitionTo(STATE.IDLE);
            };

            synth.speak(utterance);
        }, 100); 
    }

    // --- 5. Chat Communication ---
    async function sendChat() {
        const text = chatInput.value.trim();
        if (!text || isStreaming) return;

        chatInput.value = '';
        chatInput.style.height = 'auto';
        isStreaming = true;
        updateUIStreamingState(true);
        
        const userMsg = { role: 'user', content: text };
        messages.push(userMsg);
        appendMessage('user', text);

        let mayaBubble = appendMessage('maya', '...');
        let mayaText = '';
        let AIEmotion = 'neutral';
        let currentEvent = '';
        let tokenCount = 0;
        const startTime = Date.now();


        try {
            const payload = {
                messages: messages.map(m => ({ role: m.role === 'maya' ? 'assistant' : m.role, content: m.content })),
                user_id: 'anurag_dev' // Persistent User ID
            };
            if (GROQ_API_KEY) {
                payload.apiKey = GROQ_API_KEY;
            }

            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            if (diagLatency) diagLatency.textContent = `${Date.now() - startTime}ms`;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim() === '') {
                        currentEvent = '';
                        continue;
                    }
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (currentEvent === 'token') {
                            try {
                                const parsed = JSON.parse(data);
                                mayaText += parsed.token;
                                tokenCount++;
                                if (diagTokens) diagTokens.textContent = tokenCount;
                                // Multi-line robust regex
                                const displayableText = mayaText.replace(/\[ACTION:[\s\S]*?\]/g, '').trim();
                                mayaBubble.textContent = displayableText || '...';
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            } catch (e) {}
                        } else if (currentEvent === 'thinking') {
                            try {
                                const think = JSON.parse(data);
                                mayaBubble.textContent = `Maya is ${think.message.toLowerCase()}...`;
                                mayaBubble.classList.add('working');
                            } catch (e) {}
                        } else if (currentEvent === 'actions') {
                            try {
                                const actionResults = JSON.parse(data);
                                renderActionResults(mayaBubble, actionResults);
                            } catch (e) {
                                console.error("Error parsing actions:", e);
                            }
                        } else if (currentEvent === 'metadata') {
                            try {
                                const meta = JSON.parse(data);
                                AIEmotion = meta.sentiment || 'neutral';
                                const intensity = meta.score || (AIEmotion === 'neutral' ? 0.5 : 0.8);
                                if (diagEmotionInt) diagEmotionInt.textContent = intensity.toFixed(2);
                                if (emotionBadge) {
                                    emotionBadge.innerHTML = `${AIEmotion === 'happy' ? '😄' : AIEmotion === 'sad' ? '🥺' : AIEmotion === 'angry' ? '😡' : AIEmotion === 'anxious' ? '😰' : AIEmotion === 'lonely' ? '😔' : '😊'} ${AIEmotion}`;
                                }
                            } catch (e) {}
                        }
                    }
                }
            }

            handleAIResponse(mayaText, AIEmotion);
            
            // Preserve ACTION tags in history so Maya knows what she's already done
            messages.push({ role: 'maya', content: mayaText });
            
        } catch (err) {
            console.error("Chat Error:", err);
            mayaBubble.textContent = "I'm having trouble connecting right now. Let me try to reset.";
            updateStatus('Offline');
        } finally {
            isStreaming = false;
            updateUIStreamingState(false);
            if (mayaBubble) mayaBubble.classList.remove('working');
        }
    }

    function updateUIStreamingState(streaming) {
        micBtn.disabled = streaming;
        sendBtn.disabled = streaming;
        chatInput.disabled = streaming;
        micBtn.style.opacity = streaming ? '0.5' : '1';
        sendBtn.style.opacity = streaming ? '0.5' : '1';
        micBtn.style.pointerEvents = streaming ? 'none' : 'auto';
        sendBtn.style.pointerEvents = streaming ? 'none' : 'auto';
    }

    // --- 5a. UI Component Factory ---
    function renderActionResults(parentBubble, results) {
        const wrap = document.createElement('div');
        wrap.className = 'action-results-container';
        
        results.forEach(res => {
            if (res.status === 'success') {
                const component = createComponent(res.action, res.output);
                if (component) wrap.appendChild(component);
                updateDiagnosticsPluginTrace(res.action, res.duration);
            } else if (res.status === 'requires_permission') {
                const authCard = createPermissionCard(res.action, res.params);
                if (authCard) wrap.appendChild(authCard);
            } else {
                console.warn(`Action ${res.action} failed: ${res.message}`);
                updateDiagnosticsPluginTrace(res.action, "FAILED", true);
            }
        });
        
        if (wrap.hasChildNodes()) {
            parentBubble.parentElement.appendChild(wrap);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function createComponent(type, data) {
        const card = document.createElement('div');
        card.className = 'plugin-card';
        
        if (data.type === 'web_open') {
            card.innerHTML = `
                <div class="card-header">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    <span>${type.toUpperCase()} Launcher</span>
                </div>
                <button class="card-action-btn" onclick="window.open('${data.url}', '_blank')">
                    Launch ${type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
            `;
        } else if (type === 'weather') {
            card.innerHTML = `
                <div class="card-header">
                    <i class="fa-solid fa-cloud-sun"></i>
                    <span>Weather: ${data.location}</span>
                </div>
                <div class="weather-body">
                    <div class="temp">${data.temp}</div>
                    <div class="condition">${data.condition}</div>
                </div>
            `;
        }
        return card;
    }
        
    function createPermissionCard(type, params) {
        const card = document.createElement('div');
        card.className = 'plugin-card permission-card';
        card.dataset.params = JSON.stringify(params);
        card.innerHTML = `
            <div class="card-header">
                <i class="fa-solid fa-shield-halved"></i>
                <span>Permission Required</span>
            </div>
            <p class="perm-desc">Allow Maya to use <strong>${type}</strong>?</p>
            <div class="perm-actions">
                <button class="perm-btn allow" onclick="executeAuthorizedAction('${type}', this)">Allow</button>
                <button class="perm-btn deny" onclick="this.closest('.plugin-card').remove()">Deny</button>
            </div>
        `;
        return card;
    }

    async function executeAuthorizedAction(type, btn) {
        const card = btn.closest('.plugin-card');
        const params = JSON.parse(card.dataset.params || '{}');
        card.innerHTML = '<div class="loader-mini"></div> Executing...';
        
        try {
            const resp = await fetch('/execute_action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: type, params })
            });
            const res = await resp.json();
            
            if (res.status === 'success') {
                const component = createComponent(type, res.output);
                card.replaceWith(component);
                updateDiagnosticsPluginTrace(type, res.duration);
            } else {
                card.innerHTML = `<span style="color:#ff4d4d">Error: ${res.message}</span>`;
            }
        } catch (e) {
            card.innerHTML = '<span style="color:#ff4d4d">Execution Failed</span>';
        }
    }

    window.executeAuthorizedAction = executeAuthorizedAction; // Make global for onclick

    function updateDiagnosticsPluginTrace(name, duration, failed = false) {
        const traceEl = document.getElementById('diag-plugin-trace');
        if (!traceEl) return;
        
        const entry = document.createElement('div');
        entry.className = `diag-trace-entry ${failed ? 'failed' : ''}`;
        entry.innerHTML = `
            <span class="plugin-name">${name}</span>
            <span class="plugin-time">${duration}</span>
        `;
        
        traceEl.prepend(entry);
        if (traceEl.children.length > 5) traceEl.lastElementChild.remove();
    }

    // --- 6. Event Listeners ---
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        sendBtn.style.display = chatInput.value.trim() ? 'block' : 'none';
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChat();
        }
    });

    document.getElementById('chat-form').addEventListener('submit', (e) => {
        e.preventDefault();
        sendChat();
    });

    micBtn.addEventListener('click', () => {
        if (recognition) recognition.start();
    });

    muteBtn.addEventListener('click', () => {
        isMuted = !isMuted;
        muteBtn.innerHTML = isMuted ? '<i class="fa-solid fa-volume-xmark"></i>' : '<i class="fa-solid fa-volume-high"></i>';
        if (isMuted && synth.speaking) synth.cancel();
    });

    clearBtn.addEventListener('click', () => {
        chatMessages.innerHTML = '';
        messages = [];
        if (synth.speaking) synth.cancel();
        hideSubtitles();
        transitionTo(STATE.IDLE);
    });

    diagToggle.addEventListener('click', () => {
        diagPanel.classList.toggle('active');
        diagToggle.classList.toggle('active');
    });

    const sidebar = document.querySelector('.chat-box-overlay');
    const diagPanelOverlay = document.getElementById('diag-panel');
    
    let touchStartX = 0;
    let touchStartY = 0;

    // Mobile swipe for Sidebar
    document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, {passive: true});
    
    document.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;
        const diffX = touchEndX - touchStartX;
        const diffY = Math.abs(touchEndY - touchStartY);

        // Sidebar logic (Horizontal swipe)
        if (diffY < 50) { // Ensure it's mostly a horizontal swipe
            if (diffX > 100) { // Swipe right: Show sidebar
                sidebar.classList.remove('hidden');
            } else if (diffX < -100) { // Swipe left: Hide sidebar
                sidebar.classList.add('hidden');
            }
        }
        
        // Diagnostics Panel logic (Vertical swipe from top)
        if (touchStartY < 100 && touchEndY > 200) {
            diagPanelOverlay.classList.add('active');
            diagToggle.classList.add('active');
        }
    }, {passive: true});

    // Tap outside to close diag
    document.addEventListener('click', (e) => {
        if (diagPanelOverlay.classList.contains('active') && 
            !diagPanelOverlay.contains(e.target) && 
            e.target !== diagToggle) {
            diagPanelOverlay.classList.remove('active');
            diagToggle.classList.remove('active');
        }
    });
});
