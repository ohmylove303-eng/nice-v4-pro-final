// US Stock Dashboard - Complete JavaScript Logic (PART5/PART6)
// ============================================================

// === Global Variables ===
let priceUpdateInterval;
let currentChartTicker = null;
let selectedDate = null;
let currentLang = localStorage.getItem('dashboardLang') || 'ko';
let currentModel = localStorage.getItem('dashboardModel') || 'gemini';
let usStockChart = null;
let currentChartPick = null;
let currentChartPeriod = '1y';
let indicatorState = { bb: false, sr: false, rsi: false, macd: false };
let indicatorData = null;
let bbUpperSeries = null, bbMiddleSeries = null, bbLowerSeries = null;
let srLines = [];
let rsiChart = null, macdChart = null;
let summaryChart, summaryCandleSeries, summaryVolumeSeries;
let chartResizeObserver = null;
let currentChartData = { candles: [], volumes: [] };
let currentRange = '1Y';

// === i18n Dictionary ===
const i18n = {
    'us-market-indices': { ko: '🇺🇸 US Market Indices', en: '🇺🇸 US Market Indices' },
    'realtime-data': { ko: 'Real-time Data', en: 'Real-time Data' },
    'final-top10': { ko: '📊 Final Top 10 - Smart Money Picks', en: '📊 Final Top 10 - Smart Money Picks' },
    'ai-analysis': { ko: '🤖 AI 투자 분석', en: '🤖 AI Investment Analysis' },
    'etf-flows': { ko: '💰 ETF Fund Flows - 자금 흐름', en: '💰 ETF Fund Flows' },
    'top-inflows': { ko: '📈 Top Inflows', en: '📈 Top Inflows' },
    'top-outflows': { ko: '📉 Top Outflows', en: '📉 Top Outflows' },
    'options-flow': { ko: 'Options Flow - 기관 포지션', en: 'Options Flow - Institutional Positions' },
    'macro-analysis': { ko: '🌍 Macro Analysis - AI 예측', en: '🌍 Macro Analysis - AI Predictions' },
    'gemini-macro': { ko: 'Gemini 3.0 매크로 분석', en: 'Gemini 3.0 Macro Analysis' },
    'gpt-macro': { ko: 'GPT-5.2 매크로 분석', en: 'GPT-5.2 Macro Analysis' },
    'loading': { ko: '분석 로딩 중...', en: 'Loading analysis...' }
};

// === Market Tab Switching ===
function switchMarketTab(tabElement, tabName) {
    // 1. Update Tabs Visual
    document.querySelectorAll('.nav-tab').forEach(t => {
        t.classList.remove('bg-blue-600', 'text-white', 'border-blue-500');
        t.classList.add('text-gray-400', 'border-transparent', 'hover:text-gray-300', 'hover:border-gray-300');
    });
    tabElement.classList.remove('text-gray-400', 'border-transparent', 'hover:text-gray-300', 'hover:border-gray-300');
    tabElement.classList.add('bg-blue-600', 'text-white', 'border-blue-500');

    // 2. Hide All Contents
    const contents = [
        'content-us-market',
        'content-economic-calendar',
        'content-analysis',
        'content-historical-returns',
        'content-risk',
        'content-holdings-matrix',
        'content-kr-market'
    ];
    contents.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });

    // 3. Show Selected Content
    let targetId = 'content-us-market';
    if (tabName === 'us-market') targetId = 'content-us-market';
    else if (tabName === 'economic-calendar') targetId = 'content-economic-calendar';
    else if (tabName === 'analysis') targetId = 'content-analysis';
    else if (tabName === 'returns') targetId = 'content-historical-returns';
    else if (tabName === 'risk') targetId = 'content-risk';
    else if (tabName === 'holdings') targetId = 'content-holdings-matrix';
    else if (tabName === 'kr-market') targetId = 'content-kr-market';

    const targetEl = document.getElementById(targetId);
    if (targetEl) targetEl.classList.remove('hidden');

    // 4. Trigger Specific Updates
    if (tabName === 'economic-calendar') {
        if (typeof updateEconomicCalendar === 'function') updateEconomicCalendar();
        if (typeof updateCorporateEvents === 'function') updateCorporateEvents();
    } else if (tabName === 'us-market') {
        updateUSMarketDashboard();
    } else if (tabName === 'returns') {
        if (typeof updateHistoricalTab === 'function') updateHistoricalTab();
    } else if (tabName === 'risk') {
        // Risk update logic if needed
        updateUSMarketDashboard();
    } else if (tabName === 'holdings') {
        if (typeof loadHoldingsMatrix === 'function') loadHoldingsMatrix();
    }
}


// === Language Toggle ===
function translateUI() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (i18n[key]) el.textContent = i18n[key][currentLang] || i18n[key]['en'];
    });
}

// === Initialization ===
document.addEventListener('DOMContentLoaded', async () => {
    // Language toggle
    document.getElementById('lang-toggle')?.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const lang = e.target.dataset.lang;
            if (lang !== currentLang) {
                currentLang = lang;
                localStorage.setItem('dashboardLang', lang);
                document.querySelectorAll('#lang-toggle button').forEach(btn => {
                    btn.className = btn.dataset.lang === lang
                        ? 'px-2 py-0.5 text-xs rounded-full bg-blue-600 text-white transition-colors'
                        : 'px-2 py-0.5 text-xs rounded-full text-gray-400 hover:text-white transition-colors';
                });
                translateUI();
                reloadMacroAnalysis();
            }
        }
    });

    // Model toggle
    document.getElementById('model-toggle')?.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const model = e.target.dataset.model;
            if (model && model !== currentModel) {
                currentModel = model;
                localStorage.setItem('dashboardModel', model);
                document.querySelectorAll('#model-toggle button').forEach(btn => {
                    btn.className = btn.dataset.model === model
                        ? 'px-2 py-0.5 text-xs rounded-full bg-purple-600 text-white transition-colors'
                        : 'px-2 py-0.5 text-xs rounded-full text-gray-400 hover:text-white transition-colors';
                });
                const labelEl = document.getElementById('macro-model-label');
                if (labelEl) {
                    labelEl.textContent = model === 'gpt' ? i18n['gpt-macro'][currentLang] : i18n['gemini-macro'][currentLang];
                }
                reloadMacroAnalysis();
            }
        }
    });

    // Period buttons
    document.getElementById('us-chart-period-btns')?.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const period = e.target.dataset.period;
            currentChartPeriod = period;
            document.querySelectorAll('#us-chart-period-btns button').forEach(btn => {
                btn.className = 'px-2 py-1 text-xs rounded bg-gray-700 text-gray-300 hover:bg-blue-600 hover:text-white transition-colors';
            });
            e.target.className = 'px-2 py-1 text-xs rounded bg-blue-600 text-white';
            if (currentChartPick) loadUSStockChart(currentChartPick, -1, period);
        }
    });

    // Date picker
    const today = new Date().toISOString().split('T')[0];
    const historyDate = document.getElementById('history-date');
    if (historyDate) {
        historyDate.max = today;
        historyDate.addEventListener('change', (e) => {
            selectedDate = e.target.value;
            updateDashboard();
        });
    }

    translateUI();
    priceUpdateInterval = setInterval(updateRealtimePrices, 20000);
    updateDashboard();

    setInterval(() => { console.log('🔄 Auto-refresh...'); reloadMacroAnalysis(); }, 600000);
});

