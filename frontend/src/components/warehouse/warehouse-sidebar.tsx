import React from 'react';
import { motion } from 'motion/react';
import {
  Home,
  Package,
  Thermometer,
  AlertTriangle,
  TrendingUp,
  Calendar,
  Settings,
  Search,
  Bell,
  ChevronLeft,
  ChevronRight,
  Menu,
  Download
} from 'lucide-react';
import { ViewState, Aisle, Shelf } from './warehouse-types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ExportWarehouseData } from './export-warehouse-data';

interface WarehouseSidebarProps {
  currentView: ViewState;
  selectedAisle: Aisle | null;
  selectedShelf: Shelf | null;
  aisles: Aisle[];
  onNavigateBack: () => void;
  onNavigateHome: () => void;
  onAisleSelect: (aisle: Aisle) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function WarehouseSidebar({
  currentView,
  selectedAisle,
  selectedShelf,
  aisles,
  onNavigateBack,
  onNavigateHome,
  onAisleSelect,
  collapsed,
  onToggleCollapse
}: WarehouseSidebarProps) {
  const getTotalMedications = () => {
    return aisles.reduce((acc, aisle) =>
      acc + aisle.shelves.reduce((shelfAcc, shelf) =>
        shelfAcc + shelf.medications.length, 0), 0);
  };

  const getExpiringMedications = () => {
    const today = new Date();
    const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);

    let expiringCount = 0;
    aisles.forEach(aisle => {
      aisle.shelves.forEach(shelf => {
        shelf.medications.forEach(med => {
          const expiryDate = new Date(med.expiryDate);
          if (expiryDate <= thirtyDaysFromNow) {
            expiringCount++;
          }
        });
      });
    });
    return expiringCount;
  };

  const getAisleUtilization = (aisle: Aisle) => {
    const totalMeds = aisle.shelves.reduce((acc, shelf) => acc + shelf.medications.length, 0);
    const totalCapacity = aisle.shelves.length;
    return totalCapacity > 0 ? (totalMeds / totalCapacity) * 100 : 0;
  };

  const totalMedications = getTotalMedications();
  const expiringMedications = getExpiringMedications();

