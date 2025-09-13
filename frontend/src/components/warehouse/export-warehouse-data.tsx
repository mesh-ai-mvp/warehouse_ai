import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Download, FileText, FileSpreadsheet, FileJson, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useWarehouseLayout, useAisleDetails } from '@/hooks/useWarehouseQueries';
import { toast } from '@/hooks/use-toast';

interface ExportOptions {
  format: 'csv' | 'json' | 'excel';
  includeInventory: boolean;
  includeExpiry: boolean;
  includeCapacity: boolean;
  includeTemperature: boolean;
  dateRange: 'all' | 'expiring-30' | 'expiring-90';
}

export function ExportWarehouseData() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'csv',
    includeInventory: true,
    includeExpiry: true,
    includeCapacity: true,
    includeTemperature: false,
    dateRange: 'all'
  });

  const { data: warehouseLayout } = useWarehouseLayout();

  const generateCSV = () => {
    if (!warehouseLayout) return '';

    let csv = 'Aisle,Category,Temperature,Shelf Count,Avg Utilization,Medication Count\n';

    warehouseLayout.aisles.forEach(aisle => {
      csv += `"${aisle.aisle_name}","${aisle.category}",${aisle.temperature},${aisle.shelf_count || 0},${aisle.avg_utilization || 0},${aisle.medication_count || 0}\n`;
    });

    if (exportOptions.includeInventory) {
      csv += '\n\nMedication Inventory Report\n';
      csv += 'Aisle,Shelf,Medication,Quantity,Expiry Date,Status\n';

      // Add medication details if available
      warehouseLayout.aisles.forEach(aisle => {
        // Simulated medication data - in real implementation, fetch from API
        csv += `"${aisle.aisle_name}","Shelf 1","Sample Med",100,"2025-12-31","In Stock"\n`;
      });
    }

    if (exportOptions.includeCapacity) {
      csv += '\n\nCapacity Report\n';
      csv += 'Zone,Total Capacity,Used Capacity,Available,Utilization %\n';

      warehouseLayout.zones.forEach(zone => {
        const capacity = zone.capacity || 1000;
        const used = Math.round(capacity * 0.75); // Simulated data
        csv += `"${zone.zone_name}",${capacity},${used},${capacity - used},${((used/capacity)*100).toFixed(1)}\n`;
      });
    }

    return csv;
  };

  const generateJSON = () => {
    if (!warehouseLayout) return '{}';

    const exportData: any = {
      exportDate: new Date().toISOString(),
      warehouse: {
        totalZones: warehouseLayout.zones.length,
        totalAisles: warehouseLayout.aisles.length,
        totalShelves: warehouseLayout.stats?.total_shelves || 0,
        totalMedications: warehouseLayout.stats?.total_medications || 0,
        avgUtilization: warehouseLayout.stats?.avg_utilization || 0
      },
      zones: warehouseLayout.zones,
      aisles: warehouseLayout.aisles
    };

    if (exportOptions.includeInventory) {
      exportData.inventory = {
        totalItems: warehouseLayout.stats?.total_medications || 0,
        criticalAlerts: warehouseLayout.stats?.critical_alerts || 0,
        expiringSoon: warehouseLayout.stats?.expiring_soon || 0
      };
    }

    if (exportOptions.includeCapacity) {
      exportData.capacity = warehouseLayout.zones.map(zone => ({
        zoneName: zone.zone_name,
        capacity: zone.capacity || 1000,
        utilization: 75 // Simulated
      }));
    }

    return JSON.stringify(exportData, null, 2);
  };

  const handleExport = async () => {
    setIsExporting(true);
    setExportSuccess(false);

    try {
      let data: string;
      let filename: string;
      let mimeType: string;

      switch (exportOptions.format) {
        case 'csv':
          data = generateCSV();
          filename = `warehouse-export-${new Date().toISOString().split('T')[0]}.csv`;
          mimeType = 'text/csv';
          break;
        case 'json':
          data = generateJSON();
          filename = `warehouse-export-${new Date().toISOString().split('T')[0]}.json`;
          mimeType = 'application/json';
          break;
        case 'excel':
          // For Excel, we'd need a library like xlsx, so we'll use CSV for now
          data = generateCSV();
          filename = `warehouse-export-${new Date().toISOString().split('T')[0]}.csv`;
          mimeType = 'text/csv';
          toast({
            title: "Excel Export",
            description: "Exporting as CSV format compatible with Excel",
          });
          break;
        default:
          throw new Error('Invalid format');
      }

      // Create blob and download
      const blob = new Blob([data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setExportSuccess(true);
      toast({
        title: "Export Successful",
        description: `Data exported as ${filename}`,
      });

      // Reset success state after 3 seconds
      setTimeout(() => {
        setExportSuccess(false);
        setIsOpen(false);
      }, 3000);

    } catch (error) {
      console.error('Export failed:', error);
      toast({
        title: "Export Failed",
        description: "There was an error exporting the data",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'csv':
        return <FileText className="w-4 h-4" />;
      case 'excel':
        return <FileSpreadsheet className="w-4 h-4" />;
      case 'json':
        return <FileJson className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="border-slate-600 hover:bg-slate-700"
        >
          <Download className="w-4 h-4 mr-2" />
          Export Data
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px] bg-slate-800 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">Export Warehouse Data</DialogTitle>
          <DialogDescription className="text-slate-400">
            Choose your export format and select which data to include
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Format Selection */}
          <div className="space-y-2">
            <Label className="text-slate-300">Export Format</Label>
            <div className="grid grid-cols-3 gap-3">
              {(['csv', 'json', 'excel'] as const).map((format) => (
                <Card
                  key={format}
                  className={`p-3 cursor-pointer transition-all ${
                    exportOptions.format === format
                      ? 'bg-blue-900/30 border-blue-500'
                      : 'bg-slate-900/50 border-slate-700 hover:border-slate-600'
                  }`}
                  onClick={() => setExportOptions(prev => ({ ...prev, format }))}
                >
                  <div className="flex flex-col items-center gap-2">
                    {getFormatIcon(format)}
                    <span className="text-xs text-slate-300 uppercase">{format}</span>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Data Selection */}
          <div className="space-y-2">
            <Label className="text-slate-300">Include Data</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="inventory"
                  checked={exportOptions.includeInventory}
                  onCheckedChange={(checked) =>
                    setExportOptions(prev => ({ ...prev, includeInventory: checked as boolean }))
                  }
                  className="border-slate-600"
                />
                <label
                  htmlFor="inventory"
                  className="text-sm text-slate-300 cursor-pointer"
                >
                  Inventory Details
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="expiry"
                  checked={exportOptions.includeExpiry}
                  onCheckedChange={(checked) =>
                    setExportOptions(prev => ({ ...prev, includeExpiry: checked as boolean }))
                  }
                  className="border-slate-600"
                />
                <label
                  htmlFor="expiry"
                  className="text-sm text-slate-300 cursor-pointer"
                >
                  Expiry Information
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="capacity"
                  checked={exportOptions.includeCapacity}
                  onCheckedChange={(checked) =>
                    setExportOptions(prev => ({ ...prev, includeCapacity: checked as boolean }))
                  }
                  className="border-slate-600"
                />
                <label
                  htmlFor="capacity"
                  className="text-sm text-slate-300 cursor-pointer"
                >
                  Capacity Reports
                </label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="temperature"
                  checked={exportOptions.includeTemperature}
                  onCheckedChange={(checked) =>
                    setExportOptions(prev => ({ ...prev, includeTemperature: checked as boolean }))
                  }
                  className="border-slate-600"
                />
                <label
                  htmlFor="temperature"
                  className="text-sm text-slate-300 cursor-pointer"
                >
                  Temperature Logs
                </label>
              </div>
            </div>
          </div>

          {/* Date Range Filter */}
          <div className="space-y-2">
            <Label className="text-slate-300">Expiry Date Range</Label>
            <Select
              value={exportOptions.dateRange}
              onValueChange={(value: any) =>
                setExportOptions(prev => ({ ...prev, dateRange: value }))
              }
            >
              <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">All Items</SelectItem>
                <SelectItem value="expiring-30">Expiring in 30 days</SelectItem>
                <SelectItem value="expiring-90">Expiring in 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Export Summary */}
          <Card className="p-4 bg-slate-900/50 border-slate-700">
            <h4 className="text-sm text-slate-300 mb-2">Export Summary</h4>
            <div className="space-y-1 text-xs text-slate-400">
              <div>Format: {exportOptions.format.toUpperCase()}</div>
              <div>Total Zones: {warehouseLayout?.zones.length || 0}</div>
              <div>Total Aisles: {warehouseLayout?.aisles.length || 0}</div>
              <div>Total Medications: {warehouseLayout?.stats?.total_medications || 0}</div>
            </div>
          </Card>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            onClick={() => setIsOpen(false)}
            className="border-slate-600 hover:bg-slate-700"
          >
            Cancel
          </Button>
          <Button
            onClick={handleExport}
            disabled={isExporting || exportSuccess}
            className={exportSuccess ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}
          >
            {isExporting ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="mr-2"
                >
                  <Download className="w-4 h-4" />
                </motion.div>
                Exporting...
              </>
            ) : exportSuccess ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                Exported!
              </>
            ) : (
              <>
                <Download className="w-4 h-4 mr-2" />
                Export
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}