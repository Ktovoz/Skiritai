<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ClockCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  SwapOutlined,
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

const comp = computed(() => props.report.comparison)
const hasComparison = computed(() => !!comp.value)

const deltaPassed = computed(() => {
  if (!comp.value) return 0
  return props.report.success_count - comp.value.prev_ok
})

const deltaFailed = computed(() => {
  if (!comp.value) return 0
  return props.report.failed_count - (comp.value.prev_total - comp.value.prev_ok)
})

function formatElapsed(s: number): string {
  if (!s && s !== 0) return '-'
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<template>
  <div>
    <!-- Stats row -->
    <div class="summary-bar">
      <div class="stat-item">
        <CheckCircleOutlined class="stat-icon pass" />
        <div class="stat-body">
          <div class="stat-value">{{ report.success_count }}</div>
          <div class="stat-label">Passed</div>
        </div>
        <span v-if="hasComparison && deltaPassed !== 0" class="stat-delta" :class="deltaPassed > 0 ? 'up' : 'down'">
          <ArrowUpOutlined v-if="deltaPassed > 0" />
          <ArrowDownOutlined v-else />
          {{ Math.abs(deltaPassed) }}
        </span>
      </div>
      <div class="stat-item">
        <CloseCircleOutlined class="stat-icon fail" />
        <div class="stat-body">
          <div class="stat-value">{{ report.failed_count }}</div>
          <div class="stat-label">Failed</div>
        </div>
        <span v-if="hasComparison && deltaFailed !== 0" class="stat-delta" :class="deltaFailed > 0 ? 'down' : 'up'">
          <ArrowUpOutlined v-if="deltaFailed < 0" />
          <ArrowDownOutlined v-else />
          {{ Math.abs(deltaFailed) }}
        </span>
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

    <!-- Comparison bar -->
    <div v-if="hasComparison" class="comparison-bar">
      <SwapOutlined class="comp-icon" />
      <span class="comp-text">
        vs previous run ({{ comp!.prev_timestamp }}):
        {{ comp!.prev_ok }}/{{ comp!.prev_total }} passed
        <span v-if="comp!.prev_elapsed != null"> in {{ formatElapsed(comp!.prev_elapsed) }}</span>
      </span>
      <span v-if="deltaPassed > 0" class="comp-delta positive">+{{ deltaPassed }} passed</span>
      <span v-else-if="deltaPassed < 0" class="comp-delta negative">{{ deltaPassed }} passed</span>
      <span v-else class="comp-delta neutral">No change</span>
    </div>
  </div>
</template>

<style scoped>
.summary-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
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
  position: relative;
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

.stat-body { min-width: 0; }
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

.stat-delta {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 4px;
}
.stat-delta.up { color: #389e0d; background: #f6ffed; }
.stat-delta.down { color: #cf1322; background: #fff1f0; }

/* -- Comparison bar -- */
.comparison-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 10px 16px;
  margin-bottom: 16px;
  font-size: 12px;
  color: #8c8c8c;
}
.comp-icon {
  font-size: 14px;
  color: #bfbfbf;
}
.comp-text { flex: 1; }
.comp-delta {
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}
.comp-delta.positive { color: #389e0d; background: #f6ffed; }
.comp-delta.negative { color: #cf1322; background: #fff1f0; }
.comp-delta.neutral { color: #8c8c8c; background: #f5f5f5; }
</style>
