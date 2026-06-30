"""A tiny, dependency-free tabbed PDF viewer/editor that runs in the browser.

Run ``python3 -m pdftoolkit.app --dir somefolder`` (or ``pdftoolkit serve``) and
open the printed URL. The page lists PDFs from the chosen storage provider,
opens each in its own **tab**, renders it with the browser's built-in PDF
viewer, and applies notes/highlights through the same engine the CLI uses,
saving the edit back to where the file came from.

This is the thin shell over the engine -- the "lightweight editor" surface.
Everything heavy (parsing, rewriting, annotating) is the standard-library
toolkit; the only runtime here is Python's own ``http.server``.

Storage is pluggable (:mod:`pdftoolkit.storage`): local disk always, and Google
Drive too when an OAuth token is supplied via ``--drive-token`` or the
``GDRIVE_TOKEN`` environment variable.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import annotations, ops
from .document import Document
from .storage import DriveStorage, LocalStorage

PAGE_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>PDF Toolkit</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.4 system-ui, sans-serif; color: #1d2433; height: 100vh; display: flex; flex-direction: column; }
  header { background: #1f2a44; color: #fff; padding: 8px 14px; display: flex; gap: 12px; align-items: center; }
  header b { font-size: 15px; }
  header select, header button { font: inherit; padding: 3px 8px; border-radius: 6px; border: 1px solid #4a5878; background: #2c3a5e; color: #fff; cursor: pointer; }
  .body { flex: 1; display: flex; min-height: 0; }
  .sidebar { width: 210px; border-right: 1px solid #dde2ec; overflow: auto; padding: 8px; }
  .sidebar h3 { margin: 6px 4px; font-size: 12px; text-transform: uppercase; color: #7a869a; }
  .file { padding: 6px 8px; border-radius: 6px; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .file:hover { background: #eef1f7; }
  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .tabs { display: flex; gap: 2px; background: #eef1f7; padding: 4px 4px 0; overflow-x: auto; }
  .tab { padding: 6px 10px; background: #d7dded; border-radius: 8px 8px 0 0; cursor: pointer; white-space: nowrap; display: flex; gap: 6px; align-items: center; }
  .tab.active { background: #fff; font-weight: 600; }
  .tab .x { color: #8893a8; }
  .tab .x:hover { color: #d33; }
  .viewer { flex: 1; background: #525a6b; }
  .viewer iframe { width: 100%; height: 100%; border: 0; }
  .empty { color: #8893a8; padding: 40px; text-align: center; }
  .panel { width: 260px; border-left: 1px solid #dde2ec; padding: 12px; overflow: auto; }
  .panel h3 { margin: 4px 0 10px; }
  .panel label { display: block; margin: 8px 0 2px; font-size: 12px; color: #58637a; }
  .panel input, .panel select, .panel textarea { width: 100%; font: inherit; padding: 5px; border: 1px solid #cdd4e0; border-radius: 6px; }
  .panel .row { display: flex; gap: 6px; }
  .panel button.add { margin-top: 12px; width: 100%; padding: 8px; background: #2f6df6; color: #fff; border: 0; border-radius: 7px; cursor: pointer; font-weight: 600; }
  .hint { font-size: 11px; color: #8893a8; margin-top: 8px; }
  #msg { font-size: 12px; margin-top: 8px; min-height: 16px; }
</style>
</head>
<body>
<header>
  <b>PDF Toolkit</b>
  <label style="font-size:12px">source
    <select id="source"></select>
  </label>
  <button id="refresh">Refresh</button>
  <span style="flex:1"></span>
  <span style="font-size:12px;opacity:.7">tabs &middot; open &middot; note &middot; highlight</span>
</header>
<div class="body">
  <div class="sidebar"><h3>Files</h3><div id="files"></div></div>
  <div class="main">
    <div class="tabs" id="tabs"></div>
    <div class="viewer" id="viewer"><div class="empty">Open a file from the left to start.</div></div>
  </div>
  <div class="panel">
    <h3>Annotate</h3>
    <label>Page</label>
    <input id="a_page" type="number" min="1" value="1">
    <label>Type</label>
    <select id="a_kind"><option value="note">Note (memo)</option><option value="highlight">Highlight (marker)</option></select>
    <div id="note_fields">
      <label>Position x, y</label>
      <div class="row"><input id="a_x" type="number" value="100"><input id="a_y" type="number" value="700"></div>
    </div>
    <div id="hl_fields" style="display:none">
      <label>Rect x0, y0, x1, y1</label>
      <div class="row"><input id="a_x0" type="number" value="72"><input id="a_y0" type="number" value="710"></div>
      <div class="row"><input id="a_x1" type="number" value="320"><input id="a_y1" type="number" value="730"></div>
    </div>
    <label>Text</label>
    <textarea id="a_text" rows="2" placeholder="memo / comment"></textarea>
    <label>Colour</label>
    <select id="a_color"><option>yellow</option><option>green</option><option>pink</option><option>blue</option><option>orange</option></select>
    <button class="add" id="a_add">Add to active tab</button>
    <div id="msg"></div>
    <div class="hint">Coordinates are PDF points, origin at the bottom-left. Click-to-place is the next step.</div>
  </div>
</div>
<script>
const tabs = [];
let active = -1;

async function loadSources() {
  const r = await fetch('/api/sources'); const j = await r.json();
  const sel = document.getElementById('source');
  sel.innerHTML = j.sources.map(s => `<option value="${s}">${s}</option>`).join('');
}
async function loadFiles() {
  const src = document.getElementById('source').value;
  const r = await fetch('/api/files?source=' + encodeURIComponent(src));
  const j = await r.json();
  const box = document.getElementById('files');
  if (j.error) { box.innerHTML = '<div class="hint">' + j.error + '</div>'; return; }
  box.innerHTML = '';
  (j.files || []).forEach(f => {
    const d = document.createElement('div');
    d.className = 'file'; d.textContent = f.name; d.title = f.name;
    d.onclick = () => openTab(src, f.id, f.name);
    box.appendChild(d);
  });
  if (!j.files || !j.files.length) box.innerHTML = '<div class="hint">No PDFs here.</div>';
}
function openTab(source, id, name) {
  let i = tabs.findIndex(t => t.source === source && t.id === id);
  if (i < 0) { tabs.push({ source, id, name, v: Date.now() }); i = tabs.length - 1; }
  active = i; render();
}
function closeTab(i, ev) {
  ev.stopPropagation(); tabs.splice(i, 1);
  if (active >= tabs.length) active = tabs.length - 1;
  render();
}
function fileUrl(t) {
  return '/file?source=' + encodeURIComponent(t.source) + '&id=' + encodeURIComponent(t.id) + '&v=' + t.v;
}
function render() {
  const bar = document.getElementById('tabs'); bar.innerHTML = '';
  tabs.forEach((t, i) => {
    const el = document.createElement('div');
    el.className = 'tab' + (i === active ? ' active' : '');
    el.onclick = () => { active = i; render(); };
    el.innerHTML = '<span>' + t.name + '</span><span class="x">&times;</span>';
    el.querySelector('.x').onclick = (e) => closeTab(i, e);
    bar.appendChild(el);
  });
  const v = document.getElementById('viewer');
  if (active < 0) { v.innerHTML = '<div class="empty">Open a file from the left to start.</div>'; return; }
  v.innerHTML = '<iframe src="' + fileUrl(tabs[active]) + '#page=' + (document.getElementById('a_page').value || 1) + '"></iframe>';
}
document.getElementById('a_kind').onchange = (e) => {
  const hl = e.target.value === 'highlight';
  document.getElementById('hl_fields').style.display = hl ? '' : 'none';
  document.getElementById('note_fields').style.display = hl ? 'none' : '';
};
document.getElementById('refresh').onclick = loadFiles;
document.getElementById('source').onchange = loadFiles;
document.getElementById('a_add').onclick = async () => {
  const msg = document.getElementById('msg');
  if (active < 0) { msg.textContent = 'Open a file first.'; return; }
  const t = tabs[active];
  const body = {
    source: t.source, id: t.id, page: +document.getElementById('a_page').value,
    kind: document.getElementById('a_kind').value,
    text: document.getElementById('a_text').value,
    color: document.getElementById('a_color').value,
  };
  if (body.kind === 'note') {
    body.x = +document.getElementById('a_x').value; body.y = +document.getElementById('a_y').value;
  } else {
    body.rect = [ +document.getElementById('a_x0').value, +document.getElementById('a_y0').value,
                  +document.getElementById('a_x1').value, +document.getElementById('a_y1').value ];
  }
  msg.textContent = 'Saving...';
  const r = await fetch('/api/annotate', { method: 'POST', body: JSON.stringify(body) });
  const j = await r.json();
  if (j.ok) { t.v = Date.now(); render(); msg.textContent = 'Saved.'; }
  else { msg.textContent = 'Error: ' + (j.error || 'failed'); }
};
loadSources().then(loadFiles);
</script>
</body>
</html>
"""


