<template>
  <div id="app">
    <div :class="['min-h-screen font-sans p-6 relative overflow-hidden',
      isPower
        ? 'power-gradient-2'
        : (darkMode
          ? 'bg-gradient-to-br from-gray-950 via-gray-900 to-gray-800'
          : 'light-motion-bg'),
      (!isPower) ? 'orange-on' : ''
    ]">
      <!-- Feathered orange circle with gentle motion (both light and dark; hidden in Power Mode) -->
      <div v-if="!isPower" ref="orangeRef" class="orange-feather" aria-hidden="true"></div>
      <div :class="['absolute inset-0 backdrop-blur-[2px] z-0',
        isPower ? 'bg-cyan-500/10'
          : (darkMode ? 'bg-white/5' : 'bg-white/0')
      ]"></div>
      <div class="relative z-10 max-w-7xl mx-auto">
        <!-- Global loader overlay bound to shared state -->
        <LoaderOverlay :show="loaderState.show" :text="loaderState.text" />
        <header
          v-if="!showResearchAssistant && !showTranslator && !showBeginnerTeacher && !showHomeworkHelper && !showDailyLife && !showMemoryManager"
          class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center justify-between gap-4">
            <h1
              :class="[darkMode ? 'text-white' : 'text-black', 'text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight font-serif']">
              Sarvajña<span class="text-orange-400">GPT</span>
            </h1>
            <!-- Mobile Hamburger -->
            <button v-if="isMobile" @click="toggleMobileActions"
              class="md:hidden h-11 w-11 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 flex items-center justify-center shadow-md transition"
              aria-label="Open menu" title="Menu">
              <span class="material-symbols-outlined text-orange-300">{{ showMobileActions ? 'close' : 'menu' }}</span>
            </button>
          </div>
          <!-- Actions Row (desktop) -->
          <div class="hidden sm:flex items-center gap-3 flex-wrap">
            <div v-if="isPower"
              class="flex items-center gap-1 px-3 py-2 rounded-full bg-red-500/20 border border-red-400/30 text-red-100 shadow">
              <span class="material-symbols-outlined text-sm">flash_on</span>
              <span class="text-xs font-semibold">Power Mode</span>
            </div>
            <!-- Model Selector -->
            <!-- Model Selector -->
            <button @click="openModelModal" :title="backendModel || selectedModel || 'auto'" aria-label="Select model"
              class="flex justify-center items-center gap-2 bg-white/10 hover:bg-white/20 transition-all duration-300 backdrop-blur-md rounded-full text-sm text-white border border-white/10 group shadow-lg hover:shadow-orange-500/20"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-lg flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                model_training
              </span>
              <span class="text-xs hidden sm:inline-flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white/90' : 'text-orange-300'">
                {{ backendModel || selectedModel || 'auto' }}
              </span>
            </button>

            <!-- Live Server -->
            <button @click="openLanModal" aria-label="Live Server"
              class="flex justify-center items-center gap-2 bg-white/10 hover:bg-white/20 transition-all duration-300 backdrop-blur-md rounded-full text-sm text-white border border-white/10 group shadow-lg hover:shadow-orange-500/20"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-lg flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                wifi
              </span>
              <span class="text-xs hidden sm:inline-flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white/90' : 'text-orange-300'">
                Live
              </span>
            </button>

            <!-- Health -->
            <button @click="openHealthModal" aria-label="System Health"
              class="flex justify-center items-center gap-2 bg-white/10 hover:bg-white/20 transition-all duration-300 backdrop-blur-md rounded-full text-sm text-white border border-white/10 group shadow-lg hover:shadow-orange-500/20"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-lg flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                monitor_heart
              </span>
              <span class="text-xs hidden sm:inline-flex items-center justify-center"
                :class="(darkMode || isPower) ? 'text-white/90' : 'text-orange-300'">
                Health
              </span>
            </button>

            <!-- Dark Mode Toggle -->
            <button @click="toggleDarkMode"
              class="bg-white/10 hover:bg-white/20 transition-all duration-300 backdrop-blur-md rounded-full group shadow-lg hover:shadow-orange-500/20 border border-white/10 flex items-center justify-center"
              style="padding: 0.75rem;">
              <span
                class="material-symbols-outlined text-orange-300 group-hover:rotate-45 transition-transform duration-300">
                {{ darkMode ? 'dark_mode' : 'light_mode' }}
              </span>
            </button>


          </div>
          <!-- Mobile Action Drawer -->
          <transition name="fade">
            <div v-if="showMobileActions" class="sm:hidden grid grid-cols-3 gap-2">
              <button @click="openModelModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">model_training</span>
                <small>{{ selectedModel || 'auto' }}</small>
              </button>
              <button @click="openLanModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">wifi</span>
                <small>Live</small>
              </button>
              <button @click="openHealthModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">monitor_heart</span>
                <small>Health</small>
              </button>
              <button @click="toggleDarkMode"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2 col-span-1">
                <span class="material-symbols-outlined text-orange-300">{{ darkMode ? 'dark_mode' : 'light_mode'
                  }}</span>
                <small>{{ darkMode ? 'Dark' : 'Light' }}</small>
              </button>
              <button v-if="isPower" disabled
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-red-500/20 border border-red-400/30 text-[0.65rem] text-red-100 shadow p-2">
                <span class="material-symbols-outlined">flash_on</span>
                <small>Power</small>
              </button>
            </div>
          </transition>
        </header>
        <header
          v-if="showResearchAssistant || showTranslator || showBeginnerTeacher || showHomeworkHelper || showDailyLife || showMemoryManager"
          class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center justify-between gap-4 w-full sm:w-auto">
            <h1
              :class="[darkMode ? 'text-white' : 'text-black', 'text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight font-serif']">
              Sarvajña<span class="text-orange-400">GPT</span>
            </h1>
            <!-- Mobile Hamburger (in-tool) -->
            <button v-if="isMobile" @click="toggleInToolMobileActions"
              class="md:hidden h-11 w-11 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 flex items-center justify-center shadow-md transition"
              aria-label="Menu" title="Menu">
              <span class="material-symbols-outlined text-orange-300">{{ showInToolMobileActions ? 'close' : 'menu'
                }}</span>
            </button>
          </div>
          <!-- Desktop actions -->
          <div class="hidden sm:flex items-center gap-3 flex-wrap">
            <div v-if="isPower"
              class="flex items-center gap-1 px-3 py-2 rounded-full bg-red-500/20 border border-red-400/30 text-red-100 shadow">
              <span class="material-symbols-outlined text-sm">flash_on</span>
              <span class="text-xs font-semibold">Power Mode</span>
            </div>
            <!-- Desktop Action Buttons -->
            <button @click="openLanModal" title="Local Live Access" aria-label="Local Live Access"
              class="flex items-center gap-2 rounded-full text-xs font-medium bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-white shadow transition h-11"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-base"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                wifi
              </span>
              <span>Live</span>
            </button>

            <button @click="openModelModal" :title="backendModel || selectedModel || 'auto'" aria-label="Select model"
              class="flex items-center gap-2 rounded-full text-xs font-medium bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-white shadow transition h-11"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-base"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                model_training
              </span>
              <span>{{ backendModel || selectedModel || 'auto' }}</span>
            </button>

            <button @click="openHealthModal" aria-label="Health"
              class="flex items-center gap-2 rounded-full text-xs font-medium bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-white shadow transition h-11"
              style="padding: 0.5rem 0.75rem;">
              <span class="material-symbols-outlined text-base"
                :class="(darkMode || isPower) ? 'text-white' : 'text-orange-300'">
                monitor_heart
              </span>
              <span>Health</span>
            </button>

            <button @click="toggleDarkMode"
              class="flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 border border-white/10 backdrop-blur-md shadow transition group h-11 w-11"
              aria-label="Toggle dark mode" style="padding: 0.75rem;">
              <span class="material-symbols-outlined text-orange-300 group-hover:rotate-45 transition-transform">
                {{ darkMode ? 'dark_mode' : 'light_mode' }}
              </span>
            </button>
          </div>
          <!-- In-tool Mobile Action Drawer -->
          <transition name="fade">
            <div v-if="showInToolMobileActions" class="sm:hidden grid grid-cols-3 gap-2">
              <button @click="openModelModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">model_training</span>
                <small>{{ selectedModel || 'auto' }}</small>
              </button>
              <button @click="openLanModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">wifi</span>
                <small>Live</small>
              </button>
              <button @click="openHealthModal"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2">
                <span class="material-symbols-outlined text-orange-300">monitor_heart</span>
                <small>Health</small>
              </button>
              <button @click="toggleDarkMode"
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 text-[0.65rem] text-white shadow transition p-2 col-span-1">
                <span class="material-symbols-outlined text-orange-300">{{ darkMode ? 'dark_mode' : 'light_mode'
                  }}</span>
                <small>{{ darkMode ? 'Dark' : 'Light' }}</small>
              </button>
              <button v-if="isPower" disabled
                class="h-20 flex flex-col items-center justify-center gap-1 rounded-xl bg-red-500/20 border border-red-400/30 text-[0.65rem] text-red-100 shadow p-2">
                <span class="material-symbols-outlined">flash_on</span>
                <small>Power</small>
              </button>
            </div>
          </transition>
        </header>

        <!-- Model selector modal -->
        <div v-if="showModelModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-2 sm:px-4">
          <div
            class="rounded-2xl w-full max-w-[880px] p-5 sm:p-6 shadow-2xl border border-white/20 max-h-[90vh] flex flex-col overflow-hidden"
            style="background:rgba(255,255,255,0.16);backdrop-filter:blur(18px) saturate(170%);-webkit-backdrop-filter:blur(18px) saturate(170%);">
            <div class="flex justify-between items-center mb-4">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-white/90">model_training</span>
                <h3 class="text-xl font-semibold text-white">Ollama Models</h3>
              </div>
              <div class="flex items-center gap-2">
                <button @click="fetchOllamaModels"
                  class="px-4 py-2 rounded bg-white/20 text-white hover:bg-white/30 transition">Refresh</button>
                <button @click="showModelModal = false" class="text-white/80 hover:text-white">Close</button>
              </div>

            </div>
            <div class="mb-4 text-xs sm:text-sm text-white/80 leading-relaxed">Only showing models discoverable from
              your local Ollama installation. Install missing ones via the provided PowerShell command. Sizes are
              approximate when available.</div>
            <div class="mb-5 flex-1 min-h-0 overflow-auto glass-modal-scroll pr-3"
              style="scrollbar-gutter: stable both-edges;">
              <div class="mb-3 text-sm text-white/90">Current backend model: <strong class="text-white">{{ backendModel
                || 'Unknown' }}</strong></div>
              <div class="mb-3">
                <h4 class="text-sm font-semibold text-white mb-2">Installed</h4>
                <table class="w-full text-sm">
                  <thead class="text-left text-white/70 border-b border-white/20">
                    <tr>
                      <th class="py-2">Model</th>
                      <th class="py-2">Size</th>
                      <th class="py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="installedModels.length === 0">
                      <td colspan="3" class="py-3 text-white/70">No models found from local Ollama. Ensure Ollama is
                        running.</td>
                    </tr>
                    <tr v-for="m in installedModels" :key="m.name" class="border-b border-white/10">
                      <td class="py-2 text-white">{{ m.name }}</td>
                      <td class="py-2 text-white/90">{{ humanizeBytes(m.size) }}</td>
                      <td class="py-2 text-right">
                        <button @click="setBackendModel(m.name)"
                          class="px-3 py-1 rounded bg-white/20 text-white hover:bg-white/30 transition">Use</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div>
                <h4 class="text-sm font-semibold text-white mb-2">Recommended</h4>
                <table class="w-full text-sm">
                  <thead class="text-left text-white/70 border-b border-white/20">
                    <tr>
                      <th class="py-2">Model</th>
                      <th class="py-2">Size</th>
                      <th class="py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="m in recommendedModels" :key="m.name" class="border-b border-white/10">
                      <td class="py-2 text-white">{{ m.name }}</td>
                      <td class="py-2 text-white/90">{{ m.estimated_size || 'Unknown' }}</td>
                      <td class="py-2 text-right">
                        <button @click="prepareInstall(m)"
                          class="px-3 py-1 bg-orange-600 text-white rounded hover:bg-orange-500 transition">Install</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Install confirmation modal -->
        <div v-if="showInstallConfirm" class="fixed inset-0 z-60 flex items-center justify-center bg-black/40">
          <div class="rounded-2xl w-[720px] max-w-[98%] p-6 shadow-2xl border border-white/20"
            style="background:rgba(255,255,255,0.16);backdrop-filter:blur(16px) saturate(160%);-webkit-backdrop-filter:blur(16px) saturate(160%);">
            <div class="flex justify-between items-center mb-4">
              <h3 class="text-lg font-semibold text-white">Install model: {{ installingModel?.name }}</h3>
              <button @click="cancelInstall" class="text-white/80 hover:text-white">Close</button>
            </div>
            <div class="mb-3 text-sm text-white/90">Estimated disk usage: <strong class="text-white">{{
              installingModel?.estimated_size || installingModel?.sizeDisplay || 'Unknown' }}</strong></div>
            <div class="mb-3 text-sm text-white/90">This will run the following PowerShell command on your machine to
              download and install the model using Ollama:</div>
            <pre
              class="bg-black/30 text-white p-3 rounded text-xs overflow-auto border border-white/10">{{ installCommand }}</pre>
            <div class="mt-4 flex justify-end gap-2">
              <button @click="copyCommandToClipboard"
                class="px-4 py-2 rounded bg-white/20 text-white hover:bg-white/30 transition">Copy command</button>
              <button @click="executeInstall"
                class="px-4 py-2 rounded bg-orange-600 text-white hover:bg-orange-500 transition">I understand —
                Install</button>
              <button @click="showInstallConfirm = false"
                class="px-4 py-2 rounded bg-red-500/20 text-red-100 hover:bg-red-500/30 transition">Cancel</button>
            </div>
          </div>
        </div>
        <section
          v-if="!showResearchAssistant && !showTranslator && !showBeginnerTeacher && !showHomeworkHelper && !showDailyLife && !showMemoryManager"
          class="mb-20 text-center">
          <h2 style="margin-top: 40px;"
            :class="[darkMode ? 'text-white' : 'text-black', 'text-4xl md:text-5xl lg:text-7xl font-bold mb-8 drop-shadow-lg font-serif tracking-tight']">
            <span
              class="text-4xl md:text-5xl lg:text-7xl font-bold bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">Agentic
              AI</span>
            That Understands
          </h2>
          <p
            :class="[darkMode ? 'text-gray-300' : 'text-gray-900', 'text-lg md:text-xl max-w-3xl mx-auto leading-relaxed font-light']">
            Your proactive companion for learning, decision-making, and daily life — context-aware, adaptive, and always
            acting with purpose.
          </p>
        </section>
        <section
          v-if="!showResearchAssistant && !showTranslator && !showBeginnerTeacher && !showHomeworkHelper && !showDailyLife && !showMemoryManager"
          class="mt-10 pb-5">
          <div class="flex items-center justify-between mb-4">
            <div></div>
            <div class="gap-3 hidden md:flex">
              <button @click="prevSlide" aria-label="Previous"
                class="h-12 w-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md text-white flex items-center justify-center shadow-lg transition">
                <span
                  :class="['material-symbols-outlined text-lg', (darkMode || isPower) ? 'text-white' : 'text-black']">chevron_left</span>
              </button>
              <button @click="nextSlide" aria-label="Next"
                class="h-12 w-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 backdrop-blur-md text-white flex items-center justify-center shadow-lg transition">
                <span
                  :class="['material-symbols-outlined text-lg', (darkMode || isPower) ? 'text-white' : 'text-black']">chevron_right</span>
              </button>
            </div>
          </div>
          <div @mouseenter="pauseAutoplay" @mouseleave="resumeAutoplay" class="overflow-hidden px-1 md:px-2"
            @touchstart.passive="onTouchStart" @touchmove.passive="onTouchMove" @touchend="onTouchEnd">
            <div :class="['flex gap-0', transitionEnabled ? 'transition-transform ease-in-out' : '']"
              :style="trackComputedStyle" @transitionend="onTransitionEnd">
              <div v-for="(item, idx) in extendedFeatures" :key="item.id + '-' + idx"
                class="flex-shrink-0 px-1 md:px-3 pb-2.5 pt-2.5" :style="{ width: `calc(100% / ${visibleCount})` }">
                <button @click="item.action" type="button" :class="[
                  'shadow-lg transform hover:-translate-y-1 transition-all duration-300 rounded-2xl group cursor-pointer h-[18rem] sm:h-72 w-full text-left focus:outline-none',
                  isPower ? 'hover:shadow-red-500/30' : (darkMode ? 'hover:shadow-orange-400/25' : 'hover:shadow-orange-500/20')
                ]">
                  <div :class="[
                    isPower
                      ? 'bg-red-50/40 border-red-200/20 text-black'
                      : (darkMode ? 'bg-white/10 border-white/10 text-white' : 'bg-white border-gray-100 text-black'),
                    'backdrop-blur-md rounded-2xl p-6 h-full flex flex-col justify-between',
                    'group-hover:ring-4',
                    isPower ? 'group-hover:ring-red-400/30' : (darkMode ? 'group-hover:ring-orange-400/25' : 'group-hover:ring-orange-500/25')
                  ]">
                    <div>
                      <div
                        :class="item.iconBg + ' rounded-full w-14 h-14 flex items-center justify-center mb-4 group-hover:opacity-90 transition-all'">
                        <span
                          :class="['material-symbols-outlined text-2xl', (darkMode || isPower) ? 'text-white' : 'text-black']">{{
                            item.icon }}</span>
                      </div>
                      <h3
                        :class="[(darkMode || isPower) ? 'text-white' : 'text-orange-400', 'text-xl font-semibold mb-2 font-serif']">
                        {{ item.title }}</h3>
                      <p :class="[(darkMode || isPower) ? 'text-gray-300' : 'text-gray-700', 'text-sm']">{{ item.desc }}
                      </p>
                    </div>
                    <div class="mt-4">
                      <span :class="[
                        isPower ? 'text-red-400 hover:text-red-300' : (darkMode ? 'text-orange-300 hover:text-orange-200' : 'text-orange-500 hover:text-orange-400'),
                        'flex items-center group-hover:translate-x-1 transition-all select-none'
                      ]">Explore
                        <span class="material-symbols-outlined ml-1 text-sm">arrow_forward</span></span>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </section>
        <!-- System Health Modal -->
        <div v-if="showHealthModal"
          class="fixed inset-0 z-60 flex items-center justify-center bg-black/40 px-2 sm:px-4">
          <div
            class="rounded-2xl w-full max-w-[880px] p-5 sm:p-6 shadow-2xl border border-white/20 max-h-[90vh] overflow-hidden flex flex-col"
            style="background:rgba(255,255,255,0.16);backdrop-filter:blur(18px) saturate(170%);-webkit-backdrop-filter:blur(18px) saturate(170%);">
            <div class="flex justify-between items-center mb-4">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-white/90">monitor_heart</span>
                <h3 class="text-xl font-semibold text-white">System Health</h3>
              </div>
              <div class="flex items-center gap-2">
                <button @click="refreshHealth"
                  class="px-3 py-1 rounded bg-white/20 text-white hover:bg-white/30 transition">Refresh</button>
                <button @click="showHealthModal = false" class="text-white/80 hover:text-white">Close</button>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs sm:text-sm text-white">
              <div>
                <div class="text-white/80">Backend</div>
                <div class="mt-1">Python: <span class="text-white">{{ health.python || '—' }}</span></div>
                <div>Platform: <span class="text-white">{{ health.platform || '—' }}</span></div>
                <div class="mt-1">VS Code: <span
                    :class="health.automation?.vscode_ready ? 'text-green-300' : 'text-red-300'">{{
                      health.automation?.vscode_ready ? 'Ready' : 'Missing' }}</span></div>
                <div>Word: <span :class="health.automation?.word_ready ? 'text-green-300' : 'text-yellow-300'">{{
                  health.automation?.word_ready ? 'Ready' : 'Unavailable' }}</span></div>
                <div>CUA: <span :class="health.automation?.cua_ready ? 'text-green-300' : 'text-yellow-300'">{{
                  health.automation?.cua_ready ? 'Ready' : 'Inactive' }}</span></div>
              </div>
              <div>
                <div class="text-white/80">OCR</div>
                <div class="mt-1">Tesseract: <span
                    :class="health.ocr?.tesseract_version ? 'text-green-300' : 'text-red-300'">{{
                      health.ocr?.tesseract_version || 'Not detected' }}</span></div>
                <div class="mt-0.5">Renderers:
                  <span :class="ocrAnyRenderer ? 'text-green-300' : 'text-red-300'">{{ ocrRendererSummary }}</span>
                </div>
                <div class="text-[11px] opacity-70 mt-0.5">
                  Poppler is optional; using {{ preferredRendererLabel }}.
                </div>
              </div>
              <div>
                <div class="text-white/80">Packages</div>
                <div class="mt-1">Torch: <span class="text-white">{{ health.packages?.torch?.version ||
                  health.packages?.torch?.error || '—' }}</span></div>
                <div>CUDA: <span
                    :class="health.packages?.torch?.cuda_available ? 'text-green-300' : 'text-yellow-300'">{{
                      health.packages?.torch?.cuda_available ? 'Yes' : 'No' }}</span></div>
              </div>
            </div>
            <!-- Feature Matrix -->
            <div class="mt-4 sm:mt-6 flex-1 min-h-0 overflow-auto pr-1">
              <div class="flex items-center justify-between mb-2">
                <h4 class="text-white/80 font-semibold text-sm tracking-wide">Feature Readiness</h4>
                <span class="text-xs px-2 py-0.5 rounded-full"
                  :class="health.ok ? 'bg-green-500/30 text-green-200' : 'bg-red-500/30 text-red-200'">{{ health.ok ?
                    'ALL CRITICAL READY' : 'MISSING ITEMS' }}</span>
              </div>
              <div v-if="health.features_summary && health.features_summary.length"
                class="grid md:grid-cols-2 gap-3 max-h-72 overflow-auto pr-3 text-xs glass-modal-scroll"
                style="scrollbar-gutter: stable both-edges;">
                <div v-for="f in health.features_summary" :key="f.name"
                  class="p-3 rounded-lg border border-white/15 bg-white/5 backdrop-blur-sm flex flex-col gap-1">
                  <div class="flex items-center justify-between">
                    <span class="font-medium"
                      :class="f.ok ? 'text-green-200' : (f.optional ? 'text-yellow-200' : 'text-red-300')">{{ f.name
                      }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full"
                      :class="f.ok ? 'bg-green-500/25 text-green-100' : 'bg-red-500/30 text-red-100'">{{ f.ok ? 'OK' :
                        (f.optional ? 'Optional' : 'Missing') }}</span>
                  </div>
                  <div v-if="!f.ok && f.missing && f.missing.length" class="text-red-200/80 leading-snug">
                    <span class="opacity-80">Missing:</span>
                    <span class="ml-1">{{ f.missing.join(', ') }}</span>
                  </div>
                  <div v-else class="text-green-300/70">Ready</div>
                </div>
              </div>
              <div v-else class="text-white/60 text-xs">No feature matrix data.</div>
            </div>
            <!-- Missing critical summary -->
            <div v-if="health.missing_critical_dependencies && health.missing_critical_dependencies.length"
              class="mt-4 text-xs text-red-200">
              <div class="font-medium mb-1">Critical Dependencies Missing:</div>
              <div class="flex flex-wrap gap-1">
                <span v-for="m in health.missing_critical_dependencies" :key="m"
                  class="px-2 py-0.5 bg-red-500/25 rounded-full">{{ m }}</span>
              </div>
            </div>
          </div>
        </div>
        <!-- LAN Info Modal -->
        <div v-if="showLanModal" class="fixed inset-0 z-60 flex items-center justify-center bg-black/40 px-2 sm:px-4">
          <div
            class="rounded-2xl w-full max-w-[640px] p-5 sm:p-6 shadow-2xl border border-white/20 max-h-[88vh] overflow-hidden flex flex-col"
            style="background:rgba(255,255,255,0.16);backdrop-filter:blur(18px) saturate(170%);-webkit-backdrop-filter:blur(18px) saturate(170%);">
            <div class="flex justify-between items-center mb-4">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-white/90">wifi</span>
                <h3 class="text-xl font-semibold text-white">Local Live Access</h3>
              </div>
              <button @click="showLanModal = false" class="text-white/80 hover:text-white">Close</button>
            </div>
            <div class="flex flex-wrap items-center gap-2 mb-3 text-[11px] sm:text-xs">
              <span
                :class="['px-2 py-0.5 rounded-full', lanInfo.live_enabled ? 'bg-green-500/30 text-green-200' : 'bg-red-500/30 text-red-200']">{{
                  lanInfo.live_enabled ? 'ENABLED' : 'DISABLED' }}</span>
              <span class="px-2 py-0.5 rounded-full bg-white/10 text-white/80">Devices: {{ lanInfo.connected_count || 0
                }}</span>
              <button v-if="!lanInfo.live_enabled" @click="enableLive()"
                class="px-3 py-1 rounded bg-green-600/70 hover:bg-green-600 text-white transition">Enable</button>
              <button v-else @click="disableLive()"
                class="px-3 py-1 rounded bg-red-600/70 hover:bg-red-600 text-white transition">Disable</button>
              <button @click="fetchLanInfo()"
                class="px-3 py-1 rounded bg-white/15 hover:bg-white/25 text-white transition">Refresh</button>
            </div>
            <div class="text-sm text-white/80 mb-3">Use these URLs from another device on the <strong>same Wi‑Fi /
                LAN</strong>. No internet required. Keep this computer on. If it does not load, allow Python / Uvicorn
              through Windows Firewall (port 8000).</div>
            <div v-if="lanInfo.live_enabled && lanInfo.urls && lanInfo.urls.length"
              class="space-y-2 flex-1 min-h-0 overflow-auto pr-2 glass-modal-scroll"
              style="scrollbar-gutter:stable both-edges;">
              <div v-for="u in lanInfo.urls" :key="u"
                class="flex items-center gap-2 bg-white/10 border border-white/10 rounded px-3 py-2">
                <code class="text-white text-xs break-all flex-1">{{ u }}</code>
                <button @click="copyText(u)"
                  class="px-2 py-1 text-[11px] rounded bg-white/20 hover:bg-white/30 text-white">Copy</button>
              </div>
            </div>
            <div v-else class="text-white/70 text-sm" :class="!lanInfo.live_enabled ? 'italic' : ''">
              <span v-if="!lanInfo.live_enabled">Live access disabled.</span>
              <span v-else>Scanning local interfaces...</span>
            </div>
            <div v-if="lanInfo.connected_count" class="mt-4 text-[11px] text-white/70">
              Recently active devices (last {{ lanInfo.client_ttl_seconds / 60 || 5 }} min):
              <span v-for="ip in lanInfo.connected_clients" :key="ip" class="ml-1 px-1.5 py-0.5 bg-white/10 rounded">{{
                ip }}</span>
            </div>
            <div class="mt-4 text-[10px] sm:text-[11px] text-white/60">
              Tip: Bookmark one of these on your phone browser. Use http not https. This is local only.
            </div>
          </div>
        </div>
        <div v-if="darkMode || isPower"
          class="absolute top-20 right-10 w-80 h-80 rounded-full bg-orange-500/10 blur-3xl animate-pulse"></div>
        <div v-if="darkMode || isPower"
          class="absolute bottom-20 left-10 w-96 h-96 rounded-full bg-indigo-500/10 blur-3xl"></div>
        <div v-if="darkMode || isPower"
          class="absolute top-[40%] left-[30%] w-60 h-60 rounded-full bg-cyan-500/10 blur-3xl animate-pulse"></div>
        <div v-if="darkMode || isPower"
          class="absolute -bottom-10 right-[20%] w-40 h-40 rounded-full bg-teal-500/10 blur-3xl"></div>
        <ResearchAssistant v-if="showResearchAssistant" :darkMode="darkMode" @back="showResearchAssistant = false" />
        <MemoryManager v-if="showMemoryManager" :darkMode="darkMode" @back="showMemoryManager = false" />
        <BeginnerTeacher v-if="showBeginnerTeacher" :darkMode="darkMode" @back="showBeginnerTeacher = false" />
        <HomeworkHelper v-if="showHomeworkHelper" :darkMode="darkMode" @back="showHomeworkHelper = false" />
        <Translator v-if="showTranslator" :darkMode="darkMode" :powerMode="isPower" @back="showTranslator = false" />
        <DailyLife v-if="showDailyLife" :darkMode="darkMode" @back="showDailyLife = false" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Light motion background: soft animated blobs + faint grid + noise overlay */
.light-motion-bg {
  background: radial-gradient(1200px 800px at 20% -10%, rgba(255, 255, 255, 0.7), rgba(255, 255, 255, 0)),
    radial-gradient(900px 700px at 110% 20%, rgba(173, 216, 230, 0.35), rgba(255, 255, 255, 0)),
    radial-gradient(800px 600px at -10% 80%, rgba(135, 206, 250, 0.35), rgba(255, 255, 255, 0)),
    #f7fbff;
  position: relative;
}

.light-motion-bg::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(220px 220px at 10% 20%, rgba(120, 180, 255, 0.30), transparent 60%),
    radial-gradient(280px 250px at 80% 10%, rgba(255, 160, 200, 0.22), transparent 65%),
    radial-gradient(260px 240px at 20% 85%, rgba(140, 230, 200, 0.22), transparent 62%),
    radial-gradient(240px 240px at 90% 75%, rgba(255, 220, 140, 0.16), transparent 60%);
  filter: blur(40px);
  animation: float-blobs 22s ease-in-out infinite alternate;
  pointer-events: none;
  z-index: 0;
}

