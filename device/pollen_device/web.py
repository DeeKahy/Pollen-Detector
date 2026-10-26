"""Debug web UI + JSON API. Open http://<pi-ip>:8080 in a browser on the same network."""
import logging
import shutil
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from . import checks
from .cycle import Busy

log = logging.getLogger("pollen.web")
START = time.time()


def cpu_temp():
    try:
        return round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000, 1)
    except (OSError, ValueError):
        return None


def create_app(cfg, ctl, hw, store, uploader, logbuf):
    app = Flask(__name__)
    password = cfg["web"].get("password") or ""

    @app.before_request
    def check_auth():
        if not password:
            return None
        auth = request.authorization
        if auth and auth.password == password:
            return None
        return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="pollen"'})

    @app.errorhandler(Busy)
    def busy(e):
        return jsonify(ok=False, error=str(e)), 409

    def status():
        disk = shutil.disk_usage(store.dir)
        return {
            "device_id": cfg["device_id"],
            "mock_hardware": hw.mock,
            "mock_camera": hw.camera.mock,
            "camera_error": hw.camera.error,
            "fan": hw.fan.value,
            "led": hw.led.value,
            "stepper_moving": hw.stepper.moving,
            "exposure_us": cfg["camera"]["exposure_us"],
            "analogue_gain": cfg["camera"]["analogue_gain"],
            "controller": ctl.status(),
            "store": store.stats(),
            "upload": {"enabled": cfg["upload"]["enabled"], "server": cfg["upload"]["server_url"],
                       "last": uploader.last_result},
            "disk_free_gb": round(disk.free / 1e9, 2),
            "cpu_temp_c": cpu_temp(),
            "uptime_s": round(time.time() - START),
        }

    app.config["status_fn"] = status

    @app.get("/")
    def index():
        return Response(INDEX_HTML, mimetype="text/html")

    @app.get("/api/status")
    def api_status():
        return jsonify(status())

    @app.post("/api/fan")
    def api_fan():
        ctl.set_fan(float((request.json or {}).get("value", 0)))
        return jsonify(ok=True, fan=hw.fan.value)

    @app.post("/api/led")
    def api_led():
        ctl.set_led(float((request.json or {}).get("value", 0)))
        return jsonify(ok=True, led=hw.led.value)

    @app.post("/api/jog")
    def api_jog():
        steps = int((request.json or {}).get("steps", 0))
        if abs(steps) > 100000:
            return jsonify(ok=False, error="too many steps"), 400
        return jsonify(ok=True, moved=ctl.jog(steps))

    @app.post("/api/skip")
    def api_skip():
        return jsonify(ok=True, moved=ctl.skip_section())

    @app.post("/api/capture")
    def api_capture():
        return jsonify(ok=True, capture=ctl.manual_capture())

    @app.post("/api/exposure")
    def api_exposure():
        body = request.json or {}
        hw.camera.set_exposure(int(body.get("exposure_us", cfg["camera"]["exposure_us"])),
                               float(body.get("analogue_gain", cfg["camera"]["analogue_gain"])))
        return jsonify(ok=True)

    @app.post("/api/cycle/<action>")
    def api_cycle(action):
        if action == "run":
            # run in background so the HTTP request returns immediately
            import threading

            def run():
                try:
                    ctl.run_cycle()
                except Busy as e:
                    log.warning("Run cycle: %s", e)
                except Exception:
                    log.exception("Manual cycle failed")
                    hw.all_off()
            threading.Thread(target=run, daemon=True).start()
        elif action == "pause":
            ctl.pause()
        elif action == "resume":
            ctl.resume()
        elif action == "abort":
            ctl.abort()
        elif action == "reset-tracking":
            ctl.reset_tracking()
        else:
            abort(404)
        return jsonify(ok=True)

    @app.post("/api/cycle/settings")
    def api_cycle_settings():
        body = request.json or {}
        c = cfg["cycle"]
        for key, typ in (("interval_min", float), ("blow_s", float), ("pitch_steps", int)):
            if key in body:
                c[key] = typ(body[key])
        log.info("Cycle settings changed (not saved to config.yaml): %s", body)
        return jsonify(ok=True, cycle=c)

    @app.get("/api/checks")
    def api_checks():
        return jsonify(checks.run_all(cfg, hw, ctl))

    @app.post("/api/test/coils")
    def api_test_coils():
        with ctl._action("coil test"):
            hw.stepper.test_coils()
        return jsonify(ok=True)

    @app.post("/api/camera/retry")
    def api_camera_retry():
        if hw.mock:
            return jsonify(ok=False, error="mock hardware mode"), 400
        with ctl._action("camera restart"):
            hw.camera.start()
        return jsonify(ok=not hw.camera.mock, error=hw.camera.error)

    @app.post("/api/upload/now")
    def api_upload_now():
        if not cfg["upload"]["enabled"]:
            return jsonify(ok=False, error="upload disabled in config"), 400
        return jsonify(ok=True, result=uploader.upload_pending())

    @app.get("/api/preview.jpg")
    def api_preview():
        return Response(hw.camera.preview_jpeg(), mimetype="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.get("/api/captures")
    def api_captures():
        return jsonify(store.recent_captures(int(request.args.get("limit", 24))))

    @app.get("/images/<path:rel>")
    def images(rel):
        return send_from_directory(store.images, rel)

    @app.get("/api/logs")
    def api_logs():
        return jsonify(list(logbuf))

    return app


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pollen device</title>
<style>
:root{--bg:#f6f7f4;--card:#fff;--ink:#1d211b;--mut:#6b7266;--acc:#3f7d3a;--warn:#b5462f;--line:#dfe3da}
@media (prefers-color-scheme:dark){:root{--bg:#141713;--card:#1d211b;--ink:#e6eae2;--mut:#9aa293;--acc:#7fc276;--warn:#ef8a6f;--line:#30362d}}
*{box-sizing:border-box}body{margin:0;font:14px/1.4 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0}.pill{padding:2px 8px;border-radius:99px;border:1px solid var(--line);font-size:12px}
.mock{color:var(--warn);border-color:var(--warn)}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;padding:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.card h2{font-size:14px;margin:0 0 8px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
button{font:inherit;padding:6px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer;margin:2px}
button.p{background:var(--acc);color:#fff;border-color:var(--acc)}button.w{color:var(--warn);border-color:var(--warn)}
input{font:inherit;width:90px;padding:5px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
table{border-collapse:collapse;width:100%}td{padding:2px 4px;word-break:break-word;border-bottom:1px solid var(--line);vertical-align:top}td:first-child{color:var(--mut);white-space:nowrap}
#preview{width:100%;background:#000;border-radius:6px;min-height:120px}
#log{height:260px;overflow:auto;font:12px ui-monospace,monospace;white-space:pre-wrap;background:var(--bg);padding:6px;border-radius:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px}
.grid a{font-size:11px;color:var(--mut);text-decoration:none}.grid img{width:100%;border-radius:4px;display:block}
.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:4px 0}
#msg{color:var(--warn);font-size:12px;min-height:1em}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--mut)}
.dot.ok{background:var(--acc)}.dot.warn{background:#d39b2a}.dot.fail{background:var(--warn)}
#chk td:first-child{width:180px}
</style></head><body>
<header><h1>Pollen device <span id="dev"></span></h1><span id="mode" class="pill"></span><span id="act" class="pill"></span><span id="msg"></span></header>
<main>
<section class="card" style="grid-column:1/-1"><h2>Hardware checks</h2>
 <div class="row"><button class="p" onclick="runChecks()">Run checks</button>
  <button onclick="coilTest()">Coil test (LEDs A→D)</button>
  <button onclick="retryCam()">Retry camera</button>
  <span id="chkts" style="color:var(--mut);font-size:12px"></span></div>
 <table id="chk"></table>
</section>
<section class="card"><h2>Live preview</h2>
 <img id="preview" alt="preview">
 <div class="row"><label><input type="checkbox" id="live" onchange="if(this.checked)refreshPreview()"> live</label> <span id="fps"></span>
  <button onclick="refreshPreview()">Refresh</button>
  <button onclick="post('/api/capture')">Capture full-res</button></div>
 <div class="row">Exposure µs <input id="exp"> gain <input id="gain"> <button onclick="setExp()">Set</button></div>
</section>
<section class="card"><h2>Manual control</h2>
 <div class="row">Fan <button onclick="post('/api/fan',{value:1})">On</button><button onclick="post('/api/fan',{value:0})">Off</button>
   <span id="fanst"></span></div>
 <div class="row">LED <button onclick="post('/api/led',{value:1})">On</button><button onclick="post('/api/led',{value:0})">Off</button>
   <span id="ledst"></span></div>
 <div class="row">Tape steps <input id="steps" value="500">
   <button onclick="jog(1)">Forward</button><button onclick="jog(-1)">Back</button></div>
 <div class="row"><button onclick="post('/api/skip')">Skip section (1 pitch, no fan)</button>
   <button onclick="post('/api/cycle/reset-tracking')">Reset tracking</button></div>
 <p style="color:var(--mut);font-size:12px">Odometer counts all steps. After manual jogging, press Reset tracking so images are not linked to the wrong sample.</p>
</section>
<section class="card"><h2>Sampling cycle</h2>
 <div class="row"><button class="p" onclick="post('/api/cycle/run')">Run one cycle now</button>
  <button onclick="post('/api/cycle/resume')">Resume schedule</button><button onclick="post('/api/cycle/pause')">Pause</button>
  <button class="w" onclick="post('/api/cycle/abort')">Abort</button></div>
 <div class="row">every <input id="int"> min, blow <input id="blow"> s, pitch <input id="pitch"> steps
  <button onclick="setCycle()">Apply</button></div>
 <table id="cyc"></table>
</section>
<section class="card"><h2>Status</h2><table id="st"></table>
 <div class="row"><button onclick="post('/api/upload/now')">Upload now</button></div></section>
<section class="card" style="grid-column:1/-1"><h2>Recent captures</h2><div class="grid" id="caps"></div></section>
<section class="card" style="grid-column:1/-1"><h2>Log</h2><div id="log"></div></section>
</main>
<script>
const $=id=>document.getElementById(id);let filled=false;
async function post(url,body){$('msg').textContent='';
 const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});
 const j=await r.json().catch(()=>({}));if(!r.ok)$('msg').textContent=j.error||('HTTP '+r.status);
 tick();if(url=='/api/capture')loadCaps();return j}
function jog(d){post('/api/jog',{steps:d*parseInt($('steps').value||0)})}
function setExp(){post('/api/exposure',{exposure_us:+$('exp').value,analogue_gain:+$('gain').value}).then(refreshPreview)}
function setCycle(){post('/api/cycle/settings',{interval_min:+$('int').value,blow_s:+$('blow').value,pitch_steps:+$('pitch').value})}
let prevT=0;
function refreshPreview(){prevT=Date.now();$('preview').src='/api/preview.jpg?t='+prevT}
// Live mode: ask for the next frame as soon as the last one arrives (short gap so the Pi can do other work).
function nextFrame(ok){if(ok&&prevT)$('fps').textContent=((Date.now()-prevT)/1000).toFixed(2)+' s/frame';
 if($('live').checked)setTimeout(refreshPreview,ok?100:2000)}
$('preview').onload=()=>nextFrame(true);$('preview').onerror=()=>nextFrame(false);
function rows(el,obj){el.innerHTML=Object.entries(obj).map(([k,v])=>`<tr><td>${k}</td><td>${typeof v=='object'&&v!==null?JSON.stringify(v):v}</td></tr>`).join('')}
async function tick(){try{
 const s=await (await fetch('/api/status')).json();const c=s.controller;
 $('dev').textContent=s.device_id;$('act').textContent=c.activity+(c.paused?' · paused':'');
 $('mode').textContent=s.mock_hardware?'MOCK hardware':(s.mock_camera?'MOCK camera':'real hardware');
 $('mode').className='pill'+(s.mock_hardware||s.mock_camera?' mock':'');
 $('fanst').textContent=s.fan?'● on':'○ off';$('ledst').textContent=s.led?'● on':'○ off';
 if(!filled){$('exp').value=s.exposure_us;$('gain').value=s.analogue_gain;$('int').value=c.cycle.interval_min;$('blow').value=c.cycle.blow_s;$('pitch').value=c.cycle.pitch_steps;filled=true}
 rows($('cyc'),{'next cycle in':c.paused?'paused':c.next_run+' s','odometer (steps)':c.tape_steps,'samples in transit':JSON.stringify(c.pipeline),'fan→camera (pitches)':c.cycle.camera_offset_cycles,'last cycle':c.last_cycle});
 rows($('st'),{'camera error':s.camera_error||'none','captures':s.store.captures,'pending upload':s.store.pending_upload,'upload':s.upload.enabled?s.upload.server:'disabled','last upload':s.upload.last,'disk free':s.disk_free_gb+' GB','CPU temp':s.cpu_temp_c==null?'n/a':s.cpu_temp_c+' °C','uptime':s.uptime_s+' s'});
 const l=await (await fetch('/api/logs')).json();const el=$('log');const atEnd=el.scrollTop+el.clientHeight>=el.scrollHeight-5;
 el.textContent=l.join('\n');if(atEnd)el.scrollTop=el.scrollHeight;
}catch(e){$('msg').textContent='device unreachable'}}
async function loadCaps(){const c=await (await fetch('/api/captures?limit=24')).json();
 $('caps').innerHTML=c.map(x=>`<a href="/images/${x.path}" target="_blank"><img loading="lazy" src="/images/${x.path.replace(/\.png$/,'.thumb.jpg')}">#${x.id} ${x.kind}${x.sample_id?' s'+x.sample_id:''}<br>${x.ts.slice(5,16).replace('T',' ')}${x.uploaded_at?' ✓':''}</a>`).join('')}
async function runChecks(){$('chkts').textContent='running…';
 try{const r=await fetch('/api/checks');const j=await r.json();
  $('chk').innerHTML=j.checks.map(c=>`<tr><td><span class="dot ${c.status}"></span>${c.name}</td><td>${c.detail}</td></tr>`).join('');
  $('chkts').textContent='last run '+j.ts}catch(e){$('chkts').textContent='checks failed: '+e}}
async function coilTest(){$('chkts').textContent='coil test running (8 s) - watch LEDs A, B, C, D…';
 await post('/api/test/coils');$('chkts').textContent='coil test done'}
async function retryCam(){$('chkts').textContent='restarting camera…';const j=await post('/api/camera/retry');
 $('chkts').textContent=j.ok?'camera running':'camera failed: '+(j.error||'');refreshPreview();runChecks()}
setInterval(tick,2000);setInterval(loadCaps,15000);
tick();loadCaps();refreshPreview();runChecks();
</script></body></html>
"""
