import { useState, useCallback, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ArrowLeft,
  ArrowRight,
  Brain,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Sparkles,
  Package,
  Truck,
  DollarSign,
  Calendar,
  RefreshCw,
  Save,
  Send,
  Plus,
  Trash2,
  ShoppingCart,
  Zap,
  FileText,
  User,
} from 'lucide-react'

import { useSuppliers, useMedication, useInventory, useCreatePurchaseOrder } from '@/hooks/use-api'
import type { PurchaseOrderCreate, LineItem } from '@/types/api'

interface POStep {
  id: string
  title: string
  description: string
  completed: boolean
}

interface POGenerationState {
  step: number
  isAiGenerating: boolean
  aiProgress: number
  selectedMedications: string[]
  supplier: string
  deliveryDate: string
  notes: string
  lineItems: LineItem[]
  aiRecommendations?: {
    items: Array<{
      medication_id: string
      medication_name: string
      suggested_quantity: number
      reason: string
      priority: 'high' | 'medium' | 'low'
    }>
    supplier_suggestion?: string
    estimated_total: number
  }
}

const steps: POStep[] = [
  {
    id: 'selection',
    title: 'Item Selection',
    description: 'Choose medications or use AI recommendations',
    completed: false,
  },
  {
    id: 'ai-analysis',
    title: 'AI Analysis',
    description: 'Generate intelligent purchase recommendations',
    completed: false,
  },
  {
    id: 'review',
    title: 'Review & Adjust',
    description: 'Review AI suggestions and make adjustments',
    completed: false,
  },
  {
    id: 'supplier',
    title: 'Supplier & Terms',
    description: 'Select supplier and delivery details',
    completed: false,
  },
  {
    id: 'finalize',
    title: 'Finalize Order',
    description: 'Review final order and submit',
    completed: false,
  },
]

