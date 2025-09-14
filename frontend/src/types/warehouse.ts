// Warehouse TypeScript type definitions

export interface Zone {
  zone_id: number;
  zone_name: string;
  zone_type: 'restricted' | 'cold' | 'ambient' | 'quarantine' | 'office';
  temperature_range: string;
  capacity: number;
  current_utilization: number;
  aisle_count: number;
  aisles?: Aisle[];
}

export interface Aisle {
  aisle_id: number;
  zone_id: number;
  aisle_code: string;
  aisle_name: string;
  position_x: number;
  position_z: number;
  temperature: number;
  humidity?: number;
  category: 'General' | 'Refrigerated' | 'Controlled' | 'Quarantine' | 'Office';
  shelf_count: number;
  medication_count: number;
  avg_utilization: number;
  shelves?: Shelf[];
}

export interface Shelf {
  shelf_id: number;
  aisle_id: number;
  shelf_code: string;
  position: number;
  level: number;
  capacity_slots: number;
  max_weight_kg?: number;
  current_weight_kg?: number;
  utilization_percent: number;
  status: 'active' | 'inactive' | 'maintenance';
  medication_count?: number;
  total_items?: number;
  medications?: ShelfMedication[];
}

export interface ShelfPosition {
  position_id: number;
  shelf_id: number;
  grid_x: number;
  grid_y: number;
  grid_label: string;
  is_golden_zone: boolean;
  accessibility: number;
  reserved_for?: string;
  max_weight: number;
  allows_stacking: boolean;
  medication?: PositionMedication;
}

export interface PositionMedication {
  med_id: number;
  name: string;
  batch_id?: number;
  lot_number?: string;
  quantity: number;
  expiry_date: string;
  expiry_status: 'critical' | 'soon' | 'normal' | 'long';
  velocity: 'fast' | 'medium' | 'slow';
  placement_reason?: string;
  behind_medication?: string;
  further_back?: string;
}

export interface ShelfMedication {
  med_id: number;
  name: string;
  category: string;
  quantity: number;
  shelf_id: number;
  batch_id?: number;
  expiry_date?: string;
  velocity_score?: number;
  movement_category?: 'Fast' | 'Medium' | 'Slow';
  placement?: string;
}

export interface WarehouseStats {
  total_medications: number;
  total_aisles: number;
  total_shelves: number;
  avg_utilization: number;
  critical_alerts: number;
  expiring_soon: number;
  low_stock_count: number;
  overstock_count: number;
}

export interface WarehouseLayout {
  zones: Zone[];
  aisles: Aisle[];
  stats: WarehouseStats;
  alerts?: Alert[];
}

export interface AisleDetails {
  aisle: Aisle & {
    zone_name: string;
    temperature_range: string;
  };
  shelves: Shelf[];
  medications: ShelfMedication[];
  temperature?: {
    current: number;
    min: number;
    max: number;
    avg: number;
  };
}

export interface ShelfInventory {
  shelf: Shelf;
  medications: ShelfMedication[];
  batches: BatchInfo[];
  capacity: {
    total_slots: number;
    used_slots: number;
    available_slots: number;
    utilization_percent: number;
  };
}

export interface ShelfDetailedLayout {
  shelf: Shelf & {
    aisle_name: string;
    category: string;
    temperature: number;
  };
  dimensions: {
    width_slots: number;
    depth_rows: number;
    total_positions: number;
    occupied_positions: number;
    utilization_percent: number;
  };
  rows: {
    front: ShelfPosition[];
    middle: ShelfPosition[];
    back: ShelfPosition[];
  };
  placement_strategy: {
    front_row: string;
    middle_row: string;
    back_row: string;
  };
  position_map: Record<string, {
    med_name: string;
    quantity: number;
    expiry: string;
  }>;
  alerts?: Alert[];
}

export interface BatchInfo {
  batch_id: number;
  med_id: number;
  lot_number: string;
  quantity: number;
  remaining_quantity: number;
  expiry_date: string;
  manufacture_date: string;
  supplier_id: number;
}

export interface MoveRequest {
  med_id: number;
  from_shelf: number;
  to_shelf: number;
  quantity: number;
  batch_id?: number;
  reason?: string;
}

export interface MoveResponse {
  success: boolean;
  message: string;
  movement_id?: number;
  updated_positions?: {
    from: ShelfPosition;
    to: ShelfPosition;
  };
}

export interface Alert {
  id?: number;
  type: 'temperature' | 'expiry' | 'capacity' | 'stock' | 'movement';
  severity: 'critical' | 'warning' | 'info';
  message: string;
  position?: string;
  shelf_id?: number;
  aisle_id?: number;
  med_id?: number;
  timestamp?: string;
  acknowledged?: boolean;
}

export interface WarehouseAlerts {
  alerts: Alert[];
  summary: {
    total: number;
    critical: number;
    warning: number;
    info: number;
    unacknowledged: number;
  };
}

export interface MovementHistory {
  movement_id: number;
  med_id: number;
  med_name: string;
  position_id?: number;
  movement_type: 'pick' | 'replenish' | 'relocate';
  quantity: number;
  movement_date: string;
  operator_id?: string;
  order_id?: number;
  from_position?: string;
  to_position?: string;
}

// View state types
export type ViewState = 'warehouse' | 'aisle' | 'shelf';

export interface ViewContext {
  currentView: ViewState;
  selectedZone?: Zone;
  selectedAisle?: Aisle;
  selectedShelf?: Shelf;
  selectedPosition?: ShelfPosition;
}