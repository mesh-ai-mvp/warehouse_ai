import { type ComponentType } from 'react'
import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface ReUIStatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
    period?: string
  }
  icon?: ComponentType<{ className?: string }>
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'info'
  className?: string
  delay?: number
}

const cardVariants = {
  hidden: {
    opacity: 0,
    y: 20,
    scale: 0.95,
  },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.6,
      delay: delay * 0.1,
      ease: [0.22, 1, 0.36, 1],
    },
  }),
}

const valueVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.8,
      delay: 0.3,
      ease: 'easeOut',
    },
  },
}

const getTrendIcon = (direction: string) => {
  switch (direction) {
    case 'up':
      return TrendingUp
    case 'down':
      return TrendingDown
    default:
      return Minus
  }
}

const getTrendColor = (direction: string) => {
  switch (direction) {
    case 'up':
      return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/50'
    case 'down':
      return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50'
    default:
      return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-950/50'
  }
}

const getVariantStyles = (variant: string) => {
  switch (variant) {
    case 'success':
      return 'border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20'
    case 'warning':
      return 'border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20'
    case 'destructive':
      return 'border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-950/20'
    case 'info':
      return 'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20'
    default:
      return 'border-border bg-card'
  }
}

export function ReUIStatCard({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  variant = 'default',
  className,
  delay = 0,
}: ReUIStatCardProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true,
  })

  const TrendIcon = trend ? getTrendIcon(trend.direction) : null

  return (
    <motion.div
      ref={ref}
      custom={delay}
      variants={cardVariants}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      whileHover={{ y: -5, transition: { duration: 0.2 } }}
      className={className}
    >
      <Card
        className={cn(
          'relative overflow-hidden transition-all duration-300 hover:shadow-lg',
          getVariantStyles(variant)
        )}
      >
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                {title}
              </p>

              <motion.div
                variants={valueVariants}
                initial="hidden"
                animate={inView ? 'visible' : 'hidden'}
                className="space-y-1"
              >
                <p className="text-3xl font-bold tracking-tight">{value}</p>

                {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
              </motion.div>

              {trend && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={inView ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                  transition={{ delay: 0.5, duration: 0.4 }}
                  className="flex items-center gap-2"
                >
                  <div
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                      getTrendColor(trend.direction)
                    )}
                  >
                    {TrendIcon && <TrendIcon className="h-3 w-3" />}
                    <span>{Math.abs(trend.value)}%</span>
                  </div>

                  {trend.period && (
                    <span className="text-xs text-muted-foreground">vs {trend.period}</span>
                  )}
                </motion.div>
              )}
            </div>

            {Icon && (
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={inView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.5 }}
                transition={{ delay: 0.4, duration: 0.5 }}
                className="p-3 rounded-full bg-primary/10 text-primary"
              >
                <Icon className="h-6 w-6" />
              </motion.div>
            )}
          </div>

          {/* Decorative gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-primary/5 pointer-events-none" />
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Alternative compact style
interface ReUIStatCardCompactProps {
  title: string
  value: string | number
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
    period?: string
  }
  icon?: ComponentType<{ className?: string }>
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'info'
  className?: string
  delay?: number
}

export function ReUIStatCardCompact({
  title,
  value,
  trend,
  icon: Icon,
  variant = 'default',
  className,
  delay = 0,
}: ReUIStatCardCompactProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true,
  })

  const TrendIcon = trend ? getTrendIcon(trend.direction) : null

  return (
    <motion.div
      ref={ref}
      custom={delay}
      variants={cardVariants}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
      className={className}
    >
      <Card
        className={cn('transition-all duration-300 hover:shadow-md', getVariantStyles(variant))}
      >
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {title}
              </p>

              <motion.p
                variants={valueVariants}
                initial="hidden"
                animate={inView ? 'visible' : 'hidden'}
                className="text-xl font-bold"
              >
                {value}
              </motion.p>

              {trend && (
                <div
                  className={cn(
                    'inline-flex items-center gap-1 text-xs',
                    trend.direction === 'up'
                      ? 'text-green-600'
                      : trend.direction === 'down'
                        ? 'text-red-600'
                        : 'text-gray-600'
                  )}
                >
                  {TrendIcon && <TrendIcon className="h-3 w-3" />}
                  <span>{Math.abs(trend.value)}%</span>
                </div>
              )}
            </div>

            {Icon && <Icon className="h-8 w-8 text-primary/60" />}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Grid layout for multiple stats
export function ReUIStatsGrid({
  stats,
  columns = 4,
  className,
}: {
  stats: ReUIStatCardProps[]
  columns?: number
  className?: string
}) {
  return (
    <div
      className={cn(
        'grid gap-6',
        columns === 2 && 'grid-cols-1 md:grid-cols-2',
        columns === 3 && 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
        columns === 4 && 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
        className
      )}
    >
      {stats.map((stat, index) => (
        <ReUIStatCard key={index} {...stat} delay={index} />
      ))}
    </div>
  )
}

// Pharmaceutical-specific presets
export const PharmacyStatPresets = {
  totalMedications: (count: number) => ({
    title: 'Total Medications',
    value: count.toLocaleString(),
    subtitle: 'Active inventory items',
    trend: { value: 3.2, direction: 'up' as const, period: 'last month' },
    variant: 'info' as const,
  }),

  lowStockAlerts: (count: number, critical: number) => ({
    title: 'Low Stock Alerts',
    value: count,
    subtitle: `${critical} critical items`,
    trend: { value: 12, direction: 'up' as const, period: 'yesterday' },
    variant: count > 0 ? ('warning' as const) : ('success' as const),
  }),

  inventoryValue: (value: number) => ({
    title: 'Inventory Value',
    value: `$${value.toLocaleString()}`,
    subtitle: 'Current market value',
    trend: { value: 5.8, direction: 'up' as const, period: 'last quarter' },
    variant: 'success' as const,
  }),

  ordersToday: (count: number) => ({
    title: 'Orders Today',
    value: count,
    subtitle: 'Purchase orders created',
    trend: { value: 8.3, direction: 'up' as const, period: 'yesterday' },
    variant: 'default' as const,
  }),

  expiringMedications: (count: number) => ({
    title: 'Expiring Soon',
    value: count,
    subtitle: 'Within 30 days',
    trend: { value: 15, direction: 'down' as const, period: 'last week' },
    variant: count > 0 ? ('destructive' as const) : ('success' as const),
  }),
}
