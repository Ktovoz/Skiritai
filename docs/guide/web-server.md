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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cases/` | List all test cases |
| `GET` | `/api/cases/{id}` | Get case details |
| `POST` | `/api/cases/{id}/run` | Run a test case |
| `POST` | `/api/cases/{id}/stop` | Stop a running case |
| `GET` | `/api/cases/{id}/scripts` | List generated replay scripts |
| `GET` | `/api/cases/{id}/results` | View test results |

## WebSocket

Connect to `ws://localhost:8000/api/ws/cases/{case_id}` for real-time event streaming:

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/cases/my_test");
ws.onmessage = (event) => {
  console.log(JSON.parse(event.data));
};
```

Events include step start/end, tool calls, screenshots, and errors.
