import * as path from "node:path";
import { defineConfig } from "@rspack/cli";
import { rspack } from "@rspack/core";
import BundleTracker from "webpack-bundle-tracker";

// Target browsers, see: https://github.com/browserslist/browserslist
const BROWSER_TARGETS = [
  "chrome >= 87",
  "edge >= 88",
  "firefox >= 78",
  "safari >= 14",
];

const BASE_PATH = path.join(__dirname, "../");
const SBILY_PATH = path.join(BASE_PATH, "sbily");

export const commonConfig = defineConfig({
  target: "web",
  context: BASE_PATH,
  entry: {
    main: path.resolve(SBILY_PATH, "src/index.ts"),
    vendors: path.resolve(SBILY_PATH, "src/vendors.ts"),
  },
  output: {
    path: path.resolve(SBILY_PATH, "static/rspack_bundles/"),
    publicPath: "/static/rspack_bundles/",
    filename: "js/[name]-[fullhash].js",
    chunkFilename: "js/[name]-[hash].js",
    cssFilename: "css/[name]-[contenthash].css",
    assetModuleFilename: "assets/[name]-[hash][ext]",
    clean: true,
  },
  plugins: [
    new BundleTracker({
      path: path.resolve(BASE_PATH),
      filename: "webpack-stats.json",
    }),
    new rspack.EnvironmentPlugin(["NODE_ENV", "STRIPE_PUBLIC_KEY"]),
  ],
  module: {
    rules: [
      {
        test: /\.[jt]s$/,
        use: [
          {
            loader: "builtin:swc-loader",
            options: {
              jsc: { parser: { syntax: "typescript" } },
              env: { targets: BROWSER_TARGETS },
            },
          },
        ],
      },
      {
        test: /\.css$/,
        type: "css",
        use: [
          {
            loader: "postcss-loader",
            options: {
              postcssOptions: {
                plugins: ["postcss-preset-env", "autoprefixer", "tailwindcss"],
              },
            },
          },
        ],
      },
    ],
  },
  optimization: {
    minimizer: [
      new rspack.SwcJsMinimizerRspackPlugin(),
      new rspack.LightningCssMinimizerRspackPlugin({
        minimizerOptions: { targets: BROWSER_TARGETS },
      }),
    ],
  },
  resolve: {
    modules: ["node_modules"],
    extensions: ["...", ".ts"],
    alias: {
      "@": path.resolve(SBILY_PATH, "src"),
    },
  },
  experiments: {
    css: true,
  },
});
