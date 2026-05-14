<script setup lang="ts">
import { computed, ref } from 'vue'
import { Collapse, CollapsePanel } from 'ant-design-vue'
import {
  CheckCircleFilled, CloseCircleFilled,
  CameraOutlined, SafetyCertificateOutlined, ThunderboltOutlined,
} from '@ant-design/icons-vue'
import type { StepEntry } from '../types'
import VerificationTag from './VerificationTag.vue'
import ScreenshotViewer from './ScreenshotViewer.vue'

const props = defineProps<{
  step: StepEntry
  index: number
  defaultOpen?: boolean
}>()

const panelKey = computed(() => `step-${props.index}`)

const stepType = computed(() => props.step.type || 'action')

const typeIcon = computed(() => {
  switch (stepType.value) {
    case 'screenshot': return CameraOutlined
    case 'verify': return SafetyCertificateOutlined
    default: return ThunderboltOutlined
  }
})

const typeLabel = computed(() => {
  switch (stepType.value) {
    case 'screenshot': return 'Screenshot'
    case 'verify': return 'Verify'
    default: return 'Action'
  }
})

const displayTitle = computed(() => {
  return props.step.title || props.step.step_id
})

const statusColor = computed(() => props.step.status === 'success' ? '#52c41a' : '#ff4d4f')

const elapsedHeat = computed(() => {
  const s = props.step.elapsed
  if (s < 5) return 'fast'
  if (s < 15) return 'normal'
  if (s < 30) return 'slow'
  return 'critical'
})

const elapsedColor = computed(() => {
  switch (elapsedHeat.value) {
    case 'fast': return '#8c8c8c'
    case 'normal': return '#d48806'
    case 'slow': return '#d46b08'
    case 'critical': return '#cf1322'
    default: return '#8c8c8c'
  }
})

const activeKeys = ref<string[]>(props.defaultOpen ? [panelKey.value] : [])

function formatElapsed(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<template>
  <div class="step-timeline-row">
    <div class="timeline-rail">
      <div class="timeline-node" :class="step.status" />
      <div v-if="index > 0" class="timeline-line" />
    </div>
    <div class="step-card">
      <Collapse v-model:activeKey="activeKeys" :bordered="false" class="step-collapse">
        <CollapsePanel :key="panelKey" :show-arrow="false">
          <template #header>
            <div class="header-row">
              <span class="step-index">{{ index }}</span>
              <span class="type-badge" :class="stepType">
                <component :is="typeIcon" class="type-badge-icon" />
                {{ typeLabel }}
              </span>
              <span class="step-title">{{ displayTitle }}</span>
              <span class="step-spacer" />
              <span v-if="step.mode && step.mode !== stepType" class="mode-label">{{ step.mode }}</span>
              <span class="elapsed" :style="{ color: elapsedColor }">{{ formatElapsed(step.elapsed) }}</span>
              <span class="status-dot" :style="{ background: statusColor }">
                <CheckCircleFilled v-if="step.status === 'success'" />
                <CloseCircleFilled v-else />
              </span>
              <span class="expand-arrow" :class="{ open: activeKeys.includes(panelKey) }">&#9656;</span>
            </div>
          </template>
          <div class="body">
            <div v-if="step.summary" class="summary">{{ step.summary }}</div>
            <div v-if="step.error" class="error-block">{{ step.error }}</div>

            <div v-if="step.verifications && step.verifications.length > 0" class="verifications">
              <VerificationTag
                v-for="(v, i) in step.verifications"
                :key="i"
                :verification="v"
              />
            </div>

            <ScreenshotViewer :screenshots="step.screenshots" />
          </div>
        </CollapsePanel>
      </Collapse>
    </div>
  </div>
</template>

<style scoped>
.step-timeline-row {
  display: flex;
  gap: 16px;
  min-height: 0;
}

/* -- Timeline rail (left side) -- */
.timeline-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 14px;
  flex-shrink: 0;
  position: relative;
}
.timeline-node {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 16px;
  border: 2px solid #d9d9d9;
  background: #fff;
  z-index: 1;
}
.timeline-node.success { border-color: #b7eb8f; background: #f6ffed; }
.timeline-node.failed { border-color: #ffa39e; background: #fff1f0; }

.timeline-line {
  width: 2px;
  flex: 1;
  background: #f0f0f0;
  margin-top: 2px;
}

/* -- Step card -- */
.step-card {
  flex: 1;
  min-width: 0;
}
.step-collapse {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.2s;
}
.step-collapse:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* -- Header -- */
.header-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  font-size: 13px;
}
.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #f0f2f5;
  color: #8c8c8c;
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.3px;
  flex-shrink: 0;
  background: #f5f7fa;
  color: #8c8c8c;
}
.type-badge-icon { font-size: 12px; }
.type-badge.action { color: #595959; background: #f5f7fa; }
.type-badge.verify { color: #389e0d; background: #f6ffed; }
.type-badge.screenshot { color: #7c6913; background: #fffdf0; }

.step-title {
  font-weight: 500;
  color: #262626;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.step-spacer { flex: 1; }

.mode-label {
  font-size: 11px;
  color: #bfbfbf;
  flex-shrink: 0;
}

.elapsed {
  flex-shrink: 0;
  min-width: 42px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  transition: color 0.2s;
}

.status-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  color: #fff;
  font-size: 11px;
  flex-shrink: 0;
}

.expand-arrow {
  font-size: 12px;
  color: #bfbfbf;
  flex-shrink: 0;
  transition: transform 0.2s;
}
.expand-arrow.open {
  transform: rotate(90deg);
}

/* -- Body -- */
.body { padding: 4px 0; }
.summary {
  font-size: 13px;
  color: #595959;
  line-height: 1.7;
  white-space: pre-wrap;
  margin-bottom: 12px;
  max-height: 200px;
  overflow-y: auto;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}
.error-block {
  font-size: 13px;
  color: #cf1322;
  background: #fff1f0;
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 12px;
  line-height: 1.6;
}
.verifications { margin-bottom: 8px; }
</style>
