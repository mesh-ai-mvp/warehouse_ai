import { useParams, Link, Navigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  ArrowLeft,
  Package,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  MapPin,
  Calendar,
  DollarSign,
  Truck,
  Clock,
  ShoppingCart,
  Activity,
} from "lucide-react"

import { 
  useMedication, 
  useConsumptionHistory, 
  useSupplierPrices 
} from "@/hooks/use-api"
import MedicationHistoryChart from "@/components/medication-history-chart"

function getStockLevelInfo(currentStock: number, reorderPoint: number) {
  const percentage = (currentStock / reorderPoint) * 100
  
  if (currentStock <= reorderPoint * 0.25) {
    return { level: 'critical', label: 'Critical', color: 'destructive', percentage }
  } else if (currentStock <= reorderPoint * 0.5) {
    return { level: 'very-low', label: 'Very Low', color: 'destructive', percentage }
  } else if (currentStock <= reorderPoint) {
    return { level: 'low', label: 'Low', color: 'secondary', percentage }
  } else if (currentStock <= reorderPoint * 1.5) {
    return { level: 'normal', label: 'Normal', color: 'outline', percentage }
  } else {
    return { level: 'high', label: 'High', color: 'secondary', percentage }
  }
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  subtitle, 
  trend 
}: {
  title: string
  value: string | number
  icon: any
  subtitle?: string
  trend?: { value: number; direction: 'up' | 'down' }
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
        {trend && (
          <div className="flex items-center gap-1 mt-1">
            {trend.direction === 'up' ? (
              <TrendingUp className="h-3 w-3 text-green-500" />
            ) : (
              <TrendingDown className="h-3 w-3 text-red-500" />
            )}
            <span className={`text-xs ${trend.direction === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {trend.value}% vs last period
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function MedicationDetail() {
  const { id } = useParams<{ id: string }>()
  
  if (!id) {
    return <Navigate to="/inventory" replace />
  }

  const { data: medication, isLoading, error } = useMedication(id)
  const { data: consumptionHistory } = useConsumptionHistory(id, !!medication)
  const { data: supplierPrices } = useSupplierPrices(id, !!medication)

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/inventory">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Medication Details</h2>
            <p className="text-muted-foreground">Error loading medication information</p>
          </div>
        </div>
        
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load medication details. Please try again later.
          </AlertDescription>
        </Alert>
        
        <Button asChild>
          <Link to="/inventory">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Inventory
          </Link>
        </Button>
      </div>
    )
  }

  if (isLoading || !medication) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-md" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-20 mb-2" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const stockInfo = getStockLevelInfo(medication.current_stock, medication.reorder_point)
  const daysUntilStockout = medication.days_until_stockout

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to="/inventory">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{medication.name}</h1>
            <div className="flex items-center gap-4 mt-2">
              <Badge variant="outline">{medication.category}</Badge>
              <Badge variant={stockInfo.color as any}>{stockInfo.label}</Badge>
              {medication.batch_number && (
                <span className="text-sm text-muted-foreground">
                  Batch: {medication.batch_number}
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button asChild>
            <Link to={`/create-po?medication=${medication.med_id}`}>
              <ShoppingCart className="mr-2 h-4 w-4" />
              Create PO
            </Link>
          </Button>
          <Button variant="outline">
            <Activity className="mr-2 h-4 w-4" />
            View Analytics
          </Button>
        </div>
      </div>

      {/* Critical Stock Alert */}
      {stockInfo.level === 'critical' && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Critical Stock Level!</strong> This medication is critically low. 
            Consider creating a purchase order immediately to avoid stockouts.
          </AlertDescription>
        </Alert>
      )}

      {daysUntilStockout <= 7 && daysUntilStockout > 0 && (
        <Alert variant="destructive">
          <Clock className="h-4 w-4" />
          <AlertDescription>
            <strong>Urgent:</strong> This medication will run out in {daysUntilStockout} days 
            at the current consumption rate.
          </AlertDescription>
        </Alert>
      )}

      {/* Statistics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Current Stock"
          value={(medication.current_stock || 0).toLocaleString()}
          icon={Package}
          subtitle={`Reorder at ${medication.reorder_point || 0}`}
        />
        
        <StatCard
          title="Days Until Stockout"
          value={daysUntilStockout > 0 ? `${daysUntilStockout} days` : 'Out of stock'}
          icon={Clock}
          subtitle={`${(medication.avg_daily_pick || 0).toFixed(1)} daily usage`}
          trend={daysUntilStockout < 30 ? { value: 15, direction: 'down' } : undefined}
        />
        
        <StatCard
          title="Inventory Value"
          value={`$${(medication.total_value || 0).toLocaleString()}`}
          icon={DollarSign}
          subtitle={`$${(medication.unit_cost || 0).toFixed(2)} per unit`}
        />
        
        <StatCard
          title="Pack Size"
          value={medication.pack_size}
          icon={Package}
          subtitle={medication.storage_location}
        />
      </div>

      {/* Stock Level Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5" />
            Stock Level Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Current Stock vs Reorder Point</span>
              <span>{Math.round(stockInfo.percentage)}%</span>
            </div>
            <Progress value={Math.min(stockInfo.percentage, 100)} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>0</span>
              <span>Reorder Point ({medication.reorder_point || 0})</span>
              <span>Optimal Level</span>
            </div>
          </div>
          
          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {(medication.current_stock || 0) <= (medication.reorder_point || 0) * 0.25 ? 'Critical' : 
                 (medication.current_stock || 0) <= (medication.reorder_point || 0) * 0.5 ? 'Very Low' : 
                 (medication.current_stock || 0) <= (medication.reorder_point || 0) ? 'Low' : 'Normal'}
              </div>
              <div className="text-sm text-muted-foreground">Status</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {(medication.avg_daily_pick || 0).toFixed(1)}
              </div>
              <div className="text-sm text-muted-foreground">Daily Usage</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {Math.round(((medication.current_stock || 0) - (medication.reorder_point || 0)) / Math.max(medication.avg_daily_pick || 1, 1))}
              </div>
              <div className="text-sm text-muted-foreground">Days Buffer</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Basic Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Category</label>
                <div className="mt-1">
                  <Badge variant="outline">{medication.category}</Badge>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Storage Location</label>
                <div className="mt-1 flex items-center gap-1">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <Badge variant="outline" className="font-mono">
                    {medication.storage_location}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Pack Size</label>
                <div className="mt-1 font-mono">{medication.pack_size || 0} units</div>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Unit Cost</label>
                <div className="mt-1 font-mono">${(medication.unit_cost || 0).toFixed(2)}</div>
              </div>
            </div>
            
            {medication.batch_number && (
              <>
                <Separator />
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Batch Number</label>
                    <div className="mt-1 font-mono">{medication.batch_number}</div>
                  </div>
                  {medication.expiry_date && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">Expiry Date</label>
                      <div className="mt-1 flex items-center gap-1">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        {new Date(medication.expiry_date).toLocaleDateString()}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Supplier Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5" />
              Supplier Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Primary Supplier</label>
              <div className="mt-1 text-lg font-medium">{medication.supplier || 'Unknown'}</div>
            </div>
            
            <div>
              <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
              <div className="mt-1 text-sm text-muted-foreground">
                {medication.last_updated ? new Date(medication.last_updated).toLocaleString() : 'Unknown'}
              </div>
            </div>

            {supplierPrices && supplierPrices.length > 0 && (
              <>
                <Separator />
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">
                    Alternative Suppliers
                  </label>
                  <div className="space-y-2">
                    {supplierPrices.slice(0, 3).map((supplier) => (
                      <div key={supplier.supplier_id} className="flex justify-between items-center text-sm">
                        <span>{supplier.supplier_name}</span>
                        <div className="text-right">
                          <div className="font-mono">${(supplier.unit_price || 0).toFixed(2)}</div>
                          <div className="text-xs text-muted-foreground">
                            {supplier.lead_time_days} days lead time
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Historical Data Chart */}
      {consumptionHistory && consumptionHistory.length > 0 && (
        <MedicationHistoryChart
          consumptionHistory={consumptionHistory}
          medicationName={medication.name}
          currentStock={medication.current_stock}
          reorderPoint={medication.reorder_point}
          height={300}
        />
      )}

      {/* Consumption History Table */}
      {consumptionHistory && consumptionHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Consumption History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Consumed</TableHead>
                  <TableHead>Remaining Stock</TableHead>
                  <TableHead>AI Prediction</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {consumptionHistory.slice(0, 10).map((record) => (
                  <TableRow key={record.date}>
                    <TableCell>
                      {new Date(record.date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="font-mono">
                      {record.quantity_consumed}
                    </TableCell>
                    <TableCell className="font-mono">
                      {record.remaining_stock}
                    </TableCell>
                    <TableCell>
                      {record.ai_prediction ? (
                        <span className="font-mono text-blue-600">
                          {record.ai_prediction.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}