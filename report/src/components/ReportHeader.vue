<script setup lang="ts">
import { computed } from 'vue'
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons-vue'
import type { ReportData } from '../types'

const props = defineProps<{ report: ReportData }>()

const isPassed = computed(() => props.report.status === 'completed')
</script>

<template>
  <div class="report-header" :class="{ passed: isPassed, failed: !isPassed }">
    <div class="header-left">
      <h1 class="case-title">{{ report.case_name }}</h1>
      <div class="header-meta">
        <span class="meta-item">{{ report.success_count }}/{{ report.total_steps }} steps</span>
        <span class="meta-divider" />
        <span class="meta-item">{{ formatElapsed(report.elapsed_seconds) }}</span>
      </div>
    </div>
    <div class="header-status">
      <CheckCircleFilled v-if="isPassed" class="status-icon" />
      <CloseCircleFilled v-else class="status-icon" />
      <span class="status-text">{{ isPassed ? 'PASSED' : 'FAILED' }}</span>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-radius: 10px;
  padding: 20px 28px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
}
.case-title {
  font-size: 20px;
  font-weight: 600;
  color: #262626;
  margin: 0 0 6px 0;
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.meta-item {
  font-size: 13px;
  color: #8c8c8c;
}
.meta-divider {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #d9d9d9;
}
.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.5px;
}
.report-header.passed .header-status {
  background: #f6ffed;
  color: #389e0d;
}
.report-header.failed .header-status {
  background: #fff1f0;
  color: #cf1322;
}
.status-icon {
  font-size: 16px;
}
</style>
