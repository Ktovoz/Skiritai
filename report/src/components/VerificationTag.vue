<script setup lang="ts">
import { Tag } from 'ant-design-vue'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons-vue'
import type { Verification } from '../types'

defineProps<{ verification: Verification }>()
</script>

<template>
  <div class="verification-row">
    <Tag :color="verification.passed ? 'success' : 'error'" class="verif-tag">
      <CheckCircleOutlined v-if="verification.passed" />
      <CloseCircleOutlined v-else />
      <span class="verif-text">{{ verification.assertion }}</span>
    </Tag>
    <span v-if="verification.reason" class="verif-reason">{{ verification.reason }}</span>
  </div>
</template>

<style scoped>
.verification-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.verif-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  white-space: normal;
  line-height: 1.5;
}
.verif-text {
  margin-left: 4px;
}
.verif-reason {
  font-size: 12px;
  color: #999;
  line-height: 1.5;
  margin-top: 2px;
}
</style>
