<script setup lang="ts">
import { computed } from 'vue'
import { Collapse, CollapsePanel, Tag } from 'ant-design-vue'
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons-vue'
import type { StepEntry } from '../types'
import VerificationTag from './VerificationTag.vue'
import ScreenshotViewer from './ScreenshotViewer.vue'

const props = defineProps<{
  step: StepEntry
  index: number
}>()

const panelKey = computed(() => `step-${props.index}`)

function formatElapsed(s: number): string {
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}m${sec}s`
}
</script>

<template>
  <div class="step-card-wrapper">
    <Collapse :bordered="false" class="step-collapse">
      <CollapsePanel :key="panelKey">
        <template #header>
          <div class="panel-header">
            <span class="step-num">#{{ index }}</span>
            <span class="step-name">{{ step.step_id }}</span>
            <Tag v-if="step.mode" class="mode-tag">{{ step.mode }}</Tag>
            <span class="step-status" :class="step.status">
              <CheckCircleFilled v-if="step.status === 'success'" />
              <CloseCircleFilled v-else />
              {{ step.status.toUpperCase() }}
            </span>
            <span class="step-time">{{ formatElapsed(step.elapsed) }}</span>
          </div>
        </template>
        <div class="panel-body">
          <div v-if="step.summary" class="step-summary">{{ step.summary }}</div>
          <div v-if="step.error" class="step-error">{{ step.error }}</div>

          <div v-if="step.verifications.length > 0" class="verifications">
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
.step-card-wrapper {
  margin-bottom: 8px;
}
.step-collapse {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.step-num {
  font-size: 13px;
  color: #bbb;
  min-width: 28px;
}
.step-name {
  font-weight: 600;
  font-size: 14px;
  flex: 1;
  color: #333;
}
.mode-tag {
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  border: none;
}
.step-status {
  font-weight: 600;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.step-status.success { color: #1a7d1a; }
.step-status.failed { color: #c41e1e; }
.step-time {
  font-size: 12px;
  color: #aaa;
  min-width: 50px;
  text-align: right;
}
.panel-body {
  padding: 4px 0;
}
.step-summary {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  white-space: pre-wrap;
  margin-bottom: 12px;
  max-height: 200px;
  overflow-y: auto;
}
.step-error {
  font-size: 13px;
  color: #c41e1e;
  background: #fff2f0;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}
.verifications {
  margin-bottom: 8px;
}
</style>
