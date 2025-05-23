import { ncontiero } from "@ncontiero/eslint-config";

export default ncontiero(
  {
    ignores: ["**/*.html", "**/countries-50m.json"],
    javascript: {
      overrides: {
        "node/no-unsupported-features/node-builtins": [
          "error",
          { allowExperimental: true },
        ],
      },
    },
    unicorn: {
      overrides: { "unicorn/prefer-query-selector": "off" },
    },
    toml: {
      overrides: { "toml/indent": ["error", 4] },
    },
  },
  {
    files: ["sbily/src/vendors.ts"],
    rules: {
      "perfectionist/sort-objects": "error",
    },
  },
  {
    files: ["emails/**"],
    rules: {
      "import/no-default-export": "off",
    },
  },
);