.light-motion-bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(0deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.3)),
    repeating-linear-gradient(0deg,
      rgba(0, 62, 140, 0.06) 0px,
      rgba(0, 62, 140, 0.06) 1px,
      transparent 1px,
      transparent 40px),
    repeating-linear-gradient(90deg,
      rgba(0, 62, 140, 0.06) 0px,
      rgba(0, 62, 140, 0.06) 1px,
      transparent 1px,
      transparent 40px);
  mix-blend-mode: normal;
  opacity: 0.20;
  animation: grid-fade 16s ease-in-out infinite alternate;
  pointer-events: none;
  z-index: 0;
}

@keyframes float-blobs {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
  }

  50% {
    transform: translate3d(-2%, 1%, 0) scale(1.02);
  }

  100% {
    transform: translate3d(2%, -1%, 0) scale(1.03);
  }
}

@keyframes grid-fade {
  0% {
    opacity: 0.22;
    filter: hue-rotate(0deg) saturate(1);
  }

  100% {
    opacity: 0.30;
    filter: hue-rotate(10deg) saturate(1.1);
  }
}

@media (prefers-reduced-motion: reduce) {

  .light-motion-bg::before,
  .light-motion-bg::after {
    animation: none !important;
  }
}

/* Orange feather circle */
.orange-feather {
  position: absolute;
  top: 0;
  left: 0;
  width: clamp(520px, 48vw, 780px);
  height: clamp(520px, 48vw, 780px);
  background: radial-gradient(circle at 45% 50%,
      rgba(255, 120, 0, 0.55) 0%,
      rgba(255, 150, 40, 0.42) 28%,
      rgba(255, 185, 110, 0.22) 55%,
      rgba(255, 205, 150, 0.10) 72%,
      rgba(255, 205, 150, 0) 80%);
  filter: blur(70px);
  border-radius: 50%;
  mix-blend-mode: normal;
  pointer-events: none;
  z-index: 1;
  transform: translate(-12vw, 10vh) scale(1.02);
  will-change: transform;
}

