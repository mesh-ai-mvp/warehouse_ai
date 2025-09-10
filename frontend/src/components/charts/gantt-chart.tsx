import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { format, differenceInDays, startOfDay, addDays, isSameDay } from 'date-fns'
import { 
  Calendar, 
  Clock, 
  Package, 
  Truck, 
  CheckCircle, 
  AlertCircle,
  MoreHorizontal,
  Filter
} from 'lucide-react'

interface GanttTask {
  id: string
  title: string
  description?: string
  startDate: Date
  endDate: Date
  status: 'pending' | 'in-progress' | 'completed' | 'delayed' | 'cancelled'
  progress?: number // 0-100
  assignee?: string
  priority?: 'low' | 'medium' | 'high' | 'critical'
  type?: 'order' | 'delivery' | 'manufacturing' | 'quality-check' | 'custom'
  metadata?: {
    supplier?: string
    amount?: number
    items?: number
  }
}

interface GanttChartProps {
  tasks: GanttTask[]
  title?: string
  subtitle?: string
  showToday?: boolean
  viewMode?: 'days' | 'weeks' | 'months'
  height?: number
  className?: string
  onTaskClick?: (task: GanttTask) => void
  showControls?: boolean
}

const chartVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
}

const taskVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4 }
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'bg-green-500 border-green-600'
    case 'in-progress': return 'bg-blue-500 border-blue-600'
    case 'pending': return 'bg-gray-400 border-gray-500'
    case 'delayed': return 'bg-red-500 border-red-600'
    case 'cancelled': return 'bg-red-200 border-red-300'
    default: return 'bg-gray-400 border-gray-500'
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed': return CheckCircle
    case 'in-progress': return Clock
    case 'pending': return Clock
    case 'delayed': return AlertCircle
    case 'cancelled': return AlertCircle
    default: return Clock
  }
}

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'order': return Package
    case 'delivery': return Truck
    case 'manufacturing': return Package
    case 'quality-check': return CheckCircle
    default: return Package
  }
}

const getPriorityBadge = (priority: string) => {
  switch (priority) {
    case 'critical': return <Badge variant="destructive" className="text-xs">Critical</Badge>
    case 'high': return <Badge variant="secondary" className="text-xs bg-orange-100 text-orange-800">High</Badge>
    case 'medium': return <Badge variant="outline" className="text-xs">Medium</Badge>
    case 'low': return <Badge variant="outline" className="text-xs text-gray-600">Low</Badge>
    default: return null
  }
}

