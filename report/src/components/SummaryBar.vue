<script setup lang="ts">
import { computed } from 'vue'
import { Card, Statistic } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExperimentOutlined,
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
</script>

<template>
  <div class="summary-bar">
    <Card class="stat-card stat-pass">
      <Statistic title="Passed" :value="report.success_count" :value-style="{ color: '#1a7d1a' }">
        <template #prefix><CheckCircleOutlined /></template>
      </Statistic>
    </Card>
    <Card class="stat-card stat-fail">
      <Statistic title="Failed" :value="report.failed_count" :value-style="{ color: '#c41e1e' }">
        <template #prefix><CloseCircleOutlined /></template>
      </Statistic>
    </Card>
    <Card class="stat-card stat-assert">
      <Statistic
        title="Assertions"
        :value="assertionStats.passed + '/' + assertionStats.total"
        :value-style="{ color: '#1677ff' }"
      >
        <template #prefix><ExperimentOutlined /></template>
      </Statistic>
    </Card>
    <Card class="stat-card stat-time">
      <Statistic
        title="Total Time"
        :value="formatElapsed(report.elapsed_seconds)"
        :value-style="{ color: '#555' }"
      >
        <template #prefix><ClockCircleOutlined /></template>
      </Statistic>
    </Card>
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
.summary-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  border-radius: 8px;
}
.stat-pass { border-left: 3px solid #1a7d1a; }
.stat-fail { border-left: 3px solid #c41e1e; }
.stat-assert { border-left: 3px solid #1677ff; }
.stat-time { border-left: 3px solid #888; }
</style>
