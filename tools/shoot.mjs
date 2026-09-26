// Screenshot the website with headless Chrome over the DevTools protocol (no extra packages).
// Usage: node tools/shoot.mjs <url> <out.png> [section-id] [waitSeconds] [width] [height] [theme]
// Scrolls natively (?nolenis) to the section so the 3D camera rig is at that keyframe.
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const [url, out, section = "", wait = "10", width = "1440", height = "900", theme = "dark", offset = "1"] = process.argv.slice(2);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9300 + Math.floor(Math.random() * 400);
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${port}`, "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
  "--hide-scrollbars", `--window-size=${width},${height}`, "--user-data-dir=/tmp/hb-shoot-" + port, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
try {
  let ws;
  for (let i = 0; i < 50 && !ws; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
    } catch { await sleep(200); }
  }
  await new Promise((r) => ws.addEventListener("open", r));
  let id = 0;
  const pending = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === "Runtime.exceptionThrown") console.log("[page exception]", m.params.exceptionDetails?.exception?.description?.slice(0, 300));
    if (m.method === "Runtime.consoleAPICalled")
      console.log(`[page ${m.params.type}]`, m.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 300));
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: +width, height: +height, deviceScaleFactor: 1, mobile: +width < 600 });
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `try{localStorage.setItem('theme','${theme}')}catch(e){}` });
  const sep = url.includes("?") ? "&" : "?";
  await send("Page.navigate", { url: `${url}${sep}nolenis=1${section ? "#" + section : ""}` });
  await sleep(9000); // let hydration finish (the page resets to the top on mount)
  if (section) {
    await send("Runtime.evaluate", { expression: `(() => { const el = document.getElementById('${section}'); if (el) { window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + ${+offset}); window.dispatchEvent(new Event('scroll')); } })()` });
  }
  await sleep(+wait * 1000);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(out, Buffer.from(shot.result.data, "base64"));
  console.log("saved", out);
} finally {
  chrome.kill("SIGKILL");
}