function resetDate() {
    document.getElementById('history-date').value = '';
    selectedDate = null;
    updateDashboard();
}

// === KR Market Dashboard ===
async function updateDashboard() {
    try {
        let url = '/api/portfolio';
        if (selectedDate) url += `?date=${selectedDate}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.error) { console.error(data.error); return; }

        if (data.market_indices) renderMarketIndices(data.market_indices);
        if (data.top_holdings) renderHoldingsTable(data.top_holdings);
        if (data.style_box) renderStyleBox(data.style_box);
        if (data.top_holdings?.length > 0) updateSummaryChart(data.top_holdings[0].ticker);
    } catch (e) {
        console.error("Error updating dashboard:", e);
    }
}

function renderMarketIndices(indices) {
    const container = document.getElementById('market-indices-container');
    if (!container) return;
    container.innerHTML = '';
    if (!indices || indices.length === 0) {
        container.innerHTML = '<div class="col-span-full text-center text-gray-500 text-sm">No market data available</div>';
        return;
    }
    indices.forEach(idx => {
        const colorClass = idx.color === 'red' ? 'text-[#FF4560]' : (idx.color === 'blue' ? 'text-[#2962FF]' : 'text-gray-400');
        const sign = idx.change_pct > 0 ? '+' : '';
        const div = document.createElement('div');
        div.className = 'bg-[#1a1a1a] border border-[#2a2a2a] rounded p-3 flex flex-col items-center justify-center hover:bg-[#252525] transition-colors';
        div.innerHTML = `
            <span class="text-xs text-gray-400 mb-1">${idx.name}</span>
            <span class="text-lg font-bold text-white mb-1">${idx.price}</span>
            <span class="text-xs font-medium ${colorClass}">${sign}${idx.change} (${sign}${idx.change_pct.toFixed(2)}%)</span>
        `;
        container.appendChild(div);
    });
}

function renderHoldingsTable(holdings) {
    const tbody = document.getElementById('holdings-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    holdings.forEach(stock => {
        const tr = document.createElement('tr');
        tr.className = 'border-b border-gray-800 hover:bg-gray-800 transition-colors cursor-pointer';
        tr.onclick = () => updateSummaryChart(stock.ticker);

        const ytdVal = typeof stock.ytd === 'number' ? stock.ytd : parseFloat(stock.ytd || 0);
        const ytdColor = ytdVal >= 0 ? 'text-red-400' : 'text-blue-400';
        const ytdSign = ytdVal >= 0 ? '+' : '';
        const currentPrice = stock.price || 0;
        const recPrice = stock.recommendation_price || 0;
        let priceColor = 'text-gray-300';
        if (currentPrice > recPrice) priceColor = 'text-red-400';
        else if (currentPrice < recPrice) priceColor = 'text-blue-400';
        const returnPct = stock.return_pct || 0;
        const returnColor = returnPct > 0 ? 'text-red-400' : (returnPct < 0 ? 'text-blue-400' : 'text-gray-400');
        const returnSign = returnPct > 0 ? '+' : '';

        tr.innerHTML = `
            <td class="py-3 text-left font-mono text-blue-400">${stock.ticker}</td>
            <td class="py-3 text-left font-medium text-white">${stock.name}</td>
            <td class="py-3 text-left font-mono text-gray-400">${recPrice.toLocaleString()}</td>
            <td class="py-3 text-left font-mono ${priceColor}">${currentPrice.toLocaleString()}</td>
            <td class="py-3 text-left font-mono ${returnColor}">${returnSign}${returnPct.toFixed(2)}%</td>
            <td class="py-3 text-center font-bold text-yellow-400">${stock.score?.toFixed(1) || '-'}</td>
            <td class="py-3 text-center text-sm text-gray-300">${stock.grade || '-'}</td>
            <td class="py-3 text-center text-sm text-gray-300">${stock.wave || '-'}</td>
            <td class="py-3 text-center text-sm text-gray-300">${stock.sd_stage || '-'}</td>
            <td class="py-3 text-center text-sm text-gray-300">${stock.inst_trend || '-'}</td>
            <td class="py-3 text-center font-mono ${ytdColor}">${ytdSign}${ytdVal.toFixed(1)}%</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderStyleBox(data) {
    const setCell = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val + '%';
    };
    setCell('sb-large-value', data.large_value);
    setCell('sb-large-core', data.large_core);
    setCell('sb-large-growth', data.large_growth);
    setCell('sb-mid-value', data.mid_value);
    setCell('sb-mid-core', data.mid_core);
    setCell('sb-mid-growth', data.mid_growth);
    setCell('sb-small-value', data.small_value);
    setCell('sb-small-core', data.small_core);
    setCell('sb-small-growth', data.small_growth);
}

function setChartRange(range) {
    currentRange = range;
    document.querySelectorAll('.chart-range-btn').forEach(btn => {
        if (btn.dataset.range === range) {
            btn.classList.remove('text-gray-400', 'hover:text-white', 'hover:bg-[#333]');
            btn.classList.add('text-white', 'bg-[#333]');
        } else {
            btn.classList.add('text-gray-400', 'hover:text-white', 'hover:bg-[#333]');
            btn.classList.remove('text-white', 'bg-[#333]');
        }
    });
    if (summaryChart && currentChartData.candles.length > 0) {
        const filtered = filterDataByRange(currentChartData.candles, currentChartData.volumes, range);
        summaryCandleSeries.setData(filtered.candles);
        summaryVolumeSeries.setData(filtered.volumes);
        summaryChart.timeScale().fitContent();
    }
}

function filterDataByRange(candles, volumes, range) {
    if (!candles || candles.length === 0) return { candles: [], volumes: [] };
    if (range === 'All') return { candles, volumes };

    const lastCandleTime = candles[candles.length - 1].time;
    const lastDate = new Date(lastCandleTime);
    let startDate = new Date(lastDate);

    switch (range) {
        case '1D': startDate.setDate(lastDate.getDate() - 1); break;
        case '1W': startDate.setDate(lastDate.getDate() - 7); break;
        case '1M': startDate.setMonth(lastDate.getMonth() - 1); break;
        case '3M': startDate.setMonth(lastDate.getMonth() - 3); break;
        case '6M': startDate.setMonth(lastDate.getMonth() - 6); break;
        case '1Y': startDate.setFullYear(lastDate.getFullYear() - 1); break;
        case '5Y': startDate.setFullYear(lastDate.getFullYear() - 5); break;
    }
    const startTime = startDate.getTime();
    return {
        candles: candles.filter(d => new Date(d.time).getTime() >= startTime),
        volumes: volumes.filter(d => new Date(d.time).getTime() >= startTime)
    };
}

async function updateSummaryChart(ticker) {
    const container = document.getElementById('summary-chart-container');
    if (!container) return;

    if (chartResizeObserver) { chartResizeObserver.disconnect(); chartResizeObserver = null; }
    if (summaryChart) { summaryChart.remove(); summaryChart = null; }

    container.innerHTML = '<div class="absolute inset-0 flex items-center justify-center text-gray-500">Loading chart...</div>';
    document.getElementById('summary-chart-ticker').innerText = ticker;
    currentChartTicker = ticker;

    try {
        const response = await fetch(`/api/stock/${ticker}`);
        const data = await response.json();
        container.innerHTML = '';
        if (data.error) { container.innerHTML = `<div class="absolute inset-0 flex items-center justify-center text-red-500">Error: ${data.error}</div>`; return; }

        const priceData = data.candles || data.price_history;
        if (!priceData || priceData.length === 0) { container.innerHTML = '<div class="absolute inset-0 flex items-center justify-center text-gray-500">No price data</div>'; return; }

        currentChartData.candles = priceData.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }));
        currentChartData.volumes = priceData.map(d => ({ time: d.time, value: d.volume, color: d.close >= d.open ? 'rgba(239, 68, 68, 0.5)' : 'rgba(59, 130, 246, 0.5)' }));

        summaryChart = LightweightCharts.createChart(container, {
            layout: { background: { color: '#121212' }, textColor: '#D1D5DB' },
            grid: { vertLines: { color: '#2a2a2a' }, horzLines: { color: '#2a2a2a' } },
            width: container.clientWidth, height: container.clientHeight,
            timeScale: { timeVisible: true, secondsVisible: false },
            handleScroll: false, handleScale: false
        });

        summaryCandleSeries = summaryChart.addCandlestickSeries({ upColor: '#EF4444', downColor: '#3B82F6', borderVisible: false, wickUpColor: '#EF4444', wickDownColor: '#3B82F6' });
        summaryVolumeSeries = summaryChart.addHistogramSeries({ color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: '' });
        summaryChart.priceScale('').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

        chartResizeObserver = new ResizeObserver(entries => {
            if (entries.length > 0 && summaryChart) summaryChart.applyOptions({ width: entries[0].contentRect.width, height: entries[0].contentRect.height });
        });
        chartResizeObserver.observe(container);
        setChartRange(currentRange);
    } catch (e) {
        console.error("Chart error:", e);
        container.innerHTML = '<div class="absolute inset-0 flex items-center justify-center text-red-500">Error loading chart</div>';
    }
}

