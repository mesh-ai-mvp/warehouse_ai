// API Response Types for Pharmaceutical Warehouse Management System

export interface Medication {
  med_id: number
  name: string
  category: string
  current_stock: number
  reorder_point: number
  supplier: string
  pack_size: number
  unit_cost: number
  total_value: number
  avg_daily_pick: number
  days_until_stockout: number
  storage_location: string
  batch_number?: string
  expiry_date?: string
  last_updated: string
}

export interface InventoryFilters {
  search?: string
  category?: string
  supplier?: string
  stock_level?: 'low' | 'normal' | 'high' | 'critical'
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface InventoryResponse {
  items: Medication[]
  total: number
  page: number
  page_size: number
  total_pages: number
  filters_applied: InventoryFilters
}

export interface Supplier {
  supplier_id: number
  name: string
  contact_person?: string
  email?: string
  phone?: string
  address?: string
  rating?: number
  last_order_date?: string
}

export interface PurchaseOrder {
  id: string
  supplier: string
  status: 'pending' | 'approved' | 'completed' | 'cancelled' | 'draft'
  created_date: string
  delivery_date?: string
  total_amount: number
  line_items: POLineItem[]
  buyer_name?: string
  notes?: string
  ai_generated?: boolean
}

export interface POLineItem {
  medication_id: string
  medication_name: string
  quantity: number
  unit_price: number
  total_price: number
  supplier_sku?: string
}

export interface ConsumptionHistory {
  medication_id: string
  date: string
  quantity_consumed: number
  remaining_stock: number
  forecast_value?: number
  ai_prediction?: number
}

export interface SupplierPrice {
  supplier_id: string
  supplier_name: string
  unit_price: number
  minimum_order_quantity: number
  lead_time_days: number
  last_updated: string
}

export interface AIGenerationSession {
  session_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
  created_at: string
  completed_at?: string
}

export interface AIGenerationResult {
  session_id: string
  purchase_orders: PurchaseOrder[]
  reasoning: string
  total_estimated_cost: number
  estimated_delivery_date: string
  confidence_score: number
}

export interface DashboardStats {
  total_medications: number
  low_stock_count: number
  critical_stock_count: number
  total_value: number
  orders_today: number
  revenue_mtd: number
  trending_up_count: number
  trending_down_count: number
}

export interface FilterOptions {
  categories: string[]
  suppliers: string[]
  storage_locations: string[]
  stock_levels: Array<{
    value: string
    label: string
    count: number
  }>
}

// Error types
export interface APIError {
  detail: string
  code?: string
  field?: string
}

// Request types
export interface CreatePORequest {
  supplier_id: string
  delivery_date?: string
  buyer_name?: string
  notes?: string
  line_items: Array<{
    medication_id: string
    quantity: number
    unit_price?: number
  }>
}

// Backend API format for PO creation
export interface CreatePOBackendRequest {
  items: Array<{
    med_id: number
    total_quantity: number
    allocations: Array<{
      supplier_id: number
      quantity: number
      unit_price: number
    }>
  }>
  meta: {
    requested_delivery_date?: string
    notes?: string
    buyer?: string
  }
  send_emails?: boolean
}

// Alternative interface for simplified PO creation (matches frontend usage)
export interface PurchaseOrderCreate {
  supplier: string
  delivery_date?: string
  notes?: string
  line_items: POLineItem[]
  ai_generated?: boolean
}

// Type alias for LineItem to match frontend usage
export type LineItem = POLineItem

// AI Purchase Order Generation Request Interface
export interface AIGenerationRequest {
  criteria?: {
    max_budget?: number
    preferred_suppliers?: string[]
    priority_medications?: string[]
    delivery_deadline?: string
  }
  include_forecasting?: boolean
  confidence_threshold?: number
  // Extended fields used by AI PO UI and backend
  days_forecast?: number
  urgency_threshold?: number // 0..1 fraction of reorder point
  category_filter?: string
  store_ids?: number[]
  medication_ids?: number[]
}
