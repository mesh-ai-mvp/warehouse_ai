import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Package, Thermometer, Calendar, AlertCircle } from 'lucide-react';
import type { Aisle, Shelf } from './warehouse-types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface AisleViewProps {
  aisle: Aisle;
  onShelfClick: (shelf: Shelf) => void;
  onBack: () => void;
}

export function AisleView({ aisle, onShelfClick, onBack }: AisleViewProps) {
  const [hoveredShelf, setHoveredShelf] = useState<string | null>(null);

  const getShelfFillLevel = (shelf: Shelf) => {
    // Calculate based on actual quantities, not just count
    const totalQuantity = shelf.medications.reduce((sum, med) => sum + (med.quantity || 0), 0);
    const fillPercentage = (totalQuantity / Math.max(1, shelf.capacity)) * 100;
    return Math.min(fillPercentage, 100);
  };

  const getShelfStatusColor = (shelf: Shelf) => {
    const fillLevel = getShelfFillLevel(shelf);
    if (fillLevel > 80) return 'from-green-400 to-green-600';
    if (fillLevel > 50) return 'from-yellow-400 to-yellow-600';
    if (fillLevel > 20) return 'from-orange-400 to-orange-600';
    if (fillLevel > 0) return 'from-red-400 to-red-600';
    return 'from-gray-300 to-gray-500';
  };

  const hasExpiringMedications = (shelf: Shelf) => {
    const today = new Date();
    const thirtyDaysFromNow = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);

    return shelf.medications.some(med => {
      const expiryDate = new Date(med.expiryDate);
      return expiryDate <= thirtyDaysFromNow;
    });
  };

  // Calculate based on actual quantities, not just item count
  const totalQuantity = aisle.shelves.reduce((acc, shelf) =>
    acc + shelf.medications.reduce((sum, med) => sum + (med.quantity || 0), 0), 0);
  const totalCapacity = aisle.shelves.reduce((acc, shelf) => acc + shelf.capacity, 0);
  // Estimate 100 items per position for quantity-based utilization
  const estimatedMaxQuantity = totalCapacity * 100;
  const utilizationRate = estimatedMaxQuantity > 0 ?
    Math.min(100, (totalQuantity / estimatedMaxQuantity) * 100) : 0;

  return (
    <div className="overflow-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="p-6 border-b bg-card/50 backdrop-blur-sm z-10 mb-16"
      >
        <div className="flex items-center gap-4 mb-4 mt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className=""
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Overview
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">{aisle.name}</h1>
            <div className="flex items-center gap-6 text-muted-foreground">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4" />
                <span>{aisle.category}</span>
              </div>
              <div className="flex items-center gap-2">
                <Thermometer className="w-4 h-4" />
                <span>{aisle.temperature}°C</span>
              </div>
              <div className="flex items-center gap-2">
                <span>{aisle.shelves.length} Shelves</span>
              </div>
            </div>
          </div>

          <Card className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{utilizationRate.toFixed(1)}%</div>
              <div className="text-sm text-muted-foreground">Utilization</div>
            </div>
          </Card>
        </div>
      </motion.div>

      {/* 3D Aisle View */}
      <div className="flex-1 flex items-center justify-center p-8 pt-32 pb-16 perspective-1000 min-h-[700px]">
        <motion.div
          initial={{ opacity: 0, rotateX: 60, z: -200 }}
          animate={{ opacity: 1, rotateX: 15, z: 0 }}
          transition={{ duration: 1, ease: [0.23, 1, 0.320, 1] }}
          className="relative preserve-3d w-[900px] h-[600px] mt-16"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(15deg) rotateY(-5deg)'
          }}
        >
          {/* Left Shelf Unit */}
          <div className="absolute left-16 top-1/2 -translate-y-1/2 z-10 mt-4">
            <motion.div
              initial={{ x: -100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="grid grid-rows-4 gap-12"
            >
              {aisle.shelves.filter((_, i) => i % 2 === 0).map((shelf, index) => (
                <motion.div
                  key={shelf.id}
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.5 + index * 0.1 }}
                  className="relative cursor-pointer group"
                  onMouseEnter={() => setHoveredShelf(shelf.id)}
                  onMouseLeave={() => setHoveredShelf(null)}
                  onClick={() => onShelfClick(shelf)}
                  whileHover={{ scale: 1.02, z: 10 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div
                    className={`w-64 h-24 bg-gradient-to-r ${getShelfStatusColor(shelf)} rounded-lg shadow-lg relative overflow-hidden`}
                    style={{
                      boxShadow: hoveredShelf === shelf.id
                        ? '0 15px 30px rgba(0,0,0,0.4), 0 0 20px rgba(59, 130, 246, 0.3)'
                        : '0 8px 16px rgba(0,0,0,0.3)'
                    }}
                  >
                    {/* Shelf Contents Visualization */}
                    <div className="absolute inset-2 grid grid-cols-8 grid-rows-2 gap-1.5">
                      {Array.from({ length: 16 }).map((_, i) => (
                        <div
                          key={i}
                          className={`rounded-sm ${i < shelf.medications.length * 4
                              ? 'bg-white/60'
                              : 'bg-white/10'
                            }`}
                        />
                      ))}
                    </div>

                    {/* Expiry Alert */}
                    {hasExpiringMedications(shelf) && (
                      <div className="absolute top-1 right-1">
                        <AlertCircle className="w-4 h-4 text-red-300 animate-pulse" />
                      </div>
                    )}

                    {/* Shelf Label */}
                    <div
                      className="absolute bottom-1 left-2 text-xs text-white/80 hover:text-white hover:bg-black/20 px-1 rounded transition-colors cursor-pointer"
                      onMouseEnter={() => setHoveredShelf(shelf.id)}
                      onMouseLeave={() => setHoveredShelf(null)}
                    >
                      {shelf.code ? shelf.code : `Shelf ${shelf.position + 1}`}
                    </div>

                    {/* Fill Level Indicator */}
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
                      <div
                        className="h-full bg-white/60 transition-all duration-300"
                        style={{ width: `${getShelfFillLevel(shelf)}%` }}
                      />
                    </div>
                  </div>

                  {/* Hover Info */}
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{
                      opacity: hoveredShelf === shelf.id ? 1 : 0,
                      x: hoveredShelf === shelf.id ? 0 : -20
                    }}
                    transition={{ duration: 0.2 }}
                    className="absolute left-[270px] top-0 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl border border-white/20 min-w-[200px] z-50 pointer-events-none"
                  >
                    <div className="text-sm text-slate-800 space-y-1">
                      <div className="flex justify-between">
                        <span>Position:</span>
                        <span>{shelf.position + 1}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Level:</span>
                        <span>{shelf.level + 1}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Medications:</span>
                        <span>{shelf.medications.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Fill Level:</span>
                        <span>{getShelfFillLevel(shelf).toFixed(0)}%</span>
                      </div>
                      {hasExpiringMedications(shelf) && (
                        <div className="text-red-600 text-xs flex items-center gap-1 mt-2">
                          <AlertCircle className="w-3 h-3" />
                          Expiring items
                        </div>
                      )}
                    </div>
                  </motion.div>
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* Right Shelf Unit */}
          <div className="absolute right-16 top-1/2 -translate-y-1/2 z-10 mt-4">
            <motion.div
              initial={{ x: 100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="grid grid-rows-4 gap-12"
            >
              {aisle.shelves.filter((_, i) => i % 2 === 1).map((shelf, index) => (
                <motion.div
                  key={shelf.id}
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.6 + index * 0.1 }}
                  className="relative cursor-pointer group"
                  onMouseEnter={() => setHoveredShelf(shelf.id)}
                  onMouseLeave={() => setHoveredShelf(null)}
                  onClick={() => onShelfClick(shelf)}
                  whileHover={{ scale: 1.02, z: 10 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div
                    className={`w-64 h-24 bg-gradient-to-r ${getShelfStatusColor(shelf)} rounded-lg shadow-lg relative overflow-hidden`}
                    style={{
                      boxShadow: hoveredShelf === shelf.id
                        ? '0 15px 30px rgba(0,0,0,0.4), 0 0 20px rgba(59, 130, 246, 0.3)'
                        : '0 8px 16px rgba(0,0,0,0.3)'
                    }}
                  >
                    {/* Shelf Contents Visualization */}
                    <div className="absolute inset-2 grid grid-cols-8 grid-rows-2 gap-1.5">
                      {Array.from({ length: 16 }).map((_, i) => (
                        <div
                          key={i}
                          className={`rounded-sm ${i < shelf.medications.length * 4
                              ? 'bg-white/60'
                              : 'bg-white/10'
                            }`}
                        />
                      ))}
                    </div>

                    {/* Expiry Alert */}
                    {hasExpiringMedications(shelf) && (
                      <div className="absolute top-1 right-1">
                        <AlertCircle className="w-4 h-4 text-red-300 animate-pulse" />
                      </div>
                    )}

                    {/* Shelf Label */}
                    <div
                      className="absolute bottom-1 left-2 text-xs text-white/80 hover:text-white hover:bg-black/20 px-1 rounded transition-colors cursor-pointer"
                      onMouseEnter={() => setHoveredShelf(shelf.id)}
                      onMouseLeave={() => setHoveredShelf(null)}
                    >
                      {shelf.code ? shelf.code : `Shelf ${shelf.position + 1}`}
                    </div>

                    {/* Fill Level Indicator */}
                    <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
                      <div
                        className="h-full bg-white/60 transition-all duration-300"
                        style={{ width: `${getShelfFillLevel(shelf)}%` }}
                      />
                    </div>
                  </div>

                  {/* Hover Info */}
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{
                      opacity: hoveredShelf === shelf.id ? 1 : 0,
                      x: hoveredShelf === shelf.id ? 0 : 20
                    }}
                    transition={{ duration: 0.2 }}
                    className="absolute right-[270px] top-0 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl border border-white/20 min-w-[200px] z-50 pointer-events-none"
                  >
                    <div className="text-sm text-slate-800 space-y-1">
                      <div className="flex justify-between">
                        <span>Position:</span>
                        <span>{shelf.position + 1}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Level:</span>
                        <span>{shelf.level + 1}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Medications:</span>
                        <span>{shelf.medications.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Fill Level:</span>
                        <span>{getShelfFillLevel(shelf).toFixed(0)}%</span>
                      </div>
                      {hasExpiringMedications(shelf) && (
                        <div className="text-red-600 text-xs flex items-center gap-1 mt-2">
                          <AlertCircle className="w-3 h-3" />
                          Expiring items
                        </div>
                      )}
                    </div>
                  </motion.div>
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* Aisle Floor */}
          <motion.div
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="absolute top-16 left-32 right-32 bottom-16 bg-gradient-to-b from-muted/30 to-muted/50 rounded-lg border-2 border-border/30 z-0 overflow-visible"
            style={{ transform: 'rotateX(90deg) translateZ(-20px)' }}
          >
            {/* Aisle markings */}
            <div className="w-full h-full grid grid-cols-3 opacity-30">
              <div className="border-r border-border"></div>
              <div className="border-r border-border"></div>
              <div></div>
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* Instructions */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 1 }}
        className="fixed bottom-6 right-6 text-right z-20"
      >
        <div className="text-muted-foreground text-sm bg-card/60 backdrop-blur-sm px-4 py-2 rounded-full">
          Click on any shelf to view detailed medication inventory
        </div>
      </motion.div>
    </div>
  );
}