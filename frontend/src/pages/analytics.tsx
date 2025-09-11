import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Package,
  DollarSign,
  AlertTriangle,
  Users,
  FileText,
  Download,
  RefreshCw,
} from 'lucide-react'
import { StatCard } from '@/components/analytics/stat-card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { apiClient } from '@/lib/api-client'

// Mock data for analytics - will be replaced with real API calls
const mockAnalyticsData = {
  kpis: {
    totalRevenue: 2450000,
    totalOrders: 1247,
    avgOrderValue: 1965,
    lowStockItems: 23,
    criticalStockItems: 8,
    totalSuppliers: 45,
    onTimeDeliveries: 94.5,
    inventoryTurnover: 8.2,
  },
  trends: {
    revenueChange: 12.5,
    ordersChange: 8.3,
    avgOrderChange: 3.7,
    stockAlertsChange: -15.2,
  },
  consumptionData: [
    { month: 'Jan', consumption: 450000, orders: 120, forecast: 460000 },
    { month: 'Feb', consumption: 520000, orders: 135, forecast: 530000 },
    { month: 'Mar', consumption: 480000, orders: 128, forecast: 485000 },
    { month: 'Apr', consumption: 590000, orders: 155, forecast: 580000 },
    { month: 'May', consumption: 610000, orders: 162, forecast: 615000 },
    { month: 'Jun', consumption: 580000, orders: 148, forecast: 570000 },
  ],
  supplierPerformance: [
    { name: 'PharmaCorp', orders: 45, onTime: 96.2, avgDelay: 1.2, rating: 4.8 },
    { name: 'MedSupply Pro', orders: 38, onTime: 94.1, avgDelay: 2.1, rating: 4.6 },
    { name: 'HealthDist Inc', orders: 32, onTime: 91.8, avgDelay: 3.2, rating: 4.3 },
    { name: 'BioPharma Ltd', orders: 28, onTime: 98.5, avgDelay: 0.8, rating: 4.9 },
    { name: 'MediCore Systems', orders: 25, onTime: 89.3, avgDelay: 4.1, rating: 4.1 },
  ],
  categoryBreakdown: [
    { name: 'Antibiotics', value: 35, color: '#0088FE' },
    { name: 'Pain Relief', value: 25, color: '#00C49F' },
    { name: 'Cardiovascular', value: 20, color: '#FFBB28' },
    { name: 'Respiratory', value: 12, color: '#FF8042' },
    { name: 'Other', value: 8, color: '#8884D8' },
  ],
  stockAlerts: [
    {
      medication: 'Amoxicillin 500mg',
      current: 45,
      reorder: 100,
      daysLeft: 3,
      priority: 'critical',
    },
    { medication: 'Ibuprofen 200mg', current: 78, reorder: 150, daysLeft: 5, priority: 'low' },
    { medication: 'Lisinopril 10mg', current: 32, reorder: 80, daysLeft: 4, priority: 'low' },
    { medication: 'Metformin 500mg', current: 15, reorder: 120, daysLeft: 2, priority: 'critical' },
  ],
}

