/**
 * 🐺 KreoPoly Swarm Dashboard — Beast Mode v2
 * Real-time WebSocket updates, charts, controls
 */

// ═══════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════
let ws = null;
let reconnectAttempts = 0;
let maxReconnect = 10;
let state = null;
let performanceChart = null;

// ═══════════════════════════════════════════════════════════
// WEBSOCKET
// ═══════════════════════════════════════════════════════════
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('🔌 WebSocket connected');
        updateConnectionStatus(true);
        reconnectAttempts = 0;
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) {
            console.error('WS parse error:', e);
        }
    };
    
    ws.onclose = () => {
        updateConnectionStatus(false);
        if (reconnectAttempts < maxReconnect) {
            reconnectAttempts++;
            setTimeout(connectWebSocket, 3000);
        }
    };
    
    ws.onerror = (err) => {
        console.error('WS error:', err);
    };
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('ws-status');
    if (connected) {
        status.innerHTML = '<span class="w-2 h-2 rounded-full bg-green-400"></span> ONLINE';
        status.className = 'px-3 py-1 rounded-full text-xs font-mono bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1';
    } else {
        status.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-400"></span> OFFLINE';
        status.className = 'px-3 py-1 rounded-full text-xs font-mono bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1';
    }
}

// ═══════════════════════════════════════════════════════════
// UPDATE DASHBOARD
// ═══════════════════════════════════════════════════════════
function updateDashboard(data) {
    state = data;
    
    // Update timestamp
    document.getElementById('last-update').textContent = 'Updated: ' + new Date().toLocaleTimeString();
    
    // Portfolio
    const portfolio = data.portfolio || {};
    document.getElementById('balance').textContent = formatCurrency(portfolio.balance);
    document.getElementById('daily-pnl').textContent = formatPnL(portfolio.daily_pnl);
    document.getElementById('daily-pnl').className = 'text-lg font-bold ' + (portfolio.daily_pnl >= 0 ? 'text-green-400' : 'text-red-400');
    document.getElementById('total-pnl').textContent = formatPnL(portfolio.total_pnl);
    document.getElementById('total-pnl').className = 'text-lg font-bold ' + (portfolio.total_pnl >= 0 ? 'text-green-400' : 'text-red-400');
    document.getElementById('win-rate').textContent = (portfolio.win_rate || 0).toFixed(1) + '%';
    document.getElementById('drawdown').textContent = (portfolio.drawdown || 0).toFixed(1) + '%';
    
    // Risk
    const riskUsed = portfolio.risk_used || 0;
    const riskBudget = portfolio.risk_budget || 500;
    document.getElementById('risk-used').textContent = `$${riskUsed.toFixed(0)} / $${riskBudget}`;
    document.getElementById('risk-budget-text').textContent = `$${riskUsed.toFixed(0)} / $${riskBudget}`;
    const riskPct = (riskUsed / riskBudget) * 100;
    document.getElementById('risk-budget-bar').style.width = riskPct + '%';
    document.getElementById('risk-budget-bar').className = 
        'h-full rounded-full transition-all ' + 
        (riskPct > 80 ? 'bg-red-500' : riskPct > 50 ? 'bg-yellow-500' : 'bg-green-500');
    
    // Mode badges
    const settings = data.settings || {};
    const modeBadge = document.getElementById('mode-badge');
    modeBadge.textContent = settings.paper_mode ? '📊 PAPER' : '💰 REAL';
    modeBadge.className = settings.paper_mode 
        ? 'px-3 py-1 rounded-full text-xs font-mono bg-blue-500/20 text-blue-400 border border-blue-500/30'
        : 'px-3 py-1 rounded-full text-xs font-mono bg-red-500/20 text-red-400 border border-red-500/30';
    
    const autoBadge = document.getElementById('auto-badge');
    autoBadge.textContent = settings.auto_mode ? '🤖 AUTO' : '🤖 MANUAL';
    autoBadge.className = settings.auto_mode
        ? 'px-3 py-1 rounded-full text-xs font-mono bg-green-500/20 text-green-400 border border-green-500/30'
        : 'px-3 py-1 rounded-full text-xs font-mono bg-gray-500/20 text-gray-400 border border-gray-500/30';
    
    // Circuit breaker / kill switch
    const circuitStatus = document.getElementById('circuit-status');
    circuitStatus.textContent = settings.emergency_stop ? '● TRIGGERED' : '● ACTIVE';
    circuitStatus.className = settings.emergency_stop ? 'text-red-400 font-bold' : 'text-green-400 font-bold';
    
    const killStatus = document.getElementById('kill-switch-status');
    killStatus.textContent = settings.emergency_stop ? '● DISARMED' : '● ARMED';
    killStatus.className = settings.emergency_stop ? 'text-red-400 font-bold' : 'text-green-400 font-bold';
    
    // Market Regime
    const regime = data.market_regime || 'CHOP';
    const regimeEl = document.getElementById('market-regime');
    regimeEl.textContent = {
        'BULL': '🐂 BULL',
        'BEAR': '🐻 BEAR', 
        'CHOP': '📊 CHOP',
        'HIGH_VOL': '⚡ HIGH VOL',
    }[regime] || '📊 CHOP';
    regimeEl.className = 'px-3 py-1.5 rounded-lg text-xs font-bold border ' + {
        'BULL': 'bg-green-500/20 text-green-400 border-green-500/30',
        'BEAR': 'bg-red-500/20 text-red-400 border-red-500/30',
        'CHOP': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
        'HIGH_VOL': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    }[regime] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    
    // Multi-chain
    const chains = data.chains || {};
    updateChainCard('solana', chains.solana);
    updateChainCard('base', chains.base);
    updateChainCard('eth', chains.ethereum);
    
    // Positions
    const positions = data.open_positions || [];
    document.getElementById('positions-count').textContent = positions.length;
    updatePositionsTable(positions);
    
    // Signals
    const signals = data.active_signals || [];
    document.getElementById('signals-count').textContent = signals.length;
    updateActiveSignals(signals);
    
    // Agent Health
    updateAgentHealth(data.agent_health || []);
    
    // Events
    updateEvents(data.recent_events || []);
    
    // Whale
    updateWhaleActivity(data.whale_activity || []);
    
    // Performance chart
    updatePerformanceChart(data.performance_history || []);
}

