"""Debug web UI + JSON API. Open http://<pi-ip>:8080 in a browser on the same network."""
import json
import logging
import shutil
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

from . import checks
from .cycle import Busy
from .hardware import LED_COLOURS, LED_PRESETS

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
    # Camera settings changed in the web UI survive restarts.
    saved = store.get_state("camera_settings")
    if saved:
        hw.camera.apply_settings(saved)
    hw.led.calibration = store.get_state("led_calibration")
    hw.led.refresh()

    def set_camera(new):
        hw.camera.apply_settings(new)
        hw.led.refresh()  # a new LED colour applies to a lit LED straight away
        store.set_state("camera_settings", hw.camera.settings())

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
            "led": led_status(),
            "stepper_moving": hw.stepper.moving,
            "exposure_us": cfg["camera"]["exposure_us"],
            "analogue_gain": cfg["camera"]["analogue_gain"],
            "camera_settings": hw.camera.settings(),
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
        return Response(index_html(cfg), mimetype="text/html")

    @app.get("/api/status")
    def api_status():
        return jsonify(status())

    @app.post("/api/fan")
    def api_fan():
        ctl.set_fan(float((request.json or {}).get("value", 0)))
        return jsonify(ok=True, fan=hw.fan.value)

    def led_status():
        return {"on": hw.led.lit, "rgb": hw.led.target(), "effect": hw.led.effect,
                "duty": hw.led.levels() if hw.led.effect else hw.led.duties(),
                "pwm_hz": cfg["pins"]["led_pwm_frequency"], "calibration": hw.led.calibration}

    @app.post("/api/led")
    def api_led():
        # {"rgb": [r, g, b]} (0..1) and/or {"on": true}; {"colour": "white"|"red"|...|"off"};
        # {"effect": "pulse", "period_s": 4, "hue_s": 40, "low": 0.2} / {"effect": null};
        # old {"value": 1} still works. The colour is saved like the camera settings.
        body = request.json or {}
        try:
            if "rgb" in body:
                hw.led.stop_effect()
                set_camera({"led_rgb": body["rgb"]})
            if "colour" in body:
                hw.led.set_colour(body["colour"])
                set_camera({})
            if "on" in body or "value" in body:
                ctl.set_led(bool(body.get("on", body.get("value"))))
            if body.get("effect") == "pulse":
                hw.led.start_pulse(**{k: body[k] for k in ("period_s", "hue_s", "low") if k in body})
            elif "effect" in body:
                hw.led.stop_effect()
                hw.led.refresh()
        except (ValueError, TypeError) as e:
            return jsonify(ok=False, error=str(e)), 400
        return jsonify(ok=True, led=led_status())

    @app.post("/api/led/calibrate")
    def api_led_calibrate():
        try:
            ctl.calibrate_led()
        except (RuntimeError, ValueError) as e:
            log.warning("LED calibration failed: %s", e)
            return jsonify(ok=False, error=f"calibration failed: {e}"), 400
        return jsonify(ok=True, led=led_status())

    @app.post("/api/led/auto")
    def api_led_auto():
        """Try each LED colour with a matching exposure; keep the one with the crispest picture."""
        results = ctl.auto_setup()
        best = results[0]
        hw.led.stop_effect()
        set_camera({"led_rgb": best["rgb"], "exposure_us": best["exposure_us"],
                    "analogue_gain": best["analogue_gain"], "awb": False})
        ctl.set_led(True)
        log.info("Auto setup chose %s", best)
        return jsonify(ok=True, results=results, led=led_status(), settings=hw.camera.settings())

    @app.post("/api/led/calibration/clear")
    def api_led_calibration_clear():
        ctl.clear_led_calibration()
        return jsonify(ok=True, led=led_status())

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
        note = str((request.json or {}).get("note", "")).strip()
        return jsonify(ok=True, capture=ctl.manual_capture(note))

    @app.post("/api/exposure")
    def api_exposure():
        body = request.json or {}
        set_camera({k: body.get(k) for k in ("exposure_us", "analogue_gain")})
        return jsonify(ok=True)

    @app.post("/api/camera/settings")
    def api_camera_settings():
        try:
            set_camera(request.json or {})
        except Exception as e:
            log.exception("Camera settings failed")
            return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 400
        return jsonify(ok=True, settings=hw.camera.settings())

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
        caps = store.recent_captures(int(request.args.get("limit", 24)))
        for c in caps:
            meta = json.loads(c["meta"])
            c["note"] = meta.get("note", "")
            led = meta.get("led")  # missing on pictures from before the RGB LED
            if isinstance(led, dict) and "rgb" not in led:  # early RGB pictures: on/off per pin
                led = {"rgb": [float(led.get(k) or 0) for k in LED_COLOURS]}
            c["led"] = led["rgb"] if led else None
        return jsonify(caps)

    @app.post("/api/captures/<int:cid>/note")
    def api_capture_note(cid):
        meta = store.set_note(cid, str((request.json or {}).get("note", "")).strip())
        if meta is None:
            abort(404)
        return jsonify(ok=True)

    @app.post("/api/captures/<int:cid>/delete")
    def api_capture_delete(cid):
        if not store.delete_capture(cid):
            abort(404)
        log.info("Deleted capture #%d", cid)
        return jsonify(ok=True)

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
#pbar,.pbar{height:4px;background:var(--line);border-radius:2px;overflow:hidden;margin-top:4px}#pbar div,.pbar div{height:100%;width:0;background:var(--acc)}
.pbar{height:8px;border-radius:4px}.pbar div{transition:width .3s linear}
#log{height:260px;overflow:auto;font:12px ui-monospace,monospace;white-space:pre-wrap;background:var(--bg);padding:6px;border-radius:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px}
.grid>div{font-size:11px;color:var(--mut)}.grid a{color:inherit;text-decoration:none}.grid img{width:100%;border-radius:4px;display:block}
.grid .note{color:var(--ink);white-space:pre-wrap;word-break:break-word}.grid button{font-size:11px;padding:1px 6px}
textarea{font:inherit;width:100%;box-sizing:border-box;padding:5px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
input[type=checkbox]{width:auto}
.row label{display:inline-flex;align-items:center;gap:4px}
.picker{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
#wheel{width:220px;height:220px;touch-action:none;cursor:crosshair;border-radius:50%}
.pside{display:flex;flex-direction:column;gap:6px;align-items:flex-start;min-width:120px}
#swatch{width:72px;height:72px;border-radius:12px;border:1px solid var(--line)}
#swatch.pulse{animation:hue var(--hue,40s) linear infinite,breathe var(--per,4s) ease-in-out infinite}
@keyframes hue{from{filter:hue-rotate(0deg)}to{filter:hue-rotate(360deg)}}
@keyframes breathe{0%,100%{opacity:var(--low,.2)}50%{opacity:1}}
#pulsebtn.on{background:linear-gradient(90deg,#e0413a,#e6c229,#2a9d4a,#2f6fd6,#b03fd0);color:#fff;border-color:transparent}
#pins{font-size:12px;color:var(--mut);line-height:1.5}
#inten{width:220px;padding:0}.rgbin input{width:64px}
.chip{width:26px;height:26px;border-radius:50%;padding:0;border:2px solid var(--line)}
.hint{color:var(--mut);font-size:12px;margin:4px 0}ol.hint{padding-left:18px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;border:1px solid var(--line);vertical-align:-1px;margin-left:4px}
select{font:inherit;padding:4px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
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
 <div id="pbar"><div></div></div>
 <div class="row"><label><input type="checkbox" id="live" onchange="if(this.checked)refreshPreview()"> live</label> <span id="fps"></span>
  <button onclick="refreshPreview()">Refresh</button>
  <button onclick="capture()">Capture full-res</button></div>
 <textarea id="note" rows="2" placeholder="Note saved with the next manual picture (light, sample, weather…)"></textarea>
 <details><summary>Camera settings</summary>
 <div class="row">Exposure µs <input id="exp" title="0 = auto"> gain <input id="gain"></div>
 <div class="row"><label><input type="checkbox" id="awb"> auto white balance</label>
  red <input id="cgr" title="used when auto white balance is off"> blue <input id="cgb" title="used when auto white balance is off"></div>
 <div class="row">brightness <input id="bri" title="-1..1, 0 = normal"> contrast <input id="con" title="1 = normal"></div>
 <div class="row">saturation <input id="sat" title="1 = normal, 0 = greyscale"> sharpness <input id="shp" title="1 = normal, 0 = none"></div>
 <div class="row">noise reduction <select id="nr"><option>off</option><option>fast</option><option>high_quality</option></select></div>
 <div class="row">LED settle s <input id="settle"> <label><input type="checkbox" id="dng"> also save raw DNG</label></div>
 </details>
 <div class="row"><button onclick="setCam()">Set</button></div>
</section>
<section class="card"><h2>LED colour</h2>
 <div class="picker">
  <canvas id="wheel" width="440" height="440" title="drag to pick a colour"></canvas>
  <div class="pside">
   <div id="swatch"></div>
   <button id="ledon" class="p" onclick="ledToggle()">Turn on</button>
   <div id="pins"></div>
  </div>
 </div>
 <div class="row">intensity <input type="range" id="inten" min="0" max="100" oninput="pickInten()"> <span id="inten_v"></span></div>
 <div class="row rgbin">R <input id="rv" type="number" min="0" max="255" onchange="pickRgb()">
  G <input id="gv" type="number" min="0" max="255" onchange="pickRgb()">
  B <input id="bv" type="number" min="0" max="255" onchange="pickRgb()"></div>
 <div class="row" id="presets">PRESETS</div>
 <div class="row"><button class="p" id="autobtn" onclick="autoSetup()">🎯 Auto setup</button>
  <span class="hint">tries blue, green, red and white, sets the exposure for each and keeps the sharpest</span></div>
 <div id="autorun" hidden><div class="pbar"><div id="autofill"></div></div><div class="hint" id="autoprog"></div></div>
 <table id="autotab"></table>
 <div class="row"><button id="pulsebtn" onclick="pulseToggle()">✨ Pulse</button></div>
 <div class="row hint">breathe every <input id="pper" type="number" min="0.5" step="0.5" value="4" style="width:56px"> s,
  colours every <input id="phue" type="number" min="2" step="5" value="40" style="width:56px"> s,
  lowest <input id="plow" type="number" min="5" max="100" step="5" value="20" style="width:56px"> %</div>
 <p class="hint">Pictures use this colour too. Below full brightness each colour flickers PWM_HZ times a second: use an exposure in whole PERIOD µs steps (not auto) to avoid faint stripes.</p>
 <details id="caldet"><summary>Calibrate with the camera <span id="calst"></span></summary>
  <ol class="hint"><li>Take the tape out.</li><li>Point the LED at the camera, from where it normally sits.</li>
   <li>Dim the room. Set the exposure and white balance you will use for pictures (auto white balance off is best).</li>
   <li>Press Calibrate. It photographs the LED off, then red, green and blue (5 to 30 s).</li></ol>
  <p class="hint">After that the picker means "what the camera sees": white is white in the pictures, and each colour is mixed from the three pins to match.</p>
  <div id="calrun" hidden><div class="pbar"><div id="calfill"></div></div><div class="hint" id="calprog"></div></div>
  <div class="row"><button class="p" id="calbtn" onclick="calibrate()">Calibrate</button><button onclick="post('/api/led/calibration/clear').then(ledResp)">Clear calibration</button></div>
  <table id="caltab"></table>
 </details>
</section>
<section class="card"><h2>Manual control</h2>
 <div class="row">Fan <button onclick="post('/api/fan',{value:1})">On</button><button onclick="post('/api/fan',{value:0})">Off</button>
   <span id="fanst"></span></div>
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
// Camera settings: [field id, setting name, kind]
const CAM=[['exp','exposure_us','n'],['gain','analogue_gain','n'],['awb','awb','b'],['cgr','colour_gain_red','n'],['cgb','colour_gain_blue','n'],
 ['bri','brightness','n'],['con','contrast','n'],['sat','saturation','n'],['shp','sharpness','n'],['nr','noise_reduction','s'],['settle','led_settle_s','n'],['dng','save_dng','b']];
function fillCam(s){for(const[id,k,t]of CAM){if(t=='b')$(id).checked=s[k];else $(id).value=s[k]}}
function setCam(){const b={};for(const[id,k,t]of CAM)b[k]=t=='b'?$(id).checked:t=='n'?+$(id).value:$(id).value;
 post('/api/camera/settings',b).then(j=>{if(j.settings)fillCam(j.settings);refreshPreview()})}
// ---- LED colour picker: hue/saturation wheel + intensity (HSV), synced with R G B 0..255 ----
let hsv=[0,0,1],ledOn=false,ledFilled=false,ledPostT=0,ledFx=null;
function hsv2rgb(h,s,v){const f=n=>{const k=(n+h/60)%6;return v-v*s*Math.max(0,Math.min(k,4-k,1))};return[f(5),f(3),f(1)]}
function rgb2hsv(r,g,b){const mx=Math.max(r,g,b),mn=Math.min(r,g,b),d=mx-mn;let h=0;
 if(d){h=mx==r?((g-b)/d)%6:mx==g?(b-r)/d+2:(r-g)/d+4;h=(h*60+360)%360}return[h,mx?d/mx:0,mx]}
const css=c=>`rgb(${c.map(v=>Math.round(v*255)).join(',')})`;
const W=$('wheel'),wc=W.getContext('2d'),R=W.width/2;let wheelImg;
function drawWheel(){if(!wheelImg){wheelImg=wc.createImageData(W.width,W.height);const d=wheelImg.data;
  for(let y=0;y<W.height;y++)for(let x=0;x<W.width;x++){const dx=x-R,dy=y-R,r=Math.hypot(dx,dy)/R,i=(y*W.width+x)*4;
   if(r>1){d[i+3]=0;continue}const c=hsv2rgb((Math.atan2(dy,dx)*180/Math.PI+360)%360,r,1);
   d[i]=c[0]*255;d[i+1]=c[1]*255;d[i+2]=c[2]*255;d[i+3]=255}}
 wc.putImageData(wheelImg,0,0);const a=hsv[0]*Math.PI/180,x=R+Math.cos(a)*hsv[1]*R,y=R+Math.sin(a)*hsv[1]*R;
 wc.lineWidth=4;wc.strokeStyle='#000';wc.beginPath();wc.arc(x,y,14,0,7);wc.stroke();
 wc.lineWidth=2;wc.strokeStyle='#fff';wc.beginPath();wc.arc(x,y,14,0,7);wc.stroke()}
function showPick(){const c=hsv2rgb(...hsv);drawWheel();$('swatch').style.background=css(c);
 $('inten').value=Math.round(hsv[2]*100);$('inten_v').textContent=$('inten').value+' %';
 [$('rv').value,$('gv').value,$('bv').value]=c.map(v=>Math.round(v*255))}
// Send at most every 120 ms while dragging; the last value always gets sent.
let sendT=null,sendWant=false;
function sendRgb(){ledPostT=Date.now();if(sendT){sendWant=true;return}const c=hsv2rgb(...hsv);
 post('/api/led',{rgb:c,on:true}).then(ledResp);sendT=setTimeout(()=>{sendT=null;if(sendWant){sendWant=false;sendRgb()}},120)}
function wheelAt(e){const b=W.getBoundingClientRect(),dx=(e.clientX-b.left)/b.width*2-1,dy=(e.clientY-b.top)/b.height*2-1;
 hsv[0]=(Math.atan2(dy,dx)*180/Math.PI+360)%360;hsv[1]=Math.min(1,Math.hypot(dx,dy));if(hsv[2]==0)hsv[2]=1;showPick();sendRgb()}
W.onpointerdown=e=>{W.setPointerCapture(e.pointerId);wheelAt(e)};W.onpointermove=e=>{if(W.hasPointerCapture(e.pointerId))wheelAt(e)};
function pickInten(){hsv[2]=$('inten').value/100;showPick();sendRgb()}
function pickRgb(){const c=['rv','gv','bv'].map(id=>Math.max(0,Math.min(255,+$(id).value||0))/255);
 const n=rgb2hsv(...c);if(n[2]==0)n[0]=hsv[0];if(n[1]==0)n[0]=hsv[0];hsv=n;showPick();sendRgb()}
function pickPreset(c){hsv=rgb2hsv(...c);showPick();sendRgb()}
function pulseToggle(){ledPostT=Date.now();post('/api/led',ledFx?{effect:null}:
 {effect:'pulse',period_s:+$('pper').value,hue_s:+$('phue').value,low:$('plow').value/100}).then(ledResp)}
function ledToggle(){ledPostT=Date.now();post('/api/led',{on:!ledOn}).then(ledResp)}
// Auto setup: same pattern as the calibration (blocking POST, poll status for progress).
let autoPoll=null;
async function autoSetup(){$('autobtn').disabled=true;$('autotab').innerHTML='';
 autoPoll=setInterval(async()=>{try{showAuto((await (await fetch('/api/status')).json()).controller.auto_setup)}catch(e){}},300);
 try{const j=await post('/api/led/auto');
  if(j.results){ledFilled=false;ledResp(j);fillCam(j.settings);
   $('autotab').innerHTML='<tr><td>colour</td><td>exposure</td><td>detail</td></tr>'+j.results.map((r,i)=>
    `<tr><td>${i?'':'✓ '}${r.colour}</td><td>${r.exposure_us} µs${r.analogue_gain>1?' × gain '+r.analogue_gain:''}</td><td>${r.detail}</td></tr>`).join('')}}
 finally{clearInterval(autoPoll);autoPoll=null;showAuto(null);$('autobtn').disabled=false}}
function showAuto(p){$('autorun').hidden=!p;if(!p)return;
 const into=Math.min(0.95,Math.max(0,1-(p.left_s-(p.steps-p.step-1)*p.step_s)/p.step_s));
 $('autofill').style.width=((p.step+(p.step<p.steps?into:0))/p.steps*100)+'%';
 $('autoprog').textContent=`${p.colour||''} (${p.step+1} of ${p.steps}) · try ${p.try} at ${p.exposure_us} µs · about ${Math.ceil(p.left_s)} s left · ${Math.round(p.elapsed_s)} s so far`}
// Calibration: the POST blocks until done, so poll the status meanwhile for the progress bar.
let calPoll=null;
async function calibrate(){$('calst').textContent='· running…';$('calbtn').disabled=true;
 calPoll=setInterval(async()=>{try{showCal((await (await fetch('/api/status')).json()).controller.led_calibration)}catch(e){}},300);
 try{const j=await post('/api/led/calibrate');ledResp(j)}finally{clearInterval(calPoll);calPoll=null;showCal(null);$('calbtn').disabled=false}}
function showCal(p){$('calrun').hidden=!p;if(!p)return;$('caldet').open=true;
 // Each try takes one picture with the LED off, then red, green, blue. Fill smoothly within the current picture.
 const into=Math.min(0.95,Math.max(0,1-(p.try_left_s-(p.frames-p.frame-1)*p.frame_s)/p.frame_s));
 const f=Math.min(p.frames,p.frame+(p.frame<p.frames?into:0));$('calfill').style.width=(f/p.frames*100)+'%';
 const now=p.frame<p.frames?`picture ${p.frame+1} of ${p.frames} (LED ${p.colours[p.frame]})`:'checking';
 $('calprog').textContent=`Try ${p.try} at ${p.exposure_us} µs · ${now} · about ${Math.ceil(p.try_left_s)} s left`
  +(p.try>1?' (more tries if it is still too bright or dark)':'')+` · ${Math.round(p.elapsed_s)} s so far`+(p.note?` · ${p.note}`:'')}
function ledResp(j){if(!j||!j.led)return;const l=j.led,wasFx=ledFx;ledOn=l.on;ledFx=l.effect;
 const sw=$('swatch');sw.classList.toggle('pulse',!!ledFx);$('pulsebtn').classList.toggle('on',!!ledFx);
 if(ledFx){sw.style.background='hsl(0,100%,50%)';sw.style.setProperty('--hue',ledFx.hue_s+'s');sw.style.setProperty('--per',ledFx.period_s+'s');sw.style.setProperty('--low',ledFx.low)}
 else if(wasFx)showPick();  // back to the picked colour
 if(!ledFilled){const n=rgb2hsv(...l.rgb);if(n[1]>0)hsv[0]=n[0];hsv=[hsv[0],n[1],n[2]];ledFilled=true;showPick()}
 $('ledon').textContent=l.on?'Turn off':'Turn on';$('ledon').className=l.on?'':'p';
 $('pins').innerHTML=(l.on?(ledFx?'● pulsing':'● on'):'○ off')+'<br>pins: '+['red','green','blue'].map(k=>k[0].toUpperCase()+' '+Math.round(l.duty[k]*100)+'%').join(' · ')
  +'<br>'+(l.calibration?'calibrated'+(l.calibration.mock?' (simulated)':''):'not calibrated');
 const cal=l.calibration;$('calst').textContent=cal?'· done '+cal.ts.slice(0,16).replace('T',' '):'· not done';
 $('caltab').innerHTML=cal?rows0({'exposure':cal.exposure_us+' µs, gain '+cal.analogue_gain,
  'camera sees from LED red':cal.matrix.map(r=>r[0].toFixed(3)).join(' / ')+' (R / G / B)',
  'from LED green':cal.matrix.map(r=>r[1].toFixed(3)).join(' / '),'from LED blue':cal.matrix.map(r=>r[2].toFixed(3)).join(' / '),
  'dark (LED off)':cal.dark.map(v=>v.toFixed(3)).join(' / ')}):''}
function rows0(o){return Object.entries(o).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('')}
function capture(){post('/api/capture',{note:$('note').value})}
const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let caps=[];
async function editNote(id){const c=caps.find(x=>x.id==id);const t=prompt('Note for picture #'+id,c?c.note:'');
 if(t!==null){await post('/api/captures/'+id+'/note',{note:t});loadCaps()}}
async function delCap(id){if(confirm('Delete picture #'+id+' and its note? This cannot be undone.')){await post('/api/captures/'+id+'/delete');loadCaps()}}
function setCycle(){post('/api/cycle/settings',{interval_min:+$('int').value,blow_s:+$('blow').value,pitch_steps:+$('pitch').value})}
let prevT=0,frameMs=1000;
// Progress bar: the server can't report progress, so fill towards 90 % over the last frame's time.
function bar(pct,ms){const b=$('pbar').firstChild;b.style.transition=ms?`width ${ms}ms ease-out`:'none';b.style.width=pct+'%'}
function refreshPreview(){prevT=Date.now();bar(0,0);$('pbar').offsetWidth;bar(90,frameMs);
 $('preview').src='/api/preview.jpg?t='+prevT}
// Live mode: ask for the next frame as soon as the last one arrives (short gap so the Pi can do other work).
function nextFrame(ok){if(ok&&prevT){frameMs=Date.now()-prevT;$('fps').textContent=(frameMs/1000).toFixed(2)+' s/frame'}
 bar(100,80);
 if($('live').checked)setTimeout(refreshPreview,ok?100:2000)}
$('preview').onload=()=>nextFrame(true);$('preview').onerror=()=>nextFrame(false);
function rows(el,obj){el.innerHTML=Object.entries(obj).map(([k,v])=>`<tr><td>${k}</td><td>${typeof v=='object'&&v!==null?JSON.stringify(v):v}</td></tr>`).join('')}
async function tick(){try{
 const s=await (await fetch('/api/status')).json();const c=s.controller;
 $('dev').textContent=s.device_id;$('act').textContent=c.activity+(c.paused?' · paused':'');
 $('mode').textContent=s.mock_hardware?'MOCK hardware':(s.mock_camera?'MOCK camera':'real hardware');
 $('mode').className='pill'+(s.mock_hardware||s.mock_camera?' mock':'');
 $('fanst').textContent=s.fan?'● on':'○ off';if(Date.now()-ledPostT>2000)ledResp({led:s.led});if(!calPoll)showCal(c.led_calibration);if(!autoPoll)showAuto(c.auto_setup);  // skip status that may predate our last change
 if(!filled){fillCam(s.camera_settings);$('int').value=c.cycle.interval_min;$('blow').value=c.cycle.blow_s;$('pitch').value=c.cycle.pitch_steps;filled=true}
 rows($('cyc'),{'next cycle in':c.paused?'paused':c.next_run+' s','odometer (steps)':c.tape_steps,'samples in transit':JSON.stringify(c.pipeline),'fan→camera (pitches)':c.cycle.camera_offset_cycles,'last cycle':c.last_cycle});
 rows($('st'),{'camera error':s.camera_error||'none','captures':s.store.captures,'pending upload':s.store.pending_upload,'upload':s.upload.enabled?s.upload.server:'disabled','last upload':s.upload.last,'disk free':s.disk_free_gb+' GB','CPU temp':s.cpu_temp_c==null?'n/a':s.cpu_temp_c+' °C','uptime':s.uptime_s+' s'});
 const l=await (await fetch('/api/logs')).json();const el=$('log');const atEnd=el.scrollTop+el.clientHeight>=el.scrollHeight-5;
 el.textContent=l.join('\n');if(atEnd)el.scrollTop=el.scrollHeight;
}catch(e){$('msg').textContent='device unreachable'}}
async function loadCaps(){caps=await (await fetch('/api/captures?limit=24')).json();
 $('caps').innerHTML=caps.map(x=>`<div><a href="/images/${x.path}" target="_blank"><img loading="lazy" src="/images/${x.path.replace(/\.png$/,'.thumb.jpg')}">#${x.id} ${x.kind}${x.sample_id?' s'+x.sample_id:''}${x.led?`<span class="sw" title="LED colour" style="background:${css(x.led)}"></span>`:''}<br>${x.ts.slice(5,16).replace('T',' ')}${x.uploaded_at?' ✓':''}</a>
 ${x.note?`<div class="note">${esc(x.note)}</div>`:''}<button onclick="editNote(${x.id})">note</button> <a href="/images/${x.path.replace(/\.png$/,'.json')}" target="_blank">json</a> <button onclick="delCap(${x.id})">delete</button></div>`).join('')}
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
INDEX_HTML = INDEX_HTML.replace("PRESETS", "".join(
    f'<button class="chip" title="{n}" style="background:rgb({",".join(str(v * 255) for v in c)})" '
    f'onclick="pickPreset([{",".join(map(str, c))}])"></button>' for n, c in LED_PRESETS.items()))


def index_html(cfg):
    hz = cfg["pins"]["led_pwm_frequency"]
    return INDEX_HTML.replace("PWM_HZ", str(hz)).replace("PERIOD", str(round(1e6 / hz)))