@media (max-width: 768px) {
  .orange-feather {
    width: min(88vw, 720px);
    height: min(88vw, 720px);
    filter: blur(56px);
    transform: translate(-22vw, 12vh) scale(1.02);
  }
}

@media (prefers-reduced-motion: reduce) {
  .orange-feather {
    transition: none;
  }
}

*,
:after,
:before {
  --tw-border-spacing-x: 0;
  --tw-border-spacing-y: 0;
  --tw-translate-x: 0;
  --tw-translate-y: 0;
  --tw-rotate: 0;
  --tw-skew-x: 0;
  --tw-skew-y: 0;
  --tw-scale-x: 1;
  --tw-scale-y: 1;
  --tw-pan-x: ;
  --tw-pan-y: ;
  --tw-pinch-zoom: ;
  --tw-scroll-snap-strictness: proximity;
  --tw-gradient-from-position: ;
  --tw-gradient-via-position: ;
  --tw-gradient-to-position: ;
  --tw-ordinal: ;
  --tw-slashed-zero: ;
  --tw-numeric-figure: ;
  --tw-numeric-spacing: ;
  --tw-numeric-fraction: ;
  --tw-ring-inset: ;
  --tw-ring-offset-width: 0px;
  --tw-ring-offset-color: #fff;
  --tw-ring-color: rgba(59, 130, 246, 0.5);
  --tw-ring-offset-shadow: 0 0 #0000;
  --tw-ring-shadow: 0 0 #0000;
  --tw-shadow: 0 0 #0000;
  --tw-shadow-colored: 0 0 #0000;
  --tw-blur: ;
  --tw-brightness: ;
  --tw-contrast: ;
  --tw-grayscale: ;
  --tw-hue-rotate: ;
  --tw-invert: ;
  --tw-saturate: ;
  --tw-sepia: ;
  --tw-drop-shadow: ;
  --tw-backdrop-blur: ;
  --tw-backdrop-brightness: ;
  --tw-backdrop-contrast: ;
  --tw-backdrop-grayscale: ;
  --tw-backdrop-hue-rotate: ;
  --tw-backdrop-invert: ;
  --tw-backdrop-opacity: ;
  --tw-backdrop-saturate: ;
  --tw-backdrop-sepia: ;
  --tw-contain-size: ;
  --tw-contain-layout: ;
  --tw-contain-paint: ;
  --tw-contain-style: ;
}

