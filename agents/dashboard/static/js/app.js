/**
 * KreoPoly Swarm Dashboard - Real-time WebSocket Client
 */

const WS_URL = `ws://${window.location.host}/ws`;
let ws = null;
let reconnectInterval = 3000;

// ── WebSocket ──

function connectWebSocket() {
    ws = new WebSocket(WS_URL);
    
    ws.onopen = () => {
        console.log('✅ WebSocket connected');
        updateStatus('ws-status', '● LIVE', 'bg-green-500/20 text-green-400 border-green-500/30');
    };
    
    ws.onmessage = (event) => {
        try {
            const state = JSON.parse(event.data);
            updateDashboard(state);
        } catch (e) {
            console.error('Parse error:', e);
        }
    };
    
    ws.onclose = () => {
        console.log('❌ WebSocket disconnected');
        updateStatus('ws-status', '● OFFLINE', 'bg-red-500/20 text-red-400 border-red-500/30');
        setTimeout(connectWebSocket, reconnectInterval);
    };
    
    ws.onerror = (err) => {
        console.error('WebSocket error:', err);
    };
}

function updateStatus(id, text, classes) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = text;
        el.className = `px-3 py-1 rounded-full text-xs font-mono border ${classes}`;
    }
}

// ── Dashboard Updates ──

function updateDashboard(state) {
    // Portfolio
    const p = state.portfolio || {};
    updateText('balance', `$${(p.balance || 0).toFixed(2)}`);
    updateText('open-positions', p.open_positions || 0);
    updateText('win-rate', `${(p.win_rate || 0).toFixed(1)}%`);
    
    const dailyPnl = p.daily_pnl || 0;
    const dailyEl = document.getElementById('daily-pnl');
    dailyEl.textContent = `${dailyPnl >= 0 ? '+' : ''}$${dailyPnl.toFixed(2)}`;
    dailyEl.className = `text-xl font-bold ${dailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`;
    
    const totalPnl = p.total_pnl || 0;
    const totalEl = document.getElementById('total-pnl');
    totalEl.textContent = `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`;
    totalEl.className = `text-xl font-bold ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`;
    
    const dd = p.drawdown || 0;
    const ddEl = document.getElementById('drawdown');
    ddEl.textContent = `${dd.toFixed(1)}%`;
    ddEl.className = `text-xl font-bold ${dd > 10 ? 'text-red-400' : dd > 5 ? 'text-yellow-400' : 'text-green-400'}`;
    
    // Settings badges
    const settings = state.settings || {};
    updateStatus('auto-status', settings.auto_mode ? 'AUTO: ON' : 'AUTO: OFF',
        settings.auto_mode ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-gray-500/20 text-gray-400 border-gray-500/30');
    updateStatus('paper-status', settings.paper_mode ? 'PAPER' : 'REAL',
        settings.paper_mode ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' : 'bg-orange-500/20 text-orange-400 border-orange-500/30');
    
    if (settings.emergency_stop) {
        updateStatus('ws-status', '🛑 STOPPED', 'bg-red-600 text-white border-red-600 pulse');
    }
    
    // Positions table
    const positions = state.open_positions || [];
    updatePositions(positions);
    
    // Metrics
    const m = state.metrics || {};
    updateText('metric-scanned', m.tokens_scanned || 0);
    updateText('metric-signals', m.signals_generated || 0);
    updateText('metric-trades', m.trades_executed || 0);
    updateText('metric-tp', m.tp_hits || 0);
    updateText('metric-sl', m.sl_hits || 0);
    
    // Agent health
    updateAgentHealth(state.agent_health || []);
    
    // Events
    updateEvents(state.recent_events || []);
}

function updateText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function updatePositions(positions) {
    const tbody = document.getElementById('positions-table');
    const countBadge = document.getElementById('positions-count');
    
    countBadge.textContent = positions.length;
    
    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-500">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => {
        const pnlClass = pos.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400';
        const statusClass = pos.status === 'OPEN' ? 'bg-blue-500/20 text-blue-400' :
                           pos.status.startsWith('HIT_TP') ? 'bg-green-500/20 text-green-400' :
                           'bg-red-500/20 text-red-400';
        
        return `
            <tr class="border-b border-gray-800 hover:bg-white/5">
                <td class="py-2 font-mono">${pos.symbol}</td>
                <td class="text-right py-2 font-mono">$${pos.entry_price?.toFixed(8) || '?'}</td>
                <td class="text-right py-2 font-mono">$${pos.current_price?.toFixed(8) || '?'}</td>
                <td class="text-right py-2 font-mono ${pnlClass}">${pos.pnl_percent >= 0 ? '+' : ''}${pos.pnl_percent?.toFixed(2) || 0}%</td>
                <td class="text-right py-2 font-mono ${pnlClass}">${pos.pnl_usd >= 0 ? '+' : ''}$${pos.pnl_usd?.toFixed(2) || '0.00'}</td>
                <td class="text-center py-2"><span class="px-2 py-0.5 rounded text-xs ${statusClass}">${pos.status}</span></td>
            </tr>
        `;
    }).join('');
}

function updateAgentHealth(agents) {
    const container = document.getElementById('agent-health');
    container.innerHTML = agents.map(agent => {
        const color = agent.status === 'healthy' ? '🟢' : agent.status === 'degraded' ? '🟡' : '🔴';
        return `
            <div class="flex justify-between items-center py-1">
                <span class="font-mono text-gray-300">${agent.agent}</span>
                <span class="text-xs">${color} ${agent.status}</span>
            </div>
        `;
    }).join('');
}

function updateEvents(events) {
    const container = document.getElementById('events-log');
    container.innerHTML = events.slice(0, 20).map(evt => {
        const time = evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : '?';
        const typeColor = evt.event_type === 'POSITION_OPENED' ? 'text-blue-400' :
                         evt.event_type === 'POSITION_CLOSED' ? 'text-green-400' :
                         evt.event_type === 'ALERT' ? 'text-red-400' :
                         evt.event_type === 'MANUAL_ACTION' ? 'text-yellow-400' :
                         'text-gray-400';
        return `
            <div class="py-1 border-b border-gray-800/50">
                <span class="text-gray-500">[${time}]</span>
                <span class="${typeColor} font-bold">${evt.event_type}</span>
                <span class="text-gray-400">${evt.source || '?'}</span>
            </div>
        `;
    }).join('');
}

// ── Controls ──

async function sendControl(action) {
    try {
        const response = await fetch(`/control/${action}`, { method: 'POST' });
        const result = await response.json();
        console.log(`Control ${action}:`, result.message);
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    } catch (e) {
        console.error(`Control ${action} failed:`, e);
        alert(`Failed: ${action}`);
    }
}

// ── Init ──

connectWebSocket();
