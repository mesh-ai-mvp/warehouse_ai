import React from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, Clock, AlertCircle, XCircle } from "lucide-react"

interface TimelineItem {
  id: string
  title: string
  status: "completed" | "current" | "pending" | "cancelled"
  timestamp?: string | null | undefined
  description?: string
}

interface StatusTimelineProps {
  items: TimelineItem[]
  className?: string
}

const getStatusIcon = (status: TimelineItem["status"]) => {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-4 w-4 text-green-600" />
    case "current":
      return <Clock className="h-4 w-4 text-blue-600" />
    case "pending":
      return <AlertCircle className="h-4 w-4 text-yellow-600" />
    case "cancelled":
      return <XCircle className="h-4 w-4 text-red-600" />
  }
}

const getStatusBadge = (status: TimelineItem["status"]) => {
  switch (status) {
    case "completed":
      return <Badge variant="default" className="text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30">Completed</Badge>
    case "current":
      return <Badge variant="default" className="text-blue-700 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30">In Progress</Badge>
    case "pending":
      return <Badge variant="secondary" className="text-yellow-700 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30">Pending</Badge>
    case "cancelled":
      return <Badge variant="destructive" className="text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30">Cancelled</Badge>
  }
}

export function StatusTimeline({ items, className }: StatusTimelineProps) {
  return (
    <div className={cn("space-y-6", className)}>
      {items.map((item, index) => (
        <div key={item.id} className="relative flex items-start space-x-3">
          {/* Timeline line */}
          {index < items.length - 1 && (
            <div className="absolute left-3 top-8 h-6 w-0.5 bg-border" />
          )}
          
          {/* Status icon */}
          <div className={cn(
            "flex h-6 w-6 items-center justify-center rounded-full border-2",
            item.status === "completed" && "border-green-600 bg-green-50 dark:bg-green-950",
            item.status === "current" && "border-blue-600 bg-blue-50 dark:bg-blue-950", 
            item.status === "pending" && "border-yellow-600 bg-yellow-50 dark:bg-yellow-950",
            item.status === "cancelled" && "border-red-600 bg-red-50 dark:bg-red-950"
          )}>
            {getStatusIcon(item.status)}
          </div>

          {/* Content */}
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-foreground">
                {item.title}
              </h4>
              {getStatusBadge(item.status)}
            </div>
            
            {item.timestamp && (
              <p className="text-xs text-muted-foreground">
                {new Date(item.timestamp).toLocaleString()}
              </p>
            )}
            
            {item.description && (
              <p className="text-sm text-muted-foreground">
                {item.description}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}