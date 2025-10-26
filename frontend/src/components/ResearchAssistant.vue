<template>
    <div id="ResearchAssistant" class="font-sans flex justify-center items-center w-full" style="margin-top: 20px;">
        <div
            :class="['flex flex-col md:flex-row mx-auto mt-1 w-full max-w-7xl h-[calc(100vh-140px)] md:h-[calc(100vh-150px)] min-h-[420px] md:min-h-[600px] border border-white/30 shadow-2xl rounded-3xl', 'glass-bg']">
            <!-- Sidebar for chat history -->
            <transition name="slide-fade">
                <div v-if="true"
                    :class="['hidden md:flex md:w-80 flex-col p-4 glass-transparent-bg rounded-l-3xl', 'border-r', powerMode ? 'border-white/20' : 'border-orange-200/20']">
                    <div class="flex items-center justify-between mb-4">
                        <h2 :class="['font-bold flex items-center gap-2', (darkMode ? 'text-white' : 'text-orange-400')]"
                            style="font-size: medium;">
                            <FontAwesomeIcon :icon="['fas', 'person-dots-from-line']"
                                :class="[(darkMode ? 'text-white' : 'text-orange-400'), 'text-lg']" />
                            Research Assistant
                        </h2>
                        <button @click="startNewChat"
                            class="px-3 py-1 text-sm transition flex items-center gap-1 rounded-md bg-orange-400/80 text-white hover:bg-orange-400'">
                            <span class="material-symbols-outlined text-white">add_comment</span>
                            <span>New Chat</span>
                        </button>
                    </div>
                    <div class="flex-1 overflow-y-auto pt-5 hide-scrollbar">
                        <div v-for="chatId in chats" :key="chatId" class="mb-2">
                            <button @click="loadChatMessages(chatId)" :class="[
                                selectedChatId === chatId
                                    ? (powerMode ? 'bg-white/80 text-gray-900 shadow-md' : 'bg-orange-100/50 text-orange-400 shadow-md')
                                    : (powerMode ? 'bg-white/10 text-gray-300 hover:bg-white/20 hover:text-gray-900' : 'bg-white/10 text-white/50 hover:bg-orange-50 hover:text-orange-400'),
                                'w-full text-left px-4 py-2 rounded-lg transition-all duration-200 hover:scale-[1.02] flex items-center justify-between gap-2'
                            ]" style="margin-bottom: 4px;">
                                <span class="flex items-center gap-1 min-w-0">
                                    <span class="material-symbols-outlined text-base text-orange-400">chat</span>
                                    <span
                                        :class="['truncate font-medium', (!darkMode && !powerMode) ? 'text-orange-400' : '']">{{
                                        getChatDisplayName(chatId) }}</span>
                                </span>
                                <span class="shrink-0 flex items-center gap-1 opacity-80 hover:opacity-100">
                                    <span role="button" tabindex="0" class="p-1 rounded hover:bg-red-50" title="Delete chat"
                                        @click.stop="confirmDeleteChat(chatId)" @keydown.enter.stop="confirmDeleteChat(chatId)">
                                        <span class="material-symbols-outlined text-red-600 text-base">delete</span>
                                    </span>
                                </span>
                            </button>
                        </div>
                        <!-- Back to Home Button (bottom left) -->
                        <button @click="goHome"
                            class="hidden md:flex fixed left-8 bottom-8 z-50 bg-white/80 hover:bg-orange-100 text-orange-700 font-semibold px-4 py-2 rounded-full shadow-lg items-center gap-2 transition-all">
                            <FontAwesomeIcon :icon="['fas', 'arrow-left']" class="text-lg" />
                            <span>Back to Home</span>
                        </button>
                    </div>
                </div>
            </transition>

            <!-- Mobile Sidebar Drawer -->
            <transition name="fade">
                <div v-if="isMobileSidebarOpen" class="md:hidden fixed inset-0 z-50 flex">
                    <!-- Lightweight single dim layer (no blur) for smoother performance on mobile -->
                    <div class="flex-1 bg-black/30" @click="isMobileSidebarOpen = false"></div>
                    <div
                        class="w-72 max-w-[85vw] h-full bg-white border-l border-orange-200/20 shadow-2xl p-4 flex flex-col">
                        <div class="flex items-center justify-between mb-4">
                            <h2 class="text-base font-bold text-gray-800 flex items-center gap-2">
                                <span class="material-symbols-outlined text-orange-400">lists</span>
                                Chats
                            </h2>
                            <button @click="startNewChat"
                                class="px-3 py-1 bg-orange-400/80 text-white rounded text-xs hover:bg-orange-400 transition flex items-center gap-1">
                                <span class="material-symbols-outlined text-white">add_comment</span>
                                <span>New</span>
                            </button>
                        </div>
                        <div class="flex-1 overflow-y-auto pt-2 hide-scrollbar min-h-0"
                            style="-webkit-overflow-scrolling: touch;">
                            <div style="margin-top: 5px;" v-for="chatId in chats" :key="chatId + 'm'" class="mb-2">
                                <button @click="loadChatMessages(chatId); isMobileSidebarOpen = false;"
                                    :class="[selectedChatId === chatId ? 'bg-orange-100/50 text-orange-700 shadow-md' : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:text-orange-700', 'w-full text-left px-3 py-2 rounded-lg transition-all duration-200 flex items-center justify-between gap-2']">
                                    <span class="flex items-center gap-1 min-w-0">
                                        <span class="material-symbols-outlined text-orange-400 text-base">chat</span>
                                        <span class="truncate font-medium">{{ getChatDisplayName(chatId) }}</span>
                                    </span>
                                    <span class="shrink-0 flex items-center gap-1 opacity-80 hover:opacity-100">
                                        <span role="button" tabindex="0" class="p-1 rounded hover:bg-red-50" title="Delete chat"
                                            @click.stop="confirmDeleteChat(chatId)" @keydown.enter.stop="confirmDeleteChat(chatId)">
                                            <span class="material-symbols-outlined text-red-600 text-base">delete</span>
                                        </span>
                                    </span>
                                </button>
                            </div>
                        </div>
                        <!-- Mobile Back to Home (matches desktop functionality) -->
                        <div class="pt-2">
                            <button @click="goHome"
                                class="w-full bg-white/90 hover:bg-orange-100 text-orange-700 font-semibold px-4 py-2 rounded-full shadow-md flex items-center justify-center gap-2 transition-all">
                                <FontAwesomeIcon :icon="['fas', 'arrow-left']" class="text-lg" />
                                <span>Back to Home</span>
                            </button>
                        </div>
                    </div>
                </div>
            </transition>

            <!-- Main Chat / Editor / Preview Region -->
            <transition name="fade">
                <!-- Wrapper needed so transition has exactly one child -->
                <div v-if="true" class="flex flex-1">
                    <!-- Chat Column -->
                    <div class="flex flex-col glass-transparent-bg rounded-3xl md:rounded-r-3xl md:rounded-l-none overflow-hidden md:overflow-visible flex-1">
                    <!-- Chat Header -->
                    <div
                        class="h-14 flex items-center justify-between px-6 border-b border-white/20 bg-white/10 shadow-sm rounded-t-3xl md:rounded-tr-3xl md:rounded-tl-none">
                        <div class="flex items-center space-x-3 min-w-0">
                            <!-- Mobile menu button to open chats drawer -->
                            <button
                                :class="['block md:hidden p-2 rounded-full', (darkMode || powerMode) ? 'text-white hover:text-white' : 'text-orange-700 hover:text-white']"
                                @click="isMobileSidebarOpen = true">
                                <span class="material-symbols-outlined">menu</span>
                            </button>
                            <button v-if="selectedChatId" @click="backToChatList"
                                :class="['p-1 rounded-full transition-colors', darkMode ? 'text-orange-400 hover:text-white' : 'text-orange-400 hover:text-black']">
                                <span class="material-symbols-outlined text-lg">arrow_back_ios_new</span>
                            </button>
                            <div class="w-8 h-8 bg-orange-400 rounded-full flex items-center justify-center shrink-0">
                                <FontAwesomeIcon :icon="['fas', 'person-dots-from-line']"
                                    :class="[(darkMode || powerMode) ? 'text-white' : 'text-white', 'text-lg']" />
                            </div>
                            <h2 v-if="!isEditingChatName" @click="isEditingChatName = true"
                                class="text-xl font-semibold cursor-pointer hover:underline truncate text-orange-400"
                                style="margin-left: 10px;">{{
                                    selectedChatId ? getChatDisplayName(selectedChatId) : 'Start a Chat' }}</h2>
                            <input v-else v-model="newChatName" @keyup.enter="renameChat" @blur="renameChat" type="text"
                                class="text-xl font-semibold text-gray-800 bg-transparent border-b-2 border-orange-400 focus:outline-none" />
                        </div>
                        <!-- Power Mode Toggle -->
                        <div class="flex items-center gap-3 flex-shrink-0 ml-auto">
                            <span
                                :class="[(darkMode || powerMode) ? 'text-white' : 'text-gray-800', 'text-xs md:text-sm hidden sm:inline']">Power
                                Mode</span>
                            <label class="power-toggle cursor-pointer">
                                <input type="checkbox" class="power-toggle__input" v-model="powerMode"
                                    @change="persistPowerMode" />
                                <span class="power-toggle__track">
                                    <span class="power-toggle__thumb"></span>
                                </span>
                            </label>
                        </div>
                    </div>

                    <!-- Chat Messages Container -->
                    <div ref="chatContainer"
                        class="flex-1 overflow-y-auto overflow-x-hidden px-3 md:px-6 py-3 md:py-4 space-y-3 md:space-y-4 chat-scroll">
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
                                :class="['flex items-center justify-center h-full', (darkMode || powerMode) ? 'text-white' : 'text-black']">
                                <p>Start a new chat to begin...</p>
                            </div>
                            <div v-for="(msg, index) in messages" :key="index"
                                :class="{ 'flex items-start space-x-3': true, 'justify-end': msg.sender === 'user', 'justify-start': msg.sender === 'ai' }">
                                <!-- User Message -->
                                <div v-if="msg.sender === 'user'" class="flex flex-col items-end space-y-3">
                                    <div
                                        class="flex flex-row-reverse items-start space-x-3 space-x-reverse pr-8 min-w-0">
                                        <div class="bg-orange-400 text-white p-3 rounded-2xl rounded-br-none max-w-[85vw] md:max-w-md lg:max-w-2xl shadow-lg chat-bubble break-words"
                                            style="margin-top: 10px;">
                                            <div v-if="msg.doc_info && msg.doc_info.length > 0"
                                                class="flex flex-wrap gap-2 mb-2">
                                                <div v-for="doc in (typeof msg.doc_info === 'string' ? msg.doc_info.split(',').map(d => d.trim()).filter(d => d) : Array.isArray(msg.doc_info) ? msg.doc_info : [])"
                                                    :key="doc"
                                                    class="bg-white/20 rounded-full py-1 px-3 text-xs flex items-center space-x-1">
                                                    <span
                                                        class="material-symbols-outlined text-orange-400 text-sm">description</span>
                                                    <span class="truncate font-medium">
                                                        {{ doc.length > 16 ? doc.slice(0, 13) + '...' : doc }}
                                                    </span>
                                                </div>
                                            </div>
                                            <p class="text-sm leading-relaxed whitespace-pre-wrap break-words">{{
                                                stripDocumentContent(msg.text) }}</p>
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
                                    <div class="w-full h-8 flex items-end justify-end">
                                        <div
                                            class="w-8 h-8 bg-orange-400 rounded-full flex items-center justify-center shrink-0 text-white">
                                            <FontAwesomeIcon :icon="['fas', 'user-tie']" class="text-lg" />
                                        </div>
                                    </div>
                                </div>
                                <!-- AI Message -->
                                <div v-else class="flex flex-col space-y-3">
                                    <div class="flex items-start space-x-3 pl-8 min-w-0" style="margin-top: 10px;">
                                        <div
                                            class="bg-white/80 text-gray-800 p-3 rounded-2xl rounded-bl-none max-w-[85vw] md:max-w-md lg:max-w-2xl shadow-lg chat-bubble break-words">
                                            <p class="text-sm leading-relaxed whitespace-pre-wrap break-words"
                                                v-html="getHighlightedText(msg, index)"></p>
                                            <div
                                                style="display:flex; align-items:center; gap:2px; margin-top:8px; color:#6b7280;">
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
                                            <div v-if="powerMode && msg.actions && msg.actions.length"
                                                class="mt-3 p-2 border border-orange-200 rounded bg-orange-50/80">
                                                <div class="text-xs text-orange-800 font-semibold mb-1">Proposed Actions
                                                </div>
                                                <ul class="text-xs text-gray-800 list-disc ml-5">
                                                    <li v-for="(a, ai) in msg.actions" :key="ai"><span
                                                            class="font-mono">{{ a.type }}</span></li>
                                                </ul>
                                                <button @click="executeActionsForMessage(index)"
                                                    :class="['mt-2 text-xs px-3 py-1 rounded bg-green-600 hover:bg-green-700', (darkMode || powerMode) ? 'text-white' : 'text-white']">Execute</button>
                                                <div v-if="msg.executeResult" class="mt-2 text-xs text-gray-600">Done:
                                                    {{ summarizeExecuteResult(msg.executeResult) }}</div>
                                            </div>
                                            <div v-if="msg.planPreviews && msg.planPreviews.length" class="mt-3 p-2 border border-orange-200 rounded bg-orange-100/60">
                                                <div class="text-xs text-orange-800 font-semibold mb-1">Agent Actions</div>
                                                <ul class="text-xs text-gray-800 list-disc ml-5 space-y-1">
                                                    <li v-for="(p, pi) in msg.planPreviews" :key="pi">{{ p.summary }}</li>
                                                </ul>
                                                <div v-if="msg.planExecResults && msg.planExecResults.length" class="mt-2 text-[11px] text-gray-600">
                                                    Executed {{ msg.planExecResults.length }} action(s).
                                                </div>
                                                <details class="mt-2" v-if="msg.planRaw">
                                                    <summary class="cursor-pointer text-[11px] text-orange-700 hover:underline">Raw Plan JSON</summary>
                                                    <pre class="mt-1 whitespace-pre-wrap text-[10px] bg-white/70 p-2 rounded max-h-48 overflow-auto">{{ msg.planRaw }}</pre>
                                                </details>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="w-full h-8 flex items-end">
                                        <div
                                            class="w-8 h-8 bg-orange-400 rounded-full flex items-center justify-center shrink-0">
                                            <FontAwesomeIcon :icon="['fas', 'person-dots-from-line']"
                                                class="text-white text-lg" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-if="isSending" class="flex justify-start items-center mt-2 pl-6 md:pl-12">
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
                    <div
                        class="flex flex-col px-3 md:px-6 py-3 md:py-4 bg-white/10 border-t border-white/20 shadow-lg rounded-br-3xl">
                        <!-- Power Mode Panel removed: actions now proposed/executed via chat UI -->
                        <!-- File chip display -->
                        <div v-if="attachedFiles.length > 0" class="flex flex-wrap gap-2 mb-2" style="margin-bottom: 15px;">
                            <div v-for="(file, index) in attachedFiles" :key="index"
                                class="bg-gray-200/80 rounded-full py-1 px-3 text-sm flex items-center space-x-2">
                                <span class="material-symbols-outlined text-orange-400 text-sm">draft</span>
                                <span class="truncate font-medium max-w-40 text-gray-500" style="margin-left: 5px;margin-right: 5px;">{{ file.name }}</span>
                                <button @click="removeAttachedFile(index)"
                                    class="text-gray-500 hover:text-gray-700 transition-colors">
                                    <span class="material-symbols-outlined text-sm pt-1">cancel</span>
                                </button>
                            </div>
                        </div>

                        <div v-if="inlineSelectionSummary"
                            class="mb-2 w-full rounded-xl border border-emerald-200 bg-emerald-50/80 px-3 py-2 text-emerald-700 shadow-inner">
                            <div class="flex flex-col gap-2">
                                <div class="flex items-center gap-2">
                                    <span class="material-symbols-outlined text-base text-emerald-500">select_check_box</span>
                                    <div class="text-xs font-semibold leading-tight">Inline selection ready
                                        ({{ inlineSelectionSummary.label || 'Target' }})</div>
                                    <div class="ml-auto text-[10px] uppercase tracking-wide text-emerald-600/80">
                                        {{ inlineSelectionSummary.length }} chars
                                    </div>
                                </div>
                                <div class="text-xs leading-snug whitespace-pre-wrap text-emerald-700/90">
                                    {{ inlineSelectionSummary.preview }}</div>
                                <div class="flex items-center gap-2 text-[11px]">
                                    <button @click="disableInlineSelection"
                                        class="flex items-center gap-1 rounded bg-red-500/90 px-2 py-1 text-white transition hover:bg-red-600">
                                        <span class="material-symbols-outlined text-sm">close</span>
                                        Remove Selection
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div v-else-if="inlineSelectionMessage"
                            class="mb-2 flex w-full items-center gap-2 rounded-xl border border-gray-200 bg-white/80 px-3 py-2 text-[12px] text-gray-600">
                            <span class="material-symbols-outlined text-base text-gray-500">info</span>
                            <span class="leading-snug">{{ inlineSelectionMessage }}</span>
                            <span v-if="inlineSelectionLoading" class="ml-auto text-[10px] uppercase tracking-wide text-gray-400">Working…</span>
                        </div>

                        <div class="flex items-center w-full p-2 bg-white/50 rounded-full shadow-inner">
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

                            <!-- Inline selection refresh button -->
                            <button @click="enableInlineSelection" :disabled="inlineSelectionLoading || isSending"
                                :title="inlineSelectionData ? 'Selection monitoring active' : 'Enable selection monitoring'"
                                :class="[
                                    'mr-2 w-8 h-8 flex items-center justify-center rounded-full transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-60',
                                    inlineSelectionData ? 'bg-emerald-500/90 text-white' : 'bg-emerald-100/60 text-emerald-600 hover:bg-emerald-200/70'
                                ]" style="margin-left: 5px;">
                                <span v-if="inlineSelectionLoading" class="material-symbols-outlined text-lg animate-spin">sync</span>
                                <span v-else class="material-symbols-outlined text-lg">edit_note</span>
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
                                    <input v-model="userMessage" @keyup.enter="sendMessage" @input="onUserInput"
                                        @focus="handleInputFocus"
                                        :disabled="isSending" type="text"
                                        placeholder="Send a message... (type # to see memory tags/folders)"
                                        class="flex-1 bg-transparent text-gray-800 placeholder-gray-500 focus:outline-none px-3"
                                        style="width: 100%;" />
                                </div>
                                <!-- Hashtag suggestion dropdown -->
                                <div v-if="showSuggestions"
                                    class="absolute left-0 bottom-12 w-80 glass-bg rounded-md shadow-lg z-50 max-h-56 overflow-auto suggestion-dropdown">
                                    <div class="p-2 text-xs text-orange-400">Suggestions</div>
                                    <div class="p-2">
                                        <div class="text-xs text-gray-600 px-1">Tags</div>
                                        <div class="mt-1">
                                            <button v-for="t in suggestions.tags" :key="'t-' + t"
                                                @click="applySuggestion(t)"
                                                :class="['w-full text-left px-2 py-1', (darkMode || powerMode) ? 'text-white hover:text-orange-100' : 'text-black hover:text-orange-100']">#{{
                                                    t }}</button>
                                        </div>
                                    </div>
                                </div>
                                <!-- Detected tags chips -->
                                <div v-if="detectedTags.length > 0" class="mt-2 flex flex-wrap gap-2 z-50">
                                    <button v-for="t in detectedTags" :key="t" type="button" @click="applySuggestion(t)"
                                        :title="t"
                                        class="text-sm py-1 px-3 rounded-full focus:outline-none transition-all select-none flex items-center gap-2"
                                        :style="tagValidity[t] ? 'background:#38bdf8;color:#ffffff;box-shadow:0 1px 3px rgba(0,0,0,0.12);' : 'background:#f3f4f6;color:#374151;border:1px solid #e5e7eb;'">
                                        #{{ t }}
                                    </button>
                                </div>
                            </div>

                            <!-- Send Button -->
                            <button @click="sendMessage"
                                :disabled="isSending || (!userMessage.trim() && attachedFiles.length === 0)"
                                class="w-9 h-9 flex items-center justify-center bg-orange-400 rounded-full shadow-lg transition-transform transform hover:scale-105 active:scale-95 disabled:bg-orange-400">
                                <span
                                    :class="['material-symbols-outlined text-lg', (darkMode || powerMode) ? 'text-white' : 'text-white']">send</span>
                            </button>
                        </div>
                    </div>
                    </div>
                </div>
            </transition>
        </div>
        <!-- App-wide lightweight modal -->
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
                        class="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200">
                        {{ modalCancelText || 'Cancel' }}
                    </button>
                    <button @click="handleModalConfirm"
                        :class="modalKind === 'error' ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-orange-400 hover:bg-orange-700 text-white'"
                        class="px-4 py-2 rounded-lg">
                        {{ modalConfirmText || 'OK' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { themeState } from '@/global/theme';
// Removed CodeEditorPanel & LiveHtmlPreview (agentic mode)
// vue imports come later in file
// No global loader for chats; rely on inline bubble
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
// ---------------- Power Mode State ----------------
const powerMode = ref(false)
try {
    const saved = localStorage.getItem('powerMode')
    if (saved) powerMode.value = saved === 'true'
} catch {
    /* ignore localStorage errors (private mode, etc.) */
}
// Removed split-pane editor state
// Agentic code intent state
const inferredCodeTarget = ref('');
const inferredObjective = ref('');
async function inferCodeTargetFromPrompt(promptText) {
    try {
        // Use existing CUA planner as lightweight path/objective inference if available
    const res = await fetch(API_BASE + '/api/cua/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: promptText, default_target_rel: 'agent_output/generated.txt' }) });
        if (!res.ok) return;
        const data = await res.json();
        if (data && data.target_rel) {
            inferredCodeTarget.value = data.target_rel;
            inferredObjective.value = data.objective || '';
            // Editor no longer opens; will attach plan result to chat instead
        }
    } catch (e) {
        console.debug('Inference failed', e);
    }
}
function persistPowerMode() {
    // Always update global backdrop regardless of storage errors
    themeState.setPower(!!powerMode.value);
    try { localStorage.setItem('powerMode', String(powerMode.value)); } catch { /* ignore */ }
    // Reload chat list when toggling between modes
    loadChats();
    // If a chat is currently selected, reset it and go back to the chat list
    if (selectedChatId.value) {
        selectedChatId.value = null;
        messages.value = [];
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

// Hashtag suggestion state
const suggestions = ref({ folders: [], tags: [], files: [] });
const showSuggestions = ref(false);
// no timer variable needed; debounce handles timing

function debounce(fn, ms) {
    let t = null;
    return function (...args) {
        if (t) clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), ms);
    }
}

const fetchSuggestionsDebounced = debounce(async (prefix) => {
    // prefix === '' (empty string) should still query the server to receive recent tags
    if (prefix === null || prefix === undefined) {
        suggestions.value = { folders: [], tags: [], files: [] };
        showSuggestions.value = false;
        return;
    }
    try {
    const res = await fetch(`${API_BASE}/api/memory/suggest?q=${encodeURIComponent(prefix)}&limit=20`);
        if (!res.ok) throw new Error('Suggest failed');
        const data = await res.json();
        // Start with tags from suggest
        let tagList = (data && data.tags) ? Array.from(data.tags) : [];
        // Also fetch folders to include any folder.tag values (so folder-level tags show up)
        try {
            const fres = await fetch(API_BASE + '/api/memory/folders');
            if (fres.ok) {
                const fd = await fres.json();
                const foldersArr = fd.folders || [];
                for (const ff of foldersArr) {
                    if (ff && ff.tag) {
                        const t = String(ff.tag).trim();
                        if (t && !tagList.some(x => String(x).toLowerCase() === t.toLowerCase())) tagList.push(t);
                    }
                }
            }
        } catch {
            // ignore folder fetch errors; we still show tags from suggest
        }
        suggestions.value = { folders: [], tags: tagList, files: [] };
        showSuggestions.value = (suggestions.value.tags && suggestions.value.tags.length > 0);
    } catch (err) {
        console.warn('Failed to fetch suggestions', err);
        suggestions.value = { folders: [], tags: [], files: [] };
        showSuggestions.value = false;
    }
}, 200);

function onUserInput() {
    // Find the last hashtag prefix in the input
    const v = userMessage.value || '';
    const m = v.match(/#([\w\-\d_]*)$/);
    if (m) {
        const prefix = m[1];
        fetchSuggestionsDebounced(prefix);
    } else {
        suggestions.value = { folders: [], tags: [], files: [] };
        showSuggestions.value = false;
    }
    // detect and validate any complete tags in the input
    detectAndValidateAllTags();
}

function applySuggestion(text) {
    const tag = String(text).replace(/^#/, '');
    if (!selectedTags.value.includes(tag)) selectedTags.value.push(tag);
    // remove trailing partial tag from input
    userMessage.value = (userMessage.value || '').replace(/#([\w\-\d_]*)$/, '').trim();
    showSuggestions.value = false;
}

// Detected tags in the current input and their validity
const detectedTags = ref([]);
const tagValidity = ref({});
// Selected tags chosen by clicking suggestions
const selectedTags = ref([]);

function removeSelectedTag(idx) {
    selectedTags.value.splice(idx, 1);
}

const validateTagsDebounced = debounce(async (tags) => {
    try {
        const newValidity = {};
        await Promise.all(tags.map(async (t) => {
            if (!t) return;
            try {
                const res = await fetch(`${API_BASE}/api/memory/suggest?q=${encodeURIComponent(t)}&limit=5`);
                if (!res.ok) {
                    newValidity[t] = false;
                    return;
                }
                const data = await res.json();
                const found = (data.tags && data.tags.some(x => x.toLowerCase() === t.toLowerCase()))
                    || (data.folders && data.folders.some(x => x.toLowerCase() === t.toLowerCase()))
                    || (data.files && data.files.some(x => x.toLowerCase() === t.toLowerCase()));
                newValidity[t] = !!found;
            } catch {
                newValidity[t] = false;
            }
        }));
        tagValidity.value = newValidity;
    } catch {
        console.warn('validateTagsDebounced error');
    }
}, 250);

function detectAndValidateAllTags() {
    const v = userMessage.value || '';
    const all = Array.from(new Set((v.match(/#([\w\-\d_]+)/g) || []).map(s => s.replace(/^#/, ''))));
    detectedTags.value = all;
    if (all.length > 0) validateTagsDebounced(all);
    else tagValidity.value = {};
}

// Resolve tags to a mem_context string.
// Precedence: if a tag matches a folder (folder.tag or folder.name), use that folder's items; otherwise, use item/file-level context via /api/memory/tag/{tag}/context.
async function resolveTagsToContext(tags) {
    if (!tags || tags.length === 0) return null;
    // fetch folders once
    let foldersList = [];
    try {
    const res = await fetch(API_BASE + '/api/memory/folders');
        if (res.ok) {
            const d = await res.json();
            foldersList = d.folders || [];
        }
    } catch (e) {
        console.warn('Failed to fetch folders for tag resolution', e);
    }
    const folderByTagOrName = new Map();
    for (const f of foldersList) {
        if (f.tag) folderByTagOrName.set(String(f.tag).toLowerCase(), f);
        if (f.name) folderByTagOrName.set(String(f.name).toLowerCase(), f);
    }

    const contexts = [];
    for (const t of tags) {
        const key = String(t).toLowerCase();
        if (folderByTagOrName.has(key)) {
            // folder matched - use folder items
            const folder = folderByTagOrName.get(key);
            try {
                const r = await fetch(`${API_BASE}/api/memory/folders/${folder.id}/items`);
                if (r.ok) {
                    const jd = await r.json();
                    const previews = (jd.items || []).map(i => (i.preview || i.title || i.filename || '')).filter(Boolean);
                    if (previews.length) contexts.push(`Folder: ${folder.name}\n` + previews.slice(0, 5).join('\n---\n'));
                }
            } catch (e) {
                console.warn('Failed to fetch folder items for tag', t, e);
            }
        } else {
            // no folder matched; fetch tag/file context
            try {
                const r2 = await fetch(`${API_BASE}/api/memory/tag/${encodeURIComponent(t)}/context`);
                if (r2.ok) {
                    const jd2 = await r2.json();
                    const previews = (jd2.items || []).map(i => (i.preview || i.filename || '')).filter(Boolean);
                    if (previews.length) contexts.push(`Tag: #${t}\n` + previews.slice(0, 5).join('\n---\n'));
                }
            } catch (e) {
                console.warn('Failed to fetch tag context for', t, e);
            }
        }
    }
    if (contexts.length === 0) return null;
    // join contexts with separators, keep total length bounded
    const joined = contexts.join('\n====\n').slice(0, 3000);
    return joined;
}

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
            // Simple additive hash
            let hash = 0;
            for (let i = 0; i < utf8.length; i++) { hash = (hash + utf8[i]) % 0xffffffff; }
            return sessionKeyPrefix + btoa(hash.toString(16));
        } catch {
            // fallback: use raw string
            return sessionKeyPrefix + btoa((text + '|' + lang + '|' + speaker).slice(0, 32));
        }
    }

    let sessionKey = hashTTSKey(ttsText, lang, speaker);
    let cached = sessionStorage.getItem(sessionKey);
    if (cached) {
        chunkUrls = JSON.parse(cached);
        playChunksFromUrls(chunkUrls, ttsText, msgIndex);
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
                const res = await fetch(API_BASE + '/api/voice_chunk', {
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
            } catch (_err) {
                console.error('TTS chunked playback error:', _err);
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
        playChunksFromUrls(chunkUrls, ttsText, msgIndex);
    } catch (_err) {
        speakingIndex.value = -1;
        speakingWord.value = -1;
        console.error('TTS chunked playback error:', _err);
    }
}

function playChunksFromUrls(urls, text = '', msgIndex = -1) {
    if (!urls || urls.length === 0) {
        speakingIndex.value = -1;
        return;
    }
    // track which message index we are speaking for
    speakingIndex.value = msgIndex;
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
    audioPlayer = new Audio(API_BASE + urls[chunkIndex]);
        // Estimate word range for this chunk
        let wordsPerChunk = words.length > 0 ? Math.ceil(words.length / urls.length) : 0;
        let startWord = chunkIndex * wordsPerChunk;
        // optional endWord calculation removed (not used)
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

function detectLanguage(text) {
    // Simple heuristic: check if all chars are ASCII (then 'en'), else 'auto'
    try {
        for (let i = 0; i < text.length; i++) {
            if (text.charCodeAt(i) > 127) return 'auto';
        }
        return 'en';
    } catch {
        return 'auto';
    }
}

function getDefaultSpeaker(lang) {
    // Map language to default speaker (customize as needed)
    const speakers = {
        en: 'default',
        auto: 'default'
        // ... add more language -> speaker mappings as needed
    };
    return speakers[lang] || 'default';
}

// --- Word Highlighting: highlight word by word if speaking ---
function getHighlightedText(msg, msgIndex) {
    // Base rendered (with optional word highlighting if speaking)
    if (speakingIndex.value !== msgIndex) {
        // Not currently speaking this message; still we may want to append dynamic previews (HTML links) below.
        return appendDynamicResourceLinks(formatBold(msg.text), msg);
    }
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
                html += `<span style="background: #fb923c; color: white; border-radius: 4px; padding: 0 2px;">${tokens[i]}</span>`;
            } else {
                html += tokens[i];
            }
            wordIdx++;
        }
    }
    return appendDynamicResourceLinks(html, msg);
}

// Attach dynamic resource links (e.g., HTML preview) for AI messages whose execute results wrote .html files
function appendDynamicResourceLinks(currentHtml, msg) {
    try {
        if (!msg || msg.sender !== 'ai') return currentHtml;
        const htmlFiles = new Set();
        if (msg.executeResult && Array.isArray(msg.executeResult.results)) {
            for (const r of msg.executeResult.results) {
                const p = (r && r.result && (r.result.path || r.result.saved_path)) || r.path;
                if (typeof p === 'string' && p.toLowerCase().endsWith('.html')) htmlFiles.add(p);
            }
        }
        if (Array.isArray(msg.planExecResults)) {
            for (const r of msg.planExecResults) {
                const p = r && r.result && r.result.path;
                if (typeof p === 'string' && p.toLowerCase().endsWith('.html')) htmlFiles.add(p);
            }
        }
        if (htmlFiles.size === 0) return currentHtml;
        const links = [];
        const arr = Array.from(htmlFiles);
        for (let i = 0; i < arr.length; i++) {
            const abs = String(arr[i] || '');
            try {
                let rel = abs;
                const marker = 'agent_output';
                const idx = abs.toLowerCase().lastIndexOf(marker);
                if (idx !== -1) {
                    rel = abs.substring(idx + marker.length + 1).replace(/\\/g,'/');
                }
                const url = `${API_BASE}/api/code/raw?path=${encodeURIComponent(rel)}`;
                links.push(`<a href="${url}" target="_blank" style="color:#fb923c; text-decoration:underline;">Preview: ${escapeHtml(rel)}</a>`);
            } catch { /* ignore */ }
        }
        if (links.length === 0) return currentHtml;
        return currentHtml + `\n\n<div style="margin-top:8px; padding:6px 8px; background:#fff7ed; border:1px solid #fed7aa; border-radius:6px; font-size:12px; line-height:1.4; color:#92400e;">${links.join(' | ')}</div>`;
    } catch { return currentHtml; }
}

function escapeHtml(str) {
    try {
        return str.replace(/[&<>"]/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[s]));
    } catch { return str; }
}

// Name of this frontend service so backend can separate chats per-service
// Service is dynamic: normal chats use research_assistant, Power Mode uses power_mode
function getServiceName() { return powerMode.value ? 'power_mode' : 'research_assistant' }

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
    // Create a stable key for the user message we are regenerating (chatId + userMsg timestamp + text snippet)
    const regenKey = `${selectedChatId.value}::${userMsg.timestamp || ''}::${String(userMsg.text || '').slice(0, 120)}`;
    if (pendingRegens.has(regenKey)) return;
    pendingRegens.add(regenKey);
    isSending.value = true;
    try {
        // Capture prev AI row id before removing it from local UI (so we can send replace_id)
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
                // Fetch context by resolving tags to folder/file previews
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
                service: getServiceName(),
                mem_context: mem_context,
                replace_last: true,
                replace_id: prevAiRowId,
                request_id: request_id,
                mem_tags: (allTags && allTags.length) ? allTags : undefined
            })
        });
        if (!res.ok) throw new Error('Failed to get LLM response');
        // Refresh canonical chat history from server so UI matches DB (prevents old AI text reappearing later)
        await loadChatMessages(selectedChatId.value);
        // scrollToBottom will be called by loadChatMessages via nextTick
    } catch (err) {
        console.error('Error regenerating response', err);
    } finally {
        pendingRegens.delete(regenKey);
        isSending.value = false;
    }
}
// Dynamic API base: prefer current origin unless it's a file:// or development mismatch; fall back to same host:8000
const ORIGIN = (typeof window !== 'undefined') ? window.location.origin : '';
const API_BASE = (ORIGIN && ORIGIN.startsWith('http')) ? ORIGIN : 'http://localhost:8000';
const API_URL = API_BASE + '/api/chat';
// power_router mounts under the /api/power prefix, so endpoints are /api/power/power_chat etc.
const POWER_CHAT_URL = API_BASE + '/api/power/power_chat';
const POWER_EXECUTE_URL = API_BASE + '/api/power/power_execute';
const WORD_ENHANCE_SELECTION_URL = API_BASE + '/api/power/word/enhance_selection';
const AUTOPLAN_URL = API_BASE + '/api/agent/autoplan';
const FILE_URL = API_BASE + '/api/upload';
const CHATS_URL = API_BASE + '/api/chats';
const CHAT_HISTORY_URL = API_BASE + '/api/chat/';
const CHAT_STATE_URL = API_BASE + '/api/chat_state/';
// Endpoint for intelligently opening documents with the appropriate application
const OPEN_DOC_INTELLIGENTLY_URL = API_BASE + '/api/power/open_doc_intelligently_direct';
const DELETE_CHAT_URL = API_BASE + '/api/chat/';
// Kept for compatibility but not used in passive-first flow
// const INLINE_SELECTION_URL = API_BASE + '/api/automation/inline-selection';
const INLINE_SELECTION_PASSIVE_URL = API_BASE + '/api/automation/inline-selection/passive';

import { ref, onMounted, nextTick, toRef, watch, computed } from 'vue';
// accept darkMode as a prop from parent (App.vue) so the value stays reactive
const props = defineProps(['darkMode']);
const darkMode = toRef(props, 'darkMode');

// --- TTS/Audio State ---
import { renderLimitedMarkdown, cleanLLMText } from '@/utils/markdown';
import IconButton from './IconButton.vue';

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
// Mobile sidebar drawer state
const isMobileSidebarOpen = ref(false);
// Guard set to prevent duplicate regenerate requests for the same user message
const pendingRegens = new Set();
const isEditingChatName = ref(false);
const newChatName = ref('');
const chatNames = ref({});

// --- Inline Selection State ---
const inlineSelectionData = ref(null);
const inlineSelectionLoading = ref(false);
const inlineSelectionError = ref('');
const inlineSelectionShouldReport = ref(false);
const lastClipboardText = ref('');
let clipboardMonitorInterval = null;

// Saved selection text for Word enhancement (persists until send or clear)
const savedSelectionText = ref('');

const inlineSelectionSummary = computed(() => {
    const data = inlineSelectionData.value;
    if (!data || !Array.isArray(data.selections) || data.selections.length === 0) return null;
    const primary = data.primary;
    let candidate = null;
    if (primary) {
        candidate = data.selections.find(sel => sel && sel.source === primary) || null;
    }
    if (!candidate) {
        candidate = data.selections[0] || null;
    }
    return candidate;
});

const inlineSelectionMessage = computed(() => {
    if (inlineSelectionLoading.value) return 'Detecting selection…';
    if (inlineSelectionSummary.value) return null;
    if (!inlineSelectionShouldReport.value) return null;
    return inlineSelectionError.value || 'No active selection detected';
});

// Provide a guarded inline selection preview only if the snapshot is fresh and non-empty.
function getFreshInlineSelectionPreview(maxAgeMs = 15000) { // 15s freshness window
    try {
        const summary = inlineSelectionSummary.value;
        if (!summary) return null;
        // Must have length, preview text, and timestamp (server sends seconds epoch)
        if (!summary.length || !summary.preview) return null;
        const tsSeconds = summary.timestamp;
        if (typeof tsSeconds !== 'number') return null;
        const ageMs = Date.now() - (tsSeconds * 1000);
        if (ageMs > maxAgeMs) return null; // stale snapshot, do not include
        // Also require we are currently in Power Mode (otherwise ignore)
        if (!powerMode.value) return null;
        return String(summary.preview).trim() ? summary.preview : null;
    } catch { return null; }
}

// --- Lightweight Modal State & API ---
const modalOpen = ref(false);
const modalTitle = ref('');
const modalMessage = ref('');
const modalKind = ref('info'); // info | confirm | error
const modalConfirmText = ref('OK');
const modalCancelText = ref('Cancel');
let modalResolver = null;

function showAlertModal(message, title = 'Notice') {
    modalTitle.value = title;
    modalMessage.value = message;
    modalKind.value = 'info';
    modalConfirmText.value = 'OK';
    modalCancelText.value = '';
    modalOpen.value = true;
    return new Promise((resolve) => {
        modalResolver = () => {
            modalOpen.value = false;
            modalResolver = null;
            resolve(undefined);
        };
    });
}

function showErrorModal(message, title = 'Error') {
    modalTitle.value = title;
    modalMessage.value = message;
    modalKind.value = 'error';
    modalConfirmText.value = 'OK';
    modalCancelText.value = '';
    modalOpen.value = true;
    return new Promise((resolve) => {
        modalResolver = () => {
            modalOpen.value = false;
            modalResolver = null;
            resolve(undefined);
        };
    });
}

function showConfirmModal(message, title = 'Confirm', confirmText = 'Yes', cancelText = 'No') {
    modalTitle.value = title;
    modalMessage.value = message;
    modalKind.value = 'confirm';
    modalConfirmText.value = confirmText;
    modalCancelText.value = cancelText;
    modalOpen.value = true;
    return new Promise((resolve) => {
        modalResolver = (ok) => {
            modalOpen.value = false;
            const res = !!ok;
            modalResolver = null;
            resolve(res);
        };
    });
}

function handleModalConfirm() {
    if (modalResolver) modalResolver(true);
    else modalOpen.value = false;
}
function handleModalCancel() {
    if (modalResolver) modalResolver(false);
    else modalOpen.value = false;
}

async function refreshInlineSelection(quiet = false) {
    if (!powerMode.value) {
        inlineSelectionData.value = null;
        if (quiet) {
            inlineSelectionError.value = '';
            inlineSelectionShouldReport.value = false;
        } else {
            inlineSelectionError.value = 'Enable Power Mode to work with inline selections.';
            inlineSelectionShouldReport.value = true;
        }
        return;
    }
    if (inlineSelectionLoading.value) return;
    inlineSelectionLoading.value = true;
    if (quiet) {
        inlineSelectionError.value = '';
        inlineSelectionShouldReport.value = false;
    } else {
        inlineSelectionError.value = '';
        inlineSelectionShouldReport.value = true;
    }
    try {
        // Always read fresh clipboard text
        let clipboardText = '';
        let useClipboardAPI = false;
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                clipboardText = await navigator.clipboard.readText();
                if (clipboardText && clipboardText.trim().length > 0) {
                    useClipboardAPI = true;
                    // Update last known clipboard text
                    lastClipboardText.value = clipboardText;
                    console.debug('Got selection from browser Clipboard API:', clipboardText.length, 'chars');
                }
            }
        } catch (clipErr) {
            console.debug('Clipboard API failed (user may need to grant permission or copy first):', clipErr);
        }

        if (useClipboardAPI && clipboardText.trim()) {
            // Build selection object from clipboard
            const preview = clipboardText.trim().slice(0, 1200);
            const ts = Math.floor(Date.now() / 1000);
            inlineSelectionData.value = {
                ok: true,
                selections: [{
                    source: 'clipboard',
                    label: 'Clipboard (from Word/App)',
                    preview: preview,
                    length: clipboardText.length,
                    timestamp: ts,
                }],
                primary: 'clipboard',
            };
            inlineSelectionError.value = '';
            inlineSelectionShouldReport.value = false;
        } else {
            // Fallback to backend (sends Ctrl+C)
            let res = await fetch(INLINE_SELECTION_PASSIVE_URL, { cache: 'no-store' });
            if (!res.ok) throw new Error(`Selection probe failed (HTTP ${res.status})`);
            let data = await res.json();
            let hasSelections = data && Array.isArray(data.selections) && data.selections.length > 0;
            if (hasSelections) {
                inlineSelectionData.value = data;
                inlineSelectionError.value = '';
                inlineSelectionShouldReport.value = false;
            } else {
                inlineSelectionData.value = null;
                if (!quiet) {
                    const message = (data && (data.message || data.reason)) ? (data.message || data.reason) : 'No active selection detected (try copying with Ctrl+C)';
                    inlineSelectionError.value = message;
                    inlineSelectionShouldReport.value = true;
                } else {
                    inlineSelectionShouldReport.value = false;
                }
            }
            if (data && Array.isArray(data.errors) && data.errors.length > 0) {
                console.debug('Inline selection diagnostics:', data.errors);
            }
        }
    } catch (err) {
        inlineSelectionData.value = null;
        if (!quiet) {
            inlineSelectionError.value = err instanceof Error ? err.message : String(err);
            inlineSelectionShouldReport.value = true;
        }
        console.error('Inline selection fetch failed', err);
    } finally {
        inlineSelectionLoading.value = false;
    }
}

function handleInputFocus() {
    refreshInlineSelection(true);
}

// Kept for compatibility but replaced by disableInlineSelection
// function clearInlineSelectionIndicator() {
//     inlineSelectionData.value = null;
//     inlineSelectionError.value = '';
//     inlineSelectionShouldReport.value = false;
// }

// Start automatic clipboard monitoring when Power Mode is enabled
function startClipboardMonitoring() {
    if (clipboardMonitorInterval) return; // Already running
    
    // Initialize with current clipboard
    (async () => {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                lastClipboardText.value = await navigator.clipboard.readText();
            }
        } catch {
            // Ignore initial read error
        }
    })();
    
    clipboardMonitorInterval = setInterval(async () => {
        if (!powerMode.value) {
            // Stop monitoring if Power Mode is disabled
            stopClipboardMonitoring();
            return;
        }
        
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                const clipText = await navigator.clipboard.readText();
                if (clipText && clipText.trim() && clipText !== lastClipboardText.value) {
                    // New text copied - auto refresh and save
                    console.debug('New clipboard text detected, auto-refreshing selection');
                    lastClipboardText.value = clipText;
                    savedSelectionText.value = clipText; // Save for later use
                    await refreshInlineSelection(true); // quiet mode
                }
            }
        } catch {
            // Silently ignore clipboard permission errors
        }
    }, 300); // Check every 300ms for faster detection
}

