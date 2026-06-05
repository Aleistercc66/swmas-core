#!/usr/bin/env python3
"""
SWARM DESKTOP SERVER v2.0
No Flask needed — uses only built-in Python modules.
Runs on http://localhost:7777
"""

import json
import os
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

SWARM_DIR = Path('/root/.openclaw/workspace/swarm_general')
DATA_DIR = SWARM_DIR / 'data'
LOGS_DIR = SWARM_DIR / 'logs'


def load_json(path: Path, default=None):
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return default or {}


def get_swarm_status():
    status = {'agents': 8, 'tasks': 0, 'completed': 0, 'uptime': 'Unknown'}
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        procs = result.stdout
        swarm_procs = [l for l in procs.split('\n')
                      if any(x in l for x in ['realtime_interface', 'money_action',
                                               'telegram_alert', 'enhanced_scanner',
                                               'evolution_engine', 'profit_engine',
                                               'dexscreener', 'jupiter', 'auto_sniper'])]
        status['agents'] = len(swarm_procs)
    except Exception:
        pass
    return status


def get_evolution():
    evo = load_json(DATA_DIR / 'evolution_state.json',
                    {'generation': 0, 'current_score': 0, 'target_score': 10})
    score = evo.get('current_score', 0)
    target = evo.get('target_score', 10)
    pct = min((score / target) * 100, 100) if target else 0
    return {
        'score': round(score, 2),
        'gen': evo.get('generation', 0),
        'percent': round(pct, 1),
        'patterns': len(evo.get('patterns', {}))
    }


def get_money():
    m = load_json(DATA_DIR / 'money_state.json',
                  {'actions_taken': 0, 'opportunities_found': 0, 'strategies': {}})
    s = m.get('strategies', {})
    return {
        'cycles': m.get('actions_taken', 0),
        'opps': m.get('opportunities_found', 0),
        'actions': m.get('actions_taken', 0),
        'strategies': sum(1 for x in s.values() if x.get('active', False)),
        'scan': round(s.get('scanning', {}).get('weight', 0.25) * 100),
        'arb': round(s.get('arbitrage', {}).get('weight', 0.20) * 100),
        'yield': round(s.get('yield_farming', {}).get('weight', 0.15) * 100),
        'snipe': round(s.get('sniper', {}).get('weight', 0.20) * 100),
        'social': round(s.get('social_signals', {}).get('weight', 0.20) * 100)
    }


def get_profit():
    p = load_json(DATA_DIR / 'profit_state.json',
                  {'signals_processed': 0, 'opportunities_found': 0,
                   'alerts_sent': 0, 'min_score': 45})
    return {
        'signals': p.get('signals_processed', 0),
        'opportunities': p.get('opportunities_found', 0),
        'alerts': p.get('alerts_sent', 0),
        'min_score': p.get('min_score', 45)
    }


def get_health():
    h = {'cpu': 0, 'mem': 0, 'processes': 0}
    try:
        with open('/proc/loadavg', 'r') as f:
            h['cpu'] = round(float(f.read().split()[0]) * 10, 1)
    except Exception:
        pass
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            total = avail = 0
            for line in lines:
                if 'MemTotal' in line:
                    total = int(line.split()[1])
                elif 'MemAvailable' in line:
                    avail = int(line.split()[1])
            if total:
                h['mem'] = round(((total - avail) / total) * 100, 1)
    except Exception:
        pass
    try:
        h['processes'] = len(subprocess.run(['ps', 'aux'],
                              capture_output=True, text=True).stdout.strip().split('\n')) - 1
    except Exception:
        pass
    return h


def get_alerts(n=10):
    alerts = []
    sent = DATA_DIR / 'sent_alerts.jsonl'
    if sent.exists():
        try:
            with open(sent, 'r') as f:
                for line in f.readlines()[-n:]:
                    try:
                        d = json.loads(line.strip())
                        a = d.get('alert', {})
                        alerts.append({
                            'time': d.get('timestamp', '')[-8:] or 'NOW',
                            'level': 'success',
                            'message': f"{a.get('token', 'Unknown')[:20]} | Score: {a.get('ai_score', 0)}/100 | +{a.get('profit_potential', 0)}%"
                        })
                    except Exception:
                        pass
        except Exception:
            pass
    if not alerts:
        alerts.append({'time': 'NOW', 'level': 'info',
                       'message': 'No alerts sent yet. System warming up...'})
    return alerts


