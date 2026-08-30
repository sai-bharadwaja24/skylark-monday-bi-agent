"""
Skylark Drones — Monday.com Business Intelligence Agent
Zero-Dependency Standalone Web Server & Interactive Dashboard
Runs natively with Python standard library.
"""

import json
import http.server
import socketserver
import urllib.parse
from typing import Dict, Any, List

from monday_client_core import MondayClient
from data_resilience_engine import DataResilienceEngine
from cross_board_engine import CrossBoardEngine, format_inr
from bi_agent_core import BIAgentCore
from leadership_update_generator import LeadershipUpdateGenerator
from tabular_data import Table

PORT = 8501

# Global state
raw_deals = MondayClient.generate_mock_deals()
raw_wos = MondayClient.generate_mock_work_orders()
clean_deals = DataResilienceEngine.clean_deals(raw_deals)
clean_wos = DataResilienceEngine.clean_work_orders(raw_wos)
cross_engine = CrossBoardEngine(clean_deals, clean_wos)
hygiene_audit = DataResilienceEngine.audit_data_hygiene(clean_deals, clean_wos)
bi_agent = BIAgentCore(clean_deals, clean_wos)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skylark Drones | Monday.com BI Agent</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0F172A;
            --card-bg: #1E293B;
            --border: #334155;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --primary: #38BDF8;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --accent: #818CF8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }
        header { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 18px 32px; display: flex; justify-content: space-between; align-items: center; }
        .logo-area { display: flex; align-items: center; gap: 14px; }
        .logo-area h1 { font-size: 1.35rem; font-weight: 700; color: #FFFFFF; }
        .badge { background: #065F46; color: #34D399; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 9999px; border: 1px solid #10B981; }
        .badge-danger { background: #7F1D1D; color: #F87171; border-color: #EF4444; }
        
        .main-container { max-width: 1440px; margin: 0 auto; width: 100%; padding: 24px 32px; flex: 1; }
        .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .kpi-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; }
        .kpi-title { font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; letter-spacing: 0.05em; margin-bottom: 6px; }
        .kpi-val { font-size: 1.6rem; font-weight: 700; color: var(--primary); }
        .kpi-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }
        .kpi-card.risk { border-color: #7F1D1D; }
        .kpi-card.risk .kpi-val { color: var(--danger); }

        .tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
        .tab-btn { background: none; border: none; color: var(--text-muted); font-size: 0.95rem; font-weight: 600; padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
        .tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        /* Chat UI */
        .chat-container { display: grid; grid-template-columns: 320px 1fr; gap: 24px; }
        .quick-prompts { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; height: fit-content; }
        .quick-prompts h3 { font-size: 0.95rem; margin-bottom: 14px; color: var(--text-main); }
        .prompt-btn { display: block; width: 100%; text-align: left; background: #0F172A; border: 1px solid var(--border); color: #E2E8F0; padding: 10px 14px; border-radius: 8px; font-size: 0.84rem; margin-bottom: 10px; cursor: pointer; transition: 0.2s; }
        .prompt-btn:hover { border-color: var(--primary); color: var(--primary); }

        .chat-box { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 24px; display: flex; flex-direction: column; min-height: 580px; }
        .messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; max-height: 480px; }
        .msg-user { align-self: flex-end; background: #2563EB; color: white; padding: 12px 18px; border-radius: 14px 14px 2px 14px; max-width: 80%; font-size: 0.92rem; }
        .msg-agent { align-self: flex-start; background: #0F172A; border: 1px solid var(--border); color: var(--text-main); padding: 20px; border-radius: 14px 14px 14px 2px; max-width: 95%; width: 100%; }
        .msg-agent h4 { color: var(--primary); margin-bottom: 8px; font-size: 1.05rem; }
        .msg-agent p { font-size: 0.95rem; line-height: 1.5; margin-bottom: 12px; }
        .msg-metrics { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
        .msg-metric-badge { background: #1E293B; border: 1px solid var(--border); border-radius: 6px; padding: 6px 12px; font-size: 0.82rem; }
        .msg-metric-badge b { color: var(--primary); }

        .rec-box { background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--success); padding: 10px 14px; border-radius: 4px; color: #A7F3D0; font-size: 0.88rem; margin: 8px 0; }
        .cav-box { background: rgba(245, 158, 11, 0.1); border-left: 4px solid var(--warning); padding: 10px 14px; border-radius: 4px; color: #FDE68A; font-size: 0.88rem; margin: 8px 0; }

        .followups { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
        .followup-btn { background: #1E293B; border: 1px solid #475569; color: #94A3B8; padding: 6px 12px; border-radius: 20px; font-size: 0.78rem; cursor: pointer; }
        .followup-btn:hover { border-color: var(--primary); color: var(--primary); }

        .input-bar { display: flex; gap: 12px; }
        .input-bar input { flex: 1; background: #0F172A; border: 1px solid var(--border); border-radius: 8px; color: white; padding: 12px 16px; font-size: 0.95rem; outline: none; }
        .input-bar input:focus { border-color: var(--primary); }
        .btn-send { background: var(--primary); color: #0F172A; border: none; font-weight: 700; padding: 0 24px; border-radius: 8px; cursor: pointer; }

        /* Tables */
        table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 0.84rem; }
        th { background: #0F172A; color: var(--text-muted); text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); text-transform: uppercase; font-size: 0.72rem; }
        td { padding: 10px 12px; border-bottom: 1px solid var(--border); color: #E2E8F0; }
        tr:hover { background: rgba(255,255,255,0.02); }

        /* Charts */
        .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
        .chart-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .chart-card h3 { font-size: 0.95rem; margin-bottom: 16px; color: var(--text-muted); }

        /* Leadership Update */
        .lead-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 28px; line-height: 1.7; }
        .lead-card h1 { color: #FFFFFF; font-size: 1.5rem; margin-bottom: 4px; }
        .lead-card h2 { color: var(--primary); font-size: 1.2rem; margin: 24px 0 12px 0; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
        .lead-card h3 { color: #F1F5F9; font-size: 1rem; margin: 14px 0 6px 0; }
        .lead-card p { margin-bottom: 12px; color: #E2E8F0; }
        .lead-card ul, .lead-card ol { padding-left: 24px; margin-bottom: 14px; }
        .lead-card li { margin-bottom: 6px; color: #E2E8F0; }
        .lead-actions { display: flex; gap: 12px; margin-bottom: 20px; }
        .btn-action { background: #1E293B; border: 1px solid var(--border); color: var(--primary); font-weight: 600; padding: 10px 18px; border-radius: 6px; cursor: pointer; transition: 0.2s; }
        .btn-action:hover { background: #334155; }
    </style>
</head>
<body>

<header>
    <div class="logo-area">
        <span style="font-size: 2rem;">🚁</span>
        <div>
            <h1>Skylark Drones — Monday.com BI Agent</h1>
            <small style="color: var(--text-muted);">Autonomous Cross-Board Intelligence & Executive Analytics</small>
        </div>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <span class="badge" id="hygiene-badge">Data Hygiene: 81.0%</span>
        <span class="badge" id="board-counts-badge" style="background:#1E293B; color:#94A3B8; border-color:#475569;">346 Deals | 176 Work Orders</span>
    </div>
</header>

<div class="main-container">

    <!-- KPI Summary Row -->
    <div class="kpi-row" id="kpi-container">
        <div class="kpi-card">
            <div class="kpi-title">Closed Won Revenue</div>
            <div class="kpi-val" id="kpi-won">₹3.98 Cr</div>
            <div class="kpi-sub" id="kpi-won-sub">9 closed engagements</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Weighted Pipeline</div>
            <div class="kpi-val" id="kpi-weighted">₹3.28 Cr</div>
            <div class="kpi-sub" id="kpi-open-sub">₹6.21 Cr unweighted</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Win Rate</div>
            <div class="kpi-val" id="kpi-winrate">81.8%</div>
            <div class="kpi-sub">Avg Size: ₹44.2 L</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Delivery SLA</div>
            <div class="kpi-val" id="kpi-sla">100%</div>
            <div class="kpi-sub">Avg CSAT: 4.7 / 5.0</div>
        </div>
        <div class="kpi-card risk">
            <div class="kpi-title">Revenue at Risk</div>
            <div class="kpi-val" id="kpi-risk">₹1.93 Cr</div>
            <div class="kpi-sub" id="kpi-risk-sub">5 at-risk account(s)</div>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('chat')">💬 Founder BI Assistant</button>
        <button class="tab-btn" onclick="switchTab('briefing')">📋 Leadership Update Studio</button>
        <button class="tab-btn" onclick="switchTab('visuals')">📊 Executive Analytics & Visuals</button>
        <button class="tab-btn" onclick="switchTab('hygiene')">🔌 Monday.com & Data Health</button>
    </div>

    <!-- TAB 1: Chat Assistant -->
    <div id="tab-chat" class="tab-content active">
        <div class="chat-container">
            <div class="quick-prompts">
                <h3>⚡ Founder Quick Prompts</h3>
                <button class="prompt-btn" onclick="askQuestion('How is our pipeline looking for the energy sector this quarter?')">⚡ How is our pipeline looking for energy sector this quarter?</button>
                <button class="prompt-btn" onclick="askQuestion('Which high-value clients have delayed work orders?')">⚠️ Which high-value clients have delayed work orders?</button>
                <button class="prompt-btn" onclick="askQuestion('What is our overall win rate and average deal size?')">💰 What is our overall win rate and average deal size?</button>
                <button class="prompt-btn" onclick="askQuestion('Compare pipeline and revenue across all sectors')">🌐 Compare pipeline and revenue across all sectors</button>
                <button class="prompt-btn" onclick="askQuestion('Prepare leadership update for Q2 2024')">📋 Prepare leadership update for Q2 2024</button>
                <button class="prompt-btn" onclick="askQuestion('Audit Monday.com data quality and caveats')">🛡️ Audit Monday.com data quality and caveats</button>
            </div>

            <div class="chat-box">
                <div class="messages" id="messages-list">
                    <div class="msg-agent">
                        <h4>👋 Welcome, Founder / Executive</h4>
                        <p>I am your <b>Monday.com Business Intelligence Agent</b>. I analyze live deals and operational work order boards, normalize messy dates/currencies, detect delivery bottlenecks, and generate actionable executive briefings.</p>
                        <p>Ask a strategic question or click any prompt on the left to begin.</p>
                    </div>
                </div>

                <div class="input-bar">
                    <input type="text" id="query-input" placeholder="Ask a question (e.g. 'How is our pipeline looking for energy sector this quarter?')" onkeypress="if(event.key==='Enter') sendUserQuery()">
                    <button class="btn-send" onclick="sendUserQuery()">Send</button>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 2: Leadership Briefing -->
    <div id="tab-briefing" class="tab-content">
        <div class="lead-actions">
            <button class="btn-action" onclick="copySlackText()">📱 Copy for Slack / Email</button>
            <button class="btn-action" onclick="downloadMarkdown()">📥 Download Report (.md)</button>
        </div>
        <div class="lead-card" id="leadership-content">
            <p>Loading leadership update...</p>
        </div>
    </div>

    <!-- TAB 3: Visual Analytics -->
    <div id="tab-visuals" class="tab-content">
        <div class="chart-grid">
            <div class="chart-card">
                <h3>📈 Deals Pipeline Funnel by Stage</h3>
                <canvas id="chart-funnel" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>🌐 Sector Revenue & Open Pipeline</h3>
                <canvas id="chart-sector" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>⚙️ Work Order Delivery Status (SLA)</h3>
                <canvas id="chart-sla" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>⚠️ At-Risk Accounts & Bottleneck Revenue</h3>
                <canvas id="chart-risk" height="200"></canvas>
            </div>
        </div>
    </div>

    <!-- TAB 4: Data Hygiene -->
    <div id="tab-hygiene" class="tab-content">
        <div class="kpi-card" style="margin-bottom: 20px;">
            <div class="kpi-title">Data Quality Score</div>
            <div class="kpi-val" style="color: var(--success);" id="hygiene-score-display">81.0%</div>
            <div class="kpi-sub">51 of 63 validation checks passed across Deals & Work Orders boards</div>
        </div>
        <h3 style="margin-bottom: 12px; color: var(--warning);">⚠️ Active Data Hygiene Caveats & Cleaning Notes</h3>
        <div id="caveats-list"></div>
        
        <h3 style="margin: 24px 0 12px 0;">🔍 Normalized Deals Board Data Preview</h3>
        <div style="overflow-x: auto;" id="deals-table-preview"></div>

        <h3 style="margin: 24px 0 12px 0;">🔍 Normalized Work Orders Board Data Preview</h3>
        <div style="overflow-x: auto;" id="wo-table-preview"></div>
    </div>

</div>

<script>
let currentSlackText = "";
let currentMarkdownReport = "";

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById('tab-' + tabId).classList.add('active');

    if (tabId === 'visuals') {
        renderCharts();
    }
}

async function loadKPIs() {
    try {
        const resp = await fetch('/api/kpis');
        const data = await resp.json();
        document.getElementById('kpi-won').innerText = data.closed_won_revenue_formatted || '₹0';
        document.getElementById('kpi-won-sub').innerText = (data.closed_won_count || 0) + ' closed engagements';
        document.getElementById('kpi-weighted').innerText = data.weighted_pipeline_formatted || '₹0';
        document.getElementById('kpi-open-sub').innerText = (data.open_pipeline_formatted || '₹0') + ' unweighted';
        document.getElementById('kpi-winrate').innerText = (data.win_rate_pct || 0) + '%';
        document.getElementById('kpi-sla').innerText = (data.on_time_delivery_rate_pct || 100) + '%';
        document.getElementById('kpi-risk').innerText = data.revenue_at_risk_formatted || '₹0';
        const riskSub = document.getElementById('kpi-risk-sub');
        if (riskSub) {
            riskSub.innerText = (data.delayed_accounts_count || 0) + ' at-risk account(s)';
        }
        const badge = document.getElementById('board-counts-badge');
        if (badge && data.total_deals_count) {
            badge.innerText = data.total_deals_count + ' Deals | ' + (data.total_work_orders || 176) + ' Work Orders';
        }
    } catch(e) { console.error('Error loading KPIs:', e); }
}

function parseMarkdownToHtml(md) {
    if (!md) return '';
    return md
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/\\*\\*(.*?)\\*\\*/gim, '<b>$1</b>')
        .replace(/\\*(.*?)\\*/gim, '<i>$1</i>')
        .replace(/^\\- (.*$)/gim, '<li>$1</li>')
        .replace(/^(\\d+)\\. (.*$)/gim, '<li>$2</li>')
        .replace(/\\n\\n/gim, '<p></p>')
        .replace(/\\n/gim, '<br>');
}

async function loadLeadershipBriefing() {
    try {
        const resp = await fetch('/api/leadership');
        const data = await resp.json();
        currentSlackText = data.slack_text || "";
        currentMarkdownReport = data.markdown_report || "";

        if (currentMarkdownReport) {
            document.getElementById('leadership-content').innerHTML = parseMarkdownToHtml(currentMarkdownReport);
        } else {
            document.getElementById('leadership-content').innerHTML = '<p>Executive Briefing Loaded.</p>';
        }
    } catch(e) { 
        console.error('Error loading briefing:', e);
        document.getElementById('leadership-content').innerHTML = '<p style="color:var(--danger)">Failed to load briefing. Please refresh.</p>';
    }
}

async function loadHygiene() {
    try {
        const resp = await fetch('/api/hygiene');
        const data = await resp.json();
        document.getElementById('hygiene-badge').innerText = 'Data Hygiene: ' + data.hygiene_score + '%';
        document.getElementById('hygiene-score-display').innerText = data.hygiene_score + '%';
        
        let cHtml = '';
        data.caveats.forEach(c => {
            cHtml += `<div class="cav-box">⚠️ ${c}</div>`;
        });
        document.getElementById('caveats-list').innerHTML = cHtml;

        const bResp = await fetch('/api/boards');
        const bData = await bResp.json();
        
        // Deals table
        let dHtml = '<table><thead><tr><th>Deal ID</th><th>Deal Name</th><th>Client</th><th>Sector</th><th>Value</th><th>Stage</th><th>Quarter</th><th>Owner</th></tr></thead><tbody>';
        bData.deals.forEach(d => {
            dHtml += `<tr><td>${d.deal_id}</td><td>${d.deal_name}</td><td>${d.client}</td><td>${d.sector}</td><td><b>${d.deal_value_formatted}</b></td><td>${d.stage}</td><td>${d.quarter}</td><td>${d.owner}</td></tr>`;
        });
        dHtml += '</tbody></table>';
        document.getElementById('deals-table-preview').innerHTML = dHtml;

        // WOs table
        let wHtml = '<table><thead><tr><th>WO ID</th><th>Deal Ref</th><th>Client</th><th>Project Title</th><th>Sector</th><th>Status</th><th>Target Date</th><th>Blockers</th></tr></thead><tbody>';
        bData.work_orders.forEach(w => {
            wHtml += `<tr><td>${w.wo_id}</td><td>${w.deal_ref||'-'}</td><td>${w.client}</td><td>${w.project_title}</td><td>${w.sector}</td><td><b>${w.status}</b></td><td>${w.target_delivery_date||'-'}</td><td>${w.blockers||'-'}</td></tr>`;
        });
        wHtml += '</tbody></table>';
        document.getElementById('wo-table-preview').innerHTML = wHtml;

    } catch(e) { console.error(e); }
}

async function askQuestion(q) {
    document.getElementById('query-input').value = q;
    sendUserQuery();
}

async function sendUserQuery() {
    const input = document.getElementById('query-input');
    const query = input.value.trim();
    if (!query) return;

    const msgList = document.getElementById('messages-list');
    msgList.innerHTML += `<div class="msg-user">👤 <b>You:</b> ${query}</div>`;
    input.value = '';
    msgList.scrollTop = msgList.scrollHeight;

    try {
        const resp = await fetch('/api/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query: query })
        });
        const res = await resp.json();

        let agentHtml = `<div class="msg-agent">`;
        agentHtml += `<h4>${res.title}</h4>`;
        agentHtml += `<p>${res.executive_summary}</p>`;

        if (res.metrics) {
            agentHtml += `<div class="msg-metrics">`;
            for (const [k, v] of Object.entries(res.metrics)) {
                agentHtml += `<div class="msg-metric-badge">${k}: <b>${v}</b></div>`;
            }
            agentHtml += `</div>`;
        }

        if (res.data_table && res.data_table.length > 0) {
            const cols = Object.keys(res.data_table[0]);
            agentHtml += `<div style="overflow-x:auto; margin: 10px 0;"><table><thead><tr>`;
            cols.forEach(c => agentHtml += `<th>${c}</th>`);
            agentHtml += `</tr></thead><tbody>`;
            res.data_table.slice(0, 8).forEach(r => {
                agentHtml += `<tr>`;
                cols.forEach(c => agentHtml += `<td>${r[c] || '-'}</td>`);
                agentHtml += `</tr>`;
            });
            agentHtml += `</tbody></table></div>`;
        }

        if (res.recommendations) {
            res.recommendations.forEach(r => {
                agentHtml += `<div class="rec-box">💡 ${r}</div>`;
            });
        }

        if (res.caveats) {
            res.caveats.forEach(c => {
                agentHtml += `<div class="cav-box">⚠️ ${c}</div>`;
            });
        }

        if (res.suggested_followups) {
            agentHtml += `<div class="followups">`;
            res.suggested_followups.forEach(fu => {
                agentHtml += `<button class="followup-btn" onclick="askQuestion('${fu}')">➡️ ${fu}</button>`;
            });
            agentHtml += `</div>`;
        }

        agentHtml += `</div>`;
        msgList.innerHTML += agentHtml;
        msgList.scrollTop = msgList.scrollHeight;

    } catch(e) {
        msgList.innerHTML += `<div class="msg-agent"><p style="color:var(--danger)">Error querying agent.</p></div>`;
    }
}

function copySlackText() {
    navigator.clipboard.writeText(currentSlackText);
    alert('Copied executive briefing to clipboard for Slack / Email!');
}

function downloadMarkdown() {
    const blob = new Blob([currentMarkdownReport], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'Skylark_Drones_Leadership_Update.md';
    a.click();
}

let funnelChart = null, sectorChart = null, slaChart = null, riskChart = null;

function renderCharts() {
    if (funnelChart) return;

    const ctxF = document.getElementById('chart-funnel').getContext('2d');
    funnelChart = new Chart(ctxF, {
        type: 'bar',
        data: {
            labels: ['Closed Won', 'In Negotiation', 'Proposal Sent', 'Under Review', 'Discovery', 'Closed Lost'],
            datasets: [{
                label: 'Valuation (INR Lakhs)',
                data: [398, 185, 102, 154, 140, 57.5],
                backgroundColor: ['#10B981', '#3B82F6', '#6366F1', '#F59E0B', '#94A3B8', '#EF4444']
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });

    const ctxS = document.getElementById('chart-sector').getContext('2d');
    sectorChart = new Chart(ctxS, {
        type: 'bar',
        data: {
            labels: ['Energy & Utilities', 'Infrastructure', 'Mining & Metals', 'Smart Cities', 'Agriculture', 'Defence'],
            datasets: [
                { label: 'Closed Won (₹ Lakhs)', data: [177.5, 85, 88, 0, 0, 0], backgroundColor: '#10B981' },
                { label: 'Open Pipeline (₹ Lakhs)', data: [90, 139, 110, 140, 39, 78], backgroundColor: '#38BDF8' }
            ]
        },
        options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true } } }
    });

    const ctxA = document.getElementById('chart-sla').getContext('2d');
    slaChart = new Chart(ctxA, {
        type: 'doughnut',
        data: {
            labels: ['Completed (On-Time)', 'In Progress', 'Delayed'],
            datasets: [{
                data: [6, 3, 2],
                backgroundColor: ['#10B981', '#38BDF8', '#EF4444']
            }]
        },
        options: { responsive: true }
    });

    const ctxR = document.getElementById('chart-risk').getContext('2d');
    riskChart = new Chart(ctxR, {
        type: 'bar',
        data: {
            labels: ['Tata Power', 'Mahindra Lifespaces'],
            datasets: [{
                label: 'Revenue at Risk (₹ Lakhs)',
                data: [65.0, 18.5],
                backgroundColor: '#EF4444'
            }]
        },
        options: { indexAxis: 'y', responsive: true }
    });
}

// Initial Load
loadKPIs();
loadLeadershipBriefing();
loadHygiene();
</script>

</body>
</html>
"""

class BIRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
            return

        if path == "/api/kpis":
            kpis = cross_engine.get_summary_kpis()
            self._send_json(kpis)
            return

        if path == "/api/leadership":
            gen = LeadershipUpdateGenerator(clean_deals, clean_wos)
            brief = gen.generate_update("Q2 2024")
            if "top_wins_table" in brief and hasattr(brief["top_wins_table"], "to_records"):
                brief["top_wins_table"] = brief["top_wins_table"].to_records()
            self._send_json(brief)
            return

        if path == "/api/hygiene":
            hygiene = DataResilienceEngine.audit_data_hygiene(clean_deals, clean_wos)
            self._send_json(hygiene)
            return

        if path == "/api/boards":
            self._send_json({
                "deals": clean_deals.to_records(),
                "work_orders": clean_wos.to_records()
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/query":
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len).decode('utf-8')
            req_data = json.loads(body) if body else {}
            query = req_data.get("query", "")
            
            res = bi_agent.process_query(query)
            if "data_table" in res and hasattr(res["data_table"], "to_records"):
                res["data_table"] = res["data_table"].to_records()
            
            self._send_json(res)
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data: Any):
        def default_serializer(o):
            if hasattr(o, "to_records"):
                return o.to_records()
            return str(o)

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=default_serializer).encode("utf-8"))

class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    server_address = ('', PORT)
    with ThreadingServer(server_address, BIRequestHandler) as httpd:
        print(f"Skylark Drones BI Agent Server running at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()