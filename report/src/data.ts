import type { ReportData } from './types'

const FALLBACK: ReportData = {
  case_name: 'No Data',
  status: 'completed',
  total_steps: 0,
  success_count: 0,
  failed_count: 0,
  steps: [],
  phase: 'done',
  elapsed_seconds: 0,
}

export function loadReportData(): ReportData {
  const el = document.getElementById('report-data')
  if (!el || !el.textContent) return FALLBACK
  try {
    const parsed = JSON.parse(el.textContent)
    if (parsed.placeholder) return FALLBACK
    return parsed as ReportData
  } catch {
    return FALLBACK
  }
}
