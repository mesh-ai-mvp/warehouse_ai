import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'

export interface AIPOGenerationParams {
  store_ids?: number[]
  category_filter?: string
  days_forecast?: number
  urgency_threshold?: number
}

export interface AIPOGenerationResult {
  session_id: string
  estimated_total: number
  supplier_suggestion: string
  reasoning: string
  items: {
    medication_id: number
    medication_name?: string
    suggested_quantity: number
    reason: string
    priority: 'high' | 'medium' | 'low'
  }[]
}

export interface AIPOStatus {
  session_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  result?: AIPOGenerationResult
}

export function useAIPOGeneration() {
  const [currentSession, setCurrentSession] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<'idle' | 'generating' | 'completed' | 'error'>('idle')
  const [result, setResult] = useState<AIPOGenerationResult | null>(null)

  const queryClient = useQueryClient()

  const generatePO = useMutation({
    mutationFn: async (params: AIPOGenerationParams) => {
      setStatus('generating')
      setProgress(0)
      setResult(null)

      try {
        // Map UI params to backend request
        const request = {
          days_forecast: params.days_forecast ?? 30,
          urgency_threshold: params.urgency_threshold ?? 0.5,
          category_filter: params.category_filter,
          store_ids: params.store_ids,
          // allow backend to auto-select meds based on urgency if none provided
          medication_ids: [],
        } as any

        // Start AI PO generation (backend async kickoff)
        const response = await apiClient.generateAIPO(request)

        setCurrentSession(response.session_id)

        // Poll status
        const progressInterval = setInterval(async () => {
          try {
            const statusResponse = await apiClient.getAIStatus(response.session_id)

            // Normalize progress percent from various shapes
            const raw = (statusResponse as any).progress
            const pctValue = typeof raw === 'object' ? (raw?.percent_complete ?? 0) : raw
            const pctNum = Number.isFinite(Number(pctValue)) ? Number(pctValue) : 0
            setProgress(Math.min(100, Math.max(0, Math.round(pctNum))))

            const isDone =
              (statusResponse as any).status === 'completed' ||
              (statusResponse as any).has_result === true
            if (isDone) {
              setStatus('completed')
              // Ensure progress looks finished while fetching final data
              setProgress(prev => (prev < 99 ? 99 : prev))
              const final = await apiClient.getAIResult(response.session_id)
              // Normalize result to AIPOGenerationResult shape expected by UI
              const normalized = ((): AIPOGenerationResult => {
                const items =
                  (final as any).po_items?.map((it: any) => ({
                    medication_id: it.med_id,
                    medication_name: it.med_name,
                    suggested_quantity: it.quantity,
                    reason: `${it.supplier_name} • lead ${it.lead_time}d`,
                    priority: 'medium' as const,
                  })) || []
                const computedTotal =
                  (final as any).po_items?.reduce(
                    (sum: number, it: any) => sum + (Number(it.subtotal) || 0),
                    0
                  ) || 0
                return {
                  session_id: (final as any).session_id || response.session_id,
                  estimated_total: (final as any).metadata?.total_cost ?? computedTotal,
                  supplier_suggestion:
                    (final as any).po_items?.[0]?.supplier_name || 'Top Supplier',
                  reasoning: Object.values((final as any).reasoning || {})
                    .map((r: any) => r.summary)
                    .join(' \n '),
                  items,
                } as AIPOGenerationResult
              })()
              setResult(normalized)
              setProgress(100)
              clearInterval(progressInterval)
              toast.success('AI Purchase Order generated successfully!')
              queryClient.invalidateQueries({ queryKey: ['inventory'] })
            } else if ((statusResponse as any).status === 'failed') {
              setStatus('error')
              clearInterval(progressInterval)
              toast.error('AI PO generation failed')
              throw new Error('AI PO generation failed')
            }
          } catch (error) {
            clearInterval(progressInterval)
            setStatus('error')
            throw error
          }
        }, 1200)

        return response
      } catch (error) {
        setStatus('error')
        toast.error('Failed to start AI PO generation')
        throw error
      }
    },
  })

  const resetGeneration = () => {
    setCurrentSession(null)
    setProgress(0)
    setStatus('idle')
    setResult(null)
  }

  return {
    generatePO: generatePO.mutate,
    isGenerating: generatePO.isPending || status === 'generating',
    progress,
    status,
    result,
    error: generatePO.error,
    resetGeneration,
    isLoading: generatePO.isPending,
  }
}
