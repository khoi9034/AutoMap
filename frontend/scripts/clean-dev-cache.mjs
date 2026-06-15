import { rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(scriptDir, "..");
const nextCachePath = resolve(frontendRoot, ".next");

if (!nextCachePath.startsWith(frontendRoot)) {
  console.error(`Refusing to remove path outside frontend: ${nextCachePath}`);
  process.exit(1);
}

await rm(nextCachePath, { recursive: true, force: true });
console.log("AutoMap dev cache prepared.");
