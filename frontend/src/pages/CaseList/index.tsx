import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, message } from 'antd'
import { PlayCircleOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { caseApi } from '../../services/api'
import type { CaseSummary } from '../../types/case'

export default function CaseList() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<CaseSummary[]>([])
  const [loading, setLoading] = useState(false)

  const loadCases = async () => {
    setLoading(true)
    try {
      const data = await caseApi.list()
      setCases(data)
    } catch {
      message.error('加载用例列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCases()
  }, [])

  const handleRun = async (caseId: string) => {
    try {
      await caseApi.run(caseId)
      message.success('执行已启动')
      navigate(`/case/${caseId}`)
    } catch {
      message.error('启动执行失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 200,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '步骤数',
      dataIndex: 'steps',
      key: 'steps',
      width: 100,
      render: (count: number) => <Tag>{count} 步</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: CaseSummary) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/case/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record.id)}
          >
            执行
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>测试用例</h2>
        <Button onClick={loadCases}>刷新</Button>
      </div>
      <Table
        columns={columns}
        dataSource={cases}
        rowKey="id"
        loading={loading}
        pagination={false}
      />
    </div>
  )
}
