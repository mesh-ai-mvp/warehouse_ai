// Warehouse API Service Layer
import { WarehouseLayout, AisleDetails, ShelfInventory, ShelfDetailedLayout, MoveRequest, MoveResponse, WarehouseAlerts } from '@/types/warehouse';

export class WarehouseService {
  private apiBase = '/api/warehouse';

  // Get complete warehouse layout with zones and aisles
  async getLayout(): Promise<WarehouseLayout> {
    const response = await fetch(`${this.apiBase}/layout`);
    if (!response.ok) {
      throw new Error('Failed to fetch warehouse layout');
    }
    return response.json();
  }

  // Get detailed aisle information with shelves
  async getAisleDetails(aisleId: string | number): Promise<AisleDetails> {
    const response = await fetch(`${this.apiBase}/aisle/${aisleId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch aisle ${aisleId} details`);
    }
    return response.json();
  }

  // Get shelf inventory
  async getShelfInventory(shelfId: string | number): Promise<ShelfInventory> {
    const response = await fetch(`${this.apiBase}/shelf/${shelfId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch shelf ${shelfId} inventory`);
    }
    return response.json();
  }

  // Get detailed shelf layout with 3D positions
  async getDetailedShelfLayout(shelfId: string | number): Promise<ShelfDetailedLayout> {
    const response = await fetch(`${this.apiBase}/shelf/${shelfId}/detailed`);
    if (!response.ok) {
      throw new Error(`Failed to fetch detailed shelf ${shelfId} layout`);
    }
    return response.json();
  }

  // Move medication between shelves
  async moveMedication(request: MoveRequest): Promise<MoveResponse> {
    const response = await fetch(`${this.apiBase}/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    if (!response.ok) {
      throw new Error('Failed to move medication');
    }
    return response.json();
  }

  // Get warehouse alerts
  async getWarehouseAlerts(): Promise<WarehouseAlerts> {
    const response = await fetch(`${this.apiBase}/alerts`);
    if (!response.ok) {
      throw new Error('Failed to fetch warehouse alerts');
    }
    return response.json();
  }

  // Get temperature readings for an aisle
  async getTemperatureReadings(aisleId?: string | number): Promise<any> {
    const url = aisleId
      ? `${this.apiBase}/temperature/${aisleId}`
      : `${this.apiBase}/temperature`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch temperature readings');
    }
    return response.json();
  }

  // Get movement history
  async getMovementHistory(medId?: string | number): Promise<any> {
    const url = medId
      ? `${this.apiBase}/movement-history?med_id=${medId}`
      : `${this.apiBase}/movement-history`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch movement history');
    }
    return response.json();
  }

  // Get placement recommendations for a medication
  async getPlacementRecommendation(medId: number): Promise<any> {
    const response = await fetch(`${this.apiBase}/placement/recommend/${medId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch placement recommendations');
    }
    return response.json();
  }

  // Validate FIFO compliance
  async validateFIFO(): Promise<any> {
    const response = await fetch(`${this.apiBase}/fifo/validate`);
    if (!response.ok) {
      throw new Error('Failed to validate FIFO compliance');
    }
    return response.json();
  }

  // Get movement statistics
  async getMovementStatistics(days: number = 7): Promise<any> {
    const response = await fetch(`${this.apiBase}/statistics/movement?days=${days}`);
    if (!response.ok) {
      throw new Error('Failed to fetch movement statistics');
    }
    return response.json();
  }
}

// Singleton instance
export const warehouseService = new WarehouseService();