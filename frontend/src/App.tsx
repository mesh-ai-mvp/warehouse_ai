import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "./providers/theme-provider"
import { MainLayout } from "./components/layout/main-layout"
import { Dashboard } from "./pages/dashboard"
import { Inventory } from "./pages/inventory"
import { MedicationDetail } from "./pages/medication-detail"
import { PurchaseOrders } from "./pages/purchase-orders"
import { CreatePO } from "./pages/create-po"
import { CreatePOEnhanced } from "./pages/create-po-enhanced"
import { Toaster } from "@/components/ui/sonner"
import "./App.css"

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 1,
    },
  },
})

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="pharma-ui-theme">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="min-h-screen bg-background font-sans antialiased">
            <Routes>
              <Route path="/" element={<MainLayout />}>
                <Route index element={<Dashboard />} />
                <Route path="/inventory" element={<Inventory />} />
                <Route path="/medication/:id" element={<MedicationDetail />} />
                <Route path="/purchase-orders" element={<PurchaseOrders />} />
                <Route path="/purchase-orders/:id" element={<div className="p-4">PO Detail Page Coming Soon</div>} />
                <Route path="/create-po" element={<CreatePOEnhanced />} />
                <Route path="/create-po-legacy" element={<CreatePO />} />
                <Route path="/analytics" element={<div className="p-4">Analytics Page Coming Soon</div>} />
                <Route path="/settings" element={<div className="p-4">Settings Page Coming Soon</div>} />
              </Route>
            </Routes>
            <Toaster />
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
