import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

// Create a test query client with default options
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  })

// Custom render function that includes necessary providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient
  route?: string
}

export function renderWithProviders(
  ui: ReactElement,
  {
    queryClient = createTestQueryClient(),
    route = '/',
    ...renderOptions
  }: CustomRenderOptions = {}
) {
  // Set the initial URL if provided
  if (route !== '/') {
    window.history.pushState({}, 'Test page', route)
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </QueryClientProvider>
    )
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'

// Mock data factories for testing
export const createMockMedication = (overrides = {}) => ({
  id: 'med-1',
  name: 'Amoxicillin 500mg',
  category: 'Antibiotic',
  current_stock: 45,
  reorder_point: 100,
  supplier: 'PharmaCorp',
  unit_cost: 2.50,
  pack_size: 100,
  storage_location: 'A1-B2',
  expiry_date: '2024-12-31',
  batch_number: 'AMX123',
  ...overrides
})

export const createMockPurchaseOrder = (overrides = {}) => ({
  id: 'po-1',
  supplier: 'PharmaCorp',
  status: 'pending' as const,
  created_date: '2024-01-15T10:30:00Z',
  delivery_date: '2024-01-22T10:30:00Z',
  total_amount: 1250.00,
  buyer_name: 'John Doe',
  line_items: [
    {
      medication_id: 'med-1',
      medication_name: 'Amoxicillin 500mg',
      quantity: 500,
      unit_cost: 2.50,
      total_cost: 1250.00
    }
  ],
  ai_generated: false,
  ...overrides
})

export const createMockInventoryResponse = (overrides = {}) => ({
  items: [createMockMedication()],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
  ...overrides
})

