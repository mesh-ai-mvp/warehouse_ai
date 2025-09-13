import React from 'react';
import { motion } from 'motion/react';
import { AlertTriangle, Package, TrendingUp, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useWarehouseLayout } from '@/hooks/useWarehouseQueries';

interface CapacityWarning {
  id: string;
  type: 'aisle' | 'shelf' | 'zone';
  name: string;
  currentCapacity: number;
  maxCapacity: number;
  utilizationPercent: number;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  recommendation: string;
}

interface CapacityWarningsProps {
  compactView?: boolean;
  autoRefresh?: boolean;
}

export function CapacityWarnings({ compactView = false, autoRefresh = false }: CapacityWarningsProps) {
  const { data: warehouseLayout } = useWarehouseLayout({
    refetchInterval: autoRefresh ? 30000 : undefined
  });

  // Calculate capacity warnings from warehouse data
  const warnings: CapacityWarning[] = React.useMemo(() => {
    if (!warehouseLayout) return [];

    const calculatedWarnings: CapacityWarning[] = [];

    // Check each aisle for capacity issues
    warehouseLayout.aisles.forEach(aisle => {
      const utilization = aisle.avg_utilization || 0;

      if (utilization >= 90) {
        calculatedWarnings.push({
          id: `aisle-${aisle.aisle_id}`,
          type: 'aisle',
          name: aisle.aisle_name,
          currentCapacity: Math.round(utilization),
          maxCapacity: 100,
          utilizationPercent: utilization,
          severity: 'critical',
          message: `${aisle.aisle_name} is at ${utilization.toFixed(0)}% capacity`,
          recommendation: 'Immediate redistribution needed. Consider moving items to underutilized aisles.'
        });
      } else if (utilization >= 75) {
        calculatedWarnings.push({
          id: `aisle-${aisle.aisle_id}`,
          type: 'aisle',
          name: aisle.aisle_name,
          currentCapacity: Math.round(utilization),
          maxCapacity: 100,
          utilizationPercent: utilization,
          severity: 'warning',
          message: `${aisle.aisle_name} approaching capacity limit`,
          recommendation: 'Plan for redistribution soon to prevent overcrowding.'
        });
      }
    });

    // Check zones for overall capacity
    warehouseLayout.zones.forEach(zone => {
      const totalMedications = warehouseLayout.stats?.total_medications || 0;
      const zoneCapacity = zone.capacity || 1000;
      const zoneUtilization = (totalMedications / (warehouseLayout.zones.length * zoneCapacity)) * 100;

      if (zoneUtilization >= 85) {
        calculatedWarnings.push({
          id: `zone-${zone.zone_id}`,
          type: 'zone',
          name: zone.zone_name,
          currentCapacity: Math.round(zoneUtilization),
          maxCapacity: 100,
          utilizationPercent: zoneUtilization,
          severity: zoneUtilization >= 95 ? 'critical' : 'warning',
          message: `Zone ${zone.zone_name} at ${zoneUtilization.toFixed(0)}% capacity`,
          recommendation: 'Consider expanding storage or optimizing shelf arrangements.'
        });
      }
    });

    // Sort by severity
    return calculatedWarnings.sort((a, b) => {
      const severityOrder = { critical: 0, warning: 1, info: 2 };
      return severityOrder[a.severity] - severityOrder[b.severity];
    });
  }, [warehouseLayout]);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default:
        return <Package className="w-4 h-4 text-blue-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500';
      case 'warning':
        return 'bg-yellow-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getProgressColor = (utilization: number) => {
    if (utilization >= 90) return 'bg-red-500';
    if (utilization >= 75) return 'bg-yellow-500';
    if (utilization >= 50) return 'bg-blue-500';
    return 'bg-green-500';
  };

  if (compactView) {
    return (
      <Card className="p-4 bg-slate-800/80 border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white font-medium flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Capacity Alerts
          </h3>
          <Badge variant={warnings.length > 0 ? 'destructive' : 'secondary'}>
            {warnings.length} {warnings.length === 1 ? 'Alert' : 'Alerts'}
          </Badge>
        </div>

        {warnings.length === 0 ? (
          <p className="text-slate-400 text-sm">All storage areas within normal capacity</p>
        ) : (
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {warnings.slice(0, 3).map(warning => (
              <div key={warning.id} className="flex items-center gap-2 text-sm">
                {getSeverityIcon(warning.severity)}
                <span className="text-slate-300 flex-1 truncate">{warning.message}</span>
              </div>
            ))}
            {warnings.length > 3 && (
              <p className="text-slate-500 text-xs">+{warnings.length - 3} more alerts</p>
            )}
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card className="bg-slate-800/80 border-slate-700">
      <div className="p-6 border-b border-slate-700">
        <div className="flex items-center justify-between">
          <h2 className="text-xl text-white font-semibold flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Capacity Management
          </h2>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-slate-600 text-slate-300">
              {warnings.filter(w => w.severity === 'critical').length} Critical
            </Badge>
            <Badge variant="outline" className="border-slate-600 text-slate-300">
              {warnings.filter(w => w.severity === 'warning').length} Warnings
            </Badge>
          </div>
        </div>
      </div>

      <div className="p-6">
        {warnings.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-8"
          >
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Package className="w-8 h-8 text-green-500" />
            </div>
            <p className="text-green-400 font-medium mb-2">Optimal Capacity</p>
            <p className="text-slate-400 text-sm">All storage areas are within normal operating capacity</p>
          </motion.div>
        ) : (
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {warnings.map((warning, index) => (
              <motion.div
                key={warning.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-4 rounded-lg border ${
                  warning.severity === 'critical'
                    ? 'bg-red-900/20 border-red-800'
                    : warning.severity === 'warning'
                    ? 'bg-yellow-900/20 border-yellow-800'
                    : 'bg-blue-900/20 border-blue-800'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-1">{getSeverityIcon(warning.severity)}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-white font-medium">{warning.name}</h4>
                      <Badge
                        variant={warning.severity === 'critical' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {warning.type.toUpperCase()}
                      </Badge>
                    </div>

                    <p className="text-slate-300 text-sm mb-2">{warning.message}</p>

                    <div className="mb-3">
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Utilization</span>
                        <span>{warning.utilizationPercent.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${warning.utilizationPercent}%` }}
                          transition={{ duration: 1, delay: index * 0.1 }}
                          className={`h-full ${getProgressColor(warning.utilizationPercent)}`}
                        />
                      </div>
                    </div>

                    <div className="flex items-start gap-2">
                      <span className="text-xs text-slate-500">Recommendation:</span>
                      <p className="text-xs text-slate-400 italic">{warning.recommendation}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Summary Statistics */}
        <div className="mt-6 pt-6 border-t border-slate-700">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl text-white font-semibold">
                {warehouseLayout?.stats?.total_shelves || 0}
              </div>
              <div className="text-xs text-slate-400">Total Shelves</div>
            </div>
            <div className="text-center">
              <div className="text-2xl text-white font-semibold">
                {warehouseLayout?.stats?.avg_utilization?.toFixed(1) || 0}%
              </div>
              <div className="text-xs text-slate-400">Avg Utilization</div>
            </div>
            <div className="text-center">
              <div className="text-2xl text-white font-semibold">
                {warehouseLayout?.stats?.total_medications || 0}
              </div>
              <div className="text-xs text-slate-400">Total Items</div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}