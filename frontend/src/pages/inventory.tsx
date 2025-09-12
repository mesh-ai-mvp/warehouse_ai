import { useState, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import type {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
} from '@tanstack/react-table'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import {
  ArrowUpDown,
  ChevronDown,
  MoreHorizontal,
  Package,
  Search,
  Filter,
  Download,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'

import { useInventory, useFilterOptions } from '@/hooks/use-api'
import type { Medication, InventoryFilters } from '@/types/api'

function getStockLevelInfo(medication: Medication) {
  const { current_stock, reorder_point } = medication
  const percentage = (current_stock / reorder_point) * 100

  if (current_stock <= reorder_point * 0.25) {
    return { level: 'critical', label: 'Critical', color: 'destructive', percentage }
  } else if (current_stock <= reorder_point * 0.5) {
    return { level: 'very-low', label: 'Very Low', color: 'destructive', percentage }
  } else if (current_stock <= reorder_point) {
    return { level: 'low', label: 'Low', color: 'secondary', percentage }
  } else if (current_stock <= reorder_point * 1.5) {
    return { level: 'normal', label: 'Normal', color: 'outline', percentage }
  } else {
    return { level: 'high', label: 'High', color: 'secondary', percentage }
  }
}

export function Inventory() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  // Extract filters from URL params
  const filters: InventoryFilters = useMemo(
    () => ({
      search: searchParams.get('search') || undefined,
      category: searchParams.get('category') || undefined,
      supplier: searchParams.get('supplier') || undefined,
      stock_level: (searchParams.get('filter') as any) || undefined,
      page: parseInt(searchParams.get('page') || '1'),
      page_size: parseInt(searchParams.get('page_size') || '10'),
      sort_by: searchParams.get('sort_by') || undefined,
      sort_order: (searchParams.get('sort_order') as any) || undefined,
    }),
    [searchParams]
  )

  const { data, isLoading, error, refetch } = useInventory(filters)
  const { data: filterOptions } = useFilterOptions()

  const updateFilters = (newFilters: Partial<InventoryFilters>) => {
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

  const columns: ColumnDef<Medication>[] = [
    {
      id: 'select',
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={value => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={value => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: 'name',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Medication Name
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const medication = row.original
        return (
          <div className="space-y-1">
            <div className="font-medium">
              <Link
                to={`/medication/${medication.med_id}`}
                className="hover:underline flex items-center gap-2"
              >
                {medication.name}
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
            {medication.batch_number && (
              <div className="text-xs text-muted-foreground">Batch: {medication.batch_number}</div>
            )}
          </div>
        )
      },
    },
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => <Badge variant="outline">{row.getValue('category')}</Badge>,
    },
    {
      accessorKey: 'current_stock',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Current Stock
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const medication = row.original
        const stock = row.getValue('current_stock') as number
        const stockInfo = getStockLevelInfo(medication)

        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="font-mono">{(stock || 0).toLocaleString()}</span>
              <Badge variant={stockInfo.color as any} className="text-xs">
                {stockInfo.label}
              </Badge>
            </div>
            <div className="space-y-1">
              <Progress value={Math.min(stockInfo.percentage, 100)} className="h-1" />
              <div className="text-xs text-muted-foreground">
                Reorder at {medication.reorder_point}
              </div>
            </div>
          </div>
        )
      },
    },
    {
      accessorKey: 'days_until_stockout',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Days Until Stockout
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const days = row.getValue('days_until_stockout') as number

        if (days <= 0) {
          return <Badge variant="destructive">Out of Stock</Badge>
        } else if (days <= 7) {
          return <Badge variant="destructive">{days} days</Badge>
        } else if (days <= 30) {
          return <Badge variant="secondary">{days} days</Badge>
        } else {
          return <span className="text-muted-foreground">{days} days</span>
        }
      },
    },
    {
      accessorKey: 'supplier',
      header: 'Supplier',
      cell: ({ row }) => (
        <div className="max-w-32 truncate" title={row.getValue('supplier')}>
          {row.getValue('supplier')}
        </div>
      ),
    },
    {
      accessorKey: 'total_value',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
        >
          Value
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const value = row.getValue('total_value') as number
        return <div className="font-mono">${(value || 0).toLocaleString()}</div>
      },
    },
    {
      accessorKey: 'storage_location',
      header: 'Location',
      cell: ({ row }) => (
        <Badge variant="outline" className="font-mono text-xs">
          {row.getValue('storage_location')}
        </Badge>
      ),
    },
    {
      accessorKey: 'avg_daily_pick',
      header: 'Daily Usage',
      cell: ({ row }) => {
        const usage = row.getValue('avg_daily_pick') as number
        return (
          <div className="flex items-center gap-1">
            <span className="font-mono">{(usage || 0).toFixed(1)}</span>
            <TrendingDown className="h-3 w-3 text-muted-foreground" />
          </div>
        )
      },
    },
    {
      id: 'actions',
      enableHiding: false,
      cell: ({ row }) => {
        const medication = row.original

        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <Link to={`/medication/${medication.med_id}`}>
                <DropdownMenuItem>View Details</DropdownMenuItem>
              </Link>
              <Link to={`/create-po?medication=${medication.med_id}`}>
                <DropdownMenuItem>Create PO</DropdownMenuItem>
              </Link>
            </DropdownMenuContent>
          </DropdownMenu>
        )
      },
    },
  ]

  const table = useReactTable({
    data: data?.items || [],
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  const selectedRows = table.getFilteredSelectedRowModel().rows
  const selectedMedications = selectedRows.map(row => row.original)

  // Fixed widths for consistent alignment (prevents column shift)
  const columnClasses: Record<string, string> = {
    select: 'w-8',
    name: 'min-w-[220px]',
    category: 'w-36',
    current_stock: 'w-56',
    days_until_stockout: 'w-40 text-center',
    supplier: 'min-w-[220px]',
    total_value: 'w-32 text-right',
    storage_location: 'w-40',
    avg_daily_pick: 'w-28 text-right',
    actions: 'w-12',
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Inventory</h2>
          <p className="text-muted-foreground">Manage your pharmaceutical inventory</p>
        </div>

        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load inventory data. Please check your connection and try again.
          </AlertDescription>
        </Alert>

        <Button onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SidebarTrigger className="h-8 w-8" />
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Inventory</h2>
            <p className="text-muted-foreground">
              Manage your pharmaceutical inventory ({(data?.total || 0).toLocaleString()} items)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <RefreshCw className={`${isLoading ? 'animate-spin' : ''} h-4 w-4 mr-2`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
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
                  placeholder="Search medications..."
                  value={filters.search || ''}
                  onChange={e => updateFilters({ search: e.target.value, page: 1 })}
                  className="pl-8"
                />
              </div>
            </div>

            <Select
              value={filters.category || 'all'}
              onValueChange={value =>
                updateFilters({ category: value === 'all' ? undefined : value, page: 1 })
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {filterOptions?.categories.map(category => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
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
                {filterOptions?.suppliers.map(supplier => (
                  <SelectItem key={supplier} value={supplier}>
                    {supplier}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.stock_level || 'all'}
              onValueChange={value =>
                updateFilters({
                  stock_level: value === 'all' ? undefined : (value as any),
                  page: 1,
                })
              }
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Stock Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="low">Low Stock</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="high">High Stock</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Actions Bar */}
      {selectedMedications.length > 0 && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                {selectedMedications.length} items selected
              </span>
              <Button size="sm" variant="secondary">
                <Package className="h-4 w-4 mr-2" />
                Create PO for Selected
              </Button>
              <Button size="sm" variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Export Selected
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="flex items-center py-4 px-6 border-b">
            <div className="flex items-center gap-4 flex-1">
              <div className="flex items-center space-x-2">
                <p className="text-sm font-medium">Show</p>
                <Select
                  value={filters.page_size?.toString() || '10'}
                  onValueChange={value => updateFilters({ page_size: parseInt(value), page: 1 })}
                >
                  <SelectTrigger className="h-8 w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent side="top">
                    {[10, 20, 50, 100].map(pageSize => (
                      <SelectItem key={pageSize} value={pageSize.toString()}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="ml-auto">
                  Columns <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {table
                  .getAllColumns()
                  .filter(column => column.getCanHide())
                  .map(column => (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      className="capitalize"
                      checked={column.getIsVisible()}
                      onCheckedChange={value => column.toggleVisibility(!!value)}
                    >
                      {column.id}
                    </DropdownMenuCheckboxItem>
                  ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="rounded-md">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map(headerGroup => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map(header => (
                      <TableHead
                        key={header.id}
                        className={columnClasses[header.column.id as string] || ''}
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 10 }).map((_, i) => (
                    <TableRow key={i}>
                      {columns.map((_, j) => (
                        <TableCell key={j}>
                          <Skeleton className="h-4 w-20" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : table.getRowModel().rows?.length ? (
                  table.getRowModel().rows.map(row => (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() && 'selected'}
                      className="hover:bg-muted/50 transition-colors"
                    >
                      {row.getVisibleCells().map(cell => (
                        <TableCell
                          key={cell.id}
                          className={columnClasses[cell.column.id as string] || ''}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      No medications found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-6 py-4 border-t">
            <div className="flex-1 text-sm text-muted-foreground">
              {table.getFilteredSelectedRowModel().rows.length} of{' '}
              {table.getFilteredRowModel().rows.length} row(s) selected.
            </div>
            <div className="flex items-center space-x-6 lg:space-x-8">
              <div className="flex items-center space-x-2">
                <p className="text-sm font-medium">Page</p>
                <div className="flex w-24 items-center justify-center text-sm font-medium">
                  {data?.page || 1} of {data?.total_pages || 1}
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilters({ page: Math.max(1, (data?.page || 1) - 1) })}
                  disabled={!data?.page || data.page <= 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => updateFilters({ page: (data?.page || 1) + 1 })}
                  disabled={!data?.page || data.page >= (data?.total_pages || 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