function updateChainCard(chain, data) {
    if (!data) return;
    document.getElementById(`${chain}-pairs`).textContent = data.pairs || '--';
    document.getElementById(`${chain}-signals`).textContent = data.signals || '--';
    document.getElementById(`${chain}-volume`).textContent = formatVolume(data.volume);
}

function updatePositionsTable(positions) {
    const tbody = document.getElementById('positions-table');
    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-600">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => {
        const pnlClass = pos.pnl_percent >= 0 ? 'text-green-400' : 'text-red-400';
        const sltp = pos.stop_loss && pos.take_profits 
            ? `SL ${pos.stop_loss.toFixed(2)} / TP ${pos.take_profits[0]?.toFixed(2) || '?'}`
            : 'N/A';
        return `
            <tr class="border-b border-white/5 hover:bg-white/5 transition">
                <td class="py-2 font-bold">${pos.symbol}</td>
                <td class="text-right py-2 text-gray-400">$${pos.entry_price?.toFixed(6) || '?'}</td>
                <td class="text-right py-2">$${pos.current_price?.toFixed(6) || '?'}</td>
                <td class="text-right py-2 ${pnlClass}">${pos.pnl_percent?.toFixed(2) || 0}%</td>
                <td class="text-right py-2 ${pnlClass}">${formatPnL(pos.pnl_usd || 0)}</td>
                <td class="text-center py-2 text-gray-500">${pos.time_in_trade || '0m'}</td>
                <td class="text-center py-2 text-[10px] text-gray-500">${sltp}</td>
            </tr>
        `;
    }).join('');
}

