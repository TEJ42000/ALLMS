/**
 * Usage Analytics Dashboard JavaScript
 * Handles charts, data grid, and API interactions
 */

// Chart color constants
const CHART_COLORS = {
    INPUT_TOKENS: '#6c63ff',      // Purple
    OUTPUT_TOKENS: '#00d4aa',     // Teal
    CACHE_WRITE: '#ff6b6b',       // Red
    CACHE_READ: '#4ecdc4',        // Cyan
    PRIMARY: '#6c63ff',
    SUCCESS: '#00d4aa',
    WARNING: '#ffa500',
    DANGER: '#ff6b6b',
};

// State management
const state = {
    days: 7,
    startDate: null,
    endDate: null,
    granularity: 'daily',
    tokenGranularity: 'daily',
    gridLimit: 100,
};

// Chart instances
let timeseriesChart = null;
let breakdownChart = null;
let topUsersChart = null;
let modelsChart = null;
let tokenBreakdownChart = null;
let usageGrid = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDateControls();
    initializeTokenGranularityControls();
    initializeGrid();
    loadDashboardData();
});

// Date controls
function initializeDateControls() {
    // Set default dates
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - state.days);
    
    document.getElementById('start-date').value = formatDate(startDate);
    document.getElementById('end-date').value = formatDate(endDate);
    state.startDate = formatDate(startDate);
    state.endDate = formatDate(endDate);
    
    // Quick select buttons
    document.querySelectorAll('.quick-select button').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.quick-select button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            state.days = parseInt(btn.dataset.days);
            const end = new Date();
            const start = new Date();
            start.setDate(start.getDate() - state.days);
            
            document.getElementById('start-date').value = formatDate(start);
            document.getElementById('end-date').value = formatDate(end);
            state.startDate = formatDate(start);
            state.endDate = formatDate(end);
            
            loadDashboardData();
        });
    });
    
    // Apply custom dates
    document.getElementById('apply-dates').addEventListener('click', () => {
        state.startDate = document.getElementById('start-date').value;
        state.endDate = document.getElementById('end-date').value;
        document.querySelectorAll('.quick-select button').forEach(b => b.classList.remove('active'));
        loadDashboardData();
    });
    
    // Granularity controls
    document.querySelectorAll('#granularity-controls button').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#granularity-controls button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.granularity = btn.dataset.granularity;
            loadTimeseriesChart();
        });
    });
    
    // Export CSV
    document.getElementById('export-csv').addEventListener('click', () => {
        window.location.href = `/api/admin/usage/export?days=${state.days}`;
    });
    
    // Grid limit
    document.getElementById('grid-limit').addEventListener('change', (e) => {
        state.gridLimit = parseInt(e.target.value);
        loadGridData();
    });
    
    // Grid search
    document.getElementById('grid-search').addEventListener('input', (e) => {
        if (usageGrid) {
            usageGrid.setFilter([
                {field: 'user_email', type: 'like', value: e.target.value},
            ]);
        }
    });
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

