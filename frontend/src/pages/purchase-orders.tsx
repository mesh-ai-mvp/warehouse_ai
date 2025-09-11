import { useState, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ShoppingCart,
  Search,
  Filter,
  Download,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Calendar,
  Package,
  DollarSign,
  Truck,
  Plus,
  Clock,
} from 'lucide-react'

import { usePurchaseOrders, useSuppliers } from '@/hooks/use-api'

function getStatusBadge(status: string) {
  const variants = {
    pending: 'secondary',
    approved: 'default',
    completed: 'default',
    cancelled: 'destructive',
    draft: 'outline',
  } as const

  const colors = {
    pending: 'text-yellow-700 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    approved: 'text-blue-700 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    completed: 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    cancelled: 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    draft: 'text-gray-700 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/30',
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

export function PurchaseOrders() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Extract filters from URL params
  const filters = useMemo(
    () => ({
      search: searchParams.get('search') || undefined,
      status: searchParams.get('status') || undefined,
      supplier: searchParams.get('supplier') || undefined,
      page: parseInt(searchParams.get('page') || '1'),
      page_size: parseInt(searchParams.get('page_size') || '20'),
    }),
    [searchParams]
  )

  const { data, isLoading, error, refetch } = usePurchaseOrders(filters)
  const { data: suppliers } = useSuppliers()

  const updateFilters = (newFilters: Partial<typeof filters>) => {
    const params = new URLSearchParams(searchParams)

    Object.entries(newFilters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        params.delete(key)
      } else {
        params.set(key, value.toString())
      }
    })

    setSearchParams(params)
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Purchase Orders</h2>
          <p className="text-muted-foreground">Manage your purchase orders</p>
        </div>

        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load purchase orders. Please check your connection and try again.
          </AlertDescription>
        </Alert>

        <Button onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    )
  }

  const totalValue = data?.items?.reduce((sum, po) => sum + po.total_amount, 0) || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Purchase Orders</h2>
          <p className="text-muted-foreground">
            Manage your purchase orders ({(data?.total || 0).toLocaleString()} total)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button asChild>
            <Link to="/create-po">
              <Plus className="h-4 w-4 mr-2" />
              Create PO
            </Link>
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (data?.total || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-20" /> : `$${totalValue.toLocaleString()}`}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? (
                <Skeleton className="h-8 w-12" />
              ) : (
                data?.items?.filter(po => po.status === 'pending').length || '0'
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? (
                <Skeleton className="h-8 w-12" />
              ) : (
                data?.items?.filter(po => {
                  const poDate = new Date(po.created_date)
                  const now = new Date()
                  return (
                    poDate.getMonth() === now.getMonth() &&
                    poDate.getFullYear() === now.getFullYear()
                  )
                }).length || '0'
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-64">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search purchase orders..."
                  value={filters.search || ''}
                  onChange={e => updateFilters({ search: e.target.value, page: 1 })}
                  className="pl-8"
                />
              </div>
            </div>

            <Select
              value={filters.status || 'all'}
              onValueChange={value =>
                updateFilters({ status: value === 'all' ? undefined : value, page: 1 })
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.supplier || 'all'}
              onValueChange={value =>
                updateFilters({ supplier: value === 'all' ? undefined : value, page: 1 })
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Supplier" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Suppliers</SelectItem>
                {suppliers?.map(supplier => (
                  <SelectItem key={supplier.supplier_id} value={supplier.name}>
                    {supplier.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Purchase Orders Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order ID</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created Date</TableHead>
                <TableHead>Delivery Date</TableHead>
                <TableHead>Line Items</TableHead>
                <TableHead>Total Amount</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-32" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-6 w-16" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-12" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-8 w-16" />
                    </TableCell>
                  </TableRow>
                ))
              ) : data?.items?.length ? (
                data.items.map(po => (
                  <TableRow key={po.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell>
                      <div className="font-medium">
                        <Link
                          to={`/purchase-orders/${po.id}`}
                          className="hover:underline flex items-center gap-2"
                        >
                          {po.id}
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                      {po.ai_generated && <div className="text-xs text-blue-600">AI Generated</div>}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Truck className="h-4 w-4 text-muted-foreground" />
                        {po.supplier}
                      </div>
                    </TableCell>
                    <TableCell>{getStatusBadge(po.status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        {new Date(po.created_date).toLocaleDateString()}
                      </div>
                    </TableCell>
                    <TableCell>
                      {po.delivery_date ? (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {new Date(po.delivery_date).toLocaleDateString()}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Package className="h-4 w-4 text-muted-foreground" />
                        {po.line_items.length} items
                      </div>
                    </TableCell>
                    <TableCell className="font-mono font-medium">
                      ${(po.total_amount || 0).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link to={`/purchase-orders/${po.id}`}>View Details</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center">
                    No purchase orders found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {data && data.total > 0 && (
            <div className="flex items-center justify-between px-6 py-4 border-t">
              <div className="text-sm text-muted-foreground">
                Showing {(data.page - 1) * filters.page_size + 1} to{' '}
                {Math.min(data.page * filters.page_size, data.total)} of {data.total} orders
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilters({ page: Math.max(1, data.page - 1) })}
                  disabled={data.page <= 1}
                >
                  Previous
                </Button>
                <div className="flex items-center gap-1 text-sm">
                  Page {data.page} of {Math.ceil(data.total / filters.page_size)}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilters({ page: data.page + 1 })}
                  disabled={data.page >= Math.ceil(data.total / filters.page_size)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
