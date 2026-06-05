// Dashboard JavaScript - Real-time updates and controls
const API_BASE = '/api';
let isRunning = false;
let autoRefreshInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    addLog('Dashboard loaded. System ready.');
});

// Start/Stop App
async function startApp() {
    try {
        const response = await fetch(`${API_BASE}/start`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            isRunning = true;
            updateUIState(true);
            addLog('🚀 App started - scanning for opportunities');
            startAutoRefresh();
        } else {
            addLog(`❌ Failed to start: ${data.error}`);
        }
    } catch (e) {
        addLog(`❌ Error: ${e.message}`);
    }
}

async function stopApp() {
    try {
        const response = await fetch(`${API_BASE}/stop`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            isRunning = false;
            updateUIState(false);
            addLog('🛑 App stopped');
            stopAutoRefresh();
        }
    } catch (e) {
        addLog(`❌ Error: ${e.message}`);
    }
}

function updateUIState(running) {
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    if (running) {
        statusDot.classList.add('active');
        statusText.textContent = 'Scanning...';
        btnStart.disabled = true;
        btnStop.disabled = false;
    } else {
        statusDot.classList.remove('active');
        statusText.textContent = 'Stopped';
        btnStart.disabled = false;
        btnStop.disabled = true;
    }
}

// Refresh Data
async function refreshData() {
    await loadDashboardData();
    addLog('🔄 Data refreshed');
}

