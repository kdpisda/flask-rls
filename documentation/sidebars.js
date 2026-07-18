// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'intro',
    'installation',
    'quick-start',
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/configuration',
        'guides/context',
        'guides/policies',
        'guides/alembic',
        'guides/testing',
      ],
    },
    {
      type: 'category',
      label: 'Examples',
      items: [
        'examples/tenant-based',
        'examples/user-based',
        'examples/expression-policy',
      ],
    },
    'api-reference',
  ],
};

module.exports = sidebars;
