import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

export interface AIPOGenerationParams {
  store_ids?: number[];
  category_filter?: string;
  days_forecast?: number;
  urgency_threshold?: number;
}

export interface AIPOGenerationResult {
  session_id: string;
  estimated_total: number;
  supplier_suggestion: string;
  reasoning: string;
  items: {
    medication_id: number;
    suggested_quantity: number;
    reason: string;
    priority: 'high' | 'medium' | 'low';
  }[];
}

export interface AIPOStatus {
  session_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  result?: AIPOGenerationResult;
}

export function useAIPOGeneration() {
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'generating' | 'completed' | 'error'>('idle');
  const [result, setResult] = useState<AIPOGenerationResult | null>(null);
  
  const queryClient = useQueryClient();

  const generatePO = useMutation({
    mutationFn: async (params: AIPOGenerationParams) => {
      setStatus('generating');
      setProgress(0);
      setResult(null);

      try {
        // Start AI PO generation
        const response = await apiClient.request<{ session_id: string }>('/ai/generate-po', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params)
        });

        setCurrentSession(response.session_id);

        // Simulate progress updates (in real implementation, use WebSocket or polling)
        const progressInterval = setInterval(async () => {
          try {
            const statusResponse = await apiClient.request<AIPOStatus>(
              `/ai/generate-po/${response.session_id}/status`
            );

            setProgress(statusResponse.progress);

            if (statusResponse.status === 'completed') {
              setStatus('completed');
              setResult(statusResponse.result!);
              setProgress(100);
              clearInterval(progressInterval);
              toast.success('AI Purchase Order generated successfully!');
              
              // Invalidate related queries
              queryClient.invalidateQueries({ queryKey: ['inventory'] });
            } else if (statusResponse.status === 'failed') {
              setStatus('error');
              clearInterval(progressInterval);
              toast.error('AI PO generation failed');
              throw new Error('AI PO generation failed');
            }
          } catch (error) {
            clearInterval(progressInterval);
            setStatus('error');
            throw error;
          }
        }, 1000);

        return response;
      } catch (error) {
        setStatus('error');
        toast.error('Failed to start AI PO generation');
        throw error;
      }
    },
  });

  const resetGeneration = () => {
    setCurrentSession(null);
    setProgress(0);
    setStatus('idle');
    setResult(null);
  };

  return {
    generatePO: generatePO.mutate,
    isGenerating: generatePO.isPending || status === 'generating',
    progress,
    status,
    result,
    error: generatePO.error,
    resetGeneration,
    isLoading: generatePO.isPending,
  };
}