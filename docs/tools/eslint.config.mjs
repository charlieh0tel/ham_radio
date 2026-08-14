// Lint the pages' extracted JSX.
//
// The pages ship as single HTML files with the app inside a
// <script type="text/babel"> block, so eslint cannot read them directly.  It
// lints the same generated .check/*.jsx the type checker uses, which means a
// diagnostic's line number matches the HTML.
//
// The rule this exists for is react-hooks/exhaustive-deps.  A dependency array
// that quietly lists a derived object rather than the inputs behind it is a
// class of bug nothing but a linter finds.  antenna-matching.html is the page
// with hooks; sherwood.html is plain JS, and gets the recommended rules only.

import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';

// Browser globals both pages use.  eslint has no built-in browser environment
// under flat config and the `globals` package is not a dependency here, so the
// set is spelled out; add to it when a page starts using something new.
const BROWSER_GLOBALS = {
  window: 'readonly', document: 'readonly', console: 'readonly',
  navigator: 'readonly', fetch: 'readonly',
  setTimeout: 'readonly', clearTimeout: 'readonly',
  matchMedia: 'readonly', DOMParser: 'readonly',
  URL: 'readonly', URLSearchParams: 'readonly', Blob: 'readonly',
};

const COMMON_RULES = {
  ...js.configs.recommended.rules,
  // Unused vars are worth seeing; unused args, and the siblings of a rest
  // element (the idiom for dropping a key from an object), are not.
  'no-unused-vars': ['warn', { args: 'none', ignoreRestSiblings: true }],
};

export default [
  {
    files: ['.check/antenna-matching.jsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...BROWSER_GLOBALS, React: 'readonly', ReactDOM: 'readonly',
                 math: 'readonly', fmin: 'readonly' },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...COMMON_RULES,
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  {
    // Plain JS, no JSX and no hooks.  Its entry points are named only by
    // inline on* attributes in the markup, which no-unused-vars cannot see;
    // each carries a disable comment saying so.
    files: ['.check/sherwood.jsx'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...BROWSER_GLOBALS, Chart: 'readonly' },
    },
    rules: COMMON_RULES,
  },
];
