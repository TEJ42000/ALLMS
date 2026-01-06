/**
 * Usage Analytics Dashboard JavaScript
 * Handles charts, data grid, and API interactions
 */

// State management
const state = {
    days: 7,
    startDate: null,
    endDate: null,
    granularity: 'daily',
    gridLimit: 100,
};

// Chart instances
let timeseriesChart = null;
let breakdownChart = null;
let topUsersChart = null;
let modelsChart = null;
let usageGrid = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDateControls();
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
            loadTopUsersChart(),
            loadModelsChart(),
            loadGridData(),
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
    } catch (error) {
        console.error('Error loading KPIs:', error);
    }
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
            { title: 'Input Tokens', field: 'input_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
            { title: 'Output Tokens', field: 'output_tokens', sorter: 'number',
              formatter: (cell) => cell.getValue()?.toLocaleString() || '0' },
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

