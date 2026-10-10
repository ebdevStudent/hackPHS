// Node module hook: resolve the browser import-map specifiers ("three", "three/addons/...") to the vendored files.
import { pathToFileURL } from "node:url";
import path from "node:path";
const VENDOR = path.resolve(import.meta.dirname, "../../static/vendor");
export async function resolve(spec, ctx, next) {
  if (spec === "three") return { url: pathToFileURL(path.join(VENDOR, "three.module.js")).href, shortCircuit: true };
  if (spec.startsWith("three/addons/")) return { url: pathToFileURL(path.join(VENDOR, "addons", spec.slice(13))).href, shortCircuit: true };
  return next(spec, ctx);
}