::backdrop {
  --tw-border-spacing-x: 0;
  --tw-border-spacing-y: 0;
  --tw-translate-x: 0;
  --tw-translate-y: 0;
  --tw-rotate: 0;
  --tw-skew-x: 0;
  --tw-skew-y: 0;
  --tw-scale-x: 1;
  --tw-scale-y: 1;
  --tw-pan-x: ;
  --tw-pan-y: ;
  --tw-pinch-zoom: ;
  --tw-scroll-snap-strictness: proximity;
  --tw-gradient-from-position: ;
  --tw-gradient-via-position: ;
  --tw-gradient-to-position: ;
  --tw-ordinal: ;
  --tw-slashed-zero: ;
  --tw-numeric-figure: ;
  --tw-numeric-spacing: ;
  --tw-numeric-fraction: ;
  --tw-ring-inset: ;
  --tw-ring-offset-width: 0px;
  --tw-ring-offset-color: #fff;
  --tw-ring-color: rgba(59, 130, 246, 0.5);
  --tw-ring-offset-shadow: 0 0 #0000;
  --tw-ring-shadow: 0 0 #0000;
  --tw-shadow: 0 0 #0000;
  --tw-shadow-colored: 0 0 #0000;
  --tw-blur: ;
  --tw-brightness: ;
  --tw-contrast: ;
  --tw-grayscale: ;
  --tw-hue-rotate: ;
  --tw-invert: ;
  --tw-saturate: ;
  --tw-sepia: ;
  --tw-drop-shadow: ;
  --tw-backdrop-blur: ;
  --tw-backdrop-brightness: ;
  --tw-backdrop-contrast: ;
  --tw-backdrop-grayscale: ;
  --tw-backdrop-hue-rotate: ;
  --tw-backdrop-invert: ;
  --tw-backdrop-opacity: ;
  --tw-backdrop-saturate: ;
  --tw-backdrop-sepia: ;
  --tw-contain-size: ;
  --tw-contain-layout: ;
  --tw-contain-paint: ;
  --tw-contain-style: ;
}

