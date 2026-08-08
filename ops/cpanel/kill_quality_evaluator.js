const { execFileSync } = require("node:child_process");

const output = execFileSync("ps", ["-u", String(process.getuid()), "-o", "pid=,args="], {
  encoding: "utf8",
});
const pids = output
  .split("\n")
  .map((line) => line.trim())
  .filter((line) => line.includes("evaluate_advisor_quality.py"))
  .map((line) => Number(line.split(/\s+/, 1)[0]))
  .filter((pid) => Number.isInteger(pid) && pid > 1 && pid !== process.pid);

for (const pid of pids) {
  try {
    process.kill(pid, "SIGTERM");
  } catch {}
}
console.log(`Stopped ${pids.length} quality evaluator process(es)`);
