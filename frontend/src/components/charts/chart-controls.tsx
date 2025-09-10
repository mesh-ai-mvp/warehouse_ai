import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import { 
  Filter, 
  Download, 
  Maximize2, 
  Settings, 
  Calendar as CalendarIcon,
  RefreshCw,
  BarChart3,
  LineChart,
  PieChart,
  TrendingUp,
  X
} from 'lucide-react'

interface ChartFilter {
  id: string
  label: string
  type: 'select' | 'multiselect' | 'date-range' | 'number-range' | 'text' | 'checkbox'
  value: any
  options?: { label: string; value: any }[]
  placeholder?: string
  min?: number
  max?: number
}

interface ChartControlsProps {
  title?: string
  filters?: ChartFilter[]
  chartTypes?: Array<{
    id: string
    label: string
    icon: React.ComponentType<any>
    active?: boolean
  }>
  dateRange?: {
    start: Date | null
    end: Date | null
  }
  showLegend?: boolean
  showGrid?: boolean
  showTooltips?: boolean
  onFilterChange?: (filterId: string, value: any) => void
  onChartTypeChange?: (typeId: string) => void
  onDateRangeChange?: (start: Date | null, end: Date | null) => void
  onToggleLegend?: (show: boolean) => void
  onToggleGrid?: (show: boolean) => void
  onToggleTooltips?: (show: boolean) => void
  onExport?: (format: 'png' | 'pdf' | 'csv' | 'xlsx') => void
  onRefresh?: () => void
  onFullscreen?: () => void
  className?: string
}

const controlVariants = {
  hidden: { opacity: 0, y: -10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3 }
  },
  exit: { opacity: 0, y: -10, transition: { duration: 0.2 } }
}

