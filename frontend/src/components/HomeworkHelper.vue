<template>
    <div id="HomeworkHelper" class="font-sans flex justify-center items-center w-full" style="margin-top: 20px;">
        <div
            class="flex flex-col md:flex-row mx-auto mt-1 w-full max-w-7xl h-[calc(100vh-140px)] md:h-[calc(100vh-150px)] min-h-[500px] md:min-h-[600px] glass-bg border border-white/30 shadow-2xl rounded-3xl">
            <!-- Sidebar for chat history -->
            <transition name="slide-fade">
                <div v-if="true"
                    :class="['hidden md:flex md:w-80 flex-col p-4 glass-transparent-bg rounded-l-3xl border-r', darkMode ? 'border-white/20' : 'border-orange-200/20']">
                    <div class="flex items-center justify-between mb-4">
                        <h2
                            :class="['text-lg font-bold flex items-center gap-2', darkMode ? 'text-white' : 'text-orange-400']">
                            <span
                                :class="['material-symbols-outlined text-2xl align-middle mr-2', darkMode ? 'text-white' : 'text-orange-400']">school</span>
                            Homework Helper
                        </h2>
                        <button @click="startNewChat"
                            class="px-3 py-1 text-sm transition flex items-center gap-1 rounded-md bg-orange-400/80 text-white hover:bg-orange-400'">
                            <span class="material-symbols-outlined text-white">add_comment</span>
                            <span>New Chat</span>
                        </button>
                    </div>
                    <div class="flex-1 overflow-y-auto pt-5 hide-scrollbar">
                        <button v-for="chatId in chats" :key="chatId" @click="loadChatMessages(chatId)"
                            :class="[selectedChatId === chatId ? (darkMode ? 'bg-orange-100/20 text-orange-300 shadow-md' : 'bg-orange-100/50 text-orange-600 shadow-md') : (darkMode ? 'bg-white/10 text-white/50 hover:bg-orange-50/10 hover:text-orange-300' : 'bg-white/10 text-gray-600 hover:bg-orange-50 hover:text-orange-600'), 'w-full text-left px-4 py-2 rounded-lg transition-all duration-200 hover:scale-[1.02] mb-2 flex items-center justify-between gap-2']"
                            style="margin-bottom: 10px;">
                            <span class="flex items-center gap-1 min-w-0">
                                <span
                                    :class="['material-symbols-outlined text-base', selectedChatId === chatId ? (darkMode ? 'text-orange-300' : 'text-orange-600') : (darkMode ? 'text-orange-400' : 'text-orange-500')]">chat</span>
                                <span class="truncate font-medium">{{ getChatDisplayName(chatId) }}</span>
                            </span>
                            <span class="shrink-0 flex items-center gap-1 opacity-80 hover:opacity-100">
                                <span role="button" tabindex="0" class="p-1 rounded hover:bg-red-50" title="Delete chat"
                                    @click.stop="confirmDeleteChat(chatId)" @keydown.enter.stop="confirmDeleteChat(chatId)">
                                    <span class="material-symbols-outlined text-red-600 text-base">delete</span>
                                </span>
                            </span>
                        </button>
                        <!-- Back to Home Button (bottom left) -->
                        <button @click="goHome"
                            class="fixed left-8 bottom-8 z-50 bg-white/80 hover:bg-orange-100 text-orange-700 font-semibold px-4 py-2 rounded-full shadow-lg flex items-center gap-2 transition-all">
                            <FontAwesomeIcon :icon="['fas', 'arrow-left']" class="text-lg" />
                            <span>Back to Home</span>
                        </button>
                    </div>
                </div>
            </transition>

            <!-- Mobile Sidebar Drawer -->
            <transition name="fade">
                <div v-if="isMobileSidebarOpen" class="md:hidden fixed inset-0 z-40 flex">
                    <div class="flex-1 bg-black/30" @click="isMobileSidebarOpen=false"></div>
                    <div class="w-72 max-w-[85vw] h-full bg-white/90 backdrop-blur-md border-l border-orange-200/30 shadow-2xl p-4 flex flex-col">
                        <div class="flex items-center justify-between mb-4">
                            <h2 class="text-base font-bold text-gray-800 flex items-center gap-2">
                                <span class="material-symbols-outlined text-orange-400">lists</span>
                                Chats
                            </h2>
                            <button @click="startNewChat" class="px-3 py-1 bg-orange-400/80 text-white rounded text-xs hover:bg-orange-400 transition flex items-center gap-1">
                                <span class="material-symbols-outlined text-white">add_comment</span>
                                <span>New</span>
                            </button>
                        </div>
                        <div class="flex-1 overflow-y-auto pt-2 hide-scrollbar min-h-0">
                            <div v-for="chatId in chats" :key="chatId + '-m'" class="mb-2">
                                <button @click="loadChatMessages(chatId); isMobileSidebarOpen=false;" :class="[selectedChatId===chatId ? 'bg-orange-100/60 text-orange-700 shadow' : 'bg-gray-100 text-gray-700 hover:bg-gray-200', 'w-full text-left px-3 py-2 rounded-lg transition flex items-center justify-between gap-2']">
                                    <span class="flex items-center gap-1 min-w-0">
                                        <span class="material-symbols-outlined text-orange-400 text-base">chat</span>
                                        <span class="truncate font-medium">{{ getChatDisplayName(chatId) }}</span>
                                    </span>
                                    <span role="button" tabindex="0" class="p-1 rounded hover:bg-red-50" @click.stop="confirmDeleteChat(chatId)" @keydown.enter.stop="confirmDeleteChat(chatId)">
                                        <span class="material-symbols-outlined text-red-600 text-base">delete</span>
                                    </span>
                                </button>
                            </div>
                        </div>
                        <div class="pt-2">
                            <button @click="goHome" class="w-full bg-white/90 hover:bg-orange-100 text-orange-700 font-semibold px-4 py-2 rounded-full shadow flex items-center justify-center gap-2">
                                <FontAwesomeIcon :icon="['fas','arrow-left']" class="text-lg" />
                                <span>Home</span>
                            </button>
                        </div>
                    </div>
                </div>
            </transition>

            <!-- Main Chat Area -->
            <transition name="fade">
                <div v-if="true" class="flex-1 flex flex-col glass-transparent-bg rounded-3xl md:rounded-r-3xl md:rounded-l-none">
                    <!-- Chat Header -->
                    <div
                        class="h-14 flex items-center justify-between px-4 md:px-6 border-b border-white/20 bg-white/10 shadow-sm rounded-t-3xl md:rounded-tr-3xl md:rounded-tl-none">
                        <div class="flex items-center space-x-3 min-w-0">
                            <button class="block md:hidden p-2 rounded-full text-orange-500" @click="isMobileSidebarOpen=true">
                                <span class="material-symbols-outlined">menu</span>
                            </button>
                            <button v-if="selectedChatId" @click="backToChatList"
                                :class="['p-1 rounded-full transition-colors', darkMode ? 'text-orange-400 hover:text-white' : 'text-orange-400 hover:text-black']">
                                <span class="material-symbols-outlined text-lg">arrow_back_ios_new</span>
                            </button>
                            <div class="w-8 h-8 bg-orange-400 rounded-full flex items-center justify-center shrink-0"
                                style="margin-right: 10px;">
                                <span class="material-symbols-outlined text-2xl align-middle"
                                    style="color:whitesmoke;">school</span>
                            </div>
                            <h2 v-if="!isEditingChatName" @click="isEditingChatName = true"
                                class="text-xl font-semibold text-orange-400 cursor-pointer hover:underline">{{
                                    selectedChatId ? getChatDisplayName(selectedChatId) : 'Start a Chat' }}</h2>
                            <input v-else v-model="newChatName" @keyup.enter="renameChat" @blur="renameChat" type="text"
                                class="text-xl font-semibold text-gray-800 bg-transparent border-b-2 border-orange-600 focus:outline-none" />
                        </div>
                    </div>

                    <!-- Chat Messages Container -->
                     <div ref="chatContainer" class="flex-1 overflow-y-auto px-3 md:px-6 py-3 md:py-4 space-y-3 md:space-y-4 pb-28 md:pb-4">
                        <transition-group name="list-fade" tag="div">
                            <div v-if="isLoadingHistory" class="flex items-center justify-center h-full text-gray-500">
                                <div class="loader-dots">
                                    <div></div>
                                    <div></div>
                                    <div></div>
                                    <div></div>
                                </div>
                            </div>
                            <div v-else-if="messages.length === 0"
                                class="flex items-center justify-center h-full text-gray-400">
                                <p>Start a new chat to begin...</p>
                            </div>
                            <div v-for="(msg, index) in messages" :key="index"
                                :class="{ 'flex items-start space-x-3': true, 'justify-end': msg.sender === 'user', 'justify-start': msg.sender === 'ai' }">
                                <!-- User Message -->
                                <div v-if="msg.sender === 'user'" class="flex flex-col items-end space-y-3">
                                    <!-- chat bubble -->
                                    <div class="flex flex-row-reverse items-start space-x-3 space-x-reverse pr-8">
                                        <div
                                            :class="['p-3 rounded-2xl rounded-br-none max-w-md shadow-lg', darkMode ? 'bg-orange-400 text-white' : 'bg-orange-400 text-white']">
                                            <div v-if="msg.doc_info && msg.doc_info.length > 0"
                                                class="flex flex-wrap gap-2 mb-2">
                                                <div v-for="doc in (typeof msg.doc_info === 'string' ? msg.doc_info.split(',').map(d => d.trim()).filter(d => d) : Array.isArray(msg.doc_info) ? msg.doc_info : [])"
                                                    :key="doc"
                                                    class="bg-white/20 rounded-full py-1 px-3 text-xs flex items-center space-x-1">
                                                    <span
                                                        class="material-symbols-outlined text-whitesmoke text-sm" style="margin-right: 3px;">description</span>
                                                    <span class="truncate font-medium">
                                                        {{ doc.length > 16 ? doc.slice(0, 13) + '...' : doc }}
                                                    </span>
                                                </div>
                                            </div>
                                            <p class="text-sm leading-relaxed">{{ stripDocumentContent(msg.text) }}</p>
                                            <div
                                                style="display:flex; align-items:center; gap:6px; margin-top:8px; color:rgba(255,255,255,0.7); justify-content:flex-end;">
                                                <div
                                                    style="display:flex; align-items:center; gap:6px; margin-right:6px;">
                                                    <FontAwesomeIcon :icon="['fas', 'clock']"
                                                        style="font-size:14px; color:whitesmoke;" />
                                                    <span style="font-size:12px; color:whitesmoke;">{{
                                                        formatTime(msg.timestamp) }}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- footer wrapper with account circle -->
                                    <div class="w-full h-8 flex items-end justify-end">
                                        <div
                                            :class="['w-8 h-8 rounded-full flex items-center justify-center shrink-0', darkMode ? 'bg-orange-400 text-white' : 'bg-orange-400 text-white']">
                                            <FontAwesomeIcon :icon="['fas', 'user-tie']" class="text-lg" />
                                        </div>
                                    </div>
                                </div>

                                <!-- AI Message -->
                                <div v-else class="flex flex-col space-y-3">
                                    <!-- chat bubble(s) -->
                                    <div class="flex items-start space-x-3 pl-8">
                                        <div
                                            class="bg-white/80 text-gray-800 p-3 rounded-2xl rounded-bl-none max-w-md shadow-lg">
                                            <p class="text-sm leading-relaxed" v-html="getHighlightedText(msg, index)">
                                            </p>
                                            <div
                                                style="display:flex; align-items:center; gap:10px; margin-top:8px; color:#6b7280;">
                                                <div
                                                    style="display:flex; align-items:center; gap:6px; margin-right:6px;">
                                                    <FontAwesomeIcon :icon="['fas', 'clock']"
                                                        style="font-size:18px; color:#9ca3af;" />
                                                    <span style="font-size:12px; color:#6b7280;">{{
                                                        formatTime(msg.timestamp) }}</span>
                                                </div>

                                                <IconButton title="Copy" @click="copyToClipboard(msg.text)"
                                                    style="padding:6px;">
                                                    <FontAwesomeIcon :icon="['fas', 'copy']"
                                                        style="font-size:15px; color:inherit;" />
                                                </IconButton>

                                                <IconButton :title="isSpeaking(index) ? 'Stop Audio' : 'Read Aloud'"
                                                    :class="isSpeaking(index) ? 'text-red-500' : ''"
                                                    @click="toggleAudio(msg, index)" style="padding:6px;">
                                                    <FontAwesomeIcon
                                                        :icon="isSpeaking(index) ? ['fas', 'stop'] : ['fas', 'volume-up']"
                                                        style="font-size:15px; color:inherit;" />
                                                </IconButton>

                                                <IconButton title="Regenerate" @click="regenerateResponse(index)"
                                                    style="padding:6px;">
                                                    <FontAwesomeIcon :icon="['fas', 'rotate-right']"
                                                        style="font-size:15px; color:inherit;" />
                                                </IconButton>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- footer wrapper (always at bottom, below other children) -->
                                    <div class="w-full h-8 flex items-end">
                                        <div
                                            :class="['w-8 h-8 rounded-full flex items-center justify-center shrink-0', darkMode ? 'bg-orange-400' : 'bg-orange-400']">
                                            <FontAwesomeIcon :icon="['fas', 'person-dots-from-line']"
                                                :class="['text-lg', darkMode ? 'text-white' : 'text-white']" />
                                        </div>
                                    </div>
                                </div>

                            </div>
                            <!-- Loader for thinking animation -->
                            <div v-if="isSending" class="flex justify-start items-center mt-2 pl-12">
                                <div
                                    class="bg-white/80 p-3 rounded-2xl rounded-bl-none shadow-lg flex items-center justify-center">
                                    <div class="loader-dots-orange">
                                        <div></div>
                                        <div></div>
                                        <div></div>
                                        <div></div>
                                    </div>
                                </div>
                            </div>
                        </transition-group>
                    </div>

                    <!-- Chat Input Bar -->
                    <div class="flex flex-col px-3 md:px-6 py-3 md:py-4 bg-white/10 border-t border-white/20 shadow-lg rounded-br-3xl sticky bottom-0 md:static z-30 md:z-auto backdrop-blur-sm">
                        <div v-if="attachedFiles.length > 0" class="flex flex-wrap gap-2 mb-2" style="margin-bottom: 15px;">
                            <div v-for="(file, index) in attachedFiles" :key="index"
                                class="flex items-center gap-3 bg-white/60 backdrop-blur-sm rounded-xl px-3 py-2 shadow-sm border border-orange-200/40 max-w-[260px] relative">
                                <div v-if="isImageFile(file)" class="w-10 h-10 rounded-lg overflow-hidden bg-gray-200 flex items-center justify-center shrink-0">
                                    <img :src="file.preview || file.tempUrl" alt="preview" class="object-cover w-full h-full" v-if="file.preview || file.tempUrl" />
                                    <span v-else class="material-symbols-outlined text-orange-400 text-base">image</span>
                                </div>
                                <div v-else class="w-10 h-10 rounded-lg bg-orange-100/60 flex items-center justify-center shrink-0">
                                    <span class="material-symbols-outlined text-orange-500 text-base">draft</span>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-semibold text-gray-700 truncate" :title="file.name">{{ file.name }}</div>
                                    <div v-if="file.ocr_text && isImageFile(file)" class="mt-0.5 text-[10px] text-gray-500 leading-snug line-clamp-2">{{ file.ocr_text.slice(0,90) }}<span v-if="file.ocr_text.length>90">…</span></div>
                                </div>
                                <button @click="removeAttachedFile(index)" class="ml-auto text-gray-500 hover:text-gray-700 transition-colors" title="Remove">
                                    <span class="material-symbols-outlined text-sm">cancel</span>
                                </button>
                            </div>
                        </div>

                        <div class="flex items-center w-full p-2 bg-white/50 rounded-full shadow-inner flex-wrap gap-1 sm:gap-2">
                            <!-- File attachment button -->
                            <label for="file-input" class="cursor-pointer" style="margin-right: 4px;">
                                <div
                                    class="w-8 h-8 flex items-center justify-center rounded-full bg-orange-100/40 text-orange-400 hover:bg-orange-200/60 transition-all duration-200">
                                    <span class="material-symbols-outlined text-lg">attach_file_add</span>
                                </div>
                                <input id="file-input" type="file" @change="attachFiles" class="hidden" multiple />
                            </label>
                            <!-- Voice input button -->
                            <button @click="startVoiceInput" :disabled="isSending"
                                class="mr-2 w-8 h-8 flex items-center justify-center rounded-full bg-orange-100/40 text-orange-400 hover:bg-orange-200/60 transition-all duration-200">
                                <span class="material-symbols-outlined text-lg">mic</span>
                            </button>

                            <!-- Input field -->
                            <div class="relative flex-1 min-w-0">
                                <div class="flex items-center gap-2 w-full">
                                    <!-- Selected tags inline next to the input -->
                                    <div v-if="selectedTags.length > 0" class="flex items-center gap-2 flex-wrap"
                                        style="margin-left: 5px;">
                                        <div v-for="(tag, idx) in selectedTags" :key="tag + '-' + idx"
                                            class="bg-orange-400 text-white rounded-full py-1 px-3 text-sm flex items-center space-x-2">
                                            <span>#{{ tag }}</span>
                                            <button @click="removeSelectedTag(idx)"
                                                class="ml-1 text-white/80 hover:text-white">
                                                <span class="material-symbols-outlined text-[14px]"
                                                    style="padding-top: 25%;">close</span>
                                            </button>
                                        </div>
                                    </div>
                                    <input v-model="userMessage" @input="onUserInputHW" @keyup.enter="sendMessage"
                                        :disabled="isSending" type="text" placeholder="Send a message..."
                                        class="flex-1 bg-transparent text-gray-800 placeholder-gray-500 focus:outline-none px-3" style="width: 100%;" />
                                </div>
                                <!-- Hashtag suggestion dropdown (ResearchAssistant style, adapted color) -->
                                <div v-if="showSuggestions"
                                    class="absolute left-0 bottom-12 w-80 glass-bg rounded-md shadow-lg z-50 max-h-56 overflow-auto suggestion-dropdown">
                                    <div class="p-2 text-xs" style="color:#f59e42">Suggestions</div>
                                    <div class="p-2">
                                        <div class="text-xs text-gray-600 px-1">Tags</div>
                                        <div class="mt-1">
                                            <button v-for="t in suggestions.tags" :key="'t-' + t"
                                                @click="applySuggestionHW(t)" :class="['w-full text-left px-2 py-1', (darkMode) ? 'text-white hover:text-orange-100' : 'text-black hover:text-orange-100']">#{{ t }}</button>
                                        </div>
                                    </div>
                                </div>
                                <div v-if="detectedTags.length > 0" class="mt-2 flex flex-wrap gap-2 z-50">
                                    <button v-for="t in detectedTags" :key="t" type="button"
                                        @click="applySuggestionHW(t)" :title="t"
                                        class="text-sm py-1 px-3 rounded-full focus:outline-none transition-all select-none flex items-center gap-2"
                                        :style="tagValidity[t] ? 'background:#60a5fa;color:#ffffff;box-shadow:0 1px 3px rgba(0,0,0,0.12);' : 'background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;'">
                                        #{{ t }}
                                    </button>
                                </div>
                            </div>

                            <!-- Send Button -->
                            <button @click="sendMessage"
                                :disabled="isSending || (!userMessage.trim() && attachedFiles.length === 0)"
                                :class="['w-9 h-9 flex items-center justify-center rounded-full shadow-lg transition-transform transform hover:scale-105 active:scale-95', isSending || (!userMessage.trim() && attachedFiles.length === 0) ? 'bg-orange-300' : 'bg-orange-400']">
                                <span
                                    :class="['material-symbols-outlined text-lg', darkMode ? 'text-white' : 'text-white']">send</span>
                            </button>
                        </div>
                    </div>
                </div>
            </transition>
            <!-- App-wide lightweight modal for this component -->
            <div v-if="modalOpen" class="fixed inset-0 z-[100] flex items-center justify-center">
                <div class="absolute inset-0 bg-black/2"></div>
                <div class="relative bg-white rounded-2xl shadow-2xl w-[90vw] max-w-md p-5 border border-orange-200/40">
                    <div class="flex items-start gap-3">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center" :class="{
                            'bg-orange-100 text-orange-700': modalKind === 'info',
                            'bg-red-100 text-red-700': modalKind === 'error',
                            'bg-amber-100 text-amber-700': modalKind === 'confirm',
                        }">
                            <span class="material-symbols-outlined">
                                {{ modalKind === 'error' ? 'error' : (modalKind === 'confirm' ? 'help' : 'info') }}
                            </span>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="text-lg font-semibold text-gray-900 mb-1">{{ modalTitle }}</div>
                            <div class="text-sm text-gray-700 whitespace-pre-line break-words">{{ modalMessage }}</div>
                        </div>
                        <button class="p-2 rounded-lg text-gray-500 hover:bg-gray-100" @click="handleModalCancel"
                            aria-label="Close modal">
                            <span class="material-symbols-outlined">close</span>
                        </button>
                    </div>
                    <div class="mt-4 flex justify-end gap-2">
                        <button v-if="modalKind === 'confirm'" @click="handleModalCancel"
                            :class="['px-4 py-2 rounded-lg border', darkMode ? 'bg-white/10 text-white border-white/10 hover:bg-white/20' : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-gray-200']">
                            {{ modalCancelText || 'Cancel' }}
                        </button>
                        <button @click="handleModalConfirm"
                            :class="modalKind === 'error' ? 'bg-red-600 hover:bg-red-700 text-white' : (darkMode ? 'bg-orange-600 hover:bg-orange-500 text-white' : 'bg-orange-600 hover:bg-orange-500 text-white')"
                            class="px-4 py-2 rounded-lg">
                            {{ modalConfirmText || 'OK' }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
// @ts-nocheck
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { toRef } from 'vue';
// accept darkMode as prop
const props = defineProps(['darkMode']);
const darkMode = toRef(props, 'darkMode');
// Mobile sidebar state
const isMobileSidebarOpen = ref(false);
import { renderLimitedMarkdown, cleanLLMText } from '@/utils/markdown';
// Format time as HH:MM in user's local time zone and locale (no seconds)
function formatTime(ts) {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
}
// --- TTS/Audio State ---
// let chunkQueue = []; // removed unused
let chunkIndex = 0;
let chunkUrls = [];
let chunkPaused = false;
// let chunkLang = '';
// let chunkSpeaker = '';
const sessionKeyPrefix = 'tts_chunk_';

function stopAudio() {
    // Stop browser TTS if active
    if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
    }
    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer = null;
    }
    chunkIndex = 0;
    chunkUrls = [];
    chunkPaused = false;
    speakingIndex.value = -1;
    speakingWord.value = -1;
}

