'use client'
import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip } from '@/components/ui/chart'
import type { ChartConfig } from '@/components/ui/chart'
import { TrendingUp, Brain } from 'lucide-react'
import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis, ReferenceLine } from 'recharts'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { TimeScaleSelector, TimeScale, getTimeScaleConfig } from '@/components/time-scale-selector'

interface ConsumptionDataPoint {
  date: string
  consumption?: number
  predicted?: number
  upper_bound?: number
  lower_bound?: number
}

interface ConsumptionForecastChartProps {
  historicalData: ConsumptionDataPoint[]
  forecastData: ConsumptionDataPoint[]
  title?: string
  subtitle?: string
  height?: number
  // Time scale functionality
  timeScale?: TimeScale
  onTimeScaleChange?: (value: TimeScale) => void
  showTimeScaleSelector?: boolean
}

const chartConfig = {
  consumption: {
    label: 'Historical',
    color: '#3B82F6', // Blue
  },
  predicted: {
    label: 'AI Forecast',
    color: '#10B981', // Green
  },
  confidence: {
    label: 'Confidence Interval',
    color: '#10B981', // Green with opacity
  },
} satisfies ChartConfig

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border bg-popover p-3 shadow-sm shadow-black/5 min-w-[150px]">
        <div className="text-xs font-medium text-muted-foreground tracking-wide mb-2.5">
          {new Date(label).toLocaleDateString()}
        </div>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => {
            const config = chartConfig[entry.dataKey as keyof typeof chartConfig]
            if (!config || entry.dataKey === 'upper_bound' || entry.dataKey === 'lower_bound') {
              return null // Don't show bounds in tooltip
            }

            return (
              <div key={index} className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-muted-foreground">{config.label}:</span>
                <span className="font-semibold text-popover-foreground">
                  {entry.value.toLocaleString()} units
                </span>
              </div>
            )
          })}

          {/* Show confidence interval if available */}
          {payload.find((p: any) => p.dataKey === 'upper_bound') && (
            <div className="text-xs text-muted-foreground pt-1 border-t">
              Range: {payload.find((p: any) => p.dataKey === 'lower_bound')?.value.toLocaleString()}{' '}
              - {payload.find((p: any) => p.dataKey === 'upper_bound')?.value.toLocaleString()}{' '}
              units
            </div>
          )}
        </div>
      </div>
    )
  }
  return null
}

