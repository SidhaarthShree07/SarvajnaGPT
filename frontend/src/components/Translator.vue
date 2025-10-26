<template>
    <div v-bind="attrs" class="font-sans min-h-screen w-full flex flex-col items-center pt-6 md:pt-10 px-3 md:px-0">
        <!-- Back Button -->
        <button @click="emit('back')"
            :class="['fixed left-6 bottom-6 md:left-12 md:bottom-12 px-5 py-3 rounded-full bg-white/10 transition-colors focus:outline-none flex items-center gap-2 z-50', (darkMode || powerMode) ? 'text-white hover:bg-white/20 focus:ring-2 focus:ring-orange-400' : 'text-orange-400 hover:bg-white/20 focus:ring-2 focus:ring-orange-400']"
            >
            <span class="material-symbols-outlined text-lg">arrow_back</span>
            <span class="hidden md:inline">Back to Home</span>
        </button>

    <div class="frosted-glass-card w-full max-w-[1000px] mx-auto p-6 md:p-12 rounded-3xl border border-white/20 shadow-2xl flex flex-col gap-8 md:gap-12 items-center">
            <!-- Header -->
            <div class="w-full flex flex-wrap md:flex-nowrap items-center gap-4 md:gap-8 justify-between mb-6 md:mb-8 px-2 md:px-6">
                <span class="material-symbols-outlined text-orange-400 text-3xl">translate</span>
                <div class="flex-1">
                    <h2 :class="['text-2xl font-bold', darkMode ? 'text-white' : 'text-orange-400']">Translator</h2>
                    <p :class="[darkMode ? 'text-gray-300' : 'text-gray-800','text-sm font-light']">AI-powered translation</p>
                </div>
                <button class="icon-btn" title="Clear conversation" @click="clearChat">
                    <span class="material-symbols-outlined text-orange-300">delete</span>
                </button>
            </div>

            <!-- Language selector header -->
            <div class="w-full flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 md:gap-6 mb-6 md:mb-8 px-2 md:px-6">
                <div class="dropdown-container flex-1 min-w-[140px] order-1">
                    <label :class="[darkMode ? 'text-white' : 'text-gray-800','lang-label']">Your Language</label>
                    <button :class="['lang-btn w-full', darkMode ? 'text-white' : 'text-gray-800']" @click="openLangModal('user')">
                        {{ languages.find(l => l.code === userLang)?.label || 'Select Language' }}
                    </button>
                </div>
                <div class="flex items-center justify-center order-2 md:order-none">
                <button class="icon-btn swap-btn mx-auto" title="Swap Languages" @click="swapLanguages">
                    <span class="material-symbols-outlined text-2xl text-orange-400">swap_horiz</span>
                </button>
                </div>
                <div class="dropdown-container flex-1 min-w-[140px] order-3 md:order-none">
                    <label :class="[darkMode ? 'text-white' : 'text-gray-800','lang-label']">Target Language</label>
                    <button :class="['lang-btn w-full', darkMode ? 'text-white' : 'text-gray-800']" @click="openLangModal('other')">
                        {{ languages.find(l => l.code === otherLang)?.label || 'Select Language' }}
                    </button>
                </div>
        <!-- Language Modal -->
    <div v-if="showLangModal" class="lang-mo fixed inset-0 z-50 flex items-center justify-center rounded-3xl bg-black/60 p-4 overflow-y-auto">
        <div class="lang-modal rounded-2xl p-6 md:p-8 w-full max-w-2xl mx-auto flex flex-col gap-4 md:gap-6 max-h-[90vh] overflow-y-auto">
                <div class="flex items-center justify-between mb-4">
                    <h3 :class="[darkMode ? 'text-white' : 'text-orange-400','text-2xl font-bold']">Select Language</h3>
                    <button class="icon-btn" @click="closeLangModal" title="Close">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <input v-model="langSearch" type="text" class="lang-search-input" placeholder="Search language..." />
                <div class="lang-grid grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 md:gap-4">
                    <button v-for="lang in filteredLanguages" :key="lang.code" class="lang-select-btn" @click="selectLang(lang.code)">
                        {{ lang.label }}
                    </button>
                </div>
            </div>
        </div>
            </div>

            <!-- Conversation area -->
            <div ref="messagesBox" class="w-full box-output overflow-y-auto px-3 md:px-6 mb-6 md:mb-8" style="max-height: 420px; min-height: 160px;">
                <div v-if="messages.length === 0" :class="[(darkMode || powerMode) ? 'text-gray-300/60' : 'text-gray-600/60','text-center py-8']">No conversation yet. Start translating!</div>
                <div v-for="(msg, idx) in messages" :key="idx" class="flex items-start gap-3 mb-3" :class="msg.role === 'user' ? 'flex-row' : 'flex-row-reverse'" style="margin-bottom: 10px;">
                    <div class="flex-shrink-0">
                        <span class="material-symbols-outlined text-2xl" :class="msg.role === 'user' ? 'text-orange-400' : 'text-orange-300'">person</span>
                    </div>
                    <div class="flex-1">
                        <div :class="['bg-white/10 rounded-xl px-4 py-2 mb-2 border border-white/20 flex items-center gap-2', darkMode ? 'text-white' : 'text-gray-800']">
                            <span v-html="boldify(cleanForDisplay(msg.text))"></span>
                            <button @click="playAudio(msg.text, msg.role === 'user' ? userLang : otherLang)" class="ml-2 bg-orange-400 hover:bg-orange-500 text-white rounded-full p-1 flex items-center" title="Play Voice">
                                <span class="material-symbols-outlined text-base">volume_up</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Input area -->
            <div class="w-full flex flex-col gap-3 md:gap-4 px-1 md:px-4">
                <div class="flex items-center gap-3 flex-wrap">
                    <button class="icon-btn role-btn" @click="activeRole = 'user'" title="Speak as You">
                        <span class="material-symbols-outlined text-2xl" :class="activeRole === 'user' ? 'text-orange-500' : 'text-orange-300'">person</span>
                    </button>
                    <button class="icon-btn role-btn" @click="activeRole = 'other'" title="Speak as Other">
                        <span class="material-symbols-outlined text-2xl" :class="activeRole === 'other' ? 'text-orange-400' : 'text-orange-200'">group</span>
                    </button>
                    <div :class="[(darkMode || powerMode) ? 'text-gray-300' : 'text-gray-700','text-sm ml-2']">Typing as <b>{{ activeRole === 'user' ? 'You' : 'Other' }}</b></div>
                </div>
                <textarea v-model="activeText" rows="2" class="box-textarea resize-y min-h-[90px]" placeholder="Type or use voice..."></textarea>
                <div class="box-btn-row flex justify-end gap-2 pt-1">

                    <button @click="startVoice(activeRole)" class="icon-btn action-btn" :title="(activeRole==='user'? isListeningUser : isListeningOther) ? 'Listening...' : 'Voice Input'">
                            <span class="material-symbols-outlined text-2xl voice-icon text-orange-400">keyboard_voice</span>
                    </button>
                        <button @click="translate(activeRole)" class="icon-btn action-btn shrink-0" title="Send">
                            <span class="material-symbols-outlined text-xl md:text-2xl send-icon text-orange-400">send</span>
                        </button>
                </div>
            </div>
        </div>
    </div>
    <!-- App-wide lightweight modal for this component -->
    <div v-if="modalOpen" class="fixed inset-0 z-[100] flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl w-[90vw] max-w-md p-5 border border-indigo-200/40">
            <div class="flex items-start gap-3">
                <div class="w-10 h-10 rounded-full flex items-center justify-center"
                     :class="{
                       'bg-indigo-100 text-indigo-700': modalKind==='info',
                       'bg-red-100 text-red-700': modalKind==='error',
                       'bg-amber-100 text-amber-700': modalKind==='confirm',
                     }">
                    <span class="material-symbols-outlined">
                        {{ modalKind==='error' ? 'error' : (modalKind==='confirm' ? 'help' : 'info') }}
                    </span>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-lg font-semibold text-gray-900 mb-1">{{ modalTitle }}</div>
                    <div class="text-sm text-gray-700 whitespace-pre-line break-words">{{ modalMessage }}</div>
                </div>
                <button class="p-2 rounded-lg text-gray-500 hover:bg-gray-100" @click="handleModalCancel" aria-label="Close modal">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="mt-4 flex justify-end gap-2">
                <button v-if="modalKind==='confirm'" @click="handleModalCancel"
                        class="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200">
                    {{ modalCancelText || 'Cancel' }}
                </button>
                <button @click="handleModalConfirm"
                        :class="modalKind==='error' ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-indigo-600 hover:bg-indigo-700 text-white'"
                        class="px-4 py-2 rounded-lg">
                    {{ modalConfirmText || 'OK' }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
// accept theme props from parent
const props = defineProps(['darkMode', 'powerMode']);
const darkMode = toRef(props, 'darkMode');
const powerMode = toRef(props, 'powerMode');

// declare emitted events so parent listeners are recognized
const emit = defineEmits(['back']);

// capture and bind any non-prop attributes (like style) so Vue doesn't warn when component
// renders a fragment. We'll bind `attrs` onto the main wrapper element below.
import { useAttrs } from 'vue';
const attrs = useAttrs();

// Lightweight modal helpers
const modalOpen = ref(false);
const modalTitle = ref('');
const modalMessage = ref('');
const modalKind = ref('info'); // 'info' | 'confirm' | 'error'
const modalConfirmText = ref('OK');
const modalCancelText = ref('Cancel');
let modalResolver = null;

function showAlertModal(message, title = 'Notice') {
    modalTitle.value = title; modalMessage.value = message; modalKind.value = 'info';
    modalConfirmText.value = 'OK'; modalCancelText.value = ''; modalOpen.value = true;
    return new Promise((resolve) => { modalResolver = () => { modalOpen.value = false; modalResolver = null; resolve(undefined); }; });
}
function handleModalConfirm() { if (modalResolver) modalResolver(true); else modalOpen.value = false; }
function handleModalCancel() { if (modalResolver) modalResolver(false); else modalOpen.value = false; }
const showLangModal = ref(false);
const langModalTarget = ref('user');
const langSearch = ref('');
function openLangModal(target) {
    langModalTarget.value = target;
    langSearch.value = '';
    showLangModal.value = true;
}
function closeLangModal() {
    showLangModal.value = false;
}
function selectLang(code) {
    if (langModalTarget.value === 'user') userLang.value = code;
    else otherLang.value = code;
    showLangModal.value = false;
}
const filteredLanguages = computed(() => {
    if (!langSearch.value.trim()) return languages;
    return languages.filter(l => l.label.toLowerCase().includes(langSearch.value.trim().toLowerCase()));
});
// Set multi-word component name to fix lint error
defineOptions({ name: 'TranslatorComponent' });
// Imports must be at top
import { ref, computed, toRef } from 'vue';
import { nextTick } from 'vue';
// Local UI state
// Mobile UI: which side is active for typing
const activeRole = ref('user');

const languages = [
    { code: 'en', label: 'English' },
    { code: 'hi', label: 'Hindi' },
    { code: 'fr', label: 'French' },
    { code: 'de', label: 'German' },
    { code: 'es', label: 'Spanish' },
    { code: 'ta', label: 'Tamil' },
    { code: 'te', label: 'Telugu' },
    { code: 'bn', label: 'Bengali' },
    { code: 'zh-cn', label: 'Chinese' },
    { code: 'ru', label: 'Russian' },
    { code: 'ja', label: 'Japanese' },
    { code: 'ko', label: 'Korean' },
    { code: 'ar', label: 'Arabic' },
    { code: 'tr', label: 'Turkish' },
    { code: 'it', label: 'Italian' },
    { code: 'pt', label: 'Portuguese' },
    { code: 'pl', label: 'Polish' },
    { code: 'nl', label: 'Dutch' },
    { code: 'uk', label: 'Ukrainian' },
];


const userLang = ref('en');
const otherLang = ref('hi');
const userInput = ref('');
const otherInput = ref('');
const isListeningUser = ref(false);
const isListeningOther = ref(false);

const messages = ref([]); // {role: 'user'|'other', text, voiceUrl}
const messagesBox = ref(null);

function scrollToBottom() {
    nextTick(() => {
        const el = messagesBox.value;
        if (el) el.scrollTop = el.scrollHeight;
    });
}

// Bind the single textarea to the appropriate input based on activeRole
const activeText = computed({
    get() {
        return activeRole.value === 'user' ? userInput.value : otherInput.value;
    },
    set(v) {
        if (activeRole.value === 'user') userInput.value = v; else otherInput.value = v;
    }
});

function swapLanguages() {
    const temp = userLang.value;
    userLang.value = otherLang.value;
    otherLang.value = temp;
}

function startVoice(who) {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showAlertModal('Voice recognition not supported in this browser.', 'Notice');
        return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = new SpeechRecognition();
    recognition.lang = who === 'user' ? userLang.value : otherLang.value;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    if (who === 'user') isListeningUser.value = true;
    else isListeningOther.value = true;
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (who === 'user') {
            userInput.value = transcript;
            isListeningUser.value = false;
            sendTranslate('user', transcript);
        } else {
            otherInput.value = transcript;
            isListeningOther.value = false;
            sendTranslate('other', transcript);
        }
    };
    recognition.onerror = () => {
        if (who === 'user') isListeningUser.value = false;
        else isListeningOther.value = false;
    };
    recognition.onend = () => {
        if (who === 'user') isListeningUser.value = false;
        else isListeningOther.value = false;
    };
    recognition.start();
}

