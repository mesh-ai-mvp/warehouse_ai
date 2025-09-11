import { motion, useAnimation } from 'framer-motion'
import React, { ReactNode, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface AnimatedCardProps {
  children: ReactNode
  className?: string
  hoverScale?: number
  glowColor?: string
  delay?: number
  onClick?: () => void
}

export function AnimatedCard({
  children,
  className,
  hoverScale = 1.02,
  glowColor = 'rgba(59, 130, 246, 0.15)',
  delay = 0,
  onClick,
}: AnimatedCardProps) {
  const [isHovered, setIsHovered] = useState(false)
  const controls = useAnimation()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{
        scale: hoverScale,
        boxShadow: `0 10px 30px ${glowColor}`,
        transition: { duration: 0.2 },
      }}
      whileTap={{ scale: 0.98 }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn('cursor-pointer', className)}
      onClick={onClick}
    >
      <Card className="relative overflow-hidden border transition-all duration-300 hover:border-blue-300 dark:hover:border-blue-700">
        {/* Animated background gradient */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered ? 0.1 : 0 }}
          transition={{ duration: 0.3 }}
          className="absolute inset-0 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500"
        />

        {/* Shimmer effect */}
        <motion.div
          initial={{ x: '-100%', opacity: 0 }}
          animate={{
            x: isHovered ? '100%' : '-100%',
            opacity: isHovered ? 0.3 : 0,
          }}
          transition={{ duration: 0.6, ease: 'easeInOut' }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent -skew-x-12"
        />

        <div className="relative z-10">{children}</div>
      </Card>
    </motion.div>
  )
}

interface StatCardProps {
  title: string
  value: string
  subtitle?: string
  icon?: React.ComponentType<{ className?: string }>
  trend?: {
    value: number
    direction: 'up' | 'down'
  }
  delay?: number
  variant?: 'default' | 'success' | 'warning' | 'destructive'
}

export function AnimatedStatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  delay = 0,
  variant = 'default',
}: StatCardProps) {
  const [counter, setCounter] = useState(0)
  const numericValue = parseInt(value.replace(/[^0-9]/g, '')) || 0

  const variantStyles = {
    default: 'border-blue-200 dark:border-blue-800',
    success: 'border-green-200 dark:border-green-800',
    warning: 'border-yellow-200 dark:border-yellow-800',
    destructive: 'border-red-200 dark:border-red-800',
  }

  const glowColors = {
    default: 'rgba(59, 130, 246, 0.15)',
    success: 'rgba(34, 197, 94, 0.15)',
    warning: 'rgba(245, 158, 11, 0.15)',
    destructive: 'rgba(239, 68, 68, 0.15)',
  }

  return (
    <AnimatedCard delay={delay} glowColor={glowColors[variant]} className={variantStyles[variant]}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && (
          <div className="opacity-50">{React.createElement(icon, { className: 'h-4 w-4' })}</div>
        )}
      </CardHeader>
      <CardContent>
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, delay: delay + 0.2 }}
          className="text-2xl font-bold"
        >
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: delay + 0.4 }}
          >
            {value}
          </motion.span>
        </motion.div>

        {subtitle && (
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: delay + 0.6 }}
            className="text-xs text-muted-foreground mt-1"
          >
            {subtitle}
          </motion.p>
        )}

        {trend && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, delay: delay + 0.8 }}
            className={cn(
              'flex items-center text-xs mt-2',
              trend.direction === 'up' ? 'text-green-600' : 'text-red-600'
            )}
          >
            <motion.span
              animate={{ y: trend.direction === 'up' ? [-2, 0, -2] : [2, 0, 2] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            >
              {trend.direction === 'up' ? '↗' : '↘'}
            </motion.span>
            <span className="ml-1">{Math.abs(trend.value)}%</span>
          </motion.div>
        )}
      </CardContent>
    </AnimatedCard>
  )
}

// Pulse loading card for skeleton states
export function PulseCard({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay }}
    >
      <Card>
        <CardHeader>
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-3/4"
          />
        </CardHeader>
        <CardContent>
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
            className="h-8 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-2"
          />
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.4 }}
            className="h-3 bg-gray-300 dark:bg-gray-600 rounded w-full"
          />
        </CardContent>
      </Card>
    </motion.div>
  )
}
