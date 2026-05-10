# Web Server

Skiritai includes an optional FastAPI web server for remote test management.

## Install

```bash
pip install -e ".[web]"
```

## Start

```bash
skiritai serve
```

The server starts at `http://localhost:8000` by default.

## REST API

### Case Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cases/` | List all test cases |
| `GET` | `/api/cases/{id}` | Get case details with steps |
| `POST` | `/api/cases/{id}/run` | Run a test case |
| `POST` | `/api/cases/{id}/stop` | Stop a running case |
| `GET` | `/api/health` | Health check |

### Script Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cases/{id}/scripts` | List all generated replay scripts |
| `GET` | `/api/cases/{id}/scripts/{step}` | Get script content |
| `PUT` | `/api/cases/{id}/scripts/{step}` | Update script content |
| `POST` | `/api/cases/{id}/scripts/{step}/solidify` | Solidify a script for replay mode |

### Result Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cases/{id}/results` | List all historical execution results |
| `GET` | `/api/cases/{id}/results/{timestamp}` | Get a specific run's report + screenshot list |
| `GET` | `/api/cases/{id}/results/{timestamp}/screenshots/{file}` | Serve screenshot PNG |

## WebSocket

Connect to `ws://localhost:8000/api/ws/cases/{case_id}` for real-time event streaming:

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/cases/my_test");
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  // msg.type: "node_status" | "log" | "execution_status"
  console.log(msg);
};
```

### WebSocket Message Types

| Type | Description |
|------|-------------|
| `node_status` | Step started (`running`), completed (`success`), or failed (`failed`) |
| `log` | Tool call or log message from the execution engine |
| `execution_status` | Execution started (`running`) or completed with full report |

### Sending Commands

The server accepts `{"command": "stop"}` to cancel a running execution:

```javascript
ws.send(JSON.stringify({ command: "stop" }));
```