export function ChartControls({
  title = "Chart Controls",
  filters = [],
  chartTypes = [],
  dateRange,
  showLegend = true,
  showGrid = true,
  showTooltips = true,
  onFilterChange,
  onChartTypeChange,
  onDateRangeChange,
  onToggleLegend,
  onToggleGrid,
  onToggleTooltips,
  onExport,
  onRefresh,
  onFullscreen,
  className
}: ChartControlsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeFilters, setActiveFilters] = useState<string[]>([])

  const handleFilterChange = (filterId: string, value: any) => {
    onFilterChange?.(filterId, value)
    
    // Track active filters
    if (value && value !== '' && value !== null) {
      if (!activeFilters.includes(filterId)) {
        setActiveFilters([...activeFilters, filterId])
      }
    } else {
      setActiveFilters(activeFilters.filter(id => id !== filterId))
    }
  }

  const clearAllFilters = () => {
    filters.forEach(filter => {
      onFilterChange?.(filter.id, filter.type === 'checkbox' ? false : null)
    })
    setActiveFilters([])
  }

  const renderFilter = (filter: ChartFilter) => {
    switch (filter.type) {
      case 'select':
        return (
          <Select value={filter.value || ''} onValueChange={(value) => handleFilterChange(filter.id, value)}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder={filter.placeholder} />
            </SelectTrigger>
            <SelectContent>
              {filter.options?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )

      case 'text':
        return (
          <Input
            placeholder={filter.placeholder}
            value={filter.value || ''}
            onChange={(e) => handleFilterChange(filter.id, e.target.value)}
            className="h-8"
          />
        )

      case 'number-range':
        return (
          <div className="flex items-center gap-2">
            <Input
              type="number"
              placeholder={filter.min?.toString()}
              value={filter.value?.min || ''}
              onChange={(e) => handleFilterChange(filter.id, { ...filter.value, min: e.target.value })}
              className="h-8 w-20"
            />
            <span className="text-sm text-muted-foreground">to</span>
            <Input
              type="number"
              placeholder={filter.max?.toString()}
              value={filter.value?.max || ''}
              onChange={(e) => handleFilterChange(filter.id, { ...filter.value, max: e.target.value })}
              className="h-8 w-20"
            />
          </div>
        )

      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={filter.id}
              checked={filter.value || false}
              onCheckedChange={(checked) => handleFilterChange(filter.id, checked)}
            />
            <Label htmlFor={filter.id} className="text-sm">
              {filter.label}
            </Label>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <Card className={cn("mb-6", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Settings className="h-4 w-4" />
            {title}
            {activeFilters.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {activeFilters.length} active
              </Badge>
            )}
          </CardTitle>
          
          <div className="flex items-center gap-2">
            {/* Quick actions */}
            <div className="flex items-center gap-1">
              {onRefresh && (
                <Button
                  onClick={onRefresh}
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                >
                  <RefreshCw className="h-4 w-4" />
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
              
              {onExport && (
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                      <Download className="h-4 w-4" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-40" align="end">
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Export as</p>
                      <div className="grid gap-1">
                        {(['png', 'pdf', 'csv', 'xlsx'] as const).map(format => (
                          <Button
                            key={format}
                            onClick={() => onExport(format)}
                            variant="ghost"
                            size="sm"
                            className="justify-start h-8"
                          >
                            {format.toUpperCase()}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              )}
            </div>
            
            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
              size="sm"
              className="h-8 px-2"
            >
              <Filter className="h-4 w-4 mr-1" />
              {isExpanded ? 'Hide' : 'Show'} Filters
            </Button>
          </div>
        </div>
      </CardHeader>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            variants={controlVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <CardContent className="pt-0">
              <div className="space-y-6">
                {/* Chart type selection */}
                {chartTypes.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Chart Type</Label>
                    <div className="flex items-center gap-2 flex-wrap">
                      {chartTypes.map(type => {
                        const IconComponent = type.icon
                        return (
                          <Button
                            key={type.id}
                            onClick={() => onChartTypeChange?.(type.id)}
                            variant={type.active ? "default" : "outline"}
                            size="sm"
                            className="h-8"
                          >
                            <IconComponent className="h-3 w-3 mr-1" />
                            {type.label}
                          </Button>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Date range */}
                {dateRange && onDateRangeChange && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Date Range</Label>
                    <div className="flex items-center gap-2">
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button variant="outline" size="sm" className="h-8 w-32 justify-start">
                            <CalendarIcon className="h-3 w-3 mr-1" />
                            {dateRange.start ? format(dateRange.start, 'MMM dd') : 'Start date'}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0">
                          <Calendar
                            mode="single"
                            selected={dateRange.start || undefined}
                            onSelect={(date) => onDateRangeChange(date || null, dateRange.end)}
                          />
                        </PopoverContent>
                      </Popover>
                      
                      <span className="text-sm text-muted-foreground">to</span>
                      
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button variant="outline" size="sm" className="h-8 w-32 justify-start">
                            <CalendarIcon className="h-3 w-3 mr-1" />
                            {dateRange.end ? format(dateRange.end, 'MMM dd') : 'End date'}
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0">
                          <Calendar
                            mode="single"
                            selected={dateRange.end || undefined}
                            onSelect={(date) => onDateRangeChange(dateRange.start, date || null)}
                          />
                        </PopoverContent>
                      </Popover>
                    </div>
                  </div>
                )}

                {/* Display options */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Display Options</Label>
                  <div className="flex items-center gap-4 flex-wrap">
                    {onToggleLegend && (
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="show-legend"
                          checked={showLegend}
                          onCheckedChange={onToggleLegend}
                        />
                        <Label htmlFor="show-legend" className="text-sm">
                          Show Legend
                        </Label>
                      </div>
                    )}
                    
                    {onToggleGrid && (
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="show-grid"
                          checked={showGrid}
                          onCheckedChange={onToggleGrid}
                        />
                        <Label htmlFor="show-grid" className="text-sm">
                          Show Grid
                        </Label>
                      </div>
                    )}
                    
                    {onToggleTooltips && (
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="show-tooltips"
                          checked={showTooltips}
                          onCheckedChange={onToggleTooltips}
                        />
                        <Label htmlFor="show-tooltips" className="text-sm">
                          Show Tooltips
                        </Label>
                      </div>
                    )}
                  </div>
                </div>

                {/* Filters */}
                {filters.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-medium">Filters</Label>
                      {activeFilters.length > 0 && (
                        <Button
                          onClick={clearAllFilters}
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs"
                        >
                          <X className="h-3 w-3 mr-1" />
                          Clear all
                        </Button>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filters.map(filter => (
                        <div key={filter.id} className="space-y-1">
                          <Label className="text-xs text-muted-foreground">
                            {filter.label}
                          </Label>
                          {renderFilter(filter)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Applied filters summary */}
                {activeFilters.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Active Filters</Label>
                    <div className="flex items-center gap-2 flex-wrap">
                      {activeFilters.map(filterId => {
                        const filter = filters.find(f => f.id === filterId)
                        if (!filter) return null
                        
                        return (
                          <Badge key={filterId} variant="secondary" className="text-xs">
                            {filter.label}: {String(filter.value)}
                            <Button
                              onClick={() => handleFilterChange(filterId, null)}
                              variant="ghost"
                              size="sm"
                              className="h-4 w-4 p-0 ml-1 hover:bg-transparent"
                            >
                              <X className="h-2 w-2" />
                            </Button>
                          </Badge>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}

// Pharmaceutical preset filters
export const PharmacyFilters = {
  inventoryFilters: [
    {
      id: 'category',
      label: 'Category',
      type: 'select' as const,
      value: '',
      options: [
        { label: 'All Categories', value: '' },
        { label: 'Antibiotics', value: 'antibiotics' },
        { label: 'Pain Relief', value: 'pain-relief' },
        { label: 'Vaccines', value: 'vaccines' },
        { label: 'Cardiovascular', value: 'cardiovascular' },
        { label: 'Diabetes', value: 'diabetes' }
      ]
    },
    {
      id: 'supplier',
      label: 'Supplier',
      type: 'select' as const,
      value: '',
      options: [
        { label: 'All Suppliers', value: '' },
        { label: 'PharmaCorp', value: 'pharmacorp' },
        { label: 'MediSupply', value: 'medisupply' },
        { label: 'HealthSource', value: 'healthsource' }
      ]
    },
    {
      id: 'stock-level',
      label: 'Stock Level',
      type: 'select' as const,
      value: '',
      options: [
        { label: 'All Levels', value: '' },
        { label: 'In Stock', value: 'in-stock' },
        { label: 'Low Stock', value: 'low-stock' },
        { label: 'Critical', value: 'critical' },
        { label: 'Out of Stock', value: 'out-of-stock' }
      ]
    },
    {
      id: 'search',
      label: 'Search',
      type: 'text' as const,
      value: '',
      placeholder: 'Search medications...'
    }
  ],

  chartTypes: [
    {
      id: 'bar',
      label: 'Bar Chart',
      icon: BarChart3,
      active: false
    },
    {
      id: 'line',
      label: 'Line Chart',
      icon: LineChart,
      active: true
    },
    {
      id: 'area',
      label: 'Area Chart',
      icon: TrendingUp,
      active: false
    },
    {
      id: 'pie',
      label: 'Pie Chart',
      icon: PieChart,
      active: false
    }
  ]
}