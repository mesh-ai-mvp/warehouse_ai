import { useMemo } from 'react'
import Plot from 'react-plotly.js'
import type { PlotData, Layout, Config } from 'plotly.js'
import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Loader2, Maximize2, Download } from 'lucide-react'

interface PlotlyChartProps {
  data: PlotData[]
  layout?: Partial<Layout>
  config?: Partial<Config>
  title?: string
  subtitle?: string
  loading?: boolean
  height?: number
  className?: string
  showControls?: boolean
  onExport?: () => void
  onFullscreen?: () => void
}

const chartVariants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 20,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: 'easeInOut',
    },
  },
}

const headerVariants = {
  hidden: { opacity: 0, y: -10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      delay: 0.2,
    },
  },
}

export function PlotlyChart({
  data,
  layout = {},
  config = {},
  title,
  subtitle,
  loading = false,
  height = 400,
  className = '',
  showControls = true,
  onExport,
  onFullscreen,
}: PlotlyChartProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true,
  })

  // Dark mode aware layout
  const enhancedLayout = useMemo(
    () => ({
      autosize: true,
      height,
      margin: { l: 60, r: 40, t: 40, b: 60 },
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        family: 'Inter, system-ui, sans-serif',
        size: 12,
        color: 'hsl(var(--foreground))',
      },
      xaxis: {
        gridcolor: 'hsl(var(--border))',
        linecolor: 'hsl(var(--border))',
        tickcolor: 'hsl(var(--muted-foreground))',
        titlefont: { color: 'hsl(var(--foreground))' },
      },
      yaxis: {
        gridcolor: 'hsl(var(--border))',
        linecolor: 'hsl(var(--border))',
        tickcolor: 'hsl(var(--muted-foreground))',
        titlefont: { color: 'hsl(var(--foreground))' },
      },
      legend: {
        font: { color: 'hsl(var(--foreground))' },
        bgcolor: 'transparent',
      },
      ...layout,
    }),
    [layout, height]
  )

  // Responsive config
  const enhancedConfig = useMemo(
    () => ({
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      toImageButtonOptions: {
        format: 'png',
        filename: 'pharmaceutical-chart',
        height: 500,
        width: 700,
        scale: 1,
      },
      ...config,
    }),
    [config]
  )

  return (
    <motion.div
      ref={ref}
      variants={chartVariants as any}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      className={className}
    >
      <Card className="overflow-hidden">
        {(title || subtitle || showControls) && (
          <motion.div
            variants={headerVariants}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
              <div className="space-y-1">
                {title && <CardTitle className="text-lg">{title}</CardTitle>}
                {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
              </div>

              {showControls && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    Pharmaceutical Analytics
                  </Badge>

                  <div className="flex items-center gap-1">
                    {onExport && (
                      <Button onClick={onExport} variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <Download className="h-4 w-4" />
                      </Button>
                    )}

                    {onFullscreen && (
                      <Button
                        onClick={onFullscreen}
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                      >
                        <Maximize2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </CardHeader>
          </motion.div>
        )}

        <CardContent className={title || subtitle || showControls ? '' : 'pt-6'}>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              >
                <Loader2 className="h-8 w-8 text-blue-500" />
              </motion.div>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : { opacity: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="w-full"
            >
              <Plot
                data={data}
                layout={enhancedLayout}
                config={enhancedConfig}
                className="w-full"
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
              />
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Preset pharmaceutical chart configurations
export const PharmaPlotlyPresets = {
  // Time series with forecast
  consumptionForecast: (historicalData: any[], forecastData: any[]) => ({
    data: [
      {
        x: historicalData.map(d => d.date),
        y: historicalData.map(d => d.consumption),
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Historical Consumption',
        line: { color: '#3B82F6', width: 3 },
        marker: { size: 6, color: '#3B82F6' },
      },
      {
        x: forecastData.map(d => d.date),
        y: forecastData.map(d => d.predicted),
        type: 'scatter',
        mode: 'lines',
        name: 'AI Forecast',
        line: { color: '#10B981', width: 2, dash: 'dash' },
        fill: 'tonexty',
        fillcolor: 'rgba(16, 185, 129, 0.1)',
      },
      {
        x: forecastData.map(d => d.date),
        y: forecastData.map(d => d.upper_bound),
        type: 'scatter',
        mode: 'lines',
        name: 'Upper Bound',
        line: { width: 0 },
        showlegend: false,
        hoverinfo: 'skip',
      },
      {
        x: forecastData.map(d => d.date),
        y: forecastData.map(d => d.lower_bound),
        type: 'scatter',
        mode: 'lines',
        name: 'Confidence Interval',
        line: { width: 0 },
        fill: 'tonexty',
        fillcolor: 'rgba(16, 185, 129, 0.2)',
      },
    ],
    layout: {
      title: 'Consumption Trends & AI Forecast',
      xaxis: { title: 'Date' },
      yaxis: { title: 'Daily Consumption (units)' },
    },
  }),

  // Stock level trends with reorder points
  stockLevelTrends: (stockData: any[], reorderPoint: number) => ({
    data: [
      {
        x: stockData.map(d => d.date),
        y: stockData.map(d => d.stock_level),
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Current Stock',
        line: { color: '#0EA5E9', width: 3 },
        marker: { size: 4 },
      },
      {
        x: stockData.map(d => d.date),
        y: Array(stockData.length).fill(reorderPoint),
        type: 'scatter',
        mode: 'lines',
        name: 'Reorder Point',
        line: { color: '#EF4444', width: 2, dash: 'dash' },
      },
      {
        x: stockData.map(d => d.date),
        y: Array(stockData.length).fill(reorderPoint * 0.5),
        type: 'scatter',
        mode: 'lines',
        name: 'Critical Level',
        line: { color: '#DC2626', width: 2, dash: 'dot' },
      },
    ],
    layout: {
      title: 'Stock Level Monitoring',
      xaxis: { title: 'Date' },
      yaxis: { title: 'Stock Level (units)' },
      shapes: [
        {
          type: 'rect',
          xref: 'paper',
          yref: 'y',
          x0: 0,
          y0: 0,
          x1: 1,
          y1: reorderPoint * 0.5,
          fillcolor: 'rgba(239, 68, 68, 0.1)',
          layer: 'below',
          line: { width: 0 },
        },
      ],
    },
  }),

  // Multi-medication comparison
  medicationComparison: (medications: any[]) => ({
    data: medications.map((med, index) => ({
      x: med.data.map((d: any) => d.date),
      y: med.data.map((d: any) => d.consumption),
      type: 'scatter',
      mode: 'lines',
      name: med.name,
      line: {
        width: 3,
        color: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'][index % 5],
      },
    })),
    layout: {
      title: 'Medication Usage Comparison',
      xaxis: { title: 'Date' },
      yaxis: { title: 'Daily Consumption (units)' },
    },
  }),

  // Supplier performance heatmap
  supplierPerformance: (supplierData: any[]) => ({
    data: [
      {
        z: supplierData.map(s => s.metrics),
        x: supplierData.map(s => s.supplier),
        y: ['On-Time Delivery', 'Quality Score', 'Cost Efficiency', 'Response Time'],
        type: 'heatmap',
        colorscale: [
          [0, '#EF4444'],
          [0.5, '#F59E0B'],
          [1, '#10B981'],
        ],
        showscale: true,
      },
    ],
    layout: {
      title: 'Supplier Performance Matrix',
      xaxis: { title: 'Suppliers' },
      yaxis: { title: 'Performance Metrics' },
    },
  }),
}
