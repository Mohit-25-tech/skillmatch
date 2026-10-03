import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
const require = createRequire(import.meta.url);
const source = dirname(require.resolve("swagger-ui-dist/package.json"));
const target = resolve("public/docs-assets");
mkdirSync(target, { recursive: true });
for (const file of [
  "swagger-ui-bundle.js",
  "swagger-ui.css",
  "favicon-32x32.png",
]) {
  copyFileSync(resolve(source, file), resolve(target, file));
}
