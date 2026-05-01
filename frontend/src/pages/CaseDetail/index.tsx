import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button, Card, Descriptions, List, Tag, Space, message, Typography, Collapse, Image,
} from 'antd'
import {
  ArrowLeftOutlined, PlayCircleOutlined, ReloadOutlined,
} from '@ant-design/icons'
import { caseApi } from '../../services/api'
import { createCaseWS } from '../../services/websocket'
import type { Case, ExecutionResult, WSMessage, ExecutionReport } from '../../types/case'

const { Text } = Typography

export default function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const [caseData, setCaseData] = useState<Case | null>(null)
  const [results, setResults] = useState<ExecutionResult[]>([])
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<WSMessage[]>([])
  const [currentReport, setCurrentReport] = useState<ExecutionReport | null>(null)
  const [stepStatuses, setStepStatuses] = useState<Record<string, string>>({})

  const loadCase = useCallback(async () => {
    if (!caseId) return
    try {
      const data = await caseApi.get(caseId)
      setCaseData(data)
    } catch {
      message.error('加载用例失败')
      navigate('/')
    }
  }, [caseId, navigate])

  const loadResults = useCallback(async () => {
    if (!caseId) return
    try {
      const data = await caseApi.results(caseId)
      setResults(data)
    } catch {
      // ignore
    }
  }, [caseId])

  useEffect(() => {
    loadCase()
    loadResults()
  }, [loadCase, loadResults])

  const handleRun = async () => {
    if (!caseId) return
    setRunning(true)
    setLogs([])
    setCurrentReport(null)
    setStepStatuses({})

    try {
      await caseApi.run(caseId)
      message.success('执行已启动')
    } catch {
      message.error('启动执行失败')
      setRunning(false)
    }
  }

  // WebSocket for real-time updates
  useEffect(() => {
    if (!caseId || !running) return

    const ws = createCaseWS(caseId, (msg: WSMessage) => {
      setLogs(prev => [...prev, msg])

      if (msg.type === 'node_status' && msg.node_id) {
        setStepStatuses(prev => ({
          ...prev,
          [msg.node_id!]: msg.status || 'unknown',
        }))
      }

      if (msg.type === 'execution_status') {
        if (msg.data?.report) {
          setCurrentReport(msg.data.report)
        }
        setRunning(false)
        loadResults()
      }
    })

    return () => ws.close()
  }, [caseId, running, loadResults])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'processing'
      case 'success': return 'success'
      case 'failed': return 'error'
      default: return 'default'
    }
  }

  if (!caseData) return null

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回
        </Button>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={running}
        >
          {running ? '执行中...' : '执行'}
        </Button>
      </Space>

      <Card title={caseData.name} style={{ marginBottom: 16 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="ID">{caseData.id}</Descriptions.Item>
          <Descriptions.Item label="描述">{caseData.description}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="步骤" style={{ marginBottom: 16 }}>
        <List
          dataSource={caseData.steps}
          renderItem={step => (
            <List.Item>
              <Space>
                <Tag color={step.mode === 'solidified' ? 'green' : 'blue'}>
                  {step.mode}
                </Tag>
                <Text strong>{step.name}</Text>
                <Text type="secondary">{step.description}</Text>
                {stepStatuses[step.id] && (
                  <Tag color={getStatusColor(stepStatuses[step.id])}>
                    {stepStatuses[step.id]}
                  </Tag>
                )}
              </Space>
            </List.Item>
          )}
        />
      </Card>

      {/* Real-time execution logs */}
      {logs.length > 0 && (
        <Card title="执行日志" style={{ marginBottom: 16 }}>
          <div style={{ maxHeight: 300, overflow: 'auto', fontFamily: 'monospace', fontSize: 12 }}>
            {logs.map((log, i) => (
              <div key={i} style={{ padding: '2px 0' }}>
                {log.type === 'log' && (
                  <Text>[{log.node_id}] {log.data?.message}</Text>
                )}
                {log.type === 'node_status' && (
                  <Text>
                    [{log.node_id}] 状态: <Tag color={getStatusColor(log.status || '')}>{log.status}</Tag>
                  </Text>
                )}
                {log.type === 'execution_status' && (
                  <Text>
                    执行完成: <Tag color={log.status === 'completed' ? 'success' : 'error'}>{log.status}</Tag>
                  </Text>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Current execution report */}
      {currentReport && (
        <Card title="执行报告" style={{ marginBottom: 16 }}>
          <Descriptions column={2}>
            <Descriptions.Item label="状态">
              <Tag color={currentReport.status === 'completed' ? 'success' : 'error'}>
                {currentReport.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成功/总数">
              {currentReport.success_count}/{currentReport.total_steps}
            </Descriptions.Item>
          </Descriptions>
          <List
            size="small"
            dataSource={currentReport.steps}
            renderItem={step => (
              <List.Item>
                <Space>
                  <Tag color={step.status === 'success' ? 'green' : 'red'}>{step.status}</Tag>
                  <Text>{step.step_id}</Text>
                  {step.error && <Text type="danger">{step.error}</Text>}
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Historical results */}
      {results.length > 0 && (
        <Card title="历史结果">
          <Collapse>
            {results.map(r => (
              <Collapse.Panel
                key={r.timestamp}
                header={
                  <Space>
                    <Tag color={r.report.status === 'completed' ? 'green' : 'red'}>
                      {r.report.status}
                    </Tag>
                    <Text>{r.timestamp}</Text>
                    <Text type="secondary">
                      {r.report.success_count}/{r.report.total_steps} 成功
                    </Text>
                  </Space>
                }
              >
                <List
                  size="small"
                  dataSource={r.report.steps}
                  renderItem={step => (
                    <List.Item>
                      <Space>
                        <Tag color={step.status === 'success' ? 'green' : 'red'}>{step.status}</Tag>
                        <Text>{step.step_id}</Text>
                        {step.error && <Text type="danger">{step.error}</Text>}
                      </Space>
                    </List.Item>
                  )}
                />
                {r.screenshots && r.screenshots.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text strong>截图: </Text>
                    {r.screenshots.map(s => (
                      <Tag key={s}>{s}</Tag>
                    ))}
                  </div>
                )}
              </Collapse.Panel>
            ))}
          </Collapse>
        </Card>
      )}
    </div>
  )
}
