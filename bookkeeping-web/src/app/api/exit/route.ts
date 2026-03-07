import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

const PID_FILE = path.join(process.cwd(), ".dev-server.pid");

export async function POST() {
  try {
    const pidText = await fs.readFile(PID_FILE, "utf-8").catch(() => "");
    const pid = Number(pidText.trim());
    if (!Number.isNaN(pid) && pid > 0) {
      try {
        process.kill(pid, "SIGTERM");
      } catch {
        // Ignore if process is already gone.
      }
    }
    await fs.unlink(PID_FILE).catch(() => undefined);
  } catch {
    // Ignore cleanup errors and continue shutdown flow.
  }

  setTimeout(() => {
    process.exit(0);
  }, 300);

  return NextResponse.json({ ok: true, message: "服务正在退出" });
}