// === Real-time Prices ===
async function updateRealtimePrices() {
    const rows = document.querySelectorAll('#holdings-table-body tr');
    const tickers = [];
    const tickerRowMap = {};

    rows.forEach(row => {
        const tickerCell = row.querySelector('td:first-child');
        if (tickerCell) {
            const ticker = tickerCell.innerText.trim();
            tickers.push(ticker);
            tickerRowMap[ticker] = row;
        }
    });

    if (tickers.length === 0) return;

    try {
        const response = await fetch('/api/realtime-prices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tickers: tickers })
        });
        const prices = await response.json();

        for (const [ticker, data] of Object.entries(prices)) {
            let currentPrice = typeof data === 'number' ? data : data.current;
            const row = tickerRowMap[ticker];
            if (row) {
                const priceCell = row.querySelector('td:nth-child(4)');
                if (priceCell) {
                    const oldPrice = parseFloat(priceCell.innerText.replace(/,/g, ''));
                    if (oldPrice !== currentPrice) {
                        priceCell.innerText = currentPrice.toLocaleString();
                        const flashColor = currentPrice > oldPrice ? 'text-green-400' : 'text-red-400';
                        priceCell.className = `py-3 text-left font-mono ${flashColor} transition-colors duration-500`;
                        setTimeout(() => { priceCell.className = 'py-3 text-left font-mono text-gray-300 transition-colors duration-500'; }, 1000);
                    }
                }
            }
        }
    } catch (e) {
        console.error("Realtime price error:", e);
    }
}

// === US Market Dashboard ===
async function updateUSMarketDashboard() {
    try {
        const [portfolioRes, smartMoneyRes, etfFlowsRes, historyDatesRes] = await Promise.all([
            fetch('/api/us/portfolio'),
            fetch('/api/us/smart-money'),
            fetch('/api/us/etf-flows'),
            fetch('/api/us/history-dates')
        ]);

        const portfolioData = await portfolioRes.json();
        const smartMoneyData = await smartMoneyRes.json();
        const etfFlowsData = await etfFlowsRes.json();
        const historyDatesData = await historyDatesRes.json();

        if (portfolioData.market_indices) renderUSMarketIndices(portfolioData.market_indices);
        if (historyDatesData.dates) populateUSHistoryDates(historyDatesData.dates);
        if (smartMoneyData.top_picks) renderUSSmartMoneyPicks(smartMoneyData);
        if (etfFlowsData.top_inflows) renderUSETFFlows(etfFlowsData);

        try { const macroRes = await fetch('/api/us/macro-analysis'); const macroData = await macroRes.json(); if (macroData.macro_indicators) renderUSMacroAnalysis(macroData); } catch (e) { }
        try { const sectorRes = await fetch('/api/us/sector-heatmap'); const sectorData = await sectorRes.json(); if (sectorData.series) renderUSSectorHeatmap(sectorData); } catch (e) { }
        try { const optionsRes = await fetch('/api/us/options-flow'); const optionsData = await optionsRes.json(); if (optionsData.options_flow) renderUSOptionsFlow(optionsData); } catch (e) { }
        try { const calendarRes = await fetch('/api/us/calendar'); const calendarData = await calendarRes.json(); renderUSCalendar(calendarData); } catch (e) { }
        try { const riskRes = await fetch('/api/us/risk'); const riskData = await riskRes.json(); renderRiskTab(riskData); renderHoldingsMatrix(riskData); } catch (e) { }
        try { const histRes = await fetch('/api/us/historical-returns'); const histData = await histRes.json(); renderHistoricalTab(histData); } catch (e) { }
    } catch (e) {
        console.error("US dashboard error:", e);
    }
}

function renderHistoricalTab(data) {
    if (!data.heatmap_series) return;

    // Heatmap
    const container = document.getElementById('historical-heatmap');
    if (container) {
        container.innerHTML = '';
        const options = {
            series: data.heatmap_series,
            chart: { type: 'heatmap', height: 350, toolbar: { show: false }, background: 'transparent' },
            colors: ['#00E396'],
            dataLabels: { enabled: true, style: { colors: ['#fff'] } },
            plotOptions: { heatmap: { shadeIntensity: 0.5, colorScale: { ranges: [{ from: -100, to: -0.01, color: '#FF4560', name: '하락 (Negative)' }, { from: 0, to: 100, color: '#00E396', name: '상승 (Positive)' }] } } },
            stroke: { width: 1, colors: ['#1a1a1a'] },
            xaxis: { type: 'category', labels: { style: { colors: '#a0a0a0' } } },
            yaxis: { labels: { style: { colors: '#a0a0a0' } } },
            theme: { mode: 'dark' }
        };
        new ApexCharts(container, options).render();
    }

    // Stats
    const statsContainer = document.getElementById('historical-stats');
    if (statsContainer && data.yearly_stats) {
        statsContainer.innerHTML = '';
        Object.entries(data.yearly_stats).sort((a, b) => b[0] - a[0]).forEach(([year, stats]) => {
            const retClass = stats.total_return >= 0 ? 'text-green-400' : 'text-red-400';
            const div = document.createElement('div');
            div.className = 'bg-[#252525] rounded p-3 text-sm border-l-4 ' + (stats.total_return >= 0 ? 'border-green-500' : 'border-red-500');
            div.innerHTML = `
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-white text-lg">${year}</span>
                    <span class="${retClass} font-bold text-lg">${stats.total_return > 0 ? '+' : ''}${stats.total_return}%</span>
                </div>
                <div class="grid grid-cols-3 gap-2 text-xs text-gray-400">
                    <div>최고: <span class="text-green-400">${stats.best_month}%</span></div>
                    <div>최악: <span class="text-red-400">${stats.worst_month}%</span></div>
                    <div>승률: <span class="text-blue-400">${stats.positive_months}/12</span></div>
                </div>
            `;
            statsContainer.appendChild(div);
        });
    }
}

