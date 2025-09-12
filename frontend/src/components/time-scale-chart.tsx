'use client'

import React, { useState } from 'react'
import { TimeScale, getTimeScaleConfig } from '@/components/time-scale-selector'
import ConsumptionForecastChart from '@/components/consumption-forecast-chart'
import { useConsumptionForecast } from '@/hooks/useAnalytics'

interface TimeScaleChartProps {
  medicationId?: number
  title?: string
  subtitle?: string
  height?: number
  className?: string
  defaultTimeScale?: TimeScale
}

export function TimeScaleChart({
  medicationId,
  title = 'Demand Forecast',
  subtitle = 'Historical data with predictive analytics',
  height = 350,
  className = '',
  defaultTimeScale = 'weekly'
}: TimeScaleChartProps) {
  const [timeScale, setTimeScale] = useState<TimeScale>(defaultTimeScale)
  
  // Get configuration for the selected time scale
  const scaleConfig = getTimeScaleConfig(timeScale)
  
  // Fetch data based on selected time scale
  const { data: forecastData, isLoading, error } = useConsumptionForecast(
    medicationId, 
    scaleConfig.days,
    timeScale
  )

  // Format X-axis based on time scale
  const formatDateForScale = (dateStr: string): string => {
    const date = new Date(dateStr)
    switch (timeScale) {
      case 'weekly':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      case 'monthly':
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      case 'quarterly':
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
      default:
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }

  // Transform data for display based on time scale
  const transformedHistoricalData = React.useMemo(() => {
    if (!forecastData?.historical_data) return []
    
    return forecastData.historical_data.map(item => ({
      ...item,
      displayDate: formatDateForScale(item.date)
    }))
  }, [forecastData?.historical_data, timeScale])

  const transformedForecastData = React.useMemo(() => {
    if (!forecastData?.forecast_data) return []
    
    return forecastData.forecast_data.map(item => ({
      ...item,
      displayDate: formatDateForScale(item.date)
    }))
  }, [forecastData?.forecast_data, timeScale])

  if (error) {
    console.error('TimeScaleChart error:', error)
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-destructive/10 rounded-lg border border-destructive/20">
        <div className="text-center space-y-4">
          <div className="text-lg font-semibold text-destructive">Chart Data Unavailable</div>
          <div className="text-sm text-muted-foreground max-w-md">
            Unable to load forecast data. This may be due to a server issue or network connectivity problem.
          </div>
          <div className="flex gap-2">
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm"
            >
              Reload Page
            </button>
            <button 
              onClick={() => setTimeScale('weekly')} 
              className="px-4 py-2 border border-input rounded-md hover:bg-accent text-sm"
            >
              Reset to Weekly View
            </button>
          </div>
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-muted-foreground mt-4 p-2 bg-muted rounded font-mono">
              Error: {error instanceof Error ? error.message : 'Unknown error'}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <ConsumptionForecastChart
      historicalData={transformedHistoricalData}
      forecastData={transformedForecastData}
      title={title}
      subtitle={subtitle}
      height={height}
      timeScale={timeScale}
      onTimeScaleChange={setTimeScale}
      showTimeScaleSelector={true}
    />
  )
}

export default TimeScaleChart