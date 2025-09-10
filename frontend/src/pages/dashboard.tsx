import { motion } from "framer-motion"
import { useInView } from "react-intersection-observer"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AnimatedStatCard } from "@/components/ui/animated-card"
import { AnimatedChart } from "@/components/ui/animated-chart"
import { ReUIStatCard, PharmacyStatPresets } from "@/components/ui/reui-stats"
import { GanttChart, PharmaGanttPresets } from "@/components/charts/gantt-chart"
import { PlotlyChart, PharmaPlotlyPresets } from "@/components/charts/plotly-chart"
import { ChartControls, PharmacyFilters } from "@/components/charts/chart-controls"
import {
  Package,
  AlertTriangle,
  TrendingUp,
  ShoppingCart,
  DollarSign,
  Calendar,
  Activity,
  Zap,
  Brain,
  Sparkles,
  RefreshCw
} from "lucide-react"
import { useDashboardStats, useInventory, usePurchaseOrders } from "@/hooks/use-api"

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
}

const headerVariants = {
  hidden: { opacity: 0, y: -30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: [0.22, 1, 0.36, 1]
    }
  }
}

const sectionVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: "easeOut"
    }
  }
}

export function Dashboard() {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true
  })

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useDashboardStats()
  const { data: inventory } = useInventory({ page_size: 100 })
  const { data: purchaseOrders } = usePurchaseOrders({ page_size: 20 })

  // Mock data for charts (in real implementation, this would come from API)
  const inventoryTrendData = [
    { date: '2024-01-01', stock_level: 2450 },
    { date: '2024-01-02', stock_level: 2380 },
    { date: '2024-01-03', stock_level: 2290 },
    { date: '2024-01-04', stock_level: 2420 },
    { date: '2024-01-05', stock_level: 2510 },
    { date: '2024-01-06', stock_level: 2480 },
    { date: '2024-01-07', stock_level: 2560 },
  ]

  const categoryData = [
    { category: 'Antibiotics', count: 450, value: 450 },
    { category: 'Pain Relief', count: 320, value: 320 },
    { category: 'Vaccines', count: 180, value: 180 },
    { category: 'Cardiovascular', count: 280, value: 280 },
    { category: 'Diabetes', count: 150, value: 150 },
    { category: 'Others', count: 620, value: 620 },
  ]

  const lowStockData = inventory?.items
    ?.filter(med => med.current_stock <= med.reorder_point)
    ?.slice(0, 8)
    ?.map(med => ({
      medication: med.name.substring(0, 15) + (med.name.length > 15 ? '...' : ''),
      current_stock: med.current_stock,
      reorder_point: med.reorder_point,
      value: med.current_stock
    })) || []

  const consumptionData = [
    { date: 'Mon', consumption: 145 },
    { date: 'Tue', consumption: 168 },
    { date: 'Wed', consumption: 142 },
    { date: 'Thu', consumption: 189 },
    { date: 'Fri', consumption: 176 },
    { date: 'Sat', consumption: 98 },
    { date: 'Sun', consumption: 87 },
  ]

  return (
    <motion.div
      ref={ref}
      variants={containerVariants}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      className="space-y-8"
    >
      {/* Header */}
      <motion.div variants={headerVariants} className="flex items-center justify-between">
        <div>
          <motion.h1 
            className="text-4xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            Dashboard
          </motion.h1>
          <motion.p 
            className="text-muted-foreground mt-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Real-time pharmaceutical inventory management with AI insights
          </motion.p>
        </div>
        
        <motion.div 
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Badge variant="outline" className="text-blue-600 border-blue-200 bg-blue-50">
            <Sparkles className="h-3 w-3 mr-1" />
            AI Powered
          </Badge>
          <Button 
            onClick={() => refetchStats()}
            variant="outline"
            size="sm"
            className="hover:bg-blue-50"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${statsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </motion.div>
      </motion.div>

      {/* Key Metrics */}
      <motion.section variants={sectionVariants}>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <AnimatedStatCard
            title="Total Medications"
            value={(stats?.total_medications || 0).toString()}
            subtitle="Across all categories"
            icon={Package}
            trend={{ value: 12, direction: 'up' }}
            delay={0}
          />
          
          <AnimatedStatCard
            title="Low Stock Alerts"
            value={(stats?.low_stock_count || 0).toString()}
            subtitle={`${stats?.critical_stock_count || 0} critical`}
            icon={AlertTriangle}
            trend={{ value: 8, direction: 'up' }}
            variant="warning"
            delay={1}
          />
          
          <AnimatedStatCard
            title="Inventory Value"
            value={`$${(stats?.total_value || 0).toLocaleString()}`}
            subtitle="Current market value"
            icon={DollarSign}
            trend={{ value: 5.2, direction: 'up' }}
            variant="success"
            delay={2}
          />
          
          <AnimatedStatCard
            title="Orders Today"
            value={(stats?.orders_today || 0).toString()}
            subtitle="Purchase orders created"
            icon={ShoppingCart}
            trend={{ value: 5.2, direction: 'up' }}
            delay={3}
          />
        </div>
      </motion.section>

      {/* AI Insights */}
      <motion.section variants={sectionVariants}>
        <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/50 dark:to-purple-950/50 border-blue-200 dark:border-blue-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
              <Brain className="h-5 w-5" />
              AI Insights & Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <motion.div 
                className="flex items-center gap-3 p-3 bg-white/60 dark:bg-white/5 rounded-lg"
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <div className="h-10 w-10 bg-blue-100 dark:bg-blue-900/50 rounded-full flex items-center justify-center">
                  <Zap className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="font-medium text-blue-900 dark:text-blue-100">Optimal Reorder Time</p>
                  <p className="text-sm text-blue-700 dark:text-blue-300">3 medications need immediate attention</p>
                </div>
              </motion.div>
              
              <motion.div 
                className="flex items-center gap-3 p-3 bg-white/60 dark:bg-white/5 rounded-lg"
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <div className="h-10 w-10 bg-green-100 dark:bg-green-900/50 rounded-full flex items-center justify-center">
                  <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="font-medium text-green-900 dark:text-green-100">Demand Forecast</p>
                  <p className="text-sm text-green-700 dark:text-green-300">15% increase expected next month</p>
                </div>
              </motion.div>
              
              <motion.div 
                className="flex items-center gap-3 p-3 bg-white/60 dark:bg-white/5 rounded-lg"
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.2 }}
              >
                <div className="h-10 w-10 bg-purple-100 dark:bg-purple-900/50 rounded-full flex items-center justify-center">
                  <Activity className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="font-medium text-purple-900 dark:text-purple-100">Cost Optimization</p>
                  <p className="text-sm text-purple-700 dark:text-purple-300">Potential savings: $12,450</p>
                </div>
              </motion.div>
            </div>
          </CardContent>
        </Card>
      </motion.section>

      {/* Charts Grid */}
      <motion.section variants={sectionVariants}>
        <div className="grid gap-6 md:grid-cols-2">
          <AnimatedChart
            type="area"
            data={inventoryTrendData}
            title="Inventory Levels Trend"
            subtitle="Stock levels over the past week"
            xAxisKey="date"
            dataKey="stock_level"
            height={300}
            delay={0}
          />
          
          <AnimatedChart
            type="pie"
            data={categoryData}
            title="Category Distribution"
            subtitle="Medication categories breakdown"
            xAxisKey="category"
            dataKey="value"
            height={300}
            delay={1}
          />

          <AnimatedChart
            type="bar"
            data={lowStockData}
            title="Low Stock Alerts"
            subtitle="Medications requiring immediate attention"
            xAxisKey="medication"
            dataKey="current_stock"
            colors={['#EF4444', '#F59E0B', '#10B981']}
            height={300}
            delay={2}
          />
          
          <AnimatedChart
            type="line"
            data={consumptionData}
            title="Weekly Consumption Pattern"
            subtitle="Daily medication usage this week"
            xAxisKey="date"
            dataKey="consumption"
            height={300}
            delay={3}
          />
        </div>
      </motion.section>

      {/* Enhanced Analytics Section */}
      <motion.section variants={sectionVariants}>
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Advanced Analytics</h2>
              <p className="text-sm text-muted-foreground">
                Enhanced pharmaceutical analytics with interactive controls
              </p>
            </div>
            <Badge variant="outline" className="text-blue-600 border-blue-200">
              Phase 4 Complete
            </Badge>
          </div>

          {/* Chart Controls */}
          <ChartControls
            title="Analytics Controls"
            filters={PharmacyFilters.inventoryFilters}
            chartTypes={PharmacyFilters.chartTypes}
            dateRange={{
              start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
              end: new Date()
            }}
            onFilterChange={(filterId, value) => console.log('Filter changed:', filterId, value)}
            onChartTypeChange={(typeId) => console.log('Chart type changed:', typeId)}
            onDateRangeChange={(start, end) => console.log('Date range changed:', start, end)}
            onExport={(format) => console.log('Export as:', format)}
            onRefresh={() => console.log('Refresh data')}
            onFullscreen={() => console.log('Toggle fullscreen')}
          />

          {/* ReUI Statistics Grid */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <ReUIStatCard
              {...PharmacyStatPresets.totalMedications(stats?.total_medications || 2456)}
              icon={Package}
              delay={0}
            />
            <ReUIStatCard
              {...PharmacyStatPresets.lowStockAlerts(stats?.low_stock_count || 15, stats?.critical_stock_count || 3)}
              icon={AlertTriangle}
              delay={1}
            />
            <ReUIStatCard
              {...PharmacyStatPresets.inventoryValue(stats?.total_value || 1850000)}
              icon={DollarSign}
              delay={2}
            />
            <ReUIStatCard
              {...PharmacyStatPresets.ordersToday(stats?.orders_today || 8)}
              icon={ShoppingCart}
              delay={3}
            />
          </div>

          {/* Plotly.js Advanced Analytics */}
          <div className="grid gap-6 lg:grid-cols-2">
            <PlotlyChart
              title="Consumption Forecast with AI"
              subtitle="Historical data with predictive analytics"
              {...PharmaPlotlyPresets.consumptionForecast(
                [
                  { date: '2024-01-01', consumption: 145 },
                  { date: '2024-01-02', consumption: 168 },
                  { date: '2024-01-03', consumption: 142 },
                  { date: '2024-01-04', consumption: 189 },
                  { date: '2024-01-05', consumption: 176 }
                ],
                [
                  { date: '2024-01-06', predicted: 185, upper_bound: 210, lower_bound: 160 },
                  { date: '2024-01-07', predicted: 195, upper_bound: 220, lower_bound: 170 },
                  { date: '2024-01-08', predicted: 188, upper_bound: 215, lower_bound: 165 }
                ]
              )}
              height={350}
              showControls={true}
            />
            
            <PlotlyChart
              title="Stock Level Monitoring"
              subtitle="Real-time stock tracking with alerts"
              {...PharmaPlotlyPresets.stockLevelTrends(
                [
                  { date: '2024-01-01', stock_level: 450 },
                  { date: '2024-01-02', stock_level: 420 },
                  { date: '2024-01-03', stock_level: 390 },
                  { date: '2024-01-04', stock_level: 360 },
                  { date: '2024-01-05', stock_level: 335 },
                  { date: '2024-01-06', stock_level: 310 }
                ],
                400 // reorder point
              )}
              height={350}
              showControls={true}
            />
          </div>

          {/* Gantt Chart for Delivery Timeline */}
          <GanttChart
            title="Delivery & Manufacturing Timeline"
            subtitle="Track purchase orders and production schedules"
            tasks={[
              ...PharmaGanttPresets.generateDeliveryTimeline(
                purchaseOrders?.items?.slice(0, 4).map(order => ({
                  ...order,
                  order_date: new Date(Date.now() - Math.random() * 5 * 24 * 60 * 60 * 1000),
                  delivery_date: new Date(Date.now() + Math.random() * 10 * 24 * 60 * 60 * 1000)
                })) || []
              ),
              ...PharmaGanttPresets.generateManufacturingSchedule()
            ]}
            showToday={true}
            height={300}
            onTaskClick={(task) => console.log('Task clicked:', task)}
          />
        </div>
      </motion.section>

      {/* Recent Activity */}
      <motion.section variants={sectionVariants}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {purchaseOrders?.items?.slice(0, 5).map((order, index) => (
                <motion.div
                  key={order.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1, duration: 0.3 }}
                  className="flex items-center justify-between p-3 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <ShoppingCart className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium">Purchase Order #{order.id}</p>
                      <p className="text-sm text-muted-foreground">
                        {order.supplier} • {order.line_items.length} items
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">${(order.total_amount || 0).toLocaleString()}</p>
                    <Badge variant="outline" size="sm">
                      {order.status}
                    </Badge>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.section>
    </motion.div>
  )
}