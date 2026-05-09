export interface CaseStep {
  id: string
  name: string
  mode: 'explore' | 'solidified'
  description: string
  url?: string
}

export interface Case {
  id: string
  name: string
  description: string
  steps: CaseStep[]
}

export interface CaseSummary {
  id: string
  name: string
  description: string
  steps: number
  case_dir: string
}

export interface Script {
  step_id: string
  path: string
  content: string
}

export interface StepResult {
  step_id: string
  status: 'success' | 'failed'
  mode: string
  summary?: string
  error?: string
}

export interface ExecutionReport {
  case_id: string
  case_name: string
  status: 'completed' | 'failed' | 'cancelled' | 'error'
  total_steps: number
  success_count: number
  failed_count: number
  timestamp: string
  steps: StepResult[]
}

export interface ExecutionResult {
  timestamp: string
  report: ExecutionReport
  screenshots?: string[]
}

export interface WSMessage {
  type: 'node_status' | 'execution_status' | 'log'
  node_id?: string
  status?: string
  data?: {
    message?: string
    summary?: string
    error?: string
    report?: ExecutionReport
  }
}