function stopClipboardMonitoring() {
    if (clipboardMonitorInterval) {
        clearInterval(clipboardMonitorInterval);
        clipboardMonitorInterval = null;
    }
}

// Enable inline selection and start monitoring
function enableInlineSelection() {
    if (!powerMode.value) {
        inlineSelectionError.value = 'Enable Power Mode to work with inline selections.';
        inlineSelectionShouldReport.value = true;
        return;
    }
    // Start monitoring
    startClipboardMonitoring();
    // Do an immediate check and save
    refreshInlineSelection(false).then(() => {
        // Save the initial selection if available
        const preview = getFreshInlineSelectionPreview();
        if (preview) {
            savedSelectionText.value = preview;
        }
    });
}

// Disable inline selection and stop monitoring
function disableInlineSelection() {
    // Stop monitoring
    stopClipboardMonitoring();
    // Clear selection data
    inlineSelectionData.value = null;
    inlineSelectionError.value = '';
    inlineSelectionShouldReport.value = false;
    lastClipboardText.value = '';
    savedSelectionText.value = ''; // Clear saved selection
}

const acceptedFileTypes = ['.pdf', '.txt', '.doc', '.docx', '.md', '.csv', '.json'];

function generateChatId() {
    return 'chat_' + Date.now();
}

function getChatDisplayName(chatId) {
    return chatNames.value[chatId] || `Chat ${chatId.substring(5, 15)}...`;
}