// Load all dashboard data
async function loadDashboardData() {
    showLoading();
    try {
        await Promise.all([
            loadKPIs(),
            loadTimeseriesChart(),
            loadBreakdownChart(),
            loadTokenBreakdownChart(),
            loadCacheAnalytics(),
            loadTopUsersChart(),
            loadModelsChart(),
            loadGridData(),
            loadCrossReference(),  // Load Anthropic cross-reference
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    } finally {
        hideLoading();
    }
}

// Load KPIs
async function loadKPIs() {
    try {
        const response = await fetch(`/api/admin/usage/dashboard/kpis?days=${state.days}`);
        const data = await response.json();

        document.getElementById('kpi-requests').textContent = data.total_requests.toLocaleString();
        document.getElementById('kpi-cost').textContent = `$${data.total_cost.toFixed(2)}`;
        document.getElementById('kpi-users').textContent = data.unique_users.toLocaleString();
        document.getElementById('kpi-avg').textContent = `$${data.avg_cost_per_request.toFixed(4)}`;

        // New KPIs
        document.getElementById('kpi-input-tokens').textContent = formatTokens(data.total_input_tokens);
        document.getElementById('kpi-output-tokens').textContent = formatTokens(data.total_output_tokens);
        document.getElementById('kpi-cache-hit-rate').textContent = `${data.cache_hit_rate.toFixed(1)}%`;
        document.getElementById('kpi-cache-savings').textContent = `$${data.cache_cost_savings.toFixed(2)}`;
    } catch (error) {
        console.error('Error loading KPIs:', error);
    }
}

// Helper function to format large token numbers
function formatTokens(tokens) {
    if (tokens >= 1000000) {
        return `${(tokens / 1000000).toFixed(1)}M`;
    } else if (tokens >= 1000) {
        return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toLocaleString();
}

// Time series chart
async function loadTimeseriesChart() {
    try {
        const response = await fetch(
            `/api/admin/usage/timeseries?start_date=${state.startDate}&end_date=${state.endDate}&granularity=${state.granularity}&metric=cost`
        );
        const data = await response.json();
        
        const chartData = data.data.map(d => ({
            x: d.bucket,
            y: d.value,
        }));

        const options = {
            series: [{
                name: 'Cost ($)',
                data: chartData
            }],
            chart: {
                type: 'area',
                height: 280,
                toolbar: { show: false },
                background: 'transparent',
            },
            colors: ['#6c63ff'],
            dataLabels: { enabled: false },
            stroke: { curve: 'smooth', width: 2 },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.5,
                    opacityTo: 0.1,
                }
            },
            xaxis: {
                type: 'category',
                labels: { style: { colors: '#aaa' } },
            },
            yaxis: {
                labels: {
                    style: { colors: '#aaa' },
                    formatter: (val) => `$${val.toFixed(2)}`
                }
            },
            tooltip: {
                theme: 'dark',
                y: { formatter: (val) => `$${val.toFixed(4)}` }
            },
            grid: { borderColor: '#333' },
        };

        if (timeseriesChart) {
            timeseriesChart.updateOptions(options);
        } else {
            timeseriesChart = new ApexCharts(document.getElementById('chart-timeseries'), options);
            timeseriesChart.render();
        }
    } catch (error) {
        console.error('Error loading timeseries:', error);
    }
}

// Breakdown chart (donut)
async function loadBreakdownChart() {
    try {
        const response = await fetch(`/api/admin/usage/breakdown?days=${state.days}&dimension=operation_type`);
        const data = await response.json();

        const options = {
            series: data.breakdown.map(d => d.cost),
            labels: data.breakdown.map(d => d.label),
            chart: {
                type: 'donut',
                height: 320,
                background: 'transparent',
            },
            colors: ['#6c63ff', '#00d4aa', '#ff6b6b', '#ffd93d', '#4ecdc4'],
            legend: {
                position: 'bottom',
                labels: { colors: '#aaa' }
            },
            dataLabels: {
                enabled: true,
                formatter: (val) => `${val.toFixed(1)}%`
            },
            tooltip: {
                theme: 'dark',
                y: { formatter: (val) => `$${val.toFixed(4)}` }
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '60%',
                        labels: {
                            show: true,
                            total: {
                                show: true,
                                label: 'Total',
                                formatter: () => `$${data.total_cost.toFixed(2)}`
                            }
                        }
                    }
                }
            }
        };

        if (breakdownChart) {
            breakdownChart.updateOptions(options);
        } else {
            breakdownChart = new ApexCharts(document.getElementById('chart-breakdown'), options);
            breakdownChart.render();
        }
    } catch (error) {
        console.error('Error loading breakdown:', error);
    }
}

// Top users chart (horizontal bar)
async function loadTopUsersChart() {
    try {
        const response = await fetch(`/api/admin/usage/top-users?days=${state.days}&limit=10`);
        const data = await response.json();

        const options = {
            series: [{
                name: 'Cost',
                data: data.users.map(u => u.total_cost)
            }],
            chart: {
                type: 'bar',
                height: 280,
                toolbar: { show: false },
                background: 'transparent',
            },
            colors: ['#6c63ff'],
            plotOptions: {
                bar: { horizontal: true, borderRadius: 4 }
            },
            dataLabels: {
                enabled: true,
                formatter: (val) => `$${val.toFixed(2)}`,
                style: { colors: ['#fff'] }
            },
            xaxis: {
                categories: data.users.map(u => u.email.split('@')[0]),
                labels: { style: { colors: '#aaa' } }
            },
            yaxis: { labels: { style: { colors: '#aaa' } } },
            tooltip: {
                theme: 'dark',
                y: { formatter: (val) => `$${val.toFixed(4)}` }
            },
            grid: { borderColor: '#333' },
        };

        if (topUsersChart) {
            topUsersChart.updateOptions(options);
        } else {
            topUsersChart = new ApexCharts(document.getElementById('chart-top-users'), options);
            topUsersChart.render();
        }
    } catch (error) {
        console.error('Error loading top users:', error);
    }
}

