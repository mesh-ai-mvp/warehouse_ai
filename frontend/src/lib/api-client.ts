import type {
  InventoryResponse,
  InventoryFilters,
  Medication,
  Supplier,
  PurchaseOrder,
  ConsumptionHistory,
  SupplierPrice,
  AIGenerationSession,
  AIGenerationResult,
  DashboardStats,
  FilterOptions,
  CreatePORequest,
  CreatePOBackendRequest,
  PurchaseOrderCreate,
  LineItem,
  APIError,
  AIGenerationRequest,
} from '@/types/api'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const error: APIError = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`,
        }))
        throw new Error(error.detail)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('An unexpected error occurred')
    }
  }

  // Inventory endpoints
  async getInventory(filters: InventoryFilters = {}): Promise<InventoryResponse> {
    const params = new URLSearchParams()

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString())
      }
    })

    const queryString = params.toString()
    const endpoint = `/inventory${queryString ? `?${queryString}` : ''}`

    return this.request<InventoryResponse>(endpoint)
  }

  async getMedication(id: string): Promise<Medication> {
    // Get medication detail
    const medDetail = await this.request<any>(`/medication/${id}`)

    // Get inventory data for this medication
    const inventoryResponse = await this.getInventory({ search: medDetail.name, page_size: 50 })
    const inventoryData = inventoryResponse.items.find(item => item.med_id.toString() === id)

    // Merge the data into the expected format
    const medication: Medication = {
      med_id: parseInt(id),
      name: medDetail.name,
      category: medDetail.category,
      current_stock: inventoryData?.current_stock || 0,
      reorder_point: inventoryData?.reorder_point || 0,
      supplier: medDetail.supplier?.name || inventoryData?.supplier_name || '',
      pack_size: medDetail.pack_size || inventoryData?.pack_size || 0,
      unit_cost: medDetail.price?.price_per_unit || inventoryData?.current_price || 0,
      total_value:
        (inventoryData?.current_stock || 0) *
        (medDetail.price?.price_per_unit || inventoryData?.current_price || 0),
      avg_daily_pick: medDetail.sku_meta?.avg_daily_pick || inventoryData?.avg_daily_pick || 0,
      days_until_stockout: inventoryData?.days_until_stockout || 0,
      storage_location: medDetail.storage?.zone_type || inventoryData?.storage_location || '',
      batch_number: undefined, // Not available in current API
      expiry_date: undefined, // Not available in current API
      last_updated: inventoryData?.last_updated || new Date().toISOString(),
    }

    return medication
  }

  async getConsumptionHistory(medicationId: string): Promise<ConsumptionHistory[]> {
    return this.request<ConsumptionHistory[]>(`/medication/${medicationId}/consumption-history`)
  }

  async getSupplierPrices(medicationId: string): Promise<SupplierPrice[]> {
    return this.request<SupplierPrice[]>(`/medications/${medicationId}/supplier-prices`)
  }

  // Filter options
  async getFilterOptions(): Promise<FilterOptions> {
    return this.request<FilterOptions>('/filters')
  }

  // Supplier endpoints
  async getSuppliers(): Promise<Supplier[]> {
    const response = await this.request<{ suppliers: Supplier[] }>('/suppliers')
    return response.suppliers
  }

  // Purchase Order endpoints
  async getPurchaseOrders(
    filters: {
      status?: string
      supplier?: string
      page?: number
      page_size?: number
    } = {}
  ): Promise<{
    items: PurchaseOrder[]
    total: number
    page: number
    page_size: number
  }> {
    const params = new URLSearchParams()

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString())
      }
    })

    const queryString = params.toString()
    const endpoint = `/purchase-orders${queryString ? `?${queryString}` : ''}`

    const response = await this.request<{
      purchase_orders: any[]
      total?: number
      page?: number
      page_size?: number
    }>(endpoint)

    // Map the API response to the expected format
    const mappedItems: PurchaseOrder[] = response.purchase_orders.map(po => ({
      id: po.po_id || po.id,
      supplier: po.supplier_name || po.supplier,
      status: po.status,
      created_date: po.created_at || po.created_date,
      delivery_date: po.delivery_date,
      total_amount: Number(po.total_amount || 0),
      line_items: po.line_items || [],
      buyer_name: po.buyer_name,
      notes: po.notes,
      ai_generated: po.ai_generated,
    }))

    return {
      items: mappedItems,
      total: response.total || response.purchase_orders.length,
      page: response.page || 1,
      page_size: response.page_size || 20,
    }
  }

  async getPurchaseOrder(id: string): Promise<PurchaseOrder> {
    return this.request<PurchaseOrder>(`/purchase-orders/${id}`)
  }

  async createPurchaseOrder(
    data: CreatePORequest | PurchaseOrderCreate,
    options: { sendEmails?: boolean } = {}
  ): Promise<PurchaseOrder> {
    // Convert frontend formats to backend API format
    let supplier_id: number
    let supplier_name: string
    let line_items: any[]
    let delivery_date: string | undefined
    let notes: string | undefined
    let buyer_name: string | undefined

    if ('supplier' in data) {
      // Handle PurchaseOrderCreate format
      const suppliers = await this.getSuppliers()
      const supplier = suppliers.find(s => s.name === data.supplier)
      supplier_id = supplier?.supplier_id || parseInt(data.supplier)
      supplier_name = supplier?.name || data.supplier
      line_items = data.line_items
      delivery_date = data.delivery_date
      notes = data.notes
      buyer_name = (data as any).buyer_name
    } else {
      // Handle CreatePORequest format
      const suppliers = await this.getSuppliers()
      const supplier = suppliers.find(s => s.supplier_id.toString() === data.supplier_id)
      supplier_id = parseInt(data.supplier_id)
      supplier_name = supplier?.name || `Supplier ${data.supplier_id}`
      line_items = data.line_items.map(item => ({
        medication_id: item.medication_id,
        medication_name: '', // Will be filled by backend
        quantity: item.quantity,
        unit_price: item.unit_price || 0,
        total_price: (item.unit_price || 0) * item.quantity,
      }))
      delivery_date = data.delivery_date
      notes = data.notes
      buyer_name = data.buyer_name
    }

    // Transform to backend API format
    const backendRequest: CreatePOBackendRequest = {
      items: line_items.map(item => ({
        med_id: parseInt(item.medication_id.toString()),
        total_quantity: item.quantity,
        allocations: [
          {
            supplier_id: supplier_id,
            quantity: item.quantity,
            unit_price: item.unit_price || 0,
          },
        ],
      })),
      meta: {
        requested_delivery_date: delivery_date,
        notes: notes,
        buyer: buyer_name,
      },
      send_emails: options.sendEmails || false,
    }

    return this.request<PurchaseOrder>('/purchase-orders', {
      method: 'POST',
      body: JSON.stringify(backendRequest),
    })
  }

  async sendPOEmails(request: CreatePOBackendRequest): Promise<{ sent: number }> {
    return this.request('/purchase-orders/send-emails', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // AI PO Generation endpoints
  async generateAIPO(request: AIGenerationRequest): Promise<AIGenerationSession> {
    return this.request<AIGenerationSession>('/purchase-orders/generate-ai', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getAIStatus(sessionId: string): Promise<AIGenerationSession> {
    return this.request<AIGenerationSession>(`/purchase-orders/ai-status/${sessionId}`)
  }

  async getAIResult(sessionId: string): Promise<AIGenerationResult> {
    return this.request<AIGenerationResult>(`/purchase-orders/ai-result/${sessionId}`)
  }

  async createFromAI(
    sessionId: string,
    selectedPOs: string[] = []
  ): Promise<{
    created_orders: PurchaseOrder[]
    success_count: number
    total_count: number
  }> {
    return this.request('/purchase-orders/create-from-ai', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        selected_pos: selectedPOs,
      }),
    })
  }

  // System status
  async getAIConfigStatus(): Promise<{
    openai_configured: boolean
    model_available: boolean
    status: string
  }> {
    return this.request('/ai/config-status')
  }

  // Dashboard stats
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      const stats = await this.request('/dashboard/stats')

      // Add extra mock fields for UI compatibility
      return {
        ...stats,
        revenue_mtd: stats.total_value * 0.1, // Mock calculation
        trending_up_count: Math.floor(stats.total_medications * 0.3),
        trending_down_count: Math.floor(stats.total_medications * 0.2),
      }
    } catch (error) {
      // Return mock data if real data fails
      return {
        total_medications: 2450,
        low_stock_count: 15,
        critical_stock_count: 5,
        total_value: 125000,
        orders_today: 8,
        revenue_mtd: 45200,
        trending_up_count: 735,
        trending_down_count: 490,
      }
    }
  }

  // Analytics endpoints
  async getAnalyticsKPIs(timeRange: string = '30d', filters: any = {}): Promise<any> {
    const params = new URLSearchParams({ time_range: timeRange, ...filters })
    const endpoint = `/analytics/kpis?${params}`

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development
      return {
        kpis: {
          totalRevenue: 2450000,
          totalOrders: 1247,
          avgOrderValue: 1965,
          lowStockItems: 23,
          criticalStockItems: 8,
          totalSuppliers: 45,
          onTimeDeliveries: 94.5,
          inventoryTurnover: 8.2,
        },
        trends: {
          revenueChange: 12.5,
          ordersChange: 8.3,
          avgOrderChange: 3.7,
          stockAlertsChange: -15.2,
        },
      }
    }
  }

  async getConsumptionTrends(timeRange: string = '6m', medicationId?: string): Promise<any[]> {
    const params = new URLSearchParams({ time_range: timeRange })
    if (medicationId) params.append('medication_id', medicationId)
    const endpoint = `/analytics/consumption-trends?${params}`

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development
      return [
        { month: 'Jan', consumption: 450000, orders: 120, forecast: 460000 },
        { month: 'Feb', consumption: 520000, orders: 135, forecast: 530000 },
        { month: 'Mar', consumption: 480000, orders: 128, forecast: 485000 },
        { month: 'Apr', consumption: 590000, orders: 155, forecast: 580000 },
        { month: 'May', consumption: 610000, orders: 162, forecast: 615000 },
        { month: 'Jun', consumption: 580000, orders: 148, forecast: 570000 },
      ]
    }
  }

  async getSupplierPerformanceAnalytics(timeRange: string = '3m'): Promise<any[]> {
    const endpoint = `/analytics/supplier-performance?time_range=${timeRange}`

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development
      return [
        { name: 'PharmaCorp', orders: 45, onTime: 96.2, avgDelay: 1.2, rating: 4.8 },
        { name: 'MedSupply Pro', orders: 38, onTime: 94.1, avgDelay: 2.1, rating: 4.6 },
        { name: 'HealthDist Inc', orders: 32, onTime: 91.8, avgDelay: 3.2, rating: 4.3 },
        { name: 'BioPharma Ltd', orders: 28, onTime: 98.5, avgDelay: 0.8, rating: 4.9 },
        { name: 'MediCore Systems', orders: 25, onTime: 89.3, avgDelay: 4.1, rating: 4.1 },
      ]
    }
  }

  async getCategoryBreakdown(): Promise<any[]> {
    const endpoint = '/analytics/category-breakdown'

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development
      return [
        { name: 'Antibiotics', value: 35, color: '#0088FE' },
        { name: 'Pain Relief', value: 25, color: '#00C49F' },
        { name: 'Cardiovascular', value: 20, color: '#FFBB28' },
        { name: 'Respiratory', value: 12, color: '#FF8042' },
        { name: 'Other', value: 8, color: '#8884D8' },
      ]
    }
  }

  async getStockAlerts(): Promise<any[]> {
    const endpoint = '/analytics/stock-alerts'

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development
      return [
        {
          medication: 'Amoxicillin 500mg',
          current: 45,
          reorder: 100,
          daysLeft: 3,
          priority: 'critical',
        },
        { medication: 'Ibuprofen 200mg', current: 78, reorder: 150, daysLeft: 5, priority: 'low' },
        { medication: 'Lisinopril 10mg', current: 32, reorder: 80, daysLeft: 4, priority: 'low' },
        {
          medication: 'Metformin 500mg',
          current: 15,
          reorder: 120,
          daysLeft: 2,
          priority: 'critical',
        },
      ]
    }
  }

  async getStockLevelTrends(medicationId?: number, timeRange: string = '7d'): Promise<any> {
    const params = new URLSearchParams()
    if (medicationId) params.append('medication_id', medicationId.toString())
    params.append('time_range', timeRange)

    const endpoint = `/analytics/stock-level-trends?${params}`
    return await this.request(endpoint)
  }

  async getConsumptionForecast(medicationId?: number, forecastDays: number = 7): Promise<any> {
    const params = new URLSearchParams()
    if (medicationId) params.append('medication_id', medicationId.toString())
    params.append('forecast_days', forecastDays.toString())

    const endpoint = `/analytics/consumption-forecast?${params}`
    return await this.request(endpoint)
  }

  async getDeliveryTimeline(): Promise<any[]> {
    const endpoint = '/analytics/delivery-timeline'
    return await this.request(endpoint)
  }

  // Reports endpoints
  async getReportTemplates(): Promise<any[]> {
    const endpoint = '/reports/templates'

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development - handled in the component
      return []
    }
  }

  async createReportTemplate(template: any): Promise<any> {
    return this.request('/reports/templates', {
      method: 'POST',
      body: JSON.stringify(template),
    })
  }

  async runReport(templateId: string, parameters: any = {}): Promise<any> {
    return this.request(`/reports/templates/${templateId}/run`, {
      method: 'POST',
      body: JSON.stringify(parameters),
    })
  }

  async exportReport(templateId: string, format: string, parameters: any = {}): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/reports/templates/${templateId}/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ format, parameters }),
    })

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`)
    }

    return await response.blob()
  }

  async getReportHistory(filters: { limit?: number; offset?: number } = {}): Promise<any[]> {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) params.append(key, value.toString())
    })

    const endpoint = `/reports/history${params.toString() ? `?${params}` : ''}`

    try {
      return await this.request(endpoint)
    } catch (error) {
      // Return mock data for development - handled in the component
      return []
    }
  }

  async deleteReportTemplate(templateId: string): Promise<void> {
    await this.request(`/reports/templates/${templateId}`, {
      method: 'DELETE',
    })
  }
}

// Create singleton instance
export const apiClient = new ApiClient()
export default apiClient