/*! tailwindcss v3.4.17 | MIT License | https://tailwindcss.com*/
*,
:after,
:before {
  border: 0 solid #e5e7eb;
  box-sizing: border-box;
}

:after,
:before {
  --tw-content: "";
}

:host,
html {
  line-height: 1.5;
  -webkit-text-size-adjust: 100%;
  font-family:
    Open Sans,
    ui-sans-serif,
    system-ui,
    sans-serif,
    Apple Color Emoji,
    Segoe UI Emoji,
    Segoe UI Symbol,
    Noto Color Emoji;
  font-feature-settings: normal;
  font-variation-settings: normal;
  -moz-tab-size: 4;
  tab-size: 4;
  -webkit-tap-highlight-color: transparent;
}

body {
  line-height: inherit;
  margin: 0;
}

hr {
  border-top-width: 1px;
  color: inherit;
  height: 0;
}

abbr:where([title]) {
  text-decoration: underline dotted;
}

h1,
h2,
h3,
h4,
h5,
h6 {
  font-size: inherit;
  font-weight: inherit;
}

a {
  color: inherit;
  text-decoration: inherit;
}

b,
strong {
  font-weight: bolder;
}

code,
kbd,
pre,
samp {
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Monaco,
    Consolas,
    Liberation Mono,
    Courier New,
    monospace;
  font-feature-settings: normal;
  font-size: 1em;
  font-variation-settings: normal;
}

small {
  font-size: 80%;
}

sub,
sup {
  font-size: 75%;
  line-height: 0;
  position: relative;
  vertical-align: baseline;
}

sub {
  bottom: -0.25em;
}

sup {
  top: -0.5em;
}

table {
  border-collapse: collapse;
  border-color: inherit;
  text-indent: 0;
}

button,
input,
optgroup,
select,
textarea {
  color: inherit;
  font-family: inherit;
  font-feature-settings: inherit;
  font-size: 100%;
  font-variation-settings: inherit;
  font-weight: inherit;
  letter-spacing: inherit;
  line-height: inherit;
  margin: 0;
  padding: 0;
}

button,
select {
  text-transform: none;
}

button,
input:where([type="button"]),
input:where([type="reset"]),
input:where([type="submit"]) {
  appearance: button;
  -webkit-appearance: button;
  background-color: transparent;
  background-image: none;
}

:-moz-focusring {
  outline: auto;
}

:-moz-ui-invalid {
  box-shadow: none;
}

progress {
  vertical-align: baseline;
}

::-webkit-inner-spin-button,
::-webkit-outer-spin-button {
  height: auto;
}

[type="search"] {
  appearance: textfield;
  -webkit-appearance: textfield;
  outline-offset: -2px;
}

::-webkit-search-decoration {
  -webkit-appearance: none;
}

::-webkit-file-upload-button {
  appearance: button;
  -webkit-appearance: button;
  font: inherit;
}

summary {
  display: list-item;
}

blockquote,
dd,
dl,
figure,
h1,
h2,
h3,
h4,
h5,
h6,
hr,
p,
pre {
  margin: 0;
}

fieldset {
  margin: 0;
}

fieldset,
legend {
  padding: 0;
}

menu,
ol,
ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

dialog {
  padding: 0;
}

textarea {
  resize: vertical;
}

input::placeholder,
textarea::placeholder {
  color: #9ca3af;
  opacity: 1;
}

[role="button"],
button {
  cursor: pointer;
}

:disabled {
  cursor: default;
}

audio,
canvas,
embed,
iframe,
img,
object,
svg,
video {
  display: block;
}

img,
video {
  height: auto;
  max-width: 100%;
}

[hidden]:where(:not([hidden="until-found"])) {
  display: none;
}

.power-gradient-2 {
  background-image: linear-gradient(120deg, #A47451, #9c9881, #73a09d, #3b899a, #095b79, #002847, #000116);
}

#app .absolute {
  position: absolute;
}

#app .relative {
  position: relative;
}

#app .inset-0 {
  inset: 0;
}

#app .-bottom-10 {
  bottom: -40px;
}

#app .bottom-20 {
  bottom: 80px;
}

#app .left-10 {
  left: 40px;
}

#app .left-\[30\%\] {
  left: 30%;
}

#app .right-10 {
  right: 40px;
}

#app .right-\[20\%\] {
  right: 20%;
}

#app .top-20 {
  top: 80px;
}

#app .top-\[40\%\] {
  top: 40%;
}

#app .z-10 {
  z-index: 10;
}

#app .mx-auto {
  margin-left: auto;
  margin-right: auto;
}

#app .mb-16 {
  margin-bottom: 64px;
}

#app .mb-20 {
  margin-bottom: 80px;
}

#app .mb-4 {
  margin-bottom: 16px;
}

#app .mb-6 {
  margin-bottom: 24px;
}

#app .mb-8 {
  margin-bottom: 32px;
}

#app .ml-1 {
  margin-left: 4px;
}

#app .mt-10 {
  margin-top: 40px;
}

#app .mt-4 {
  margin-top: 16px;
}

#app .flex {
  display: flex;
}

#app .grid {
  display: grid;
}

#app .h-16 {
  height: 64px;
}

#app .h-40 {
  height: 160px;
}

#app .h-60 {
  height: 240px;
}

#app .h-80 {
  height: 320px;
}

#app .h-96 {
  height: 384px;
}

#app .min-h-screen {
  min-height: 100vh;
}

#app .w-16 {
  width: 64px;
}

#app .w-40 {
  width: 160px;
}

#app .w-60 {
  width: 240px;
}

#app .w-80 {
  width: 320px;
}

#app .w-96 {
  width: 384px;
}

#app .max-w-3xl {
  max-width: 48rem;
}

#app .max-w-7xl {
  max-width: 80rem;
}

@keyframes pulse {
  50% {
    opacity: 0.5;
  }
}

#app .animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

#app .grid-cols-1 {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

#app .flex-row {
  flex-direction: row;
}

#app .items-center {
  align-items: center;
}

#app .justify-center {
  justify-content: center;
}

#app .justify-between {
  justify-content: space-between;
}

#app .gap-4 {
  gap: 16px;
}

#app .gap-8 {
  gap: 32px;
}

#app .overflow-hidden {
  overflow: hidden;
}

#app .rounded-2xl {
  border-radius: 48px;
}

#app .rounded-full {
  border-radius: 9999px;
}

#app .border {
  border-width: 1px;
}

#app .border-white\/10 {
  border-color: hsla(0, 0%, 100%, 0.1);
}

#app .bg-orange-500\/10 {
  background-color: rgba(249, 115, 22, 0.1);
}

#app .bg-orange-500\/20 {
  background-color: rgba(249, 115, 22, 0.2);
}

#app .bg-cyan-500\/10 {
  background-color: rgba(6, 182, 212, 0.1);
}

#app .bg-cyan-500\/20 {
  background-color: rgba(6, 182, 212, 0.2);
}

#app .bg-indigo-500\/10 {
  background-color: rgba(99, 102, 241, 0.1);
}

#app .bg-indigo-500\/20 {
  background-color: rgba(99, 102, 241, 0.2);
}

#app .bg-sky-500\/20 {
  background-color: rgba(14, 165, 233, 0.2);
}

#app .bg-teal-500\/10 {
  background-color: rgba(20, 184, 166, 0.1);
}

#app .bg-teal-500\/20 {
  background-color: rgba(20, 184, 166, 0.2);
}

#app .bg-white\/10 {
  background-color: hsla(0, 0%, 100%, 0.1);
}

#app .bg-white\/5 {
  background-color: hsla(0, 0%, 100%, 0.05);
}

#app .bg-gradient-to-br {
  background-image: linear-gradient(to bottom right, var(--tw-gradient-stops));
}


#app .from-gray-900 {
  --tw-gradient-from: #111827 var(--tw-gradient-from-position);
  --tw-gradient-to: rgba(17, 24, 39, 0) var(--tw-gradient-to-position);
  --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to);
}

#app .via-orange-950 {
  --tw-gradient-to: rgba(67, 20, 7, 0) var(--tw-gradient-to-position);
  --tw-gradient-stops: var(--tw-gradient-from), #431407 var(--tw-gradient-via-position), var(--tw-gradient-to);
}


#app .to-indigo-900 {
  --tw-gradient-to: #312e81 var(--tw-gradient-to-position);
}

#app .bg-clip-text {
  background-clip: text;
}

#app .p-3 {
  padding: 12px;
}

#app .p-6 {
  padding: 24px;
}

#app .p-8 {
  padding: 32px;
}

#app .text-center {
  text-align: center;
}

#app .font-sans {
  font-family:
    Open Sans,
    ui-sans-serif,
    system-ui,
    sans-serif,
    Apple Color Emoji,
    Segoe UI Emoji,
    Segoe UI Symbol,
    Noto Color Emoji;
}