def get_logs(n=15):
    logs = []
    files = [LOGS_DIR / 'scanner.log', LOGS_DIR / 'profit_engine.log',
             LOGS_DIR / 'money_action.log']
    all_lines = []
    for f in files:
        if f.exists():
            try:
                with open(f, 'r') as fh:
                    all_lines.extend(fh.readlines()[-n:])
            except Exception:
                pass
    all_lines.sort()
    for line in all_lines[-n:]:
        line = line.strip()
        if not line:
            continue
        time_str = 'NOW'
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                tp = parts[0].strip()
                if len(tp) >= 19:
                    time_str = tp[-8:]
        level = 'info'
        if 'ERROR' in line or 'error' in line.lower():
            level = 'error'
        elif 'WARN' in line or 'warning' in line.lower():
            level = 'warning'
        elif 'complete' in line.lower() or 'success' in line.lower():
            level = 'success'
        msg = line
        if '|' in line:
            msg = '|'.join(line.split('|')[2:]).strip()
        logs.append({'time': time_str, 'level': level, 'message': msg[:100]})
    if not logs:
        logs.append({'time': 'NOW', 'level': 'info',
                     'message': 'System initializing. Logs will appear shortly.'})
    return logs


def render_html():
    swarm = get_swarm_status()
    evo = get_evolution()
    money = get_money()
    profit = get_profit()
    health = get_health()
    alerts = get_alerts()
    logs = get_logs()

    def level_color(lvl):
        return {'success': '#00ff88', 'warning': '#ffaa00',
                'error': '#ff4444', 'info': '#00ccff'}.get(lvl, '#00ccff')

    alerts_html = '\n'.join(
        f'<div class="log-entry"><span class="log-time">{a["time"]}</span>'
        f'<span style="color:{level_color(a["level"])}">{a["message"]}</span></div>'
        for a in alerts
    )
    logs_html = '\n'.join(
        f'<div class="log-entry"><span class="log-time">{l["time"]}</span>'
        f'<span style="color:{level_color(l["level"])}">{l["message"]}</span></div>'
        for l in logs
    )

    cpu_warn = 'warning' if health['cpu'] > 70 else 'danger' if health['cpu'] > 90 else ''
    mem_warn = 'warning' if health['mem'] > 80 else 'danger' if health['mem'] > 95 else ''
    score_warn = 'warning' if profit['min_score'] < 50 else ''

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>SWARM DASHBOARD</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0e1a;color:#e0e6ed;font-family:'Segoe UI',monospace}}
.header{{background:linear-gradient(90deg,#0a0e1a,#1a1f3a,#0a0e1a);border-bottom:2px solid #00ff88;padding:20px 40px;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:28px;color:#00ff88;text-shadow:0 0 20px rgba(0,255,136,0.5);letter-spacing:3px}}
.status{{display:flex;gap:15px;align-items:center}}
.badge{{background:rgba(0,255,136,0.15);border:1px solid #00ff88;padding:6px 14px;border-radius:20px;font-size:11px;color:#00ff88}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px;padding:30px 40px}}
.card{{background:linear-gradient(135deg,#111833,#1a2040);border:1px solid #2a3a5c;border-radius:12px;padding:24px;position:relative}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#00ff88,#00ccff,#ff00ff)}}
.card-title{{font-size:13px;color:#7a8bb5;text-transform:uppercase;letter-spacing:2px;margin-bottom:16px}}
.metric-row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1a2a4a}}
.metric-row:last-child{{border:none}}
.label{{color:#8a9bb8;font-size:13px}}
.value{{font-size:16px;font-weight:bold;color:#00ff88}}
.value.warning{{color:#ffaa00}}
.value.danger{{color:#ff4444}}
.value.info{{color:#00ccff}}
.big{{font-size:42px;font-weight:bold;color:#00ff88;text-shadow:0 0 30px rgba(0,255,136,0.4);margin:8px 0}}
.progress{{height:6px;background:#1a2040;border-radius:3px;overflow:hidden;margin-top:6px}}
.fill{{height:100%;background:linear-gradient(90deg,#00ff88,#00ccff);border-radius:3px}}
.fill.warning{{background:linear-gradient(90deg,#ffaa00,#ff7700)}}
.fill.danger{{background:linear-gradient(90deg,#ff4444,#ff0000)}}
.logs{{max-height:250px;overflow-y:auto;font-size:11px;line-height:1.5;background:#0a1020;border-radius:8px;padding:12px;margin-top:12px}}
.log-entry{{padding:3px 0;border-bottom:1px solid #1a2040;font-family:'Courier New',monospace}}
.log-time{{color:#5a7a9a;margin-right:8px}}
.strat{{display:flex;justify-content:space-between;padding:8px;margin:4px 0;background:rgba(255,255,255,0.03);border-radius:6px;border-left:3px solid #00ff88}}
.strat.scan{{border-left-color:#00ff88}}
.strat.arb{{border-left-color:#00ccff}}
.strat.yield{{border-left-color:#ffaa00}}
.strat.snipe{{border-left-color:#ff4444}}
.strat.social{{border-left-color:#ff00ff}}
.footer{{text-align:center;padding:20px;color:#4a5a7a;font-size:11px;border-top:1px solid #1a2040}}
.pulse{{animation:pulse 2s infinite}}@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.5}}}}
::-webkit-scrollbar{{width:6px}}
::-webkit-scrollbar-track{{background:#0a0e1a}}
::-webkit-scrollbar-thumb{{background:#2a3a5c;border-radius:3px}}
</style>
</head>
<body>
<div class="header">
<h1>SWARM DASHBOARD</h1>
<div class="status">
<span class="badge pulse">LIVE</span>
<span class="badge">BOT: ONLINE</span>
<span class="badge">MONEY: ACTIVE</span>
<span class="badge">EVO: GEN {evo['gen']}</span>
</div>
</div>

<div class="grid">

<div class="card"><div class="card-title">Swarm Status</div>
<div class="metric-row"><span class="label">Active Agents</span><span class="value">{swarm['agents']}</span></div>
<div class="metric-row"><span class="label">Active Tasks</span><span class="value info">{swarm['tasks']}</span></div>
<div class="metric-row"><span class="label">Completed</span><span class="value">{swarm['completed']}</span></div>
<div class="metric-row"><span class="label">Uptime</span><span class="value info">{swarm['uptime']}</span></div>
</div>

<div class="card"><div class="card-title">Evolution Engine</div>
<div class="big">{evo['score']}</div>
<div class="metric-row"><span class="label">Target</span><span class="value">10.0</span></div>
<div class="progress"><div class="fill" style="width:{evo['percent']}%"></div></div>
<div class="metric-row"><span class="label">Generation</span><span class="value">{evo['gen']}</span></div>
<div class="metric-row"><span class="label">Patterns</span><span class="value info">{evo['patterns']}</span></div>
</div>

<div class="card"><div class="card-title">Money Engine</div>
<div class="metric-row"><span class="label">Cycles</span><span class="value">{money['cycles']}</span></div>
<div class="metric-row"><span class="label">Opportunities</span><span class="value info">{money['opps']}</span></div>
<div class="metric-row"><span class="label">Actions Taken</span><span class="value">{money['actions']}</span></div>
<div class="metric-row"><span class="label">Strategies</span><span class="value">{money['strategies']}</span></div>
</div>

<div class="card"><div class="card-title">Profit Pipeline</div>
<div class="metric-row"><span class="label">Signals</span><span class="value">{profit['signals']}</span></div>
<div class="metric-row"><span class="label">Opportunities</span><span class="value info">{profit['opportunities']}</span></div>
<div class="metric-row"><span class="label">Alerts Sent</span><span class="value">{profit['alerts']}</span></div>
<div class="metric-row"><span class="label">Min Score</span><span class="value {score_warn}">{profit['min_score']}/100</span></div>
</div>

<div class="card"><div class="card-title">System Health</div>
<div class="metric-row"><span class="label">CPU Load</span><span class="value {cpu_warn}">{health['cpu']:.1f}%</span></div>
<div class="progress"><div class="fill {cpu_warn}" style="width:{min(health['cpu'],100)}%"></div></div>
<div class="metric-row"><span class="label">Memory</span><span class="value {mem_warn}">{health['mem']:.1f}%</span></div>
<div class="progress"><div class="fill {mem_warn}" style="width:{min(health['mem'],100)}%"></div></div>
<div class="metric-row"><span class="label">Processes</span><span class="value">{health['processes']}</span></div>
</div>

<div class="card"><div class="card-title">Active Strategies</div>
<div class="strat scan"><span>Scanning</span><span class="value">{money['scan']}% (25%)</span></div>
<div class="strat arb"><span>Arbitrage</span><span class="value info">{money['arb']}% (20%)</span></div>
<div class="strat yield"><span>Yield</span><span class="value warning">{money['yield']}% (15%)</span></div>
<div class="strat snipe"><span>Sniper</span><span class="value danger">{money['snipe']}% (20%)</span></div>
<div class="strat social"><span>Social</span><span class="value">{money['social']}% (20%)</span></div>
</div>

</div>

<div class="grid">
<div class="card" style="grid-column:1/-1"><div class="card-title">Recent Alerts</div>
<div class="logs">{alerts_html}</div></div>
<div class="card" style="grid-column:1/-1"><div class="card-title">System Logs</div>
<div class="logs">{logs_html}</div></div>
</div>

<div class="footer">
SWARM DESKTOP SERVER v2.0 | Auto-refresh every 5s | http://localhost:7777
</div>

<script>setInterval(()=>location.reload(),5000);</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(render_html().encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            data = {
                'swarm': get_swarm_status(),
                'evolution': get_evolution(),
                'money': get_money(),
                'profit': get_profit(),
                'health': get_health(),
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(data, indent=2).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    print("=" * 55)
    print("  SWARM DESKTOP SERVER v2.0")
    print("=" * 55)
    print("  Open your browser:")
    print("  http://localhost:7777")
    print("  http://127.0.0.1:7777")
    print("=" * 55)
    print()
    server = HTTPServer(('0.0.0.0', 7777), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()
