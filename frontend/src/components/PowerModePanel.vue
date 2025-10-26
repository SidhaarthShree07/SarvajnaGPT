<template>
  <div class="w-full p-4 bg-white/70 rounded-xl border border-indigo-200/40">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-base font-semibold text-gray-800">Power Mode Actions (Offline)</h3>
      <button @click="refreshLogs" class="text-xs px-3 py-1 rounded-full bg-indigo-600 text-white hover:bg-indigo-700">Refresh Logs</button>
    </div>

    <!-- Simple action builder: create folder and write file under agent_output -->
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="p-3 bg-white rounded-lg border border-gray-200">
        <h4 class="text-sm font-bold text-gray-700 mb-2">Create Folder</h4>
        <label class="text-xs text-gray-500">Parent (relative or absolute under allowlist)</label>
        <input v-model="createFolder.parent_path" placeholder="projects" class="w-full text-sm px-3 py-2 border rounded mb-2"/>
        <label class="text-xs text-gray-500">Name</label>
        <input v-model="createFolder.name" placeholder="demo" class="w-full text-sm px-3 py-2 border rounded mb-3"/>
        <button @click="previewCreateFolder" class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Preview</button>
        <button v-if="pendingPreview && pendingPreview.action.type==='fs.create_folder'" @click="executePending" class="ml-2 text-xs px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700">Execute</button>
      </div>

      <div class="p-3 bg-white rounded-lg border border-gray-200">
        <h4 class="text-sm font-bold text-gray-700 mb-2">Write File</h4>
        <label class="text-xs text-gray-500">Relative path (e.g., projects/demo/README.md)</label>
        <input v-model="writeFile.relative_path" placeholder="projects/demo/README.md" class="w-full text-sm px-3 py-2 border rounded mb-2"/>
        <label class="text-xs text-gray-500">Encoding</label>
        <input v-model="writeFile.encoding" placeholder="utf-8" class="w-full text-sm px-3 py-2 border rounded mb-2"/>
        <label class="text-xs text-gray-500">Content</label>
        <textarea v-model="writeFile.content" rows="6" class="w-full text-sm px-3 py-2 border rounded font-mono" placeholder="# Hello\nThis is generated offline."></textarea>
        <div class="mt-2">
          <button @click="previewWriteFile" class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Preview</button>
          <button v-if="pendingPreview && pendingPreview.action.type==='fs.write_file'" @click="executePending" class="ml-2 text-xs px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700">Execute</button>
        </div>
      </div>

      <div class="p-3 bg-white rounded-lg border border-gray-200">
        <h4 class="text-sm font-bold text-gray-700 mb-2">Create Word (.docx)</h4>
        <label class="text-xs text-gray-500">Relative path</label>
        <input v-model="word.target_rel" placeholder="docs/demo.docx" class="w-full text-sm px-3 py-2 border rounded mb-2"/>
        <label class="text-xs text-gray-500">Paragraph</label>
        <textarea v-model="word.paragraph" rows="5" class="w-full text-sm px-3 py-2 border rounded" placeholder="Write your first paragraph here..."></textarea>
        <div class="mt-2">
          <button @click="previewWord" class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700">Preview</button>
          <button v-if="pendingPreview && pendingPreview.action===undefined && pendingPreview.target_rel===word.target_rel" @click="executeWord" class="ml-2 text-xs px-3 py-1 rounded bg-green-600 text-white hover:bg-green-700">Execute</button>
        </div>
      </div>
    </div>

    <div v-if="pendingPreview" class="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded">
      <div class="text-sm text-indigo-800">Preview: {{ pendingPreview.summary }}</div>
      <div class="text-xs text-gray-600">Target: {{ pendingPreview.target_path || pendingPreview.target_abs }}</div>
    </div>

    <div v-if="logs.entries && logs.entries.length" class="mt-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">Recent Activity</h4>
      <ul class="text-xs text-gray-700 max-h-40 overflow-auto space-y-1">
        <li v-for="(e, i) in logs.entries" :key="i">
          <span class="font-mono text-gray-500">{{ e.timestamp }}</span>
          — {{ e.summary }}
          <span v-if="e.error" class="text-red-600">(error: {{ e.error }})</span>
        </li>
      </ul>
      <div class="text-xs text-gray-500 mt-1">Base: {{ logs.base_dir }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const createFolder = ref({ parent_path: 'projects', name: 'demo' })
const writeFile = ref({ relative_path: 'projects/demo/README.md', content: '# Hello\nThis is generated offline.', encoding: 'utf-8' })
const pendingPreview = ref(null)
const logs = ref({ entries: [] })

// Derive backend base dynamically so it works over LAN / any host without edits
const API_BASE = typeof window !== 'undefined' ? window.location.origin : ''
const API = API_BASE + '/api/agent'
const WORD = API_BASE + '/api/word'

async function previewCreateFolder() {
  const action = {
    id: crypto.randomUUID(),
    type: 'fs.create_folder',
    params: { ...createFolder.value },
    preview_only: true,
  }
  const res = await fetch(`${API}/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(action) })
  if (!res.ok) throw new Error('Preview failed')
  pendingPreview.value = await res.json()
}

async function previewWriteFile() {
  const action = {
    id: crypto.randomUUID(),
    type: 'fs.write_file',
    params: { ...writeFile.value },
    preview_only: true,
  }
  const res = await fetch(`${API}/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(action) })
  if (!res.ok) throw new Error('Preview failed')
  pendingPreview.value = await res.json()
}

async function executePending() {
  if (!pendingPreview.value) return
  const a = pendingPreview.value.action
  const res = await fetch(`${API}/execute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify([a]) })
  if (!res.ok) throw new Error('Execute failed')
  const data = await res.json()
  pendingPreview.value = null
  await refreshLogs()
  return data
}

async function refreshLogs() {
  const res = await fetch(`${API}/logs`)
  if (res.ok) logs.value = await res.json()
}

refreshLogs()

// ---- Word helpers ----
const word = ref({ target_rel: 'docs/demo.docx', paragraph: 'Hello from Power Mode!' })

async function previewWord() {
  const res = await fetch(`${WORD}/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(word.value) })
  if (!res.ok) throw new Error('Word preview failed')
  pendingPreview.value = await res.json()
}

async function executeWord() {
  const res = await fetch(`${WORD}/execute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(word.value) })
  if (!res.ok) throw new Error('Word execute failed')
  const data = await res.json()
  pendingPreview.value = null
  await refreshLogs()
  return data
}
</script>

<style scoped>
</style>
