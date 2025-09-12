'use client'

import { Calendar, Clock, TrendingUp } from 'lucide-react'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'

export type TimeScale = 'weekly' | 'monthly' | 'quarterly'

interface TimeScaleSelectorProps {
  value: TimeScale
  onValueChange: (value: TimeScale) => void
  className?: string
}

export function TimeScaleSelector({ value, onValueChange, className }: TimeScaleSelectorProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span className="text-sm font-medium text-muted-foreground">Time Scale:</span>
      <ToggleGroup 
        type="single" 
        value={value} 
        onValueChange={(newValue) => newValue && onValueChange(newValue as TimeScale)}
        className="bg-background"
      >
        <ToggleGroupItem 
          value="weekly" 
          aria-label="Weekly view"
          className="text-xs px-3 py-1.5 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
        >
          <Calendar className="h-3 w-3 mr-1.5" />
          Weekly
        </ToggleGroupItem>
        <ToggleGroupItem 
          value="monthly" 
          aria-label="Monthly view"
          className="text-xs px-3 py-1.5 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
        >
          <Clock className="h-3 w-3 mr-1.5" />
          Monthly
        </ToggleGroupItem>
        <ToggleGroupItem 
          value="quarterly" 
          aria-label="Quarterly view"
          className="text-xs px-3 py-1.5 data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
        >
          <TrendingUp className="h-3 w-3 mr-1.5" />
          Quarterly
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  )
}

// Helper functions to get time scale configuration
export function getTimeScaleConfig(timeScale: TimeScale) {
  switch (timeScale) {
    case 'weekly':
      return {
        days: 14,
        label: 'Weekly',
        aggregation: 'daily',
        format: 'MMM dd'
      }
    case 'monthly':
      return {
        days: 60,
        label: 'Monthly', 
        aggregation: 'weekly',
        format: 'MMM dd'
      }
    case 'quarterly':
      return {
        days: 90,
        label: 'Quarterly',
        aggregation: 'monthly', 
        format: 'MMM yyyy'
      }
  }
}