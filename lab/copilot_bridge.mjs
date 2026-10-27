// Enmo Safety lab — Copilot SDK bridge.
// Author: m03 (Intel) | Revision: 1.1
// Revision History:
//   1.0 — list live models; answer JSONL chat requests with a replaced system
//         message and no tools, so the model sees exactly the harness prompt.
//   1.1 — sessions are tagged clientName=enmo-safety-lab and deleted after each
//         request: benchmark prompts are not persisted and the store stays small.
//
// Usage:
//   node copilot_bridge.mjs --list
//   node copilot_bridge.mjs --serve   (stdin: one JSON request per line; stdout: one JSON reply per line)
//   request: {"id": "...", "model": "gpt-4.1", "system": "...", "prompt": "...", "timeout_ms": 120000}

import { pathToFileURL } from "node:url";
import { homedir } from "node:os";
import { join } from "node:path";
import { existsSync, readdirSync } from "node:fs";
import readline from "node:readline";

function sdkPath() {
  if (process.env.COPILOT_SDK_PATH) return process.env.COPILOT_SDK_PATH;
  const base = join(homedir(), ".copilot", "pkg", "universal");
  const versions = existsSync(base) ? readdirSync(base).sort() : [];
  for (const v of versions.reverse()) {
    const p = join(base, v, "copilot-sdk", "index.js");
    if (existsSync(p)) return p;
  }
  throw new Error("copilot-sdk not found; set COPILOT_SDK_PATH");
}

const sdk = await import(pathToFileURL(sdkPath()).href);
const client = new sdk.CopilotClient({ logLevel: "error" });
await client.start();

const out = (obj) => process.stdout.write(JSON.stringify(obj) + "\n");

async function chat(req) {
  const t0 = Date.now();
  const session = await client.createSession({
    clientName: "enmo-safety-lab",
    model: req.model,
    systemMessage: { mode: "replace", content: req.system || "You are a helpful assistant." },
    availableTools: [],
    onPermissionRequest: async () => ({ kind: "denied-interactively-by-user" }),
  });
  try {
    const ev = await session.sendAndWait({ prompt: req.prompt }, req.timeout_ms || 180000);
    return { id: req.id, ok: true, text: ev?.data?.content ?? "", latency_ms: Date.now() - t0 };
  } finally {
    const sid = session.sessionId;
    await session.destroy().catch(() => {});
    if (sid) await client.deleteSession(sid).catch(() => {});
  }
}

const mode = process.argv[2] || "--list";
try {
  if (mode === "--list") {
    const models = await client.listModels();
    out(models.map((m) => ({ id: m.id, name: m.name, policy: m.policy?.state ?? null,
                             billing: m.billing ?? null })));
  } else if (mode === "--serve") {
    const rl = readline.createInterface({ input: process.stdin });
    for await (const line of rl) {
      if (!line.trim()) continue;
      let req;
      try { req = JSON.parse(line); } catch { out({ ok: false, error: "bad json" }); continue; }
      try { out(await chat(req)); }
      catch (e) { out({ id: req.id, ok: false, error: String(e?.message || e) }); }
    }
  }
} finally {
  await client.stop();
}
