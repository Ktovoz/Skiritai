# 路线图

Skiritai 正在快速迭代，以下是接下来的发展方向。

## 视觉感知层

当前 AI 探索依赖 DOM 分析和 CSS 选择器。下一个重大升级将引入**视觉感知**能力 — 智能体将像人类测试员一样"看见"页面。

### 基于视觉的 AI 探索

- **截图理解** — 智能体通过解读页面截图，根据视觉特征识别 UI 元素，而非仅依赖 DOM 结构
- **Canvas 与 WebGL 支持** — 与无 DOM 可访问的界面交互（图表、游戏、媒体播放器）
- **布局感知导航** — 理解元素间的空间关系，实现更自然的交互模式

### 多模态模型支持

- **视觉语言模型** — 接入 GPT-4o、Claude 3.5 Sonnet、Gemini 等 VLM，实现更丰富的页面理解
- **原生多模态模型** — 支持内置视觉能力的模型，减少对独立 DOM 分析步骤的依赖
- **模型无关的感知层** — 感知层自动适配已配置的模型，选择最优策略

### 视觉回归检测

- **跨运行截图对比** — 自动发现测试执行间的非预期 UI 变化
- **差异高亮** — 生成可视化 Diff，精确展示页面变化
- **基线管理** — 维护已审核的截图基线，标记偏差

---

## 多端与跨端测试

Skiritai 目前仅支持 **Web** 端测试（基于 Playwright/Chromium）。我们计划将相同的「探索 → 回放」工作流扩展到更多平台。

### 当前：Web 端

- 基于 Playwright 的浏览器自动化
- 14 个内置工具（navigate、click、fill、scroll 等）
- 基于 CDP 的持久化浏览器会话

### 规划中：移动端（iOS / Android）

- Appium 或 browser-use mobile 集成
- 相同的 `BaseCase` API — 一次编写用例，在移动设备上运行
- 触控手势支持（点击、滑动、缩放）
- 真机与模拟器/仿真器支持

### 规划中：API 测试

- AI 智能体可用的 HTTP 请求工具（GET、POST、PUT、DELETE）
- JSON Schema 验证与响应断言
- 在同一用例中混合 API 调用与浏览器步骤
- 认证流程支持（OAuth、API Key、JWT）

### 调研中：桌面端

- Playwright Electron 支持用于 Electron 应用
- 原生桌面应用的系统级自动化
- 跨窗口交互模式

### 愿景

目标是构建**统一的测试框架**，相同的「探索 → 回放」工作流在 Web、移动端、API 上通用 — 一次编写，到处测试。

```python
class CrossPlatformCase(BaseCase):
    async def web_login(self):
        await self.ai.action("登录 Web 应用")

    async def api_check(self):
        await self.ai.action("验证用户资料 API 返回正确数据")

    async def mobile_notification(self):
        await self.ai.action("检查移动端是否收到推送通知")
```

---

## 近期已完成

| 功能 | 说明 |
|------|------|
| **可视化报告** | Vue 3 + Ant Design 独立 HTML 报告，包含截图、断言和步骤详情 |
| **`ai.screenshot()`** | 测试执行中捕获命名截图 |
| **`ai.verify()`** | 自然语言断言 API |
| **`@max_steps`** | 按步骤控制智能体递归限制的装饰器 |
| **失败策略** | `@on_failure(SKIP/RETRY)` 实现多步骤弹性流程 |