export function CreatePO() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const preselectedMedication = searchParams.get('medication')

  const [state, setState] = useState<POGenerationState>({
    step: 0,
    isAiGenerating: false,
    aiProgress: 0,
    selectedMedications: preselectedMedication ? [preselectedMedication] : [],
    supplier: '',
    deliveryDate: '',
    notes: '',
    lineItems: [],
  })

  const { data: suppliers } = useSuppliers()
  const { data: inventory } = useInventory()
  const { data: medicationDetail } = useMedication(
    preselectedMedication || '',
    !!preselectedMedication
  )
  const createPOMutation = useCreatePurchaseOrder()

  // Auto-advance to AI analysis if medication is preselected
  useEffect(() => {
    if (preselectedMedication && medicationDetail && state.step === 0) {
      setState(prev => ({
        ...prev,
        step: 1,
        selectedMedications: [preselectedMedication],
      }))
    }
  }, [preselectedMedication, medicationDetail, state.step])

  const simulateAIGeneration = useCallback(async () => {
    setState(prev => ({ ...prev, isAiGenerating: true, aiProgress: 0 }))

    // Simulate AI processing steps
    const steps = [
      { progress: 20, message: 'Analyzing inventory levels...' },
      { progress: 40, message: 'Forecasting demand patterns...' },
      { progress: 60, message: 'Optimizing quantities...' },
      { progress: 80, message: 'Selecting best suppliers...' },
      { progress: 100, message: 'Generating recommendations...' },
    ]

    for (const step of steps) {
      await new Promise(resolve => setTimeout(resolve, 800))
      setState(prev => ({ ...prev, aiProgress: step.progress }))
    }

    // Mock AI recommendations based on selected medications
    const mockRecommendations = {
      items: state.selectedMedications.map(medId => {
        const med = inventory?.items?.find(item => item.id === medId)
        return {
          medication_id: medId,
          medication_name: med?.name || `Medication ${medId}`,
          suggested_quantity: Math.max(med?.reorder_point || 100, med?.current_stock || 0) * 2,
          reason:
            med?.current_stock && med?.current_stock <= med?.reorder_point
              ? 'Critical stock level - immediate reorder needed'
              : 'Preventive restocking based on consumption patterns',
          priority: (med?.current_stock && med?.current_stock <= med?.reorder_point * 0.5
            ? 'high'
            : 'medium') as 'high' | 'medium' | 'low',
        }
      }),
      supplier_suggestion: suppliers?.[0]?.name || 'PharmaCorp Supply',
      estimated_total: 0,
    }

    mockRecommendations.estimated_total = mockRecommendations.items.reduce((total, item) => {
      const med = inventory?.items?.find(m => m.id === item.medication_id)
      return total + item.suggested_quantity * (med?.unit_cost || 10)
    }, 0)

    setState(prev => ({
      ...prev,
      isAiGenerating: false,
      aiProgress: 100,
      aiRecommendations: mockRecommendations,
      lineItems: mockRecommendations.items.map(item => ({
        medication_id: item.medication_id,
        quantity: item.suggested_quantity,
        unit_price: inventory?.items?.find(m => m.id === item.medication_id)?.unit_cost || 10,
        total:
          item.suggested_quantity *
          (inventory?.items?.find(m => m.id === item.medication_id)?.unit_cost || 10),
      })),
      supplier: mockRecommendations.supplier_suggestion,
    }))
  }, [state.selectedMedications, inventory, suppliers])

  const handleNext = async () => {
    if (state.step === 1 && !state.aiRecommendations) {
      await simulateAIGeneration()
    }
    setState(prev => ({ ...prev, step: Math.min(prev.step + 1, steps.length - 1) }))
  }

  const handlePrevious = () => {
    setState(prev => ({ ...prev, step: Math.max(prev.step - 1, 0) }))
  }

  const handleSubmit = async () => {
    try {
      const poData: PurchaseOrderCreate = {
        supplier: state.supplier,
        line_items: state.lineItems,
        notes: state.notes,
        delivery_date: state.deliveryDate || undefined,
        ai_generated: true,
      }

      const result = await createPOMutation.mutateAsync(poData)
      navigate(`/purchase-orders/${result.id}`)
    } catch (error) {
      console.error('Failed to create purchase order:', error)
    }
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: number) => {
    setState(prev => ({
      ...prev,
      lineItems: prev.lineItems.map((item, i) =>
        i === index
          ? {
              ...item,
              [field]: value,
              total_price:
                field === 'quantity' || field === 'unit_price'
                  ? (field === 'quantity' ? value : item.quantity) *
                    (field === 'unit_price' ? value : item.unit_price)
                  : item.total_price,
            }
          : item
      ),
    }))
  }

  const currentStep = steps[state.step]
  const progressPercent = ((state.step + 1) / steps.length) * 100

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <Brain className="h-8 w-8 text-blue-600" />
              Create Purchase Order
            </h1>
            <p className="text-muted-foreground">
              AI-powered purchase order generation and optimization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-blue-600 border-blue-200">
            <Sparkles className="h-3 w-3 mr-1" />
            AI Enhanced
          </Badge>
          <Button variant="outline" onClick={() => navigate('/purchase-orders')}>
            <FileText className="h-4 w-4 mr-2" />
            View Orders
          </Button>
        </div>
      </div>

      {/* Progress */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">
                Step {state.step + 1} of {steps.length}
              </span>
              <span className="text-sm text-muted-foreground">
                {Math.round(progressPercent)}% Complete
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />

            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold">{currentStep.title}</h3>
                <p className="text-sm text-muted-foreground">{currentStep.description}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Step Content */}
      {state.step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Select Medications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {preselectedMedication && medicationDetail ? (
              <div className="space-y-4">
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    Pre-selected medication: <strong>{medicationDetail.name}</strong>
                  </AlertDescription>
                </Alert>
                <div className="border rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium">{medicationDetail.name}</h4>
                      <p className="text-sm text-muted-foreground">{medicationDetail.category}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        <span>Current Stock: {medicationDetail.current_stock}</span>
                        <span>Reorder Point: {medicationDetail.reorder_point}</span>
                        <Badge
                          variant={
                            medicationDetail.current_stock <= medicationDetail.reorder_point
                              ? 'destructive'
                              : 'secondary'
                          }
                        >
                          {medicationDetail.current_stock <= medicationDetail.reorder_point
                            ? 'Low Stock'
                            : 'Normal'}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-muted-foreground">
                  Select medications for your purchase order, or let our AI analyze your inventory
                  and recommend items that need restocking.
                </p>

                <div className="grid gap-2">
                  {inventory?.items?.slice(0, 10).map(med => (
                    <div
                      key={med.id || `med-${med.name}`}
                      className="border rounded-lg p-3 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-medium">{med.name}</div>
                          <div className="text-sm text-muted-foreground">
                            Stock: {med.current_stock} | Reorder: {med.reorder_point}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {med.current_stock <= med.reorder_point && (
                            <Badge variant="destructive" size="sm">
                              Low Stock
                            </Badge>
                          )}
                          <Button
                            size="sm"
                            variant={
                              state.selectedMedications.includes(med.id) ? 'default' : 'outline'
                            }
                            onClick={() => {
                              setState(prev => ({
                                ...prev,
                                selectedMedications: prev.selectedMedications.includes(med.id)
                                  ? prev.selectedMedications.filter(id => id !== med.id)
                                  : [...prev.selectedMedications, med.id],
                              }))
                            }}
                          >
                            {state.selectedMedications.includes(med.id) ? 'Remove' : 'Add'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <Button
                  className="w-full"
                  variant="outline"
                  onClick={() =>
                    setState(prev => ({
                      ...prev,
                      selectedMedications:
                        inventory?.items
                          ?.filter(med => med.current_stock <= med.reorder_point)
                          .map(med => med.id) || [],
                    }))
                  }
                >
                  <Zap className="h-4 w-4 mr-2" />
                  Auto-select Low Stock Items
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {state.step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-blue-600" />
              AI Analysis & Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {state.isAiGenerating ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
                  <span className="font-medium">AI is analyzing your inventory...</span>
                </div>
                <Progress value={state.aiProgress} className="h-2" />
                <div className="grid gap-2 text-sm text-muted-foreground">
                  <div>🔍 Analyzing current stock levels and consumption patterns</div>
                  <div>📊 Forecasting future demand using historical data</div>
                  <div>⚡ Optimizing quantities for cost efficiency</div>
                  <div>🏪 Selecting best suppliers based on pricing and lead times</div>
                </div>
              </div>
            ) : state.aiRecommendations ? (
              <div className="space-y-4">
                <Alert>
                  <Sparkles className="h-4 w-4" />
                  <AlertDescription>
                    AI has analyzed your inventory and generated smart recommendations
                  </AlertDescription>
                </Alert>

                <div className="space-y-3">
                  {state.aiRecommendations.items.map((item, index) => (
                    <div key={item.medication_id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{item.medication_name}</h4>
                            <Badge
                              variant={
                                item.priority === 'high'
                                  ? 'destructive'
                                  : item.priority === 'medium'
                                    ? 'secondary'
                                    : 'outline'
                              }
                            >
                              {item.priority} priority
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{item.reason}</p>
                          <div className="text-sm">
                            Recommended quantity:{' '}
                            <strong>{(item.suggested_quantity || 0).toLocaleString()}</strong>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Truck className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-blue-900">Recommended Supplier</h4>
                      <p className="text-sm text-blue-700">
                        {state.aiRecommendations.supplier_suggestion}
                      </p>
                      <p className="text-sm text-blue-600 mt-1">
                        Estimated Total:{' '}
                        <strong>
                          ${(state.aiRecommendations.estimated_total || 0).toLocaleString()}
                        </strong>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <Button onClick={simulateAIGeneration} size="lg" className="w-full">
                <Brain className="h-5 w-5 mr-2" />
                Generate AI Recommendations
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {state.step === 2 && state.lineItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Review & Adjust Quantities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Medication</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Unit Price</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {state.lineItems.map((item, index) => {
                  const medication = inventory?.items?.find(m => m.id === item.medication_id)
                  return (
                    <TableRow key={item.medication_id || `row-${index}`}>
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {medication?.name || `Item ${item.medication_id}`}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {medication?.category}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          value={item.quantity}
                          onChange={e =>
                            updateLineItem(index, 'quantity', parseInt(e.target.value) || 0)
                          }
                          className="w-24"
                          min="1"
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          step="0.01"
                          value={item.unit_price}
                          onChange={e =>
                            updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)
                          }
                          className="w-24"
                          min="0"
                        />
                      </TableCell>
                      <TableCell className="font-mono">${item.total_price.toFixed(2)}</TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setState(prev => ({
                              ...prev,
                              lineItems: prev.lineItems.filter((_, i) => i !== index),
                            }))
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>

            <div className="mt-4 p-4 bg-muted rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium">Total Order Value:</span>
                <span className="text-lg font-bold">
                  ${state.lineItems.reduce((sum, item) => sum + item.total_price, 0).toFixed(2)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {state.step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5" />
              Supplier & Delivery
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="supplier">Supplier</Label>
                <Select
                  value={state.supplier}
                  onValueChange={value => setState(prev => ({ ...prev, supplier: value }))}
                >
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
                <Label htmlFor="delivery-date">Delivery Date (Optional)</Label>
                <Input
                  id="delivery-date"
                  type="date"
                  value={state.deliveryDate}
                  onChange={e => setState(prev => ({ ...prev, deliveryDate: e.target.value }))}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes (Optional)</Label>
              <Textarea
                id="notes"
                placeholder="Add any special instructions or notes for this order..."
                value={state.notes}
                onChange={e => setState(prev => ({ ...prev, notes: e.target.value }))}
                rows={3}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {state.step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Final Review
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Supplier
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium">{state.supplier}</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Calendar className="h-4 w-4" />
                    Delivery
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium">{state.deliveryDate || 'ASAP'}</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    Total Value
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium text-lg">
                    ${state.lineItems.reduce((sum, item) => sum + item.total_price, 0).toFixed(2)}
                  </p>
                </CardContent>
              </Card>
            </div>

            <div>
              <h4 className="font-medium mb-3">Line Items ({state.lineItems.length})</h4>
              <div className="space-y-2">
                {state.lineItems.map((item, index) => {
                  const medication = inventory?.items?.find(m => m.id === item.medication_id)
                  return (
                    <div
                      key={item.medication_id || `item-${index}`}
                      className="flex justify-between items-center p-3 border rounded"
                    >
                      <div>
                        <span className="font-medium">
                          {medication?.name || `Item ${item.medication_id}`}
                        </span>
                        <span className="text-sm text-muted-foreground ml-2">
                          {item.quantity} × ${item.unit_price}
                        </span>
                      </div>
                      <span className="font-mono">${item.total_price.toFixed(2)}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            {state.notes && (
              <div>
                <h4 className="font-medium mb-2">Notes</h4>
                <div className="p-3 bg-muted rounded border">
                  <p className="text-sm">{state.notes}</p>
                </div>
              </div>
            )}

            <Alert>
              <Brain className="h-4 w-4" />
              <AlertDescription>
                This purchase order was generated with AI assistance for optimal inventory
                management.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button variant="outline" onClick={handlePrevious} disabled={state.step === 0}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Previous
        </Button>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/purchase-orders')}>
            <Save className="h-4 w-4 mr-2" />
            Save Draft
          </Button>

          {state.step === steps.length - 1 ? (
            <Button
              onClick={handleSubmit}
              disabled={
                !state.supplier || state.lineItems.length === 0 || createPOMutation.isPending
              }
            >
              {createPOMutation.isPending ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Submit Order
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              disabled={
                (state.step === 0 && state.selectedMedications.length === 0) ||
                (state.step === 1 && state.isAiGenerating)
              }
            >
              Next
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
