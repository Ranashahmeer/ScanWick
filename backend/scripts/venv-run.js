#!/usr/bin/env node
// Cross-platform launcher for tools installed in the backend's .venv.
// package.json scripts can't hardcode a Unix-style "./.venv/bin/<tool>" path —
// cmd.exe refuses to execute forward-slash relative paths at all, and a
// Windows venv uses .venv/Scripts instead of .venv/bin anyway. Node resolves
// both correctly, so scripts call this instead: `node scripts/venv-run.js <tool> [args...]`.
const path = require("path");
const { spawnSync } = require("child_process");

const [tool, ...args] = process.argv.slice(2);
const binDir = process.platform === "win32" ? "Scripts" : "bin";
const exeSuffix = process.platform === "win32" ? ".exe" : "";
const toolPath = path.join(__dirname, "..", ".venv", binDir, tool + exeSuffix);

const result = spawnSync(toolPath, args, { stdio: "inherit" });
if (result.error) throw result.error;
process.exit(result.status ?? 1);