function formatBold(text) {
    // Only format bold for display, never mutate the original message text
    return renderLimitedMarkdown(text);
}

// cleanLLMText and renderLimitedMarkdown are imported from the shared utility

function goHome() {
    // Restore default app backdrop before leaving
    themeState.clear();
    window.location.reload();
}

// Backend API for renaming chat: POST /api/rename_chat {chat_id, new_name}
async function renameChat() {
    if (newChatName.value.trim() && selectedChatId.value) {
        const trimmed = newChatName.value.trim();
        try {
            const res = await fetch(API_BASE + '/api/rename_chat', {
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
        const res = await fetch(CHATS_URL + '?service=' + encodeURIComponent(getServiceName()));
        if (!res.ok) throw new Error('Failed to fetch chats');
        const chatListObj = await res.json();
        const chatList = chatListObj.chats || [];
        // chatList now contains objects like { chat_id, chat_name, service }
        chats.value = chatList.map(c => c.chat_id || c);
        chatList.forEach(item => {
            const cid = item.chat_id || item;
            const cname = item.chat_name || item.chatName || null;
            if (cname) chatNames.value[cid] = cname;
            else if (!chatNames.value[cid]) chatNames.value[cid] = `Chat ${String(cid).substring(5, 15)}...`;
        });
    } catch (err) {
        console.error("Error loading chats", err);
    } finally { /* no global overlay for chats */ }
}

async function loadChatMessages(chatId) {
    isLoadingHistory.value = true;
    // no global overlay
    messages.value = [];
    selectedChatId.value = chatId;
    newChatName.value = chatNames.value[chatId] || '';
    try {
        const res = await fetch(CHAT_HISTORY_URL + chatId + '?service=' + encodeURIComponent(getServiceName()));
        if (!res.ok) throw new Error('Failed to fetch chat messages');
        const chatMsgsObj = await res.json();
        const chatMsgs = chatMsgsObj.messages || [];
        messages.value = chatMsgs.map(msg => ({ ...msg, text: cleanLLMText(msg.text || '') }));
        nextTick(scrollToBottom);
        // If Power Mode, try to reopen existing Word document (split-screen) for this chat
        if (powerMode.value) {
            try {
                const stRes = await fetch(CHAT_STATE_URL + encodeURIComponent(chatId) + '?service=' + encodeURIComponent(getServiceName()));
                if (stRes.ok) {
                    const st = await stRes.json();
                    const docPath = st && st.state && st.state.doc_path ? st.state.doc_path : null;
                    if (docPath) {
                        // Use the unified endpoint that intelligently decides between Word and VS Code
                        try {
                            await fetch(OPEN_DOC_INTELLIGENTLY_URL, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ 
                                    abs_path: docPath, 
                                    split_screen: true, 
                                    preferred_side: 'right',
                                    chat_context: messages.value.map(m => m.text).join(' ').substring(0, 1000)
                                })
                            });
                        } catch (error) {
                            console.debug('Error opening document:', error);
                        }
                    }
                }
            } catch (e) {
                // Ignore if not available or fails
                console.debug('chat_state/word reopen skipped:', e);
            }
        }
    } catch (err) {
        console.error("Error loading chat messages", err);
    } finally {
        isLoadingHistory.value = false;
        /* no global overlay */
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
    // no global overlay
    const messageText = userMessage.value;
    // Attempt agentic code target inference (non-blocking)
    if (powerMode.value && messageText && messageText.length > 10) {
        inferCodeTargetFromPrompt(messageText);
    }
    userMessage.value = '';
    const fileNames = attachedFiles.value.map(file => file.name);

    // Only sending the first file as per backend limitation
    const fileToSend = attachedFiles.value.length > 0 ? attachedFiles.value[0] : null;

    let fileContent = '';
    if (fileToSend) {
        const ext = fileToSend.name.split('.').pop().toLowerCase();
        if (["txt", "json", "csv", "py", "md"].includes(ext)) {
            // Read as text
            fileContent = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => resolve(e.target && e.target.result ? e.target.result.toString() : '');
                reader.onerror = () => reject('File read error');
                reader.readAsText(fileToSend);
            });
        } else {
            // Send to backend for extraction
            const formData = new FormData();
            formData.append('file', fileToSend);
            formData.append('chat_id', selectedChatId.value);
            const extractRes = await fetch(API_BASE + '/api/extract_text', {
                method: 'POST',
                body: formData
            });
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

    // No heuristic fast-paths: rely on LLM planner + autoplan for deciding actions.

    try {
        if (fileToSend) {
            // Upload file first
            const formData = new FormData();
            formData.append('file', fileToSend);
            formData.append('chat_id', selectedChatId.value);
            const fileRes = await fetch(FILE_URL, {
                method: 'POST',
                body: formData
            });
            if (!fileRes.ok) throw new Error('File upload failed');
        }
        // Send message to backend, include file content in text
        let fullText = messageText;
        if (fileContent) {
            fullText += '\n\n[Document Content]:\n' + fileContent;
        }
        // Before sending, check for #tags in messageText and fetch mem context to include
        let mem_context = null;
        // Collect tags from inline #tags and from selected tag chips
        const inlineTags = (messageText.match(/#([a-zA-Z0-9_-]+)/g) || []).map(s => s.replace(/^#/, ''));
        const chipTags = (selectedTags.value && selectedTags.value.length > 0) ? selectedTags.value.slice() : [];
        const allTagsSet = new Set([...inlineTags, ...chipTags].filter(Boolean).map(t => String(t).trim()));
        const allTags = Array.from(allTagsSet);
        if (allTags.length > 0) {
            try {
                mem_context = await resolveTagsToContext(allTags);
            } catch (e) {
                console.warn('Failed to resolve tags to memory context', e);
            }
        }

        if (powerMode.value) {
            // Use saved selection text instead of re-checking freshness
            const selectionText = savedSelectionText.value.trim();
            
            // Check if we should trigger Word enhancement workflow
            const monitoringActive = !!clipboardMonitorInterval;
            
            // Word enhancement is triggered when:
            // 1. Valid saved selection exists
            // 2. Monitoring is active (user clicked green button)
            // 3. Selection length suggests it's meaningful content (not just a few characters)
            const shouldEnhanceWord = !!selectionText && 
                                      monitoringActive && 
                                      selectionText.length > 10;
            
            if (shouldEnhanceWord) {
                console.log('\n' + '='.repeat(80));
                console.log('WORD ENHANCEMENT - FRONTEND DEBUG');
                console.log('='.repeat(80));
                console.log('1. SELECTION DATA:');
                console.log('   Selection length:', selectionText.length);
                console.log('   Selection preview:', selectionText.slice(0, 200));
                console.log('   Chat ID:', selectedChatId.value);
                console.log('   Monitoring active:', monitoringActive);
                console.log('   User prompt:', messageText);
                
                // Word enhancement: send selection + chat_id to backend
                try {
                    console.log('\n2. SENDING REQUEST TO BACKEND...');
                    const requestBody = {
                        prompt: messageText,
                        selection_text: selectionText,
                        chat_id: selectedChatId.value,
                        max_full_context_chars: 60000,
                        rich: true,
                    };
                    console.log('   Request body:', requestBody);
                    
                    const enhanceRes = await fetch(WORD_ENHANCE_SELECTION_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestBody)
                    });
                    
                    console.log('\n3. BACKEND RESPONSE:');
                    console.log('   Status:', enhanceRes.status, enhanceRes.statusText);
                    
                    console.log('\n3. BACKEND RESPONSE:');
                    console.log('   Status:', enhanceRes.status, enhanceRes.statusText);
                    
                    if (!enhanceRes.ok) {
                        const errData = await enhanceRes.json().catch(() => ({ detail: 'Unknown error' }));
                        console.error('   ERROR:', errData);
                        throw new Error(errData.detail || 'Word enhancement failed');
                    }
                    const enhanceData = await enhanceRes.json();
                    console.log('   Success! Response data:');
                    console.log('   - ok:', enhanceData.ok);
                    console.log('   - clipboard_copied:', enhanceData.clipboard_copied);
                    console.log('   - doc_source:', enhanceData.doc_source);
                    console.log('   - llm_output_length:', enhanceData.llm_output_length);
                    console.log('   - enhanced_text_preview:', enhanceData.enhanced_text_preview);
                    console.log('   Full response:', enhanceData);
                    
                    console.log('\n4. UPDATING UI...');
                    // Show completion message with instructions
                    const completionMsg = {
                        sender: 'ai',
                        text: enhanceData.clipboard_copied 
                            ? `✓ Enhanced text copied to clipboard!\n\n📋 **Instructions:**\n1. **Select the original text** in Word (the text you want to replace)\n2. Press **Ctrl+V** to paste the enhanced version\n\nThe enhanced text is ready in your clipboard.`
                            : '⚠ Enhancement complete but clipboard copy failed. Please check the backend logs.',
                        timestamp: Date.now(),
                    };
                    messages.value.push(completionMsg);
                    console.log('   Completion message added to chat');
                    
                    // Always clear selection after enhancement
                    console.log('   Clearing selection');
                    disableInlineSelection();
                    
                    scrollToBottom();
                    isSending.value = false;
                    console.log('\n5. WORD ENHANCEMENT COMPLETE');
                    console.log('='.repeat(80) + '\n');
                    return; // Skip normal chat flow
                } catch (err) {
                    console.error('\n❌ WORD ENHANCEMENT ERROR:');
                    console.error(err);
                    console.log('='.repeat(80) + '\n');
                    // Show error but continue to normal chat as fallback
                    const errorMsg = {
                        sender: 'ai',
                        text: `⚠ Word enhancement failed: ${err instanceof Error ? err.message : String(err)}. Continuing with normal chat...`,
                        timestamp: Date.now(),
                    };
                    messages.value.push(errorMsg);
                }
            }
            
            // Normal Power Mode chat flow
            console.debug('Using normal Power Mode chat (no Word enhancement)', {
                hasSelection: !!selectionText,
                monitoringActive: monitoringActive,
                selectionLength: selectionText.length
            });
            const res = await fetch(POWER_CHAT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: selectedChatId.value,
                    text: fullText + (selectionText ? `\n\n[Inline Selection Preview]:\n${selectionText}` : ''),
                    doc_info: fileNames.length > 0 ? fileNames.join(', ') : undefined,
                    service: getServiceName(),
                    selected_tags: selectedTags.value && selectedTags.value.length > 0 ? selectedTags.value : undefined,
                    mem_tags: selectedTags.value && selectedTags.value.length > 0 ? selectedTags.value : undefined,
                    mem_context: mem_context,
                    // Ensure backend will auto-execute actions and include results in response
                    auto_execute: true
                })
            });
            if (!res.ok) throw new Error('Failed to get Power Mode response');
            const aiResponse = await res.json();
            const assistantText = cleanLLMText(aiResponse.assistant_text || aiResponse.text || '');
            const actions = Array.isArray(aiResponse.actions) ? aiResponse.actions : [];
            const serverExecResult = aiResponse.execute_result || null;
            const aiMsg = {
                sender: 'ai',
                text: assistantText,
                timestamp: Date.now(),
                actions,
                // Prefer server-side auto-execution result if available
                executeResult: serverExecResult || null
            };
            messages.value.push(aiMsg);
            if (selectionText && !(serverExecResult && serverExecResult.inline_edit)) {
                try { showAlertModal('LLM responded but did not modify the selected text. It may have failed to detect replacement markers.'); } catch { /* ignore */ }
            }
            // If server did not auto-execute (or returned nothing), execute client-side as a fallback
            if (actions.length > 0 && (!serverExecResult || (serverExecResult && !serverExecResult.results && !serverExecResult.error))) {
                try {
                    const ex = await fetch(POWER_EXECUTE_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ actions, chat_id: selectedChatId.value, service: getServiceName() })
                    });
                    const data = await ex.json();
                    aiMsg.executeResult = data;
                } catch (e) {
                    aiMsg.executeResult = { error: String(e) };
                }
            }
            // Agentic AutoPlan (natural language -> filesystem actions) executed after conversational response
            try {
                const planRes = await fetch(AUTOPLAN_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: messageText, execute: true, base_folder: 'project' })
                });
                if (planRes.ok) {
                    const planData = await planRes.json();
                    if (Array.isArray(planData.actions) && planData.actions.length > 0) {
                        const planMsg = {
                            sender: 'ai',
                            text: 'Agent executed ' + planData.actions.length + ' action' + (planData.actions.length === 1 ? '' : 's') + '.',
                            timestamp: Date.now(),
                            planRaw: planData.raw_plan,
                            planPreviews: planData.previews || [],
                            planExecResults: planData.execution_results || [],
                        };
                        messages.value.push(planMsg);
                        nextTick(scrollToBottom);
                    }
                }
            } catch (e) {
                console.debug('autoplan failed', e);
            }
        } else {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: selectedChatId.value,
                    text: fullText,
                    doc_info: fileNames.length > 0 ? fileNames.join(', ') : undefined,
                    service: getServiceName(),
                    selected_tags: selectedTags.value && selectedTags.value.length > 0 ? selectedTags.value : undefined,
                    mem_tags: selectedTags.value && selectedTags.value.length > 0 ? selectedTags.value : undefined,
                    mem_context: mem_context
                })
            });
            if (!res.ok) throw new Error('Failed to get LLM response');
            const aiResponse = await res.json();
            messages.value.push({
                sender: 'ai',
                text: cleanLLMText((aiResponse.text || '')),
                timestamp: Date.now(),
            });
        }
        attachedFiles.value = [];
        selectedTags.value = [];
    } catch (err) {
        console.error("Error sending message", err);
    } finally {
        isSending.value = false;
        nextTick(scrollToBottom);
        await loadChats();
        /* no global overlay */
    }
}

