import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TemperatureMonitor } from './temperature-monitor';
import { ExpiryAlerts } from './expiry-alerts';
import { CapacityWarnings } from './capacity-warnings';

interface MonitoringOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

export function MonitoringOverlay({
  isOpen,
  onClose,
  isExpanded,
  onToggleExpand
}: MonitoringOverlayProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{
            y: 0,
            opacity: 1,
            height: isExpanded ? 'auto' : '60px'
          }}
          exit={{ y: -100, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.23, 1, 0.320, 1] }}
          className="fixed top-16 right-4 z-25 w-auto max-w-6xl bg-slate-900/95 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
        >
          {/* Collapsed View - Compact Strip */}
          {!isExpanded && (
            <div className="flex items-center gap-4 p-4">
              <div className="flex items-center gap-3">
                <div className="text-white font-medium">Monitoring Dashboard</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-1 bg-blue-900/50 text-blue-300 rounded">
                    Temperature: Normal
                  </span>
                  <span className="px-2 py-1 bg-orange-900/50 text-orange-300 rounded">
                    3 Expiring Soon
                  </span>
                  <span className="px-2 py-1 bg-yellow-900/50 text-yellow-300 rounded">
                    2 Capacity Warnings
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onToggleExpand}
                  className="text-slate-400 hover:text-white"
                >
                  <ChevronDown className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Expanded View - Full Dashboard */}
          {isExpanded && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-white font-medium text-lg">Real-time Monitoring</h2>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onToggleExpand}
                    className="text-slate-400 hover:text-white"
                  >
                    <ChevronUp className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <TemperatureMonitor compact={true} autoRefresh={true} />
                <ExpiryAlerts compactView={true} autoRefresh={true} />
                <CapacityWarnings compactView={true} autoRefresh={true} />
              </div>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}