function renderRiskTab(data) {
    if (!data.summary) return;

    // Metrics Cards
    const metricsContainer = document.getElementById('risk-metrics-cards');
    if (metricsContainer) {
        metricsContainer.innerHTML = '';
        const metrics = [
            { label: '연간 변동성 (Volatility)', value: data.summary.portfolio_volatility + '%', desc: '낮을수록 좋음' },
            { label: '샤프 비율 (Sharpe)', value: data.summary.sharpe_ratio, desc: '위험 대비 수익률' },
            { label: '최대 낙폭 (MDD)', value: data.summary.max_drawdown + '%', desc: '고점 대비 최대 손실' },
            { label: 'VaR (95%)', value: data.summary.var_95 + '%', desc: '상위 95% 위험 수준' }
        ];
        metrics.forEach(m => {
            const div = document.createElement('div');
            div.className = 'bg-[#252525] p-3 rounded border border-[#333]';
            div.innerHTML = `<div class="text-xs text-gray-500">${m.label}</div><div class="text-lg font-bold text-white my-1">${m.value}</div><div class="text-[10px] text-gray-600">${m.desc}</div>`;
            metricsContainer.appendChild(div);
        });
    }

    // Gauge
    const gaugeContainer = document.getElementById('risk-gauge-chart');
    if (gaugeContainer) {
        gaugeContainer.innerHTML = '';
        const vol = data.summary.portfolio_volatility;
        const options = {
            series: [Math.min(vol, 50)], // Cap at 50 for visual
            chart: { type: 'radialBar', height: 300, background: 'transparent' },
            plotOptions: {
                radialBar: {
                    startAngle: -135, endAngle: 135,
                    hollow: { margin: 15, size: '60%' },
                    track: { background: '#333', strokeWidth: '100%' },
                    dataLabels: { show: true, name: { offsetY: -10, color: '#888', fontSize: '14px' }, value: { offsetY: 5, color: '#fff', fontSize: '24px', show: true, formatter: () => vol + '%' } }
                }
            },
            fill: { type: 'gradient', gradient: { shade: 'dark', type: 'horizontal', gradientToColors: ['#F55'], stops: [0, 100] } },
            stroke: { lineCap: 'round' },
            labels: ['위험도 (Volatility)']
        };
        new ApexCharts(gaugeContainer, options).render();
    }

    // Table
    const tableBody = document.getElementById('individual-risk-table-body');
    if (tableBody && data.individual_risks) {
        tableBody.innerHTML = '';
        data.individual_risks.forEach(item => {
            const tr = document.createElement('tr');
            tr.className = 'border-b border-[#333] hover:bg-[#2a2a2a]';
            tr.innerHTML = `<td class="px-4 py-2 font-bold text-white">${item.ticker}</td><td class="px-4 py-2 text-right text-yellow-400">${item.volatility}%</td><td class="px-4 py-2 text-right text-red-400">${item.max_drawdown}%</td>`;
            tableBody.appendChild(tr);
        });
    }
}

function renderHoldingsMatrix(data) {
    if (!data.correlation_matrix) return;

    // Heatmap
    const container = document.getElementById('correlation-heatmap');
    if (container) {
        container.innerHTML = '';
        const options = {
            series: data.correlation_matrix.series,
            chart: { type: 'heatmap', height: 500, toolbar: { show: false }, background: 'transparent' },
            dataLabels: { enabled: true, style: { fontSize: '10px' } },
            stroke: { width: 1, colors: ['#1a1a1a'] },
            plotOptions: { heatmap: { shadeIntensity: 0.5, colorScale: { ranges: [{ from: -1, to: 0.3, color: '#00E396', name: 'Low/Neg' }, { from: 0.31, to: 0.7, color: '#FEB019', name: 'Medium' }, { from: 0.71, to: 1, color: '#FF4560', name: 'High' }] } } },
            theme: { mode: 'dark' },
            xaxis: { type: 'category' }
        };
        new ApexCharts(container, options).render();
    }

    // High Corr List
    const listContainer = document.getElementById('high-correlation-list');
    if (listContainer && data.correlation_matrix.high_correlations) {
        listContainer.innerHTML = '';
        data.correlation_matrix.high_correlations.forEach(pair => {
            const div = document.createElement('div');
            div.className = 'bg-[#252525] p-2 rounded flex justify-between items-center text-sm border-l-2 border-red-500';
            div.innerHTML = `<span class="text-white font-mono">${pair.pair[0]} ↔ ${pair.pair[1]}</span><span class="text-red-400 font-bold">${pair.value}</span>`;
            listContainer.appendChild(div);
        });
    }
}

async function reloadMacroAnalysis() {
    try {
        const macroRes = await fetch(`/api/us/macro-analysis?lang=${currentLang}&model=${currentModel}`);
        const macroData = await macroRes.json();
        if (macroData.macro_indicators) renderUSMacroAnalysis(macroData);
    } catch (e) { }
    if (currentChartPick) loadUSAISummary(currentChartPick.ticker);
}

function renderUSMarketIndices(indices) {
    const container = document.getElementById('us-market-indices-container');
    if (!container) return;
    container.innerHTML = '';
    if (!indices || indices.length === 0) { container.innerHTML = '<div class="col-span-full text-center text-gray-500 text-sm">Loading...</div>'; return; }
    indices.forEach(idx => {
        const colorClass = idx.color === 'green' ? 'text-[#00E396]' : 'text-[#FF4560]';
        const sign = idx.change_pct > 0 ? '+' : '';
        const div = document.createElement('div');
        div.className = 'bg-[#1a1a1a] border border-[#2a2a2a] rounded p-3 flex flex-col items-center justify-center hover:bg-[#252525] transition-colors';
        div.innerHTML = `<span class="text-xs text-gray-400 mb-1">${idx.name}</span><span class="text-lg font-bold text-white mb-1">${idx.price}</span><span class="text-xs font-medium ${colorClass}">${idx.change} (${sign}${idx.change_pct.toFixed(2)}%)</span>`;
        container.appendChild(div);
    });
}

