import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  AlertCircle,
  Calendar,
  Package,
  MapPin,
  ChevronRight,
  Filter,
  Download,
  Bell
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { warehouseService } from '@/services/warehouseService';
import { cn } from '@/lib/utils';

interface ExpiryAlert {
  med_id: number;
  medication_name: string;
  batch_number: string;
  expiry_date: string;
  days_until_expiry: number;
  quantity: number;
  location: {
    aisle: string;
    shelf: string;
    position?: string;
  };
  severity: 'critical' | 'warning' | 'info';
  action_required?: string;
}

interface ExpiryAlertsProps {
  compactView?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onMedicationClick?: (medication: ExpiryAlert) => void;
}

export function ExpiryAlerts({
  compactView = false,
  autoRefresh = true,
  refreshInterval = 60000,
  onMedicationClick
}: ExpiryAlertsProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | 'critical' | 'warning' | 'info'>('all');
  const [expandedAlerts, setExpandedAlerts] = useState<Set<string>>(new Set());

  // Fetch alerts from API
  const { data: alertsData, isLoading, refetch } = useQuery({
    queryKey: ['expiry-alerts'],
    queryFn: async () => {
      const alerts = await warehouseService.getWarehouseAlerts();

      // Transform alerts to expiry-specific format
      const expiryAlerts: ExpiryAlert[] = alerts.alerts
        .filter((alert: any) => alert.type === 'expiry')
        .map((alert: any) => {
          // Parse the message to extract medication details
          const medicationMatch = alert.message.match(/^(.*?) \(Lot: (.*?)\) expires in (\d+) days$/);

          return {
            med_id: Math.random() * 100, // Would come from API
            medication_name: medicationMatch?.[1] || 'Unknown',
            batch_number: medicationMatch?.[2] || 'N/A',
            expiry_date: new Date(Date.now() + parseInt(medicationMatch?.[3] || '0') * 24 * 60 * 60 * 1000).toISOString(),
            days_until_expiry: parseInt(medicationMatch?.[3] || '0'),
            quantity: Math.floor(Math.random() * 100) + 1, // Would come from API
            location: {
              aisle: alert.location.split(' - ')[0] || 'Unknown',
              shelf: alert.location.split(' - ')[1] || 'Unknown'
            },
            severity: alert.severity,
            action_required: alert.severity === 'critical' ? 'Immediate removal required' :
                           alert.severity === 'warning' ? 'Schedule for rotation' :
                           'Monitor closely'
          };
        });

      return expiryAlerts;
    },
    refetchInterval: autoRefresh ? refreshInterval : false
  });

  // Filter alerts by severity
  const filteredAlerts = useMemo(() => {
    if (!alertsData) return [];
    if (selectedSeverity === 'all') return alertsData;
    return alertsData.filter((alert: ExpiryAlert) => alert.severity === selectedSeverity);
  }, [alertsData, selectedSeverity]);

  // Group alerts by severity for summary
  const alertSummary = useMemo(() => {
    if (!alertsData) return { critical: 0, warning: 0, info: 0 };

    return alertsData.reduce((acc: any, alert: ExpiryAlert) => {
      acc[alert.severity] = (acc[alert.severity] || 0) + 1;
      return acc;
    }, { critical: 0, warning: 0, info: 0 });
  }, [alertsData]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return {
          bg: 'bg-red-900/20',
          border: 'border-red-700/50',
          text: 'text-red-400',
          badge: 'bg-red-500'
        };
      case 'warning':
        return {
          bg: 'bg-yellow-900/20',
          border: 'border-yellow-700/50',
          text: 'text-yellow-400',
          badge: 'bg-yellow-500'
        };
      case 'info':
        return {
          bg: 'bg-blue-900/20',
          border: 'border-blue-700/50',
          text: 'text-blue-400',
          badge: 'bg-blue-500'
        };
      default:
        return {
          bg: 'bg-gray-900/20',
          border: 'border-gray-700/50',
          text: 'text-gray-400',
          badge: 'bg-gray-500'
        };
    }
  };

  const toggleAlert = (alertId: string) => {
    setExpandedAlerts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(alertId)) {
        newSet.delete(alertId);
      } else {
        newSet.add(alertId);
      }
      return newSet;
    });
  };

  const handleExport = () => {
    // Export alerts to CSV
    const csv = [
      ['Medication', 'Batch', 'Expiry Date', 'Days Until Expiry', 'Quantity', 'Location', 'Severity', 'Action Required'],
      ...filteredAlerts.map((alert: ExpiryAlert) => [
        alert.medication_name,
        alert.batch_number,
        new Date(alert.expiry_date).toLocaleDateString(),
        alert.days_until_expiry,
        alert.quantity,
        `${alert.location.aisle} - ${alert.location.shelf}`,
        alert.severity,
        alert.action_required || ''
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `expiry-alerts-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  if (compactView) {
    // Compact view for dashboard
    return (
      <Card className="p-4 bg-slate-800/80 border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-400" />
            <h3 className="text-white font-medium">Expiry Alerts</h3>
          </div>
          <Badge variant="secondary" className="bg-red-900/50 text-red-300">
            {alertSummary.critical} Critical
          </Badge>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-12 bg-slate-700/50 rounded animate-pulse" />
            ))}
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="text-center py-4 text-slate-400">
            No expiry alerts
          </div>
        ) : (
          <div className="space-y-2">
            {filteredAlerts.slice(0, 5).map((alert: ExpiryAlert, index: number) => {
              const colors = getSeverityColor(alert.severity);
              return (
                <div
                  key={index}
                  className={cn(
                    "p-2 rounded-lg border cursor-pointer hover:bg-slate-700/30 transition-colors",
                    colors.bg,
                    colors.border
                  )}
                  onClick={() => onMedicationClick?.(alert)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-medium truncate">
                        {alert.medication_name}
                      </p>
                      <p className="text-slate-400 text-xs">
                        {alert.location.aisle} • {alert.days_until_expiry} days
                      </p>
                    </div>
                    <ChevronRight className={cn("w-4 h-4 flex-shrink-0", colors.text)} />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {filteredAlerts.length > 5 && (
          <div className="mt-3 text-center">
            <Button
              size="sm"
              variant="ghost"
              className="text-blue-400 hover:text-blue-300"
            >
              View all {filteredAlerts.length} alerts
            </Button>
          </div>
        )}
      </Card>
    );
  }

  // Full view
  return (
    <Card className="p-6 bg-slate-800/80 border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-yellow-500/20 rounded-lg">
            <Calendar className="w-6 h-6 text-yellow-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Expiry Alert System</h2>
            <p className="text-slate-400 text-sm">Monitor and manage medication expiry dates</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="text-slate-300 border-slate-600"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="text-slate-300 border-slate-600"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Alert Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="p-4 bg-red-900/20 border-red-700/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-400 text-sm">Critical</p>
              <p className="text-3xl font-bold text-white">{alertSummary.critical}</p>
            </div>
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
        </Card>

        <Card className="p-4 bg-yellow-900/20 border-yellow-700/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-yellow-400 text-sm">Warning</p>
              <p className="text-3xl font-bold text-white">{alertSummary.warning}</p>
            </div>
            <AlertCircle className="w-8 h-8 text-yellow-400" />
          </div>
        </Card>

        <Card className="p-4 bg-blue-900/20 border-blue-700/50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-400 text-sm">Info</p>
              <p className="text-3xl font-bold text-white">{alertSummary.info}</p>
            </div>
            <Bell className="w-8 h-8 text-blue-400" />
          </div>
        </Card>
      </div>

      {/* Severity Filter */}
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-4 h-4 text-slate-400" />
        <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1">
          {(['all', 'critical', 'warning', 'info'] as const).map((severity) => (
            <button
              key={severity}
              onClick={() => setSelectedSeverity(severity)}
              className={cn(
                "px-3 py-1 text-sm rounded transition-colors capitalize",
                selectedSeverity === severity
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white"
              )}
            >
              {severity}
              {severity !== 'all' && alertSummary[severity] > 0 && (
                <span className="ml-1 text-xs">({alertSummary[severity]})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Alert List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-slate-700/30 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          <p className="text-slate-400">No expiry alerts found</p>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {filteredAlerts.map((alert: ExpiryAlert, index: number) => {
              const colors = getSeverityColor(alert.severity);
              const alertId = `${alert.med_id}-${alert.batch_number}`;
              const isExpanded = expandedAlerts.has(alertId);

              return (
                <motion.div
                  key={alertId}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.05 }}
                  className={cn(
                    "rounded-lg border overflow-hidden",
                    colors.bg,
                    colors.border
                  )}
                >
                  <div
                    className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => toggleAlert(alertId)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Package className={cn("w-4 h-4", colors.text)} />
                          <h3 className="text-white font-medium">{alert.medication_name}</h3>
                          <Badge className={cn("text-white", colors.badge)}>
                            {alert.days_until_expiry === 0
                              ? 'Expires Today'
                              : alert.days_until_expiry < 0
                              ? 'Expired'
                              : `${alert.days_until_expiry} days`}
                          </Badge>
                        </div>

                        <div className="flex items-center gap-4 text-sm text-slate-300">
                          <span>Batch: {alert.batch_number}</span>
                          <span>Qty: {alert.quantity}</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {alert.location.aisle} - {alert.location.shelf}
                          </span>
                        </div>
                      </div>

                      <ChevronRight
                        className={cn(
                          "w-5 h-5 transition-transform",
                          colors.text,
                          isExpanded && "rotate-90"
                        )}
                      />
                    </div>
                  </div>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="border-t border-slate-700/50"
                      >
                        <div className="p-4 space-y-3">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="text-slate-400">Expiry Date</p>
                              <p className="text-white">
                                {new Date(alert.expiry_date).toLocaleDateString()}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-400">Action Required</p>
                              <p className={colors.text}>{alert.action_required}</p>
                            </div>
                          </div>

                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => onMedicationClick?.(alert)}
                              className="text-blue-400 border-blue-400/50 hover:bg-blue-900/30"
                            >
                              View Details
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-green-400 border-green-400/50 hover:bg-green-900/30"
                            >
                              Mark Resolved
                            </Button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {autoRefresh && (
        <div className="mt-4 text-center text-slate-500 text-sm">
          Auto-refreshing every {refreshInterval / 1000} seconds
        </div>
      )}
    </Card>
  );
}