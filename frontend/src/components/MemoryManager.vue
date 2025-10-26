<template>
  <div
    class="frosted-glass-card w-full max-w-5xl mx-auto p-6 rounded-2xl border border-white/10 shadow-xl space-y-6 relative" style="margin-top: calc(var(--spacing) * 16);">
    <LoaderOverlay :show="isBusy" :text="busyText" />
    <!-- Toasts -->
    <div class="toast-container" aria-live="polite" aria-atomic="true">
      <div v-for="t in toasts" :key="t.id" :class="['toast', t.type === 'error' ? 'toast-error' : 'toast-success']">{{
        t.text }}</div>
    </div>
    <div class="flex justify-between items-center mb-4">
      <div class="flex items-center gap-3">
        <div :class="['rounded-full w-12 h-12 flex items-center justify-center', darkMode ? 'bg-white/6' : 'bg-orange-500/20']">
          <span :class="['material-symbols-outlined', darkMode ? 'text-white/90' : 'text-orange-400']">handshake</span>
        </div>
        <div>
          <h2 :class="['text-2xl font-bold', darkMode ? 'text-white' : 'text-orange-400']">Memory Manager</h2>
          <div :class="['text-sm', darkMode ? 'text-white/80' : 'text-black']">Organize notes, files, and tags. Add, rename, delete, and recall items.
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button :class="['box-btn', darkMode ? 'text-white/70' : 'text-black']" @click="emit('back')">Close</button>
      </div>
    </div>

  <div class="flex gap-4 flex-col lg:flex-row" style="margin-top: calc(var(--spacing) * 4)">
      <!-- Left: Folders -->
  <div class="w-full lg:w-1/3 bg-white/10 border border-white/10 rounded-xl p-5">
        <div :class="['text-xs uppercase tracking-wide', darkMode ? 'text-white/70' : 'text-orange-200']">Folders</div>
        <div class="flex gap-2 items-center flex-wrap" style="margin-top: calc(var(--spacing) * 4)">
          <input v-model="newFolderName" placeholder="New folder" class="box-textarea text-sm shrink-0" style="width: 100%;" />
          <input v-model="newFolderTag" placeholder="#tag" class="box-textarea text-sm shrink-0" style="width: 100%;" />
          <button :class="['box-btn text-sm cursor-pointer shrink-0',darkMode ? 'text-white/70' : 'text-black']" @click="createFolder" title="Create folder">
            Create
          </button>
        </div>
  <ul class="space-y-2 max-h-80 overflow-auto pr-1 glass-modal-scroll" v-if="folders && folders.length" style="margin-top: calc(var(--spacing) * 4); scrollbar-gutter: stable both-edges;">
          <li v-for="f in folders" :key="f.id"
            :class="['p-2 rounded-lg flex justify-between items-center transition-all group', selectedFolder && selectedFolder.id === f.id ? 'bg-white/15' : 'hover:bg-white/10']">
            <button class="flex items-center gap-3 text-left flex-1 cursor-pointer" @click="selectFolder(f)"
              title="Open folder">
              <span :class="['material-symbols-outlined group-hover:scale-105 transition', darkMode ? 'text-white/80' : 'text-orange-400']">folder</span>
              <div>
                <div :class="['font-medium', darkMode ? 'text-white' : 'text-orange-400']">{{ f.name }}</div>
                <div :class="['text-xs', darkMode ? 'text-white/70' : 'text-black']">{{ f.tag || '' }}</div>
              </div>
            </button>
            <div class="flex items-center gap-1 ml-2">
              <button class="p-2 rounded hover:bg-white/10 transition cursor-pointer" title="Rename"
                aria-label="Rename folder" @click.stop="openFolderRenameModal(f)"><span
                  :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-200']">edit</span></button>
              <button class="p-2 rounded hover:bg-white/10 transition cursor-pointer text-rose-300 hover:text-rose-200"
                title="Delete" aria-label="Delete folder" @click.stop="confirmDeleteFolder(f)"><span
                  class="material-symbols-outlined">delete</span></button>
            </div>
          </li>
        </ul>
        <div v-else :class="['text-sm bg-white/5 border border-white/10 rounded-lg p-3', darkMode ? 'text-white/70' : 'text-orange-200/80']" style="margin-top: calc(var(--spacing) * 4)">
          No folders yet. Create your first folder above to start organizing memories.
        </div>
      </div>

      <!-- Right: Items -->
  <div class="w-full lg:w-2/3 bg-white/10 border border-white/10 rounded-xl p-5">
        <div class="text-sm flex flex-wrap gap-3 items-center justify-between">
          <span :class="['uppercase tracking-wide', darkMode ? 'text-white/80' : 'text-black/90']">Items in folder</span>
          <div class="flex items-center gap-2 flex-wrap">
            <input type="file" ref="fileInput" class="hidden" @change="uploadFile" />
            <button :class="['box-btn box-btn-compact cursor-pointer',darkMode ? 'text-white/70' : 'text-black']" @click="$refs.fileInput.click()" title="Upload file"
              aria-label="Upload file"><span
                class="material-symbols-outlined mr-1 text-sm align-middle">upload_file</span>Upload</button>
            <button :class="['box-btn box-btn-compact cursor-pointer',darkMode ? 'text-white/70' : 'text-black']" @click="saveNote" title="Save note" aria-label="Save note"><span
                class="material-symbols-outlined mr-1 text-sm align-middle">note_add</span>Note</button>
          </div>
        </div>
        <div class="divider mt-3"></div>
          <div class="flex flex-wrap gap-3 items-center" style="margin-top: calc(var(--spacing) * 4)">
          <input v-model="newItemTag" placeholder="#tag (optional)" class="box-textarea text-sm w-48" />
          <input v-model="itemSearch" placeholder="Search items" class="box-textarea text-sm flex-1 min-w-[160px]" />
          <select v-model="itemSort" class="box-textarea text-sm w-36 md:w-40">
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="title">Title A–Z</option>
          </select>
      <div v-if="activeTagFilter" :class="['text-xs ml-auto', darkMode ? 'text-white/70' : 'text-orange-200']">Filtering by tag <span
        :class="['px-2 py-0.5 rounded-full', darkMode ? 'bg-white/6' : 'bg-orange-500/20']">#{{ activeTagFilter }}</span> <button
        class="underline ml-1" @click="activeTagFilter = ''">clear</button></div>
        </div>
  <div v-if="!selectedFolder" :class="['mt-4', darkMode ? 'text-white/70' : 'text-orange-200/70']">Select a folder to see items</div>
        <div v-else>
          <textarea v-model="newNoteText" rows="4" class="box-textarea" style="width: 100%;" placeholder="Write a note..."></textarea>
          <div class="divider mt-3"></div>

          <ul class="mt-5 space-y-3">
            <li v-for="it in filteredItems" :key="it.id"
              class="p-3 rounded-lg bg-white/5 border border-white/10 flex justify-between items-start hover:shadow-md transition-all">
              <div class="flex-1">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <span :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-300']">description</span>
                    <div>
                      <div :class="['font-semibold', darkMode ? 'text-white' : 'text-black']">{{ it.title || it.filename || ('Note ' + it.id) }}</div>
                      <button v-for="t in asTags(it.tags)" :key="t" :class="['px-2 py-0.5 rounded-full text-xs hover:bg-opacity-30 transition cursor-pointer', darkMode ? 'bg-white/6 text-white/80' : 'bg-orange-300 text-white/90']"
                      @click="activeTagFilter = t" title="Filter by tag" :aria-label="'Filter by tag ' + t">#{{ t
                      }}</button>
                    </div>
                  </div>
                </div>
                <div class="mt-2 text-xs text-orange-300" style="margin-top: calc(var(--spacing) * 2)">ID: {{ it.id }} · File: {{ it.filename || '—' }}</div>
              </div>
              <div class="flex flex-col gap-2 ml-4 shrink-0 w-[130px] sm:w-[150px]">
                <button class="icon-btn cursor-pointer" title="Recall" aria-label="Recall item"
                  @click="recallAggregatedItem(it)"><span
                    class="material-symbols-outlined mr-1 text-sm align-middle">bolt</span>Recall</button>
                <button class="icon-btn cursor-pointer" title="Rename / tags" aria-label="Rename or edit tags"
                  @click="openAggregatedItemEditModal(it)"><span
                    class="material-symbols-outlined mr-1 text-sm align-middle">edit</span>Rename/Tags</button>
                <button class="icon-btn cursor-pointer text-rose-400 hover:text-rose-300" title="Delete"
                  aria-label="Delete item" @click="confirmDeleteAggregatedItem(it)"><span
                    class="material-symbols-outlined mr-1 text-sm align-middle">delete</span>Delete</button>
              </div>
            </li>
          </ul>
          <div v-if="selectedFolder && (!filteredItems || filteredItems.length === 0)"
            :class="['mt-5 text-sm bg-white/5 border border-white/10 rounded-lg p-4', darkMode ? 'text-white/70' : 'text-orange-200/80']">
            No items yet in this folder. Add a quick note or upload a file to get started.
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom: directory structure / raw listing -->
      <div class="mt-4 bg-white/10 border border-white/10 p-5 rounded-xl" style="margin-top: calc(var(--spacing) * 4)">
      <div class="flex justify-between items-center mb-2">
        <div class="text-sm uppercase tracking-wide text-orange-400">Directory structure</div>
        <div class="text-xs text-orange-300">Snapshot of folders and items</div>
      </div>
      <div class="max-h-56 overflow-auto text-sm text-gray-200 glass-modal-scroll" style="scrollbar-gutter: stable both-edges;">
        <ul>
          <li v-for="f in folders" :key="'dir-' + f.id" class="mb-1">
            <div :class="['font-medium flex items-center gap-2', darkMode ? 'text-white/80' : 'text-orange-400']"><span :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-400']">folder</span>{{ f.name }} <span :class="['text-xs', darkMode ? 'text-white/70' : 'text-orange-300']">{{ f.tag ? '• ' + f.tag : '' }}</span></div>
            <ul class="ml-4" style="margin-left: calc(var(--spacing) * 4);">
              <li v-for="it in (directoryAggregated[f.id] || [])" :key="'it-' + (it.ids ? it.ids.join('-') : it.id)" class="flex items-center gap-2">
                <span :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-400']">description</span>
                <div>
                  <div :class="darkMode ? 'text-white' : 'text-black'">{{ it.title || it.filename || ('Note ' + (it.id || (it.ids && it.ids[0]) || '?')) }} <span class="text-xs text-orange-300">(id:{{ it.ids ? it.ids[0] : it.id }})</span></div>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </div>

    <!-- Folder Rename Modal -->
    <div v-if="showFolderRenameModal" class="modal-overlay" role="dialog" aria-modal="true" aria-label="Rename folder">
      <div class="modal">
        <div class="modal-header">
          <span :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-300']">edit</span>
          <h3 :class="[ 'font-semibold', darkMode ? 'text-white' : 'text-white']">Rename Folder</h3>
        </div>
        <div class="modal-body">
          <input v-model="renameFolderName" class="box-textarea w-full" placeholder="Folder name" />
          <input v-model="renameFolderTag" class="box-textarea w-full" placeholder="#tag (optional)" />
        </div>
        <div class="modal-footer">
          <button class="box-btn" @click="applyRenameFolder">Save</button>
          <button class="box-btn" @click="cancelRenameFolder">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Item Edit Modal -->
    <div v-if="showItemEditModal" class="modal-overlay" role="dialog" aria-modal="true" aria-label="Edit item">
      <div class="modal">
        <div class="modal-header">
          <span :class="['material-symbols-outlined', darkMode ? 'text-white/80' : 'text-orange-300']">stylus_note</span>
          <h3 :class="[ 'font-semibold', darkMode ? 'text-white' : 'text-white']">Edit Item</h3>
        </div>
        <div class="modal-body">
          <input v-model="renameItemTitle" class="box-textarea w-full" placeholder="Title" />
          <input v-model="renameItemTags" class="box-textarea w-full" placeholder="tag1, tag2" />
        </div>
        <div class="modal-footer">
          <button class="box-btn" @click="applyRenameItem">Save</button>
          <button class="box-btn" @click="cancelRenameItem">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <div v-if="showConfirmModal" class="modal-overlay" role="dialog" aria-modal="true" aria-label="Confirm delete">
      <div class="modal">
        <div class="modal-header">
          <span class="material-symbols-outlined text-rose-300">warning</span>
          <h3 :class="[ 'font-semibold', darkMode ? 'text-white' : 'text-white']">{{ confirmTitle }}</h3>
        </div>
        <div class="modal-body">
          <p :class="[ darkMode ? 'text-white/80' : 'text-orange-100/90']">{{ confirmMessage }}</p>
        </div>
        <div class="modal-footer">
          <button class="box-btn danger-btn" @click="onConfirmDelete">Delete</button>
          <button class="box-btn" @click="closeConfirm">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed, toRef } from 'vue'
