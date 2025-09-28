<template>
  <button v-bind="$attrs" class="icon-btn w-8 h-8 text-[16px] p-1.5 text-gray-400 hover:bg-gray-200" @click="$emit('click', $event)">
    <slot />
  </button>
</template>

<script setup>
</script>

<style scoped>
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  transition: background-color .15s ease, transform .08s ease;
  cursor: pointer;
}
.icon-btn:active { transform: scale(.97); }
</style>
