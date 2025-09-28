import { ref, computed } from 'vue';

// Global theme/backdrop state shared across components
const backdropOverride = ref<'default' | 'power'>('default');

export const themeState = {
  backdropOverride,
  isPower: computed(() => backdropOverride.value === 'power'),
  setPower(active: boolean) {
    backdropOverride.value = active ? 'power' : 'default';
  },
  clear() { backdropOverride.value = 'default'; }
};