// Theme props and emits
const props = defineProps(['darkMode'])
const darkMode = toRef(props, 'darkMode')
const emit = defineEmits(['back'])
import LoaderOverlay from './LoaderOverlay.vue'

// Dynamic backend base URL (works for localhost, LAN, deployed domain) – rely on current origin
const API_BASE = (typeof window !== 'undefined') ? window.location.origin : ''
const apiUrl = (path) => `${API_BASE}${path}`

async function fetchJson(url, options) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`)
  }
  const ct = res.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    const text = await res.text().catch(() => '')
    throw new Error(`Expected JSON, got: ${text.slice(0, 200)}`)
  }
  return res.json()
}

const folders = ref([])
const items = ref([])
const selectedFolder = ref(null)
const directoryItems = reactive({})

// Busy overlay
const isBusy = ref(false)
const busyText = ref('Loading…')

const newFolderName = ref('')
const newFolderTag = ref('')
const newNoteText = ref('')
const newItemTag = ref('')
const itemSearch = ref('')
const itemSort = ref('newest')
const activeTagFilter = ref('')

const renamingFolderId = ref(null)
const renameFolderName = ref('')
const renameFolderTag = ref('')

const renamingItemId = ref(null)
const renameItemTitle = ref('')
const renameItemTags = ref('')

// Modals
const showFolderRenameModal = ref(false)
const showItemEditModal = ref(false)
const showConfirmModal = ref(false)
const pendingDelete = ref(null) // { kind: 'folder' | 'agg', id?, name?, agg? }

// Toasts
const toasts = ref([])
function addToast(text, type = 'success') {
  const id = Date.now() + Math.random()
  toasts.value.push({ id, text, type })
  setTimeout(() => {
    const i = toasts.value.findIndex(t => t.id === id)
    if (i > -1) toasts.value.splice(i, 1)
  }, 2500)
}

async function loadFolders() {
  try {
    isBusy.value = true
    busyText.value = 'Loading folders…'
    const data = await fetchJson(apiUrl('/api/memory/folders'))
    folders.value = data.folders || []
    // build directory mapping
    for (const f of folders.value) {
      busyText.value = `Loading items in ${f.name}…`
      const d = await fetchJson(apiUrl(`/api/memory/folders/${f.id}/items`))
      directoryItems[f.id] = d.items || []
    }
  } catch (e) {
    addToast(e.message || 'Failed to load folders', 'error')
    folders.value = []
  } finally {
    isBusy.value = false
  }
}

async function selectFolder(f) {
  selectedFolder.value = f
  try {
    isBusy.value = true
    busyText.value = `Loading ${f.name}…`
    const d = await fetchJson(apiUrl(`/api/memory/folders/${f.id}/items`))
    items.value = d.items || []
  } catch (e) {
    addToast(e.message || 'Failed to load items', 'error')
    items.value = []
  } finally {
    isBusy.value = false
  }
}

async function createFolder() {
  if (!newFolderName.value.trim()) return
  try {
  isBusy.value = true
  busyText.value = 'Creating folder…'
  const res = await fetch(apiUrl('/api/memory/folders'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newFolderName.value, tag: newFolderTag.value }) })
    if (!res.ok) throw new Error('Failed to create folder')
    addToast('Folder created')
  } catch (e) { addToast(e.message || 'Failed to create folder', 'error') }
  newFolderName.value = ''
  newFolderTag.value = ''
  await loadFolders()
  isBusy.value = false
}

function confirmDeleteFolder(f) {
  pendingDelete.value = { kind: 'folder', id: f.id, name: f.name }
  showConfirmModal.value = true
}
async function performDeleteFolder(id) {
  try {
    isBusy.value = true
    busyText.value = 'Deleting folder…'
    const res = await fetch(apiUrl(`/api/memory/folders/${id}`), { method: 'DELETE' })
    if (!res.ok) throw new Error('Failed to delete folder')
    addToast('Folder deleted')
  } catch (e) { addToast(e.message || 'Failed to delete folder', 'error') }
  if (selectedFolder.value && selectedFolder.value.id === id) selectedFolder.value = null
  await loadFolders()
  isBusy.value = false
}

function openFolderRenameModal(f) {
  renamingFolderId.value = f.id
  renameFolderName.value = f.name
  renameFolderTag.value = f.tag || ''
  showFolderRenameModal.value = true
}

async function renameFolder(id, name, tag) {
  try {
  isBusy.value = true
  busyText.value = 'Renaming folder…'
  const res = await fetch(apiUrl(`/api/memory/folders/${id}/rename`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, tag }) })
    if (!res.ok) throw new Error('Failed to rename folder')
    addToast('Folder updated')
  } catch (e) { addToast(e.message || 'Failed to rename folder', 'error') }
  await loadFolders()
  isBusy.value = false
}

function applyRenameFolder() {
  if (!renamingFolderId.value) return
  renameFolder(renamingFolderId.value, renameFolderName.value, renameFolderTag.value)
  cancelRenameFolder()
}
function cancelRenameFolder() {
  renamingFolderId.value = null
  renameFolderName.value = ''
  renameFolderTag.value = ''
  showFolderRenameModal.value = false
}

async function uploadFile(e) {
  const file = e.target.files[0]
  if (!file || !selectedFolder.value) return
  const fd = new FormData()
  fd.append('file', file)
  fd.append('folder_id', selectedFolder.value.id)
  fd.append('tags', newItemTag.value)
  try {
  isBusy.value = true
  busyText.value = 'Uploading… (OCR may take time)'
  const res = await fetch(apiUrl('/api/memory/upload'), { method: 'POST', body: fd })
    if (!res.ok) throw new Error('Upload failed')
    addToast('File uploaded')
  } catch (e) { addToast(e.message || 'Upload failed', 'error') }
  newItemTag.value = ''
  await selectFolder(selectedFolder.value)
  await loadFolders()
  isBusy.value = false
}

async function saveNote() {
  if (!selectedFolder.value || !newNoteText.value.trim()) return
  try {
  isBusy.value = true
  busyText.value = 'Saving note…'
  const res = await fetch(apiUrl('/api/memory/note'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ folder_id: selectedFolder.value.id, text: newNoteText.value, tags: newItemTag.value }) })
    if (!res.ok) throw new Error('Failed to save note')
    addToast('Note saved')
  } catch (e) { addToast(e.message || 'Failed to save note', 'error') }
  newNoteText.value = ''
  newItemTag.value = ''
  await selectFolder(selectedFolder.value)
  await loadFolders()
  isBusy.value = false
}

// legacy per-chunk helpers removed; aggregated handlers are used instead

async function updateItem(id, title, tags) {
  try {
  isBusy.value = true
  busyText.value = 'Updating item…'
  const res = await fetch(apiUrl(`/api/memory/item/${id}/update`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, tags }) })
    if (!res.ok) throw new Error('Failed to update item')
    addToast('Item updated')
  } catch (e) { addToast(e.message || 'Failed to update item', 'error') }
  if (selectedFolder.value) await selectFolder(selectedFolder.value)
  await loadFolders()
  isBusy.value = false
}

function applyRenameItem() {
  // Handle aggregated items first (no single id needed)
  if (aggregatedEditTarget.value) {
    updateAggregatedItem(aggregatedEditTarget.value, renameItemTitle.value, renameItemTags.value)
  } else {
    if (!renamingItemId.value) return
    updateItem(renamingItemId.value, renameItemTitle.value, renameItemTags.value)
  }
  cancelRenameItem()
}
function cancelRenameItem() {
  renamingItemId.value = null
  renameItemTitle.value = ''
  renameItemTags.value = ''
  showItemEditModal.value = false
  aggregatedEditTarget.value = null
}

function asTags(tagsStr) {
  if (!tagsStr) return []
  return tagsStr.split(',').map(t => t.trim()).filter(Boolean)
}

// Aggregate backend chunked items into single UI entries by filename/title
function aggregateList(rawList) {
  const map = new Map()
  for (const it of (rawList || [])) {
    // group key: prefer filename (for files), fall back to title, fall back to unique note id
    const key = it.filename || it.title || `note-${it.id}`
    if (!map.has(key)) {
      map.set(key, Object.assign({}, it, { ids: [it.id], filename: it.filename, title: it.title, tags: it.tags || '' }))
    } else {
      const cur = map.get(key)
      cur.ids.push(it.id)
      // merge tags conservatively
      const existingTags = new Set((cur.tags || '').split(',').map(t => t.trim()).filter(Boolean))
      for (const t of ((it.tags || '').split(',').map(x => x.trim()).filter(Boolean))) existingTags.add(t)
      cur.tags = Array.from(existingTags).join(', ')
      // keep earliest created_at as representative (or latest depending on UX)
      cur.created_at = Math.min(cur.created_at || Infinity, it.created_at || Infinity)
      // keep preview/title if missing
      if (!cur.title && it.title) cur.title = it.title
      if (!cur.filename && it.filename) cur.filename = it.filename
    }
  }
  return Array.from(map.values())
}

const aggregatedEditTarget = ref(null)

const aggregatedItems = computed(() => aggregateList(items.value || []))

const directoryAggregated = computed(() => {
  const out = {}
  for (const f of folders.value || []) {
    const raw = directoryItems[f.id] || []
    out[f.id] = aggregateList(raw || [])
  }
  return out
})

const filteredItems = computed(() => {
  let list = [...(aggregatedItems.value || [])]
  // tag filter
  if (activeTagFilter.value) {
    list = list.filter(it => asTags(it.tags).includes(activeTagFilter.value))
  }
  // search filter
  const q = itemSearch.value.trim().toLowerCase()
  if (q) {
    list = list.filter(it => (
      (it.title || '').toLowerCase().includes(q) ||
      (it.filename || '').toLowerCase().includes(q) ||
      (it.preview || '').toLowerCase().includes(q) ||
      (it.tags || '').toLowerCase().includes(q)
    ))
  }
  // sort
  if (itemSort.value === 'title') {
    list.sort((a, b) => (a.title || a.filename || '').localeCompare(b.title || b.filename || ''))
  } else if (itemSort.value === 'oldest') {
    list.sort((a, b) => (a.created_at || 0) - (b.created_at || 0))
  } else {
    list.sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
  }
  return list
})

// Aggregated handlers: recall uses first chunk id; delete/update operate on all chunk ids
async function recallAggregatedItem(agg) {
  if (!agg || !agg.ids || !agg.ids.length) return
  try {
    isBusy.value = true
    busyText.value = 'Recalling…'
    const d = await fetchJson(apiUrl(`/api/memory/item/${agg.ids[0]}/context`))
    const ev = new CustomEvent('memory-recall', { detail: d })
    window.dispatchEvent(ev)
  } catch (e) {
    addToast(e.message || 'Failed to recall item', 'error')
  } finally { isBusy.value = false }
}

function confirmDeleteAggregatedItem(agg) {
  if (!agg || !agg.ids || !agg.ids.length) return
  pendingDelete.value = { kind: 'agg', agg }
  showConfirmModal.value = true
}
async function performDeleteAggregatedItem(agg) {
  if (!agg || !agg.ids || !agg.ids.length) return
  try {
    isBusy.value = true
    busyText.value = 'Deleting…'
    for (const id of agg.ids) {
      const res = await fetch(apiUrl(`/api/memory/item/${id}`), { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete item chunk ' + id)
    }
    addToast('Item deleted')
  } catch (e) { addToast(e.message || 'Failed to delete item', 'error') }
  if (selectedFolder.value) await selectFolder(selectedFolder.value)
  await loadFolders()
  isBusy.value = false
}

// Confirm helpers
const confirmTitle = computed(() => pendingDelete.value?.kind === 'folder' ? 'Delete Folder' : 'Delete Item')
const confirmMessage = computed(() => {
  const p = pendingDelete.value
  if (!p) return ''
  if (p.kind === 'folder') return `This will delete the folder "${p.name}" and all its items.`
  if (p.kind === 'agg') {
    const label = p.agg.title || p.agg.filename || `Item ${p.agg.id || (p.agg.ids && p.agg.ids[0]) || ''}`
    const count = (p.agg.ids && p.agg.ids.length) || 1
    return `This will permanently delete "${label}" and its ${count} chunk(s).`
  }
  return ''
})
function closeConfirm() { showConfirmModal.value = false; pendingDelete.value = null }
async function onConfirmDelete() {
  const p = pendingDelete.value
  showConfirmModal.value = false
  if (!p) return
  if (p.kind === 'folder') {
    await performDeleteFolder(p.id)
  } else if (p.kind === 'agg') {
    await performDeleteAggregatedItem(p.agg)
  }
  pendingDelete.value = null
}

function openAggregatedItemEditModal(agg) {
  aggregatedEditTarget.value = agg
  renameItemTitle.value = agg.title || agg.filename || ''
  renameItemTags.value = agg.tags || ''
  showItemEditModal.value = true
}

async function updateAggregatedItem(agg, title, tags) {
  if (!agg || !agg.ids) return
  try {
    isBusy.value = true
    busyText.value = 'Updating…'
    for (const id of agg.ids) {
      const res = await fetch(apiUrl(`/api/memory/item/${id}/update`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, tags }) })
      if (!res.ok) throw new Error('Failed to update chunk ' + id)
    }
    addToast('Item updated')
  } catch (e) { addToast(e.message || 'Failed to update item', 'error') }
  aggregatedEditTarget.value = null
  if (selectedFolder.value) await selectFolder(selectedFolder.value)
  await loadFolders()
  isBusy.value = false
}

onMounted(() => { loadFolders() })
</script>

<style scoped>
.frosted-glass-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

/* subtle separators */
.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 1px;
}

/* Toasts */
.toast-container {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 40;
}

.toast {
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  color: #0b1220;
  background: #d1fae5;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.toast-success {
  background: #d1fae5;
  color: #065f46;
  border-color: rgba(16, 185, 129, 0.35);
}

.toast-error {
  background: #fee2e2;
  color: #7f1d1d;
  border-color: rgba(239, 68, 68, 0.35);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(3, 7, 18, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(2px);
}

.modal {
  width: 100%;
  max-width: 28rem;
  background: rgba(37, 36, 35, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.9rem;
  padding: 1rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

/* Shared control styles (duplicated from Translator.vue for local use) */
.box-textarea {
  width: auto;
  /* allow utility widths like w-36/w-24/w-48 to take effect */
  display: inline-block;
  border-radius: 0.75rem;
  border: 1px solid #e0e0e0;
  color: rgb(251 146 60 / var(--tw-text-opacity, 1));
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.95rem;
  resize: vertical;
  margin-bottom: 0.5rem;
  transition: outline-color 0.15s ease, box-shadow 0.15s ease;
}

.box-textarea:focus {
  outline: 2px solid rgba(251, 146, 60, 0.55); /* orange-400 */
  border-color: transparent;
}

.box-textarea::placeholder {
  color: rgb(251 146 60 / var(--tw-text-opacity, 1));
  opacity: 0.6;
}

.box-btn {
    padding: 0.9rem 1rem;
    font-size: 1rem;
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

.box-btn:hover {
    background: rgba(255,255,255,0.06);
    transform: translateY(-1px);
}

/* Compact variation for tighter layouts */
.box-btn-compact {
  width: auto !important;
  min-width: 90px;
  padding: 0.65rem 0.85rem;
  font-size: 0.85rem;
  text-align: center;
  padding-left: 0.85rem;
}

.icon-btn {
  background: rgba(255, 255, 255, 0.14);
  border: 1.5px solid rgba(255, 255, 255, 0.22);
  color: #fb923c; /* orange-400 */
  border-radius: 0.6rem;
  padding: 0.55rem 0.9rem;
  font-size: 1.02rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  transition: background 0.18s, color 0.18s, box-shadow 0.18s, transform 0.12s;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.icon-btn:hover {
  background: rgba(251, 146, 60, 0.12);
  color: #f97316; /* orange-600 */
  box-shadow: 0 4px 16px rgba(251, 146, 60, 0.10);
}

.danger-btn {
  background: rgba(244, 63, 94, 0.18);
  border-color: rgba(244, 63, 94, 0.35);
  color: #fecaca;
}
.danger-btn:hover {
  background: rgba(244, 63, 94, 0.26);
  color: #fee2e2;
}

/* Glass scrollbar (same as modal/chat) */
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
  background: linear-gradient(120deg, rgba(251, 146, 60, 0.95) 40%, rgba(249, 115, 22, 0.95) 100%);
  border-radius: 8px;
  min-height: 40px;
}
.glass-modal-scroll::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(120deg, rgba(251, 146, 60, 1) 80%, rgba(249, 115, 22, 1) 100%);
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .frosted-glass-card { padding: 1.25rem; }
}
@media (max-width: 820px) {
  .frosted-glass-card { padding: 1rem; }
  .box-textarea { font-size: 0.85rem; padding: 0.6rem 0.75rem; }
  .icon-btn { padding: 0.45rem 0.7rem; font-size: 0.9rem; }
  .box-btn { font-size: 0.9rem; padding: 0.7rem 0.9rem; }
}
@media (max-width: 640px) {
  .box-btn { width: auto; }
  .icon-btn { gap: 0.35rem; }
  ul.space-y-3 > li { flex-direction: column; }
  ul.space-y-3 > li > div.flex-1 { width: 100%; }
  ul.space-y-3 > li > div.ml-4 { margin-left: 0; width: 100% !important; flex-direction: row; display: flex; flex-wrap: wrap; }
  ul.space-y-3 > li > div.ml-4 button { flex: 1 1 48%; min-width: 140px; }
}
@media (max-width: 420px) {
  .box-textarea { font-size: 0.8rem; }
  .box-btn-compact { min-width: 74px; font-size: 0.75rem; }
  ul.space-y-3 > li > div.ml-4 button { flex: 1 1 100%; }
}
</style>