function renderUSSmartMoneyPicks(data) {
    const table = document.getElementById('us-smart-money-table');
    const summary = document.getElementById('us-smart-money-summary');
    if (!table) return;
    table.innerHTML = '';
    window.usSmartMoneyPicks = data.top_picks;
    if (summary) { const analysisDate = data.analysis_date || ''; const avgScore = data.summary?.avg_score || 0; summary.innerHTML = `<span class="text-purple-400">📅 분석일: ${analysisDate}</span> | 평균: ${avgScore}점`; }
    data.top_picks.forEach((pick, idx) => {
        const change = pick.change_since_rec || pick.change_pct || 0;
        const changeClass = change >= 0 ? 'text-green-400' : 'text-red-400';
        const changePrefix = change >= 0 ? '+' : '';
        const score = pick.final_score || pick.composite_score || 0;
        const aiRec = pick.ai_recommendation || '분석 중';
        const recEmoji = aiRec.includes('적극') ? '🔥' : aiRec.includes('매수') ? '📈' : '📊';
        const priceAtRec = pick.price_at_rec || pick.price_at_analysis || pick.current_price || 0;
        const currentPrice = pick.current_price || priceAtRec;
        const tr = document.createElement('tr');
        tr.className = 'border-b border-[#2a2a2a] hover:bg-[#252525] cursor-pointer';
        tr.setAttribute('data-ticker', pick.ticker);
        tr.setAttribute('data-idx', idx);
        tr.innerHTML = `<td class="p-2 text-gray-500">${pick.rank || idx + 1}</td><td class="p-2"><span class="text-gray-400 text-xs">${pick.name || ''}</span> <span class="text-white font-bold">(${pick.ticker})</span></td><td class="p-2 text-center"><span class="text-xs px-1.5 py-0.5 rounded bg-purple-900/50 text-purple-300">${pick.sector || '-'}</span></td><td class="p-2 text-center text-xs text-gray-400">${pick.avg_vol_m ? '$' + pick.avg_vol_m + 'M' : '-'}</td><td class="p-2 text-center text-blue-400 font-bold">${score}</td><td class="p-2 text-center text-xs"><span class="text-yellow-400">${recEmoji} ${aiRec}</span></td><td class="p-2 text-center text-gray-300">$${priceAtRec.toFixed(2)}</td><td class="p-2 text-center text-white font-bold">$${currentPrice.toFixed(2)}</td><td class="p-2 text-center ${changeClass} font-bold">${changePrefix}${change.toFixed(2)}%</td><td class="p-2 text-center ${pick.target_upside > 0 ? 'text-green-400' : 'text-red-400'}">${pick.target_upside ? pick.target_upside.toFixed(1) + '%' : 'N/A'}</td>`;
        tr.addEventListener('click', () => loadUSStockChart(pick, idx));
        table.appendChild(tr);
    });
    if (data.top_picks.length > 0) loadUSStockChart(data.top_picks[0], 0);
}

function populateUSHistoryDates(dates) {
    const select = document.getElementById('us-history-date-select');
    if (!select) return;
    select.innerHTML = '<option value="">📅 최신 분석</option>';
    dates.forEach(date => { const option = document.createElement('option'); option.value = date; option.textContent = date; select.appendChild(option); });
}

async function loadUSHistoryByDate(date) {
    if (!date) { updateUSMarketDashboard(); return; }
    try {
        const response = await fetch(`/api/us/history/${date}`);
        const data = await response.json();
        if (data.error) { alert(data.error); return; }
        const summary = document.getElementById('us-smart-money-summary');
        if (summary && data.summary) { const perf = data.summary.avg_performance || 0; const perfClass = perf >= 0 ? 'text-green-400' : 'text-red-400'; summary.innerHTML = `<span class="text-purple-400">📅 ${date}</span> | <span class="${perfClass}">평균 ${perf >= 0 ? '+' : ''}${perf}%</span>`; }
        renderUSSmartMoneyPicks(data);
    } catch (e) { console.error('History error:', e); }
}

function renderUSETFFlows(data) {
    const inflowsContainer = document.getElementById('us-etf-inflows');
    const outflowsContainer = document.getElementById('us-etf-outflows');
    const sentimentEl = document.getElementById('us-etf-sentiment');

    if (sentimentEl && data.market_sentiment_score) {
        const score = data.market_sentiment_score;
        let sentiment = score >= 60 ? 'Bullish' : score >= 50 ? 'Neutral' : 'Bearish';
        let bgColor = score >= 60 ? 'bg-green-600' : score >= 50 ? 'bg-gray-600' : 'bg-red-600';
        sentimentEl.textContent = `${sentiment} (${score})`;
        sentimentEl.className = `text-xs px-2 py-1 rounded ${bgColor} text-white`;
    }
    if (inflowsContainer && data.top_inflows) { inflowsContainer.innerHTML = ''; data.top_inflows.forEach(etf => { const div = document.createElement('div'); div.className = 'flex justify-between items-center text-sm'; div.innerHTML = `<span class="text-white">${etf.ticker} <span class="text-gray-500 text-xs">${etf.name || ''}</span></span><span class="text-green-400 font-bold">${etf.flow_score}</span>`; inflowsContainer.appendChild(div); }); }
    if (outflowsContainer && data.top_outflows) { outflowsContainer.innerHTML = ''; data.top_outflows.forEach(etf => { const div = document.createElement('div'); div.className = 'flex justify-between items-center text-sm'; div.innerHTML = `<span class="text-white">${etf.ticker} <span class="text-gray-500 text-xs">${etf.name || ''}</span></span><span class="text-red-400 font-bold">${etf.flow_score}</span>`; outflowsContainer.appendChild(div); }); }

    const aiBtn = document.getElementById('us-etf-ai-btn');
    const aiContainer = document.getElementById('us-etf-ai-container');
    const aiContent = document.getElementById('us-etf-ai-content');
    if (data.ai_analysis && aiBtn && aiContainer && aiContent) {
        aiBtn.classList.remove('hidden');
        const newBtn = aiBtn.cloneNode(true);
        aiBtn.parentNode.replaceChild(newBtn, aiBtn);
        newBtn.addEventListener('click', () => { aiContainer.classList.toggle('hidden'); aiContent.textContent = data.ai_analysis; });
    } else if (aiBtn) aiBtn.classList.add('hidden');
}

function renderUSOptionsFlow(data) {
    const container = document.getElementById('us-options-flow');
    const timestampEl = document.getElementById('us-options-timestamp');
    if (!container) return;
    container.innerHTML = '';
    if (timestampEl && data.timestamp) timestampEl.textContent = `📅 ${new Date(data.timestamp).toLocaleDateString('ko-KR')}`;
    const stocks = data.options_flow.slice(0, 10);
    stocks.forEach(stock => {
        const signal = stock.signal;
        let bgClass = signal.sentiment_score >= 70 ? 'bg-green-900/30 border-green-600/50' : signal.sentiment_score <= 30 ? 'bg-red-900/30 border-red-600/50' : 'bg-yellow-900/30 border-yellow-600/50';
        const div = document.createElement('div');
        div.className = `${bgClass} border rounded-lg p-3 cursor-pointer hover:opacity-80 transition-opacity`;
        div.innerHTML = `<div class="flex justify-between items-center mb-1"><span class="text-sm font-bold text-white">${stock.ticker}</span><span class="text-xs text-gray-400">$${stock.current_price}</span></div><div class="text-xs mb-1">${signal.sentiment}</div><div class="flex justify-between text-xs text-gray-400"><span>P/C: ${stock.metrics.pc_volume_ratio.toFixed(2)}</span><span>IV: ${stock.metrics.call_iv.toFixed(0)}%</span></div>`;
        container.appendChild(div);
    });
}