function translate(who) {
    // Only send if user typed and clicked button
    if (who === 'user' && userInput.value.trim()) {
        sendTranslate('user', userInput.value);
    } else if (who === 'other' && otherInput.value.trim()) {
        sendTranslate('other', otherInput.value);
    }
}

function cleanForDisplay(text) {
    // Remove <thuk>...</thuk> or <think>...</think> tags and their content
    let cleaned = text.replace(/<thuk[^>]*>[\s\S]*?<\/thuk>/gi, '').replace(/<think[^>]*>[\s\S]*?<\/think>/gi, '');
    return cleaned;
}

function boldify(text) {
    // Replace **text** with <b>text</b>
    return text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
}

function cleanForTTS(text) {
    // Remove <thuk>...</thuk> and <think>...</think> and **bold**
    let cleaned = text.replace(/<thuk[^>]*>[\s\S]*?<\/thuk>/gi, '').replace(/<think[^>]*>[\s\S]*?<\/think>/gi, '');
    cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '$1');
    return cleaned;
}

function sendTranslate(who, text) {
    let from, to;
    let role;
    if (who === 'user') {
        from = userLang.value;
        to = otherLang.value;
        role = 'user';
    } else {
        from = otherLang.value;
        to = userLang.value;
        role = 'other';
    }
    // Show the original message in the conversation
    messages.value.push({ role, text });
    scrollToBottom();
    // Clear the input after sending
    if (who === 'user') userInput.value = ''; else otherInput.value = '';
    // Compute backend base (dev vite uses port 5173/4173 etc.)
    const ORIGIN = (typeof window !== 'undefined') ? window.location.origin : '';
    const isDevVite = /:(3000|5173|4173|5174)\b/.test(ORIGIN);
    const API_BASE = isDevVite ? 'http://localhost:8000' : (ORIGIN || 'http://localhost:8000');
    const apiUrl = API_BASE + '/api/translate';

    // Insert a placeholder assistant bubble while translating
    const otherRole = role === 'user' ? 'other' : 'user';
    const placeholder = { role: otherRole, text: 'Translating…' };
    messages.value.push(placeholder);
    const idx = messages.value.length - 1;
    scrollToBottom();
    fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, from, to })
    })
        .then(async (r) => {
            let data;
            try {
                data = await r.json();
            } catch {
                const txt = await r.text();
                data = { text: txt };
            }
            return data;
        })
        .then(res => {
            console.debug('translate response:', res);
            const out = (res && typeof res.text === 'string') ? res.text : '';
            messages.value[idx] = { role: otherRole, text: out || '[no translation returned]' };
            scrollToBottom();
        })
        .catch(err => {
            messages.value[idx] = { role: otherRole, text: `Translation failed: ${String(err)}` };
            scrollToBottom();
        });
}

