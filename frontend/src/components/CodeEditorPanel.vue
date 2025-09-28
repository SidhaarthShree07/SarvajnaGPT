<template>
  <div :class="['flex flex-col h-full border-l', darkMode ? 'border-white/20 bg-white/5' : 'border-orange-300/30 bg-orange-50/40']">
    <div class="flex items-center justify-between px-3 py-2 border-b border-white/10">
      <h3 :class="['text-sm font-semibold tracking-wide flex items-center gap-2', darkMode ? 'text-white' : 'text-orange-600']">
        <span class="material-symbols-outlined text-base">code</span> Editor
      </h3>
      <div class="flex items-center gap-2">
        <button class="px-2 py-1 rounded text-xs bg-purple-600 text-white hover:bg-purple-500" @click="openAIPanel = !openAIPanel" :class="openAIPanel ? 'opacity-100' : 'opacity-80'">AI</button>
        <button class="px-2 py-1 rounded text-xs bg-slate-600 text-white hover:bg-slate-500" @click="openTerminal = !openTerminal" :class="openTerminal ? 'opacity-100' : 'opacity-80'">Term</button>
        <button class="px-2 py-1 rounded text-xs bg-green-600 text-white hover:bg-green-700" @click="saveFile" :disabled="saving || !path">
          <span class="material-symbols-outlined text-xs align-middle">save</span>
        </button>
        <button class="px-2 py-1 rounded text-xs bg-gray-500/60 text-white hover:bg-gray-600" @click="$emit('close')">
          <span class="material-symbols-outlined text-xs align-middle">close</span>
        </button>
      </div>
    </div>
    <div class="p-3 space-y-3 overflow-y-auto">
      <div class="flex items-center gap-2">
        <div class="flex-1 text-xs font-mono px-3 py-2 rounded border" :class="darkMode ? 'bg-white/5 text-white border-white/20' : 'bg-white text-gray-700 border-orange-300'">
          <span class="opacity-70">Path:</span> {{ path || '(inferring...)' }}
        </div>
        <select v-model="mode" class="rounded px-2 py-2 text-sm border" :class="darkMode ? 'bg-white/10 text-white border-white/20' : 'bg-white text-gray-700 border-orange-300'" title="Write replaces file; Append adds to end">
          <option value="write">Write</option>
          <option value="append">Append</option>
        </select>
        <button @click="previewChange" class="px-3 py-2 rounded text-xs bg-blue-600 text-white hover:bg-blue-500" :disabled="!path || previewing">
          Preview
        </button>
        <button @click="loadFile" class="px-3 py-2 rounded text-xs bg-indigo-600 text-white hover:bg-indigo-500" :disabled="!path || loading">
          Load
        </button>
        <button v-if="showHtmlPreviewButton" @click="$emit('preview-html', resolvedPath)" class="px-3 py-2 rounded text-xs bg-orange-500 text-white hover:bg-orange-400" :disabled="!resolvedPath">Live</button>
      </div>
      <div v-if="preview" class="text-xs font-mono bg-black/40 text-green-200 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap border border-white/10">
        <div class="opacity-70">Diff Preview</div>
        <pre class="text-[11px] leading-snug">{{ preview.diff_preview.join('\n') }}</pre>
      </div>
      <textarea v-model="content" :placeholder="path ? 'Edit content...' : 'Enter a path first'" class="w-full flex-1 min-h-[240px] rounded resize-y font-mono text-xs p-3 border focus:outline-none" :class="darkMode ? 'bg-white/5 text-white border-white/20 focus:border-orange-400' : 'bg-white text-gray-800 border-orange-300 focus:border-orange-500'" />
      <div class="flex items-center justify-between text-xs">
        <div :class="darkMode ? 'text-white/60' : 'text-gray-600'">{{ statusMessage }}</div>
        <div :class="darkMode ? 'text-white/50' : 'text-gray-500'">{{ content.length }} chars</div>
      </div>
      <!-- AI Edit Panel -->
      <div v-if="openAIPanel" class="mt-2 p-2 rounded border" :class="darkMode ? 'border-white/20 bg-white/5' : 'border-orange-200 bg-white/70'">
        <div class="text-xs font-semibold mb-1" :class="darkMode ? 'text-white/70' : 'text-gray-700'">AI Edit Instruction</div>
        <textarea v-model="aiInstruction" placeholder="Explain the change you want (e.g. convert function to async, add error handling)" class="w-full text-xs p-2 rounded border mb-2" :class="darkMode ? 'bg-white/10 text-white border-white/20' : 'bg-white text-gray-800 border-orange-300'"></textarea>
        <div class="flex gap-2">
          <button @click="runAIEdit(false)" class="px-3 py-1 rounded text-xs bg-purple-600 text-white hover:bg-purple-500" :disabled="aiBusy || !aiInstruction || !path">Preview</button>
          <button @click="runAIEdit(true)" class="px-3 py-1 rounded text-xs bg-green-600 text-white hover:bg-green-500" :disabled="aiBusy || !aiInstruction || !path">Apply</button>
          <div v-if="aiBusy" class="text-[11px] self-center" :class="darkMode ? 'text-white/60' : 'text-gray-600'">AI working...</div>
        </div>
        <div v-if="aiPreviewDiff.length" class="mt-2 max-h-40 overflow-auto text-[11px] font-mono whitespace-pre-wrap bg-black/40 text-green-200 p-2 rounded border border-white/10">
          <div class="opacity-70">AI Diff (first lines)</div>
          <pre>{{ aiPreviewDiff.join('\n') }}</pre>
        </div>
      </div>
      <!-- Terminal Panel -->
      <div v-if="openTerminal" class="mt-2 p-2 rounded border" :class="darkMode ? 'border-white/20 bg-white/5' : 'border-orange-200 bg-white/70'">
        <div class="text-xs font-semibold mb-1" :class="darkMode ? 'text-white/70' : 'text-gray-700'">Terminal (Allowlisted)</div>
        <form @submit.prevent="runCmd" class="flex gap-2 mb-2">
          <input v-model="terminalCmd" placeholder="e.g. python --version" class="flex-1 text-xs px-2 py-1 rounded border" :class="darkMode ? 'bg-white/10 text-white border-white/20' : 'bg-white text-gray-800 border-orange-300'" />
          <button class="px-3 py-1 rounded text-xs bg-slate-600 text-white hover:bg-slate-500" :disabled="terminalBusy">Run</button>
        </form>
        <div class="text-[11px] font-mono whitespace-pre overflow-auto max-h-48 rounded p-2" :class="darkMode ? 'bg-black/50 text-white/80' : 'bg-gray-900 text-green-200'">
          <div v-if="terminalBusy">Running...</div>
          <div v-else>
            <div v-if="terminalOut.stdout"><strong>stdout:</strong>\n{{ terminalOut.stdout }}</div>
            <div v-if="terminalOut.stderr" class="mt-2 text-red-400"><strong>stderr:</strong>\n{{ terminalOut.stderr }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed } from 'vue'