// Models chart
async function loadModelsChart() {
    try {
        const response = await fetch(`/api/admin/usage/breakdown?days=${state.days}&dimension=model`);
        const data = await response.json();

        const options = {
            series: data.breakdown.map(d => d.requests),
            labels: data.breakdown.map(d => d.label.replace('claude-', '').substring(0, 15)),
            chart: {
                type: 'pie',
                height: 280,
                background: 'transparent',
            },
            colors: ['#6c63ff', '#00d4aa', '#ff6b6b'],
            legend: {
                position: 'bottom',
                labels: { colors: '#aaa' }
            },
            tooltip: { theme: 'dark' },
        };

        if (modelsChart) {
            modelsChart.updateOptions(options);
        } else {
            modelsChart = new ApexCharts(document.getElementById('chart-models'), options);
            modelsChart.render();
        }
    } catch (error) {
        console.error('Error loading models chart:', error);
    }
}

// Token breakdown chart
async function loadTokenBreakdownChart() {
    try {
        const { startDate, endDate } = getDateRange();
        const response = await fetch(
            `/api/admin/usage/token-breakdown?start_date=${startDate}&end_date=${endDate}&granularity=${state.tokenGranularity}`
        );
        const data = await response.json();

        const categories = data.data.map(d => formatBucketLabel(d.bucket, state.tokenGranularity));

        const series = [
            {
                name: 'Input Tokens',
                data: data.data.map(d => d.input_tokens),
                color: CHART_COLORS.INPUT_TOKENS
            },
            {
                name: 'Output Tokens',
                data: data.data.map(d => d.output_tokens),
                color: CHART_COLORS.OUTPUT_TOKENS
            },
            {
                name: 'Cache Write',
                data: data.data.map(d => d.cache_creation_tokens),
                color: CHART_COLORS.CACHE_WRITE
            },
            {
                name: 'Cache Read',
                data: data.data.map(d => d.cache_read_tokens),
                color: CHART_COLORS.CACHE_READ
            }
        ];

        const options = {
            series: series,
            chart: {
                type: 'area',
                height: 320,
                stacked: true,
                toolbar: { show: true },
                background: 'transparent',
            },
            dataLabels: { enabled: false },
            stroke: { curve: 'smooth', width: 2 },
            fill: {
                type: 'gradient',
                gradient: {
                    opacityFrom: 0.6,
                    opacityTo: 0.1,
                }
            },
            xaxis: {
                categories: categories,
                labels: { style: { colors: '#888' } }
            },
            yaxis: {
                labels: {
                    style: { colors: '#888' },
                    formatter: (val) => formatTokens(val)
                }
            },
            legend: {
                position: 'top',
                labels: { colors: '#888' }
            },
            tooltip: {
                theme: 'dark',
                y: {
                    formatter: (val) => val.toLocaleString() + ' tokens'
                }
            },
            grid: {
                borderColor: '#333',
                strokeDashArray: 4,
            }
        };

        if (tokenBreakdownChart) {
            tokenBreakdownChart.destroy();
        }
        tokenBreakdownChart = new ApexCharts(document.querySelector('#chart-token-breakdown'), options);
        tokenBreakdownChart.render();
    } catch (error) {
        console.error('Error loading token breakdown chart:', error);
    }
}

