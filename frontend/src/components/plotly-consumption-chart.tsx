'use client'
import React, { useEffect, useState, useCallback } from 'react'
import Plot from 'react-plotly.js'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RefreshCw, Clock, Package, Activity, TrendingUp } from 'lucide-react'
import { useConsumptionForecast } from '@/hooks/useAnalytics'

interface ConsumptionDataPoint {
  date: string
  consumption: number
  stock?: number
}

interface ForecastDataPoint {
  date: string
  predicted: number
  upper_bound: number
  lower_bound: number
  stock?: number
}

interface PlotlyConsumptionChartProps {
  medicationId: number
  title?: string
  subtitle?: string
  height?: number
  className?: string
}

// Helper function to map time range to appropriate API parameters
function getTimeScaleForRange(days: number): { requestDays: number; timeScale: 'weekly' | 'monthly' } {
  if (days <= 30) {
    return { requestDays: days, timeScale: 'weekly' }
  } else if (days <= 90) {
    return { requestDays: days, timeScale: 'monthly' }
  } else {
    // Cap at monthly since quarterly support was removed
    return { requestDays: 90, timeScale: 'monthly' }
  }
}

export function PlotlyConsumptionChart({
  medicationId,
  title = 'Consumption Trend & Forecast',
  subtitle = 'Historical data with AI-powered forecasting',
  height = 500,
  className = ''
}: PlotlyConsumptionChartProps) {
  const [timeRange, setTimeRange] = useState(90) // Default to 90 days
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  // Get appropriate API parameters based on time range
  const { requestDays, timeScale } = getTimeScaleForRange(timeRange)

  // Fetch consumption forecast data with dynamic parameters
  const { 
    data: forecastData, 
    isLoading, 
    error,
    refetch 
  } = useConsumptionForecast(medicationId, requestDays, timeScale)

  // Check for dark mode
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains('dark'))
    }
    
    checkDarkMode()
    
    // Watch for theme changes
    const observer = new MutationObserver(checkDarkMode)
    observer.observe(document.documentElement, { 
      attributes: true, 
      attributeFilter: ['class'] 
    })
    
    return () => observer.disconnect()
  }, [])

  const handleRefresh = useCallback(async () => {
    setRefreshKey(prev => prev + 1)
    await refetch()
  }, [refetch])

  const handleTimeRangeChange = useCallback(async (days: number) => {
    setTimeRange(days)
    setRefreshKey(prev => prev + 1)
    // Refetch will happen automatically due to hook dependency changes
  }, [])

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            {title}
          </CardTitle>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading chart data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !forecastData) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            {title}
          </CardTitle>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="text-destructive text-lg font-semibold">Chart Data Unavailable</div>
            <div className="text-sm text-muted-foreground mt-2 max-w-md">
              Unable to load consumption data. This may be due to a server issue or network connectivity problem.
            </div>
            <Button onClick={handleRefresh} className="mt-4" variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const { historical_data = [], forecast_data = [] } = forecastData

  // Prepare data for Plotly (based on old implementation)
  const historicalDates = historical_data.map(d => d.date)
  const historicalConsumption = historical_data.map(d => d.consumption)
  
  const forecastDates = forecast_data.map(d => d.date)
  const forecastConsumption = forecast_data.map(d => d.predicted)
  const forecastUpperBound = forecast_data.map(d => d.upper_bound)
  const forecastLowerBound = forecast_data.map(d => d.lower_bound)

  // Calculate 7-day moving average for historical data
  const calculateMovingAverage = (data: number[], window: number = 7) => {
    return data.map((_, index) => {
      const start = Math.max(0, index - window + 1)
      const slice = data.slice(start, index + 1)
      return slice.reduce((sum, val) => sum + val, 0) / slice.length
    })
  }

  const movingAverage = historicalConsumption.length >= 7 
    ? calculateMovingAverage(historicalConsumption, 7)
    : []

  // Better number formatting function
  const formatNumber = (num: number) => {
    return num.toLocaleString('en-US', { 
      minimumFractionDigits: 0, 
      maximumFractionDigits: 1 
    })
  }

  // Use all data since API now returns the correct amount based on time range
  const allDates = [...historicalDates, ...forecastDates]
  const startDate = historicalDates[0] || forecastDates[0]

  // Chart traces with enhanced features
  const traces = [
    // Confidence interval (upper bound)
    {
      x: forecastDates,
      y: forecastUpperBound,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Confidence Interval',
      line: { width: 0, color: 'rgba(66, 165, 245, 0)' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    },
    // Confidence interval (lower bound) - creates filled area with gradient
    {
      x: forecastDates,
      y: forecastLowerBound,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Confidence Range',
      line: { width: 0, color: 'rgba(66, 165, 245, 0)' },
      fill: 'tonexty' as const,
      fillcolor: isDarkMode 
        ? 'rgba(66, 165, 245, 0.15)' 
        : 'rgba(66, 165, 245, 0.2)',
      hovertemplate: '<b>Confidence Range</b><br>' +
                    'Date: %{x}<br>' +
                    'Range: %{text}<br>' +
                    '<extra></extra>',
      text: forecastDates.map((_, i) => 
        `${formatNumber(forecastLowerBound[i])} - ${formatNumber(forecastUpperBound[i])} units`
      ),
    },
    // Historical consumption (main line with gradient fill)
    {
      x: historicalDates,
      y: historicalConsumption,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Historical Consumption',
      line: {
        color: '#1976d2',
        width: 3
      },
      fill: 'tozeroy' as const,
      fillcolor: isDarkMode 
        ? 'rgba(25, 118, 210, 0.08)'
        : 'rgba(25, 118, 210, 0.12)',
      hovertemplate: '<b>Historical Data</b><br>' +
                    'Date: %{x}<br>' +
                    'Consumption: %{text}<br>' +
                    '<extra></extra>',
      text: historicalConsumption.map(val => `${formatNumber(val)} units`),
    },
    // 7-day moving average (if available)
    ...(movingAverage.length > 0 ? [{
      x: historicalDates,
      y: movingAverage,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: '7-Day Average',
      line: {
        color: '#ff9800',
        width: 2,
        dash: 'dot' as const
      },
      opacity: 0.8,
      hovertemplate: '<b>7-Day Moving Average</b><br>' +
                    'Date: %{x}<br>' +
                    'Average: %{text}<br>' +
                    '<extra></extra>',
      text: movingAverage.map(val => `${formatNumber(val)} units`),
    }] : []),
    // Forecast line (dashed)
    {
      x: forecastDates,
      y: forecastConsumption,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'AI Forecast',
      line: {
        color: '#42a5f5',
        width: 3,
        dash: 'dash' as const
      },
      hovertemplate: '<b>AI Forecast</b><br>' +
                    'Date: %{x}<br>' +
                    'Predicted: %{text}<br>' +
                    '<extra></extra>',
      text: forecastConsumption.map(val => `${formatNumber(val)} units`),
    }
  ]

  // Enhanced layout configuration with new features
  const layout = {
    title: {
      text: '',
      font: {
        size: 18,
        color: isDarkMode ? '#e5e7eb' : '#111827',
        family: 'Inter, system-ui, sans-serif'
      }
    },
    plot_bgcolor: isDarkMode ? 'rgba(31, 41, 55, 0.5)' : '#ffffff',
    paper_bgcolor: isDarkMode ? 'transparent' : 'transparent',
    font: {
      color: isDarkMode ? '#d1d5db' : '#374151',
      family: 'Inter, system-ui, sans-serif'
    },
    // Enable spike lines for cursor tracking
    xaxis: {
      title: 'Date',
      type: 'date' as const,
      gridcolor: isDarkMode ? '#374151' : '#f3f4f6',
      linecolor: isDarkMode ? '#4b5563' : '#d1d5db',
      tickcolor: isDarkMode ? '#4b5563' : '#d1d5db',
      range: [startDate, forecastDates[forecastDates.length - 1] || historicalDates[historicalDates.length - 1]],
      spikeline: {
        mode: 'across',
        color: isDarkMode ? '#6b7280' : '#9ca3af',
        thickness: 1,
        dash: 'solid'
      },
      showspikes: true,
      spikemode: 'across',
      // Weekend gaps for time series
      rangebreaks: timeRange >= 90 ? [{
        bounds: ['sat', 'mon'],
        pattern: 'day of week'
      }] : [] // Only show weekend gaps for longer time periods
    },
    yaxis: {
      title: 'Daily Consumption (units)',
      gridcolor: isDarkMode ? '#374151' : '#f3f4f6',
      linecolor: isDarkMode ? '#4b5563' : '#d1d5db',
      tickcolor: isDarkMode ? '#4b5563' : '#d1d5db',
      // Better number formatting on y-axis
      tickformat: ',.0f',
      spikeline: {
        mode: 'across',
        color: isDarkMode ? '#6b7280' : '#9ca3af',
        thickness: 1,
        dash: 'solid'
      },
      showspikes: true,
      spikemode: 'across'
    },
    legend: {
      x: 0.02,
      y: 0.98,
      bgcolor: isDarkMode ? 'rgba(31, 41, 55, 0.8)' : 'rgba(255, 255, 255, 0.8)',
      bordercolor: isDarkMode ? '#4b5563' : '#d1d5db',
      borderwidth: 1,
      font: {
        size: 12,
        color: isDarkMode ? '#d1d5db' : '#374151'
      }
    },
    margin: {
      l: 60,
      r: 20,
      t: 20,
      b: 60
    },
    // Enhanced hover mode with spike lines
    hovermode: 'x unified' as const,
    hoverlabel: {
      bgcolor: isDarkMode ? '#374151' : '#ffffff',
      bordercolor: isDarkMode ? '#4b5563' : '#d1d5db',
      font: {
        color: isDarkMode ? '#e5e7eb' : '#111827'
      }
    },
    // Smooth transitions and animations
    transition: {
      duration: 800,
      easing: 'cubic-in-out'
    },
    shapes: historicalDates.length > 0 ? [{
      type: 'line' as const,
      x0: historicalDates[historicalDates.length - 1],
      x1: historicalDates[historicalDates.length - 1],
      y0: 0,
      y1: 1,
      yref: 'paper' as const,
      line: {
        color: isDarkMode ? '#6b7280' : '#9ca3af',
        width: 2,
        dash: 'dot' as const
      }
    }] : [],
    annotations: historicalDates.length > 0 ? [{
      x: historicalDates[historicalDates.length - 1],
      y: 0.95,
      yref: 'paper' as const,
      text: 'Forecast Start',
      showarrow: false,
      font: {
        size: 10,
        color: isDarkMode ? '#9ca3af' : '#6b7280'
      },
      bgcolor: isDarkMode ? 'rgba(31, 41, 55, 0.8)' : 'rgba(255, 255, 255, 0.8)',
      bordercolor: isDarkMode ? '#4b5563' : '#d1d5db',
      borderwidth: 1
    }] : []
  }

  // Configuration (exact match to old implementation)
  const config = {
    responsive: true,
    displayModeBar: false,
    displaylogo: false,
    modeBarButtonsToRemove: [
      'select2d', 
      'lasso2d', 
      'autoScale2d', 
      'hoverClosestCartesian', 
      'hoverCompareCartesian', 
      'toggleSpikelines'
    ],
    toImageButtonOptions: {
      format: 'png' as const,
      filename: `medication_${medicationId}_consumption_chart`,
      height: 500,
      width: 800,
      scale: 2
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {title}
            </CardTitle>
            {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          
          {/* Controls moved into chart overlay */}
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Statistics Row with enhanced formatting */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center p-3 bg-muted/30 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">
              {formatNumber(forecastData.avg_consumption || 0)}
            </div>
            <div className="text-xs text-muted-foreground">Avg Daily</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded-lg">
            <div className="text-2xl font-bold flex items-center justify-center gap-1">
              {forecastData.trend && forecastData.trend > 0 ? (
                <TrendingUp className="h-4 w-4 text-green-600" />
              ) : (
                <TrendingUp className="h-4 w-4 text-red-600 rotate-180" />
              )}
              {Math.abs((forecastData.trend || 0) * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Trend</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded-lg">
            <div className="text-2xl font-bold">
              {formatNumber(historical_data.length)}
            </div>
            <div className="text-xs text-muted-foreground">Data Points</div>
          </div>
          <div className="text-center p-3 bg-muted/30 rounded-lg">
            <div className="text-2xl font-bold">
              {formatNumber(forecast_data.length)}
            </div>
            <div className="text-xs text-muted-foreground">Forecast Days</div>
          </div>
        </div>

        {/* Plotly Chart with loading overlay */}
        <div style={{ width: '100%', height: `${height}px`, position: 'relative' }}>
          {/* Controls overlay at top-right of chart */}
          <div className="absolute top-2 right-2 z-20 flex items-center gap-2">
            <div className="flex items-center gap-1 bg-background/80 border rounded-md p-1 shadow-sm">
              {[30, 60, 90].map((days) => (
                <Button
                  key={days}
                  onClick={() => handleTimeRangeChange(days)}
                  variant={timeRange === days ? 'default' : 'outline'}
                  size="sm"
                  className="text-xs px-2 py-1 h-7"
                >
                  {days}d
                </Button>
              ))}
              <Button 
                onClick={handleRefresh}
                variant="outline" 
                size="sm"
                className="h-7 px-2"
              >
                <RefreshCw className="h-3 w-3" />
              </Button>
            </div>
          </div>

          {isLoading && (
            <div className="absolute inset-0 z-10 bg-background/80 backdrop-blur-sm flex items-center justify-center rounded-lg">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin text-primary mx-auto mb-2" />
                <div className="text-sm text-muted-foreground">Updating chart...</div>
              </div>
            </div>
          )}
          <Plot
            data={traces}
            layout={{
              ...layout,
              width: undefined,
              height: height,
              autosize: true
            }}
            config={config}
            style={{ width: '100%', height: '100%' }}
            useResizeHandler={true}
            key={`${refreshKey}-${isDarkMode}-${timeRange}`}
          />
        </div>
      </CardContent>
    </Card>
  )
}

export default PlotlyConsumptionChart