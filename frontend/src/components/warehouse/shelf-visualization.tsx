import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { Package, AlertTriangle, Clock, TrendingUp, Box, Info } from 'lucide-react';
import type { ShelfDetailedLayout, ShelfPosition, PositionMedication } from '@/types/warehouse';

interface ShelfVisualizationProps {
  shelfData: ShelfDetailedLayout;
  viewMode?: 'grid' | '3d' | 'list';
  onPositionClick?: (position: ShelfPosition) => void;
  onMedicationClick?: (medication: PositionMedication) => void;
}

interface ShelfPositionComponentProps {
  position: ShelfPosition;
  onClick?: () => void;
  highlight?: boolean;
  depth?: number;
}

// Get color based on medication properties
const getPositionColor = (position: ShelfPosition): string => {
  if (!position.medication) return 'bg-gray-700/50';

  const med = position.medication;

  // Critical expiry takes precedence
  if (med.expiry_status === 'critical') return 'bg-gradient-to-br from-red-600 to-red-700';
  if (med.expiry_status === 'soon') return 'bg-gradient-to-br from-yellow-600 to-amber-700';

  // Then velocity
  if (med.velocity === 'fast') return 'bg-gradient-to-br from-green-600 to-emerald-700';
  if (med.velocity === 'medium') return 'bg-gradient-to-br from-blue-600 to-sky-700';

  // Controlled substances
  if (med.placement_reason === 'controlled_substance') return 'bg-gradient-to-br from-purple-600 to-purple-700';

  return 'bg-gradient-to-br from-gray-600 to-gray-700';
};

// Get icon based on medication properties
const getPositionIcon = (medication?: PositionMedication) => {
  if (!medication) return null;

  if (medication.expiry_status === 'critical') return <AlertTriangle className="w-3 h-3 text-white" />;
  if (medication.expiry_status === 'soon') return <Clock className="w-3 h-3 text-white" />;
  if (medication.velocity === 'fast') return <TrendingUp className="w-3 h-3 text-white" />;

  return <Package className="w-3 h-3 text-white/80" />;
};

