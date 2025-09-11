import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'

// Analytics hooks
export function useAnalyticsKPIs(timeRange: string = '30d', filters: any = {}) {
  return useQuery({
    queryKey: ['analytics', 'kpis', timeRange, filters],
    queryFn: () => apiClient.getAnalyticsKPIs(timeRange, filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
  })
}

export function useConsumptionTrends(timeRange: string = '6m', medicationId?: string) {
  return useQuery({
    queryKey: ['analytics', 'consumption-trends', timeRange, medicationId],
    queryFn: () => apiClient.getConsumptionTrends(timeRange, medicationId),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000, // 15 minutes
  })
}

export function useSupplierPerformance(timeRange: string = '3m') {
  return useQuery({
    queryKey: ['analytics', 'supplier-performance', timeRange],
    queryFn: () => apiClient.getSupplierPerformanceAnalytics(timeRange),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  })
}

export function useCategoryBreakdown() {
  return useQuery({
    queryKey: ['analytics', 'category-breakdown'],
    queryFn: () => apiClient.getCategoryBreakdown(),
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 30 * 60 * 1000, // 30 minutes
  })
}

export function useStockAlerts() {
  return useQuery({
    queryKey: ['analytics', 'stock-alerts'],
    queryFn: () => apiClient.getStockAlerts(),
    staleTime: 2 * 60 * 1000, // 2 minutes for critical data
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })
}

// Reports hooks
export function useReportTemplates() {
  return useQuery({
    queryKey: ['reports', 'templates'],
    queryFn: () => apiClient.getReportTemplates(),
    staleTime: 10 * 60 * 1000,
  })
}

export function useCreateReportTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (template: any) => apiClient.createReportTemplate(template),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', 'templates'] })
    },
  })
}

export function useRunReport() {
  return useMutation({
    mutationFn: ({ templateId, parameters }: { templateId: string; parameters?: any }) =>
      apiClient.runReport(templateId, parameters),
  })
}

export function useExportReport() {
  return useMutation({
    mutationFn: async ({
      templateId,
      format,
      parameters,
    }: {
      templateId: string
      format: string
      parameters?: any
    }) => {
      const blob = await apiClient.exportReport(templateId, format, parameters)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `report-${templateId}-${Date.now()}.${format.toLowerCase()}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      return blob
    },
  })
}

export function useReportHistory(filters: { limit?: number; offset?: number } = {}) {
  return useQuery({
    queryKey: ['reports', 'history', filters],
    queryFn: () => apiClient.getReportHistory(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDeleteReportTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (templateId: string) => apiClient.deleteReportTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', 'templates'] })
      queryClient.invalidateQueries({ queryKey: ['reports', 'history'] })
    },
  })
}

// Combined analytics hook for dashboard
// New analytics hooks for updated charts
export function useStockLevelTrends(medicationId?: number, timeRange: string = '7d') {
  return useQuery({
    queryKey: ['analytics', 'stock-level-trends', medicationId, timeRange],
    queryFn: () => apiClient.getStockLevelTrends(medicationId, timeRange),
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useConsumptionForecast(medicationId?: number, forecastDays: number = 7) {
  return useQuery({
    queryKey: ['analytics', 'consumption-forecast', medicationId, forecastDays],
    queryFn: () => apiClient.getConsumptionForecast(medicationId, forecastDays),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000,
  })
}

export function useDeliveryTimeline() {
  return useQuery({
    queryKey: ['analytics', 'delivery-timeline'],
    queryFn: () => apiClient.getDeliveryTimeline(),
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 15 * 60 * 1000,
  })
}

export function useAnalyticsDashboard(timeRange: string = '30d', filters: any = {}) {
  const kpis = useAnalyticsKPIs(timeRange, filters)
  const consumption = useConsumptionTrends(timeRange)
  const suppliers = useSupplierPerformance(timeRange)
  const categories = useCategoryBreakdown()
  const alerts = useStockAlerts()
  const stockTrends = useStockLevelTrends()
  const forecast = useConsumptionForecast()
  const timeline = useDeliveryTimeline()

  return {
    kpis,
    consumption,
    suppliers,
    categories,
    alerts,
    stockTrends,
    forecast,
    timeline,
    isLoading:
      kpis.isLoading ||
      consumption.isLoading ||
      suppliers.isLoading ||
      categories.isLoading ||
      alerts.isLoading ||
      stockTrends.isLoading ||
      forecast.isLoading ||
      timeline.isLoading,
    isError:
      kpis.isError ||
      consumption.isError ||
      suppliers.isError ||
      categories.isError ||
      alerts.isError ||
      stockTrends.isError ||
      forecast.isError ||
      timeline.isError,
    refetchAll: () => {
      kpis.refetch()
      consumption.refetch()
      suppliers.refetch()
      categories.refetch()
      alerts.refetch()
      stockTrends.refetch()
      forecast.refetch()
      timeline.refetch()
    },
  }
}
