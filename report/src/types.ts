export interface Screenshot {
  name: string
  path: string  // base64 data URI
}

export interface Verification {
  assertion: string
  passed: boolean
  reason: string
  screenshot: string | null
}

export interface StepEntry {
  step_id: string
  type?: 'action' | 'verify' | 'screenshot'
  status: 'success' | 'failed'
  mode: 'explore' | 'replay' | 'verify' | 'screenshot' | null
  summary: string
  elapsed: number
  screenshots: Screenshot[]
  verifications: Verification[]
  error?: string
}

export interface ReportData {
  case_name: string
  status: 'completed' | 'failed'
  total_steps: number
  success_count: number
  failed_count: number
  steps: StepEntry[]
  phase: string
  elapsed_seconds: number
  error?: string
}