#app .text-2xl {
  font-size: 24px;
  line-height: 31.200000000000003px;
}

#app .text-3xl {
  font-size: 30px;
  line-height: 36px;
}

#app .text-4xl {
  font-size: 36px;
  line-height: 41.4px;
}

#app .text-lg {
  font-size: 18px;
  line-height: 27px;
}

#app .text-sm {
  font-size: 14px;
  line-height: 21px;
}

#app .font-bold {
  font-weight: 700;
}

#app .font-light {
  font-weight: 300;
}

#app .font-semibold {
  font-weight: 600;
}

#app .leading-relaxed {
  line-height: 1.625;
}

#app .tracking-tight {
  letter-spacing: -0.025em;
}

#app .text-orange-300 {
  --tw-text-opacity: 1;
  color: rgb(253 186 116 / var(--tw-text-opacity, 1));
}

#app .text-orange-400 {
  --tw-text-opacity: 1;
  color: rgb(251 146 60 / var(--tw-text-opacity, 1));
}

#app .text-cyan-400 {
  --tw-text-opacity: 1;
  color: rgb(34 211 238 / var(--tw-text-opacity, 1));
}

#app .text-gray-300 {
  --tw-text-opacity: 1;
  color: rgb(209 213 219 / var(--tw-text-opacity, 1));
}

#app .text-indigo-400 {
  --tw-text-opacity: 1;
  color: rgb(129 140 248 / var(--tw-text-opacity, 1));
}

#app .text-sky-400 {
  --tw-text-opacity: 1;
  color: rgb(56 189 248 / var(--tw-text-opacity, 1));
}

#app .text-teal-400 {
  --tw-text-opacity: 1;
  color: rgb(45 212 191 / var(--tw-text-opacity, 1));
}

#app .text-transparent {
  color: transparent;
}

#app .text-white {
  --tw-text-opacity: 1;
  color: rgb(255 255 255 / var(--tw-text-opacity, 1));
}

#app .shadow-lg {
  --tw-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
  --tw-shadow-colored: 0 10px 15px -3px var(--tw-shadow-color), 0 4px 6px -4px var(--tw-shadow-color);
  box-shadow: var(--tw-ring-offset-shadow, 0 0 #0000), var(--tw-ring-shadow, 0 0 #0000), var(--tw-shadow);
}

#app .blur-3xl {
  --tw-blur: blur(64px);
}

#app .blur-3xl,
#app .drop-shadow-lg {
  filter: var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow);
}

#app .drop-shadow-lg {
  --tw-drop-shadow: drop-shadow(0 10px 8px rgba(0, 0, 0, 0.04)) drop-shadow(0 4px 3px rgba(0, 0, 0, 0.1));
}

#app .backdrop-blur-\[3px\] {
  --tw-backdrop-blur: blur(3px);
}

#app .backdrop-blur-\[3px\],
#app .backdrop-blur-md {
  -webkit-backdrop-filter: var(--tw-backdrop-blur) var(--tw-backdrop-brightness) var(--tw-backdrop-contrast) var(--tw-backdrop-grayscale) var(--tw-backdrop-hue-rotate) var(--tw-backdrop-invert) var(--tw-backdrop-opacity) var(--tw-backdrop-saturate) var(--tw-backdrop-sepia);
  backdrop-filter: var(--tw-backdrop-blur) var(--tw-backdrop-brightness) var(--tw-backdrop-contrast) var(--tw-backdrop-grayscale) var(--tw-backdrop-hue-rotate) var(--tw-backdrop-invert) var(--tw-backdrop-opacity) var(--tw-backdrop-saturate) var(--tw-backdrop-sepia);
}

#app .backdrop-blur-md {
  --tw-backdrop-blur: blur(12px);
}

#app .transition-all {
  transition-duration: 0.15s;
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}

#app .transition-transform {
  transition-duration: 0.15s;
  transition-property: transform;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}

#app .duration-300 {
  transition-duration: 0.3s;
}

#app {
  font-family: Open Sans !important;
  font-size: 16px !important;
}

#app .hover\:translate-y-\[-5px\]:hover {
  --tw-translate-y: -5px;
  transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
}

#app .hover\:bg-white\/20:hover {
  background-color: hsla(0, 0%, 100%, 0.2);
}

#app .hover\:text-orange-300:hover {
  --tw-text-opacity: 1;
  color: rgb(253 186 116 / var(--tw-text-opacity, 1));
}

#app .hover\:text-cyan-300:hover {
  --tw-text-opacity: 1;
  color: rgb(103 232 249 / var(--tw-text-opacity, 1));
}

#app .hover\:text-indigo-300:hover {
  --tw-text-opacity: 1;
  color: rgb(165 180 252 / var(--tw-text-opacity, 1));
}

#app .hover\:text-sky-300:hover {
  --tw-text-opacity: 1;
  color: rgb(125 211 252 / var(--tw-text-opacity, 1));
}

#app .hover\:text-teal-300:hover {
  --tw-text-opacity: 1;
  color: rgb(94 234 212 / var(--tw-text-opacity, 1));
}

#app .hover\:shadow-orange-500\/20:hover {
  --tw-shadow-color: rgba(249, 115, 22, 0.2);
  --tw-shadow: var(--tw-shadow-colored);
}

#app .hover\:shadow-cyan-500\/20:hover {
  --tw-shadow-color: rgba(6, 182, 212, 0.2);
  --tw-shadow: var(--tw-shadow-colored);
}

#app .hover\:shadow-indigo-500\/20:hover {
  --tw-shadow-color: rgba(99, 102, 241, 0.2);
  --tw-shadow: var(--tw-shadow-colored);
}

#app .hover\:shadow-sky-500\/20:hover {
  --tw-shadow-color: rgba(14, 165, 233, 0.2);
  --tw-shadow: var(--tw-shadow-colored);
}

#app .hover\:shadow-teal-500\/20:hover {
  --tw-shadow-color: rgba(20, 184, 166, 0.2);
  --tw-shadow: var(--tw-shadow-colored);
}

#app :is(.group:hover .group-hover\:translate-x-1) {
  --tw-translate-x: 4px;
  transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
}

#app :is(.group:hover .group-hover\:rotate-45) {
  --tw-rotate: 45deg;
  transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
}

#app :is(.group:hover .group-hover\:bg-orange-500\/30) {
  background-color: rgba(249, 115, 22, 0.3);
}

#app :is(.group:hover .group-hover\:bg-cyan-500\/30) {
  background-color: rgba(6, 182, 212, 0.3);
}

#app :is(.group:hover .group-hover\:bg-indigo-500\/30) {
  background-color: rgba(99, 102, 241, 0.3);
}

#app :is(.group:hover .group-hover\:bg-sky-500\/30) {
  background-color: rgba(14, 165, 233, 0.3);
}

#app :is(.group:hover .group-hover\:bg-teal-500\/30) {
  background-color: rgba(20, 184, 166, 0.3);
}

@media (min-width: 768px) {
  #app .md\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  #app .md\:text-4xl {
    font-size: 36px;
    line-height: 41.4px;
  }

  #app .md\:text-5xl {
    font-size: 48px;
    line-height: 52.800000000000004px;
  }

  #app .md\:text-xl {
    font-size: 20px;
    line-height: 28px;
  }
}

@media (min-width: 1024px) {
  #app .lg\:grid-cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  #app .lg\:text-7xl {
    font-size: 72px;
    line-height: 75.60000000000001px;
  }
}
</style>

<style>
/* Custom scrollbar for model modal */
.glass-modal-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.6) rgba(255, 255, 255, 0.1);
}

.glass-modal-scroll::-webkit-scrollbar {
  width: 10px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
}

.glass-modal-scroll::-webkit-scrollbar-thumb {
  background: linear-gradient(120deg, rgba(99, 102, 241, 0.85) 60%, rgba(139, 92, 246, 0.85) 100%);
  border-radius: 8px;
  min-height: 40px;
}

.glass-modal-scroll::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(120deg, rgba(99, 102, 241, 1) 80%, rgba(139, 92, 246, 1) 100%);
}
</style>


<script>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue';
import { themeState } from '@/global/theme';
import LoaderOverlay from './components/LoaderOverlay.vue';
import { loaderState } from './global/loader';
import ResearchAssistant from './components/ResearchAssistant.vue';
import Translator from './components/Translator.vue';
import BeginnerTeacher from './components/BeginnerTeacher.vue';
import HomeworkHelper from './components/HomeworkHelper.vue';
import DailyLife from './components/DailyLife.vue';
import MemoryManager from './components/MemoryManager.vue';

