import { motion } from "framer-motion"
import { useInView } from "react-intersection-observer"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface AnimatedChartProps {
  type: 'area' | 'bar' | 'pie' | 'line'
  data: any[]
  title?: string
  subtitle?: string
  height?: number
  delay?: number
  className?: string
  colors?: string[]
  dataKey?: string
  xAxisKey?: string
  yAxisKey?: string
}

const chartVariants = {
  hidden: { 
    opacity: 0, 
    scale: 0.95,
    y: 30
  },
  visible: (delay: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.8,
      delay: delay * 0.15,
      ease: [0.22, 1, 0.36, 1]
    }
  })
}

const headerVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      delay: 0.2,
      ease: "easeOut"
    }
  }
}

const DEFAULT_COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // yellow
  '#EF4444', // red
  '#8B5CF6', // purple
  '#06B6D4', // cyan
  '#F97316', // orange
  '#84CC16', // lime
]

const PHARMA_COLORS = [
  '#0EA5E9', // sky blue
  '#22C55E', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#EC4899', // pink
]

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border rounded-lg shadow-lg p-3"
      >
        <p className="font-medium text-sm">{`${label}`}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-xs" style={{ color: entry.color }}>
            {`${entry.name}: ${typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}`}
          </p>
        ))}
      </motion.div>
    )
  }
  return null
}

export function AnimatedChart({
  type,
  data,
  title,
  subtitle,
  height = 300,
  delay = 0,
  className = "",
  colors = PHARMA_COLORS,
  dataKey = "value",
  xAxisKey = "name",
  yAxisKey = "value"
}: AnimatedChartProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true
  })

  const renderChart = () => {
    const commonProps = {
      data,
      width: "100%",
      height
    }

    switch (type) {
      case 'area':
        return (
          <ResponsiveContainer {...commonProps}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors[0]} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={colors[0]} stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey={xAxisKey} 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke={colors[0]}
                fillOpacity={1}
                fill="url(#colorGradient)"
                strokeWidth={2}
                animationBegin={delay * 100}
                animationDuration={1000}
              />
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'bar':
        return (
          <ResponsiveContainer {...commonProps}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey={xAxisKey} 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar 
                dataKey={dataKey} 
                fill={colors[0]}
                radius={[4, 4, 0, 0]}
                animationBegin={delay * 100}
                animationDuration={1000}
              />
            </BarChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer {...commonProps}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                outerRadius={80}
                fill={colors[0]}
                dataKey={dataKey}
                animationBegin={delay * 100}
                animationDuration={1000}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer {...commonProps}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey={xAxisKey} 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <YAxis 
                className="text-xs fill-muted-foreground"
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={colors[0]}
                strokeWidth={3}
                dot={{ fill: colors[0], strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, stroke: colors[0], strokeWidth: 2 }}
                animationBegin={delay * 100}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        )

      default:
        return null
    }
  }

  return (
    <motion.div
      ref={ref}
      custom={delay}
      variants={chartVariants}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      className={className}
    >
      <Card className="overflow-hidden">
        {(title || subtitle) && (
          <motion.div
            variants={headerVariants}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
          >
            <CardHeader>
              {title && <CardTitle className="text-lg">{title}</CardTitle>}
              {subtitle && (
                <p className="text-sm text-muted-foreground">{subtitle}</p>
              )}
            </CardHeader>
          </motion.div>
        )}
        <CardContent className={title || subtitle ? "" : "pt-6"}>
          <motion.div
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : { opacity: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {renderChart()}
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Preset chart configurations for pharmaceutical data
export const PharmaChartPresets = {
  inventoryTrend: (data: any[]) => (
    <AnimatedChart
      type="area"
      data={data}
      title="Inventory Levels Trend"
      subtitle="Stock levels over time"
      xAxisKey="date"
      dataKey="stock_level"
    />
  ),
  
  categoryDistribution: (data: any[]) => (
    <AnimatedChart
      type="pie"
      data={data}
      title="Medication Categories"
      subtitle="Distribution by category"
      xAxisKey="category"
      dataKey="count"
    />
  ),
  
  lowStockAlert: (data: any[]) => (
    <AnimatedChart
      type="bar"
      data={data}
      title="Low Stock Medications"
      subtitle="Items requiring immediate attention"
      xAxisKey="medication"
      dataKey="current_stock"
      colors={['#EF4444', '#F59E0B', '#10B981']}
    />
  ),
  
  consumptionPattern: (data: any[]) => (
    <AnimatedChart
      type="line"
      data={data}
      title="Consumption Patterns"
      subtitle="Daily usage trends"
      xAxisKey="date"
      dataKey="consumption"
    />
  )
}