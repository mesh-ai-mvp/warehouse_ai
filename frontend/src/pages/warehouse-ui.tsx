import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { WarehouseOverview } from '@/components/warehouse/warehouse-overview';
import { AisleView } from '@/components/warehouse/aisle-view';
import { ShelfDetail } from '@/components/warehouse/shelf-detail';
import { WarehouseNavigation } from '@/components/warehouse/warehouse-navigation';
import { FloatingPanel } from '@/components/warehouse/floating-panel';
import { MonitoringOverlay } from '@/components/warehouse/monitoring-overlay';
import { MedicationSearch } from '@/components/warehouse/medication-search';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, AlertCircle, Search, X } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ViewState, Medication, Shelf, Aisle } from '@/components/warehouse/warehouse-types';
import { useWarehouseLayout, useAisleDetails, useDetailedShelfLayout } from '@/hooks/useWarehouseQueries';
import { useWarehouseWebSocket } from '@/hooks/useWarehouseWebSocket';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';
import type { Aisle as ApiAisle, Shelf as ApiShelf, ShelfMedication } from '@/types/warehouse';

// Transform API data to component format
const transformApiToComponentAisle = (apiAisle: ApiAisle, apiShelves?: ApiShelf[]): Aisle => {
  return {
    id: apiAisle.aisle_id.toString(),
    name: apiAisle.aisle_name,
    position: {
      x: apiAisle.position_x,
      z: apiAisle.position_z
    },
    category: apiAisle.category,
    temperature: apiAisle.temperature,
    shelves: apiShelves?.map(shelf => transformApiToComponentShelf(shelf)) || [],
    shelfCount: (apiAisle as any).shelf_count ?? (apiShelves?.length || 0),
    medicationCount: (apiAisle as any).total_items ?? (apiAisle as any).medication_count ?? 0
  };
};

const transformApiToComponentShelf = (apiShelf: ApiShelf): Shelf => {
  return {
    id: apiShelf.shelf_id.toString(),
    position: apiShelf.position,
    level: apiShelf.level,
    capacity: apiShelf.capacity_slots,
    medications: apiShelf.medications?.map(med => transformApiToComponentMedication(med)) || [],
    code: (apiShelf as any).shelf_code
  };
};

const transformApiToComponentMedication = (apiMed: ShelfMedication): Medication => {
  return {
    id: apiMed.med_id.toString(),
    name: apiMed.name,
    quantity: apiMed.quantity,
    maxCapacity: 300, // Default capacity, could be enhanced
    expiryDate: apiMed.expiry_date || '2025-12-31',
    batchNumber: apiMed.batch_id?.toString() || 'N/A',
    temperature: 22 // Default temperature, could be from aisle
  };
};

const mockMedications: Medication[] = [
  // General Medications
  {
    id: 'med1',
    name: 'Paracetamol 500mg',
    quantity: 245,
    maxCapacity: 300,
    expiryDate: '2025-12-15',
    batchNumber: 'PCT001',
    temperature: 22
  },
  {
    id: 'med2',
    name: 'Ibuprofen 400mg',
    quantity: 180,
    maxCapacity: 250,
    expiryDate: '2025-09-30',
    batchNumber: 'IBU002',
    temperature: 21
  },
  {
    id: 'med3',
    name: 'Aspirin 325mg',
    quantity: 320,
    maxCapacity: 400,
    expiryDate: '2026-01-10',
    batchNumber: 'ASP003',
    temperature: 22
  },
  {
    id: 'med4',
    name: 'Omeprazole 20mg',
    quantity: 150,
    maxCapacity: 200,
    expiryDate: '2025-08-25',
    batchNumber: 'OMP004',
    temperature: 22
  },
  {
    id: 'med5',
    name: 'Metformin 850mg',
    quantity: 280,
    maxCapacity: 350,
    expiryDate: '2025-11-30',
    batchNumber: 'MET005',
    temperature: 22
  },
  {
    id: 'med6',
    name: 'Lisinopril 10mg',
    quantity: 190,
    maxCapacity: 250,
    expiryDate: '2025-10-15',
    batchNumber: 'LIS006',
    temperature: 22
  },
  {
    id: 'med7',
    name: 'Simvastatin 40mg',
    quantity: 160,
    maxCapacity: 200,
    expiryDate: '2025-07-20',
    batchNumber: 'SIM007',
    temperature: 22
  },
  {
    id: 'med8',
    name: 'Amlodipine 5mg',
    quantity: 220,
    maxCapacity: 300,
    expiryDate: '2025-09-12',
    batchNumber: 'AML008',
    temperature: 22
  },
  // Refrigerated Medications
  {
    id: 'med9',
    name: 'Insulin Glargine',
    quantity: 45,
    maxCapacity: 60,
    expiryDate: '2025-06-15',
    batchNumber: 'INS009',
    temperature: 4
  },
  {
    id: 'med10',
    name: 'Amoxicillin Suspension',
    quantity: 35,
    maxCapacity: 50,
    expiryDate: '2025-05-30',
    batchNumber: 'AMX010',
    temperature: 4
  },
  {
    id: 'med11',
    name: 'Human Growth Hormone',
    quantity: 25,
    maxCapacity: 30,
    expiryDate: '2025-04-20',
    batchNumber: 'HGH011',
    temperature: 4
  },
  {
    id: 'med12',
    name: 'Epinephrine Auto-Injector',
    quantity: 40,
    maxCapacity: 50,
    expiryDate: '2025-08-10',
    batchNumber: 'EPI012',
    temperature: 4
  },
  // Controlled Substances
  {
    id: 'med13',
    name: 'Morphine Sulfate 30mg',
    quantity: 15,
    maxCapacity: 20,
    expiryDate: '2025-12-31',
    batchNumber: 'MOR013',
    temperature: 22
  },
  {
    id: 'med14',
    name: 'OxyContin 20mg',
    quantity: 12,
    maxCapacity: 15,
    expiryDate: '2025-11-15',
    batchNumber: 'OXY014',
    temperature: 22
  },
  {
    id: 'med15',
    name: 'Lorazepam 2mg',
    quantity: 25,
    maxCapacity: 30,
    expiryDate: '2025-10-05',
    batchNumber: 'LOR015',
    temperature: 22
  },
  // Quarantine Items
  {
    id: 'med16',
    name: 'Recalled Batch - Metoprolol',
    quantity: 50,
    maxCapacity: 100,
    expiryDate: '2024-12-01',
    batchNumber: 'MET016',
    temperature: 22
  }
];

