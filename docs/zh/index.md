---
layout: home

hero:
  name: "Skiritai"
  text: "AI 驱动的浏览器测试自动化"
  tagline: 以斯巴达精锐侦察部队命名——先探索，再以 30 倍速度执行。
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/guide/getting-started
    - theme: alt
      text: GitHub 源码
      link: https://github.com/Ktovoz/Skiritai

features:
  - icon: 🧠
    title: AI 智能探索
    details: 基于 LLM 的 ReAct Agent，自动分析页面、发现 UI 元素并确定操作序列——告别脆弱的 CSS 选择器。
  - icon: ⚡
    title: 30 倍回放速度
    details: 探索完成后，Agent 生成独立的 Python 脚本，直接基于 Playwright 执行，零 AI 开销。
  - icon: 🔤
    title: CJK 感知元素匹配
    details: 针对中、日、韩文字的特殊评分算法，在非英文界面中更精准地定位元素。
  - icon: 🔧
    title: 持久化浏览器会话
    details: 基于 CDP 的可选浏览器生命周期，Python 重启后会话不丢失，随时恢复探索进度。
  - icon: 🌐
    title: Web 仪表盘（可选）
    details: FastAPI 服务 + REST + WebSocket API，支持远程触发、监控和控制测试运行。
  - icon: 📦
    title: 多 LLM 支持
    details: 兼容 OpenAI 系列（GPT、通义千问）、Anthropic Claude 等，通过可插拔 Provider 系统扩展。
---
