import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'

export interface AIPOGenerationParams {
  store_ids?: number[]
  category_filter?: string
  days_forecast?: number
  medication_ids?: number[]
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
  const [progressDetails, setProgressDetails] = useState<{
    current_agent?: string
    current_action?: string
    steps_completed?: string[]
    steps_remaining?: string[]
  }>({})

  const queryClient = useQueryClient()

  const generatePO = useMutation({
    mutationFn: async (params: AIPOGenerationParams) => {
      setStatus('generating')
      setProgress(0)
      setResult(null)
      setProgressDetails({})

      try {
        // Map UI params to backend request
        const request = {
          days_forecast: params.days_forecast ?? 30,
          category_filter: params.category_filter,
          store_ids: params.store_ids,
        } as any

        // Only include medication_ids if specifically provided (don't default to empty array)
        if (params.medication_ids && params.medication_ids.length > 0) {
          request.medication_ids = params.medication_ids
        }

        console.log('🔍 Debug - AI PO generation request:', request)
        console.log('🔍 Debug - Medication IDs being sent to API:', params.medication_ids)

        // Start AI PO generation (backend async kickoff)
        const response = await apiClient.generateAIPO(request)

        setCurrentSession(response.session_id)

        // Poll status
        let lastPct = 0
        const progressInterval = setInterval(async () => {
          try {
            const statusResponse = await apiClient.getAIStatus(response.session_id)
            console.log('🔄 Status response:', statusResponse)

            // Normalize progress percent from various shapes
            const raw = (statusResponse as any).progress
            console.log('📊 Progress raw:', raw)
            setProgressDetails({
              current_agent: raw?.current_agent,
              current_action: raw?.current_action,
              steps_completed: raw?.steps_completed,
              steps_remaining: raw?.steps_remaining,
            })
            let pctNum: number
            if (typeof raw === 'object') {
              const pc = (raw as any)?.percent_complete
              if (pc !== undefined && pc !== null) {
                pctNum = Number(pc)
              } else {
                const completed = Array.isArray((raw as any).steps_completed)
                  ? (raw as any).steps_completed.length
                  : 0
                const total = completed + (Array.isArray((raw as any).steps_remaining) ? (raw as any).steps_remaining.length : 0)
                pctNum = total > 0 ? Math.round((completed / total) * 100) : 0
              }
            } else {
              pctNum = Number(raw)
            }
            pctNum = Number.isFinite(pctNum) ? pctNum : 0
            console.log('📈 Progress calculated:', pctNum)

            // Tween progress a bit for smoother movement
            const nextTarget = Math.min(100, Math.max(lastPct, Math.round(pctNum)))
            if (nextTarget > lastPct) {
              const step = Math.max(1, Math.round((nextTarget - lastPct) / 3))
              let current = lastPct
              const tween = setInterval(() => {
                current = Math.min(nextTarget, current + step)
                setProgress(current)
                if (current >= nextTarget) {
                  clearInterval(tween)
                }
              }, 150)
              lastPct = nextTarget
            }

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
        }, 800)

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
    setProgressDetails({})
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
    progressDetails,
  }
}