// Execute proposed actions for a specific AI message (Power Mode)
async function executeActionsForMessage(index) {
    const msg = messages.value[index];
    if (!msg || !Array.isArray(msg.actions) || msg.actions.length === 0) return;
    try {
        // no global overlay
        const res = await fetch(POWER_EXECUTE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ actions: msg.actions, chat_id: selectedChatId.value, service: getServiceName() })
        });
        const data = await res.json();
        // attach execute result back to this message
        msg.executeResult = data;
    } catch (e) {
        console.error('Power execute failed', e);
        msg.executeResult = { error: String(e) };
    } finally {
        /* no global overlay */
    }
}

function summarizeExecuteResult(res) {
    try {
        if (Array.isArray(res)) {
            const n = res.length;
            const types = Array.from(new Set(res.map((r) => r && (r.type || r.action || r.result || 'op')))).join(', ');
            const desktop = res.find(r => r && (r.desktop_copied || (r.result && r.result.desktop_copied)));
            if (desktop) {
                const dp = desktop.desktop_path || (desktop.result && desktop.result.desktop_path) || '';
                return `${n} operations (${types}). Copied to Desktop: ${dp ? dp : 'yes'}`;
            }
            return `${n} operations (${types})`;
        }
        if (res && typeof res === 'object') {
            if (res.results && Array.isArray(res.results)) return summarizeExecuteResult(res.results);
            const parts = [];
            if (res.created !== undefined) parts.push(`created: ${res.created}`);
            if (res.path) parts.push(`path: ${res.path}`);
            if (res.file) parts.push(`file: ${res.file}`);
            if (res.message) parts.push(`msg: ${res.message}`);
            if (res.error) parts.push(`error: ${String(res.error).slice(0, 140)}`);
            if (res.desktop_copied) parts.push(`Desktop: ${res.desktop_path || 'copied'}`);
            if (res.opened) parts.push('Opened');
            if (parts.length) return parts.join(', ');
            const keys = Object.keys(res);
            return keys.slice(0, 4).join(', ');
        }
        return String(res);
    } catch {
        try { return JSON.stringify(res).slice(0, 200); } catch { return 'done'; }
    }
}