const props = defineProps({
  darkMode: { type: Boolean, default: false },
  initialPath: { type: String, default: '' },
  objective: { type: String, default: '' }
})
const emit = defineEmits(['close','preview-html'])
// touch refs so lint sees usage
void props; void emit;

const path = ref('')
const content = ref('')
const mode = ref('write')
const preview = ref(null)
const statusMessage = ref('')
const previewing = ref(false)
const saving = ref(false)
const loading = ref(false)
const openAIPanel = ref(false)
const openTerminal = ref(false)
const aiInstruction = ref('')
const aiBusy = ref(false)
const aiPreviewDiff = ref([])
const terminalCmd = ref('')
const terminalBusy = ref(false)
const terminalOut = ref({stdout:'', stderr:''})

const resolvedPath = computed(() => path.value)
const showHtmlPreviewButton = computed(() => resolvedPath.value && /\.html?$/i.test(resolvedPath.value))

async function previewChange() {
  if (!path.value) return
  previewing.value = true
  statusMessage.value = 'Previewing...'
  try {
    const res = await fetch('/api/code/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_rel: path.value, content: content.value, mode: mode.value }) })
    if (!res.ok) throw new Error(await res.text())
    preview.value = await res.json()
    statusMessage.value = 'Preview updated.'
  } catch {
    statusMessage.value = 'Preview failed.'
  } finally {
    previewing.value = false
  }
}

// Initialize from props (agentic) once
let initialized = false
function initFromProps() {
  if (initialized) return
  if (props.initialPath) {
    path.value = props.initialPath
    if (!content.value && props.objective) {
      // Provide a scaffold header comment based on file type
      const lower = props.initialPath.toLowerCase()
      const commentStyle = lower.endsWith('.py') ? '#' : lower.endsWith('.js') ? '//' : lower.endsWith('.ts') ? '//' : lower.endsWith('.html') ? '<!--' : '#'
      let header = ''
      if (commentStyle === '<!--') {
        header = `<!-- Objective: ${props.objective} -->\n`;
      } else {
        header = `${commentStyle} Objective: ${props.objective}\n\n`
      }
      content.value = header
      statusMessage.value = 'Initialized from objective'
    }
    initialized = true
  }
}

initFromProps()

async function saveFile() {
  if (!path.value) return
  saving.value = true
  statusMessage.value = 'Saving...'
  try {
    const res = await fetch('/api/code/execute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_rel: path.value, content: content.value, mode: mode.value }) })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    statusMessage.value = 'Saved: ' + data.path
  } catch {
    statusMessage.value = 'Save failed.'
  } finally {
    saving.value = false
  }
}

async function loadFile() {
  if (!path.value) return
  loading.value = true
  statusMessage.value = 'Loading file...'
  try {
    const res = await fetch('/api/code/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_rel: path.value, max_bytes: 200000 }) })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    content.value = data.content
    statusMessage.value = data.truncated ? 'Loaded (truncated)' : 'Loaded.'
  } catch {
    statusMessage.value = 'Load failed.'
  } finally {
    loading.value = false
  }
}

async function runAIEdit(apply) {
  if (!path.value || !aiInstruction.value) return
  aiBusy.value = true
  aiPreviewDiff.value = []
  try {
    const res = await fetch('/api/code/ai_edit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_rel: path.value, instruction: aiInstruction.value, apply }) })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    if (!apply && data.updated_content) {
      content.value = data.updated_content
    }
    aiPreviewDiff.value = data.diff || []
    statusMessage.value = apply ? 'AI changes applied.' : 'AI preview loaded (content replaced locally).'
  } catch {
    statusMessage.value = 'AI edit failed.'
  } finally {
    aiBusy.value = false
  }
}

async function runCmd() {
  if (!terminalCmd.value) return
  terminalBusy.value = true
  terminalOut.value = {stdout:'', stderr:''}
  try {
    const res = await fetch('/api/code/terminal', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cmd: terminalCmd.value, cwd: path.value ? path.value.replace(/\\[^\\/]*$/, '') : '.' }) })
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    terminalOut.value = data
  } catch {
    terminalOut.value = {stdout:'', stderr:'Command failed'}
  } finally {
    terminalBusy.value = false
  }
}
</script>
<style scoped>
textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
</style>
