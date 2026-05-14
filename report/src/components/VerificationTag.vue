<script setup lang="ts">
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons-vue'
import type { Verification } from '../types'

defineProps<{ verification: Verification }>()
</script>

<template>
  <div class="verif-item" :class="{ passed: verification.passed, failed: !verification.passed }">
    <div class="verif-header">
      <span class="verif-icon">
        <CheckCircleFilled v-if="verification.passed" />
        <CloseCircleFilled v-else />
      </span>
      <span class="verif-assertion">{{ verification.assertion }}</span>
    </div>
    <div v-if="verification.reason" class="verif-reason">{{ verification.reason }}</div>
  </div>
</template>

<style scoped>
.verif-item {
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  border: 1px solid #f0f0f0;
  background: #fafafa;
}
.verif-item.passed { border-left: 3px solid #b7eb8f; }
.verif-item.failed { border-left: 3px solid #ffa39e; }

.verif-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.verif-icon {
  flex-shrink: 0;
  font-size: 14px;
  margin-top: 1px;
}
.verif-item.passed .verif-icon { color: #52c41a; }
.verif-item.failed .verif-icon { color: #ff4d4f; }

.verif-assertion {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
  line-height: 1.5;
}
.verif-reason {
  margin-top: 6px;
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.6;
  padding-left: 22px;
}
</style>
