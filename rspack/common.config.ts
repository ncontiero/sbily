import path from "node:path";
import { defineConfig } from "@rspack/cli";
import { type SwcLoaderOptions, rspack } from "@rspack/core";
import BundleTracker from "webpack-bundle-tracker";

const BASE_PATH = path.join(import.meta.dirname, "../");
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
    filename: "js/[name].js",
    chunkFilename: "js/[name].js",
    cssFilename: "css/[name].css",
    assetModuleFilename: "assets/[name][ext]",
    clean: true,
  },
  plugins: [
    new BundleTracker({
      path: path.resolve(BASE_PATH),
      filename: "webpack-stats.json",
    }),
    new rspack.DefinePlugin({
      "process.env.NODE_ENV": JSON.stringify(process.env.NODE_ENV),
      "process.env.STRIPE_PUBLIC_KEY": JSON.stringify(
        process.env.STRIPE_PUBLIC_KEY,
      ),
    }),
  ],
  module: {
    rules: [
      {
        test: /\.(?:js|jsx|ts|tsx)$/,
        use: [
          {
            loader: "builtin:swc-loader",
            options: {
              detectSyntax: "auto",
            } satisfies SwcLoaderOptions,
          },
        ],
        type: "javascript/auto",
      },
      {
        test: /\.css$/,
        type: "css",
        use: ["postcss-loader"],
      },
    ],
  },
  resolve: {
    modules: ["node_modules"],
    extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
    alias: {
      "@": path.resolve(SBILY_PATH, "src"),
    },
  },
  experiments: {
    css: true,
  },
});
