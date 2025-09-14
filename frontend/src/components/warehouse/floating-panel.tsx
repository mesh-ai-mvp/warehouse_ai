import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Package,
  Calendar,
  Thermometer,
  AlertTriangle,
  Download,
  X,
  ChevronRight
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Aisle } from './warehouse-types';
import { ExportWarehouseData } from './export-warehouse-data';

interface FloatingPanelProps {
  isOpen: boolean;
  onClose: () => void;
  aisles: Aisle[];
  onAisleSelect: (aisle: Aisle) => void;
  selectedAisle: Aisle | null;
}

export function FloatingPanel({
  isOpen,
  onClose,
  aisles,
  onAisleSelect,
  selectedAisle
}: FloatingPanelProps) {
  const [searchQuery, setSearchQuery] = React.useState('');

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

  const getCriticalAlerts = () => {
    let criticalCount = 0;
    aisles.forEach(aisle => {
      if (aisle.category === 'Refrigerated' && aisle.temperature > 8) {
        criticalCount++;
      }
      if (aisle.category === 'Quarantine' && aisle.shelves.some(s => s.medications.length > 0)) {
        criticalCount++;
      }
    });
    return criticalCount;
  };

  const filteredAisles = aisles.filter(aisle =>
    aisle.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    aisle.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalMedications = getTotalMedications();
  const expiringMedications = getExpiringMedications();
  const criticalAlerts = getCriticalAlerts();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: -400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -400, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.23, 1, 0.320, 1] }}
          className="fixed left-4 top-20 z-30 w-80 max-h-[calc(100vh-6rem)] bg-card/95 backdrop-blur-md rounded-xl border shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="p-4 border-b border-slate-700/50">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-white font-medium text-lg">Warehouse Control</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="w-8 h-8 p-0 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Search */}
            <div className="relative">
              <Input
                placeholder="Search aisles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-3 pr-8 bg-slate-800/50 border-slate-700 text-white placeholder-slate-400"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="p-4 border-b border-slate-700/50">
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
                <div className="text-white text-lg font-medium">{totalMedications}</div>
              </Card>

              <Card className="p-3 bg-slate-800/50 border-slate-700">
                <div className="flex items-center gap-2 mb-1">
                  <Calendar className="w-4 h-4 text-orange-400" />
                  <span className="text-slate-400 text-xs">Expiring Soon</span>
                </div>
                <div className="text-white text-lg font-medium">{expiringMedications}</div>
              </Card>

              <Card className="p-3 bg-slate-800/50 border-slate-700">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="text-slate-400 text-xs">Critical Alerts</span>
                </div>
                <div className="text-white text-lg font-medium">{criticalAlerts}</div>
              </Card>

              <Card className="p-3 bg-slate-800/50 border-slate-700">
                <div className="flex items-center gap-2 mb-1">
                  <Thermometer className="w-4 h-4 text-cyan-400" />
                  <span className="text-slate-400 text-xs">Cold Storage</span>
                </div>
                <div className="text-white text-lg font-medium">
                  {aisles.filter(a => a.category === 'Refrigerated').length}
                </div>
              </Card>
            </div>
          </div>

          {/* Aisles List */}
          <div className="flex-1 overflow-y-auto p-4">
            <h3 className="text-white font-medium mb-3">Warehouse Aisles</h3>

            {filteredAisles.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-slate-400 text-sm">No aisles found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredAisles.map((aisle, index) => {
                  const utilization = getAisleUtilization(aisle);
                  const isSelected = selectedAisle?.id === aisle.id;

                  return (
                    <motion.div
                      key={aisle.id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Card
                        className={`
                          cursor-pointer transition-all p-3
                          ${isSelected
                            ? 'bg-blue-900/50 border-blue-500/50'
                            : 'bg-slate-800/30 border-slate-700 hover:bg-slate-800/50'
                          }
                        `}
                        onClick={() => onAisleSelect(aisle)}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <div className="text-white text-sm font-medium">
                                {aisle.name}
                              </div>
                              <ChevronRight className="w-3 h-3 text-slate-500" />
                            </div>
                            <div className="text-slate-400 text-xs mt-1">
                              {aisle.category} • Zone {String.fromCharCode(65 + index)}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {aisle.category === 'Refrigerated' && (
                              <Thermometer className="w-3 h-3 text-blue-400" />
                            )}
                            {aisle.category === 'Controlled' && (
                              <AlertTriangle className="w-3 h-3 text-yellow-400" />
                            )}
                            {aisle.category === 'Quarantine' && (
                              <AlertTriangle className="w-3 h-3 text-red-400" />
                            )}
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">
                            {aisle.shelves.length} shelves • {aisle.shelves.reduce((acc, shelf) => acc + shelf.medications.length, 0)} items
                          </span>
                          <Badge
                            variant="secondary"
                            className={`text-xs ${
                              utilization > 80 ? 'bg-green-900/50 text-green-300' :
                              utilization > 40 ? 'bg-yellow-900/50 text-yellow-300' :
                              utilization > 0 ? 'bg-orange-900/50 text-orange-300' :
                              'bg-gray-900/50 text-gray-300'
                            }`}
                          >
                            {utilization.toFixed(0)}%
                          </Badge>
                        </div>

                        {/* Temperature for refrigerated */}
                        {aisle.category === 'Refrigerated' && (
                          <div className="mt-2 flex items-center gap-1 text-xs text-cyan-400">
                            <Thermometer className="w-3 h-3" />
                            <span>{aisle.temperature}°C</span>
                          </div>
                        )}
                      </Card>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer Alerts */}
          {(expiringMedications > 0 || criticalAlerts > 0) && (
            <div className="p-4 border-t border-slate-700/50 space-y-2">
              {expiringMedications > 0 && (
                <Card className="p-2 bg-orange-900/20 border-orange-500/50">
                  <div className="flex items-center gap-2 text-orange-300 text-sm">
                    <Calendar className="w-4 h-4" />
                    <span>{expiringMedications} items expiring within 30 days</span>
                  </div>
                </Card>
              )}
              {criticalAlerts > 0 && (
                <Card className="p-2 bg-red-900/20 border-red-500/50">
                  <div className="flex items-center gap-2 text-red-300 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    <span>{criticalAlerts} critical alerts require attention</span>
                  </div>
                </Card>
              )}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}