// Cache analytics
async function loadCacheAnalytics() {
    try {
        const response = await fetch(`/api/admin/usage/cache-analytics?days=${state.days}`);
        const data = await response.json();

        document.getElementById('cache-hit-rate-detail').textContent = `${data.cache_hit_rate.toFixed(1)}%`;
        document.getElementById('cache-reads-detail').textContent = formatTokens(data.total_cache_reads);
        document.getElementById('total-input-detail').textContent = formatTokens(data.total_input_tokens + data.total_cache_reads);

        document.getElementById('cache-savings-detail').textContent = `$${data.cache_cost_savings.toFixed(2)}`;
        document.getElementById('cache-overhead-detail').textContent = `$${data.cache_write_overhead.toFixed(2)}`;

        const netColor = data.net_cache_benefit >= 0 ? '#00d4aa' : '#ff6b6b';
        const netSign = data.net_cache_benefit >= 0 ? '+' : '';
        document.getElementById('cache-net-detail').innerHTML =
            `<span style="color: ${netColor}">${netSign}$${data.net_cache_benefit.toFixed(2)}</span>`;

        document.getElementById('cache-operations-detail').textContent =
            `${data.operations_using_cache}/${data.total_operations}`;
        document.getElementById('cache-writes-detail').textContent = formatTokens(data.total_cache_writes);
        document.getElementById('cache-reads-count').textContent = formatTokens(data.total_cache_reads);
    } catch (error) {
        console.error('Error loading cache analytics:', error);
    }
}

// Initialize token granularity controls
function initializeTokenGranularityControls() {
    const controls = document.getElementById('token-granularity-controls');
    if (!controls) return;

    controls.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', () => {
            const granularity = button.dataset.granularity;
            state.tokenGranularity = granularity;

            controls.querySelectorAll('button').forEach(b => b.classList.remove('active'));
            button.classList.add('active');

            loadTokenBreakdownChart();
        });
    });
}