  return (
    <motion.div
      initial={{ x: -300, opacity: 0 }}
      animate={{
        x: 0,
        opacity: 1,
        width: collapsed ? '80px' : '320px'
      }}
      transition={{ duration: 0.6, ease: [0.23, 1, 0.320, 1] }}
      className="bg-slate-900/95 backdrop-blur-sm border-r border-slate-700/50 flex flex-col h-full relative"
    >
      {/* Collapse Toggle */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onToggleCollapse}
        className="absolute -right-3 top-4 z-50 w-6 h-6 p-0 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-full"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3 text-slate-300" />
        ) : (
          <ChevronLeft className="w-3 h-3 text-slate-300" />
        )}
      </Button>
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Package className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, delay: 0.1 }}
            >
              <h1 className="text-white font-medium">MediCore</h1>
              <p className="text-slate-400 text-sm">Warehouse Management</p>
            </motion.div>
          )}
        </div>

        {/* Search */}
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            className="relative"
          >
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search medications..."
              className="pl-10 bg-slate-800/50 border-slate-700 text-white placeholder-slate-400"
            />
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <div className="p-4 border-b border-slate-700/50">
        <div className={`flex ${collapsed ? 'flex-col' : ''} gap-2`}>
          <Button
            variant={currentView === 'warehouse' ? 'default' : 'ghost'}
            size="sm"
            onClick={onNavigateHome}
            className={collapsed ? 'w-full justify-center p-2' : 'flex-1'}
            title={collapsed ? 'Overview' : undefined}
          >
            <Home className="w-4 h-4" />
            {!collapsed && <span className="ml-2">Overview</span>}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={`text-slate-400 ${collapsed ? 'w-full justify-center p-2' : ''}`}
            title={collapsed ? 'Notifications' : undefined}
          >
            <Bell className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={`text-slate-400 ${collapsed ? 'w-full justify-center p-2' : ''}`}
            title={collapsed ? 'Settings' : undefined}
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      {!collapsed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, delay: 0.1 }}
          className="p-4 border-b border-slate-700/50"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-medium">Quick Stats</h3>
            <ExportWarehouseData />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Card className="p-3 bg-slate-800/50 border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <Package className="w-4 h-4 text-blue-400" />
                <span className="text-slate-400 text-xs">Total Items</span>
              </div>
              <div className="text-white text-lg">{totalMedications}</div>
            </Card>

            <Card className="p-3 bg-slate-800/50 border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4 text-orange-400" />
                <span className="text-slate-400 text-xs">Expiring</span>
              </div>
              <div className="text-white text-lg">{expiringMedications}</div>
            </Card>
          </div>
        </motion.div>
      )}

      {/* Current Context */}
      {currentView !== 'warehouse' && !collapsed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2, delay: 0.1 }}
          className="p-4 border-b border-slate-700/50"
        >
          <h3 className="text-white font-medium mb-3">Current Location</h3>
          <div className="space-y-2">
            {selectedAisle && (
              <div className="text-sm">
                <div className="text-slate-400">Aisle:</div>
                <div className="text-white">{selectedAisle.name}</div>
              </div>
            )}
            {selectedShelf && (
              <div className="text-sm">
                <div className="text-slate-400">Shelf:</div>
                <div className="text-white">Position {selectedShelf.position + 1}, Level {selectedShelf.level + 1}</div>
              </div>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onNavigateBack}
            className="w-full mt-3 border-slate-600 text-slate-300 hover:bg-slate-700"
          >
            Go Back
          </Button>
        </motion.div>
      )}

      {/* Collapsed Context */}
      {currentView !== 'warehouse' && collapsed && (
        <div className="p-2 border-b border-slate-700/50 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={onNavigateBack}
            className="w-10 h-10 p-0 border-slate-600 text-slate-300 hover:bg-slate-700"
            title="Go Back"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Aisles List */}
      <div className="flex-1 overflow-auto p-4">
        {!collapsed && (
          <motion.h3
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            className="text-white font-medium mb-3"
          >
            Warehouse Aisles
          </motion.h3>
        )}
        <div className="space-y-2">
          {aisles.map((aisle, index) => {
            const utilization = getAisleUtilization(aisle);
            const isSelected = selectedAisle?.id === aisle.id;

            return (
              <motion.div
                key={aisle.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Card
                  className={`cursor-pointer transition-all ${
                    collapsed ? 'p-2' : 'p-3'
                  } ${
                    isSelected
                      ? 'bg-blue-900/50 border-blue-500/50'
                      : 'bg-slate-800/30 border-slate-700 hover:bg-slate-800/50'
                  }`}
                  onClick={() => onAisleSelect(aisle)}
                  title={collapsed ? aisle.name : undefined}
                >
                  {collapsed ? (
                    <div className="flex flex-col items-center">
                      <div className="flex items-center gap-1 mb-1">
                        {aisle.category === 'Refrigerated' && (
                          <Thermometer className="w-4 h-4 text-blue-400" />
                        )}
                        {aisle.category === 'Controlled' && (
                          <AlertTriangle className="w-4 h-4 text-yellow-400" />
                        )}
                        {aisle.category === 'General' && (
                          <Package className="w-4 h-4 text-green-400" />
                        )}
                        {aisle.category === 'Quarantine' && (
                          <AlertTriangle className="w-4 h-4 text-red-400" />
                        )}
                        {aisle.category === 'Office' && (
                          <Package className="w-4 h-4 text-purple-400" />
                        )}
                      </div>
                      <div className="text-white text-xs font-medium">
                        {String.fromCharCode(65 + index)}
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <div className="text-white text-sm font-medium">
                            {aisle.name}
                          </div>
                          <div className="text-slate-400 text-xs">
                            {aisle.category}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {aisle.category === 'Refrigerated' && (
                            <Thermometer className="w-3 h-3 text-blue-400" />
                          )}
                          {aisle.category === 'Controlled' && (
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                          )}
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          {aisle.shelves.length} shelves
                        </span>
                        <Badge
                          variant="secondary"
                          className={`text-xs ${
                            utilization > 80 ? 'bg-green-900 text-green-300' :
                            utilization > 40 ? 'bg-yellow-900 text-yellow-300' :
                            utilization > 0 ? 'bg-orange-900 text-orange-300' :
                            'bg-gray-900 text-gray-300'
                          }`}
                        >
                          {utilization.toFixed(0)}%
                        </Badge>
                      </div>

                      {/* Temperature indicator for refrigerated areas */}
                      {aisle.category === 'Refrigerated' && (
                        <div className="mt-2 text-xs text-slate-400">
                          <Thermometer className="w-3 h-3 inline mr-1" />
                          {aisle.temperature}°C
                        </div>
                      )}
                    </>
                  )}
                </Card>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Alerts */}
      {expiringMedications > 0 && (
        <div className="p-4 border-t border-slate-700/50">
          <Card className="p-3 bg-orange-900/20 border-orange-500/50">
            {collapsed ? (
              <div className="flex justify-center">
                <AlertTriangle className="w-5 h-5 text-orange-300" title={`${expiringMedications} items expiring soon`} />
              </div>
            ) : (
              <div className="flex items-center gap-2 text-orange-300 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>{expiringMedications} items expiring soon</span>
              </div>
            )}
          </Card>
        </div>
      )}
    </motion.div>
  );
}