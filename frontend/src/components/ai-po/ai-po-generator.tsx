import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle, DrawerTrigger } from '@/components/ui/drawer';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAIPOGeneration } from '@/hooks/use-ai-po';
import { Bot, Sparkles, TrendingUp, Package, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface AIPOGenerationParams {
  store_ids?: number[];
  category_filter?: string;
  days_forecast?: number;
  urgency_threshold?: number;
}

export function AIPOGenerator({ onGenerated }: { onGenerated?: (result: any) => void }) {
  const [open, setOpen] = useState(false);
  const [params, setParams] = useState<AIPOGenerationParams>({
    days_forecast: 30,
    urgency_threshold: 0.5,
  });

  const { generatePO, isGenerating, progress, status, result, error, resetGeneration } = useAIPOGeneration();

  const handleGenerate = () => {
    generatePO(params);
  };

  const handleAcceptResult = () => {
    if (result && onGenerated) {
      onGenerated(result);
      setOpen(false);
      resetGeneration();
      toast.success('AI recommendations applied to your order');
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'generating':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      default:
        return <Bot className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusMessage = () => {
    if (progress < 25) return "Analyzing inventory levels...";
    if (progress < 50) return "Calculating demand forecasts...";
    if (progress < 75) return "Evaluating supplier options...";
    if (progress < 100) return "Optimizing purchase recommendations...";
    return "AI analysis complete!";
  };

  return (
    <Drawer open={open} onOpenChange={setOpen}>
      <DrawerTrigger asChild>
        <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
          <Bot className="mr-2 h-4 w-4" />
          AI Generate PO
          <Sparkles className="ml-2 h-4 w-4" />
        </Button>
      </DrawerTrigger>
      
      <DrawerContent className="max-h-[80vh]">
        <DrawerHeader>
          <DrawerTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            AI Purchase Order Generation
          </DrawerTitle>
          <DrawerDescription>
            Let our AI analyze your inventory and generate optimal purchase orders
          </DrawerDescription>
        </DrawerHeader>

        <div className="px-4 pb-4 space-y-6">
          {!isGenerating && !result && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="forecast-days">Forecast Period (days)</Label>
                  <Input
                    id="forecast-days"
                    type="number"
                    value={params.days_forecast}
                    onChange={(e) => setParams(prev => ({ ...prev, days_forecast: parseInt(e.target.value) }))}
                    min="7"
                    max="90"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="urgency">Urgency Threshold</Label>
                  <Select
                    value={params.urgency_threshold?.toString()}
                    onValueChange={(value) => setParams(prev => ({ ...prev, urgency_threshold: parseFloat(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0.25">High Priority (25% stock)</SelectItem>
                      <SelectItem value="0.5">Normal (50% stock)</SelectItem>
                      <SelectItem value="0.75">Low Priority (75% stock)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Alert>
                <TrendingUp className="h-4 w-4" />
                <AlertDescription>
                  Our AI will analyze consumption patterns, supplier performance, and stock levels to generate optimal purchase recommendations.
                </AlertDescription>
              </Alert>

              <Button 
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full"
                size="lg"
              >
                <Bot className="mr-2 h-4 w-4" />
                Generate AI Recommendations
              </Button>
            </div>
          )}

          {isGenerating && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {getStatusIcon()}
                  AI Analysis in Progress
                </CardTitle>
                <CardDescription>
                  {status === 'generating' ? getStatusMessage() : 'Working...'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Progress</span>
                    <span>{progress}%</span>
                  </div>
                  <Progress value={progress} className="w-full" />
                </div>
                
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  This usually takes 1-2 minutes
                </div>
              </CardContent>
            </Card>
          )}

          {result && status === 'completed' && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  AI Recommendations Ready
                </CardTitle>
                <CardDescription>Review and apply to the form below.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm text-muted-foreground">Estimated Total</Label>
                    <div className="text-2xl font-bold text-green-600">
                      ${result.estimated_total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm text-muted-foreground">Recommended Supplier</Label>
                    <div className="text-lg font-medium">
                      {result.supplier_suggestion}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label className="text-sm font-medium">Recommended Items ({result.items.length})</Label>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {result.items.map((item, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded">
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">
                            {item.medication_name || `Medication ID: ${item.medication_id}`}
                          </div>
                          <div className="text-sm text-muted-foreground truncate">{item.reason}</div>
                        </div>
                        <div className="flex items-center gap-3 min-w-[160px] justify-end">
                          <Badge variant={item.priority === 'high' ? 'destructive' : item.priority === 'medium' ? 'info' : 'secondary'} className="capitalize">
                            {item.priority}
                          </Badge>
                          <div className="text-right">
                            <div className="font-mono font-bold">
                              {item.suggested_quantity.toLocaleString()}
                            </div>
                            <div className="text-xs text-muted-foreground">units</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex gap-2">
                <Button onClick={resetGeneration} variant="outline" className="flex-1">
                  Generate New
                </Button>
                <Button onClick={handleAcceptResult} className="flex-1">
                  <Package className="mr-2 h-4 w-4" />
                  Use Recommendations
                </Button>
              </CardFooter>
            </Card>
          )}

          {error && status === 'error' && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Failed to generate AI recommendations. Please try again.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}