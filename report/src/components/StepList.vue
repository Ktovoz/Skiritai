<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  FilterOutlined, ExpandOutlined, NodeCollapseOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import type { StepEntry } from '../types'
import StepCard from './StepCard.vue'

const props = defineProps<{
  steps: StepEntry[]
}>()

type FilterType = 'all' | 'action' | 'verify' | 'screenshot' | 'failed'
const activeFilter = ref<FilterType>('all')
const allExpanded = ref(false)

const failedCount = computed(() => props.steps.filter(s => s.status === 'failed').length)

const filteredSteps = computed(() => {
  switch (activeFilter.value) {
    case 'action': return props.steps.filter(s => (s.type || 'action') === 'action')
    case 'verify': return props.steps.filter(s => (s.type || 'action') === 'verify')
    case 'screenshot': return props.steps.filter(s => (s.type || 'action') === 'screenshot')
    case 'failed': return props.steps.filter(s => s.status === 'failed')
    default: return props.steps
  }
})

function setFilter(f: FilterType) {
  activeFilter.value = f
  allExpanded.value = false
}

function toggleExpandAll() {
  allExpanded.value = !allExpanded.value
}

const filters: { key: FilterType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'action', label: 'Action' },
  { key: 'verify', label: 'Verify' },
  { key: 'screenshot', label: 'Screenshot' },
  { key: 'failed', label: 'Failed' },
]
</script>

<template>
  <div class="step-list">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="filter-group">
        <FilterOutlined class="toolbar-icon" />
        <button
          v-for="f in filters"
          :key="f.key"
          class="filter-btn"
          :class="{ active: activeFilter === f.key }"
          @click="setFilter(f.key)"
        >
          {{ f.label }}
          <span v-if="f.key === 'failed' && failedCount > 0" class="filter-count">{{ failedCount }}</span>
        </button>
      </div>
      <div class="toolbar-actions">
        <button class="action-btn" @click="toggleExpandAll">
          <ExpandOutlined v-if="!allExpanded" />
          <NodeCollapseOutlined v-else />
          {{ allExpanded ? 'Collapse All' : 'Expand All' }}
        </button>
      </div>
    </div>

    <!-- Steps -->
    <div class="steps-container">
      <div v-for="(step, index) in filteredSteps" :key="step.step_id" :id="`step-${step.step_id}`">
        <StepCard
          :step="step"
          :index="index + 1"
          :default-open="allExpanded || step.status === 'failed'"
        />
      </div>
      <div v-if="filteredSteps.length === 0" class="empty-hint">
        No steps match the current filter.
      </div>
    </div>
  </div>
</template>

<style scoped>
.step-list {
  margin-bottom: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 0 0 30px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.toolbar-icon {
  font-size: 13px;
  color: #bfbfbf;
  margin-right: 4px;
}
.filter-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: #8c8c8c;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.filter-btn:hover {
  background: #f5f5f5;
  color: #595959;
}
.filter-btn.active {
  background: #f0f2f5;
  color: #262626;
  font-weight: 500;
  border-color: #d9d9d9;
}
.filter-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  background: #ff4d4f;
  color: #fff;
  font-size: 10px;
  padding: 0 4px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  background: none;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  color: #8c8c8c;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}
.action-btn:hover {
  background: #f5f5f5;
  color: #595959;
  border-color: #d9d9d9;
}

.steps-container {
  padding-left: 0;
}
.empty-hint {
  text-align: center;
  color: #bfbfbf;
  font-size: 13px;
  padding: 40px 0;
  margin-left: 30px;
}
</style>