function isSpeaking(idx) {
    return speakingIndex.value === idx;
}

function toggleAudio(msg, idx) {
    if (isSpeaking(idx)) {
        stopAudio();
    } else {
        readAloud(msg, idx);
    }
}
function stripDocumentContent(text) {
    // Remove everything after [Document Content]: for display
    const idx = text.indexOf('[Document Content]:');
    if (idx !== -1) {
        return text.slice(0, idx).trim();
    }
    return text;
}

const speakingIndex = ref(-1);
const speakingWord = ref(-1);
let audioPlayer = null;

// --- Advanced TTS: chunked, sessionStorage, browser TTS for English, speaker selection ---
async function readAloud(msg, msgIndex) {
    if (!msg.text) return;
    stopAudio();
    speakingIndex.value = msgIndex;
    speakingWord.value = -1;

    // Always clean text for TTS on every click (never cache or mutate)
    function cleanForTTS(text) {
        let t = text.replace(/\*\*/g, '');
        t = t.replace(/\*/g, '');
        t = t.replace(/"/g, '');
        t = t.replace(/\[Document Content\]:[\s\S]*/g, '');
        // Remove numbers for non-English only
        // Detect language first
        let langGuess = msg.lang || detectLanguage(text);
        if (!langGuess.startsWith('en')) {
            t = t.replace(/\d+/g, '');
        }
        return t.trim();
    }

    // Detect language (simple heuristic, or use msg.lang if available)
    let lang = msg.lang || detectLanguage(msg.text);
    let speaker = getDefaultSpeaker(lang);
    // Always use freshly cleaned text for TTS, never cache or mutate
    let ttsText = cleanForTTS(msg.text);

    // Use browser TTS for English
    if (lang.startsWith('en')) {
        playWithBrowserTTS(ttsText, lang, msgIndex);
        return;
    }

    // Use a hash of the cleaned text, lang, and speaker as the sessionStorage key
    function hashTTSKey(text, lang, speaker) {
        // Simple hash: base64 of utf-8 bytes of text+lang+speaker
        try {
            let str = text + '|' + lang + '|' + speaker;
            let utf8 = new TextEncoder().encode(str);
            let hash = 0;
            for (let i = 0; i < utf8.length; i++) {
                hash = ((hash << 5) - hash) + utf8[i];
                hash |= 0;
            }
            return sessionKeyPrefix + btoa(hash.toString());
        } catch {
            // fallback: use raw string
            return sessionKeyPrefix + btoa((text + '|' + lang + '|' + speaker).slice(0, 32));
        }
    }

    let sessionKey = hashTTSKey(ttsText, lang, speaker);
    let cached = sessionStorage.getItem(sessionKey);
    if (cached) {
        chunkUrls = JSON.parse(cached);
        playChunksFromUrls(chunkUrls, ttsText);
        return;
    }

    // Use chunked TTS backend for other languages
    chunkIndex = 0;
    chunkUrls = [];
    chunkPaused = false;

    // Progressive chunk fetching
    async function fetchAllChunks() {
        let urls = [];
        let chunkIdx = 0;
        let done = false;
        while (!done) {
            try {
                const res = await fetch(`${API_BASE}/api/voice_chunk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: ttsText, lang, speaker, chunk: chunkIdx })
                });
                if (!res.ok) throw new Error('TTS chunk request failed');
                const data = await res.json();
                if (data.chunks && Array.isArray(data.chunks) && data.chunks.length > 0) {
                    urls.push(...data.chunks);
                }
                done = data.done;
                chunkIdx++;
            } catch (err) {
                console.error('TTS chunked playback error:', err);
                break;
            }
        }
        return urls;
    }

    try {
        chunkUrls = await fetchAllChunks();
        if (!chunkUrls || chunkUrls.length === 0) throw new Error('No chunks returned');
        // Save to sessionStorage with the hash key
        sessionStorage.setItem(sessionKey, JSON.stringify(chunkUrls));
        playChunksFromUrls(chunkUrls, ttsText);
    } catch (err) {
        speakingIndex.value = -1;
        speakingWord.value = -1;
        console.error('TTS chunked playback error:', err);
    }
}

function playChunksFromUrls(urls, text = '') {
    if (!urls || urls.length === 0) {
        speakingIndex.value = -1;
        return;
    }
    chunkIndex = 0;
    // Split text into words for highlighting
    let words = text ? text.split(/\s+/) : [];
    function playNext() {
        if (chunkPaused || chunkIndex >= urls.length) {
            speakingIndex.value = -1;
            speakingWord.value = -1;
            return;
        }
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer = null;
        }
    audioPlayer = new Audio(`${API_BASE}${urls[chunkIndex]}`);
        // Estimate word range for this chunk
        let wordsPerChunk = words.length > 0 ? Math.ceil(words.length / urls.length) : 0;
        let startWord = chunkIndex * wordsPerChunk;
        speakingWord.value = startWord;
        audioPlayer.onplay = () => {
            // Highlight the first word of this chunk
            speakingWord.value = startWord;
        };
        audioPlayer.onended = () => {
            chunkIndex++;
            // Move highlight to next chunk's first word
            if (chunkIndex < urls.length) {
                speakingWord.value = chunkIndex * wordsPerChunk;
            } else {
                speakingWord.value = -1;
            }
            playNext();
        };
        audioPlayer.onerror = () => {
            chunkIndex++;
            playNext();
        };
        audioPlayer.play();
    }
    playNext();
}

// function pauseAudio() {
//     chunkPaused = true;
//     if (audioPlayer) audioPlayer.pause();
// }

// function resumeAudio() {
//     if (!chunkPaused) return;
//     chunkPaused = false;
//     if (audioPlayer) audioPlayer.play();
//     else if (chunkUrls.length > 0 && chunkIndex < chunkUrls.length) {
//         playChunksFromUrls(chunkUrls, speakingIndex.value);
//     }
// }

function playWithBrowserTTS(text, lang, msgIndex) {
    if (!window.speechSynthesis) {
        showAlertModal('Browser TTS not supported.');
        speakingIndex.value = -1;
        return;
    }
    stopAudio();
    speakingIndex.value = msgIndex;
    let utter = new window.SpeechSynthesisUtterance(text);
    utter.lang = lang;
    utter.onboundary = function (event) {
        if (event.name === 'word' && event.charIndex !== undefined) {
            // Find which word is being spoken
            let upto = text.slice(0, event.charIndex);
            let wordIdx = upto.split(/\s+/).length - 1;
            speakingWord.value = wordIdx;
        }
    };
    utter.onend = () => {
        speakingIndex.value = -1;
        speakingWord.value = -1;
    };
    window.speechSynthesis.speak(utter);
}

function isAscii(text) {
    for (let i = 0; i < text.length; i++) {
        if (text.charCodeAt(i) > 0x7f) return false;
    }
    return true;
}

function detectLanguage(text) {
    // Simple heuristic: check for non-ASCII for non-English
    if (isAscii(text)) return 'en';
    // Could use a better detector or backend-provided lang
    return 'auto';
}

function getDefaultSpeaker(lang) {
    // Map language to default speaker (customize as needed)
    const speakers = {
        en: 'en_speaker'
        // ... add more
    };
    return speakers[lang] || 'default';
}

// --- Word Highlighting: highlight word by word if speaking ---
function getHighlightedText(msg, msgIndex) {
    if (speakingIndex.value !== msgIndex) return formatBold(msg.text);
    // Only highlight word-by-word for English
    let lang = msg.lang || detectLanguage(msg.text);
    if (!lang.startsWith('en')) {
        return formatBold(msg.text);
    }
    // Highlighting: split by words, preserve spaces but do not count them as words
    const displayText = msg.text;
    // Split into words and spaces, but only count non-space tokens for highlighting
    let tokens = displayText.match(/\S+|\s+/g) || [];
    let html = '';
    let wordIdx = 0;
    for (let i = 0; i < tokens.length; i++) {
        if (/^\s+$/.test(tokens[i])) {
            // It's a space, just append
            html += tokens[i];
        } else {
            // It's a word
            if (speakingWord.value === wordIdx) {
                html += `<span style="background: #6366f1; color: white; border-radius: 4px; padding: 0 2px;">${tokens[i]}</span>`;
            } else {
                html += tokens[i];
            }
            wordIdx++;
        }
    }
    return html;
}

async function regenerateResponse(aiMsgIndex) {
    // Find the last user message before this AI message
    let userMsg = null;
    for (let i = aiMsgIndex - 1; i >= 0; i--) {
        if (messages.value[i] && messages.value[i].sender === 'user') {
            userMsg = messages.value[i];
            break;
        }
    }
    if (!userMsg) return;
    const regenKey = `${selectedChatId.value}::${userMsg.timestamp || ''}::${String(userMsg.text || '').slice(0, 120)}`;
    if (pendingRegens.has(regenKey)) return;
    pendingRegens.add(regenKey);
    isSending.value = true;
    try {
        const prevAiRowId = (messages.value[aiMsgIndex] && messages.value[aiMsgIndex].row_id) ? messages.value[aiMsgIndex].row_id : null;
        // Remove the AI message to be regenerated locally (UI update)
        messages.value.splice(aiMsgIndex, 1);
        // Build mem_context: include inline #tags in the user message and any selected tag chips
        let mem_context = null;
        let allTags = [];
        try {
            const inlineTags = (userMsg && userMsg.text) ? Array.from(new Set(((userMsg.text || '').match(/#([a-zA-Z0-9_-]+)/g) || []).map(s => s.replace(/^#/, '')))) : [];
            const chipTags = (selectedTags.value && selectedTags.value.length > 0) ? selectedTags.value.slice() : [];
            allTags = Array.from(new Set([...inlineTags, ...chipTags]));
            if (allTags.length > 0) {
                mem_context = await resolveTagsToContext(allTags);
            }
        } catch (e) {
            console.warn('Failed to build mem_context for regeneration', e);
            mem_context = null;
            allTags = [];
        }
        let request_id = null;
        try {
            request_id = btoa(unescape(encodeURIComponent(regenKey)));
        } catch (err) {
            console.warn('request_id generation failed, falling back', err);
            request_id = String(Date.now()) + '-' + Math.random().toString(36).slice(2, 8);
        }

        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: selectedChatId.value,
                text: userMsg.text + (userMsg.file_content ? '\n\n[Document Content]:\n' + userMsg.file_content : ''),
                doc_info: userMsg.doc_info && userMsg.doc_info.length > 0 ? (Array.isArray(userMsg.doc_info) ? userMsg.doc_info.join(', ') : userMsg.doc_info) : undefined,
                service: SERVICE_NAME,
                mem_context: mem_context,
                replace_last: true,
                replace_id: prevAiRowId,
                request_id: request_id,
                mem_tags: (allTags && allTags.length) ? allTags : undefined
            })
        });
        if (!res.ok) throw new Error('Failed to get LLM response');
        await loadChatMessages(selectedChatId.value);
    } catch (err) {
        console.error('Error regenerating response', err);
    } finally {
        pendingRegens.delete(regenKey);
        isSending.value = false;
    }
}
const API_BASE = typeof window !== 'undefined' ? window.location.origin : '';
const API_URL = API_BASE + '/api/chat';
const FILE_URL = API_BASE + '/api/upload';
const CHATS_URL = API_BASE + '/api/chats';
const CHAT_HISTORY_URL = API_BASE + '/api/chat/';
const DELETE_CHAT_URL = API_BASE + '/api/chat/';
// Service name for scoping chats to this component
const SERVICE_NAME = 'homework_helper';

import { ref, onMounted, nextTick } from 'vue';
import IconButton from './IconButton.vue';

// Using shared markdown utilities for rendering and cleaning
const suggestions = ref({ folders: [], tags: [], files: [] });
const showSuggestions = ref(false);
const detectedTags = ref([]);
const tagValidity = ref({});
const selectedTags = ref([]);
function debounce(fn, ms) { let t = null; return function (...args) { if (t) clearTimeout(t); t = setTimeout(() => fn.apply(this, args), ms); } }
const fetchSuggestionsDebounced = debounce(async (prefix) => {
    if (prefix === null || prefix === undefined) { suggestions.value = { folders: [], tags: [], files: [] }; showSuggestions.value = false; return; }
    try {
    const res = await fetch(`${API_BASE}/api/memory/suggest?q=${encodeURIComponent(prefix)}&limit=20`);
        if (!res.ok) throw new Error('Suggest failed');
        const data = await res.json();
        let tagList = (data && data.tags) ? Array.from(data.tags) : [];
    try { const fres = await fetch(`${API_BASE}/api/memory/folders`); if (fres.ok) { const fd = await fres.json(); const foldersArr = fd.folders || []; for (const ff of foldersArr) { if (ff && ff.tag) { const t = String(ff.tag).trim(); if (t && !tagList.some(x => String(x).toLowerCase() === t.toLowerCase())) tagList.push(t); } } } } catch (err) { console.warn('Failed fetching folders for suggestions', err); }
        suggestions.value = { folders: [], tags: tagList, files: [] };
        showSuggestions.value = (suggestions.value.tags && suggestions.value.tags.length > 0);
    } catch (err) { console.warn('Failed to fetch suggestions', err); suggestions.value = { folders: [], tags: [], files: [] }; showSuggestions.value = false; }
}, 200);
function onUserInputHW() { const v = userMessage.value || ''; const m = v.match(/#([\w\-\d_]*)$/); if (m) { fetchSuggestionsDebounced(m[1]); } else { suggestions.value = { folders: [], tags: [], files: [] }; showSuggestions.value = false; } detectAndValidateAllTagsHW(); }
function applySuggestionHW(text) {
    const tag = String(text).replace(/^#/, '');
    if (!selectedTags.value.includes(tag)) selectedTags.value.push(tag);
    // remove trailing partial tag from input
    userMessage.value = (userMessage.value || '').replace(/#([\w\-\d_]*)$/, '').trim();
    showSuggestions.value = false;
}

function removeSelectedTag(idx) {
    selectedTags.value.splice(idx, 1);
}
const validateTagsDebounced = debounce(async (tags) => { try { const newValidity = {}; await Promise.all(tags.map(async (t) => { if (!t) return; try { const res = await fetch(`${API_BASE}/api/memory/suggest?q=${encodeURIComponent(t)}&limit=5`); if (!res.ok) { newValidity[t] = false; return; } const data = await res.json(); const found = (data.tags && data.tags.some(x => x.toLowerCase() === t.toLowerCase())) || (data.folders && data.folders.some(x => x.toLowerCase() === t.toLowerCase())) || (data.files && data.files.some(x => x.toLowerCase() === t.toLowerCase())); newValidity[t] = !!found; } catch { newValidity[t] = false; } })); tagValidity.value = newValidity; } catch { console.warn('validateTagsDebounced error'); } }, 250);
function detectAndValidateAllTagsHW() { const v = userMessage.value || ''; const all = Array.from(new Set((v.match(/#([\w\-\d_]+)/g) || []).map(s => s.replace(/^#/, '')))); detectedTags.value = all; if (all.length > 0) validateTagsDebounced(all); else tagValidity.value = {}; }
async function resolveTagsToContext(tags) { if (!tags || tags.length === 0) return null; let foldersList = []; try { const res = await fetch(`${API_BASE}/api/memory/folders`); if (res.ok) { const d = await res.json(); foldersList = d.folders || []; } } catch (e) { console.warn('Failed to fetch folders for tag resolution', e); } const folderByTagOrName = new Map(); for (const f of foldersList) { if (f.tag) folderByTagOrName.set(String(f.tag).toLowerCase(), f); if (f.name) folderByTagOrName.set(String(f.name).toLowerCase(), f); } const contexts = []; for (const t of tags) { const key = String(t).toLowerCase(); if (folderByTagOrName.has(key)) { const folder = folderByTagOrName.get(key); try { const r = await fetch(`${API_BASE}/api/memory/folders/${folder.id}/items`); if (r.ok) { const jd = await r.json(); const previews = (jd.items || []).map(i => (i.preview || i.title || i.filename || '')).filter(Boolean); if (previews.length) contexts.push(`Folder: ${folder.name}\n` + previews.slice(0, 5).join('\n---\n')); } } catch (e) { console.warn('Failed to fetch folder items for tag', t, e); } } else { try { const r2 = await fetch(`${API_BASE}/api/memory/tag/${encodeURIComponent(t)}/context`); if (r2.ok) { const jd2 = await r2.json(); const previews = (jd2.items || []).map(i => (i.preview || i.filename || '')).filter(Boolean); if (previews.length) contexts.push(`Tag: #${t}\n` + previews.slice(0, 5).join('\n---\n')); } } catch (e) { console.warn('Failed to fetch tag context for', t, e); } } } if (contexts.length === 0) return null; const joined = contexts.join('\n====\n').slice(0, 3000); return joined; }

let recognition = null;
const isListening = ref(false);
const chats = ref([]);
const selectedChatId = ref('');
const messages = ref([]);
const userMessage = ref('');
const isSending = ref(false);
const chatContainer = ref(null);
const attachedFiles = ref([]);
const isLoadingHistory = ref(false);
// Guard set to prevent duplicate regenerate requests for the same user message
const pendingRegens = new Set();
const isEditingChatName = ref(false);
const newChatName = ref('');
const chatNames = ref({});

// Extended to include common image formats for OCR extraction
const acceptedFileTypes = ['.pdf', '.txt', '.doc', '.docx', '.md', '.csv', '.json', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'];

// Returns true if a file (or file-like object) is an image we support for inline preview / OCR
function isImageFile(file) {
    if (!file) return false;
    const name = (file.name || '').toLowerCase();
    return /\.(png|jpe?g|bmp|tiff?|webp)$/.test(name);
}

function revokeAttachmentObjectUrls() {
    try {
        (attachedFiles.value || []).forEach(f => { if (f && f.tempUrl) { try { URL.revokeObjectURL(f.tempUrl); } catch {/* ignore */} } });
    } catch {/* ignore */}
}

function generateChatId() {
    return 'chat_' + Date.now();
}

function getChatDisplayName(chatId) {
    return chatNames.value[chatId] || `Chat ${chatId.substring(5, 15)}...`;
}

function formatBold(text) {
    // Only format bold for display, never mutate the original message text
    const html = renderLimitedMarkdown(text);
    return html.replace(/#([\w\-\d_]+)/g, '<span style="background:#eef6fb;color:#0369a1;padding:2px 6px;border-radius:999px;">#$1</span>');
}


function goHome() {
    window.location.reload();
}

// Backend API for renaming chat: POST /api/rename_chat {chat_id, new_name}
async function renameChat() {
    if (newChatName.value.trim() && selectedChatId.value) {
        const trimmed = newChatName.value.trim();
        try {
            const res = await fetch(`${API_BASE}/api/rename_chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: selectedChatId.value, new_name: trimmed })
            });
            if (!res.ok) throw new Error('Failed to rename chat');
            // Update local name
            chatNames.value[selectedChatId.value] = trimmed;
        } catch (err) {
            console.error('Rename chat error', err);
        }
        isEditingChatName.value = false;
        newChatName.value = '';
    } else {
        isEditingChatName.value = false;
    }
}

function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window)) {
        showAlertModal('Voice input is not supported in this browser.');
        return;
    }
    if (isListening.value) return;
    isListening.value = true;
    // @ts-ignore
    recognition = new window.webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userMessage.value = transcript;
        isListening.value = false;
        // Do NOT send automatically; user can edit and send manually
    };
    recognition.onerror = () => {
        isListening.value = false;
    };
    recognition.onend = () => {
        isListening.value = false;
    };
    recognition.start();
}
async function loadChats() {
    try {
        const res = await fetch(CHATS_URL + '?service=' + encodeURIComponent(SERVICE_NAME));
        if (!res.ok) throw new Error('Failed to fetch chats');
        const chatListObj = await res.json();
        const chatList = chatListObj.chats || [];
        chats.value = chatList.map(c => c.chat_id || c);
        chatList.forEach(item => {
            const cid = item.chat_id || item;
            const cname = item.chat_name || item.chatName || null;
            if (cname) chatNames.value[cid] = cname;
            else if (!chatNames.value[cid]) chatNames.value[cid] = `Chat ${String(cid).substring(5, 15)}...`;
        });
    } catch (err) {
        console.error("Error loading chats", err);
    }
}

async function loadChatMessages(chatId) {
    isLoadingHistory.value = true;
    messages.value = [];
    selectedChatId.value = chatId;
    newChatName.value = chatNames.value[chatId] || '';
    try {
        const res = await fetch(CHAT_HISTORY_URL + chatId + '?service=' + encodeURIComponent(SERVICE_NAME));
        if (!res.ok) throw new Error('Failed to fetch chat messages');
        const chatMsgsObj = await res.json();
        const chatMsgs = chatMsgsObj.messages || [];
        messages.value = chatMsgs.map(msg => ({ ...msg, text: cleanLLMText(msg.text || '') }));
        nextTick(scrollToBottom);
    } catch (err) {
        console.error("Error loading chat messages", err);
    } finally {
        isLoadingHistory.value = false;
    }
}

async function confirmDeleteChat(chatId) {
    const ok = await showConfirmModal('Delete this chat and all its messages? This cannot be undone.', 'Delete Chat', 'Delete', 'Cancel');
    if (ok) await deleteChat(chatId);
}

async function deleteChat(chatId) {
    try {
        const res = await fetch(`${DELETE_CHAT_URL}${encodeURIComponent(chatId)}?service=${encodeURIComponent(SERVICE_NAME)}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete chat');
        chats.value = chats.value.filter(c => c !== chatId);
        if (selectedChatId.value === chatId) {
            selectedChatId.value = '';
            messages.value = [];
        }
        await loadChats();
    } catch (err) {
        console.error('Delete chat failed', err);
    }
}

// Helper to get next "New Chat N" name
function getNextNewChatName() {
    // Find all chat names that match "New Chat N"
    const usedNumbers = Object.values(chatNames.value)
        .map(name => {
            if (typeof name !== 'string') return null;
            const m = /^New Chat (\d+)$/.exec(name);
            return m ? parseInt(m[1], 10) : null;
        })
        .filter(n => n !== null);
    let n = 1;
    while (usedNumbers.includes(n)) n++;
    return `New Chat ${n}`;
}

async function startNewChat() {
    const newId = generateChatId();
    selectedChatId.value = newId;
    messages.value = [];
    chats.value.unshift(newId);
    const newName = getNextNewChatName();
    chatNames.value[newId] = newName;
    newChatName.value = newName;
    isEditingChatName.value = false;
}

async function sendMessage() {
    if (!userMessage.value.trim() && attachedFiles.value.length === 0 || isSending.value || !selectedChatId.value) return;

    isSending.value = true;
    const messageText = userMessage.value;
    userMessage.value = '';
    const fileNames = attachedFiles.value.map(file => file.name);

    // Only sending the first file as per backend limitation
    const fileToSend = attachedFiles.value.length > 0 ? attachedFiles.value[0] : null;

    let fileContent = '';
    if (fileToSend) {
        const ext = fileToSend.name.split('.').pop().toLowerCase();
        if (["txt", "json", "csv", "py", "md"].includes(ext)) {
            fileContent = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target && e.target.result ? e.target.result.toString() : '');
                reader.onerror = () => reject('File read error');
                reader.readAsText(fileToSend);
            });
        } else if (["png","jpg","jpeg","bmp","tif","tiff"].includes(ext)) {
            // Let the /api/upload endpoint perform OCR; we'll call it early to capture ocr_text
            try {
                const upForm = new FormData();
                upForm.append('file', fileToSend);
                upForm.append('chat_id', selectedChatId.value);
                const earlyRes = await fetch(FILE_URL, { method: 'POST', body: upForm });
                if (earlyRes.ok) {
                    const upData = await earlyRes.json();
                    if (upData.ocr_text) fileContent = upData.ocr_text;
                }
            } catch (e) { console.warn('Early image OCR upload failed', e); }
            // Fallback: if no OCR text captured, invoke generic extract_text
            if (!fileContent) {
                const fd = new FormData(); fd.append('file', fileToSend); fd.append('chat_id', selectedChatId.value);
                try {
                    const exRes = await fetch(`${API_BASE}/api/extract_text`, { method: 'POST', body: fd });
                    if (exRes.ok) { const exData = await exRes.json(); fileContent = exData.text || ''; }
                } catch (e) { console.warn('Image extract fallback failed', e); }
            }
        } else {
            // Non-plain text document (pdf/docx/pptx/etc.) use extract_text endpoint
            const formData = new FormData();
            formData.append('file', fileToSend);
            formData.append('chat_id', selectedChatId.value);
            const extractRes = await fetch(`${API_BASE}/api/extract_text`, { method: 'POST', body: formData });
            if (extractRes.ok) {
                const extractData = await extractRes.json();
                fileContent = extractData.text || '';
            } else {
                fileContent = '[Could not extract text from document]';
            }
        }
    }

    const userMsg = {
        sender: 'user',
        text: messageText,
        timestamp: Date.now(),
        doc_info: fileNames,
        file: fileToSend ? fileToSend.name : null,
        file_content: fileContent
    };
    messages.value.push(userMsg);

    try {
        if (fileToSend) {
            // If we didn't already upload during OCR step (images), ensure it's present server-side
            // For images we may have uploaded early; backend is idempotent on overwriting same filename.
            try {
                const formData = new FormData();
                formData.append('file', fileToSend);
                formData.append('chat_id', selectedChatId.value);
                const fileRes = await fetch(FILE_URL, { method: 'POST', body: formData });
                if (!fileRes.ok) console.warn('Secondary upload returned non-OK');
            } catch (e) { console.warn('Upload error (secondary)', e); }
        }
        // Send message to backend, include file content in text
        let fullText = messageText;
        if (fileContent) {
            fullText += '\n\n[Document Content]:\n' + fileContent;
        }
        // Before sending, check for #tags in messageText and fetch mem context to include
        let mem_context = null;
        try {
            const inlineTags = (messageText.match(/#([a-zA-Z0-9_-]+)/g) || []).map(s => s.replace(/^#/, ''));
            const chipTags = (selectedTags.value && selectedTags.value.length > 0) ? selectedTags.value.slice() : [];
            const allTagsSet = new Set([...inlineTags, ...chipTags].filter(Boolean).map(t => String(t).trim()));
            const allTags = Array.from(allTagsSet);
            if (allTags.length > 0) {
                mem_context = await resolveTagsToContext(allTags);
            }
        } catch (e) {
            console.warn('Failed to resolve tags to memory context', e);
        }

        const res = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: selectedChatId.value,
                text: fullText,
                doc_info: fileNames.length > 0 ? fileNames.join(', ') : undefined,
                service: SERVICE_NAME,
                selected_tags: selectedTags.value && selectedTags.value.length > 0 ? selectedTags.value : undefined,
                mem_context: mem_context,
                // Provide tags so backend can include 'Relevant links from memory'
                mem_tags: (() => {
                    try {
                        const inline = (messageText.match(/#([a-zA-Z0-9_-]+)/g) || []).map(s => s.replace(/^#/, ''));
                        const chips = (selectedTags.value && selectedTags.value.length > 0) ? selectedTags.value.slice() : [];
                        const merged = Array.from(new Set([...(inline || []), ...(chips || [])]));
                        return merged.length ? merged : undefined;
                    } catch { return undefined; }
                })()
            })
        });
        if (!res.ok) throw new Error('Failed to get LLM response');
        const aiResponse = await res.json();
        messages.value.push({
            sender: 'ai',
            text: cleanLLMText((aiResponse.text || '')),
            timestamp: Date.now(),
        });
    revokeAttachmentObjectUrls();
    attachedFiles.value = [];
        selectedTags.value = [];
    } catch (err) {
        console.error("Error sending message", err);
    } finally {
        isSending.value = false;
        nextTick(scrollToBottom);
        await loadChats();
    }
}

function attachFiles(event) {
    const target = event.target;
    if (!target.files) return;
    const newFiles = Array.from(target.files || []);
    const validFiles = newFiles.filter((file) => {
        if (!(file instanceof File)) return false;
        if (!file.name) return false;
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        return acceptedFileTypes.includes(fileExtension);
    });
    const remaining = 3 - attachedFiles.value.length;
    if (remaining <= 0) return;
    const filesToAdd = validFiles.slice(0, remaining);
    filesToAdd.forEach((f) => {
        if (isImageFile(f)) {
            try { 
                f['tempUrl'] = URL.createObjectURL(f); 
            } catch {/* ignore */}
        }
    });
    attachedFiles.value.push(...filesToAdd);

    // Optional: quick debug log of first text file added
    const debugFile = filesToAdd.find((f) => /(\.txt|\.md|\.csv|\.json|\.py)$/i.test(f.name));
    if (debugFile) {
        try {
            const reader = new FileReader();
            reader.onload = e => console.log(`Preview of ${debugFile.name}:`, (e.target && e.target.result || '').toString().slice(0,120));
            reader.readAsText(debugFile);
        } catch {/* ignore */}
    }
    // Allow selecting same file again by resetting input
    try { target.value = ''; } catch {/* ignore */}
}

function removeAttachedFile(index) {
    attachedFiles.value.splice(index, 1);
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
    } catch {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
}

function scrollToBottom() {
    if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    }
}

function backToChatList() {
    selectedChatId.value = '';
    messages.value = [];
}

// Lightweight Modal state & API for this component
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
function showConfirmModal(message, title = 'Confirm', confirmText = 'Yes', cancelText = 'No') {
    modalTitle.value = title; modalMessage.value = message; modalKind.value = 'confirm';
    modalConfirmText.value = confirmText; modalCancelText.value = cancelText; modalOpen.value = true;
    return new Promise((resolve) => { modalResolver = (ok) => { modalOpen.value = false; const res = !!ok; modalResolver = null; resolve(res); }; });
}
function handleModalConfirm() { if (modalResolver) modalResolver(true); else modalOpen.value = false; }
function handleModalCancel() { if (modalResolver) modalResolver(false); else modalOpen.value = false; }

onMounted(async () => {
    await loadChats();
    startNewChat();
});
</script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

/* Hide scrollbar for sidebar chat list */
.hide-scrollbar {
    scrollbar-width: none;
    /* Firefox */
    -ms-overflow-style: none;
    /* IE 10+ */
}

.hide-scrollbar::-webkit-scrollbar {
    display: none;
}

/* Custom scrollbar for main chat area */
.flex-1.overflow-y-auto.px-6.py-4.space-y-4 {
    scrollbar-width: thin;
    scrollbar-color: #fb923c rgba(255, 255, 255, 0.08);
}

.flex-1.overflow-y-auto.px-6.py-4.space-y-4::-webkit-scrollbar {
    width: 8px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}

.flex-1.overflow-y-auto.px-6.py-4.space-y-4::-webkit-scrollbar-thumb {
    background: linear-gradient(120deg, #6366f1 60%, #8b5cf6 100%);
    border-radius: 8px;
    min-height: 40px;
    opacity: 0.7;
}

.flex-1.overflow-y-auto.px-6.py-4.space-y-4::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(120deg, #6366f1 80%, #8b5cf6 100%);
    opacity: 1;
}

body {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(120deg, #6366f1 0%, #8b5cf6 100%);
    min-height: 100vh;
}

#HomeworkHelper {
    overflow: hidden;
    border-radius: 32px;
}

.material-symbols-outlined {
    font-variation-settings:
        'FILL' 0,
        'wght' 400,
        'GRAD' 0,
        'opsz' 24
}

/* Glassmorphism background utility */
.glass-bg {
    background: rgba(255, 255, 255, 0.18);
    backdrop-filter: blur(18px) saturate(180%);
    -webkit-backdrop-filter: blur(18px) saturate(180%);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.18);
}

/* Chat Loader */
.loader-dots {
    display: inline-block;
    position: relative;
    width: 48px;
    height: 12px;
}

.loader-dots div {
    position: absolute;
    top: 0;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #cbd5e1;
    animation-timing-function: cubic-bezier(0, 1, 1, 0);
}

.loader-dots div:nth-child(1) {
    left: 0;
    animation: loader-dots1 0.6s infinite;
}

.loader-dots div:nth-child(2) {
    left: 0;
    animation: loader-dots2 0.6s infinite;
}

.loader-dots div:nth-child(3) {
    left: 20px;
    animation: loader-dots2 0.6s infinite;
}

.loader-dots div:nth-child(4) {
    left: 40px;
    animation: loader-dots3 0.6s infinite;
}

@keyframes loader-dots1 {
    0% {
        transform: scale(0);
    }

    100% {
        transform: scale(1);
    }
}

@keyframes loader-dots3 {
    0% {
        transform: scale(1);
    }

    100% {
        transform: scale(0);
    }
}

@keyframes loader-dots2 {
    0% {
        transform: translate(0, 0);
    }

    100% {
        transform: translate(20px, 0);
    }
}

/* AI Message Loader */
.loader-dots-orange {
    display: inline-block;
    position: relative;
    width: 48px;
    height: 12px;
}

.loader-dots-orange div {
    position: absolute;
    top: 0;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #6366f1;
    animation-timing-function: cubic-bezier(0, 1, 1, 0);
}

.loader-dots-orange div:nth-child(1) {
    left: 0;
    animation: loader-dots-orange1 0.6s infinite;
}

.loader-dots-orange div:nth-child(2) {
    left: 0;
    animation: loader-dots-orange2 0.6s infinite;
}

.loader-dots-orange div:nth-child(3) {
    left: 20px;
    animation: loader-dots-orange2 0.6s infinite;
}

.loader-dots-orange div:nth-child(4) {
    left: 40px;
    animation: loader-dots-orange3 0.6s infinite;
}

@keyframes loader-dots-orange1 {
    0% {
        transform: scale(0);
    }

    100% {
        transform: scale(1);
    }
}

@keyframes loader-dots-orange3 {
    0% {
        transform: scale(1);
    }

    100% {
        transform: scale(0);
    }
}

@keyframes loader-dots-orange2 {
    0% {
        transform: translate(0, 0);
    }

    100% {
        transform: translate(20px, 0);
    }
}

.slide-fade-enter-active,
.slide-fade-leave-active {
    transition: all 0.5s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
    transform: translateX(-20px);
    opacity: 0;
}

.fade-enter-active,
.fade-leave-active {
    transition: all 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.list-fade-enter-active,
.list-fade-leave-active {
    transition: all 0.5s ease-in-out;
}

.list-fade-enter-from,
.list-fade-leave-to {
    opacity: 0;
    transform: translateY(20px);
}
</style>
