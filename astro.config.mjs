import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// TODO: 部署前把 USERNAME 换成你的 GitHub 用户名
export default defineConfig({
  site: 'https://shuhui-sh.github.io',
  integrations: [sitemap()],
  markdown: {
    shikiConfig: {
      themes: { light: 'github-light', dark: 'github-dark' },
      defaultColor: false,
      wrap: true,
    },
  },
});
