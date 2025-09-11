'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip } from '@/components/ui/chart'
import type { ChartConfig } from '@/components/ui/chart'
import { TrendingDown, TrendingUp, AlertTriangle, Package } from 'lucide-react'
import { Line, CartesianGrid, ComposedChart, XAxis, YAxis, ReferenceLine, Area } from 'recharts'

interface StockDataPoint {
  date: string
  stock_level: number
}

interface StockLevelChartProps {
  data: StockDataPoint[]
  reorderPoint: number
  title?: string
  subtitle?: string
  height?: number
}

const chartConfig = {
  stock_level: {
    label: 'Stock Level',
    color: '#0EA5E9', // Sky blue
  },
  reorder: {
    label: 'Reorder Point',
    color: '#EF4444', // Red
  },
  critical: {
    label: 'Critical Level',
    color: '#DC2626', // Dark red
  },
} satisfies ChartConfig

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const stockLevel = payload[0]?.value

    return (
      <div className="rounded-lg border bg-popover p-3 shadow-sm shadow-black/5 min-w-[150px]">
        <div className="text-xs font-medium text-muted-foreground tracking-wide mb-2.5">
          {new Date(label).toLocaleDateString()}
        </div>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: chartConfig.stock_level.color }}
            />
            <span className="text-muted-foreground">Stock Level:</span>
            <span className="font-semibold text-popover-foreground">
              {stockLevel?.toLocaleString()} units
            </span>
          </div>

          {/* Status indicator */}
          <div className="pt-1 border-t">
            <Badge
              variant={
                stockLevel <= payload[0]?.payload.criticalLevel
                  ? 'destructive'
                  : stockLevel <= payload[0]?.payload.reorderPoint
                    ? 'secondary'
                    : 'success'
              }
              className="text-xs"
            >
              {stockLevel <= payload[0]?.payload.criticalLevel
                ? 'Critical'
                : stockLevel <= payload[0]?.payload.reorderPoint
                  ? 'Low Stock'
                  : 'Normal'}
            </Badge>
          </div>
        </div>
      </div>
    )
  }
  return null
}

export default function StockLevelChart({
  data,
  reorderPoint,
  title = 'Stock Level Monitoring',
  subtitle = 'Real-time stock tracking with alerts',
  height = 350,
}: StockLevelChartProps) {
  const criticalLevel = reorderPoint * 0.5

  // Add reference levels to data
  const enhancedData = data.map(item => ({
    ...item,
    reorderPoint,
    criticalLevel,
  }))

  // Weekly ticks for x-axis
  const weeklyTicks = enhancedData
    .map((d, i) => ({ i, date: d.date }))
    .filter(({ i }) => i % 7 === 0)
    .map(({ date }) => date)

  // Calculate metrics
  const currentStock = data[data.length - 1]?.stock_level || 0
  const previousStock = data[data.length - 2]?.stock_level || currentStock
  const stockTrend = currentStock > previousStock ? 'up' : 'down'
  const trendPercentage = Math.abs(((currentStock - previousStock) / previousStock) * 100)

  const daysOfStock = Math.floor(
    currentStock / ((data[0]?.stock_level - currentStock) / data.length || 1)
  )

  const stockStatus =
    currentStock <= criticalLevel ? 'critical' : currentStock <= reorderPoint ? 'low' : 'normal'

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-lg flex items-center gap-2">
            <Package className="h-5 w-5 text-blue-600" />
            {title}
          </CardTitle>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>

        <Badge
          variant={
            stockStatus === 'critical'
              ? 'destructive'
              : stockStatus === 'low'
                ? 'secondary'
                : 'success'
          }
          className="text-xs"
        >
          {stockStatus === 'critical' ? <AlertTriangle className="size-3 mr-1" /> : null}
          {stockStatus.charAt(0).toUpperCase() + stockStatus.slice(1)}
        </Badge>
      </CardHeader>

      <CardContent className="px-2 pb-6">
        {/* Stats Section */}
        <div className="flex items-center flex-wrap gap-3.5 md:gap-10 px-5 mb-8 text-sm">
          <div className="flex items-center gap-3.5">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: chartConfig.stock_level.color }}
            />
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Current:</span>
              <span className="text-lg font-bold">{currentStock.toLocaleString()} units</span>
              <Badge variant={stockTrend === 'up' ? 'success' : 'destructive'} className="text-xs">
                {stockTrend === 'up' ? (
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
              <span className="text-sm text-muted-foreground">Days of Stock:</span>
              <span
                className={`text-lg font-bold ${daysOfStock <= 7 ? 'text-red-600' : daysOfStock <= 14 ? 'text-yellow-600' : 'text-green-600'}`}
              >
                {daysOfStock > 0 ? `~${daysOfStock}d` : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Chart */}
        <ChartContainer config={chartConfig} className="w-full" style={{ height: `${height}px` }}>
          <ComposedChart
            data={enhancedData}
            margin={{
              top: 20,
              right: 5,
              left: 5,
              bottom: 10,
            }}
          >
            <defs>
              <linearGradient id="stockGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartConfig.stock_level.color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={chartConfig.stock_level.color} stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="criticalGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartConfig.critical.color} stopOpacity={0.1} />
                <stop offset="100%" stopColor={chartConfig.critical.color} stopOpacity={0.05} />
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

            {/* Critical zone background */}
            <Area
              dataKey={() => criticalLevel}
              stroke="none"
              fill="url(#criticalGradient)"
              fillOpacity={0.3}
            />

            {/* Reorder point reference line */}
            <ReferenceLine
              y={reorderPoint}
              stroke={chartConfig.reorder.color}
              strokeDasharray="5 5"
              strokeOpacity={0.8}
            />

            {/* Critical level reference line */}
            <ReferenceLine
              y={criticalLevel}
              stroke={chartConfig.critical.color}
              strokeDasharray="2 2"
              strokeOpacity={0.8}
            />

            {/* Stock level area */}
            <Area
              dataKey="stock_level"
              type="monotone"
              stroke={chartConfig.stock_level.color}
              fill="url(#stockGradient)"
              strokeWidth={3}
            />

            {/* Stock level line */}
            <Line
              dataKey="stock_level"
              type="monotone"
              stroke={chartConfig.stock_level.color}
              strokeWidth={3}
              dot={{
                r: 4,
                fill: chartConfig.stock_level.color,
                strokeWidth: 2,
                stroke: 'var(--background)',
              }}
              activeDot={{ r: 6, stroke: chartConfig.stock_level.color, strokeWidth: 2 }}
            />

            <ChartTooltip content={<CustomTooltip />} />
          </ComposedChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
