import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Thermometer, AlertTriangle, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';

interface TemperatureReading {
  aisle_id: number;
  aisle_name: string;
  temperature: number;
  humidity: number;
  reading_time: string;
  alert_triggered: boolean;
  temperature_range: string;
  trend?: 'up' | 'down' | 'stable';
}

interface TemperatureMonitorProps {
  aisleId?: number;
  compact?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function TemperatureMonitor({
  aisleId,
  compact = false,
  autoRefresh = true,
  refreshInterval = 30000
}: TemperatureMonitorProps) {
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '6h' | '24h'>('1h');

  // Fetch temperature data
  const { data: temperatures, isLoading, refetch } = useQuery({
    queryKey: ['temperature-readings', aisleId, selectedTimeRange],
    queryFn: async () => {
      // Simulated API call - replace with actual endpoint
      const mockData: TemperatureReading[] = [
        {
          aisle_id: 1,
          aisle_name: "Controlled Substances A",
          temperature: 22.5,
          humidity: 45,
          reading_time: new Date().toISOString(),
          alert_triggered: false,
          temperature_range: "20-25°C",
          trend: 'stable'
        },
        {
          aisle_id: 2,
          aisle_name: "Refrigerated Storage B",
          temperature: 4.2,
          humidity: 60,
          reading_time: new Date().toISOString(),
          alert_triggered: false,
          temperature_range: "2-8°C",
          trend: 'up'
        },
        {
          aisle_id: 3,
          aisle_name: "General Storage C",
          temperature: 23.8,
          humidity: 50,
          reading_time: new Date().toISOString(),
          alert_triggered: false,
          temperature_range: "15-30°C",
          trend: 'down'
        },
        {
          aisle_id: 4,
          aisle_name: "Refrigerated Storage D",
          temperature: 9.1,
          humidity: 65,
          reading_time: new Date().toISOString(),
          alert_triggered: true,
          temperature_range: "2-8°C",
          trend: 'up'
        }
      ];

      if (aisleId) {
        return mockData.filter(t => t.aisle_id === aisleId);
      }
      return mockData;
    },
    refetchInterval: autoRefresh ? refreshInterval : false
  });

  // Get temperature status
  const getTemperatureStatus = (temp: number, range: string) => {
    const [min, max] = range.match(/\d+/g)?.map(Number) || [0, 100];

    if (temp < min - 1 || temp > max + 1) {
      return { status: 'critical', color: 'bg-red-500', textColor: 'text-red-500' };
    }
    if (temp < min || temp > max) {
      return { status: 'warning', color: 'bg-yellow-500', textColor: 'text-yellow-500' };
    }
    return { status: 'normal', color: 'bg-green-500', textColor: 'text-green-500' };
  };

  // Get trend icon
  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-orange-400" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-blue-400" />;
      default:
        return <div className="w-4 h-4 bg-gray-400 rounded-full" />;
    }
  };

  if (compact) {
    // Compact view for dashboard
    return (
      <Card className="p-4 bg-slate-800/80 border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Thermometer className="w-5 h-5 text-blue-400" />
            <h3 className="text-white font-medium">Temperature Monitor</h3>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => refetch()}
            className="text-slate-400 hover:text-white"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-8 bg-slate-700/50 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {temperatures?.slice(0, 3).map((reading) => {
              const status = getTemperatureStatus(reading.temperature, reading.temperature_range);
              return (
                <div
                  key={reading.aisle_id}
                  className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <div className={cn("w-2 h-2 rounded-full", status.color)} />
                    <span className="text-slate-300 text-sm">{reading.aisle_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn("font-medium", status.textColor)}>
                      {reading.temperature}°C
                    </span>
                    {getTrendIcon(reading.trend)}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {temperatures && temperatures.some(t => t.alert_triggered) && (
          <div className="mt-3 p-2 bg-red-900/30 border border-red-700/50 rounded-lg">
            <div className="flex items-center gap-2 text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4" />
              <span>{temperatures.filter(t => t.alert_triggered).length} Temperature Alert(s)</span>
            </div>
          </div>
        )}
      </Card>
    );
  }

  // Full view
  return (
    <Card className="p-6 bg-slate-800/80 border-slate-700">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Thermometer className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Temperature Monitoring</h2>
            <p className="text-slate-400 text-sm">Real-time temperature and humidity tracking</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Time Range Selector */}
          <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1">
            {(['1h', '6h', '24h'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRange(range)}
                className={cn(
                  "px-3 py-1 text-sm rounded transition-colors",
                  selectedTimeRange === range
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:text-white"
                )}
              >
                {range}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="text-slate-300 border-slate-600"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-32 bg-slate-700/30 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {temperatures?.map((reading) => {
            const status = getTemperatureStatus(reading.temperature, reading.temperature_range);
            const isAlert = reading.alert_triggered;

            return (
              <motion.div
                key={reading.aisle_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "p-4 rounded-lg border transition-all",
                  isAlert
                    ? "bg-red-900/20 border-red-700/50"
                    : "bg-slate-700/30 border-slate-600/50"
                )}
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-white font-medium">{reading.aisle_name}</h3>
                    <p className="text-slate-400 text-sm">Target: {reading.temperature_range}</p>
                  </div>
                  {isAlert && (
                    <Badge variant="destructive" className="animate-pulse">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Alert
                    </Badge>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-slate-400 text-sm">Temperature</span>
                      {getTrendIcon(reading.trend)}
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className={cn("text-2xl font-bold", status.textColor)}>
                        {reading.temperature}
                      </span>
                      <span className="text-slate-400 text-sm">°C</span>
                    </div>
                  </div>

                  <div>
                    <div className="text-slate-400 text-sm mb-1">Humidity</div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-bold text-white">
                        {reading.humidity}
                      </span>
                      <span className="text-slate-400 text-sm">%</span>
                    </div>
                  </div>
                </div>

                {/* Temperature Range Indicator */}
                <div className="mt-3">
                  <div className="relative h-2 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={cn("absolute h-full transition-all", status.color)}
                      style={{
                        left: '20%',
                        width: '60%'
                      }}
                    />
                    <div
                      className="absolute w-3 h-3 bg-white rounded-full -top-0.5 transition-all"
                      style={{
                        left: `${Math.min(Math.max(((reading.temperature - 0) / 40) * 100, 0), 100)}%`,
                        transform: 'translateX(-50%)'
                      }}
                    />
                  </div>
                </div>

                <div className="mt-2 text-xs text-slate-400">
                  Last updated: {new Date(reading.reading_time).toLocaleTimeString()}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Alert Summary */}
      {temperatures && temperatures.some(t => t.alert_triggered) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6 p-4 bg-red-900/20 border border-red-700/50 rounded-lg"
        >
          <div className="flex items-center gap-2 text-red-400 mb-2">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-medium">Temperature Alerts Active</span>
          </div>
          <ul className="space-y-1 text-red-300 text-sm ml-7">
            {temperatures
              .filter(t => t.alert_triggered)
              .map(t => (
                <li key={t.aisle_id}>
                  • {t.aisle_name}: {t.temperature}°C (Target: {t.temperature_range})
                </li>
              ))}
          </ul>
        </motion.div>
      )}

      {autoRefresh && (
        <div className="mt-4 text-center text-slate-500 text-sm">
          Auto-refreshing every {refreshInterval / 1000} seconds
        </div>
      )}
    </Card>
  );
}