// Replace playAudio with async version that uses /api/voice_chunk
async function playAudio(urlOrText, lang) {
    // If urlOrText is a URL, just play it. If it's text, call /api/voice_chunk.
    if (typeof urlOrText === 'string' && urlOrText.startsWith('/static/')) {
        // Always use backend domain for static audio
    const ORIGIN = (typeof window !== 'undefined') ? window.location.origin : '';
    const isDevVite = /:(3000|5173|4173|5174)\b/.test(ORIGIN);
    const API_BASE = isDevVite ? 'http://localhost:8000' : (ORIGIN || 'http://localhost:8000');
    const absUrl = API_BASE + urlOrText;
        console.log('Playing static audio URL:', absUrl);
        const audio = new Audio(absUrl);
        audio.play().catch(e => console.error('Audio playback error:', e));
        return;
    }
    // Otherwise, generate TTS using /api/voice_chunk
    const text = cleanForTTS(urlOrText);
    const ORIGIN2 = (typeof window !== 'undefined') ? window.location.origin : '';
    const isDevVite2 = /:(3000|5173|4173|5174)\b/.test(ORIGIN2);
    const API_BASE2 = isDevVite2 ? 'http://localhost:8000' : (ORIGIN2 || 'http://localhost:8000');
    const apiUrl = API_BASE2 + '/api/voice_chunk';
    const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, lang })
    });
    try {
        const data = await res.json();
        const urls = (data && Array.isArray(data.chunks) && data.chunks.length > 0)
            ? data.chunks
            : (data && data.voiceUrl ? [data.voiceUrl] : []);
        console.log('Received audio URLs:', urls);
        if (urls.length > 0) {
            // Ensure absolute URL for audio playback
            let playUrl = urls[0];
            if (playUrl.startsWith('/static/')) {
                const ORIGIN3 = (typeof window !== 'undefined') ? window.location.origin : '';
                const isDevVite3 = /:(3000|5173|4173|5174)\b/.test(ORIGIN3);
                const API_BASE3 = isDevVite3 ? 'http://localhost:8000' : (ORIGIN3 || 'http://localhost:8000');
                playUrl = API_BASE3 + playUrl;
            }
            // Play first chunk for now; can be extended to sequential playback
            const audio = new Audio(playUrl);
            audio.play().catch(e => console.error('Audio playback error:', e));
        } else {
            console.warn('No audio URL received from backend.');
        }
    } catch (err) {
        console.error('Error parsing or playing audio:', err);
    }
}

