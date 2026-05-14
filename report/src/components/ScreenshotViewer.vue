<script setup lang="ts">
import { Image } from 'ant-design-vue'
import { CameraOutlined } from '@ant-design/icons-vue'
import type { Screenshot } from '../types'

defineProps<{ screenshots: Screenshot[] }>()
</script>

<template>
  <div v-if="screenshots.length > 0" class="screenshot-section">
    <div class="screenshot-label">
      <CameraOutlined class="screenshot-label-icon" />
      Screenshots
    </div>
    <Image.PreviewGroup>
      <div class="screenshot-grid">
        <div v-for="s in screenshots" :key="s.name" class="screenshot-thumb-wrapper">
          <Image
            :src="s.path"
            :alt="s.name"
            class="screenshot-thumb"
          />
          <div class="screenshot-name">{{ s.name }}</div>
        </div>
      </div>
    </Image.PreviewGroup>
  </div>
</template>

<style scoped>
.screenshot-section {
  margin-top: 12px;
}
.screenshot-label {
  font-size: 12px;
  color: #8c8c8c;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.screenshot-label-icon {
  font-size: 13px;
}
.screenshot-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.screenshot-thumb-wrapper {
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  overflow: hidden;
  background: #fafafa;
  transition: box-shadow 0.2s;
}
.screenshot-thumb-wrapper:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.screenshot-thumb {
  width: 260px;
  cursor: pointer;
  display: block;
}
.screenshot-thumb :deep(img) {
  max-height: 180px;
  object-fit: cover;
}
.screenshot-name {
  padding: 6px 10px;
  font-size: 11px;
  color: #8c8c8c;
  text-align: center;
  border-top: 1px solid #f0f0f0;
}
</style>