function ShelfPositionComponent({ position, onClick, highlight, depth = 1 }: ShelfPositionComponentProps) {
  const [isHovered, setIsHovered] = useState(false);

  const depthStyles = {
    1: 'z-30', // Front row
    2: 'z-20 scale-95 opacity-90', // Middle row
    3: 'z-10 scale-90 opacity-80' // Back row
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <motion.div
            className={cn(
              'relative aspect-square rounded-lg p-2 cursor-pointer transition-all duration-300',
              'border-2 border-transparent hover:border-white/30',
              getPositionColor(position),
              highlight && 'ring-2 ring-yellow-400 ring-offset-2 ring-offset-gray-900',
              position.is_golden_zone && 'shadow-lg shadow-yellow-500/20',
              depthStyles[depth]
            )}
            onClick={onClick}
            onHoverStart={() => setIsHovered(true)}
            onHoverEnd={() => setIsHovered(false)}
            whileHover={{
              scale: 1.05,
              zIndex: 40,
              transition: { duration: 0.2 }
            }}
            whileTap={{ scale: 0.95 }}
            style={{
              transformStyle: 'preserve-3d',
              transform: `perspective(1000px) rotateX(${depth === 3 ? 10 : depth === 2 ? 5 : 0}deg)`
            }}
          >
            {/* Position Label */}
            <div className="absolute top-1 left-1 text-xs font-mono text-white/60">
              {position.grid_label}
            </div>

            {/* Golden Zone Indicator */}
            {position.is_golden_zone && (
              <div className="absolute top-1 right-1">
                <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse" />
              </div>
            )}

            {/* Medication Content */}
            {position.medication ? (
              <div className="flex flex-col items-center justify-center h-full">
                <div className="mb-1">
                  {getPositionIcon(position.medication)}
                </div>
                <div className="text-xs text-white font-medium text-center line-clamp-2">
                  {position.medication.name.split(' ')[0]}
                </div>
                <div className="text-xs text-white/70 mt-1">
                  Qty: {position.medication.quantity}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <Box className="w-4 h-4 text-gray-500" />
              </div>
            )}

            {/* Hover Effect */}
            <AnimatePresence>
              {isHovered && position.medication && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="absolute inset-0 bg-black/80 rounded-lg p-2 flex items-center justify-center"
                >
                  <div className="text-xs text-white text-center">
                    <div className="font-semibold">{position.medication.lot_number}</div>
                    <div className="text-white/60">Exp: {position.medication.expiry_date}</div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </TooltipTrigger>

        <TooltipContent side="top" className="bg-gray-900 border-gray-700">
          {position.medication ? (
            <div className="space-y-1">
              <p className="font-semibold">{position.medication.name}</p>
              <p className="text-xs">Position: {position.grid_label}</p>
              <p className="text-xs">Quantity: {position.medication.quantity}</p>
              <p className="text-xs">Batch: {position.medication.lot_number}</p>
              <p className="text-xs">Expiry: {position.medication.expiry_date}</p>
              <p className="text-xs">Status: {position.medication.expiry_status}</p>
              <p className="text-xs">Velocity: {position.medication.velocity}</p>
              {position.medication.behind_medication && (
                <p className="text-xs text-yellow-400">Behind: {position.medication.behind_medication}</p>
              )}
            </div>
          ) : (
            <div>
              <p className="font-semibold">Empty Position</p>
              <p className="text-xs">Position: {position.grid_label}</p>
              <p className="text-xs">Max Weight: {position.max_weight}kg</p>
              {position.reserved_for && (
                <p className="text-xs">Reserved for: {position.reserved_for}</p>
              )}
            </div>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function ShelfVisualization({
  shelfData,
  viewMode = 'grid',
  onPositionClick,
  onMedicationClick
}: ShelfVisualizationProps) {
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);

  const handlePositionClick = (position: ShelfPosition) => {
    setSelectedPosition(position.grid_label);
    onPositionClick?.(position);
    if (position.medication) {
      onMedicationClick?.(position.medication);
    }
  };

  return (
    <div className="space-y-4">
      {/* Shelf Header */}
      <Card className="bg-gradient-to-r from-gray-800 to-gray-900 border-gray-700">
        <div className="p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-white">
              Shelf {shelfData.shelf.position} - Level {shelfData.shelf.level}
            </h3>
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="text-blue-400 border-blue-400">
                {shelfData.shelf.category}
              </Badge>
              <Badge variant="outline" className="text-green-400 border-green-400">
                {shelfData.shelf.temperature}°C
              </Badge>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Utilization:</span>
              <span className="ml-2 text-white font-medium">
                {shelfData.dimensions.utilization_percent}%
              </span>
            </div>
            <div>
              <span className="text-gray-400">Occupied:</span>
              <span className="ml-2 text-white font-medium">
                {shelfData.dimensions.occupied_positions}/{shelfData.dimensions.total_positions}
              </span>
            </div>
            <div>
              <span className="text-gray-400">Capacity:</span>
              <span className="ml-2 text-white font-medium">
                {shelfData.shelf.capacity_slots} slots
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* 3D Grid Visualization */}
      {viewMode === 'grid' && (
        <Card className="bg-gray-900/50 border-gray-700">
          <div className="p-6">
            <div
              className="space-y-4"
              style={{
                perspective: '1000px',
                transformStyle: 'preserve-3d'
              }}
            >
              {/* Back Row */}
              <motion.div
                className="relative"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="absolute -left-16 top-1/2 -translate-y-1/2 text-sm text-gray-400 font-medium">
                  Back
                </div>
                <div className="grid grid-cols-10 gap-3">
                  {shelfData.rows.back.map((position) => (
                    <ShelfPositionComponent
                      key={position.position_id}
                      position={position}
                      onClick={() => handlePositionClick(position)}
                      highlight={selectedPosition === position.grid_label}
                      depth={3}
                    />
                  ))}
                </div>
              </motion.div>

              {/* Middle Row */}
              <motion.div
                className="relative"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="absolute -left-16 top-1/2 -translate-y-1/2 text-sm text-gray-400 font-medium">
                  Middle
                </div>
                <div className="grid grid-cols-10 gap-3">
                  {shelfData.rows.middle.map((position) => (
                    <ShelfPositionComponent
                      key={position.position_id}
                      position={position}
                      onClick={() => handlePositionClick(position)}
                      highlight={selectedPosition === position.grid_label}
                      depth={2}
                    />
                  ))}
                </div>
              </motion.div>

              {/* Front Row */}
              <motion.div
                className="relative"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0 }}
              >
                <div className="absolute -left-16 top-1/2 -translate-y-1/2 text-sm text-gray-400 font-medium">
                  Front
                </div>
                <div className="grid grid-cols-10 gap-3">
                  {shelfData.rows.front.map((position) => (
                    <ShelfPositionComponent
                      key={position.position_id}
                      position={position}
                      onClick={() => handlePositionClick(position)}
                      highlight={selectedPosition === position.grid_label}
                      depth={1}
                    />
                  ))}
                </div>
              </motion.div>
            </div>

            {/* Column Labels */}
            <div className="grid grid-cols-10 gap-2 mt-4 ml-20">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(num => (
                <div key={num} className="text-xs text-gray-500 text-center">
                  {num}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Legend */}
      <Card className="bg-gray-900/50 border-gray-700">
        <div className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-4 h-4 text-gray-400" />
            <h4 className="text-sm font-medium text-gray-300">Placement Strategy</h4>
          </div>

          <div className="grid grid-cols-3 gap-4 text-xs">
            <div>
              <div className="font-medium text-gray-400 mb-1">Front Row</div>
              <div className="text-gray-500">{shelfData.placement_strategy.front_row}</div>
            </div>
            <div>
              <div className="font-medium text-gray-400 mb-1">Middle Row</div>
              <div className="text-gray-500">{shelfData.placement_strategy.middle_row}</div>
            </div>
            <div>
              <div className="font-medium text-gray-400 mb-1">Back Row</div>
              <div className="text-gray-500">{shelfData.placement_strategy.back_row}</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-green-600 to-emerald-700 rounded" />
              <span className="text-xs text-gray-400">Fast Moving</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-blue-600 to-sky-700 rounded" />
              <span className="text-xs text-gray-400">Medium Velocity</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-gray-600 to-gray-700 rounded" />
              <span className="text-xs text-gray-400">Slow Moving</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-red-600 to-red-700 rounded" />
              <span className="text-xs text-gray-400">Expiring Soon</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-yellow-600 to-amber-700 rounded" />
              <span className="text-xs text-gray-400">Expiry Warning</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gradient-to-br from-purple-600 to-purple-700 rounded" />
              <span className="text-xs text-gray-400">Controlled</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-700/50 rounded" />
              <span className="text-xs text-gray-400">Empty</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-yellow-400 rounded" />
              <span className="text-xs text-gray-400">Golden Zone</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Alerts */}
      {shelfData.alerts && shelfData.alerts.length > 0 && (
        <Card className="bg-red-900/20 border-red-800">
          <div className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <h4 className="text-sm font-medium text-red-400">Active Alerts</h4>
            </div>
            <div className="space-y-2">
              {shelfData.alerts.map((alert, index) => (
                <div key={index} className="flex items-start gap-2 text-xs">
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs',
                      alert.severity === 'critical' ? 'border-red-500 text-red-400' :
                      alert.severity === 'warning' ? 'border-yellow-500 text-yellow-400' :
                      'border-blue-500 text-blue-400'
                    )}
                  >
                    {alert.type}
                  </Badge>
                  <span className="text-gray-300">{alert.message}</span>
                  {alert.position && (
                    <span className="text-gray-500">({alert.position})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}