import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { 
  ChevronLeft, 
  ChevronRight, 
  Package, 
  Truck, 
  FileText, 
  CheckCircle, 
  Calendar as CalendarIcon,
  Search,
  Plus,
  Minus,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { useInventory, useSuppliers, useCreatePurchaseOrder } from '@/hooks/use-api';
import { AIPOGenerator } from '@/components/ai-po/ai-po-generator';
import { toast } from 'sonner';
import { ProfessionalNotification } from '@/components/animations/success-animation';

interface POLineItem {
  medication_id: number;
  medication_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface POFormData {
  supplier: string;
  delivery_date: Date;
  buyer_name: string;
  notes: string;
  line_items: POLineItem[];
}

const STEPS = [
  { id: 'supplier', title: 'Supplier Selection', description: 'Choose supplier and delivery details' },
  { id: 'medications', title: 'Medications', description: 'Select medications and quantities' },
  { id: 'review', title: 'Review & Submit', description: 'Review and finalize your order' }
];

export function CreatePOWizard({ onComplete }: { onComplete?: (po: any) => void }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<POFormData>({
    supplier: '',
    delivery_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 1 week from now
    buyer_name: '',
    notes: '',
    line_items: []
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [showNotification, setShowNotification] = useState(false);
  
  const { data: suppliers } = useSuppliers();
  const { data: inventory } = useInventory({ search: searchTerm, page_size: 50 });
  const createPOMutation = useCreatePurchaseOrder();

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  const updateFormData = (updates: Partial<POFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
  };

  const addLineItem = (medication: any) => {
    const existing = formData.line_items.find(item => item.medication_id === medication.med_id);
    if (existing) {
      updateFormData({
        line_items: formData.line_items.map(item => 
          item.medication_id === medication.med_id 
            ? { ...item, quantity: item.quantity + 1, total_price: (item.quantity + 1) * item.unit_price }
            : item
        )
      });
    } else {
      const newItem: POLineItem = {
        medication_id: medication.med_id,
        medication_name: medication.name,
        quantity: 1,
        unit_price: medication.current_price || 0,
        total_price: medication.current_price || 0
      };
      updateFormData({
        line_items: [...formData.line_items, newItem]
      });
    }
    toast.success(`Added ${medication.name} to order`);
  };

  const updateLineItem = (medication_id: number, updates: Partial<POLineItem>) => {
    updateFormData({
      line_items: formData.line_items.map(item =>
        item.medication_id === medication_id
          ? { ...item, ...updates, total_price: (updates.quantity || item.quantity) * (updates.unit_price || item.unit_price) }
          : item
      )
    });
  };

  const removeLineItem = (medication_id: number) => {
    updateFormData({
      line_items: formData.line_items.filter(item => item.medication_id !== medication_id)
    });
  };

  const handleAIRecommendations = (result: any) => {
    // Convert AI recommendations to line items
    const aiLineItems: POLineItem[] = result.items.map((item: any) => ({
      medication_id: item.medication_id,
      medication_name: `Medication ${item.medication_id}`, // Would need to look this up
      quantity: item.suggested_quantity,
      unit_price: 10, // Placeholder - would need actual price
      total_price: item.suggested_quantity * 10
    }));

    updateFormData({
      line_items: aiLineItems,
      supplier: result.supplier_suggestion,
      notes: `AI Generated PO: ${result.reasoning}`
    });

    setCurrentStep(2); // Jump to review step
    toast.success('AI recommendations applied!');
  };

  const canGoNext = () => {
    switch (currentStep) {
      case 0: // Supplier step
        return formData.supplier && formData.buyer_name;
      case 1: // Medications step
        return formData.line_items.length > 0;
      case 2: // Review step
        return true;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < STEPS.length - 1 && canGoNext()) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    try {
      const poData = {
        supplier: formData.supplier,
        delivery_date: formData.delivery_date.toISOString().split('T')[0],
        buyer_name: formData.buyer_name,
        notes: formData.notes,
        line_items: formData.line_items.map(item => ({
          medication_id: item.medication_id.toString(),
          quantity: item.quantity,
          unit_price: item.unit_price
        }))
      };

      await createPOMutation.mutateAsync(poData);
      
      // Show professional notification
      setShowNotification(true);
      
      // Hide notification after 3 seconds
      setTimeout(() => {
        setShowNotification(false);
        if (onComplete) {
          onComplete(poData);
        }
      }, 3000);
    } catch (error) {
      toast.error('Failed to create purchase order');
    }
  };

  const totalAmount = formData.line_items.reduce((sum, item) => sum + item.total_price, 0);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Professional Success Notification */}
      <ProfessionalNotification 
        show={showNotification}
        message="Purchase Order Created Successfully!"
        type="success"
        onComplete={() => setShowNotification(false)}
      />
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">Create Purchase Order</h1>
        <p className="text-muted-foreground">
          Follow the steps below to create a new purchase order
        </p>
      </div>

      {/* Progress */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex justify-between text-sm">
              <span>Step {currentStep + 1} of {STEPS.length}</span>
              <span>{Math.round(progress)}% complete</span>
            </div>
            <Progress value={progress} className="w-full" />
            
            <div className="flex justify-between">
              {STEPS.map((step, index) => (
                <div 
                  key={step.id} 
                  className={cn(
                    "flex items-center space-x-2 text-sm",
                    index === currentStep ? "text-primary font-medium" : "text-muted-foreground",
                    index < currentStep ? "text-green-600" : ""
                  )}
                >
                  <div className={cn(
                    "w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs",
                    index === currentStep ? "border-primary bg-primary text-primary-foreground" : 
                    index < currentStep ? "border-green-600 bg-green-600 text-white" : "border-muted-foreground"
                  )}>
                    {index < currentStep ? <CheckCircle className="w-3 h-3" /> : index + 1}
                  </div>
                  <span className="hidden sm:inline">{step.title}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Generator */}
      <div className="flex justify-center">
        <AIPOGenerator onGenerated={handleAIRecommendations} />
      </div>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {currentStep === 0 && <Truck className="h-5 w-5" />}
            {currentStep === 1 && <Package className="h-5 w-5" />}
            {currentStep === 2 && <FileText className="h-5 w-5" />}
            {STEPS[currentStep].title}
          </CardTitle>
          <CardDescription>
            {STEPS[currentStep].description}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Step 1: Supplier Selection */}
          {currentStep === 0 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="supplier">Supplier *</Label>
                  <Select value={formData.supplier} onValueChange={(value) => updateFormData({ supplier: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select supplier" />
                    </SelectTrigger>
                    <SelectContent>
                      {suppliers?.map(supplier => (
                        <SelectItem key={supplier.supplier_id} value={supplier.name}>
                          {supplier.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="buyer">Buyer Name *</Label>
                  <Input
                    id="buyer"
                    value={formData.buyer_name}
                    onChange={(e) => updateFormData({ buyer_name: e.target.value })}
                    placeholder="Enter buyer name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Delivery Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-start text-left font-normal">
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {format(formData.delivery_date, "PPP")}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={formData.delivery_date}
                        onSelect={(date) => date && updateFormData({ delivery_date: date })}
                        disabled={(date) => date < new Date()}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notes">Notes (Optional)</Label>
                  <Textarea
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => updateFormData({ notes: e.target.value })}
                    placeholder="Add any special instructions..."
                    rows={3}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Medication Selection */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search medications..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {/* Selected Items */}
              {formData.line_items.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Selected Items ({formData.line_items.length})</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {formData.line_items.map((item) => (
                        <div key={item.medication_id} className="flex items-center justify-between p-3 border rounded">
                          <div className="flex-1">
                            <div className="font-medium">{item.medication_name}</div>
                            <div className="text-sm text-muted-foreground">
                              ${item.unit_price} per unit
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => updateLineItem(item.medication_id, { quantity: Math.max(1, item.quantity - 1) })}
                              >
                                <Minus className="h-3 w-3" />
                              </Button>
                              <Input
                                type="number"
                                value={item.quantity}
                                onChange={(e) => updateLineItem(item.medication_id, { quantity: parseInt(e.target.value) || 1 })}
                                className="w-20 text-center"
                                min="1"
                              />
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => updateLineItem(item.medication_id, { quantity: item.quantity + 1 })}
                              >
                                <Plus className="h-3 w-3" />
                              </Button>
                            </div>
                            <div className="text-right min-w-20">
                              <div className="font-medium">${item.total_price.toLocaleString()}</div>
                            </div>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => removeLineItem(item.medication_id)}
                            >
                              <Minus className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Available Medications */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Available Medications</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {inventory?.items?.slice(0, 10).map((med) => (
                      <div key={med.med_id} className="flex items-center justify-between p-3 border rounded hover:bg-muted/50">
                        <div className="flex-1">
                          <div className="font-medium">{med.name}</div>
                          <div className="text-sm text-muted-foreground flex items-center gap-4">
                            <span>Stock: {med.current_stock}</span>
                            <span>Reorder: {med.reorder_point}</span>
                            {med.current_stock <= med.reorder_point && (
                              <Badge variant="destructive" className="text-xs">Low Stock</Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-right">
                            <div className="font-medium">${med.current_price}</div>
                            <div className="text-xs text-muted-foreground">per unit</div>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => addLineItem(med)}
                            disabled={formData.line_items.some(item => item.medication_id === med.med_id)}
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Step 3: Review */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  Please review your purchase order details before submitting.
                </AlertDescription>
              </Alert>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Order Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label className="text-sm text-muted-foreground">Supplier</Label>
                      <div className="font-medium">{formData.supplier}</div>
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Buyer</Label>
                      <div className="font-medium">{formData.buyer_name}</div>
                    </div>
                    <div>
                      <Label className="text-sm text-muted-foreground">Delivery Date</Label>
                      <div className="font-medium">{format(formData.delivery_date, "PPP")}</div>
                    </div>
                    {formData.notes && (
                      <div>
                        <Label className="text-sm text-muted-foreground">Notes</Label>
                        <div className="text-sm">{formData.notes}</div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Order Summary</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span>Total Items:</span>
                      <span className="font-medium">{formData.line_items.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Quantity:</span>
                      <span className="font-medium">
                        {formData.line_items.reduce((sum, item) => sum + item.quantity, 0).toLocaleString()}
                      </span>
                    </div>
                    <Separator />
                    <div className="flex justify-between text-lg font-bold">
                      <span>Total Amount:</span>
                      <span>${totalAmount.toLocaleString()}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Line Items Table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Line Items</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {formData.line_items.map((item) => (
                      <div key={item.medication_id} className="flex justify-between items-center p-3 border rounded">
                        <div className="flex-1">
                          <div className="font-medium">{item.medication_name}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.quantity.toLocaleString()} × ${item.unit_price}
                          </div>
                        </div>
                        <div className="font-medium">${item.total_price.toLocaleString()}</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex justify-between">
            <Button 
              variant="outline" 
              onClick={handlePrevious}
              disabled={currentStep === 0}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              Previous
            </Button>

            {currentStep < STEPS.length - 1 ? (
              <Button 
                onClick={handleNext}
                disabled={!canGoNext()}
              >
                Next
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button 
                onClick={handleSubmit}
                disabled={createPOMutation.isPending || formData.line_items.length === 0}
                className="bg-green-600 hover:bg-green-700"
              >
                {createPOMutation.isPending ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Create Purchase Order
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}