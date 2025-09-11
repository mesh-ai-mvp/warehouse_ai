'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
  Package,
  Truck,
  CheckCircle,
  Clock,
  AlertCircle,
  Calendar,
  ShoppingCart,
} from 'lucide-react'
import { format, isAfter, isBefore } from 'date-fns'

interface TimelineTask {
  id: string
  title: string
  description?: string
  startDate: Date
  endDate: Date
  status: 'pending' | 'in-progress' | 'completed' | 'delayed'
  type: 'order' | 'delivery'
  progress?: number
  priority?: 'low' | 'medium' | 'high' | 'critical'
  metadata?: {
    supplier?: string
    amount?: number
    items?: number
  }
}

interface DeliveryTimelineProps {
  tasks: TimelineTask[]
  title?: string
  subtitle?: string
  height?: number
  showToday?: boolean
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return CheckCircle
    case 'in-progress':
      return Clock
    case 'delayed':
      return AlertCircle
    default:
      return Clock
  }
}

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'order':
      return ShoppingCart
    case 'delivery':
      return Truck
    default:
      return Package
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'in-progress':
      return 'default'
    case 'delayed':
      return 'destructive'
    default:
      return 'secondary'
  }
}

const getPriorityBadge = (priority: string = 'medium') => {
  const variants = {
    critical: 'destructive',
    high: 'secondary',
    medium: 'outline',
    low: 'outline',
  } as const

  return (
    <Badge variant={variants[priority as keyof typeof variants]} className="text-xs">
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </Badge>
  )
}

export default function DeliveryTimeline({
  tasks,
  title = 'Delivery Timeline',
  subtitle = 'Track purchase orders and delivery schedules',
  height = 400,
  showToday = true,
}: DeliveryTimelineProps) {
  const today = new Date()
  const sortedTasks = [...tasks].sort((a, b) => a.startDate.getTime() - b.startDate.getTime())

  // Calculate overall progress
  const completedTasks = tasks.filter(task => task.status === 'completed').length
  const overallProgress = (completedTasks / tasks.length) * 100

  // Get upcoming and active tasks
  const activeTasks = tasks.filter(
    task =>
      task.status === 'in-progress' ||
      (isAfter(today, task.startDate) && isBefore(today, task.endDate))
  )

  const upcomingTasks = tasks
    .filter(task => isAfter(task.startDate, today) && task.status === 'pending')
    .slice(0, 3)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-lg flex items-center gap-2">
            <Truck className="h-5 w-5 text-blue-600" />
            {title}
          </CardTitle>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {tasks.length} Tasks
          </Badge>
          <Badge variant="success" className="text-xs">
            {completedTasks} Completed
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Overall Progress</span>
            <span className="text-muted-foreground">{overallProgress.toFixed(0)}%</span>
          </div>
          <Progress value={overallProgress} className="h-2" />
        </div>

        <Separator />

        {/* Active Tasks */}
        {activeTasks.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-600" />
              Active Tasks ({activeTasks.length})
            </h3>

            <div className="space-y-3">
              {activeTasks.map(task => {
                const StatusIcon = getStatusIcon(task.status)
                const TypeIcon = getTypeIcon(task.type)

                return (
                  <div key={task.id} className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg">
                    <div className="flex-shrink-0">
                      <div
                        className={`h-8 w-8 rounded-full flex items-center justify-center ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-600'
                            : task.status === 'delayed'
                              ? 'bg-red-100 text-red-600'
                              : 'bg-blue-100 text-blue-600'
                        }`}
                      >
                        <StatusIcon className="h-4 w-4" />
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <TypeIcon className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium text-sm truncate">{task.title}</span>
                        <Badge variant={getStatusColor(task.status) as any} className="text-xs">
                          {task.status.replace('-', ' ')}
                        </Badge>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {format(task.startDate, 'MMM dd')} - {format(task.endDate, 'MMM dd')}
                        </div>
                        {task.metadata?.supplier && <span>Supplier: {task.metadata.supplier}</span>}
                      </div>

                      {task.progress !== undefined && (
                        <div className="mt-2">
                          <Progress value={task.progress} className="h-1" />
                        </div>
                      )}
                    </div>

                    <div className="flex-shrink-0">{getPriorityBadge(task.priority)}</div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {activeTasks.length > 0 && upcomingTasks.length > 0 && <Separator />}

        {/* Upcoming Tasks */}
        {upcomingTasks.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Calendar className="h-4 w-4 text-orange-600" />
              Upcoming Tasks ({upcomingTasks.length})
            </h3>

            <div className="space-y-2">
              {upcomingTasks.map(task => {
                const TypeIcon = getTypeIcon(task.type)
                const daysUntilStart = Math.ceil(
                  (task.startDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
                )

                return (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 p-2 hover:bg-muted/30 rounded-lg transition-colors"
                  >
                    <div className="flex-shrink-0">
                      <div className="h-6 w-6 rounded-full bg-gray-100 flex items-center justify-center">
                        <TypeIcon className="h-3 w-3 text-gray-600" />
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate">{task.title}</span>
                        <Badge variant="outline" className="text-xs">
                          {daysUntilStart === 0
                            ? 'Today'
                            : daysUntilStart === 1
                              ? 'Tomorrow'
                              : `in ${daysUntilStart}d`}
                        </Badge>
                      </div>

                      {task.metadata?.supplier && (
                        <p className="text-xs text-muted-foreground">{task.metadata.supplier}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Today Indicator */}
        {showToday && (
          <div className="flex items-center justify-center p-2 bg-blue-50 dark:bg-blue-950/20 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
              <div className="h-2 w-2 bg-blue-600 rounded-full animate-pulse" />
              <span className="font-medium">Today: {format(today, 'MMMM dd, yyyy')}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