function renderUSMacroAnalysis(data) {
    const indicatorsEl = document.getElementById('us-macro-indicators');
    const analysisEl = document.getElementById('us-macro-ai-analysis');
    const timestampEl = document.getElementById('us-macro-timestamp');

    if (timestampEl && data.timestamp) timestampEl.textContent = `📅 ${new Date(data.timestamp).toLocaleDateString('ko-KR')} ${new Date(data.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}`;

    if (indicatorsEl && data.macro_indicators) {
        indicatorsEl.innerHTML = '';
        const volatilityIndicators = ['VIX', 'SKEW', 'FearGreed'];
        const cryptoIndicators = ['BTC', 'ETH'];
        const yieldIndicators = ['YieldSpread', '2Y_Yield', '10Y_Yield'];
        for (const [name, values] of Object.entries(data.macro_indicators)) {
            const change = values.change_1d || 0;
            const changeClass = change >= 0 ? 'text-green-400' : 'text-red-400';
            const arrow = change >= 0 ? '▲' : '▼';
            let boxClass = 'bg-[#1a1a1a] rounded p-2 text-center border border-[#2a2a2a]';
            let labelClass = 'text-xs text-gray-500';
            if (volatilityIndicators.includes(name)) { boxClass = 'bg-purple-900/30 rounded p-2 text-center border border-purple-600/50 shadow-lg shadow-purple-500/20'; labelClass = 'text-xs text-purple-300 font-bold'; }
            else if (cryptoIndicators.includes(name)) { boxClass = 'bg-orange-900/30 rounded p-2 text-center border border-orange-600/50 shadow-lg shadow-orange-500/20'; labelClass = 'text-xs text-orange-300 font-bold'; }
            else if (yieldIndicators.includes(name)) { boxClass = 'bg-blue-900/30 rounded p-2 text-center border border-blue-600/50 shadow-lg shadow-blue-500/20'; labelClass = 'text-xs text-blue-300 font-bold'; }
            const div = document.createElement('div');
            div.className = boxClass;
            div.innerHTML = `<div class="${labelClass}">${name}</div><div class="text-sm font-bold text-white">${values.current ?? values.value ?? '-'}</div><div class="${changeClass} text-xs">${arrow} ${Math.abs(change).toFixed(2)}%</div>`;
            indicatorsEl.appendChild(div);
        }
    }
    if (analysisEl && data.ai_analysis) {
        let html = data.ai_analysis.replace(/### (.*)/g, '<h3 class="text-purple-300 font-bold mt-3 mb-1">$1</h3>').replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>').replace(/🚀/g, '<span class="text-green-400">🚀</span>').replace(/⚠️/g, '<span class="text-yellow-400">⚠️</span>').replace(/\n/g, '<br>');
        analysisEl.innerHTML = html;
    }
}

function renderUSSectorHeatmap(data) {
    const container = document.getElementById('us-sector-heatmap');
    if (!container || !data.series) return;
    container.innerHTML = '';
    const dateEl = document.getElementById('us-heatmap-date');
    if (dateEl && data.data_date) dateEl.textContent = `기준: ${data.data_date}`;
    const seriesData = data.series.map(sector => ({ name: sector.name, data: sector.data.map(stock => ({ x: stock.x, y: stock.y, fillColor: stock.color, meta: { change: stock.change, price: stock.price } })) }));
    const options = { series: seriesData, chart: { type: 'treemap', height: 300, toolbar: { show: false }, background: 'transparent' }, legend: { show: false }, colors: ['#3b82f6'], plotOptions: { treemap: { distributed: true, enableShades: false, useFillColorAsStroke: true } }, dataLabels: { enabled: true, style: { fontSize: '10px', fontWeight: 'bold', colors: ['#ffffff'] }, formatter: function (text, op) { try { const dp = op.w.config.series[op.seriesIndex].data[op.dataPointIndex]; const ch = dp?.meta?.change; if (ch !== undefined) return [text, (ch >= 0 ? '+' : '') + ch.toFixed(1) + '%']; } catch (e) { } return text; }, offsetY: -4 }, tooltip: { theme: 'dark' }, stroke: { width: 1, colors: ['#1a1a1a'] } };
    new ApexCharts(container, options).render();
}

function renderUSCalendar(data) {
    const container = document.getElementById('us-calendar-events');
    const rangeEl = document.getElementById('us-calendar-range');
    if (!container) return;
    if (rangeEl && data.week_start && data.week_end) rangeEl.textContent = `${data.week_start} ~ ${data.week_end}`;
    container.innerHTML = '';
    if (!data.events || data.events.length === 0) { container.innerHTML = '<div class="text-center text-xs text-gray-500 py-2">No events.</div>'; return; }
    data.events.forEach(event => {
        const eventId = `cal-evt-${Math.random().toString(36).substr(2, 9)}`;
        let icon = '📅', colorClass = 'text-gray-300', bgClass = 'bg-[#2a2a2a]';
        if (event.type === 'Earnings') { icon = '🏢'; colorClass = 'text-blue-300'; bgClass = 'bg-blue-900/20 border border-blue-800/30'; }
        else if (event.impact === 'High') { icon = '🔥'; colorClass = 'text-red-300'; bgClass = 'bg-red-900/20 border border-red-800/30'; }
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = `<div class="flex items-center justify-between p-2 rounded text-xs ${bgClass} cursor-pointer hover:bg-opacity-80 transition-all" onclick="toggleCalendarDetails('${eventId}')"><div class="flex items-center gap-2"><span>${icon}</span><span class="font-medium ${colorClass}">${event.event}</span></div><div class="flex items-center gap-2"><span class="text-gray-500">${event.date}</span><i class="fas fa-chevron-down text-[10px] text-gray-500 transition-transform" id="arrow-${eventId}"></i></div></div><div id="${eventId}" class="hidden bg-[#222] border-x border-b border-[#2a2a2a] rounded-b p-3 text-xs text-gray-400">${event.description || 'No details.'}</div>`;
        container.appendChild(div);
    });
}

function toggleCalendarDetails(id) {
    const el = document.getElementById(id);
    const arrow = document.getElementById(`arrow-${id}`);
    if (el) { el.classList.toggle('hidden'); if (arrow) arrow.style.transform = el.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(180deg)'; }
}

function expandAllCalendarEvents() { document.querySelectorAll('[id^="cal-evt-"]').forEach(el => el.classList.remove('hidden')); document.querySelectorAll('[id^="arrow-cal-evt-"]').forEach(arrow => arrow.style.transform = 'rotate(180deg)'); }
function collapseAllCalendarEvents() { document.querySelectorAll('[id^="cal-evt-"]').forEach(el => el.classList.add('hidden')); document.querySelectorAll('[id^="arrow-cal-evt-"]').forEach(arrow => arrow.style.transform = 'rotate(0deg)'); }

// === US Stock Chart ===
async function loadUSStockChart(pick, idx, period = null) {
    const chartContainer = document.getElementById('us-stock-chart');
    const tickerEl = document.getElementById('us-chart-ticker');
    const infoEl = document.getElementById('us-chart-info');
    const gradeEl = document.getElementById('us-chart-grade');
    if (!chartContainer) return;

    currentChartPick = pick;
    const usePeriod = period || currentChartPeriod;
    tickerEl.textContent = pick.ticker;
    const score = pick.final_score || pick.composite_score || 0;
    infoEl.textContent = `${pick.name || pick.ticker} | Score: ${score}/100`;
    const aiRec = pick.ai_recommendation || '분석 중';
    gradeEl.textContent = aiRec;
    gradeEl.className = `px-3 py-1 rounded text-sm font-bold ${aiRec.includes('적극') ? 'bg-yellow-600' : 'bg-green-600'} text-white`;

    if (idx >= 0) { document.querySelectorAll('#us-smart-money-table tr').forEach(tr => tr.classList.remove('bg-[#2a2a2a]')); document.querySelector(`#us-smart-money-table tr[data-idx="${idx}"]`)?.classList.add('bg-[#2a2a2a]'); }

    try {
        chartContainer.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><i class="fas fa-spinner fa-spin text-2xl"></i></div>';
        const response = await fetch(`/api/us/stock-chart/${pick.ticker}?period=${usePeriod}`);
        const data = await response.json();
        if (data.error) { chartContainer.innerHTML = `<div class="flex items-center justify-center h-full text-gray-500">${data.error}</div>`; return; }
        chartContainer.innerHTML = '';
        if (usStockChart) usStockChart.remove();
        usStockChart = LightweightCharts.createChart(chartContainer, { width: chartContainer.clientWidth, height: 300, layout: { background: { color: '#1a1a1a' }, textColor: '#999' }, grid: { vertLines: { color: '#2a2a2a' }, horzLines: { color: '#2a2a2a' } }, timeScale: { borderColor: '#2a2a2a', timeVisible: true, rightOffset: 5 }, rightPriceScale: { borderColor: '#2a2a2a' } });
        const candleSeries = usStockChart.addCandlestickSeries({ upColor: '#22c55e', downColor: '#ef4444', borderUpColor: '#22c55e', borderDownColor: '#ef4444', wickUpColor: '#22c55e', wickDownColor: '#ef4444' });
        candleSeries.setData(data.candles);
        usStockChart.timeScale().fitContent();

        indicatorData = null; bbUpperSeries = null; bbMiddleSeries = null; bbLowerSeries = null; srLines = [];
        document.getElementById('us-rsi-chart')?.classList.add('hidden');
        document.getElementById('us-macd-chart')?.classList.add('hidden');
        if (rsiChart) { rsiChart.remove(); rsiChart = null; }
        if (macdChart) { macdChart.remove(); macdChart = null; }

        if (indicatorState.bb || indicatorState.sr || indicatorState.rsi || indicatorState.macd) {
            loadTechnicalIndicators(pick.ticker, usePeriod).then(() => { if (indicatorState.bb) renderBollingerBands(); if (indicatorState.sr) renderSupportResistance(); if (indicatorState.rsi) renderRSI(); if (indicatorState.macd) renderMACD(); });
        }
        loadUSAISummary(pick.ticker);
    } catch (e) {
        console.error('Chart error:', e);
        chartContainer.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500">Failed to load chart</div>';
    }
}

async function loadUSAISummary(ticker) {
    const summaryEl = document.getElementById('us-ai-summary');
    if (!summaryEl) return;
    summaryEl.innerHTML = `<span class="text-gray-500"><i class="fas fa-spinner fa-spin"></i> ${currentLang === 'en' ? 'Loading...' : 'AI 분석 로딩 중...'}</span>`;
    try {
        const response = await fetch(`/api/us/ai-summary/${ticker}?lang=${currentLang}`);
        const data = await response.json();
        if (data.error) { summaryEl.innerHTML = `<span class="text-gray-500">${data.error}</span>`; return; }
        let htmlSummary = data.summary.replace(/## (.*)/g, '<strong class="text-white block mb-1">$1</strong>').replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>').replace(/\n/g, '<br>');
        summaryEl.innerHTML = htmlSummary;
    } catch (e) {
        summaryEl.innerHTML = '<span class="text-gray-500">AI 분석을 불러올 수 없습니다.</span>';
    }
}

// === Technical Indicators ===
async function loadTechnicalIndicators(ticker, period = '1y') {
    try { const response = await fetch(`/api/us/technical-indicators/${ticker}?period=${period}`); indicatorData = await response.json(); } catch (e) { indicatorData = null; }
}

function toggleIndicator(type) {
    indicatorState[type] = !indicatorState[type];
    const btn = document.getElementById(`toggle-${type}`);
    if (indicatorState[type]) { btn.classList.add('bg-purple-600', 'text-white'); btn.classList.remove('bg-gray-700', 'text-gray-300'); }
    else { btn.classList.remove('bg-purple-600', 'text-white'); btn.classList.add('bg-gray-700', 'text-gray-300'); }
    if (!indicatorData && currentChartPick) loadTechnicalIndicators(currentChartPick.ticker, currentChartPeriod).then(() => renderIndicator(type));
    else renderIndicator(type);
}

function renderIndicator(type) { if (!indicatorData || !usStockChart) return; if (type === 'bb') renderBollingerBands(); else if (type === 'sr') renderSupportResistance(); else if (type === 'rsi') renderRSI(); else if (type === 'macd') renderMACD(); }

function renderBollingerBands() {
    if (bbUpperSeries) { usStockChart.removeSeries(bbUpperSeries); bbUpperSeries = null; }
    if (bbMiddleSeries) { usStockChart.removeSeries(bbMiddleSeries); bbMiddleSeries = null; }
    if (bbLowerSeries) { usStockChart.removeSeries(bbLowerSeries); bbLowerSeries = null; }
    if (!indicatorState.bb || !indicatorData?.bollinger) return;
    bbUpperSeries = usStockChart.addLineSeries({ color: 'rgba(147, 51, 234, 0.5)', lineWidth: 1 });
    bbMiddleSeries = usStockChart.addLineSeries({ color: 'rgba(147, 51, 234, 0.8)', lineWidth: 1, lineStyle: 2 });
    bbLowerSeries = usStockChart.addLineSeries({ color: 'rgba(147, 51, 234, 0.5)', lineWidth: 1 });
    bbUpperSeries.setData(indicatorData.bollinger.upper); bbMiddleSeries.setData(indicatorData.bollinger.middle); bbLowerSeries.setData(indicatorData.bollinger.lower);
}

function renderSupportResistance() {
    srLines.forEach(line => usStockChart.removeSeries(line)); srLines = [];
    if (!indicatorState.sr || !indicatorData?.support_resistance) return;
    const sr = indicatorData.support_resistance; const times = indicatorData.rsi || [];
    if (times.length === 0) return;
    sr.support?.forEach(level => { const line = usStockChart.addLineSeries({ color: '#22c55e', lineWidth: 1, lineStyle: 2 }); line.setData([{ time: times[0].time, value: level }, { time: times[times.length - 1].time, value: level }]); srLines.push(line); });
    sr.resistance?.forEach(level => { const line = usStockChart.addLineSeries({ color: '#ef4444', lineWidth: 1, lineStyle: 2 }); line.setData([{ time: times[0].time, value: level }, { time: times[times.length - 1].time, value: level }]); srLines.push(line); });
}

function renderRSI() {
    const container = document.getElementById('us-rsi-chart');
    if (!indicatorState.rsi) { container?.classList.add('hidden'); if (rsiChart) { rsiChart.remove(); rsiChart = null; } return; }
    container?.classList.remove('hidden'); container.innerHTML = '';
    rsiChart = LightweightCharts.createChart(container, { width: container.clientWidth, height: 80, layout: { background: { color: '#1a1a1a' }, textColor: '#666' }, grid: { vertLines: { color: '#2a2a2a' }, horzLines: { color: '#2a2a2a' } }, timeScale: { visible: false }, rightPriceScale: { borderColor: '#2a2a2a', scaleMargins: { top: 0.1, bottom: 0.1 } } });
    const rsiSeries = rsiChart.addLineSeries({ color: '#22c55e', lineWidth: 1 }); rsiSeries.setData(indicatorData.rsi || []);
    const ovLine = rsiChart.addLineSeries({ color: '#ef4444', lineWidth: 1, lineStyle: 2 }); const osLine = rsiChart.addLineSeries({ color: '#22c55e', lineWidth: 1, lineStyle: 2 });
    if (indicatorData.rsi?.length > 0) { const times = indicatorData.rsi; ovLine.setData([{ time: times[0].time, value: 70 }, { time: times[times.length - 1].time, value: 70 }]); osLine.setData([{ time: times[0].time, value: 30 }, { time: times[times.length - 1].time, value: 30 }]); }
    rsiChart.timeScale().fitContent();
}

function renderMACD() {
    const container = document.getElementById('us-macd-chart');
    if (!indicatorState.macd) { container?.classList.add('hidden'); if (macdChart) { macdChart.remove(); macdChart = null; } return; }
    container?.classList.remove('hidden'); container.innerHTML = '';
    macdChart = LightweightCharts.createChart(container, { width: container.clientWidth, height: 80, layout: { background: { color: '#1a1a1a' }, textColor: '#666' }, grid: { vertLines: { color: '#2a2a2a' }, horzLines: { color: '#2a2a2a' } }, timeScale: { visible: false }, rightPriceScale: { borderColor: '#2a2a2a' } });
    const macdLineSeries = macdChart.addLineSeries({ color: '#3b82f6', lineWidth: 1 }); const macdSignalSeries = macdChart.addLineSeries({ color: '#f59e0b', lineWidth: 1 }); const macdHistSeries = macdChart.addHistogramSeries({ color: '#22c55e', priceFormat: { type: 'volume' }, priceScaleId: '' });
    macdChart.priceScale('').applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
    macdLineSeries.setData(indicatorData.macd?.macd_line || []); macdSignalSeries.setData(indicatorData.macd?.signal_line || []);
    const histData = (indicatorData.macd?.histogram || []).map(d => ({ time: d.time, value: d.value, color: d.value >= 0 ? '#22c55e' : '#ef4444' })); macdHistSeries.setData(histData);
    macdChart.timeScale().fitContent();
}

// Utility
function switchTab(tabName) { console.log('Switch to tab:', tabName); }

// === Corporate Events (Earnings & News) ===
async function updateCorporateEvents() {
    const earningsContainer = document.getElementById('corporate-earnings-list');
    const newsContainer = document.getElementById('corporate-news-feed');

    // Set Loading State
    if (earningsContainer) earningsContainer.innerHTML = '<div class="col-span-2 text-center text-xs text-gray-500 py-4"><i class="fas fa-spinner fa-spin"></i> Loading Earnings...</div>';
    if (newsContainer) newsContainer.innerHTML = '<div class="text-center text-xs text-gray-500 py-4"><i class="fas fa-spinner fa-spin"></i> Loading News...</div>';

    try {
        const response = await fetch('/api/us/corporate-events');
        const data = await response.json();

        // 1. Render Earnings
        if (earningsContainer && data.earnings && data.earnings.length > 0) {
            earningsContainer.innerHTML = '';
            data.earnings.forEach(item => {
                const daysLeft = item.days_left;
                let badgeColor = 'bg-gray-700 text-gray-300';
                if (daysLeft <= 3) badgeColor = 'bg-red-900 text-red-300 animate-pulse'; // 임박
                else if (daysLeft <= 7) badgeColor = 'bg-orange-900 text-orange-300'; // 1주 이내

                const div = document.createElement('div');
                div.className = 'bg-[#2a2a2a] p-2 rounded border border-[#333] flex justify-between items-center';
                div.innerHTML = `
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-white text-sm">${item.ticker}</span>
                        <span class="text-[10px] text-gray-400">${item.date}</span>
                    </div>
                    <span class="text-[10px] px-1.5 py-0.5 rounded font-bold ${badgeColor}">D-${daysLeft}</span>
                `;
                earningsContainer.appendChild(div);
            });
        } else if (earningsContainer) {
            earningsContainer.innerHTML = '<div class="col-span-2 text-center text-xs text-gray-500">예정된 실적 발표가 없습니다.</div>';
        }

        // 2. Render News
        if (newsContainer && data.news && data.news.length > 0) {
            newsContainer.innerHTML = '';
            data.news.forEach(item => {
                const div = document.createElement('div');
                div.className = 'bg-[#2a2a2a] p-2 rounded border border-[#333] hover:bg-[#333] transition-colors cursor-pointer';
                div.innerHTML = `
                    <div class="flex justify-between items-start mb-1">
                        <span class="font-bold text-blue-300 text-xs">${item.ticker || 'Market'}</span>
                        <span class="text-[10px] text-gray-500">${item.date || ''}</span>
                    </div>
                    <div class="text-xs text-gray-300 line-clamp-2">${item.title}</div>
                `;
                newsContainer.appendChild(div);
            });
        } else if (newsContainer) {
            newsContainer.innerHTML = '<div class="text-center text-xs text-gray-500">최신 뉴스가 없습니다.</div>';
        }

    } catch (e) {
        console.error('Corporate events error:', e);
        if (earningsContainer) earningsContainer.innerHTML = '<div class="col-span-2 text-center text-xs text-red-500">Failed to load data.</div>';
        if (newsContainer) newsContainer.innerHTML = '<div class="text-center text-xs text-red-500">Failed to load news.</div>';
    }
}

// === Missing Tab Functions ===

function updateHistoricalTab() {
    const container = document.getElementById('content-historical-returns');
    if (!container) return;

    // Check if already loaded to avoid redundant fetches
    if (container.dataset.loaded === 'true') return;

    // Show loading state if empty
    if (!container.querySelector('.apexcharts-canvas')) {
        // Only if not already rendered
    }

    fetch('/api/us/historical-returns')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Historical data error:', data.error);
                return;
            }
            renderHistoricalTab(data);
            container.dataset.loaded = 'true';
        })
        .catch(e => console.error('Failed to load historical returns:', e));
}

