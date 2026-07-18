// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const { themes } = require('prism-react-renderer');
const lightCodeTheme = themes.github;
const darkCodeTheme = themes.dracula;

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Flask RLS',
  tagline: 'PostgreSQL Row-Level Security for Flask and SQLAlchemy',
  favicon: 'img/favicon.svg',

  url: 'https://flask-rls.com',
  baseUrl: '/',

  // GitHub pages deployment config.
  organizationName: 'kdpisda',
  projectName: 'flask-rls',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: 'docs',
          editUrl: 'https://github.com/kdpisda/flask-rls/tree/main/documentation/',
        },
        blog: false,
        sitemap: {
          lastmod: 'date',
          changefreq: 'weekly',
          priority: 0.5,
          filename: 'sitemap.xml',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Flask RLS',
        logo: {
          alt: 'Flask RLS Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://pypi.org/project/flask-rls/',
            label: 'PyPI',
            position: 'right',
          },
          {
            href: 'https://github.com/kdpisda/flask-rls',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Introduction', to: '/docs/intro' },
              { label: 'Installation', to: '/docs/installation' },
              { label: 'Quick Start', to: '/docs/quick-start' },
              { label: 'API Reference', to: '/docs/api-reference' },
            ],
          },
          {
            title: 'Community',
            items: [
              { label: 'GitHub', href: 'https://github.com/kdpisda/flask-rls' },
              { label: 'Issues', href: 'https://github.com/kdpisda/flask-rls/issues' },
            ],
          },
          {
            title: 'More',
            items: [
              { label: 'PyPI Package', href: 'https://pypi.org/project/flask-rls/' },
              { label: 'django-rls', href: 'https://django-rls.com' },
              {
                html: `
                  <a href="https://kdpisda.in" target="_blank" rel="dofollow" class="footer__link-item">
                    Created by Kuldeep Pisda
                  </a>
                `,
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Flask RLS. Built with <a href="https://docusaurus.io" target="_blank" rel="noopener noreferrer">Docusaurus</a>. Created by <a href="https://kdpisda.in" target="_blank" rel="dofollow">Kuldeep Pisda</a>.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
        additionalLanguages: ['python', 'bash', 'sql'],
      },
    }),
};

module.exports = config;