async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/dashboard`);
        const data = await response.json();
        
        updateStats(data.stats);
        updateOpportunitiesTable(data.opportunities);
        updateUIState(data.running);
        updateOSINT(data.osint_reports);
        updateMode(data.mode);
        
        document.getElementById('last-scan').textContent = 
            `Last scan: ${data.last_scan ? new Date(data.last_scan).toLocaleTimeString() : 'Never'}`;
        
        isRunning = data.running;
        if (isRunning && !autoRefreshInterval) {
            startAutoRefresh();
        }
    } catch (e) {
        addLog(`❌ Failed to load data: ${e.message}`);
    }
}

function startAutoRefresh() {
    autoRefreshInterval = setInterval(loadDashboardData, 30000); // 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Update Stats
function updateStats(stats) {
    document.getElementById('stat-total').textContent = stats.total_opportunities || 0;
    document.getElementById('stat-executed').textContent = stats.executed || 0;
    document.getElementById('stat-profit').textContent = `${stats.avg_profit_pct || 0}%`;
    document.getElementById('stat-winrate').textContent = `${stats.win_rate || 0}%`;
    document.getElementById('stat-today').textContent = stats.today_opportunities || 0;
    document.getElementById('stat-active').textContent = stats.active_count || 0;
}

// Update Opportunities Table
function updateOpportunitiesTable(opportunities) {
    const tbody = document.getElementById('opportunities-body');
    const filter = document.getElementById('filter-status').value;
    
    let filtered = opportunities;
    if (filter !== 'all') {
        filtered = opportunities.filter(o => o.status === filter);
    }
    
    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="11">No ${filter !== 'all' ? filter.replace('_', ' ') : ''} opportunities found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = filtered.map(opp => {
        const rowClass = opp.golden_hour ? 'golden-hour' : 
                        opp.status === 'cashout_ready' ? 'cashout-ready' : '';
        
        const statusBadge = getStatusBadge(opp.status);
        const confidenceColor = opp.confidence >= 70 ? 'high' : 
                               opp.confidence >= 50 ? 'medium' : 'low';
        
        return `
            <tr class="${rowClass}" data-match-id="${opp.match_id}">
                <td><strong>${opp.match_name}</strong></td>
                <td>${opp.league || '-'}</td>
                <td>${formatDate(opp.kickoff)}</td>
                <td>${opp.market} - ${opp.selection}</td>
                <td><span class="badge badge-danger">-${opp.pinnacle_drop_pct?.toFixed(1)}%</span></td>
                <td>${opp.stoiximan_odds?.toFixed(2) || '-'}</td>
                <td><span class="badge badge-success">+${opp.value_edge?.toFixed(1)}%</span></td>
                <td>
                    <div class="confidence-bar">
                        <div class="confidence-fill ${confidenceColor}" style="width: ${opp.confidence}%"></div>
                    </div>
                    <span style="font-size: 11px">${opp.confidence}/100</span>
                </td>
                <td>${opp.golden_hour ? '🔥 YES' : 'No'}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-small" onclick="viewDetails('${opp.match_id}')">View</button>
                    ${opp.status === 'cashout_ready' ? 
                        `<button class="btn btn-small btn-primary" onclick="markExecuted('${opp.match_id}')">✅ Done</button>` : 
                        ''}
                </td>
            </tr>
        `;
    }).join('');
}

function getStatusBadge(status) {
    const badges = {
        'detected': '<span class="badge badge-info">Detected</span>',
        'tracking': '<span class="badge badge-warning">Tracking</span>',
        'cashout_ready': '<span class="badge badge-success">🔥 CASHOUT!</span>',
        'executed': '<span class="badge badge-success">✅ Executed</span>',
        'expired': '<span class="badge badge-danger">Expired</span>',
        'missed': '<span class="badge badge-danger">Missed</span>'
    };
    return badges[status] || `<span class="badge">${status}</span>`;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('en-GB', { 
        day: '2-digit', 
        month: 'short', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function updateOSINT(osintReports) {
    const container = document.getElementById('osint-container');
    
    if (!osintReports || Object.keys(osintReports).length === 0) {
        container.innerHTML = '<div class="empty-row">No OSINT reports yet</div>';
        return;
    }
    
    let html = '';
    for (const [matchId, reports] of Object.entries(osintReports)) {
        if (reports.length === 0) continue;
        
        html += `<div class="osint-match">`;
        html += `<h4>🎯 Match ID: ${matchId}</h4>`;
        
        reports.forEach(report => {
            const badgeClass = report.confidence >= 70 ? 'badge-success' : 
                              report.confidence >= 50 ? 'badge-warning' : 'badge-danger';
            
            html += `
                <div class="osint-report">
                    <span class="badge ${badgeClass}">${report.type.toUpperCase()}</span>
                    <span class="osint-source">${report.source}</span>
                    <span class="osint-confidence">Confidence: ${report.confidence}%</span>
                    <p class="osint-summary">${report.summary}</p>
                </div>
            `;
        });
        
        html += `</div>`;
    }
    
    container.innerHTML = html;
}

function updateMode(mode) {
    const badge = document.getElementById('mode-badge');
    if (mode === 'demo') {
        badge.className = 'badge badge-warning';
        badge.textContent = 'DEMO MODE';
    } else {
        badge.className = 'badge badge-success';
        badge.textContent = 'LIVE MODE';
    }
}

// Actions
function viewDetails(matchId) {
    addLog(`📋 Viewing details for match ${matchId}`);
    // In production: Show modal with full details
}

async function markExecuted(matchId) {
    try {
        const response = await fetch(`${API_BASE}/opportunities/${matchId}/execute`, { 
            method: 'POST' 
        });
        const data = await response.json();
        
        if (data.success) {
            addLog(`✅ Marked ${matchId} as executed`);
            loadDashboardData();
        }
    } catch (e) {
        addLog(`❌ Error marking executed: ${e.message}`);
    }
}

// Settings
async function saveSettings() {
    const settings = {
        scan_interval: parseInt(document.getElementById('scan-interval').value),
        min_drop: parseFloat(document.getElementById('min-drop').value),
        min_confidence: parseInt(document.getElementById('min-confidence').value),
        bankroll: parseFloat(document.getElementById('bankroll').value),
        max_stake_pct: parseFloat(document.getElementById('max-stake').value),
        telegram_alerts: document.getElementById('telegram-alerts').checked
    };
    
    try {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            addLog('💾 Settings saved successfully');
        } else {
            addLog('❌ Failed to save settings');
        }
    } catch (e) {
        addLog(`❌ Error saving settings: ${e.message}`);
    }
}

// Logs
function addLog(message) {
    const container = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    container.insertBefore(entry, container.firstChild);
    
    // Keep only last 100 entries
    while (container.children.length > 100) {
        container.removeChild(container.lastChild);
    }
}

function clearLogs() {
    document.getElementById('log-container').innerHTML = '';
    addLog('Logs cleared');
}

// WebSocket connection for real-time updates (if available)
function connectWebSocket() {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = () => {
        addLog('🔌 Real-time connection established');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'opportunity') {
            addLog(`🎯 New opportunity detected: ${data.match_name}`);
            loadDashboardData();
        } else if (data.type === 'golden_hour') {
            addLog(`🔥 GOLDEN HOUR: ${data.match_name} - CASHOUT NOW!`);
            // Play alert sound if desired
        }
    };
    
    ws.onclose = () => {
        addLog('⚠️ Real-time connection lost. Reconnecting in 5s...');
        setTimeout(connectWebSocket, 5000);
    };
}

// Try to connect WebSocket on load
// connectWebSocket(); // Uncomment when WebSocket is implemented
