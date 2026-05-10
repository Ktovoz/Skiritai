# Web 服务器

Skiritai 内置一个可选的 FastAPI Web 服务器，用于远程测试管理。

## 安装

```bash
pip install -e ".[web]"
```

## 启动

```bash
skiritai serve
```

默认在 `http://localhost:8000` 启动服务。

## REST API

| 方法 | 端点 | 描述 |
|--------|----------|-------------|
| `GET` | `/api/cases/` | 列出所有测试用例 |
| `GET` | `/api/cases/{id}` | 获取用例详情 |
| `POST` | `/api/cases/{id}/run` | 运行测试用例 |
| `POST` | `/api/cases/{id}/stop` | 停止正在运行的用例 |
| `GET` | `/api/cases/{id}/scripts` | 列出已生成的回放脚本 |
| `GET` | `/api/cases/{id}/results` | 查看测试结果 |

## WebSocket

连接 `ws://localhost:8000/api/ws/cases/{case_id}` 获取实时事件流：

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/cases/my_test");
ws.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

事件类型包括：步骤开始/结束、工具调用、截图和错误。
