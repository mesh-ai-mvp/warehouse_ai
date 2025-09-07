// Consumption Chart Module with Plotly.js integration
// Safe initialization that waits for Plotly.js to load

(function() {
    'use strict';

    // Initialize when both DOM and Plotly are ready
    function initializeChartModule() {
        if (!window.Plotly) {
            console.error('Plotly.js is not available. Chart functionality disabled.');
            return;
        }

        console.log('Plotly.js loaded successfully, defining ConsumptionChart class');

        // Define ConsumptionChart class only after Plotly is available
        window.ConsumptionChart = class ConsumptionChart {
            constructor(containerId, medId) {
                this.containerId = containerId;
                this.medId = medId;
                this.chart = null;
                this.data = null;
                this.isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
                
                this.init();
            }

            async init() {
                await this.loadData();
                this.render();
                this.setupEventListeners();
            }

            async loadData() {
                try {
                    console.log(`Loading consumption data for medication ${this.medId}...`);
                    const response = await fetch(`/api/medication/${this.medId}/consumption-history`);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    console.log('Received consumption data:', data);

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    this.data = data;
                    this.updateStatistics();
                } catch (error) {
                    console.error('Error loading consumption data:', error);
                    this.showError(error.message);
                }
            }

            updateStatistics() {
                if (!this.data || !this.data.statistics) return;

                const stats = this.data.statistics;
                
                // Update statistics cards
                const avgConsumption = document.getElementById('avgDailyConsumption');
                if (avgConsumption) {
                    avgConsumption.textContent = stats.avg_daily_consumption.toFixed(1);
                }

                const daysUntilStockout = document.getElementById('daysUntilStockout');
                if (daysUntilStockout) {
                    daysUntilStockout.textContent = stats.days_until_stockout === 999 ? '∞' : stats.days_until_stockout;
                    const stockoutCard = daysUntilStockout.closest('.stat-card');
                    if (stockoutCard) {
                        stockoutCard.className = stats.days_until_stockout < 30 ? 'stat-card danger' : 'stat-card';
                    }
                }

                const currentStock = document.getElementById('currentStock');
                if (currentStock) {
                    currentStock.textContent = Math.round(stats.current_stock).toLocaleString();
                }

                const dataQuality = document.getElementById('dataQuality');
                if (dataQuality) {
                    const quality = stats.data_period_days >= 90 ? 'High' : stats.data_period_days >= 30 ? 'Medium' : 'Low';
                    dataQuality.textContent = quality;
                }
            }

            render() {
                if (!this.data) return;

                const container = document.getElementById(this.containerId);
                if (!container) {
                    console.error(`Chart container not found: ${this.containerId}`);
                    return;
                }

                // Clear any existing loading content
                container.innerHTML = '';

                // Prepare data for Plotly
                const historicalDates = this.data.historical_data.map(d => d.date);
                const historicalConsumption = this.data.historical_data.map(d => d.consumption);
                const historicalStock = this.data.historical_data.map(d => d.stock);

                const forecastDates = this.data.forecast_data.map(d => d.date);
                const forecastConsumption = this.data.forecast_data.map(d => d.consumption);
                const forecastStock = this.data.forecast_data.map(d => d.stock);

                // Chart traces
                const traces = [
                    {
                        x: historicalDates,
                        y: historicalConsumption,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Historical Consumption',
                        line: {
                            color: '#1976d2',
                            width: 3
                        },
                        fill: 'tonexty',
                        fillcolor: 'rgba(25, 118, 210, 0.1)',
                        hovertemplate: '<b>Historical Data</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Consumption: %{y:.1f} units<br>' +
                                      '<extra></extra>',
                        yaxis: 'y'
                    },
                    {
                        x: forecastDates,
                        y: forecastConsumption,
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Forecast',
                        line: {
                            color: '#42a5f5',
                            width: 2,
                            dash: 'dash'
                        },
                        hovertemplate: '<b>Forecast</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Predicted Consumption: %{y:.1f} units<br>' +
                                      '<extra></extra>',
                        yaxis: 'y'
                    },
                    {
                        x: historicalDates.concat(forecastDates),
                        y: historicalStock.concat(forecastStock),
                        type: 'scatter',
                        mode: 'lines',
                        name: 'Stock Level',
                        line: {
                            color: '#ff5722',
                            width: 2
                        },
                        opacity: 0.7,
                        hovertemplate: '<b>Stock Level</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Stock: %{y:.0f} units<br>' +
                                      '<extra></extra>',
                        yaxis: 'y2'
                    }
                ];

                // Layout configuration
                const layout = {
                    title: {
                        text: 'Consumption Trend & Forecast',
                        font: {
                            size: 18,
                            color: this.isDarkMode ? '#e5e7eb' : '#111827',
                            family: 'Inter, sans-serif'
                        },
                        x: 0.02
                    },
                    plot_bgcolor: this.isDarkMode ? '#1f2937' : '#ffffff',
                    paper_bgcolor: this.isDarkMode ? '#111827' : '#ffffff',
                    font: {
                        color: this.isDarkMode ? '#d1d5db' : '#374151',
                        family: 'Inter, sans-serif'
                    },
                    xaxis: {
                        title: 'Date',
                        type: 'date',
                        gridcolor: this.isDarkMode ? '#374151' : '#f3f4f6',
                        linecolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        tickcolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        range: [
                            historicalDates[Math.max(0, historicalDates.length - 90)],
                            forecastDates[forecastDates.length - 1]
                        ]
                    },
                    yaxis: {
                        title: 'Daily Consumption',
                        side: 'left',
                        gridcolor: this.isDarkMode ? '#374151' : '#f3f4f6',
                        linecolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        tickcolor: this.isDarkMode ? '#4b5563' : '#d1d5db'
                    },
                    yaxis2: {
                        title: 'Stock Level',
                        side: 'right',
                        overlaying: 'y',
                        gridcolor: 'transparent',
                        linecolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        tickcolor: this.isDarkMode ? '#4b5563' : '#d1d5db'
                    },
                    legend: {
                        x: 0.02,
                        y: 0.98,
                        bgcolor: this.isDarkMode ? 'rgba(31, 41, 55, 0.8)' : 'rgba(255, 255, 255, 0.8)',
                        bordercolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        borderwidth: 1,
                        font: {
                            size: 12
                        }
                    },
                    margin: {
                        l: 60,
                        r: 60,
                        t: 60,
                        b: 60
                    },
                    hovermode: 'x unified',
                    hoverlabel: {
                        bgcolor: this.isDarkMode ? '#374151' : '#ffffff',
                        bordercolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                        font: {
                            color: this.isDarkMode ? '#e5e7eb' : '#111827'
                        }
                    },
                    shapes: [
                        {
                            type: 'line',
                            x0: historicalDates[historicalDates.length - 1],
                            x1: historicalDates[historicalDates.length - 1],
                            y0: 0,
                            y1: 1,
                            yref: 'paper',
                            line: {
                                color: this.isDarkMode ? '#6b7280' : '#9ca3af',
                                width: 2,
                                dash: 'dot'
                            }
                        }
                    ],
                    annotations: [
                        {
                            x: historicalDates[historicalDates.length - 1],
                            y: 0.95,
                            yref: 'paper',
                            text: 'Forecast Start',
                            showarrow: false,
                            font: {
                                size: 10,
                                color: this.isDarkMode ? '#9ca3af' : '#6b7280'
                            },
                            bgcolor: this.isDarkMode ? 'rgba(31, 41, 55, 0.8)' : 'rgba(255, 255, 255, 0.8)',
                            bordercolor: this.isDarkMode ? '#4b5563' : '#d1d5db',
                            borderwidth: 1
                        }
                    ]
                };

                // Configuration
                const config = {
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'],
                    toImageButtonOptions: {
                        format: 'png',
                        filename: `medication_${this.medId}_consumption_chart`,
                        height: 500,
                        width: 800,
                        scale: 2
                    }
                };

                // Render chart
                window.Plotly.newPlot(this.containerId, traces, layout, config);
                this.chart = document.getElementById(this.containerId);
            }

            setupEventListeners() {
                // Theme change listener
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.attributeName === 'data-theme') {
                            this.isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
                            this.render();
                        }
                    });
                });
                observer.observe(document.documentElement, { attributes: true });

                // Time range buttons
                const timeRangeButtons = document.querySelectorAll('.time-range-btn');
                timeRangeButtons.forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const days = parseInt(e.target.dataset.days);
                        this.updateTimeRange(days);
                        
                        // Update active button
                        timeRangeButtons.forEach(b => b.classList.remove('active'));
                        e.target.classList.add('active');
                    });
                });

                // Refresh button
                const refreshBtn = document.getElementById('refreshChart');
                if (refreshBtn) {
                    refreshBtn.addEventListener('click', () => {
                        this.refresh();
                    });
                }
            }

            updateTimeRange(days) {
                if (!this.chart || !this.data) return;

                const allDates = this.data.historical_data.map(d => d.date);
                const startDate = allDates[Math.max(0, allDates.length - days)];
                const endDate = this.data.forecast_data[this.data.forecast_data.length - 1].date;

                window.Plotly.relayout(this.chart, {
                    'xaxis.range': [startDate, endDate]
                });
            }

            async refresh() {
                const refreshBtn = document.getElementById('refreshChart');
                if (refreshBtn) {
                    refreshBtn.disabled = true;
                    refreshBtn.innerHTML = '<svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7"/></svg>';
                }

                try {
                    await this.loadData();
                    this.render();
                } finally {
                    if (refreshBtn) {
                        refreshBtn.disabled = false;
                        refreshBtn.innerHTML = 'Refresh';
                    }
                }
            }

            showError(message) {
                const container = document.getElementById(this.containerId);
                if (container) {
                    container.innerHTML = `
                        <div class="chart-error">
                            <div class="error-icon">⚠️</div>
                            <h3>Unable to Load Chart Data</h3>
                            <p>${message}</p>
                            <button class="btn btn-secondary" onclick="location.reload()">Retry</button>
                        </div>
                    `;
                }
            }

            destroy() {
                if (this.chart && window.Plotly) {
                    window.Plotly.purge(this.containerId);
                    this.chart = null;
                }
                this.data = null;
            }
        };

        // Signal that ConsumptionChart is ready
        console.log('ConsumptionChart class is now available');
        window.ConsumptionChartReady = true;
    }

    // Wait for Plotly to load, then initialize
    function waitForPlotly() {
        if (window.Plotly) {
            initializeChartModule();
        } else {
            console.log('Waiting for Plotly.js to load...');
            setTimeout(waitForPlotly, 100);
        }
    }

    // Start waiting for Plotly when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitForPlotly);
    } else {
        waitForPlotly();
    }

})();