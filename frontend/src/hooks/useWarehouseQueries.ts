// React Query hooks for warehouse data fetching
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { warehouseService } from '@/services/warehouseService';
import { MoveRequest } from '@/types/warehouse';

// Query keys
export const warehouseKeys = {
  all: ['warehouse'] as const,
  layout: () => [...warehouseKeys.all, 'layout'] as const,
  aisle: (aisleId: string | number) => [...warehouseKeys.all, 'aisle', aisleId] as const,
  shelf: (shelfId: string | number) => [...warehouseKeys.all, 'shelf', shelfId] as const,
  shelfDetailed: (shelfId: string | number) => [...warehouseKeys.all, 'shelf-detailed', shelfId] as const,
  alerts: () => [...warehouseKeys.all, 'alerts'] as const,
  temperature: (aisleId?: string | number) =>
    aisleId ? [...warehouseKeys.all, 'temperature', aisleId] as const
           : [...warehouseKeys.all, 'temperature'] as const,
  movementHistory: (medId?: string | number) =>
    medId ? [...warehouseKeys.all, 'movement-history', medId] as const
          : [...warehouseKeys.all, 'movement-history'] as const,
};

// Hook to fetch warehouse layout
export function useWarehouseLayout(options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: warehouseKeys.layout(),
    queryFn: () => warehouseService.getLayout(),
    refetchInterval: options?.refetchInterval || 30000, // Default 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}

// Hook to fetch aisle details
export function useAisleDetails(aisleId: string | number | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: warehouseKeys.aisle(aisleId!),
    queryFn: () => warehouseService.getAisleDetails(aisleId!),
    enabled: options?.enabled !== false && !!aisleId,
    staleTime: 10000,
  });
}

// Hook to fetch shelf inventory
export function useShelfInventory(shelfId: string | number | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: warehouseKeys.shelf(shelfId!),
    queryFn: () => warehouseService.getShelfInventory(shelfId!),
    enabled: options?.enabled !== false && !!shelfId,
    staleTime: 10000,
  });
}

// Hook to fetch detailed shelf layout
export function useDetailedShelfLayout(shelfId: string | number | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: warehouseKeys.shelfDetailed(shelfId!),
    queryFn: () => warehouseService.getDetailedShelfLayout(shelfId!),
    enabled: options?.enabled !== false && !!shelfId,
    staleTime: 10000,
  });
}

// Hook to fetch warehouse alerts
export function useWarehouseAlerts(options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: warehouseKeys.alerts(),
    queryFn: () => warehouseService.getWarehouseAlerts(),
    refetchInterval: options?.refetchInterval || 15000, // Default 15 seconds for alerts
    staleTime: 5000,
  });
}

// Hook to fetch temperature readings
export function useTemperatureReadings(aisleId?: string | number, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: warehouseKeys.temperature(aisleId),
    queryFn: () => warehouseService.getTemperatureReadings(aisleId),
    refetchInterval: options?.refetchInterval || 60000, // Default 1 minute
    staleTime: 30000,
  });
}

// Hook to fetch movement history
export function useMovementHistory(medId?: string | number) {
  return useQuery({
    queryKey: warehouseKeys.movementHistory(medId),
    queryFn: () => warehouseService.getMovementHistory(medId),
    staleTime: 30000,
  });
}

// Mutation hook for moving medication
export function useMoveMedication() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: MoveRequest) => warehouseService.moveMedication(request),
    onSuccess: (data, variables) => {
      // Invalidate relevant queries after successful move
      queryClient.invalidateQueries({ queryKey: warehouseKeys.layout() });
      queryClient.invalidateQueries({ queryKey: warehouseKeys.shelf(variables.from_shelf) });
      queryClient.invalidateQueries({ queryKey: warehouseKeys.shelf(variables.to_shelf) });
      queryClient.invalidateQueries({ queryKey: warehouseKeys.shelfDetailed(variables.from_shelf) });
      queryClient.invalidateQueries({ queryKey: warehouseKeys.shelfDetailed(variables.to_shelf) });

      // Invalidate aisle queries if we have that information
      // This would need to be enhanced with actual aisle IDs from the response
      queryClient.invalidateQueries({ queryKey: warehouseKeys.all });
    },
    onError: (error) => {
      console.error('Failed to move medication:', error);
    },
  });
}

// Hook to prefetch data for performance
export function usePrefetchWarehouseData() {
  const queryClient = useQueryClient();

  const prefetchLayout = async () => {
    await queryClient.prefetchQuery({
      queryKey: warehouseKeys.layout(),
      queryFn: () => warehouseService.getLayout(),
      staleTime: 10000,
    });
  };

  const prefetchAisle = async (aisleId: string | number) => {
    await queryClient.prefetchQuery({
      queryKey: warehouseKeys.aisle(aisleId),
      queryFn: () => warehouseService.getAisleDetails(aisleId),
      staleTime: 10000,
    });
  };

  const prefetchShelf = async (shelfId: string | number) => {
    await queryClient.prefetchQuery({
      queryKey: warehouseKeys.shelfDetailed(shelfId),
      queryFn: () => warehouseService.getDetailedShelfLayout(shelfId),
      staleTime: 10000,
    });
  };

  return {
    prefetchLayout,
    prefetchAisle,
    prefetchShelf,
  };
}