def _spec_from_body(body: dict):
    color = annotations.COLORS.get(body.get("color", "yellow"), annotations.COLORS["yellow"])
    if body.get("kind") == "highlight":
        x0, y0, x1, y1 = body["rect"]
        return annotations.highlight([(x0, y0, x1, y1)], color=color, contents=body.get("text", ""))
    return annotations.text_note(body["x"], body["y"], body.get("text", ""), color=color)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the console quiet
        pass

    def _provider(self, kind):
        if kind == "drive" and self.server.drive is not None:
            return self.server.drive
        return self.server.local

    def _send(self, code, data: bytes, ctype="application/octet-stream"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        if path == "/":
            return self._send(200, PAGE_HTML.encode("utf-8"), "text/html; charset=utf-8")
        if path == "/api/health":
            return self._json({"ok": True})
        if path == "/api/sources":
            sources = ["local"] + (["drive"] if self.server.drive is not None else [])
            return self._json({"sources": sources})
        if path == "/api/files":
            kind = qs.get("source", ["local"])[0]
            try:
                return self._json({"source": kind, "files": self._provider(kind).list()})
            except Exception as exc:  # network/permission errors surface to the UI
                return self._json({"error": str(exc)}, 200)
        if path == "/file":
            kind = qs.get("source", ["local"])[0]
            fid = qs.get("id", [""])[0]
            try:
                data = self._provider(kind).read(fid)
            except Exception:
                return self._send(404, b"not found", "text/plain")
            return self._send(200, data, "application/pdf")
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/api/annotate":
            return self._send(404, b"not found", "text/plain")
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            provider = self._provider(body.get("source", "local"))
            data = provider.read(body["id"])
            out = ops.annotate(Document(data), {int(body["page"]): [_spec_from_body(body)]})
            provider.write(body["id"], out)
        except Exception as exc:
            return self._json({"error": str(exc)}, 400)
        return self._json({"ok": True})


def make_server(directory=".", host="127.0.0.1", port=8000, drive_token=None):
    server = ThreadingHTTPServer((host, port), Handler)
    server.local = LocalStorage(directory)
    server.drive = DriveStorage(drive_token) if drive_token else None
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pdftoolkit.app", description="Tabbed PDF viewer/editor in the browser")
    parser.add_argument("--dir", default=".", help="folder of PDFs to serve (default: current dir)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--drive-token", default=os.environ.get("GDRIVE_TOKEN"),
                        help="Google Drive OAuth2 access token (or set GDRIVE_TOKEN)")
    args = parser.parse_args(argv)
    server = make_server(args.dir, args.host, args.port, args.drive_token)
    drive = "on" if server.drive else "off"
    print(f"PDF Toolkit serving {os.path.abspath(args.dir)} (Drive: {drive})")
    print(f"  open  http://{args.host}:{args.port}/  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
