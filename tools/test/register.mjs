// Resolve the browser import-map specifiers ("three", "three/addons/...") to the vendored files.
// Node 22.15+/23.5+ provide the synchronous module.registerHooks(); older versions use register().
import * as module from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const VENDOR = path.resolve(import.meta.dirname, "../../static/vendor");
function target(spec) {
  if (spec === "three") return pathToFileURL(path.join(VENDOR, "three.module.js")).href;
  if (spec.startsWith("three/addons/")) return pathToFileURL(path.join(VENDOR, "addons", spec.slice(13))).href;
  return null;
}
if (typeof module.registerHooks === "function") {
  module.registerHooks({ resolve(spec, context, next) { const url = target(spec); return url ? { url, shortCircuit: true } : next(spec, context); } });
} else {
  module.register("./resolve-three.mjs", import.meta.url);
}
