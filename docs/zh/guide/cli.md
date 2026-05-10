# CLI 命令

Skiritai 提供 `skiritai` 命令行工具，包含以下子命令。

## 运行测试用例

```bash
skiritai run <case_dir>
skiritai run . --case my_test.py
```

选项：

- `--case` — 运行指定的用例文件
- `cases_root` — 测试用例所在目录

## 启动 Web 服务器

```bash
skiritai serve
skiritai serve --host 0.0.0.0 --port 8080
```

## 列出可用用例

```bash
skiritai list
skiritai list examples/
```

## 浏览器会话管理

```bash
# 查看持久化浏览器状态
skiritai browser status <case_dir>

# 终止孤立的浏览器进程
skiritai browser cleanup <case_dir>
```

持久化浏览器模式将 Chromium 作为独立进程运行（通过 CDP),Python 重启后依然存活。会话信息存储在 `.browser_session` 文件中。
