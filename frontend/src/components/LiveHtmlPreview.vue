<template>
  <div v-if="visible" class="flex flex-col h-full border-l" :class="darkMode ? 'border-white/20 bg-white/5' : 'border-orange-300/30 bg-orange-50/30'">
    <div class="flex items-center justify-between px-3 py-2 border-b border-white/10">
      <h3 :class="['text-sm font-semibold', darkMode ? 'text-white' : 'text-orange-600']">Live Preview</h3>
      <div class="flex items-center gap-2">
        <button class="px-2 py-1 rounded text-xs bg-indigo-600 text-white hover:bg-indigo-500" @click="refresh" :disabled="loading">Reload</button>
        <button class="px-2 py-1 rounded text-xs bg-gray-500/60 text-white hover:bg-gray-600" @click="$emit('close')">Close</button>
      </div>
    </div>
    <div class="flex-1 relative">
      <iframe v-if="iframeKey" :key="iframeKey" :src="iframeSrc" class="w-full h-full bg-white"></iframe>
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center text-xs" :class="darkMode ? 'text-white/70' : 'text-gray-500'">Loading...</div>
    </div>
    <div class="p-2 text-[11px] font-mono" :class="darkMode ? 'text-white/60' : 'text-gray-600'">{{ status }}</div>
  </div>
</template>
<script setup>
import { ref, watch, computed } from 'vue'
const props = defineProps({ path: String, darkMode: Boolean, visible: Boolean })
const emit = defineEmits(['close'])
void emit

const iframeKey = ref(0)
const status = ref('Idle')
const loading = ref(false)

const iframeSrc = computed(() => props.path ? `/api/code/raw?path=${encodeURIComponent(props.path)}` : 'about:blank')

watch(() => props.path, () => {
  if (props.visible) triggerReload()
})
watch(() => props.visible, (v) => { if (v) triggerReload() })

let debounceTimer = null
function triggerReload() {
  if (!props.path) return
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => refresh(), 250)
}

async function refresh() {
  if (!props.path) return
  loading.value = true
  status.value = 'Refreshing...'
  // bump key to force iframe reload
  iframeKey.value++
  setTimeout(() => { loading.value = false; status.value = 'Rendered ' + new Date().toLocaleTimeString() }, 500)
}
</script>
<style scoped>
iframe { border: none; }
</style>
