import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useInView } from 'react-intersection-observer'
import { useEffect, useState } from 'react'

interface AnimatedStatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
    label?: string
  }
  icon?: React.ComponentType<any>
  variant?: 'default' | 'success' | 'warning' | 'danger'
  delay?: number
  className?: string
}

const cardVariants = {
  hidden: {
    opacity: 0,
    y: 50,
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

const iconVariants = {
  hidden: { scale: 0, rotate: -180 },
  visible: {
    scale: 1,
    rotate: 0,
    transition: {
      duration: 0.5,
      delay: 0.3,
      type: 'spring',
      stiffness: 200,
      damping: 10,
    },
  },
}

const valueVariants = {
  hidden: { opacity: 0, scale: 0.8 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.4,
      delay: 0.4,
      ease: [0.22, 1, 0.36, 1],
    },
  },
}

const trendVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.3,
      delay: 0.6,
      ease: 'easeOut',
    },
  },
}

export function AnimatedStatCard({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  variant = 'default',
  delay = 0,
  className = '',
}: AnimatedStatCardProps) {
  const { ref, inView } = useInView({
    threshold: 0.1,
    triggerOnce: true,
  })

  const [animatedValue, setAnimatedValue] = useState(0)

  // Animate number counting
  useEffect(() => {
    if (inView && typeof value === 'number') {
      let start = 0
      const end = value
      const duration = 1000 // 1 second
      const increment = end / (duration / 16) // 60fps

      const timer = setInterval(() => {
        start += increment
        if (start >= end) {
          setAnimatedValue(end)
          clearInterval(timer)
        } else {
          setAnimatedValue(Math.floor(start))
        }
      }, 16)

      return () => clearInterval(timer)
    }
  }, [inView, value])

  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'border-green-200 bg-green-50/50 hover:bg-green-50'
      case 'warning':
        return 'border-yellow-200 bg-yellow-50/50 hover:bg-yellow-50'
      case 'danger':
        return 'border-red-200 bg-red-50/50 hover:bg-red-50'
      default:
        return 'border-border bg-card hover:bg-muted/50'
    }
  }

  const getTrendIcon = () => {
    if (!trend) return null

    switch (trend.direction) {
      case 'up':
        return <TrendingUp className="h-3 w-3 text-green-500" />
      case 'down':
        return <TrendingDown className="h-3 w-3 text-red-500" />
      default:
        return <Minus className="h-3 w-3 text-gray-500" />
    }
  }

  const getTrendColor = () => {
    if (!trend) return 'text-muted-foreground'

    switch (trend.direction) {
      case 'up':
        return 'text-green-600'
      case 'down':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <motion.div
      ref={ref}
      custom={delay}
      variants={cardVariants}
      initial="hidden"
      animate={inView ? 'visible' : 'hidden'}
      whileHover={{
        scale: 1.02,
        transition: { duration: 0.2 },
      }}
      whileTap={{ scale: 0.98 }}
      className={className}
    >
      <Card className={`cursor-pointer transition-colors duration-200 ${getVariantStyles()}`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
          {Icon && (
            <motion.div
              variants={iconVariants}
              initial="hidden"
              animate={inView ? 'visible' : 'hidden'}
            >
              <Icon className="h-4 w-4 text-muted-foreground" />
            </motion.div>
          )}
        </CardHeader>
        <CardContent>
          <motion.div
            variants={valueVariants}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
            className="text-2xl font-bold tracking-tight"
          >
            {typeof value === 'number' ? animatedValue.toLocaleString() : value}
          </motion.div>

          {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}

          {trend && (
            <motion.div
              variants={trendVariants}
              initial="hidden"
              animate={inView ? 'visible' : 'hidden'}
              className="flex items-center gap-1 mt-2"
            >
              {getTrendIcon()}
              <span className={`text-xs font-medium ${getTrendColor()}`}>
                {trend.value > 0 ? '+' : ''}
                {trend.value}%{trend.label && ` ${trend.label}`}
              </span>
              {trend.direction === 'up' && (
                <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                  Good
                </Badge>
              )}
              {trend.direction === 'down' && (
                <Badge variant="secondary" className="text-xs bg-red-100 text-red-700">
                  Alert
                </Badge>
              )}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