const mockAisles: Aisle[] = [
  {
    id: 'aisle1',
    name: 'General Pharmaceuticals A',
    position: { x: 0, z: 0 },
    category: 'General',
    temperature: 22,
    shelves: Array.from({ length: 8 }, (_, i) => ({
      id: `shelf-a-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 300,
      medications: i < 6 ? [mockMedications[i % 8]] : []
    }))
  },
  {
    id: 'aisle2',
    name: 'General Pharmaceuticals B',
    position: { x: 1, z: 0 },
    category: 'General',
    temperature: 22,
    shelves: Array.from({ length: 8 }, (_, i) => ({
      id: `shelf-b-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 300,
      medications: i < 5 ? [mockMedications[(i + 3) % 8]] : []
    }))
  },
  {
    id: 'aisle3',
    name: 'Cold Chain Storage',
    position: { x: 2, z: 0 },
    category: 'Refrigerated',
    temperature: 4,
    shelves: Array.from({ length: 6 }, (_, i) => ({
      id: `shelf-c-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 200,
      medications: i < 4 ? [mockMedications[8 + (i % 4)]] : []
    }))
  },
  {
    id: 'aisle4',
    name: 'Controlled Substances',
    position: { x: 0, z: 1 },
    category: 'Controlled',
    temperature: 22,
    shelves: Array.from({ length: 4 }, (_, i) => ({
      id: `shelf-d-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 150,
      medications: i < 3 ? [mockMedications[12 + i]] : []
    }))
  },
  {
    id: 'aisle5',
    name: 'Quarantine Zone',
    position: { x: 1, z: 1 },
    category: 'Quarantine',
    temperature: 22,
    shelves: Array.from({ length: 4 }, (_, i) => ({
      id: `shelf-q-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 100,
      medications: i === 0 ? [mockMedications[15]] : []
    }))
  },
  {
    id: 'aisle6',
    name: 'Office & Administration',
    position: { x: 2, z: 1 },
    category: 'Office',
    temperature: 23,
    shelves: Array.from({ length: 4 }, (_, i) => ({
      id: `shelf-o-${i}`,
      position: i,
      level: Math.floor(i / 2),
      capacity: 200,
      medications: i < 2 ? [mockMedications[6 + i]] : []
    }))
  }
];

export function WarehouseUI() {
  const [currentView, setCurrentView] = useState<ViewState>('warehouse');
  const [selectedAisle, setSelectedAisle] = useState<Aisle | null>(null);
  const [selectedAisleId, setSelectedAisleId] = useState<string | null>(null);
  const [selectedShelf, setSelectedShelf] = useState<Shelf | null>(null);
  const [selectedShelfId, setSelectedShelfId] = useState<string | null>(null);
  const [legendCollapsed, setLegendCollapsed] = useState(false);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isMonitoringOpen, setIsMonitoringOpen] = useState(false);
  const [isMonitoringExpanded, setIsMonitoringExpanded] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  // Fetch warehouse layout
  const { data: warehouseLayout, isLoading, error } = useWarehouseLayout({ refetchInterval: 30000 });

  // Fetch aisle details when an aisle is selected
  const { data: aisleDetails } = useAisleDetails(selectedAisleId, { enabled: !!selectedAisleId });

  // Fetch shelf details when a shelf is selected
  const { data: shelfDetails } = useDetailedShelfLayout(selectedShelfId, { enabled: !!selectedShelfId });

  // Initialize query client for cache invalidation
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // WebSocket connection for real-time updates
  const { isConnected, connectionStatus } = useWarehouseWebSocket({
    clientId: `warehouse-ui-${Date.now()}`,
    subscriptions: ['temperature', 'inventory', 'alerts', 'shelf'],
    onMessage: (message) => {
      // Handle different message types
      switch (message.type) {
        case 'temperature_update':
          // Invalidate temperature queries
          queryClient.invalidateQueries({ queryKey: ['warehouse', 'temperature'] });
          break;

        case 'inventory_movement':
          // Invalidate relevant queries when inventory moves
          queryClient.invalidateQueries({ queryKey: ['warehouse', 'layout'] });
          if (message.data?.from_shelf || message.data?.to_shelf) {
            queryClient.invalidateQueries({ queryKey: ['warehouse', 'shelf'] });
          }
          // Show toast notification
          toast({
            title: 'Inventory Movement',
            description: `Medication moved from shelf ${message.data?.from_shelf} to ${message.data?.to_shelf}`,
          });
          break;

        case 'alert_triggered':
          // Show alert notification
          const severity = message.data?.severity || 'info';
          toast({
            title: severity === 'critical' ? '⚠️ Critical Alert' : '📢 Alert',
            description: message.data?.message || 'New alert triggered',
            variant: severity === 'critical' ? 'destructive' : 'default',
          });
          // Invalidate alerts query
          queryClient.invalidateQueries({ queryKey: ['warehouse', 'alerts'] });
          break;

        case 'shelf_update':
          // Invalidate shelf-specific queries
          if (message.data?.shelf_id) {
            queryClient.invalidateQueries({
              queryKey: ['warehouse', 'shelf', message.data.shelf_id.toString()]
            });
          }
          break;

        case 'medication_expiry':
        case 'capacity_warning':
          // Invalidate alerts and show notification
          queryClient.invalidateQueries({ queryKey: ['warehouse', 'alerts'] });
          toast({
            title: message.type === 'medication_expiry' ? '⏰ Expiry Warning' : '📦 Capacity Warning',
            description: message.data?.message || 'Check alerts panel for details',
          });
          break;
      }
    },
    onConnect: () => {
      console.log('Connected to warehouse WebSocket');
    },
    onDisconnect: () => {
      console.log('Disconnected from warehouse WebSocket');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    }
  });

  // Transform API data to component format
  const aisles = useMemo(() => {
    if (!warehouseLayout) return mockAisles; // Fallback to mock data if API fails

    return warehouseLayout.aisles.map(apiAisle => {
      // Find shelves for this aisle if we have the details
      const shelvesForAisle = aisleDetails?.aisle.aisle_id === apiAisle.aisle_id
        ? aisleDetails.shelves
        : [];

      return transformApiToComponentAisle(apiAisle, shelvesForAisle);
    });
  }, [warehouseLayout, aisleDetails]);

  // Update selected aisle data when details are fetched
  const selectedAisleWithDetails = useMemo(() => {
    if (!selectedAisle || !aisleDetails) return selectedAisle;

    // Group medications by shelf_id
    const medicationsByShelf: { [key: string]: any[] } = {};
    if (aisleDetails.medications) {
      aisleDetails.medications.forEach((med: any) => {
        const shelfId = med.shelf_id?.toString();
        if (shelfId) {
          if (!medicationsByShelf[shelfId]) {
            medicationsByShelf[shelfId] = [];
          }
          medicationsByShelf[shelfId].push(med);
        }
      });
    }

    return {
      ...selectedAisle,
      shelves: aisleDetails.shelves.map(shelf => {
        // Add medications to each shelf
        const shelfWithMeds = {
          ...shelf,
          medications: medicationsByShelf[shelf.shelf_id.toString()] || []
        };
        return transformApiToComponentShelf(shelfWithMeds);
      })
    };
  }, [selectedAisle, aisleDetails]);

  const handleAisleClick = (aisle: Aisle) => {
    setSelectedAisle(aisle);
    setSelectedAisleId(aisle.id);
    setCurrentView('aisle');
    setIsPanelOpen(false); // Close panel when navigating
  };

  const handleShelfClick = (shelf: Shelf) => {
    setSelectedShelf(shelf);
    setSelectedShelfId(shelf.id);
    setCurrentView('shelf');
  };

  const navigateBack = () => {
    if (currentView === 'shelf') {
      setCurrentView('aisle');
      setSelectedShelf(null);
      setSelectedShelfId(null);
    } else if (currentView === 'aisle') {
      setCurrentView('warehouse');
      setSelectedAisle(null);
      setSelectedAisleId(null);
    }
  };

  const navigateHome = () => {
    setCurrentView('warehouse');
    setSelectedAisle(null);
    setSelectedAisleId(null);
    setSelectedShelf(null);
    setSelectedShelfId(null);
  };

  const handleSearchResultClick = (result: any) => {
    // Navigate to the aisle containing the medication
    const targetAisle = aisles.find(a => a.id === result.aisleId);
    if (targetAisle) {
      setSelectedAisle(targetAisle);
      setSelectedAisleId(targetAisle.id);
      setCurrentView('aisle');
      setSearchOpen(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground text-lg">Loading warehouse data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-8">
        <Alert className="max-w-md" variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load warehouse data. Using demo data instead.
            <br />
            <span className="text-xs text-muted-foreground mt-2 block">
              Error: {(error as Error).message}
            </span>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="relative space-y-6">
      {/* Page Header with Breadcrumb Navigation */}
      <div className="flex flex-col gap-4">
        <WarehouseNavigation
          currentView={currentView}
          selectedAisle={selectedAisle}
          selectedShelf={selectedShelf}
          onNavigateBack={navigateBack}
          onNavigateHome={navigateHome}
          isConnected={isConnected}
          connectionStatus={connectionStatus}
        />

        {/* Control Buttons */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPanelOpen(!isPanelOpen)}
            >
              {isPanelOpen ? 'Hide Panel' : 'Show Panel'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsMonitoringOpen(!isMonitoringOpen)}
            >
              {isMonitoringOpen ? 'Hide Monitoring' : 'Show Monitoring'}
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isConnected ? 'default' : 'destructive'}>
              <div className={`w-2 h-2 rounded-full mr-1 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              {connectionStatus}
            </Badge>
          </div>
        </div>
      </div>

      {/* Floating Control Panel */}
      <FloatingPanel
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        aisles={aisles}
        onAisleSelect={handleAisleClick}
        selectedAisle={selectedAisle}
      />

      {/* Monitoring Overlay */}
      <MonitoringOverlay
        isOpen={isMonitoringOpen}
        onClose={() => setIsMonitoringOpen(false)}
        isExpanded={isMonitoringExpanded}
        onToggleExpand={() => setIsMonitoringExpanded(!isMonitoringExpanded)}
      />

      {/* Search Bar */}
      <AnimatePresence>
        {currentView === 'warehouse' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {!searchOpen ? (
              <Button
                variant="outline"
                className="w-full max-w-md mx-auto flex items-center gap-2"
                onClick={() => setSearchOpen(true)}
              >
                <Search className="w-4 h-4" />
                <span>Search medications...</span>
              </Button>
            ) : (
              <Card className="max-w-2xl mx-auto p-4 relative">
                <MedicationSearch
                  onResultClick={handleSearchResultClick}
                  onAisleNavigate={(aisleId) => {
                    const targetAisle = aisles.find(a => a.id === aisleId);
                    if (targetAisle) {
                      handleAisleClick(targetAisle);
                    }
                  }}
                  currentAisles={aisles}
                />
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2"
                  onClick={() => setSearchOpen(false)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="relative">
        <AnimatePresence mode="wait">
          {currentView === 'warehouse' && (
            <motion.div
              key="warehouse"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              transition={{ duration: 0.5, ease: [0.23, 1, 0.320, 1] }}
            >
              <WarehouseOverview
                aisles={aisles}
                onAisleClick={handleAisleClick}
                legendCollapsed={legendCollapsed}
                onToggleLegend={() => setLegendCollapsed(!legendCollapsed)}
              />
            </motion.div>
          )}

          {currentView === 'aisle' && selectedAisleWithDetails && (
            <motion.div
              key="aisle"
              initial={{ opacity: 0, x: 100 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -100 }}
              transition={{ duration: 0.5, ease: [0.23, 1, 0.320, 1] }}
            >
              <AisleView
                aisle={selectedAisleWithDetails}
                onShelfClick={handleShelfClick}
                onBack={navigateBack}
              />
            </motion.div>
          )}

          {currentView === 'shelf' && selectedShelf && selectedAisleWithDetails && (
            <motion.div
              key="shelf"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50 }}
              transition={{ duration: 0.4, ease: [0.23, 1, 0.320, 1] }}
            >
              <ShelfDetail
                shelf={selectedShelf}
                aisleName={selectedAisleWithDetails.name}
                onBack={navigateBack}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}