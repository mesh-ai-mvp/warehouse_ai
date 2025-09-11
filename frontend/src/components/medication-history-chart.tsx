'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip } from '@/components/ui/chart'
import type { ChartConfig } from '@/components/ui/chart'
import { TrendingUp, TrendingDown, Activity, AlertTriangle } from 'lucide-react'
import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis, ReferenceLine } from 'recharts'

interface ConsumptionRecord {
  date: string
  quantity_consumed: number
  remaining_stock: number
  ai_prediction?: number
}

interface MedicationHistoryChartProps {
  consumptionHistory: ConsumptionRecord[]
  medicationName: string
  currentStock: number
  reorderPoint: number
  height?: number
}

const chartConfig = {
  remaining_stock: {
    label: 'Remaining Stock',
    color: '#3B82F6', // Blue
  },
  quantity_consumed: {
    label: 'Daily Consumption',
    color: '#EF4444', // Red
  },
  ai_prediction: {
    label: 'AI Prediction',
    color: '#10B981', // Green
  },
} satisfies ChartConfig

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border bg-popover p-3 shadow-sm shadow-black/5 min-w-[200px]">
        <div className="text-xs font-medium text-muted-foreground tracking-wide mb-2.5">
          {new Date(label).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
          })}
        </div>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => {
            const config = chartConfig[entry.dataKey as keyof typeof chartConfig]
            if (!config) return null

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
        </div>
      </div>
    )
  }
  return null
}

export default function MedicationHistoryChart({
  consumptionHistory,
  medicationName,
  currentStock,
  reorderPoint,
  height = 300,
}: MedicationHistoryChartProps) {
  const sortedHistory = [...consumptionHistory]
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .slice(-30) // Show last 30 days

  // Calculate metrics
  const avgDailyConsumption =
    sortedHistory.reduce((sum, record) => sum + record.quantity_consumed, 0) / sortedHistory.length
  const totalConsumption = sortedHistory.reduce((sum, record) => sum + record.quantity_consumed, 0)

  // Calculate trend
  const recentConsumption =
    sortedHistory.slice(-7).reduce((sum, record) => sum + record.quantity_consumed, 0) / 7
  const olderConsumption =
    sortedHistory.slice(-14, -7).reduce((sum, record) => sum + record.quantity_consumed, 0) / 7
  const trendDirection = recentConsumption > olderConsumption ? 'up' : 'down'
  const trendPercentage = Math.abs(
    ((recentConsumption - olderConsumption) / olderConsumption) * 100
  )

  // Days until stockout based on current trend
  const daysUntilStockout = currentStock / (recentConsumption || avgDailyConsumption || 1)

  const criticalLevel = reorderPoint * 0.5
  const isLowStock = currentStock <= reorderPoint
  const isCritical = currentStock <= criticalLevel

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-600" />
            Consumption & Stock History
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Historical consumption and stock levels for {medicationName}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant={isCritical ? 'destructive' : isLowStock ? 'secondary' : 'success'}
            className="text-xs"
          >
            {isCritical ? <AlertTriangle className="size-3 mr-1" /> : null}
            {isCritical ? 'Critical' : isLowStock ? 'Low Stock' : 'Normal'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="px-2 pb-6">
        {/* Stats Section */}
        <div className="flex items-center flex-wrap gap-3.5 md:gap-10 px-5 mb-8 text-sm">
          <div className="flex items-center gap-3.5">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: chartConfig.quantity_consumed.color }}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Avg Daily:</span>
              <span className="text-lg font-bold">{avgDailyConsumption.toFixed(1)} units</span>
              <Badge
                variant={trendDirection === 'up' ? 'destructive' : 'success'}
                className="text-xs"
              >
                {trendDirection === 'up' ? (
                  <TrendingUp className="size-3 mr-1" />
                ) : (
                  <TrendingDown className="size-3 mr-1" />
                )}
                {trendPercentage.toFixed(1)}%
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-3.5">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Days Until Stockout:</span>
              <span
                className={`text-lg font-bold ${
                  daysUntilStockout <= 7
                    ? 'text-red-600'
                    : daysUntilStockout <= 14
                      ? 'text-yellow-600'
                      : 'text-green-600'
                }`}
              >
                {daysUntilStockout > 0 ? `~${Math.ceil(daysUntilStockout)}d` : '0d'}
              </span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <ChartContainer config={chartConfig} className="w-full" style={{ height: `${height}px` }}>
          <ComposedChart
            data={sortedHistory}
            margin={{
              top: 20,
              right: 5,
              left: 5,
              bottom: 10,
            }}
          >
            <defs>
              <linearGradient id="stockGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartConfig.remaining_stock.color} stopOpacity={0.3} />
                <stop
                  offset="100%"
                  stopColor={chartConfig.remaining_stock.color}
                  stopOpacity={0.05}
                />
              </linearGradient>
              <linearGradient id="consumptionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={chartConfig.quantity_consumed.color}
                  stopOpacity={0.3}
                />
                <stop
                  offset="100%"
                  stopColor={chartConfig.quantity_consumed.color}
                  stopOpacity={0.05}
                />
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
              tickFormatter={value =>
                new Date(value).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                })
              }
            />

            <YAxis
              yAxisId="stock"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
              tickMargin={10}
              orientation="left"
            />

            <YAxis
              yAxisId="consumption"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }}
              tickMargin={10}
              orientation="right"
            />

            {/* Reference lines */}
            <ReferenceLine
              y={reorderPoint}
              stroke={chartConfig.quantity_consumed.color}
              strokeDasharray="5 5"
              strokeOpacity={0.6}
              yAxisId="stock"
            />

            <ReferenceLine
              y={criticalLevel}
              stroke="#DC2626"
              strokeDasharray="2 2"
              strokeOpacity={0.6}
              yAxisId="stock"
            />

            {/* Stock level area */}
            <Area
              yAxisId="stock"
              dataKey="remaining_stock"
              type="monotone"
              stroke={chartConfig.remaining_stock.color}
              fill="url(#stockGradient)"
              strokeWidth={2}
            />

            {/* Consumption bars as area */}
            <Area
              yAxisId="consumption"
              dataKey="quantity_consumed"
              type="monotone"
              stroke={chartConfig.quantity_consumed.color}
              fill="url(#consumptionGradient)"
              strokeWidth={1}
            />

            {/* AI Prediction line */}
            {sortedHistory.some(record => record.ai_prediction) && (
              <Line
                yAxisId="consumption"
                dataKey="ai_prediction"
                type="monotone"
                stroke={chartConfig.ai_prediction.color}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ r: 2, fill: chartConfig.ai_prediction.color }}
                connectNulls={false}
              />
            )}

            <ChartTooltip content={<CustomTooltip />} />
          </ComposedChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
