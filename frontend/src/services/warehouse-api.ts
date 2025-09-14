/**
 * Warehouse API Service
 * Handles all API calls for warehouse management
 */

const API_BASE = '/api/warehouse';

export interface WarehouseLayoutResponse {
  zones: any[];
  aisles: any[];
  stats: {
    total_medications: number;
    total_aisles: number;
    total_shelves: number;
    avg_utilization: number;
    critical_alerts: number;
    expiring_soon: number;
    temperature_alerts: number;
  };
}

export interface AisleDetailsResponse {
  aisle: any;
  shelves: any[];
  medications: any[];
  temperature: any;
  total_medications: number;
}

export interface ShelfDetailsResponse {
  shelf: any;
  dimensions: {
    width_slots: number;
    depth_rows: number;
    total_positions: number;
    occupied_positions: number;
    utilization_percent: number;
  };
  rows: {
    front: any[];
    middle: any[];
    back: any[];
  };
  placement_strategy: any;
  position_map: any;
  alerts: any[];
  capacity: any;
}

export interface ChaosMetricsResponse {
  chaos_metrics: Array<{
    metric_name: string;
    current_chaos_score: number;
    optimal_score: number;
    improvement_potential: number;
  }>;
  overall_chaos_score: number;
  total_improvement_potential: number;
}

export interface BatchFragmentationResponse {
  fragmented_batches: any[];
  total_fragmented: number;
  total_batches: number;
  fragmentation_rate: number;
  consolidation_opportunity: string;
}

export interface VelocityMismatchResponse {
  velocity_mismatches: any[];
  total_mismatches: number;
  optimal_mapping: any[];
  relocation_opportunity: string;
}

class WarehouseAPI {
  async getWarehouseLayout(): Promise<WarehouseLayoutResponse> {
    const response = await fetch(`${API_BASE}/layout`);
    if (!response.ok) throw new Error('Failed to fetch warehouse layout');
    return response.json();
  }

  async getAisleDetails(aisleId: number): Promise<AisleDetailsResponse> {
    const response = await fetch(`${API_BASE}/aisle/${aisleId}`);
    if (!response.ok) throw new Error('Failed to fetch aisle details');
    return response.json();
  }

  async getShelfDetails(shelfId: number): Promise<ShelfDetailsResponse> {
    const response = await fetch(`${API_BASE}/shelf/${shelfId}/detailed`);
    if (!response.ok) throw new Error('Failed to fetch shelf details');
    return response.json();
  }

  async getShelfInventory(shelfId: number) {
    const response = await fetch(`${API_BASE}/shelf/${shelfId}`);
    if (!response.ok) throw new Error('Failed to fetch shelf inventory');
    return response.json();
  }

  async getWarehouseAlerts() {
    const response = await fetch(`${API_BASE}/alerts`);
    if (!response.ok) throw new Error('Failed to fetch alerts');
    return response.json();
  }

  async getChaosMetrics(): Promise<ChaosMetricsResponse> {
    const response = await fetch(`${API_BASE}/chaos/metrics`);
    if (!response.ok) throw new Error('Failed to fetch chaos metrics');
    return response.json();
  }

  async getBatchFragmentation(): Promise<BatchFragmentationResponse> {
    const response = await fetch(`${API_BASE}/chaos/batch-fragmentation`);
    if (!response.ok) throw new Error('Failed to fetch batch fragmentation');
    return response.json();
  }

  async getVelocityMismatches(): Promise<VelocityMismatchResponse> {
    const response = await fetch(`${API_BASE}/chaos/velocity-mismatches`);
    if (!response.ok) throw new Error('Failed to fetch velocity mismatches');
    return response.json();
  }

  async getFIFOValidation() {
    const response = await fetch(`${API_BASE}/fifo/validate`);
    if (!response.ok) throw new Error('Failed to validate FIFO');
    return response.json();
  }

  async getPlacementRecommendation(medId: number) {
    const response = await fetch(`${API_BASE}/placement/recommend/${medId}`);
    if (!response.ok) throw new Error('Failed to get placement recommendation');
    return response.json();
  }

  async moveMe

dication(moveRequest: {
    med_id: number;
    from_shelf: number;
    to_shelf: number;
    quantity: number;
    reason?: string;
  }) {
    const response = await fetch(`${API_BASE}/move`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(moveRequest),
    });
    if (!response.ok) throw new Error('Failed to move medication');
    return response.json();
  }

  async getMovementStatistics(days: number = 7) {
    const response = await fetch(`${API_BASE}/statistics/movement?days=${days}`);
    if (!response.ok) throw new Error('Failed to fetch movement statistics');
    return response.json();
  }
}

export const warehouseAPI = new WarehouseAPI();