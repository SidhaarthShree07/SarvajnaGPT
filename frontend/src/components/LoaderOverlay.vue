<template>
  <transition name="fade">
    <div v-if="show" class="loader-overlay" role="status" aria-live="polite" aria-busy="true">
      <div class="loader-card">
        <!-- Primary: CSS mask using the SVG so dark background becomes transparent -->
        <div class="loader-mask" :style="maskStyle" aria-hidden="true"></div>
        <!-- Fallback: plain image with blend/filter in case mask isn't supported -->
        <img class="loader-img" :src="logoUrl" alt="Loading..." />
        <div v-if="text" class="loader-text">{{ text }}</div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import logoUrl from '../assets/loader.svg'

defineProps({
  show: { type: Boolean, default: false },
  text: { type: String, default: '' }
})

// Inline styles to ensure the bundler-resolved URL is used for mask-image
const maskStyle = {
  WebkitMaskImage: `url(${logoUrl})`,
  maskImage: `url(${logoUrl})`,
  WebkitMaskRepeat: 'no-repeat',
  maskRepeat: 'no-repeat',
  WebkitMaskPosition: 'center',
  maskPosition: 'center',
  WebkitMaskSize: 'contain',
  maskSize: 'contain'
}
</script>

<style scoped>
.loader-overlay {
  position: fixed;
  inset: 0;
  /* Subtle white glass backdrop (light, not colored) */
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.loader-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 1.25rem 1.5rem;
  /* Frosted glass card */
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 1rem;
  box-shadow: 0 20px 60px rgba(0,0,0,0.35);
}
.loader-mask {
  width: 112px;
  height: 112px;
  /* Render the SVG as an alpha/luminance mask, fill with white to remove colors/black */
  background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.75) 100%);
  /* mask-image URL is provided inline via :style to use the bundler-resolved asset */
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
  -webkit-mask-size: contain;
  -webkit-mask-mode: luminance;
  mask-repeat: no-repeat;
  mask-position: center;
  mask-size: contain;
  mask-mode: luminance;
  image-rendering: auto;
  filter: drop-shadow(0 3px 10px rgba(0,0,0,0.35));
  animation: pulse 1.25s ease-in-out infinite, float 2.4s ease-in-out infinite;
}
.loader-mask { display: none; }
.loader-img {
  /* default to fallback visible; mask variant will enable itself via @supports */
  display: block;
  width: 96px;
  height: 96px;
  background: transparent;
  /* Remove black and colors: grayscale -> black -> invert to white; plus blend */
  mix-blend-mode: screen;
  filter: grayscale(1) brightness(0) invert(1) drop-shadow(0 3px 10px rgba(0,0,0,0.35));
  image-rendering: auto;
  animation: pulse 1.25s ease-in-out infinite, float 2.4s ease-in-out infinite;
}
/* If mask-image is supported, prefer the crisp white silhouette and hide fallback */
@supports ((-webkit-mask-image: linear-gradient(black, white)) or (mask-image: linear-gradient(black, white))) {
  .loader-img { display: none; }
  .loader-mask { display: block; }
}
.loader-text {
  margin-top: 0.5rem;
  color: #e6f0ff;
  font-size: 0.95rem;
  text-align: center;
  opacity: 0.95;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); filter: brightness(1.1) contrast(1.05) drop-shadow(0 3px 10px rgba(0,0,0,0.35)); }
  50%      { transform: scale(1.06); filter: brightness(1.25) contrast(1.05) drop-shadow(0 6px 16px rgba(0,0,0,0.4)); }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}
/* simple fade transition */
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