function attachFiles(event) {
    const target = event.target;
    if (target.files) {
        const newFiles = Array.from(target.files);
        const validFiles = newFiles.filter(file => {
            // Ensure file is a File object
            if (!(file instanceof File)) return false;
            if (!file.name) return false;
            const fileExtension = '.' + file.name.split('.').pop();
            return acceptedFileTypes.includes(fileExtension);
        });

        const filesToAdd = validFiles.slice(0, 3 - attachedFiles.value.length);
        attachedFiles.value.push(...filesToAdd);

        // Read the first file for preview/logging
        if (filesToAdd.length > 0) {
            const file = filesToAdd[0];
            if (file instanceof File && file.name) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    console.log(`File content of ${file.name}:`, e.target && e.target.result);
                };
                reader.readAsText(file);
            }
        }
    }
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

async function confirmDeleteChat(chatId) {
    const ok = await showConfirmModal('Delete this chat and all its messages? This cannot be undone.', 'Delete Chat', 'Delete', 'Cancel');
    if (ok) {
        deleteChat(chatId);
    }
}

async function deleteChat(chatId) {
    try {
        const service = encodeURIComponent(getServiceName());
        const res = await fetch(`${DELETE_CHAT_URL}${encodeURIComponent(chatId)}?service=${service}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete chat');
        // Update local state
        chats.value = chats.value.filter(c => c !== chatId);
        if (selectedChatId.value === chatId) {
            selectedChatId.value = '';
            messages.value = [];
        }
        await loadChats();
    } catch (err) {
        console.error('Delete chat failed', err);
        showErrorModal('Failed to delete chat.');
    }
}

watch(powerMode, (enabled) => {
    if (!enabled) {
        disableInlineSelection();
    }
});

onMounted(async () => {
    // Ensure global backdrop matches the saved Power Mode state on entry
    themeState.setPower(!!powerMode.value);
    await loadChats();
    startNewChat();
    
    // Don't auto-start monitoring - user must click the green button
});

import { onUnmounted } from 'vue';
onUnmounted(() => {
    // Stop clipboard monitoring when component unmounts
    stopClipboardMonitoring();
    // Leaving Research Assistant should restore the default app backdrop
    try { themeState.clear(); } catch { /* noop */ }
});
</script>
<style>
/* Match custom scrollbar used across other components (applies only to main chat messages list) */
.chat-scroll {
    scrollbar-width: thin;
    /* Firefox */
    /* Use orange accents instead of purple so it works in both light/dark modes */
    scrollbar-color: #fb923c rgba(255, 255, 255, 0.08);
    /* Firefox */
}

.chat-scroll::-webkit-scrollbar {
    width: 8px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}

.chat-scroll::-webkit-scrollbar-thumb {
    background: linear-gradient(120deg, #fb923c 60%, #f97316 100%);
    border-radius: 8px;
    min-height: 40px;
    opacity: 0.7;
}

.chat-scroll::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(120deg, #fb923c 80%, #f97316 100%);
    opacity: 1;
}

/* Do not set global body background here; App.vue controls background and Power Mode */

#ResearchAssistant {
    overflow: hidden;
    border-radius: 32px;
}

/* Ensure chat bubbles never overflow on small screens */
.chat-bubble {
    word-wrap: break-word;
    /* legacy */
    overflow-wrap: anywhere;
    /* break long URLs/words */
    max-width: 100%;
}

.chat-bubble p,
.chat-bubble div {
    overflow-wrap: anywhere;
    word-break: break-word;
}

/* Prevent pre/code from forcing horizontal overflow */
.chat-bubble pre,
.chat-bubble code {
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: anywhere;
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
    /* softer orange shadow to match orange accent */
    box-shadow: 0 8px 32px 0 rgba(249, 115, 22, 0.12);
}

/* Power Mode red gradient background */
.power-glass {
    background: linear-gradient(145deg, rgba(244, 63, 94, 0.22) 0%, rgba(239, 68, 68, 0.22) 45%, rgba(248, 113, 113, 0.18) 100%);
    backdrop-filter: blur(18px) saturate(180%);
    -webkit-backdrop-filter: blur(18px) saturate(180%);
    box-shadow: 0 8px 32px 0 rgba(239, 68, 68, 0.25);
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
    background: #fb923c;
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

/* Dimmed + blurred overlay for mobile drawer */
.overlay-dim-blur {
    background: rgba(255, 255, 255, 0.35);
    backdrop-filter: blur(8px) saturate(140%);
    -webkit-backdrop-filter: blur(8px) saturate(140%);
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

/* Opaque navbar to avoid text show-through */
.navbar-opaque {
    background: #ffffff !important;
    backdrop-filter: blur(10px) saturate(150%);
    -webkit-backdrop-filter: blur(10px) saturate(150%);
}

.power-toggle {
    display: inline-flex;
    align-items: center;
    position: relative;
}

.power-toggle__input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}

.power-toggle__track {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    width: 44px;
    height: 24px;
    border-radius: 9999px;
    background-color: #e5e7eb;
    transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.power-toggle__thumb {
    position: absolute;
    top: 50%;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 9999px;
    border: 1px solid #d1d5db;
    background-color: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
    transform: translate(0, -50%);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.power-toggle__input:focus-visible + .power-toggle__track {
    outline: 2px solid rgba(249, 115, 22, 0.45);
    outline-offset: 2px;
}

.power-toggle__input:checked + .power-toggle__track {
    background-color: #fb923c;
}

.power-toggle__input:checked + .power-toggle__track .power-toggle__thumb {
    transform: translate(20px, -50%);
    border-color: #ffffff;
}
</style>