export function Analytics() {
  const [timeRange, setTimeRange] = useState('30d')
  const [selectedCategory, setSelectedCategory] = useState('all')

  // This would be replaced with actual API calls
  const {
    data: analyticsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['analytics', timeRange, selectedCategory],
    queryFn: () => Promise.resolve(mockAnalyticsData),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const handleExportReport = () => {
    // Implementation for exporting analytics data
    console.log('Exporting analytics report...')
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-20 bg-muted rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Comprehensive insights into your pharmaceutical operations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 3 months</SelectItem>
              <SelectItem value="1y">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportReport}>
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Revenue"
          value={`$${analyticsData?.kpis.totalRevenue.toLocaleString()}`}
          icon={<DollarSign className="h-8 w-8" />}
          trend={analyticsData?.trends.revenueChange}
          description="vs. previous period"
        />

        <StatCard
          title="Total Orders"
          value={analyticsData?.kpis.totalOrders.toLocaleString()}
          icon={<FileText className="h-8 w-8" />}
          trend={analyticsData?.trends.ordersChange}
          description="purchase orders processed"
        />

        <StatCard
          title="Avg Order Value"
          value={`$${analyticsData?.kpis.avgOrderValue.toLocaleString()}`}
          icon={<BarChart3 className="h-8 w-8" />}
          trend={analyticsData?.trends.avgOrderChange}
          description="per order"
        />

        <StatCard
          title="Stock Alerts"
          value={analyticsData?.kpis.lowStockItems}
          icon={<AlertTriangle className="h-8 w-8" />}
          trend={analyticsData?.trends.stockAlertsChange}
          description="items need attention"
          variant="warning"
        />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Critical Stock</p>
                <p className="text-2xl font-bold text-destructive">
                  {analyticsData?.kpis.criticalStockItems}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-destructive" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Suppliers</p>
                <p className="text-2xl font-bold">{analyticsData?.kpis.totalSuppliers}</p>
              </div>
              <Users className="h-8 w-8 text-primary" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">On-Time Delivery</p>
                <p className="text-2xl font-bold text-green-600">
                  {analyticsData?.kpis.onTimeDeliveries}%
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Inventory Turnover</p>
                <p className="text-2xl font-bold">{analyticsData?.kpis.inventoryTurnover}x</p>
              </div>
              <Package className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="consumption">Consumption Trends</TabsTrigger>
          <TabsTrigger value="suppliers">Supplier Performance</TabsTrigger>
          <TabsTrigger value="inventory">Inventory Analysis</TabsTrigger>
          <TabsTrigger value="alerts">Stock Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Trend */}
            <Card>
              <CardHeader>
                <CardTitle>Revenue & Orders Trend</CardTitle>
                <CardDescription>Monthly performance over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analyticsData?.consumptionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="consumption"
                      stroke="#8884d8"
                      fillOpacity={0.3}
                      fill="#8884d8"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="orders"
                      stroke="#82ca9d"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Category Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Medication Category Breakdown</CardTitle>
                <CardDescription>Distribution by medication type</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={analyticsData?.categoryBreakdown}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label
                    >
                      {analyticsData?.categoryBreakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="consumption">
          <Card>
            <CardHeader>
              <CardTitle>Consumption Analysis</CardTitle>
              <CardDescription>Historical consumption vs forecast predictions</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={analyticsData?.consumptionData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="consumption"
                    stackId="1"
                    stroke="#8884d8"
                    fill="#8884d8"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="forecast"
                    stackId="2"
                    stroke="#82ca9d"
                    fill="#82ca9d"
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="suppliers">
          <Card>
            <CardHeader>
              <CardTitle>Supplier Performance Dashboard</CardTitle>
              <CardDescription>Key metrics for supplier evaluation</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analyticsData?.supplierPerformance.map((supplier, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex-1">
                      <h4 className="font-semibold">{supplier.name}</h4>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span>{supplier.orders} orders</span>
                        <span>{supplier.onTime}% on-time</span>
                        <span>{supplier.avgDelay} days avg delay</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge
                        variant={
                          supplier.rating >= 4.5
                            ? 'success'
                            : supplier.rating >= 4.0
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        ⭐ {supplier.rating}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="inventory">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Inventory Turnover by Category</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analyticsData?.categoryBreakdown}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Inventory Health Score</CardTitle>
                <CardDescription>Overall inventory performance metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>Stock Availability</span>
                  <Badge variant="success">92%</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Turnover Rate</span>
                  <Badge variant="success">Good</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Obsolete Inventory</span>
                  <Badge variant="warning">3.2%</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>Forecast Accuracy</span>
                  <Badge variant="success">87%</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="alerts">
          <Card>
            <CardHeader>
              <CardTitle>Stock Alerts & Critical Items</CardTitle>
              <CardDescription>Items requiring immediate attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analyticsData?.stockAlerts.map((alert, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex-1">
                      <h4 className="font-semibold">{alert.medication}</h4>
                      <p className="text-sm text-muted-foreground">
                        Current: {alert.current} units | Reorder at: {alert.reorder} units
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={alert.priority === 'critical' ? 'destructive' : 'warning'}>
                        {alert.daysLeft} days left
                      </Badge>
                      {alert.priority === 'critical' && (
                        <Button size="sm" variant="destructive">
                          Order Now
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
