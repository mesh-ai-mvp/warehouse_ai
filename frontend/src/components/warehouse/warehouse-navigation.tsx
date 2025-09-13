import React from 'react';
import { motion } from 'motion/react';
import {
  Home,
  ChevronRight,
  ChevronLeft,
  Wifi,
  WifiOff,
  Search,
  Menu,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ViewState, Aisle, Shelf } from './warehouse-types';

interface WarehouseNavigationProps {
  currentView: ViewState;
  selectedAisle: Aisle | null;
  selectedShelf: Shelf | null;
  onNavigateBack: () => void;
  onNavigateHome: () => void;
  isConnected: boolean;
  connectionStatus: string;
  onTogglePanel?: () => void;
  isPanelOpen?: boolean;
  onToggleMonitoring?: () => void;
  isMonitoringOpen?: boolean;
}

export function WarehouseNavigation({
  currentView,
  selectedAisle,
  selectedShelf,
  onNavigateBack,
  onNavigateHome,
  isConnected,
  connectionStatus,
  onTogglePanel,
  isPanelOpen = false,
  onToggleMonitoring,
  isMonitoringOpen = false
}: WarehouseNavigationProps) {
  const getBreadcrumbs = () => {
    const crumbs = [
      { label: 'Warehouse', onClick: onNavigateHome, active: currentView === 'warehouse' }
    ];

    if (selectedAisle) {
      crumbs.push({
        label: selectedAisle.name,
        onClick: currentView === 'shelf' ? onNavigateBack : undefined,
        active: currentView === 'aisle'
      });
    }

    if (selectedShelf && currentView === 'shelf') {
      crumbs.push({
        label: `Shelf ${selectedShelf.position + 1}`,
        onClick: undefined,
        active: true
      });
    }

    return crumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="absolute top-0 left-0 right-0 z-20 bg-slate-900/80 backdrop-blur-md border-b border-slate-700/50"
    >
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left Section - Navigation */}
        <div className="flex items-center gap-4">
          {/* Menu Toggle for Floating Panel */}
          {onTogglePanel && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onTogglePanel}
              className="text-slate-400 hover:text-white"
            >
              {isPanelOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          )}

          {/* Navigation Buttons */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onNavigateHome}
              className="text-slate-400 hover:text-white"
              disabled={currentView === 'warehouse'}
            >
              <Home className="w-4 h-4" />
            </Button>

            {currentView !== 'warehouse' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onNavigateBack}
                className="text-slate-400 hover:text-white"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
            )}
          </div>

          {/* Breadcrumbs */}
          <div className="flex items-center gap-2">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && (
                  <ChevronRight className="w-4 h-4 text-slate-600" />
                )}
                <button
                  onClick={crumb.onClick}
                  disabled={!crumb.onClick}
                  className={`
                    px-2 py-1 rounded text-sm transition-colors
                    ${crumb.active
                      ? 'text-white font-medium bg-slate-800/50'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/30 cursor-pointer'
                    }
                    ${!crumb.onClick ? 'cursor-default' : ''}
                  `}
                >
                  {crumb.label}
                </button>
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Center Section - Title */}
        <div className="flex-1 text-center">
          <h1 className="text-white text-lg font-medium">MediCore Warehouse Management</h1>
        </div>

        {/* Right Section - Status and Controls */}
        <div className="flex items-center gap-4">
          {/* Monitoring Toggle */}
          {onToggleMonitoring && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleMonitoring}
              className={`text-slate-400 hover:text-white ${isMonitoringOpen ? 'bg-slate-800/50' : ''}`}
            >
              <span className="text-xs">Monitoring</span>
            </Button>
          )}

          {/* Connection Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/20 backdrop-blur-sm">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-green-500" />
                <span className="text-xs text-green-400">Live Updates</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-xs text-red-400">
                  {connectionStatus === 'connecting' ? 'Connecting...' : 'Offline'}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}