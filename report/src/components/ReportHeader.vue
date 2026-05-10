<script setup lang="ts">
import { computed } from 'vue'
import { Tag } from 'ant-design-vue'
import type { ReportData } from '../types'

const props = defineProps<{ report: ReportData }>()

const statusColor = computed(() => props.report.status === 'completed' ? 'success' : 'error')
const statusText = computed(() => props.report.status === 'completed' ? 'PASSED' : 'FAILED')
</script>

<template>
  <div class="report-header">
    <h1 class="case-title">{{ report.case_name }}</h1>
    <div class="header-meta">
      <Tag :color="statusColor" class="status-tag">{{ statusText }}</Tag>
      <span class="meta-text">{{ report.success_count }}/{{ report.total_steps }} steps passed</span>
      <span class="meta-text">{{ formatElapsed(report.elapsed_seconds) }}</span>
    </div>
  </div>
</template>

<script lang="ts">
function formatElapsed(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<style scoped>
.report-header {
  background: #fff;
  border-radius: 8px;
  padding: 24px 32px;
  margin-bottom: 16px;
  border: 1px solid #e8e8e8;
}
.case-title {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 12px 0;
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}
.status-tag {
  font-weight: 600;
  font-size: 13px;
  padding: 2px 12px;
}
.meta-text {
  font-size: 13px;
  color: #888;
}
</style>
