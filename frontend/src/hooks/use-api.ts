import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from '@tanstack/react-query';
import { toast } from 'sonner';

import { apiClient } from '@/lib/api-client';
import type {
  InventoryFilters,
  CreatePORequest,
  PurchaseOrderCreate,
  LineItem,
  AIGenerationRequest,
} from '@/types/api';

// Query Keys
export const queryKeys = {
  inventory: (filters?: InventoryFilters) => ['inventory', filters],
  medication: (id: string) => ['medication', id],
  consumptionHistory: (medicationId: string) => ['consumption-history', medicationId],
  supplierPrices: (medicationId: string) => ['supplier-prices', medicationId],
  suppliers: ['suppliers'],
  purchaseOrders: (filters?: any) => ['purchase-orders', filters],
  purchaseOrder: (id: string) => ['purchase-order', id],
  filterOptions: ['filter-options'],
  dashboardStats: ['dashboard-stats'],
  aiStatus: (sessionId: string) => ['ai-status', sessionId],
  aiResult: (sessionId: string) => ['ai-result', sessionId],
  aiConfig: ['ai-config'],
} as const;

// Dashboard Hooks
export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: () => apiClient.getDashboardStats(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
  });
}

// Inventory Hooks
export function useInventory(filters: InventoryFilters = {}) {
  return useQuery({
    queryKey: queryKeys.inventory(filters),
    queryFn: () => apiClient.getInventory(filters),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute auto-refresh
    placeholderData: (previousData) => previousData, // Keep previous data while fetching
  });
}

export function useMedication(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.medication(id),
    queryFn: () => apiClient.getMedication(id),
    enabled: !!id && enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useConsumptionHistory(medicationId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.consumptionHistory(medicationId),
    queryFn: () => apiClient.getConsumptionHistory(medicationId),
    enabled: !!medicationId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useSupplierPrices(medicationId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.supplierPrices(medicationId),
    queryFn: () => apiClient.getSupplierPrices(medicationId),
    enabled: !!medicationId && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Filter Options Hook
export function useFilterOptions() {
  return useQuery({
    queryKey: queryKeys.filterOptions,
    queryFn: () => apiClient.getFilterOptions(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Supplier Hooks
export function useSuppliers() {
  return useQuery({
    queryKey: queryKeys.suppliers,
    queryFn: () => apiClient.getSuppliers(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Purchase Order Hooks
export function usePurchaseOrders(filters: any = {}) {
  return useQuery({
    queryKey: queryKeys.purchaseOrders(filters),
    queryFn: () => apiClient.getPurchaseOrders(filters),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  });
}

export function usePurchaseOrder(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.purchaseOrder(id),
    queryFn: () => apiClient.getPurchaseOrder(id),
    enabled: !!id && enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Purchase Order Mutations
export function useCreatePurchaseOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreatePORequest | PurchaseOrderCreate) => apiClient.createPurchaseOrder(data),
    onSuccess: (newPO) => {
      // Invalidate and refetch purchase orders
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      
      // Invalidate inventory data as it may have changed
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      
      // Invalidate dashboard stats
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });

      toast.success(`Purchase Order ${newPO.id} created successfully!`);
    },
    onError: (error: Error) => {
      toast.error(`Failed to create purchase order: ${error.message}`);
    },
  });
}

export function useSendPOEmails() {
  return useMutation({
    mutationFn: (poIds: string[]) => apiClient.sendPOEmails(poIds),
    onSuccess: (result) => {
      toast.success(result.message);
    },
    onError: (error: Error) => {
      toast.error(`Failed to send emails: ${error.message}`);
    },
  });
}

// AI Generation Hooks
export function useGenerateAIPO() {
  return useMutation({
    mutationFn: (request: AIGenerationRequest) => apiClient.generateAIPO(request),
    onSuccess: (session) => {
      toast.success('AI PO generation started! Check the progress below.');
    },
    onError: (error: Error) => {
      toast.error(`Failed to start AI generation: ${error.message}`);
    },
  });
}

export function useAIStatus(sessionId: string, enabled = false) {
  return useQuery({
    queryKey: queryKeys.aiStatus(sessionId),
    queryFn: () => apiClient.getAIStatus(sessionId),
    enabled: !!sessionId && enabled,
    refetchInterval: (data) => {
      // Stop polling when completed or failed
      return data?.status === 'processing' || data?.status === 'pending' ? 2000 : false;
    },
    staleTime: 0, // Always fresh
  });
}

export function useAIResult(sessionId: string, enabled = false) {
  return useQuery({
    queryKey: queryKeys.aiResult(sessionId),
    queryFn: () => apiClient.getAIResult(sessionId),
    enabled: !!sessionId && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCreateFromAI() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, selectedPOs }: { sessionId: string; selectedPOs?: string[] }) =>
      apiClient.createFromAI(sessionId, selectedPOs),
    onSuccess: (result) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });

      toast.success(
        `Successfully created ${result.success_count} of ${result.total_count} purchase orders!`
      );
    },
    onError: (error: Error) => {
      toast.error(`Failed to create purchase orders: ${error.message}`);
    },
  });
}

// System Status Hooks
export function useAIConfig() {
  return useQuery({
    queryKey: queryKeys.aiConfig,
    queryFn: () => apiClient.getAIConfigStatus(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry if AI is not configured
  });
}

// Real-time data hook with WebSocket support (future enhancement)
export function useRealTimeInventory(filters: InventoryFilters = {}) {
  const query = useInventory(filters);
  
  // TODO: Add WebSocket integration for real-time updates
  // This would listen for inventory changes and update the query data
  
  return query;
}

// Infinite query for large datasets
export function useInfiniteInventory(filters: InventoryFilters = {}) {
  return useInfiniteQuery({
    queryKey: ['infinite-inventory', filters],
    queryFn: ({ pageParam = 1 }) => 
      apiClient.getInventory({ ...filters, page: pageParam }),
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.total_pages) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    staleTime: 30 * 1000,
  });
}