export type ViewState = 'warehouse' | 'aisle' | 'shelf';

export interface Medication {
  id: string;
  name: string;
  quantity: number;
  maxCapacity: number;
  expiryDate: string;
  batchNumber: string;
  temperature: number;
}

export interface Shelf {
  id: string;
  position: number;
  level: number;
  medications: Medication[];
  capacity: number;
  code?: string;
}

export interface Aisle {
  id: string;
  name: string;
  position: { x: number, z: number };
  shelves: Shelf[];
  category: string;
  temperature: number;
  shelfCount?: number;
  medicationCount?: number;
}

// Type exports for compatibility
export type { ViewState, Medication, Shelf, Aisle };