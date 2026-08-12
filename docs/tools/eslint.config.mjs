// Lint the pages' extracted JSX.
//
// The pages ship as single HTML files with the app inside a
// <script type="text/babel"> block, so eslint cannot read them directly.  It
// lints the same generated .check/*.jsx the type checker uses, which means a
// diagnostic's line number matches the HTML.
//
// The rule this exists for is react-hooks/exhaustive-deps.  A dependency array
// that quietly listed a derived object rather than the inputs behind it let
// switching display units discard the user's wire length; nothing but a linter
// finds that class of bug.

import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    files: ['.check/*.jsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { React: 'readonly', ReactDOM: 'readonly', window: 'readonly',
                 document: 'readonly', URLSearchParams: 'readonly',
                 URL: 'readonly', Blob: 'readonly',
                 console: 'readonly', Chart: 'readonly', math: 'readonly',
                 fmin: 'readonly' },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...js.configs.recommended.rules,
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // The pages define their app inside one scope and never export; unused
      // vars are worth seeing, unused args less so.
      'no-unused-vars': ['warn', { args: 'none' }],
    },
  },
];
