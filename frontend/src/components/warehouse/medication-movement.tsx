import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Package, ArrowRight, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { warehouseService } from '@/services/warehouseService';

interface MedicationMovementProps {
  isOpen: boolean;
  onClose: () => void;
  medication?: {
    med_id: number;
    name: string;
    currentShelf: number;
    currentPosition?: string;
    quantity: number;
  };
}

export function MedicationMovement({ isOpen, onClose, medication }: MedicationMovementProps) {
  const [targetShelf, setTargetShelf] = useState<string>('');
  const [moveQuantity, setMoveQuantity] = useState<number>(1);
  const [moveReason, setMoveReason] = useState<string>('manual_movement');
  const queryClient = useQueryClient();

  // Get available shelves
  const { data: layout } = useQuery({
    queryKey: ['warehouse-layout'],
    queryFn: () => warehouseService.getLayout(),
    enabled: isOpen
  });

  // Get placement recommendations
  const { data: recommendations } = useQuery({
    queryKey: ['placement-recommendations', medication?.med_id],
    queryFn: () => warehouseService.getPlacementRecommendation(medication!.med_id),
    enabled: isOpen && !!medication?.med_id
  });

  // Movement mutation
  const moveMutation = useMutation({
    mutationFn: (data: any) => warehouseService.moveMedication(data),
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['warehouse-layout'] });
      queryClient.invalidateQueries({ queryKey: ['aisle-details'] });
      queryClient.invalidateQueries({ queryKey: ['shelf-inventory'] });
      queryClient.invalidateQueries({ queryKey: ['shelf-detailed'] });
      onClose();
    }
  });

  const handleMove = () => {
    if (!medication || !targetShelf) return;

    moveMutation.mutate({
      med_id: medication.med_id,
      from_shelf: medication.currentShelf,
      to_shelf: parseInt(targetShelf),
      quantity: moveQuantity,
      reason: moveReason
    });
  };

  // Get all shelves from layout
  const allShelves = layout?.aisles?.flatMap((aisle: any) =>
    Array.from({ length: aisle.shelf_count || 8 }, (_, i) => ({
      id: aisle.aisle_id * 10 + i + 1, // Generate shelf IDs
      label: `${aisle.aisle_name} - Shelf ${i + 1}`,
      aisle: aisle.aisle_name,
      category: aisle.category
    }))
  ) || [];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl p-6 max-w-2xl w-full mx-4 border border-slate-700"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Package className="w-6 h-6 text-blue-400" />
                Move Medication
              </h2>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {medication && (
              <div className="space-y-6">
                {/* Current Location */}
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-semibold text-slate-400 mb-2">Current Location</h3>
                  <p className="text-white font-medium">{medication.name}</p>
                  <p className="text-slate-300">
                    Shelf #{medication.currentShelf}
                    {medication.currentPosition && ` - Position ${medication.currentPosition}`}
                  </p>
                  <p className="text-slate-400">Available: {medication.quantity} units</p>
                </div>

                {/* Quantity to Move */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Quantity to Move
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={medication.quantity}
                    value={moveQuantity}
                    onChange={(e) => setMoveQuantity(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Reason for Movement */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Reason for Movement
                  </label>
                  <select
                    value={moveReason}
                    onChange={(e) => setMoveReason(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="manual_movement">Manual Reorganization</option>
                    <option value="expiry_rotation">Expiry Date Rotation</option>
                    <option value="temperature_requirement">Temperature Requirement</option>
                    <option value="space_optimization">Space Optimization</option>
                    <option value="picking_efficiency">Picking Efficiency</option>
                    <option value="damage_isolation">Damage Isolation</option>
                  </select>
                </div>

                {/* Recommendations */}
                {recommendations?.recommended_positions?.length > 0 && (
                  <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-blue-400 mb-3">
                      Recommended Locations
                    </h3>
                    <div className="space-y-2">
                      {recommendations.recommended_positions.slice(0, 3).map((rec: any) => (
                        <button
                          key={rec.position_id}
                          onClick={() => setTargetShelf(rec.position_id.toString())}
                          className="w-full text-left p-3 bg-slate-800/50 rounded-lg hover:bg-slate-700/50 transition-colors"
                        >
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="text-white font-medium">{rec.location}</p>
                              <p className="text-xs text-slate-400">
                                {rec.reasons.join(', ')}
                              </p>
                            </div>
                            <span className="text-green-400 font-bold">
                              {rec.score}%
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Target Shelf Selection */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Target Shelf
                  </label>
                  <select
                    value={targetShelf}
                    onChange={(e) => setTargetShelf(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select a shelf...</option>
                    {allShelves
                      .filter((shelf: any) => shelf.id !== medication.currentShelf)
                      .map((shelf: any) => (
                        <option key={shelf.id} value={shelf.id}>
                          {shelf.label}
                        </option>
                      ))}
                  </select>
                </div>

                {/* Error Message */}
                {moveMutation.isError && (
                  <div className="bg-red-900/20 border border-red-700/50 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-5 h-5 text-red-400" />
                      <p className="text-red-400">
                        {(moveMutation.error as any)?.message || 'Failed to move medication'}
                      </p>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-end gap-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-slate-300 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleMove}
                    disabled={!targetShelf || moveMutation.isPending}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {moveMutation.isPending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Moving...
                      </>
                    ) : (
                      <>
                        <ArrowRight className="w-4 h-4" />
                        Move Medication
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}