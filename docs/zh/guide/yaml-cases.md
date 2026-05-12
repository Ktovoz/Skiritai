# YAML 用例

完全用 YAML 定义测试用例 — 无需编写 Python 代码。AI 智能体将像执行 Python `BaseCase` 一样执行每个步骤。

## 基本结构

```yaml
# case.yaml
name: 搜索测试
headless: false
max_steps: 20
url: https://www.baidu.com
steps:
  - name: 搜索
    action: 搜索 "Playwright 自动化"

  - name: 验证
    verify: 搜索结果已展示

  - name: 截图
    screenshot: search_result
```

将 `case.yaml`（或 `case.yml`）放入目录中，然后通过 CLI 运行。

## 运行 YAML 用例

```bash
# 通过 CLI
skiritai run examples/baidu_yaml

# 通过 Python
from skiritai import run_yaml_case
from pathlib import Path
import asyncio

report = asyncio.run(run_yaml_case(Path("examples/baidu_yaml")))
```

## 步骤类型

| 步骤键 | 说明 | 必需参数 |
|---|---|---|
| `action` | 自然语言操作 → AI 执行 | 操作描述字符串 |
| `verify` | 自然语言断言 → AI 验证（失败不阻断） | 断言字符串 |
| `screenshot` | 按名称截图 | 截图名称 |
| `analyze` | 预分析页面 DOM（上下文注入后续 action） | （忽略） |
| `page_info` | 获取页面标题、URL、文本摘要 | （忽略） |

## 步骤级选项

每个步骤可指定 `on_failure` 策略：

```yaml
steps:
  - action: 点击"高级设置"链接
    on_failure: skip    # 即使失败也继续执行

  - action: 提交表单
    on_failure: abort   # 失败时停止执行（默认）
```

| 策略 | 行为 |
|---|---|
| `abort`（默认） | 失败时停止整个用例 |
| `skip` | 记录警告并继续下一步 |

## 顶层字段

| 字段 | 必需 | 默认值 | 说明 |
|---|---|---|---|
| `name` | 否 | 目录名 | 用例显示名称 |
| `steps` | **是** | — | 步骤定义列表 |
| `headless` | 否 | 环境变量或 `false` | 无头模式运行浏览器 |
| `max_steps` | 否 | `20` | 每个 action 的最大工具调用步数 |
| `url` | 否 | — | 运行步骤前先导航到此 URL |

## 列出 YAML 用例

```bash
skiritai list examples/
```

YAML 用例会与 Python 用例一起自动发现。每个包含 `case.yaml` 或 `case.yml` 文件的目录都会被列为用例。
