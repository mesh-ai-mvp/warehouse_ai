import { ReactNode } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface StatCardProps {
  title: string
  value: string | number
  icon?: ReactNode
  trend?: number
  description?: string
  variant?: "default" | "success" | "warning" | "destructive"
}

export function StatCard({ 
  title, 
  value, 
  icon, 
  trend, 
  description,
  variant = "default" 
}: StatCardProps) {
  const getTrendColor = () => {
    if (trend === undefined) return ""
    return trend >= 0 ? "text-green-600" : "text-red-600"
  }

  const getTrendIcon = () => {
    if (trend === undefined) return null
    return trend >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />
  }

  const getVariantStyles = () => {
    switch (variant) {
      case "success":
        return "border-green-200 dark:border-green-800"
      case "warning":
        return "border-amber-200 dark:border-amber-800"
      case "destructive":
        return "border-red-200 dark:border-red-800"
      default:
        return ""
    }
  }

  return (
    <Card className={cn("transition-all hover:shadow-md", getVariantStyles())}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">{value}</p>
            {(trend !== undefined || description) && (
              <div className="flex items-center gap-2 text-sm">
                {trend !== undefined && (
                  <div className={cn("flex items-center gap-1", getTrendColor())}>
                    {getTrendIcon()}
                    <span>{Math.abs(trend)}%</span>
                  </div>
                )}
                {description && (
                  <span className="text-muted-foreground">{description}</span>
                )}
              </div>
            )}
          </div>
          {icon && (
            <div className="text-primary">
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}