export default {
  name: 'App',
  components: { ResearchAssistant, Translator, BeginnerTeacher, HomeworkHelper, DailyLife, MemoryManager, LoaderOverlay },
  setup() {
    const darkMode = ref(false);
    const showResearchAssistant = ref(false);
    const showTranslator = ref(false);
    const showBeginnerTeacher = ref(false);
    const showHomeworkHelper = ref(false);
    const showDailyLife = ref(false);
    const showMemoryManager = ref(false);
    const health = ref({});
    const showHealthModal = ref(false);
    const showMobileActions = ref(false);
    const showInToolMobileActions = ref(false);
  // Reactive viewport tracking for mobile-only UI (matches Tailwind md breakpoint 768px)
  const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);
  function handleViewportResize() { viewportWidth.value = window.innerWidth || viewportWidth.value; }
  const isMobile = computed(() => viewportWidth.value < 768);
    // LAN live server
    const showLanModal = ref(false);
    const lanInfo = ref({ urls: [] });
    let lanPingTimer = null;
    // Model selector state
    const backendModel = ref('');
    const installedModels = ref([]);
    const recommendedModels = ref([]);
    const selectedModel = ref(localStorage.getItem('selectedModel') || 'auto');
    const showModelModal = ref(false);
    const showInstallConfirm = ref(false);
    const installingModel = ref(null);
    const installCommand = ref('');

    // Carousel state
    const features = ref([
      {
        id: 'research',
        title: 'Research Assistant',
        desc: 'Get accurate, fact-checked insights and summaries for projects, papers, or deep dives.',
        icon: 'psychology_alt',
        iconBg: 'bg-orange-500/20',
        action: () => { showResearchAssistant.value = true; }
      },
      {
        id: 'translator',
        title: 'Translator',
        desc: 'Break language barriers with natural translations and cultural context for better understanding.',
        icon: 'translate',
        iconBg: 'bg-cyan-500/20',
        action: () => { showTranslator.value = true; }
      },
      {
        id: 'beginner',
        title: 'Beginner-Friendly Teacher',
        desc: 'Step-by-step explanations in easy language, making tough topics simple to learn.',
        icon: 'school',
        iconBg: 'bg-orange-500/20',
        action: () => { showBeginnerTeacher.value = true; }
      },
      {
        id: 'homework',
        title: 'Homework Helper',
        desc: 'Clear solutions and guidance to tackle assignments faster and smarter.',
        icon: 'edit_document',
        iconBg: 'bg-teal-500/20',
        action: () => { showHomeworkHelper.value = true; }
      },
      {
        id: 'daily',
        title: 'Daily Life Companion',
        desc: 'Plan, organize, and chat with AI that adapts to your routines and needs.',
        icon: 'chat',
        iconBg: 'bg-sky-500/20',
        action: () => { showDailyLife.value = true; }
      },
      {
        id: 'memory',
        title: 'Memory Manager',
        desc: 'Save notes, tags, and context so the AI always remembers — and recalls when you need it.',
        icon: 'auto_awesome',
        iconBg: 'bg-indigo-500/20',
        action: () => { showMemoryManager.value = true; }
      }
    ]);
    const currentIndex = ref(0); // logical index within original features
    const visibleCount = ref(3);
    // Infinite loop helpers
    const transitionEnabled = ref(true);
    const loopDurationMs = 1400; // slower, smoother
    const autoplayMs = 4500; // longer dwell time
    // Build extended list: [last N clones] + original + [first N clones]
    const extendedFeatures = computed(() => {
      const n = visibleCount.value;
      const list = features.value;
      if (!list.length) return [];
      const head = list.slice(0, n);
      const tail = list.slice(-n);
      return [...tail, ...list, ...head];
    });
    // The track uses a virtual index that starts offset by visibleCount to show the first real slide
    const virtualIndex = ref(visibleCount.value);
    let autoplayId = null;

    function updateVisibleCount() {
      const w = window.innerWidth || 0;
      if (w < 768) {
        visibleCount.value = 1;
      } else if (w < 1024) {
        visibleCount.value = 2;
      } else {
        visibleCount.value = 3;
      }
      // Recompute virtual index to keep alignment at the matching logical slide
      nextTickAlign();
    }

    function nextSlide() {
      // forward only
      transitionEnabled.value = true;
      virtualIndex.value += 1;
      currentIndex.value = (currentIndex.value + 1) % features.value.length;
    }

    function prevSlide() {
      // still allow user to go backward via button, but we won't auto use it
      transitionEnabled.value = true;
      virtualIndex.value -= 1;
      currentIndex.value = (currentIndex.value - 1 + features.value.length) % features.value.length;
    }

    // Touch swipe handling
    const swipeStartX = ref(0);
    const swipeStartTime = ref(0);
    const swipeActive = ref(false);
    const swipeDeltaX = ref(0);
    const swipeVelocity = ref(0);
    const swipeThreshold = 40; // px distance
    const velocityThreshold = 0.35; // px per ms
    function onTouchStart(e) {
      if (e.touches && e.touches.length === 1) {
        swipeStartX.value = e.touches[0].clientX;
        swipeStartTime.value = performance.now();
        swipeActive.value = true;
        swipeDeltaX.value = 0;
        pauseAutoplay();
      }
    }
    function onTouchMove(e) {
      if (!swipeActive.value || !e.touches || e.touches.length !== 1) return;
      swipeDeltaX.value = e.touches[0].clientX - swipeStartX.value;
    }
    function onTouchEnd() {
      if (!swipeActive.value) return;
      const dx = swipeDeltaX.value;
      const dt = Math.max(1, performance.now() - swipeStartTime.value);
      swipeVelocity.value = dx / dt; // px/ms
      const effectiveThreshold = Math.abs(dx) > swipeThreshold || Math.abs(swipeVelocity.value) > velocityThreshold;
      if (effectiveThreshold) {
        if (dx > 0) prevSlide(); else nextSlide();
      }
      swipeActive.value = false;
      swipeDeltaX.value = 0;
      resumeAutoplay();
    }

    function startAutoplay() {
      stopAutoplay();
      autoplayId = setInterval(() => {
        nextSlide();
      }, autoplayMs);
    }

    function stopAutoplay() {
      if (autoplayId) {
        clearInterval(autoplayId);
        autoplayId = null;
      }
    }

    function pauseAutoplay() { stopAutoplay(); }
    function resumeAutoplay() { startAutoplay(); }

    const trackComputedStyle = computed(() => {
      // Each step is 100/visibleCount percent
      const shift = virtualIndex.value * (100 / visibleCount.value);
      return {
        transform: `translate3d(-${shift}%, 0, 0)`,
        willChange: 'transform',
        transitionDuration: transitionEnabled.value ? `${loopDurationMs}ms` : '0ms'
      };
    });

    function onTransitionEnd() {
      const n = visibleCount.value;
      const total = features.value.length;
      // If we've moved into the trailing clones, snap back to the first real slide
      if (virtualIndex.value >= total + n) {
        transitionEnabled.value = false;
        virtualIndex.value = n; // first real slide
        // next tick re-enable transitions so future moves animate
        requestAnimationFrame(() => { transitionEnabled.value = true; });
      }
      // If we've moved into the leading clones (by manual prev), snap to last real slide window
      if (virtualIndex.value < n) {
        transitionEnabled.value = false;
        virtualIndex.value = total + n - 1;
        requestAnimationFrame(() => { transitionEnabled.value = true; });
      }
    }

    function nextTickAlign() {
      // Align virtualIndex so that the logical currentIndex is shown right after the leading clones
      const n = visibleCount.value;
      transitionEnabled.value = false;
      virtualIndex.value = n + currentIndex.value;
      requestAnimationFrame(() => { transitionEnabled.value = true; });
    }

    function humanizeBytes(n) {
      if (n === undefined || n === null || n === 0) return '—';
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let i = 0; let v = Number(n);
      while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
      return `${v.toFixed(1)} ${units[i]}`;
    }

    const API_BASE = typeof window !== 'undefined' ? window.location.origin : '';

    async function fetchOllamaModels() {
      try {
        const res = await fetch(`${API_BASE}/api/ollama/models`);
        if (!res.ok) throw new Error('Backend models endpoint failed');
        const data = await res.json();
        backendModel.value = data.current_model || '';
        installedModels.value = (data.installed || []).map(x => ({ name: x.name, size: x.size }));
        recommendedModels.value = data.recommended || [];
      } catch (err) {
        console.warn('Failed to fetch models from backend', err);
        backendModel.value = '';
        installedModels.value = [];
        recommendedModels.value = [];
      }
    }

    async function refreshHealth() {
      try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
          health.value = await res.json();
        }
      } catch {
        // leave health stale
      }
    }
    const ocrAnyRenderer = computed(() => {
      const r = health.value.ocr_renderers || {};
      return !!(r.poppler || r.pymupdf || r.pypdfium2);
    });
    const ocrRendererSummary = computed(() => {
      const r = health.value.ocr_renderers || {};
      const list = [];
      if (r.pymupdf) list.push('PyMuPDF');
      if (r.pypdfium2) list.push('PDFium');
      if (r.poppler) list.push('Poppler');
      if (!list.length) return 'No renderer';
      return list.join(', ');
    });
    const preferredRendererLabel = computed(() => {
      const r = health.value.ocr_renderers || {};
      if (r.pymupdf) return 'PyMuPDF';
      if (r.pypdfium2) return 'PDFium';
      if (r.poppler) return 'Poppler';
      return 'none';
    });
    function openHealthModal() { showHealthModal.value = true; refreshHealth(); }
    function openLanModal() { showLanModal.value = true; fetchLanInfo(); }

    function openModelModal() {
      showModelModal.value = true;
      fetchOllamaModels();
    }

    function prepareInstall(m) {
      installingModel.value = m;
      // create a typical Ollama install command using PowerShell
      installCommand.value = `# Run in Windows PowerShell\nollama pull ${m.name}`;
      showInstallConfirm.value = true;
    }

    function cancelInstall() {
      installingModel.value = null;
      installCommand.value = '';
      showInstallConfirm.value = false;
    }

    function copyCommandToClipboard() {
      if (!installCommand.value) return;
      navigator.clipboard.writeText(installCommand.value).then(() => alert('Command copied to clipboard'));
    }

    async function executeInstall() {
      if (!installingModel.value) return;
      try {
        const res = await fetch(`${API_BASE}/api/ollama/install`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: installingModel.value.name })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          alert('Install failed: ' + (data.error || data.stderr || 'unknown error'));
        } else {
          alert('Model installed. Refreshing list...');
          await fetchOllamaModels();
        }
      } catch (e) {
        alert('Install error: ' + (e && e.message));
      } finally {
        showInstallConfirm.value = false;
      }
    }

    async function fetchLanInfo() {
      try {
        const res = await fetch(`${API_BASE}/api/network/laninfo`);
        if (res.ok) {
          lanInfo.value = await res.json();
        }
      } catch (e) {
        console.warn('LAN info fetch failed', e);
      }
    }
    async function enableLive() {
      try { await fetch(`${API_BASE}/api/network/live/enable`, { method: 'POST' }); } catch { /* ignore */ }
      fetchLanInfo();
    }
    async function disableLive() {
      try { await fetch(`${API_BASE}/api/network/live/disable`, { method: 'POST' }); } catch { /* ignore */ }
      fetchLanInfo();
    }
    function startLanPingLoop() {
      stopLanPingLoop();
      const ping = async () => {
        try { await fetch(`${API_BASE}/api/network/ping`); } catch { /* ignore */ }
      };
      ping();
      lanPingTimer = setInterval(() => { ping(); fetchLanInfo(); }, 20000);
    }
    function stopLanPingLoop() {
      if (lanPingTimer) { clearInterval(lanPingTimer); lanPingTimer = null; }
    }
    function copyText(t) {
      if (!t) return;
      navigator.clipboard.writeText(t).then(() => {
      });
    }

    async function setBackendModel(name) {
      try {
        const res = await fetch(`${API_BASE}/api/model`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: name })
        });
        const data = await res.json();
        if (!res.ok || data.error) throw new Error(data.error || 'Failed to set model');
        backendModel.value = name;
        selectedModel.value = name;
        localStorage.setItem('selectedModel', name);
        showModelModal.value = false;
      } catch (e) {
        alert('Failed to set backend model: ' + (e && e.message));
      }
    }

    onMounted(async () => {
      updateVisibleCount();
      window.addEventListener('resize', updateVisibleCount);
      window.addEventListener('resize', handleViewportResize);
      // initialize virtual index after first layout
      nextTickAlign();
      startAutoplay();
      try {
        const res = await fetch(`${API_BASE}/api/model`);
        if (res.ok) {
          const d = await res.json();
          backendModel.value = d.model || backendModel.value;
        }
      } catch (e) {
        console.warn('Failed to fetch backend model', e);
      }
      refreshHealth();
      fetchLanInfo();
      startLanPingLoop();
    });
    onBeforeUnmount(() => {
      window.removeEventListener('resize', updateVisibleCount);
      window.removeEventListener('resize', handleViewportResize);
      stopAutoplay();
    });
    function toggleDarkMode() {
      darkMode.value = !darkMode.value;
    }
    const isPower = themeState.isPower;

    // Orange glow: JS-driven bouncing motion near borders (avoids center)
    const orangeRef = ref(null);
    let rafId = null;
    let lastTs = 0;
    let x = 0, y = 0; // current translate in px
    let vx = 30, vy = 24; // px per second (slower)
    let maxX = 0, maxY = 0; // bounds based on viewport and element size
    let innerMinX = 0, innerMaxX = 0, innerMinY = 0, innerMaxY = 0; // center forbidden rect
    let reducedMotion = false;

    function computeBounds() {
      const w = window.innerWidth || 0;
      const h = window.innerHeight || 0;
      const el = orangeRef.value;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const ew = rect.width || Math.min(Math.max(w * 0.48, 520), 780);
      const eh = rect.height || Math.min(Math.max(h * 0.48, 520), 780);
      maxX = Math.max(0, w - ew);
      maxY = Math.max(0, h - eh);
      // Define a band near edges: inner rectangle at ~28% from each side
      const bandX = Math.max(40, Math.floor(w * 0.28));
      const bandY = Math.max(40, Math.floor(h * 0.28));
      innerMinX = bandX;
      innerMaxX = Math.max(innerMinX, w - bandX - ew);
      innerMinY = bandY;
      innerMaxY = Math.max(innerMinY, h - bandY - eh);
      // Clamp current position
      x = Math.min(Math.max(x, 0), maxX);
      y = Math.min(Math.max(y, 0), maxY);
    }

    function setTransform() {
      const el = orangeRef.value;
      if (!el) return;
      el.style.transform = `translate(${x}px, ${y}px) scale(1.02)`;
    }

    function step(ts) {
      if (lastTs === 0) lastTs = ts;
      const dt = Math.min(0.05, (ts - lastTs) / 1000); // cap to avoid jumps
      lastTs = ts;
      x += vx * dt;
      y += vy * dt;
      // Outer bounces
      if (x <= 0) { x = 0; vx = Math.abs(vx); }
      else if (x >= maxX) { x = maxX; vx = -Math.abs(vx); }
      if (y <= 0) { y = 0; vy = Math.abs(vy); }
      else if (y >= maxY) { y = maxY; vy = -Math.abs(vy); }
      // Center avoidance: bounce off inner rectangle boundaries
      const insideInnerX = x > innerMinX && x < innerMaxX;
      const insideInnerY = y > innerMinY && y < innerMaxY;
      if (insideInnerX && insideInnerY) {
        const dx = Math.min(x - innerMinX, innerMaxX - x);
        const dy = Math.min(y - innerMinY, innerMaxY - y);
        if (dx < dy) {
          vx = -vx; x += (x < (innerMinX + innerMaxX) / 2 ? -6 : 6);
        } else {
          vy = -vy; y += (y < (innerMinY + innerMaxY) / 2 ? -6 : 6);
        }
      }
      setTransform();
      rafId = requestAnimationFrame(step);
    }

    function startOrangeMotion() {
      if (rafId) return;
      const media = window.matchMedia('(prefers-reduced-motion: reduce)');
      reducedMotion = media.matches;
      if (reducedMotion) return;
      const w = window.innerWidth || 0;
      const h = window.innerHeight || 0;
      x = Math.max(0, Math.floor(w * 0.05));
      y = Math.max(0, Math.floor(h * 0.12));
      // Randomize initial direction within a slow range
      vx = (Math.random() > 0.5 ? 1 : -1) * (22 + Math.random() * 12); // 22-34 px/s
      vy = (Math.random() > 0.5 ? 1 : -1) * (18 + Math.random() * 10); // 18-28 px/s
      computeBounds();
      setTransform();
      lastTs = 0;
      rafId = requestAnimationFrame(step);
    }

    function stopOrangeMotion() {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    }

    function toggleMobileActions() {
      showMobileActions.value = !showMobileActions.value;
    }
    function toggleInToolMobileActions() {
      showInToolMobileActions.value = !showInToolMobileActions.value;
    }

    watch(isPower, (now) => {
      if (now) {
        stopOrangeMotion();
      } else {
        startOrangeMotion();
      }
    });

    return {
      // theme & mode
      darkMode, toggleDarkMode, themeState, isPower,
      // feature panels
      showResearchAssistant, showTranslator, showBeginnerTeacher, showHomeworkHelper, showDailyLife, showMemoryManager,
      // health
      health, refreshHealth, showHealthModal, openHealthModal,
      // models
      backendModel, installedModels, recommendedModels, selectedModel, showModelModal, openModelModal, fetchOllamaModels, prepareInstall, showInstallConfirm, installingModel, installCommand, copyCommandToClipboard, executeInstall, setBackendModel, cancelInstall, humanizeBytes,
      // carousel
      features, visibleCount, nextSlide, prevSlide, pauseAutoplay, resumeAutoplay, extendedFeatures, trackComputedStyle, onTransitionEnd, transitionEnabled,
      // OCR renderer summaries
      ocrAnyRenderer, ocrRendererSummary, preferredRendererLabel,
      // LAN live server
      openLanModal, showLanModal, lanInfo, copyText, enableLive, disableLive,
      // mobile actions
      showMobileActions, toggleMobileActions, showInToolMobileActions, toggleInToolMobileActions,
  isMobile,
      // touch swipe
      onTouchStart, onTouchMove, onTouchEnd,
      // visuals
      loaderState, orangeRef,
    };
  },
};
</script>