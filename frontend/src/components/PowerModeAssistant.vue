<template>
  <div id="PowerModeAssistant" class="font-sans flex justify-center items-center w-full pt-5">
    <LoaderOverlay :show="globalBusy" :text="busyText" />
  <div class="flex flex-col md:flex-row mx-auto mt-1 w-full max-w-7xl h-[calc(100vh-140px)] md:h-[calc(100vh-150px)] min-h-[500px] md:min-h-[600px] power-glass border border-white/30 shadow-2xl rounded-3xl">
      <!-- reuse ResearchAssistant layout/content -->
      <ResearchAssistantInner :powerMode="true" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LoaderOverlay from './LoaderOverlay.vue'
import ResearchAssistantInner from './ResearchAssistant.vue'
const globalBusy = ref(false)
const busyText = ref('Loading…')
</script>

<style scoped>
.power-glass {
  background: linear-gradient(135deg, rgba(255,0,64,0.25), rgba(255,89,94,0.25));
}
</style>