function updateActiveSignals(signals) {
    const container = document.getElementById('active-signals');
    if (signals.length === 0) {
        container.innerHTML = '<div class="text-center py-8 text-gray-600 text-xs">No active signals</div>';
        return;
    }
    
    container.innerHTML = signals.map(sig => {
        const scoreColor = sig.score >= 80 ? 'bg-green-500' : sig.score >= 68 ? 'bg-yellow-500' : 'bg-orange-500';
        const scoreText = sig.score >= 80 ? 'text-green-400' : sig.score >= 68 ? 'text-yellow-400' : 'text-orange-400';
        return `
            <div class="glass-hover rounded-lg p-3 transition cursor-pointer slide-in">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <span class="text-xs px-1.5 py-0.5 rounded bg-white/10">${sig.chain?.toUpperCase()}</span>
                        <span class="font-bold text-sm">${sig.symbol}</span>
                    </div>
                    <span class="text-lg font-bold ${scoreText}">${sig.score}/100</span>
                </div>
                <div class="w-full h-1 bg-gray-700 rounded-full mb-2">
                    <div class="${scoreColor} h-full rounded-full transition-all" style="width: ${sig.score}%"></div>
                </div>
                <div class="flex justify-between text-[10px] text-gray-500">
                    <span>Score: ${sig.score_details?.liquidity || 0}L ${sig.score_details?.volume || 0}V ${sig.score_details?.momentum || 0}M</span>
                    <span>${sig.reason || 'Momentum'}</span>
                </div>
                <div class="mt-2 flex gap-1">
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-400">TP1 +${sig.tp1_pct || 4}%</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">SL ${sig.sl_pct || -3.5}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateAgentHealth(agents) {
    const container = document.getElementById('agent-health');
    container.innerHTML = agents.map(agent => {
        const statusColor = {
            'healthy': 'text-green-400',
            'warning': 'text-yellow-400',
            'down': 'text-red-400',
        }[agent.status] || 'text-gray-400';
        
        const statusBg = {
            'healthy': 'bg-green-500/10',
            'warning': 'bg-yellow-500/10',
            'down': 'bg-red-500/10',
        }[agent.status] || 'bg-gray-500/10';
        
        const fitness = agent.fitness || 0;
        const fitnessColor = fitness > 80 ? 'text-green-400' : fitness > 60 ? 'text-yellow-400' : 'text-red-400';
        
        return `
            <div class="flex items-center justify-between p-2 rounded-lg ${statusBg} hover:bg-white/5 transition">
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full ${statusColor.replace('text-', 'bg-')}"></span>
                    <span class="text-xs font-bold">${agent.agent}</span>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-[10px] text-gray-500">${agent.last_check?.split('T')[1]?.split('.')[0] || '--'}</span>
                    <span class="text-xs ${fitnessColor} font-bold">${fitness.toFixed(0)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function updateEvents(events) {
    const container = document.getElementById('events-log');
    if (events.length === 0) return;
    
    container.innerHTML = events.slice(0, 30).map(evt => {
        const time = evt.timestamp?.split('T')[1]?.split('.')[0] || '--';
        const typeColor = {
            'POSITION_OPENED': 'text-green-400',
            'POSITION_CLOSED': 'text-blue-400',
            'RISK_ASSESSED': 'text-yellow-400',
            'ALERT': 'text-red-400',
            'MANUAL_ACTION': 'text-purple-400',
        }[evt.event_type] || 'text-gray-400';
        
        return `
            <div class="flex items-start gap-2 py-1 border-b border-white/5 hover:bg-white/5 transition">
                <span class="text-gray-600 text-[10px] min-w-[50px]">${time}</span>
                <span class="${typeColor} text-[10px] min-w-[80px] font-bold">${evt.event_type}</span>
                <span class="text-gray-400 text-[10px] truncate">${JSON.stringify(evt.data).substring(0, 60)}</span>
            </div>
        `;
    }).join('');
}

function updateWhaleActivity(whales) {
    const container = document.getElementById('whale-activity');
    if (!whales || whales.length === 0) {
        container.innerHTML = '<div class="text-center py-4 text-gray-600">Waiting for whale data...</div>';
        return;
    }
    
    container.innerHTML = whales.map(w => `
        <div class="flex items-center justify-between p-2 rounded-lg bg-white/5 hover:bg-white/10 transition">
            <div>
                <span class="text-xs font-bold">${w.symbol || '?'}</span>
                <span class="text-[10px] text-gray-500"> ${w.action || 'buy'}</span>
            </div>
            <div class="text-right">
                <span class="text-xs ${w.action === 'buy' ? 'text-green-400' : 'text-red-400'}">${formatVolume(w.amount)}</span>
                <span class="text-[10px] text-gray-500"> ${w.wallet?.substring(0, 8) || '?'}...</span>
            </div>
        </div>
    `).join('');
}

function updatePerformanceChart(history) {
    if (!history || history.length === 0) return;
    
    // If chart doesn't exist, create it
    if (!performanceChart) {
        const chartEl = document.getElementById('performance-chart');
        if (!chartEl) return;
        
        performanceChart = new ApexCharts(chartEl, {
            chart: {
                type: 'area',
                height: 180,
                toolbar: { show: false },
                background: 'transparent',
            },
            theme: { mode: 'dark' },
            stroke: { curve: 'smooth', width: 2 },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.3,
                    opacityTo: 0.05,
                    stops: [0, 100]
                }
            },
            dataLabels: { enabled: false },
            xaxis: {
                type: 'datetime',
                labels: { style: { colors: '#6b7280', fontSize: '10px' } },
                axisBorder: { show: false },
                axisTicks: { show: false },
            },
            yaxis: {
                labels: { style: { colors: '#6b7280', fontSize: '10px' } },
            },
            grid: {
                borderColor: 'rgba(255,255,255,0.05)',
                strokeDashArray: 4,
            },
            tooltip: {
                theme: 'dark',
                style: { fontSize: '12px' },
            },
            series: [{
                name: 'PnL',
                data: history.map(h => ({ x: new Date(h.time).getTime(), y: h.pnl }))
            }],
            colors: ['#22c55e'],
        });
        performanceChart.render();
    } else {
        performanceChart.updateSeries([{
            data: history.map(h => ({ x: new Date(h.time).getTime(), y: h.pnl }))
        }]);
    }
}

function setChartPeriod(period) {
    // Will be implemented to fetch different time ranges
    console.log('Chart period:', period);
}

// ═══════════════════════════════════════════════════════════
// CONTROLS
// ═══════════════════════════════════════════════════════════
async function sendControl(action) {
    try {
        const response = await fetch(`/control/${action}`, { method: 'POST' });
        const result = await response.json();
        
        showToast(result.message || action, result.status === 'ok' ? 'success' : 'error');
        
        if (action === 'emergency-stop') {
            showToast('🛑 EMERGENCY STOP ACTIVATED — All trading halted!', 'error');
        }
    } catch (e) {
        showToast('Control failed: ' + e.message, 'error');
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    const colors = {
        success: 'bg-green-500/20 border-green-500/30 text-green-400',
        error: 'bg-red-500/20 border-red-500/30 text-red-400',
        warning: 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400',
        info: 'bg-blue-500/20 border-blue-500/30 text-blue-400',
    };
    
    toast.className = `toast px-4 py-3 rounded-xl border text-sm font-bold ${colors[type] || colors.info}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function clearEvents() {
    document.getElementById('events-log').innerHTML = '<div class="text-gray-600 py-2">Events cleared</div>';
}

// ═══════════════════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ═══════════════════════════════════════════════════════════
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    switch(e.key.toUpperCase()) {
        case 'E':
            if (confirm('🛑 ACTIVATE EMERGENCY STOP?')) {
                sendControl('emergency-stop');
            }
            break;
        case 'P':
            sendControl('pause');
            break;
        case 'A':
            sendControl('confirm-trade');
            break;
        case 'R':
            sendControl('resume');
            break;
    }
});

// ═══════════════════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════════════════
function formatCurrency(val) {
    if (val >= 1000000) return '$' + (val / 1000000).toFixed(2) + 'M';
    if (val >= 1000) return '$' + (val / 1000).toFixed(1) + 'K';
    return '$' + val.toFixed(2);
}

function formatPnL(val) {
    const sign = val >= 0 ? '+' : '';
    return sign + '$' + val.toFixed(2);
}

function formatVolume(val) {
    if (!val) return '--';
    if (val >= 1000000) return '$' + (val / 1000000).toFixed(1) + 'M';
    if (val >= 1000) return '$' + (val / 1000).toFixed(0) + 'K';
    return '$' + val.toFixed(0);
}

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    showToast('🐺 Dashboard loaded — Beast Mode v2 active', 'success');
});
