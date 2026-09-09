import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // The Django app that lives on the other branches of this repo — its
    // vendored AdminLTE/jQuery bundles are not ours to lint.
    "cosomis/**",
  ]),
  {
    rules: {
      // French UI copy is full of apostrophes; escaping them hurts readability.
      "react/no-unescaped-entities": "off",
    },
  },
]);

export default eslintConfig;