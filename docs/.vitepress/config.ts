import { defineConfig } from "vitepress";

export default defineConfig({
  base: "/Skiritai/",

  locales: {
    root: {
      label: "English",
      lang: "en-US",
      link: "/",
      title: "Skiritai",
      description: "AI-driven browser test automation framework",
      themeConfig: {
        nav: [
          { text: "Guide", link: "/guide/getting-started" },
          { text: "API", link: "/api/" },
        ],
        sidebar: {
          "/guide/": [
            {
              text: "Guide",
              items: [
                { text: "Getting Started", link: "/guide/getting-started" },
                { text: "Installation", link: "/guide/installation" },
                { text: "Writing Test Cases", link: "/guide/writing-cases" },
                { text: "CLI Commands", link: "/guide/cli" },
                { text: "Browser Sessions", link: "/guide/browser-sessions" },
                { text: "Replay Scripts", link: "/guide/replay-scripts" },
                { text: "Perception Layer", link: "/guide/perception" },
                { text: "Web Server", link: "/guide/web-server" },
                { text: "Configuration", link: "/guide/configuration" },
              ],
            },
          ],
          "/api/": [
            {
              text: "API Reference",
              items: [
                { text: "Overview", link: "/api/" },
                { text: "BaseCase", link: "/api/base-case" },
                { text: "AIContext", link: "/api/ai-context" },
                { text: "Tools", link: "/api/tools" },
                { text: "LLM Providers", link: "/api/llm-providers" },
                { text: "Event Bus", link: "/api/event-bus" },
              ],
            },
          ],
        },
        socialLinks: [
          { icon: "github", link: "https://github.com/Ktovoz/Skiritai" },
        ],
        search: { provider: "local" },
        footer: {
          message: "Released under the MIT License.",
          copyright: "Copyright © 2025 Joe Shen",
        },
      },
    },

    zh: {
      label: "简体中文",
      lang: "zh-CN",
      link: "/zh/",
      title: "Skiritai",
      description: "AI 驱动的浏览器测试自动化框架",
      themeConfig: {
        nav: [
          { text: "指南", link: "/zh/guide/getting-started" },
          { text: "API", link: "/zh/api/" },
        ],
        sidebar: {
          "/zh/guide/": [
            {
              text: "指南",
              items: [
                { text: "快速开始", link: "/zh/guide/getting-started" },
                { text: "安装", link: "/zh/guide/installation" },
                { text: "编写测试用例", link: "/zh/guide/writing-cases" },
                { text: "CLI 命令", link: "/zh/guide/cli" },
                { text: "浏览器会话", link: "/zh/guide/browser-sessions" },
                { text: "回放脚本", link: "/zh/guide/replay-scripts" },
                { text: "感知层", link: "/zh/guide/perception" },
                { text: "Web 服务器", link: "/zh/guide/web-server" },
                { text: "配置", link: "/zh/guide/configuration" },
              ],
            },
          ],
          "/zh/api/": [
            {
              text: "API 参考",
              items: [
                { text: "概览", link: "/zh/api/" },
                { text: "BaseCase", link: "/zh/api/base-case" },
                { text: "AIContext", link: "/zh/api/ai-context" },
                { text: "工具", link: "/zh/api/tools" },
                { text: "LLM 提供商", link: "/zh/api/llm-providers" },
                { text: "事件总线", link: "/zh/api/event-bus" },
              ],
            },
          ],
        },
        socialLinks: [
          { icon: "github", link: "https://github.com/Ktovoz/Skiritai" },
        ],
        search: { provider: "local" },
        footer: {
          message: "基于 MIT 许可证发布。",
          copyright: "Copyright © 2025 Joe Shen",
        },
      },
    },
  },
});
