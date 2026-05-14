<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import type { ReportData } from '../types'

const props = defineProps<{ report: ReportData }>()

const assertionStats = computed(() => {
  let passed = 0
  let total = 0
  for (const step of props.report.steps) {
    for (const v of step.verifications) {
      total++
      if (v.passed) passed++
    }
  }
  return { passed, total }
})

function formatElapsed(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<template>
  <div class="summary-bar">
    <div class="stat-item">
      <CheckCircleOutlined class="stat-icon pass" />
      <div class="stat-body">
        <div class="stat-value">{{ report.success_count }}</div>
        <div class="stat-label">Passed</div>
      </div>
    </div>
    <div class="stat-item">
      <CloseCircleOutlined class="stat-icon fail" />
      <div class="stat-body">
        <div class="stat-value">{{ report.failed_count }}</div>
        <div class="stat-label">Failed</div>
      </div>
    </div>
    <div class="stat-item">
      <SafetyCertificateOutlined class="stat-icon assert" />
      <div class="stat-body">
        <div class="stat-value">{{ assertionStats.passed }}/{{ assertionStats.total }}</div>
        <div class="stat-label">Assertions</div>
      </div>
    </div>
    <div class="stat-item">
      <ClockCircleOutlined class="stat-icon time" />
      <div class="stat-body">
        <div class="stat-value">{{ formatElapsed(report.elapsed_seconds) }}</div>
        <div class="stat-label">Duration</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.2s;
}
.stat-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.stat-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.stat-icon.pass { color: #52c41a; }
.stat-icon.fail { color: #ff4d4f; }
.stat-icon.assert { color: #8c8c8c; }
.stat-icon.time { color: #8c8c8c; }

.stat-body {
  min-width: 0;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #262626;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
</style>
