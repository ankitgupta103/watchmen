/**
 * @see https://prettier.io/docs/en/configuration.html
 * @type {import("prettier").Config}
 */
const config = {
  printWidth: 80,
  semi: true,
  singleQuote: true,
  tabWidth: 2,
  tailwindConfig: 'tailwind.config.ts',
  trailingComma: 'all',
  plugins: [
    '@ianvs/prettier-plugin-sort-imports',
    'prettier-plugin-tailwindcss',
  ],
  importOrder: [
    '^react$',
    '<THIRD_PARTY_MODULES>',
    '',
    '^@/components/(.*)$',
    '',
    '^@/lib/(.*)$',
    '',
    '^@/app/(.*)$',
    '',
    '^[./]',
  ],
};

export default config;
