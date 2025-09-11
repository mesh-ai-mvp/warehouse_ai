import { useParams, Link, Navigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  User,
  Calendar,
  DollarSign,
  Truck,
  Clock,
  FileText,
  Mail,
  Download,
  RefreshCw,
  Building2,
  Phone,
  MapPin,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Upload,
} from "lucide-react"

import { usePurchaseOrder } from "@/hooks/use-api"
import { StatusTimeline } from "@/components/ui/status-timeline"

function getStatusBadge(status: string) {
  const variants = {
    pending: 'secondary',
    approved: 'default', 
    completed: 'default',
    cancelled: 'destructive',
    draft: 'outline'
  } as const

  const colors = {
    pending: 'text-yellow-700 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    approved: 'text-blue-700 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    completed: 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    cancelled: 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    draft: 'text-gray-700 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30'
  } as const

  return (
    <Badge 
      variant={variants[status as keyof typeof variants] || 'outline'}
      className={colors[status as keyof typeof colors]}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}

function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  subtitle,
  className = ""
}: {
  title: string
  value: string | number
  icon: any
  subtitle?: string
  className?: string
}) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  )
}

export function PurchaseOrderDetail() {
  const { id } = useParams<{ id: string }>()
  
  if (!id) {
    return <Navigate to="/purchase-orders" replace />
  }

  const { data: po, isLoading, error, refetch } = usePurchaseOrder(id)

  // Mock timeline data based on PO status
  const getTimelineItems = (poData: any) => {
    const items = [
      {
        id: "draft",
        title: "Purchase Order Created",
        status: "completed" as const,
        timestamp: poData?.created_at || poData?.created_date,
        description: `PO ${poData?.po_number} created by ${poData?.created_by || poData?.buyer_name || 'System'}`
      }
    ]

    if (poData?.status === "draft") {
      items.push({
        id: "pending",
        title: "Awaiting Approval",
        status: "current" as const,
        timestamp: undefined,
        description: "Purchase order is pending approval"
      })
    } else if (poData?.status === "approved" || poData?.status === "completed") {
      items.push({
        id: "approved",
        title: "Purchase Order Approved", 
        status: "completed" as const,
        timestamp: undefined,
        description: "Purchase order has been approved and sent to supplier"
      })
      
      if (poData?.status === "completed") {
        items.push({
          id: "completed",
          title: "Order Delivered",
          status: "completed" as const,
          timestamp: poData?.actual_delivery_date,
          description: "All items have been delivered and received"
        })
      } else {
        items.push({
          id: "delivery",
          title: "Awaiting Delivery",
          status: "current" as const,
          timestamp: undefined,
          description: `Expected delivery: ${poData?.requested_delivery_date ? new Date(poData.requested_delivery_date).toLocaleDateString() : 'TBD'}`
        })
      }
    } else if (poData?.status === "cancelled") {
      items.push({
        id: "cancelled",
        title: "Purchase Order Cancelled",
        status: "cancelled" as const,
        timestamp: undefined,
        description: "Purchase order has been cancelled"
      })
    }

    return items
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/purchase-orders">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Purchase Orders
            </Link>
          </Button>
        </div>
        
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load purchase order: {error.message}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => refetch()} 
              className="ml-2"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/purchase-orders">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Purchase Orders
            </Link>
          </Button>
        </div>
        
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!po) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/purchase-orders">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Purchase Orders
            </Link>
          </Button>
        </div>
        
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Purchase order not found.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const deliveryProgress = po.status === 'completed' ? 100 : po.status === 'approved' ? 60 : po.status === 'pending' ? 30 : 10

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/purchase-orders">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Purchase Orders
            </Link>
          </Button>
          
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">
              Purchase Order {po.po_number || po.id}
            </h1>
            {getStatusBadge(po.status)}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Mail className="h-4 w-4 mr-2" />
            Email PO
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Key Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Amount"
          value={`$${po.total_amount?.toLocaleString() || '0'}`}
          icon={DollarSign}
          subtitle="Total order value"
        />
        <StatCard
          title="Line Items"
          value={po.items?.length || po.line_items?.length || 0}
          icon={Package}
          subtitle="Number of items"
        />
        <StatCard
          title="Supplier"
          value={po.supplier_name || po.supplier || 'N/A'}
          icon={Building2}
          subtitle="Vendor information"
        />
        <StatCard
          title="Created Date"
          value={po.created_at ? new Date(po.created_at).toLocaleDateString() : po.created_date ? new Date(po.created_date).toLocaleDateString() : 'N/A'}
          icon={Calendar}
          subtitle="Order date"
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="items">Line Items</TabsTrigger>
          <TabsTrigger value="history">Status History</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Supplier Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5" />
                  Supplier Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Company Name</h4>
                  <p className="font-medium">{po.supplier_name || po.supplier || 'N/A'}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Contact Person</h4>
                  <p>{po.contact_person || 'Not specified'}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Email</h4>
                  <p className="text-blue-600 dark:text-blue-400">{po.email || 'Not specified'}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Phone</h4>
                  <p>{po.phone || 'Not specified'}</p>
                </div>
              </CardContent>
            </Card>

            {/* Order Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Order Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">PO Number</h4>
                  <p className="font-mono">{po.po_number || po.id}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Created By</h4>
                  <p>{po.created_by || po.buyer_name || 'System'}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Expected Delivery</h4>
                  <p>{po.requested_delivery_date ? new Date(po.requested_delivery_date).toLocaleDateString() : po.delivery_date ? new Date(po.delivery_date).toLocaleDateString() : 'Not specified'}</p>
                </div>
                <div>
                  <h4 className="font-medium text-sm text-muted-foreground">Notes</h4>
                  <p className="text-sm text-muted-foreground">
                    {po.notes || 'No notes provided'}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Delivery Progress */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Truck className="h-5 w-5" />
                Delivery Progress
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Order Progress</span>
                  <span>{deliveryProgress}%</span>
                </div>
                <Progress value={deliveryProgress} className="h-2" />
                <p className="text-xs text-muted-foreground">
                  {po.status === 'draft' && 'Order is in draft status'}
                  {po.status === 'pending' && 'Order is pending approval'}
                  {po.status === 'approved' && 'Order approved, awaiting delivery'}
                  {po.status === 'completed' && 'Order has been delivered'}
                  {po.status === 'cancelled' && 'Order has been cancelled'}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="items" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Line Items ({(po.items || po.line_items || []).length} items)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Medication</TableHead>
                    <TableHead className="text-right">Quantity</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(po.items || po.line_items || []).map((item: any, index: number) => (
                    <TableRow key={index}>
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {item.med_name || item.medication_name || 'Unknown Item'}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            ID: {item.med_id || item.medication_id}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {item.quantity?.toLocaleString() || 0}
                      </TableCell>
                      <TableCell className="text-right">
                        ${item.unit_price?.toFixed(2) || '0.00'}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        ${Number((item.total_price ?? (item.quantity * item.unit_price) ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              <Separator className="my-4" />
              
              <div className="flex justify-end">
                <div className="text-right space-y-2">
                  <div className="text-lg font-bold">
                    Total: ${Number(po.total_amount ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Status History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <StatusTimeline items={getTimelineItems(po)} />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="documents" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Documents & Attachments
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No documents available</h3>
                <p className="text-muted-foreground mb-4">
                  Documents and attachments related to this purchase order will appear here.
                </p>
                <Button variant="outline">
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Document
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}