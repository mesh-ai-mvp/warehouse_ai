import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Package, Calendar, Thermometer, AlertTriangle, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import type { Shelf } from './warehouse-types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MedicationMovement } from './medication-movement';

interface ShelfDetailProps {
  shelf: Shelf;
  aisleName: string;
  onBack: () => void;
}

export function ShelfDetail({ shelf, aisleName, onBack }: ShelfDetailProps) {
  const [isMoveModalOpen, setIsMoveModalOpen] = useState(false);
  const [selectedMedication, setSelectedMedication] = useState<any>(null);

  const handleMoveClick = (medication: any) => {
    setSelectedMedication({
      med_id: medication.id,
      name: medication.name,
      currentShelf: shelf.id || shelf.position + 1, // Use shelf ID or position
      quantity: medication.quantity
    });
    setIsMoveModalOpen(true);
  };

  const getExpiryStatus = (expiryDate: string) => {
    const today = new Date();
    const expiry = new Date(expiryDate);
    const daysUntilExpiry = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) return { status: 'expired', label: 'Expired', color: 'bg-red-500' };
    if (daysUntilExpiry <= 7) return { status: 'critical', label: `${daysUntilExpiry} days`, color: 'bg-red-500' };
    if (daysUntilExpiry <= 30) return { status: 'warning', label: `${daysUntilExpiry} days`, color: 'bg-yellow-500' };
    return { status: 'good', label: `${daysUntilExpiry} days`, color: 'bg-green-500' };
  };

  const getTemperatureStatus = (temperature: number) => {
    if (temperature < 2 || temperature > 8) return { status: 'critical', color: 'text-red-500' };
    if (temperature < 4 || temperature > 6) return { status: 'warning', color: 'text-yellow-500' };
    return { status: 'good', color: 'text-green-500' };
  };

  const getStockLevel = (quantity: number, maxCapacity: number) => {
    const clampedMax = Math.max(1, maxCapacity);
    const percentage = Math.min(100, Math.max(0, (quantity / clampedMax) * 100));
    if (percentage >= 80) return { status: 'high', label: 'Well Stocked', color: 'text-green-500' };
    if (percentage >= 50) return { status: 'medium', label: 'Moderate', color: 'text-yellow-500' };
    if (percentage >= 20) return { status: 'low', label: 'Low Stock', color: 'text-orange-500' };
    return { status: 'critical', label: 'Critical', color: 'text-red-500' };
  };

  return (
    <div className="overflow-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="p-6 border-b bg-card/50 backdrop-blur-sm z-10 mb-16"
      >
        <div className="flex items-center gap-4 mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className=""
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Aisle
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">
              Shelf {shelf.position + 1} - Level {shelf.level + 1}
            </h1>
            <div className="flex items-center gap-4 text-muted-foreground">
              <span>{aisleName}</span>
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4" />
                <span>{shelf.medications.length} Items</span>
              </div>
            </div>
          </div>

          <Card className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold">
                {shelf.medications.length}/{Math.floor(shelf.capacity / 100)}
              </div>
              <div className="text-sm text-muted-foreground">Capacity</div>
            </div>
          </Card>
        </div>
      </motion.div>

      <div className="p-6 pt-12 space-y-8">
        {/* Shelf Overview */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-6">Shelf Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="text-muted-foreground text-sm">Total Medications</div>
                <div className="text-2xl font-bold">{shelf.medications.length}</div>
              </div>
              <div className="space-y-2">
                <div className="text-muted-foreground text-sm">Capacity Utilization</div>
                <div className="text-2xl font-bold">
                  {Math.round((shelf.medications.length / Math.max(1, shelf.capacity)) * 100)}%
                </div>
              </div>
              <div className="space-y-2">
                <div className="text-muted-foreground text-sm">Available Space</div>
                <div className="text-2xl font-bold">
                  {(() => {
                    const totalSlots = Math.max(1, Math.floor(shelf.capacity / 100));
                    return Math.max(0, totalSlots - shelf.medications.length);
                  })()}
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Medications List */}
        {shelf.medications.length > 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <h2 className="text-xl font-semibold mb-6">Stored Medications</h2>
            <div className="grid gap-4">
              {shelf.medications.map((medication, index) => {
                const expiryStatus = getExpiryStatus(medication.expiryDate);
                const tempStatus = getTemperatureStatus(medication.temperature);
                const stockLevel = getStockLevel(medication.quantity, medication.maxCapacity);

                return (
                  <motion.div
                    key={medication.id}
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.6 + index * 0.1 }}
                  >
                    <Card className="p-6 bg-slate-800/80 border-slate-700 hover:bg-slate-700/80 transition-colors">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <h3 className="text-white text-lg font-medium mb-2">
                            {medication.name}
                          </h3>
                          <div className="flex items-center gap-4 text-sm text-slate-300">
                            <span>Batch: {medication.batchNumber}</span>
                            <div className="flex items-center gap-1">
                              <Thermometer className="w-4 h-4" />
                              <span className={tempStatus.color}>
                                {medication.temperature}°C
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col items-end gap-2">
                          <Badge
                            variant="secondary"
                            className={`${expiryStatus.color} text-white`}
                          >
                            <Calendar className="w-3 h-3 mr-1" />
                            {expiryStatus.label}
                          </Badge>
                          <Badge
                            variant="outline"
                            className={`border-current ${stockLevel.color}`}
                          >
                            {stockLevel.label}
                          </Badge>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="space-y-1">
                          <div className="text-slate-400 text-xs">Current Stock</div>
                          <div className="text-white text-lg">
                            {medication.quantity}
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-slate-400 text-xs">Max Capacity</div>
                          <div className="text-white text-lg">
                            {medication.maxCapacity}
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-slate-400 text-xs">Fill Level</div>
                          <div className="text-white text-lg">
                            {Math.round((medication.quantity / medication.maxCapacity) * 100)}%
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-slate-400 text-xs">Expiry Date</div>
                          <div className="text-white text-sm">
                            {new Date(medication.expiryDate).toLocaleDateString()}
                          </div>
                        </div>
                      </div>

                      {/* Stock Level Bar */}
                      <div className="mt-4">
                        <div className="flex justify-between text-xs text-slate-400 mb-1">
                          <span>Stock Level</span>
                          <span>{Math.round((medication.quantity / medication.maxCapacity) * 100)}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${stockLevel.status === 'high' ? 'bg-green-500' :
                                stockLevel.status === 'medium' ? 'bg-yellow-500' :
                                  stockLevel.status === 'low' ? 'bg-orange-500' :
                                    'bg-red-500'
                              }`}
                            style={{
                              width: `${Math.min((medication.quantity / medication.maxCapacity) * 100, 100)}%`
                            }}
                          />
                        </div>
                      </div>

                      {/* Alerts */}
                      {(expiryStatus.status === 'critical' || expiryStatus.status === 'expired' ||
                        tempStatus.status === 'critical' || stockLevel.status === 'critical') && (
                          <div className="mt-4 p-3 bg-red-900/50 border border-red-500/50 rounded-lg">
                            <div className="flex items-center gap-2 text-red-300 text-sm">
                              <AlertTriangle className="w-4 h-4" />
                              <span>Attention Required:</span>
                            </div>
                            <ul className="mt-2 text-red-200 text-sm space-y-1 ml-6">
                              {(expiryStatus.status === 'critical' || expiryStatus.status === 'expired') && (
                                <li>• {expiryStatus.status === 'expired' ? 'Medication expired' : 'Medication expiring soon'}</li>
                              )}
                              {tempStatus.status === 'critical' && (
                                <li>• Temperature out of safe range</li>
                              )}
                              {stockLevel.status === 'critical' && (
                                <li>• Critical stock level - reorder required</li>
                              )}
                            </ul>
                          </div>
                        )}

                      {/* Action Buttons */}
                      <div className="mt-4 flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleMoveClick(medication)}
                          className="text-blue-400 border-blue-400/50 hover:bg-blue-900/30"
                        >
                          <ArrowRight className="w-4 h-4 mr-1" />
                          Move
                        </Button>
                      </div>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Card className="p-12 bg-slate-800/80 border-slate-700 text-center">
              <Package className="w-16 h-16 text-slate-500 mx-auto mb-4" />
              <h3 className="text-white text-xl mb-2">Empty Shelf</h3>
              <p className="text-slate-400">
                This shelf is currently empty and available for new inventory.
              </p>
              <div className="mt-6 text-slate-300">
                <div className="text-sm">Available Capacity</div>
                <div className="text-2xl">{shelf.capacity} slots</div>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <Card className="p-6 bg-slate-800/80 border-slate-700">
            <h3 className="text-white text-lg mb-4">Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white">
                <Package className="w-4 h-4 mr-2" />
                Add Medication
              </Button>
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white">
                <Clock className="w-4 h-4 mr-2" />
                Schedule Reorder
              </Button>
              <Button variant="outline" className="border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-white">
                <CheckCircle className="w-4 h-4 mr-2" />
                Mark Inspection
              </Button>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Medication Movement Modal */}
      <MedicationMovement
        isOpen={isMoveModalOpen}
        onClose={() => {
          setIsMoveModalOpen(false);
          setSelectedMedication(null);
        }}
        medication={selectedMedication}
      />
    </div>
  );
}