import React, { useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, X, Package, MapPin, Calendar, Thermometer } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useWarehouseLayout, useAisleDetails } from '@/hooks/useWarehouseQueries';
import { Aisle } from './warehouse-types';

interface SearchResult {
  medicationId: string;
  medicationName: string;
  aisleId: string;
  aisleName: string;
  shelfId: string;
  shelfPosition: string;
  quantity: number;
  expiryDate: string;
  category: string;
  temperature: number;
}

interface MedicationSearchProps {
  onResultClick?: (result: SearchResult) => void;
  onAisleNavigate?: (aisleId: string) => void;
  currentAisles?: Aisle[];
}

export function MedicationSearch({ onResultClick, onAisleNavigate, currentAisles }: MedicationSearchProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [expiryFilter, setExpiryFilter] = useState<string>('all');
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const { data: warehouseLayout } = useWarehouseLayout();

  // Simulate searching through all medications in the warehouse
  const searchResults = useMemo(() => {
    if (!searchQuery && categoryFilter === 'all' && expiryFilter === 'all') {
      return [];
    }

    const results: SearchResult[] = [];

    // Search through aisles from current view or warehouse layout
    const aisles = currentAisles || warehouseLayout?.aisles || [];

    aisles.forEach(aisle => {
      // For each aisle, check shelves and medications
      if (aisle.shelves) {
        aisle.shelves.forEach(shelf => {
          shelf.medications?.forEach(med => {
            // Apply search query filter
            const matchesSearch = !searchQuery ||
              med.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
              med.batchNumber?.toLowerCase().includes(searchQuery.toLowerCase());

            // Apply category filter
            const matchesCategory = categoryFilter === 'all' ||
              (categoryFilter === 'refrigerated' && aisle.category === 'Refrigerated') ||
              (categoryFilter === 'controlled' && aisle.category === 'Controlled') ||
              (categoryFilter === 'general' && aisle.category === 'General');

            // Apply expiry filter
            const today = new Date();
            const expiryDate = new Date(med.expiryDate);
            const daysUntilExpiry = Math.floor((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

            const matchesExpiry = expiryFilter === 'all' ||
              (expiryFilter === 'expired' && daysUntilExpiry < 0) ||
              (expiryFilter === 'expiring-soon' && daysUntilExpiry >= 0 && daysUntilExpiry <= 30) ||
              (expiryFilter === 'expiring-90' && daysUntilExpiry >= 0 && daysUntilExpiry <= 90);

            if (matchesSearch && matchesCategory && matchesExpiry) {
              results.push({
                medicationId: med.id,
                medicationName: med.name,
                aisleId: aisle.id,
                aisleName: aisle.name || `Aisle ${aisle.id}`,
                shelfId: shelf.id,
                shelfPosition: `Shelf ${shelf.position + 1}, Level ${shelf.level + 1}`,
                quantity: med.quantity,
                expiryDate: med.expiryDate,
                category: aisle.category,
                temperature: aisle.temperature || 22
              });
            }
          });
        });
      }
    });

    return results;
  }, [searchQuery, categoryFilter, expiryFilter, currentAisles, warehouseLayout]);

  const handleSearch = useCallback(() => {
    setIsSearching(true);
    setShowResults(true);

    // Simulate search delay
    setTimeout(() => {
      setIsSearching(false);
    }, 500);
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setCategoryFilter('all');
    setExpiryFilter('all');
    setShowResults(false);
  };

  const getExpiryBadgeVariant = (expiryDate: string) => {
    const today = new Date();
    const expiry = new Date(expiryDate);
    const daysUntilExpiry = Math.floor((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) return 'destructive';
    if (daysUntilExpiry <= 30) return 'warning';
    if (daysUntilExpiry <= 90) return 'secondary';
    return 'default';
  };

  const getExpiryText = (expiryDate: string) => {
    const today = new Date();
    const expiry = new Date(expiryDate);
    const daysUntilExpiry = Math.floor((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (daysUntilExpiry < 0) return `Expired ${Math.abs(daysUntilExpiry)} days ago`;
    if (daysUntilExpiry === 0) return 'Expires today';
    if (daysUntilExpiry === 1) return 'Expires tomorrow';
    if (daysUntilExpiry <= 30) return `Expires in ${daysUntilExpiry} days`;
    return `Expires ${expiryDate}`;
  };

  return (
    <div className="relative">
      <Card className="bg-slate-800/80 border-slate-700">
        <div className="p-4">
          {/* Search Bar */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search medications, batch numbers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                className="pl-10 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500"
              />
              {searchQuery && (
                <button
                  onClick={clearSearch}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-slate-400 hover:text-white" />
                </button>
              )}
            </div>

            <Popover open={showFilters} onOpenChange={setShowFilters}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="border-slate-600 hover:bg-slate-700"
                >
                  <Filter className="w-4 h-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80 bg-slate-800 border-slate-700" align="end">
                <div className="space-y-4">
                  <h4 className="font-medium text-white">Filter Options</h4>

                  {/* Category Filter */}
                  <div>
                    <label className="text-sm text-slate-300 mb-2 block">Category</label>
                    <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                      <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="all">All Categories</SelectItem>
                        <SelectItem value="general">General</SelectItem>
                        <SelectItem value="refrigerated">Refrigerated</SelectItem>
                        <SelectItem value="controlled">Controlled</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Expiry Filter */}
                  <div>
                    <label className="text-sm text-slate-300 mb-2 block">Expiry Status</label>
                    <Select value={expiryFilter} onValueChange={setExpiryFilter}>
                      <SelectTrigger className="bg-slate-900/50 border-slate-600 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-800 border-slate-700">
                        <SelectItem value="all">All Items</SelectItem>
                        <SelectItem value="expired">Expired</SelectItem>
                        <SelectItem value="expiring-soon">Expiring in 30 days</SelectItem>
                        <SelectItem value="expiring-90">Expiring in 90 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setCategoryFilter('all');
                        setExpiryFilter('all');
                      }}
                      className="flex-1 border-slate-600 hover:bg-slate-700"
                    >
                      Clear Filters
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        handleSearch();
                        setShowFilters(false);
                      }}
                      className="flex-1 bg-blue-600 hover:bg-blue-700"
                    >
                      Apply Filters
                    </Button>
                  </div>
                </div>
              </PopoverContent>
            </Popover>

            <Button
              onClick={handleSearch}
              disabled={isSearching}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSearching ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Search className="w-4 h-4" />
                </motion.div>
              ) : (
                'Search'
              )}
            </Button>
          </div>

          {/* Active Filters Display */}
          {(categoryFilter !== 'all' || expiryFilter !== 'all') && (
            <div className="flex gap-2 mt-3">
              {categoryFilter !== 'all' && (
                <Badge variant="secondary" className="bg-slate-700">
                  Category: {categoryFilter}
                  <button
                    onClick={() => setCategoryFilter('all')}
                    className="ml-2"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              )}
              {expiryFilter !== 'all' && (
                <Badge variant="secondary" className="bg-slate-700">
                  Expiry: {expiryFilter.replace('-', ' ')}
                  <button
                    onClick={() => setExpiryFilter('all')}
                    className="ml-2"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Search Results */}
        <AnimatePresence>
          {showResults && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="border-t border-slate-700 overflow-hidden"
            >
              <div className="p-4">
                {isSearching ? (
                  <div className="text-center py-8">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"
                    />
                    <p className="text-slate-400">Searching warehouse...</p>
                  </div>
                ) : searchResults.length === 0 ? (
                  <div className="text-center py-8">
                    <Package className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No medications found</p>
                    <p className="text-slate-500 text-sm mt-2">Try adjusting your search or filters</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    <p className="text-sm text-slate-400 mb-3">
                      Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
                    </p>
                    {searchResults.map((result, index) => (
                      <motion.div
                        key={`${result.medicationId}-${index}`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="p-3 bg-slate-900/50 rounded-lg border border-slate-700 hover:border-slate-600 cursor-pointer transition-colors"
                        onClick={() => {
                          if (onResultClick) onResultClick(result);
                          if (onAisleNavigate) onAisleNavigate(result.aisleId);
                        }}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="text-white font-medium">{result.medicationName}</h4>
                            <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                              <span className="flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                {result.aisleName}
                              </span>
                              <span>{result.shelfPosition}</span>
                              <span className="flex items-center gap-1">
                                <Package className="w-3 h-3" />
                                Qty: {result.quantity}
                              </span>
                              {result.temperature !== 22 && (
                                <span className="flex items-center gap-1">
                                  <Thermometer className="w-3 h-3" />
                                  {result.temperature}°C
                                </span>
                              )}
                            </div>
                          </div>
                          <Badge
                            variant={getExpiryBadgeVariant(result.expiryDate)}
                            className="text-xs"
                          >
                            {getExpiryText(result.expiryDate)}
                          </Badge>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </div>
  );
}