function clearChat() {
    messages.value = [];
}


</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

.dropdown-container {
    position: relative;
    display: inline-block;
    margin-right: 0.5rem;
}

    .box-output {
        background: rgba(255,255,255,0.10);
        border-radius: 1rem;
        padding: 2rem;
        color: #e0e7ef;
        font-size: 1.12rem;
    }
.lang-btn {
    padding: 0.7rem 0.9rem;
    font-size: 0.95rem;
    font-weight: 600;
    border: 1.2px solid rgba(255,255,255,0.14);
    border-radius: 0.9rem;
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(8px) saturate(120%);
    -webkit-backdrop-filter: blur(8px) saturate(120%);
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transition: background 0.18s, color 0.18s, transform 0.12s;
    margin: 0.25rem 0;
    width: 100%;
    text-align: left;
    padding-left: 1.2rem;
    outline: none;
}
.lang-btn:hover {
    background: rgba(255,255,255,0.06);
    transform: translateY(-1px);
}

.lang-modal {
    min-height: 400px;
}

.lang-mo {
    /* Use frosted glass for modal panel to match card */
    background: rgb(37, 36, 36);
    border: 1.2px solid rgba(255,255,255,0.10);
}

.lang-search-input {
    padding: 1rem 1.5rem;
    border-radius: 0.75rem;
    border: 1.5px solid #f88e38;
    background: rgba(255,255,255,0.08);
    color: #e0e7ef;
    font-size: 1.1rem;
    outline: none;
    margin-bottom: 1rem;
}
.lang-grid {
    width: 100%;
}
.lang-select-btn {
    padding: 0.9rem 0.75rem;
    border-radius: 1rem;
    color: #e6f7ff;
    border: 1.2px solid rgba(255,255,255,0.14);
    border-radius: 0.9rem;
    background: rgba(255,255,255,0.035);
    backdrop-filter: blur(8px) saturate(120%);
    -webkit-backdrop-filter: blur(8px) saturate(120%);
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transition: background 0.18s, color 0.18s, transform 0.12s;
}
.lang-select-btn:hover {
    background: rgba(255,255,255,0.06);
    transform: translateY(-1px);
}