export default function ConsumptionForecastChart({
  historicalData,
  forecastData,
  title = 'Demand Forecast',
  subtitle = 'Historical data with predictive analytics',
  height = 350,
  timeScale,
  onTimeScaleChange,
  showTimeScaleSelector = false,
}: ConsumptionForecastChartProps) {
  // Validate input data
  const validHistoricalData = Array.isArray(historicalData) ? historicalData : []
  const validForecastData = Array.isArray(forecastData) ? forecastData : []

  // Check if we have valid data to display
  if (validHistoricalData.length === 0 && validForecastData.length === 0) {
    return (
      <Card className="overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="space-y-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {title}
            </CardTitle>
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          </div>
          {showTimeScaleSelector && timeScale && onTimeScaleChange && (
            <TimeScaleSelector value={timeScale} onChange={onTimeScaleChange} />
          )}
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="text-muted-foreground text-sm">
              No chart data available
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Historical and forecast data are both empty
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Combine historical and forecast data with smooth transition
  const combinedData = React.useMemo(() => {
    if (validHistoricalData.length === 0 && validForecastData.length === 0) {
      return []
    }
    
    // Create smooth transition between historical and forecast
    const historical = [...validHistoricalData]
    const forecast = [...validForecastData]
    
    // If both have data, ensure smooth connection
    if (historical.length > 0 && forecast.length > 0) {
      // Find the last non-zero historical value for smooth transition
      let lastNonZeroValue = 0
      for (let i = historical.length - 1; i >= 0; i--) {
        if (historical[i].consumption && historical[i].consumption > 0) {
          lastNonZeroValue = historical[i].consumption
          break
        }
      }
      
      // If the first forecast prediction is very different from last historical,
      // adjust it for visual continuity (but keep the original logic in backend)
      if (lastNonZeroValue > 0 && forecast[0]?.predicted) {
        const ratio = forecast[0].predicted / lastNonZeroValue
        // If forecast is drastically different, add a bridging point
        if (ratio > 3 || ratio < 0.3) {
          const bridgeValue = (lastNonZeroValue + forecast[0].predicted) / 2
          // Update the first forecast point for smoother visual transition
          forecast[0] = {
            ...forecast[0],
            predicted: bridgeValue
          }
        }
      }
    }
    
    return [...historical, ...forecast]
  }, [validHistoricalData, validForecastData])

  // Build weekly ticks (every 7th point)
  const weeklyTicks = combinedData
    .map((d, i) => ({ i, date: d.date }))
    .filter(({ i }) => i % 7 === 0)
    .map(({ date }) => date)

  // Calculate metrics using validated data
  const totalHistoricalConsumption = validHistoricalData.reduce(
    (sum, item) => sum + (item.consumption || 0),
    0
  )
  const avgDailyConsumption = validHistoricalData.length > 0 ? totalHistoricalConsumption / validHistoricalData.length : 0
  const totalForecastConsumption = validForecastData.reduce(
    (sum, item) => sum + (item.predicted || 0),
    0
  )
  const forecastTrend = totalForecastConsumption > totalHistoricalConsumption ? 'up' : 'down'
  const trendPercentage = totalHistoricalConsumption > 0 ? Math.abs(
    ((totalForecastConsumption - totalHistoricalConsumption) / totalHistoricalConsumption) * 100
  ) : 0

  // Find today's date index for reference line
  const today = new Date().toISOString().split('T')[0]
  const todayIndex = combinedData.findIndex(d => d.date === today)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-lg flex items-center gap-2">
            {title}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {subtitle}{timeScale && getTimeScaleConfig(timeScale) ? ` • ${getTimeScaleConfig(timeScale).label} view` : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {showTimeScaleSelector && timeScale && onTimeScaleChange && (
            <TimeScaleSelector value={timeScale} onValueChange={onTimeScaleChange} />
          )}
          <Badge variant="outline" className="text-xs flex items-center gap-1">
            <Brain className="h-3 w-3" />
            AI Powered
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="px-2 pb-6">
        {/* Stats Section */}
        <div className="flex items-center flex-wrap gap-3.5 md:gap-10 px-5 mb-8 text-sm">
          <div className="flex items-center gap-3.5">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: chartConfig.consumption.color }}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Avg Daily</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-muted text-[10px] cursor-default">i</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    Average units dispensed per day over the displayed historical period.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <span className="text-lg font-bold">{avgDailyConsumption.toFixed(0)} units</span>
            </div>
          </div>
          <div className="flex items-center gap-3.5">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: chartConfig.predicted.color }}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Forecast Trend</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-muted text-[10px] cursor-default">i</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    Percentage change between total forecasted and total historical consumption for the same number of days.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <Badge
                variant={forecastTrend === 'up' ? 'destructive' : 'success'}
                className="text-xs"
              >
                {forecastTrend === 'up' ? <TrendingUp className="size-3 mr-1" /> : '↓'}
                {trendPercentage.toFixed(1)}%
              </Badge>
            </div>
          </div>
        </div>

        {/* Chart */}
        <ChartContainer config={chartConfig} className="w-full" style={{ height: `${height}px` }}>
          <ComposedChart
            data={combinedData}
            margin={{
              top: 20,
              right: 5,
              left: 5,
              bottom: 10,
            }}
          >
            <defs>
              <linearGradient id="consumptionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartConfig.consumption.color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={chartConfig.consumption.color} stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartConfig.predicted.color} stopOpacity={0.2} />
                <stop offset="100%" stopColor={chartConfig.predicted.color} stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--input)"
              strokeOpacity={0.5}
              horizontal={true}
              vertical={false}
            />

            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
              tickMargin={10}
              ticks={weeklyTicks}
              tickFormatter={value =>
                new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              }
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
              tickMargin={10}
              interval={0}
              tickFormatter={v => `${Math.round(v)}`}
            />

            {/* Today reference line */}
            {todayIndex >= 0 && (
              <ReferenceLine
                x={combinedData[todayIndex].date}
                stroke="var(--destructive)"
                strokeDasharray="2 2"
                strokeOpacity={0.7}
              />
            )}

            {/* Confidence interval area - single band between bounds */}
            <Area
              dataKey="upper_bound"
              stroke="none"
              fill="url(#confidenceGradient)"
              fillOpacity={0.3}
              activeDot={false as any}
            />
            <Area
              dataKey="lower_bound"
              stroke="none"
              fill="transparent"
              isAnimationActive={false}
            />

            {/* Historical consumption area */}
            <Area
              dataKey="consumption"
              type="monotone"
              stroke={chartConfig.consumption.color}
              fill="url(#consumptionGradient)"
              strokeWidth={2}
            />

            {/* Forecast line */}
            <Line
              dataKey="predicted"
              type="monotone"
              stroke={chartConfig.predicted.color}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 3, fill: chartConfig.predicted.color }}
              connectNulls={true}
            />

            <ChartTooltip content={<CustomTooltip />} />
          </ComposedChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
