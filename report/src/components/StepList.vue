<script setup lang="ts">
import type { StepEntry } from '../types'
import StepCard from './StepCard.vue'

defineProps<{ steps: StepEntry[] }>()
</script>

<template>
  <div class="step-list">
    <StepCard
      v-for="(step, index) in steps"
      :key="step.step_id"
      :step="step"
      :index="index + 1"
    />
  </div>
</template>

<style scoped>
.step-list {
  margin-bottom: 16px;
}
</style>