// Data grid
function initializeGrid() {
    usageGrid = new Tabulator('#usage-grid', {
        layout: 'fitColumns',
        pagination: true,
        paginationSize: 50,
        placeholder: 'No data available',
        columns: [
            { title: 'Timestamp', field: 'timestamp', sorter: 'datetime',
              formatter: (cell) => new Date(cell.getValue()).toLocaleString() },
            { title: 'User', field: 'user_email', sorter: 'string' },
            { title: 'Operation', field: 'operation_type', sorter: 'string' },
            { title: 'Model', field: 'model', sorter: 'string',
              formatter: (cell) => cell.getValue()?.replace('claude-', '') || '-' },
            { title: 'Input', field: 'input_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
            { title: 'Output', field: 'output_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
            { title: 'Cache Write', field: 'cache_creation_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
            { title: 'Cache Read', field: 'cache_read_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
            { title: 'Cache %', field: 'cache_percentage', sorter: 'number',
              formatter: (cell) => {
                  const row = cell.getRow().getData();
                  const totalInput = row.input_tokens + row.cache_read_tokens;
                  const cachePercent = totalInput > 0 ? (row.cache_read_tokens / totalInput * 100) : 0;
                  return cachePercent > 0 ? `${cachePercent.toFixed(1)}%` : '-';
              }
            },
            { title: 'Cost', field: 'estimated_cost_usd', sorter: 'number',
              formatter: (cell) => `$${cell.getValue()?.toFixed(4) || '0.0000'}` },
            { title: 'Course', field: 'course_id', sorter: 'string',
              formatter: (cell) => cell.getValue() || '-' },
        ],
    });
}

async function loadGridData() {
    try {
        const response = await fetch(`/api/admin/usage/records?days=${state.days}&limit=${state.gridLimit}`);
        const data = await response.json();
        usageGrid.setData(data.records);
    } catch (error) {
        console.error('Error loading grid data:', error);
    }
}

// =============================================================================
// Anthropic Cross-Reference Functions
// =============================================================================

async function loadCrossReference() {
    const section = document.getElementById('cross-reference-section');
    const errorDiv = document.getElementById('xref-error');

    try {
        const response = await fetch(`/api/admin/usage/reconciliation?days=${state.days}`);

        if (!response.ok) {
            if (response.status === 503) {
                // Admin API not configured
                const error = await response.json();
                showCrossReferenceError(error.detail);
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Show section and hide error
        section.style.display = 'block';
        errorDiv.style.display = 'none';

        // Update KPIs
        document.getElementById('xref-internal-cost').textContent = `$${data.internal_cost.toFixed(4)}`;
        document.getElementById('xref-anthropic-cost').textContent = `$${data.anthropic_cost.toFixed(4)}`;

        // Update variance with safe DOM manipulation
        const varianceColor = data.variance_cost >= 0 ? '#ff6b6b' : '#00d4aa';
        const varianceSign = data.variance_cost >= 0 ? '+' : '';
        const varianceEl = document.getElementById('xref-variance');
        varianceEl.innerHTML = ''; // Clear existing content

        const varianceSpan = document.createElement('span');
        varianceSpan.style.color = varianceColor;
        varianceSpan.textContent = `${varianceSign}$${data.variance_cost.toFixed(4)}`;

        const variancePercent = document.createElement('div');
        variancePercent.style.fontSize = '0.75rem';
        variancePercent.style.color = '#888';
        variancePercent.style.marginTop = '0.25rem';
        variancePercent.textContent = `${varianceSign}${data.variance_cost_percent.toFixed(2)}%`;

        varianceEl.appendChild(varianceSpan);
        varianceEl.appendChild(variancePercent);

        // Update status with color using safe DOM manipulation
        const statusCard = document.getElementById('xref-status-card');
        const statusEl = document.getElementById('xref-status');
        let statusColor, statusText, statusEmoji;

        if (data.match_status === 'exact') {
            statusColor = '#00d4aa';
            statusText = 'Exact Match';
            statusEmoji = '✅';
        } else if (data.match_status === 'close') {
            statusColor = '#ffa500';
            statusText = 'Close Match';
            statusEmoji = '⚠️';
        } else {
            statusColor = '#ff6b6b';
            statusText = 'Mismatch';
            statusEmoji = '❌';
        }

        statusEl.innerHTML = ''; // Clear existing content
        const statusSpan = document.createElement('span');
        statusSpan.style.color = statusColor;
        statusSpan.textContent = `${statusEmoji} ${statusText}`;
        statusEl.appendChild(statusSpan);

        // Update token comparison table
        updateTokenComparisonTable(data);

    } catch (error) {
        console.error('Error loading cross-reference:', error);
        showCrossReferenceError(`Failed to load cross-reference data. ${error?.message || 'Unknown error'}`);
    }
}

function showCrossReferenceError(message) {
    const section = document.getElementById('cross-reference-section');
    const errorDiv = document.getElementById('xref-error');
    const errorMessage = document.getElementById('xref-error-message');

    section.style.display = 'block';
    errorDiv.style.display = 'block';
    errorMessage.textContent = message;

    // Hide KPIs and table
    document.querySelector('#cross-reference-section .kpi-grid').style.display = 'none';
    document.querySelector('#cross-reference-section table').parentElement.style.display = 'none';
}

function updateTokenComparisonTable(data) {
    const tbody = document.getElementById('xref-token-table');

    const tokenTypes = [
        { key: 'input_tokens', label: 'Input Tokens', color: CHART_COLORS.INPUT_TOKENS },
        { key: 'output_tokens', label: 'Output Tokens', color: CHART_COLORS.OUTPUT_TOKENS },
        { key: 'cache_creation_tokens', label: 'Cache Write Tokens', color: CHART_COLORS.CACHE_WRITE },
        { key: 'cache_read_tokens', label: 'Cache Read Tokens', color: CHART_COLORS.CACHE_READ },
    ];

    tbody.innerHTML = tokenTypes.map(type => {
        const internal = data.internal_usage[type.key];
        const anthropic = data.anthropic_usage[type.key];
        const variance = data.variance_tokens[type.key];
        const variancePercent = anthropic > 0 ? (variance / anthropic * 100) : 0;

        const varianceColor = Math.abs(variancePercent) < 1 ? '#00d4aa' :
                             Math.abs(variancePercent) < 5 ? '#ffa500' : '#ff6b6b';
        const varianceSign = variance >= 0 ? '+' : '';

        return `
            <tr style="border-bottom: 1px solid #222;">
                <td style="padding: 0.75rem;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${type.color}; margin-right: 0.5rem;"></span>
                    ${type.label}
                </td>
                <td style="text-align: right; padding: 0.75rem;">${formatTokens(internal)}</td>
                <td style="text-align: right; padding: 0.75rem;">${formatTokens(anthropic)}</td>
                <td style="text-align: right; padding: 0.75rem; color: ${varianceColor};">
                    ${varianceSign}${formatTokens(variance)}
                </td>
                <td style="text-align: right; padding: 0.75rem; color: ${varianceColor};">
                    ${varianceSign}${variancePercent.toFixed(2)}%
                </td>
            </tr>
        `;
    }).join('');
}

// =============================================================================
// Data Management Functions
// =============================================================================

// Initialize data management controls
document.addEventListener('DOMContentLoaded', () => {
    const previewBtn = document.getElementById('preview-delete-btn');
    const deleteBtn = document.getElementById('delete-records-btn');

    if (previewBtn) {
        previewBtn.addEventListener('click', previewDeleteRecords);
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteUserRecords);
    }
});

async function previewDeleteRecords() {
    const email = document.getElementById('delete-user-email').value.trim();
    const days = document.getElementById('delete-days').value;
    const statusDiv = document.getElementById('delete-status');
    const previewDiv = document.getElementById('delete-preview');
    const previewContent = document.getElementById('delete-preview-content');

    if (!email) {
        statusDiv.textContent = '⚠️ Please enter a user email';
        statusDiv.style.color = '#ffa500';
        return;
    }

    statusDiv.textContent = '🔍 Loading preview...';
    statusDiv.style.color = '#6c63ff';
    previewDiv.style.display = 'none';

    try {
        // Build query string
        let url = `/api/admin/usage/users/${encodeURIComponent(email)}`;
        if (days) {
            url += `?days=${days}`;
        } else {
            url += '?days=36500'; // ~100 years for "all time"
        }

        const response = await fetch(url);

        if (!response.ok) {
            if (response.status === 404) {
                statusDiv.textContent = '✅ No records found for this user';
                statusDiv.style.color = '#00d4aa';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Display preview
        previewContent.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem;">
                <div>
                    <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 0.25rem;">Records</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #6c63ff;">${data.total_requests.toLocaleString()}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 0.25rem;">Total Cost</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #ff6b6b;">$${data.total_estimated_cost_usd.toFixed(2)}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 0.25rem;">Input Tokens</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #6c63ff;">${(data.total_input_tokens / 1000000).toFixed(2)}M</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 0.25rem;">Output Tokens</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #00d4aa;">${(data.total_output_tokens / 1000000).toFixed(2)}M</div>
                </div>
            </div>
            <p style="margin: 0; color: #aaa; font-size: 0.875rem;">
                Date range: ${new Date(data.start_date).toLocaleDateString()} to ${new Date(data.end_date).toLocaleDateString()}
            </p>
        `;

        previewDiv.style.display = 'block';
        statusDiv.textContent = `✅ Found ${data.total_requests} records`;
        statusDiv.style.color = '#00d4aa';

    } catch (error) {
        console.error('Error previewing records:', error);
        statusDiv.textContent = `❌ Error: ${error.message}`;
        statusDiv.style.color = '#ff6b6b';
    }
}

async function deleteUserRecords() {
    const email = document.getElementById('delete-user-email').value.trim();
    const days = document.getElementById('delete-days').value;
    const statusDiv = document.getElementById('delete-status');
    const previewDiv = document.getElementById('delete-preview');

    if (!email) {
        statusDiv.textContent = '⚠️ Please enter a user email';
        statusDiv.style.color = '#ffa500';
        return;
    }

    // Confirmation dialog
    const timeRange = days ? `from the last ${days} days` : 'from all time';
    const confirmMessage = `⚠️ DELETE ALL RECORDS?\n\nThis will permanently delete all usage records for:\n${email}\n\nTime range: ${timeRange}\n\nThis action CANNOT be undone!\n\nType "DELETE" to confirm:`;

    const confirmation = prompt(confirmMessage);

    if (confirmation !== 'DELETE') {
        statusDiv.textContent = '❌ Deletion cancelled';
        statusDiv.style.color = '#ffa500';
        return;
    }

    statusDiv.textContent = '🗑️ Deleting records...';
    statusDiv.style.color = '#ff6b6b';

    try {
        // Build query string
        let url = `/api/admin/usage/users/${encodeURIComponent(email)}?confirm=DELETE`;
        if (days) {
            url += `&days=${days}`;
        }

        const response = await fetch(url, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const result = await response.json();

        // Display success
        statusDiv.textContent = `✅ Deleted ${result.deleted_count} records (cost: $${result.total_cost_deleted.toFixed(2)})`;
        statusDiv.style.color = '#00d4aa';

        // Hide preview
        previewDiv.style.display = 'none';

        // Clear form
        document.getElementById('delete-user-email').value = '';

        // Reload dashboard data
        setTimeout(() => {
            loadDashboardData();
        }, 1000);

    } catch (error) {
        console.error('Error deleting records:', error);
        statusDiv.textContent = `❌ Error: ${error.message}`;
        statusDiv.style.color = '#ff6b6b';
    }
}