.dropdown-content {
    display: block;
    position: absolute;
    top: 115%;
    left: 0;
    min-width: 320px;
    border-radius: 18px;
    overflow: hidden;
    border: 1.5px solid rgba(255,255,255,0.18);
    background: rgba(255,255,255,0.18);
    backdrop-filter: blur(20px) brightness(1.1);
    -webkit-backdrop-filter: blur(20px) brightness(1.1);
    box-shadow: 0 8px 32px rgba(0,0,0,0.22);
    z-index: 100;
}

.grid-dropdown .dropdown-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.5rem;
    padding: 1rem;
}
.grid-dropdown a {
    color: #fff;
    padding: 1rem 0.5rem;
    text-decoration: none;
    display: block;
    text-align: center;
    border-radius: 10px;
    font-size: 1rem;
    font-family: 'Inter', sans-serif;
    background: transparent;
    transition: background-color 0.3s ease;
}
.grid-dropdown a:hover {
    background-color: rgba(255,255,255,0.22);
    color: #38bdf8;
}

.dropdown-content a {
    color: #fff;
    padding: 1rem 1.5rem;
    text-decoration: none;
    display: block;
    transition: background-color 0.3s ease;
    font-size: 1rem;
    font-family: 'Inter', sans-serif;
}

.dropdown-content a:hover {
    background-color: rgba(255, 255, 255, 0.3);
}
/* Glassmorphic dropdown list for select */
select.lang-select {
    background: rgba(255,255,255,0.10);
    border-radius: 1.2rem;
    border: 1.5px solid rgba(255,255,255,0.18);
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    color: #e0e7ef;
    font-size: 1.1rem;
    min-width: 120px;
    padding: 1.2rem 1.5rem;
}