export function GanttChart({
  tasks,
  title = "Project Timeline",
  subtitle,
  showToday = true,
  viewMode = 'days',
  height = 400,
  className,
  onTaskClick,
  showControls = true
}: GanttChartProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true
  })

  const chartData = useMemo(() => {
    if (!tasks.length) return { dates: [], minDate: new Date(), maxDate: new Date(), totalDays: 0 }

    const allDates = tasks.flatMap(task => [task.startDate, task.endDate])
    const minDate = startOfDay(new Date(Math.min(...allDates.map(d => d.getTime()))))
    const maxDate = startOfDay(new Date(Math.max(...allDates.map(d => d.getTime()))))
    
    // Add some padding
    const paddedMinDate = addDays(minDate, -2)
    const paddedMaxDate = addDays(maxDate, 2)
    
    const totalDays = differenceInDays(paddedMaxDate, paddedMinDate) + 1
    
    const dates: Date[] = []
    for (let i = 0; i < totalDays; i++) {
      dates.push(addDays(paddedMinDate, i))
    }

    return { dates, minDate: paddedMinDate, maxDate: paddedMaxDate, totalDays }
  }, [tasks])

  const getTaskPosition = (task: GanttTask) => {
    const taskStart = differenceInDays(startOfDay(task.startDate), chartData.minDate)
    const taskDuration = differenceInDays(startOfDay(task.endDate), startOfDay(task.startDate)) + 1
    
    const leftPercent = (taskStart / chartData.totalDays) * 100
    const widthPercent = (taskDuration / chartData.totalDays) * 100
    
    return { left: `${leftPercent}%`, width: `${widthPercent}%` }
  }

  const today = new Date()
  const todayPosition = chartData.dates.findIndex(date => isSameDay(date, today))
  const todayPercent = todayPosition >= 0 ? (todayPosition / chartData.totalDays) * 100 : -1

  return (
    <motion.div
      ref={ref}
      variants={chartVariants}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      className={className}
    >
      <Card className="overflow-hidden">
        {(title || subtitle || showControls) && (
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div className="space-y-1">
              {title && <CardTitle className="text-lg">{title}</CardTitle>}
              {subtitle && (
                <p className="text-sm text-muted-foreground">{subtitle}</p>
              )}
            </div>
            
            {showControls && (
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">
                  {tasks.length} Tasks
                </Badge>
                
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <Filter className="h-4 w-4" />
                </Button>
                
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardHeader>
        )}
        
        <CardContent className={title || subtitle || showControls ? "" : "pt-6"}>
          <div className="space-y-4">
            {/* Time header */}
            <div className="relative">
              <div className="grid grid-cols-12 gap-1 text-xs text-muted-foreground mb-2">
                {chartData.dates
                  .filter((_, index) => index % Math.max(1, Math.floor(chartData.totalDays / 12)) === 0)
                  .slice(0, 12)
                  .map((date, index) => (
                    <div key={index} className="text-center">
                      {format(date, viewMode === 'days' ? 'MMM dd' : 'MMM')}
                    </div>
                  ))
                }
              </div>
              
              <div className="relative h-4 bg-muted/30 rounded-sm mb-4">
                {/* Today indicator */}
                {showToday && todayPercent >= 0 && (
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
                    style={{ left: `${todayPercent}%` }}
                  >
                    <div className="absolute -top-2 -left-4 w-8 h-0.5 bg-red-500" />
                    <div className="absolute -top-6 -left-6 text-xs text-red-600 font-medium">
                      Today
                    </div>
                  </div>
                )}
                
                {/* Week/Month markers */}
                <div className="absolute inset-0">
                  {chartData.dates
                    .filter((date, index) => 
                      viewMode === 'days' 
                        ? date.getDay() === 0 // Sunday
                        : date.getDate() === 1 // First of month
                    )
                    .map((date, index) => {
                      const position = (chartData.dates.indexOf(date) / chartData.totalDays) * 100
                      return (
                        <div
                          key={index}
                          className="absolute top-0 bottom-0 w-px bg-border"
                          style={{ left: `${position}%` }}
                        />
                      )
                    })
                  }
                </div>
              </div>
            </div>

            {/* Tasks */}
            <div className="space-y-3" style={{ minHeight: height }}>
              {tasks.map((task, index) => {
                const StatusIcon = getStatusIcon(task.status)
                const TypeIcon = getTypeIcon(task.type || 'order')
                const position = getTaskPosition(task)
                
                return (
                  <motion.div
                    key={task.id}
                    variants={taskVariants}
                    custom={index}
                    className="group"
                  >
                    <div className="flex items-center gap-4">
                      {/* Task info */}
                      <div className="w-48 flex-shrink-0">
                        <div className="flex items-center gap-2 mb-1">
                          <TypeIcon className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium text-sm truncate">
                            {task.title}
                          </span>
                          {getPriorityBadge(task.priority || 'medium')}
                        </div>
                        
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <StatusIcon className="h-3 w-3" />
                          <span className="capitalize">{task.status.replace('-', ' ')}</span>
                          {task.assignee && (
                            <>
                              <span>•</span>
                              <span>{task.assignee}</span>
                            </>
                          )}
                        </div>
                        
                        {task.description && (
                          <p className="text-xs text-muted-foreground mt-1 truncate">
                            {task.description}
                          </p>
                        )}
                      </div>

                      {/* Timeline bar */}
                      <div className="flex-1 relative h-8">
                        <div className="absolute inset-y-0 left-0 right-0 bg-muted/20 rounded" />
                        
                        <motion.div
                          className={cn(
                            "absolute inset-y-1 rounded border-l-4 cursor-pointer",
                            "transition-all duration-200 hover:shadow-md group-hover:scale-105",
                            getStatusColor(task.status)
                          )}
                          style={position}
                          onClick={() => onTaskClick?.(task)}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          {/* Progress bar */}
                          {task.progress !== undefined && (
                            <div 
                              className="absolute inset-0 bg-white/20 rounded-r"
                              style={{ width: `${task.progress}%` }}
                            />
                          )}
                          
                          {/* Task content */}
                          <div className="absolute inset-0 flex items-center justify-between px-2 text-white text-xs font-medium">
                            <span className="truncate">{task.title}</span>
                            {task.progress !== undefined && (
                              <span>{task.progress}%</span>
                            )}
                          </div>
                        </motion.div>

                        {/* Metadata tooltip */}
                        <div className="absolute left-0 top-full mt-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                          <div className="bg-popover border rounded-lg shadow-lg p-3 min-w-64">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="font-medium">{task.title}</h4>
                                <Badge variant="outline" className="text-xs capitalize">
                                  {task.status.replace('-', ' ')}
                                </Badge>
                              </div>
                              
                              <div className="text-sm text-muted-foreground space-y-1">
                                <div className="flex items-center gap-2">
                                  <Calendar className="h-3 w-3" />
                                  <span>
                                    {format(task.startDate, 'MMM dd')} - {format(task.endDate, 'MMM dd')}
                                  </span>
                                </div>
                                
                                {task.metadata?.supplier && (
                                  <div>Supplier: {task.metadata.supplier}</div>
                                )}
                                
                                {task.metadata?.amount && (
                                  <div>Amount: ${task.metadata.amount.toLocaleString()}</div>
                                )}
                                
                                {task.metadata?.items && (
                                  <div>Items: {task.metadata.items}</div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      {/* Duration */}
                      <div className="w-16 flex-shrink-0 text-right">
                        <div className="text-xs text-muted-foreground">
                          {differenceInDays(task.endDate, task.startDate) + 1}d
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>

            {/* Legend */}
            <div className="pt-4 border-t">
              <div className="flex items-center gap-6 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded" />
                  <span>In Progress</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded" />
                  <span>Completed</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-gray-400 rounded" />
                  <span>Pending</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-500 rounded" />
                  <span>Delayed</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Pharmaceutical preset data generator
export const PharmaGanttPresets = {
  generateDeliveryTimeline: (orders: any[]) => {
    return orders.map((order, index) => ({
      id: order.id,
      title: `PO #${order.id}`,
      description: `${order.line_items?.length || 0} items from ${order.supplier}`,
      startDate: new Date(order.order_date || Date.now()),
      endDate: new Date(order.delivery_date || Date.now() + 7 * 24 * 60 * 60 * 1000),
      status: order.status,
      progress: order.status === 'completed' ? 100 : 
                order.status === 'in-progress' ? 60 : 0,
      assignee: order.buyer_name,
      priority: order.priority || 'medium',
      type: 'delivery',
      metadata: {
        supplier: order.supplier,
        amount: order.total_amount,
        items: order.line_items?.length || 0
      }
    }))
  },

  generateManufacturingSchedule: () => [
    {
      id: 'mfg-001',
      title: 'Aspirin Production Batch #204',
      description: '10,000 units production run',
      startDate: new Date(),
      endDate: addDays(new Date(), 5),
      status: 'in-progress',
      progress: 75,
      priority: 'high',
      type: 'manufacturing'
    },
    {
      id: 'mfg-002', 
      title: 'Ibuprofen Quality Control',
      description: 'QC testing for batch #198',
      startDate: addDays(new Date(), 3),
      endDate: addDays(new Date(), 4),
      status: 'pending',
      progress: 0,
      priority: 'medium',
      type: 'quality-check'
    }
  ]
}