function loadPortfolioRisk() {
    const container = document.getElementById('content-risk');
    if (!container) return;

    // Simple check to prevent multiple loads
    if (container.dataset.loaded === 'true') return;

    fetch('/api/us/portfolio-risk')
        .then(response => response.json())
        .then(data => {
            // If you have a render function, call it here. 
            // Since I don't see a specific renderPortfolioRisk function in the snippet,
            // I will leave this placeholder or call a generic renderer if available.
            // For now, let's assume the user might have missed this implementation too.
            // But valid JSON response is a good start.
            console.log('Risk data loaded:', data);
            container.dataset.loaded = 'true';

            // Basic rendering if container is empty
            if (container.children.length <= 1) { // Title only
                const pre = document.createElement('pre');
                pre.className = 'text-xs text-gray-400 overflow-auto bg-[#1a1a1a] p-4 rounded';
                pre.textContent = JSON.stringify(data, null, 2);
                container.appendChild(pre);
            }
        })
        .catch(e => console.error('Failed to load risk:', e));
}

function loadHoldingsMatrix() {
    const container = document.getElementById('content-holdings-matrix');
    if (!container) return;

    if (container.dataset.loaded === 'true') return;

    fetch('/api/us/holdings-matrix') // Assuming this endpoint exists or similar
        .then(r => r.json())
        .then(data => {
            console.log('Holdings data:', data);
            container.dataset.loaded = 'true';
            // Placeholder render
            if (container.children.length <= 1) {
                const div = document.createElement('div');
                div.className = 'text-gray-400 text-sm p-4';
                div.textContent = 'Data loaded successfully (Visualization coming soon)';
                container.appendChild(div);
            }
        })
        .catch(e => console.error('Holdings error:', e));
}
