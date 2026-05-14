<script setup lang="ts">
import { computed } from 'vue'
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

const statusColor = computed(() => props.step.status === 'success' ? '#52c41a' : '#ff4d4f')

function formatElapsed(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<template>
  <div class="step-card">
    <Collapse :bordered="false" class="step-collapse">
      <CollapsePanel :key="panelKey">
        <template #header>
          <div class="header-row">
            <span class="step-index">{{ index }}</span>
            <span class="type-badge" :class="stepType">
              <component :is="typeIcon" class="type-badge-icon" />
              {{ typeLabel }}
            </span>
            <span class="step-title">{{ step.step_id }}</span>
            <span class="step-spacer" />
            <span v-if="step.mode && step.mode !== stepType" class="mode-label">{{ step.mode }}</span>
            <span class="elapsed">{{ formatElapsed(step.elapsed) }}</span>
            <span class="status-dot" :style="{ background: statusColor }">
              <CheckCircleFilled v-if="step.status === 'success'" />
              <CloseCircleFilled v-else />
            </span>
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
</template>

<style scoped>
.step-card {
  margin-bottom: 6px;
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
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f0f2f5;
  color: #8c8c8c;
  font-size: 12px;
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
.type-badge-icon {
  font-size: 12px;
}
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
  color: #bfbfbf;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
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

/* -- Body -- */
.body {
  padding: 4px 0;
}
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
.verifications {
  margin-bottom: 8px;
}
</style>
