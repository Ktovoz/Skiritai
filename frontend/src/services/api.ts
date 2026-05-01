import axios from 'axios'
import type { Case, CaseSummary, Script, ExecutionResult } from '../types/case'

const http = axios.create({ baseURL: '/api' })

export const caseApi = {
  list: () =>
    http.get<CaseSummary[]>('/cases').then(r => r.data),

  get: (id: string) =>
    http.get<Case>(`/cases/${id}`).then(r => r.data),

  run: (id: string) =>
    http.post<{ case_id: string; status: string; message: string }>(`/cases/${id}/run`).then(r => r.data),

  scripts: (id: string) =>
    http.get<Script[]>(`/cases/${id}/scripts`).then(r => r.data),

  getScript: (caseId: string, stepId: string) =>
    http.get<Script>(`/cases/${caseId}/scripts/${stepId}`).then(r => r.data),

  updateScript: (caseId: string, stepId: string, content: string) =>
    http.put<Script>(`/cases/${caseId}/scripts/${stepId}`, { content }).then(r => r.data),

  solidify: (caseId: string, stepId: string) =>
    http.post(`/cases/${caseId}/scripts/${stepId}/solidify`).then(r => r.data),

  results: (id: string) =>
    http.get<ExecutionResult[]>(`/cases/${id}/results`).then(r => r.data),

  getResult: (caseId: string, timestamp: string) =>
    http.get<ExecutionResult>(`/cases/${caseId}/results/${timestamp}`).then(r => r.data),
}
