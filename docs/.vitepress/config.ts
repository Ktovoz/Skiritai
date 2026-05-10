import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Skiritai",
  description: "AI-driven browser test automation framework",
  base: "/Skiritai/",

  head: [["link", { rel: "icon", href: "/Skiritai/favicon.ico" }]],

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

    search: {
      provider: "local",
    },

    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2025 Joe Shen",
    },
  },
});
