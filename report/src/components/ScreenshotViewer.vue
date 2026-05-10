<script setup lang="ts">
import { Image } from 'ant-design-vue'
import type { Screenshot } from '../types'

defineProps<{ screenshots: Screenshot[] }>()
</script>

<template>
  <div v-if="screenshots.length > 0" class="screenshot-section">
    <div class="screenshot-title">Screenshots</div>
    <Image.PreviewGroup>
      <div class="screenshot-grid">
        <Image
          v-for="s in screenshots"
          :key="s.name"
          :src="s.path"
          :alt="s.name"
          class="screenshot-thumb"
        />
      </div>
    </Image.PreviewGroup>
  </div>
</template>

<style scoped>
.screenshot-section {
  margin-top: 12px;
}
.screenshot-title {
  font-size: 12px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.screenshot-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.screenshot-thumb {
  width: 240px;
  border-radius: 6px;
  border: 1px solid #e8e8e8;
  cursor: pointer;
  object-fit: cover;
}
.screenshot-thumb :deep(img) {
  max-height: 160px;
  object-fit: cover;
}
</style>
