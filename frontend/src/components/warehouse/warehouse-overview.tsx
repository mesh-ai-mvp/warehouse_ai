import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Aisle } from './warehouse-types';
import { Thermometer, Package, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WarehouseOverviewProps {
  aisles: Aisle[];
  onAisleClick: (aisle: Aisle) => void;
  legendCollapsed: boolean;
  onToggleLegend: () => void;
}

export function WarehouseOverview({ aisles, onAisleClick, legendCollapsed, onToggleLegend }: WarehouseOverviewProps) {
  const [hoveredAisle, setHoveredAisle] = useState<string | null>(null);

  const getAisleStatus = (aisle: Aisle) => {
    const totalMedications = aisle.shelves.reduce((acc, shelf) => acc + shelf.medications.length, 0);
    const totalCapacity = aisle.shelves.length;
    const fillPercentage = totalCapacity > 0 ? (totalMedications / totalCapacity) * 100 : 0;

    if (fillPercentage > 80) return 'high';
    if (fillPercentage > 40) return 'medium';
    if (fillPercentage > 0) return 'low';
    return 'empty';
  };

  const getStatusColor = (status: string, category: string) => {
    // Base colors by category
    const categoryColors = {
      'General': {
        high: 'from-green-400 to-green-600',
        medium: 'from-yellow-400 to-yellow-600',
        low: 'from-orange-400 to-orange-600',
        empty: 'from-gray-400 to-gray-600'
      },
      'Refrigerated': {
        high: 'from-blue-400 to-cyan-600',
        medium: 'from-blue-300 to-blue-500',
        low: 'from-slate-400 to-slate-600',
        empty: 'from-gray-400 to-gray-500'
      },
      'Controlled': {
        high: 'from-yellow-400 to-amber-600',
        medium: 'from-yellow-300 to-yellow-500',
        low: 'from-orange-400 to-orange-600',
        empty: 'from-gray-400 to-gray-500'
      },
      'Quarantine': {
        high: 'from-red-400 to-red-600',
        medium: 'from-red-300 to-red-500',
        low: 'from-pink-400 to-pink-600',
        empty: 'from-gray-400 to-gray-500'
      },
      'Office': {
        high: 'from-purple-400 to-purple-600',
        medium: 'from-purple-300 to-purple-500',
        low: 'from-indigo-400 to-indigo-600',
        empty: 'from-gray-400 to-gray-500'
      }
    };

    return categoryColors[category as keyof typeof categoryColors]?.[status as keyof typeof categoryColors.General] || 'from-gray-400 to-gray-600';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Refrigerated': return <Thermometer className="w-4 h-4" />;
      case 'Controlled': return <AlertTriangle className="w-4 h-4" />;
      default: return <Package className="w-4 h-4" />;
    }
  };

  return (
    <div className="h-full relative overflow-hidden">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-gradient-to-b from-slate-900/90 to-transparent p-6">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <h1 className="text-white text-3xl mb-2">MediCore Warehouse</h1>
          <p className="text-slate-300">Real-time pharmaceutical inventory management</p>
        </motion.div>
      </div>

      {/* 3D Warehouse Floor */}
      <div className="h-full flex items-center justify-center perspective-1000 p-8">
        <motion.div
          initial={{ opacity: 0, rotateX: 45 }}
          animate={{ opacity: 1, rotateX: 20 }}
          transition={{ duration: 1, ease: [0.23, 1, 0.320, 1] }}
          className="relative preserve-3d w-full max-w-4xl h-full max-h-[600px]"
          style={{
            transformStyle: 'preserve-3d',
            transform: 'rotateX(20deg) rotateY(-10deg)'
          }}
        >
          {/* Warehouse Building Outline */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1.2, ease: [0.23, 1, 0.320, 1] }}
            className="absolute inset-0 bg-slate-800/30 border-4 border-slate-600/50 rounded-xl backdrop-blur-sm"
            style={{
              boxShadow: '0 25px 50px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)'
            }}
          >
            {/* Building structure details */}
            <div className="absolute inset-2 border border-slate-700/30 rounded-lg" />
            <div className="absolute inset-4 border border-slate-700/20 rounded-lg" />
          </motion.div>

          {/* Main Storage Area Grid */}
          <div className="absolute inset-8 grid grid-cols-3 grid-rows-2 gap-6 p-4">
            {aisles.map((aisle, index) => {
              const status = getAisleStatus(aisle);
              const isHovered = hoveredAisle === aisle.id;

              // Calculate position based on grid
              const col = aisle.position.x;
              const row = aisle.position.z;

              return (
                <motion.div
                  key={aisle.id}
                  initial={{ opacity: 0, scale: 0, y: -100 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{
                    duration: 0.8,
                    delay: index * 0.15,
                    ease: [0.23, 1, 0.320, 1]
                  }}
                  className="relative cursor-pointer flex items-center justify-center w-full h-full"
                  style={{
                    gridColumn: col + 1,
                    gridRow: row + 1,
                    transform: `translateZ(${isHovered ? '30px' : '0px'})`,
                    transformStyle: 'preserve-3d'
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    onAisleClick(aisle);
                  }}
                  whileHover={{
                    scale: 1.05,
                    transition: { duration: 0.2 }
                  }}
                  whileTap={{ scale: 0.95 }}
                >
                  {/* Zone Background - Full clickable area */}
                  <div className="absolute inset-0 bg-gradient-to-br from-slate-700/20 to-slate-800/40 rounded-lg border border-slate-600/30" />

                  {/* Aisle Container */}
                  <div
                    className={`relative w-full h-full bg-gradient-to-br ${getStatusColor(status, aisle.category)} rounded-lg shadow-2xl overflow-hidden min-h-[120px]`}
                    style={{
                      boxShadow: isHovered
                        ? '0 25px 50px rgba(0,0,0,0.6), 0 0 40px rgba(59, 130, 246, 0.4)'
                        : '0 15px 35px rgba(0,0,0,0.4)'
                    }}
                  >
                    {/* Category indicator strip */}
                    <div className={`absolute top-0 left-0 right-0 h-2 ${
                      aisle.category === 'Refrigerated' ? 'bg-blue-400' :
                      aisle.category === 'Controlled' ? 'bg-yellow-400' :
                      aisle.category === 'Quarantine' ? 'bg-red-400' :
                      aisle.category === 'Office' ? 'bg-purple-400' :
                      'bg-green-400'
                    }`} />

                    {/* Shelving Units Visualization */}
                    <div className="absolute inset-4 grid grid-cols-6 grid-rows-4 gap-1">
                      {Array.from({ length: 24 }).map((_, i) => {
                        const shelfIndex = Math.floor(i / 3);
                        const hasStock = shelfIndex < aisle.shelves.length && aisle.shelves[shelfIndex]?.medications.length > 0;
                        return (
                          <div
                            key={i}
                            className={`rounded-sm transition-all duration-300 ${
                              hasStock ? 'bg-white/50 shadow-sm' : 'bg-white/15'
                            }`}
                          />
                        );
                      })}
                    </div>

                    {/* Aisle Walkway */}
                    <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 w-3/4 h-2 bg-slate-900/40 rounded-full" />

                    {/* Temperature/Special indicators */}
                    {aisle.category === 'Refrigerated' && (
                      <div className="absolute top-3 right-3 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                        <Thermometer className="w-3 h-3 text-white" />
                      </div>
                    )}
                    {aisle.category === 'Controlled' && (
                      <div className="absolute top-3 right-3 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-3 h-3 text-white" />
                      </div>
                    )}

                    {/* Status indicator */}
                    <div className="absolute bottom-3 left-3 flex items-center gap-1">
                      <div className={`w-2 h-2 rounded-full ${
                        status === 'high' ? 'bg-green-300 animate-pulse' :
                        status === 'medium' ? 'bg-yellow-300' :
                        status === 'low' ? 'bg-orange-300' :
                        'bg-gray-300'
                      }`} />
                      <span className="text-white/80 text-xs">
                        {aisle.shelves.reduce((acc, shelf) => acc + shelf.medications.length, 0)} items
                      </span>
                    </div>

                    {/* Aisle Number */}
                    <div className="absolute top-3 left-3 text-white/90 text-sm font-medium">
                      {String.fromCharCode(65 + index)}
                    </div>

                    {/* Glow effect */}
                    <div className="absolute inset-0 bg-gradient-to-t from-transparent via-transparent to-white/10 rounded-lg" />
                  </div>

                  {/* Aisle Info Card */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{
                      opacity: isHovered ? 1 : 0,
                      y: isHovered ? -20 : 20,
                      scale: isHovered ? 1 : 0.9
                    }}
                    transition={{ duration: 0.2 }}
                    className="absolute -top-24 left-1/2 transform -translate-x-1/2 bg-white/95 backdrop-blur-sm rounded-xl p-4 shadow-2xl border border-white/20 min-w-[240px] z-20"
                    style={{ transformStyle: 'preserve-3d' }}
                  >
                    <div className="flex items-center gap-3 mb-3">
                      {getCategoryIcon(aisle.category)}
                      <div>
                        <div className="font-medium text-slate-800">{aisle.name}</div>
                        <div className="text-xs text-slate-600">Zone {String.fromCharCode(65 + index)}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs text-slate-600">
                      <div>
                        <div className="text-slate-500">Category</div>
                        <div className="font-medium">{aisle.category}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Temperature</div>
                        <div className="font-medium">{aisle.temperature}°C</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Shelves</div>
                        <div className="font-medium">{aisle.shelves.length}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Status</div>
                        <div className={`font-medium ${
                          status === 'high' ? 'text-green-600' :
                          status === 'medium' ? 'text-yellow-600' :
                          status === 'low' ? 'text-orange-600' :
                          'text-gray-600'
                        }`}>
                          {status === 'high' ? 'Well Stocked' :
                           status === 'medium' ? 'Moderate' :
                           status === 'low' ? 'Low Stock' :
                           'Empty'}
                        </div>
                      </div>
                    </div>
                  </motion.div>

                  {/* Zone Label */}
                  <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 text-center">
                    <div
                      className="text-white text-sm font-medium bg-slate-800/80 backdrop-blur-sm px-3 py-1 rounded-full border border-slate-600/50 hover:bg-slate-700/80 transition-colors"
                      onMouseEnter={() => setHoveredAisle(aisle.id)}
                      onMouseLeave={() => setHoveredAisle(null)}
                    >
                      Zone {String.fromCharCode(65 + index)}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Entrance Area */}
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 1.2 }}
            className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-2"
          >
            <div className="bg-slate-700/80 backdrop-blur-sm px-6 py-3 rounded-t-xl border-t border-l border-r border-slate-600/50">
              <div className="text-slate-300 text-sm font-medium mb-1">Main Entrance</div>
              <div className="text-slate-400 text-xs">Loading & Receiving</div>
            </div>
            {/* Entrance doors */}
            <div className="flex gap-2 justify-center mt-2">
              <div className="w-8 h-1 bg-slate-600 rounded-full"></div>
              <div className="w-8 h-1 bg-slate-600 rounded-full"></div>
              <div className="w-8 h-1 bg-slate-600 rounded-full"></div>
            </div>
          </motion.div>

          {/* Side Facilities */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 1.4 }}
            className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-4"
          >
            <div className="bg-slate-700/60 backdrop-blur-sm px-3 py-2 rounded-l-lg border-l border-t border-b border-slate-600/50">
              <div className="text-slate-300 text-xs font-medium">Admin</div>
              <div className="text-slate-400 text-xs">Office</div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 1.6 }}
            className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-4"
          >
            <div className="bg-slate-700/60 backdrop-blur-sm px-3 py-2 rounded-r-lg border-r border-t border-b border-slate-600/50">
              <div className="text-slate-300 text-xs font-medium">Quality</div>
              <div className="text-slate-400 text-xs">Control</div>
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0, x: 50 }}
        animate={{
          opacity: 1,
          x: 0,
          width: legendCollapsed ? '60px' : 'auto'
        }}
        transition={{ duration: 0.6, delay: 0.8 }}
        className="absolute bottom-6 right-6 bg-slate-800/90 backdrop-blur-sm rounded-xl border border-slate-700 shadow-2xl overflow-hidden"
      >
        {/* Legend Header */}
        <div className="flex items-center justify-between p-3 border-b border-slate-700/50">
          {!legendCollapsed && (
            <motion.h3
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="text-white font-medium"
            >
              Zone Legend
            </motion.h3>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleLegend}
            className="w-6 h-6 p-0 text-slate-400 hover:text-white"
          >
            {legendCollapsed ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>

        {!legendCollapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="p-4"
          >
            {/* Inventory Status */}
            <div className="space-y-2 text-sm mb-4">
              <div className="text-slate-400 text-xs uppercase tracking-wide font-medium mb-2">Stock Levels</div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-gradient-to-r from-green-400 to-green-600"></div>
                <span className="text-slate-300">Well Stocked (80%+)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-gradient-to-r from-yellow-400 to-yellow-600"></div>
                <span className="text-slate-300">Moderate (40-80%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-gradient-to-r from-orange-400 to-orange-600"></div>
                <span className="text-slate-300">Low Stock (1-40%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-gradient-to-r from-gray-400 to-gray-600"></div>
                <span className="text-slate-300">Empty</span>
              </div>
            </div>

            {/* Zone Categories */}
            <div className="space-y-2 text-sm border-t border-slate-700/50 pt-4">
              <div className="text-slate-400 text-xs uppercase tracking-wide font-medium mb-2">Categories</div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded bg-blue-400"></div>
                <span className="text-slate-300">Refrigerated</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded bg-yellow-400"></div>
                <span className="text-slate-300">Controlled</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded bg-red-400"></div>
                <span className="text-slate-300">Quarantine</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded bg-green-400"></div>
                <span className="text-slate-300">General</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-2 rounded bg-purple-400"></div>
                <span className="text-slate-300">Office</span>
              </div>
            </div>

            {/* Instructions */}
            <div className="mt-4 pt-4 border-t border-slate-700/50">
              <div className="text-slate-400 text-xs">Click any zone to explore aisles and shelves</div>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}