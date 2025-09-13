import React, { useState } from 'react';
import { motion } from 'motion/react';
import { ArrowLeft, Package, Thermometer, Calendar, AlertCircle } from 'lucide-react';
import { Aisle, Shelf } from './warehouse-types';
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
    const fillPercentage = (shelf.medications.length / (shelf.capacity / 100)) * 100;
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

  const totalMedications = aisle.shelves.reduce((acc, shelf) => acc + shelf.medications.length, 0);
  const totalCapacity = aisle.shelves.reduce((acc, shelf) => acc + shelf.capacity, 0);
  const utilizationRate = totalCapacity > 0 ? (totalMedications / totalCapacity) * 100 : 0;

  return (
    <div className="h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="p-6 border-b border-slate-700/50 bg-slate-800/50 backdrop-blur-sm"
      >
        <div className="flex items-center gap-4 mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-slate-300 hover:text-white hover:bg-slate-700/50"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Overview
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl text-white mb-2">{aisle.name}</h1>
            <div className="flex items-center gap-6 text-slate-300">
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

          <Card className="p-4 bg-slate-800/80 border-slate-700">
            <div className="text-center">
              <div className="text-2xl text-white">{utilizationRate.toFixed(1)}%</div>
              <div className="text-sm text-slate-400">Utilization</div>
            </div>
          </Card>
        </div>
      </motion.div>

      {/* 3D Aisle View */}
      <div className="flex-1 flex items-center justify-center p-8 perspective-1000">
        <motion.div
          initial={{ opacity: 0, rotateX: 60, z: -200 }}
          animate={{ opacity: 1, rotateX: 15, z: 0 }}
          transition={{ duration: 1, ease: [0.23, 1, 0.320, 1] }}
          className="relative preserve-3d"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(15deg) rotateY(-5deg)'
          }}
        >
          {/* Left Shelf Unit */}
          <div className="absolute left-0">
            <motion.div
              initial={{ x: -100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="grid grid-rows-4 gap-4"
            >
              {aisle.shelves.slice(0, 4).map((shelf, index) => (
                <motion.div
                  key={shelf.id}
                  initial={{ opacity: 0, x: -50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.5 + index * 0.1 }}
                  className="relative cursor-pointer group"
                  onClick={() => onShelfClick(shelf)}
                  whileHover={{ scale: 1.02, z: 10 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div
                    className={`w-48 h-16 bg-gradient-to-r ${getShelfStatusColor(shelf)} rounded-lg shadow-lg relative overflow-hidden`}
                    style={{
                      boxShadow: hoveredShelf === shelf.id
                        ? '0 15px 30px rgba(0,0,0,0.4), 0 0 20px rgba(59, 130, 246, 0.3)'
                        : '0 8px 16px rgba(0,0,0,0.3)'
                    }}
                  >
                    {/* Shelf Contents Visualization */}
                    <div className="absolute inset-2 grid grid-cols-8 grid-rows-2 gap-1">
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
                      Shelf {shelf.position + 1}
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
                    className="absolute left-52 top-0 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl border border-white/20 min-w-[200px] z-10 pointer-events-none"
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
          <div className="absolute right-0">
            <motion.div
              initial={{ x: 100, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="grid grid-rows-4 gap-4"
            >
              {aisle.shelves.slice(4, 8).map((shelf, index) => (
                <motion.div
                  key={shelf.id}
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.6 + index * 0.1 }}
                  className="relative cursor-pointer group"
                  onClick={() => onShelfClick(shelf)}
                  whileHover={{ scale: 1.02, z: 10 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div
                    className={`w-48 h-16 bg-gradient-to-r ${getShelfStatusColor(shelf)} rounded-lg shadow-lg relative overflow-hidden`}
                    style={{
                      boxShadow: hoveredShelf === shelf.id
                        ? '0 15px 30px rgba(0,0,0,0.4), 0 0 20px rgba(59, 130, 246, 0.3)'
                        : '0 8px 16px rgba(0,0,0,0.3)'
                    }}
                  >
                    {/* Shelf Contents Visualization */}
                    <div className="absolute inset-2 grid grid-cols-8 grid-rows-2 gap-1">
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
                      Shelf {shelf.position + 1}
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
                    className="absolute right-52 top-0 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-xl border border-white/20 min-w-[200px] z-10 pointer-events-none"
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
            className="absolute top-0 left-12 right-12 bottom-0 bg-gradient-to-b from-slate-700/30 to-slate-800/50 rounded-lg border-2 border-slate-600/30"
            style={{ transform: 'rotateX(90deg) translateZ(-20px)' }}
          >
            {/* Aisle markings */}
            <div className="w-full h-full grid grid-cols-3 opacity-30">
              <div className="border-r border-slate-500"></div>
              <div className="border-r border-slate-500"></div>
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
        className="absolute bottom-6 left-1/2 transform -translate-x-1/2 text-center"
      >
        <div className="text-slate-400 text-sm bg-slate-800/60 backdrop-blur-sm px-4 py-2 rounded-full">
          Click on any shelf to view detailed medication inventory
        </div>
      </motion.div>
    </div>
  );
}