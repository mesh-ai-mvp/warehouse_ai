import React from 'react';
import { motion } from 'framer-motion';
import {
  Home,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { ViewState, Aisle, Shelf } from './warehouse-types';

interface WarehouseNavigationProps {
  currentView: ViewState;
  selectedAisle: Aisle | null;
  selectedShelf: Shelf | null;
  onNavigateBack: () => void;
  onNavigateHome: () => void;
  isConnected?: boolean;
  connectionStatus?: string;
}

export function WarehouseNavigation({
  currentView,
  selectedAisle,
  selectedShelf,
  onNavigateBack,
  onNavigateHome,
  isConnected,
  connectionStatus
}: WarehouseNavigationProps) {
  const showBackButton = currentView !== 'warehouse';

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center gap-4"
    >
      {/* Back Navigation */}
      {showBackButton && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onNavigateBack}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Back
        </Button>
      )}

      {/* Breadcrumb Navigation */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            {currentView === 'warehouse' ? (
              <BreadcrumbPage>Warehouse Overview</BreadcrumbPage>
            ) : (
              <BreadcrumbLink
                onClick={onNavigateHome}
                className="cursor-pointer"
              >
                Warehouse Overview
              </BreadcrumbLink>
            )}
          </BreadcrumbItem>

          {selectedAisle && (
            <>
              <BreadcrumbSeparator>
                <ChevronRight className="w-4 h-4" />
              </BreadcrumbSeparator>
              <BreadcrumbItem>
                {currentView === 'aisle' ? (
                  <BreadcrumbPage>{selectedAisle.name}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink
                    onClick={onNavigateBack}
                    className="cursor-pointer"
                  >
                    {selectedAisle.name}
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </>
          )}

          {selectedShelf && currentView === 'shelf' && (
            <>
              <BreadcrumbSeparator>
                <ChevronRight className="w-4 h-4" />
              </BreadcrumbSeparator>
              <BreadcrumbItem>
                <BreadcrumbPage>Shelf {selectedShelf.position + 1}</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>
    </motion.div>
  );
}