select.lang-select:focus {
    outline: none;
    border-color: #38bdf8;
}

select.lang-select option {
    background: rgba(30,41,59,0.85);
    color: #e0e7ef;
    font-size: 1.1rem;
    border-radius: 0.75rem;
    padding: 0.5rem 1rem;
}

/* For browsers supporting ::part (like Chromium-based) */
select.lang-select::part(listbox) {
    background: rgba(255,255,255,0.10);
    border-radius: 1.2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
select.lang-select::part(option) {
    background: rgba(30,41,59,0.85);
    color: #e0e7ef;
    border-radius: 0.75rem;
    padding: 0.5rem 1rem;
}
.glass-select {
    gap: 2rem;
    margin-bottom: 2rem;
}

.lang-label {
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: block;
}

.lang-select {
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    background: rgba(255, 255, 255, 0.1);
    color: #222;
    min-width: 120px;
}

.main-row {
    display: flex;
    flex-direction: row;
    gap: 2rem;
    margin-bottom: 2rem;
    width: 100%;
    align-items: flex-start;
}

.box-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.person-icon {
    color: #3b82f6;
    font-size: 1.5rem;
}

.person-icon-alt {
    color: #06b6d4;
    font-size: 1.5rem;
}

.box-label {
    color: #fff;
}

.box-textarea {
    width: 100%;
    border-radius: 0.75rem;
    border: 1px solid #e0e0e0;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.08);
    color: #222;
    font-size: 1rem;
    resize: vertical;
    margin-bottom: 0.5rem;
}

.box-btn-row {
    margin-top: 0.5rem;
    display: flex;
    justify-content: flex-end;
}

.box-btn {
    background: linear-gradient(90deg, #3b82f6, #06b6d4);
    color: #fff;
    border: none;
    border-radius: 0.5rem;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.box-btn:hover {
    background: linear-gradient(90deg, #2563eb, #0891b2);
}

    .icon-btn {
        background: rgba(255,255,255,0.14);
        border: 1.5px solid rgba(255,255,255,0.22);
        border-radius: 0.6rem; /* pill/rounded rectangle instead of full circle */
        padding: 0.55rem 0.9rem;
        font-size: 1.1rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: background 0.18s, color 0.18s, box-shadow 0.18s, transform 0.12s;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        cursor: pointer;
        gap: 0.5rem;
    }
    .icon-btn:hover {
        background: rgba(253, 186, 116, 0.18);
        color: rgb(253, 186, 116 / var(--tw-text-opacity, 1));
        box-shadow: 0 4px 16px rgba(253, 186, 116, 0.10);
    }
    .swap-btn {
        margin: 0 1.5rem;
        padding: 0.7rem 1rem;
        background: rgba(255,255,255,0.04);
        color: #e6f7ff;
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
        border-radius: 0.6rem;
    }
    .swap-btn:hover {
        background: rgba(255,255,255,0.06);
        color: #38bdf8;
    }
    .role-btn {
        padding: 0.9rem 1rem;
        font-size: 1.25rem;
        margin-right: 0.5rem;
        border-radius: 0.5rem;
    }
    .action-btn {
        padding: 0.6rem 0.9rem;
        font-size: 1rem;
        margin-right: 0.7rem;
        cursor: pointer;
        border-radius: 0.6rem; /* keep pill / rounded rectangle */
        transition: background 0.12s ease, color 0.12s ease, transform 0.12s ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        background: rgba(255,255,255,0.06);
    }

    /* Inner icon spans should not force circular backgrounds; keep subtle color change on hover */
    .action-btn .voice-icon,
    .action-btn .send-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.2rem;
        border-radius: 0.35rem;
        transition: background 0.12s ease, color 0.12s ease, transform 0.12s ease;
        background: transparent;
        font-size: 1.1rem;
    }

    .action-btn:hover {
        transform: translateY(-2px);
        background: rgba(253, 186, 116,0.08);
    }

    .action-btn:hover .voice-icon {
        color: rgb(253 186 116 / var(--tw-text-opacity, 1));
    }
    .action-btn:hover .send-icon {
        color: #22c55e;
    }

/* Removed duplicate .box-output and .box-textarea blocks for clean CSS. */

.frosted-glass-card {
        background: rgba(255,255,255,0.07);
        backdrop-filter: blur(18px) brightness(1.1);
        -webkit-backdrop-filter: blur(18px) brightness(1.1);
        border: 1.5px solid rgba(255,255,255,0.18);
        box-shadow: 0 12px 48px 0 rgba(0,0,0,0.32);
        transition: box-shadow 0.2s;
        max-width: 700px;
}
@media (max-width: 640px) {
    .frosted-glass-card { max-width: 100%; }
    .box-output { padding: 1rem 1.25rem; }
    .lang-btn { font-size: 0.9rem; }
    .icon-btn.role-btn span.material-symbols-outlined { font-size: 1.5rem; }
    .action-btn { padding: 0.5rem 0.65rem; }
}
@media (max-width: 420px) {
    .box-output { max-height: 300px; }
    .lang-select-btn { font-size: 0.8rem; }
}
</style>

<style>
html, body, #app {
    -ms-overflow-style: none; /* IE and Edge */
    scrollbar-width: none; /* Firefox */
}
html::-webkit-scrollbar, body::-webkit-scrollbar, #app::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Opera */
}
</style>
