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
import { useAIPOGeneration } from '@/hooks/use-ai-po'
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
    description: 'Choose medications or use smart recommendations',
    completed: false,
  },
  {
    id: 'ai-analysis',
    title: 'Analysis',
    description: 'Generate intelligent purchase recommendations',
    completed: false,
  },
  {
    id: 'review',
    title: 'Review & Adjust',
    description: 'Review suggestions and make adjustments',
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
  const medicationIdsParam = searchParams.get('medication_ids')
  const fromInventory = searchParams.get('from') === 'inventory'
  const withAIResult = searchParams.get('with_ai_result') === 'true'
  
  console.log('🔍 Debug - CreatePO component mounted with search params:')
  console.log('  - preselectedMedication:', preselectedMedication)
  console.log('  - medicationIdsParam:', medicationIdsParam)
  console.log('  - fromInventory:', fromInventory)
  console.log('  - withAIResult:', withAIResult)
  console.log('  - Full URL:', window.location.href)
  console.log('  - Search params string:', searchParams.toString())
  
  // Debug sessionStorage state
  console.log('🔍 Debug - CreatePO: Checking sessionStorage...')
  const sessionStorageCheck = sessionStorage.getItem('aiGenerationResult')
  console.log('🔍 Debug - CreatePO: SessionStorage has aiGenerationResult:', !!sessionStorageCheck)
  if (sessionStorageCheck) {
    console.log('🔍 Debug - CreatePO: SessionStorage data length:', sessionStorageCheck.length)
    try {
      const parsed = JSON.parse(sessionStorageCheck)
      console.log('🔍 Debug - CreatePO: SessionStorage data structure:', {
        hasItems: !!parsed.items,
        itemsCount: parsed.items?.length,
        hasSupplier: !!parsed.supplier_suggestion
      })
    } catch (e) {
      console.error('❌ CreatePO: Failed to parse sessionStorage data:', e)
    }
  }
  
  // Get preselected medication IDs from URL params or session storage
  const getPreselectedMedications = () => {
    console.log('🔍 Debug - URL params:', {
      preselectedMedication,
      medicationIdsParam,
      fromInventory
    })
    
    if (preselectedMedication) {
      console.log('🔍 Debug - Using single preselected medication:', preselectedMedication)
      return [preselectedMedication]
    }
    
    if (medicationIdsParam) {
      const ids = medicationIdsParam.split(',').filter(id => id.trim())
      console.log('🔍 Debug - Using medication IDs from URL:', ids)
      return ids
    }
    
    if (fromInventory) {
      try {
        const stored = sessionStorage.getItem('selectedMedicationIds')
        const parsed = stored ? JSON.parse(stored) : []
        console.log('🔍 Debug - Using medication IDs from session storage:', parsed)
        return parsed
      } catch {
        console.log('🔍 Debug - Failed to parse session storage')
        return []
      }
    }
    
    console.log('🔍 Debug - No preselected medications found')
    return []
  }

  // Load AI results from session storage if available
  const getAIResults = () => {
    console.log('🔍 Debug - getAIResults called, withAIResult:', withAIResult)
    if (withAIResult) {
      try {
        const stored = sessionStorage.getItem('aiGenerationResult')
        console.log('🔍 Debug - Raw sessionStorage data:', stored ? 'DATA_FOUND' : 'NO_DATA')
        if (stored) {
          const result = JSON.parse(stored)
          console.log('🔍 Debug - Parsed AI result from session storage:', result)
          console.log('🔍 Debug - AI result structure validation:', {
            hasItems: !!result.items,
            itemsLength: result.items?.length,
            hasSupplier: !!result.supplier_suggestion,
            hasReasoning: !!result.reasoning,
            itemsArray: result.items
          })
          
          // Validate critical structure
          if (!result.items || !Array.isArray(result.items) || result.items.length === 0) {
            console.error('❌ AI result has invalid items structure:', result)
            return null
          }
          
          // Don't remove immediately - keep for potential re-renders
          // Will be cleaned up after successful PO creation or component unmount
          return result
        } else {
          console.error('🚨 No AI result found in sessionStorage despite withAIResult=true')
          console.log('🔍 Debug - All sessionStorage keys:', Object.keys(sessionStorage))
        }
      } catch (error) {
        console.error('❌ Failed to load AI result from session storage:', error)
      }
    } else {
      console.log('🔍 Debug - withAIResult is false, skipping AI result loading')
    }
    return null
  }

  // Function to initialize state based on current URL params
  const initializeState = useCallback((): POGenerationState => {
    console.log('🔍 Debug - initializeState called')
    const preselectedMeds = getPreselectedMedications()
    const aiResult = getAIResults()
    
    console.log('🔍 Debug - State initialization with preselected:', preselectedMeds)
    console.log('🔍 Debug - State initialization with AI result:', aiResult)
    
    // If we have AI results from inventory, initialize with completed analysis
    if (aiResult && aiResult.items && aiResult.items.length > 0) {
      console.log('🔍 Debug - Initializing state with AI results for step 2')
      console.log('🔍 Debug - AI items:', aiResult.items)
      
      const today = new Date()
      const deliveryDate = new Date(today)
      deliveryDate.setDate(today.getDate() + 10) // 10 days from today
      
      const lineItems = aiResult.items.map((item, index) => {
        const unitPrice = 10 // Default unit price
        const quantity = item.suggested_quantity || 1
        const totalPrice = quantity * unitPrice
        
        console.log(`🔍 Debug - Creating line item ${index + 1}:`, {
          medication_id: item.medication_id,
          quantity,
          unit_price: unitPrice,
          total_price: totalPrice
        })
        
        return {
          medication_id: item.medication_id.toString(),
          quantity,
          unit_price: unitPrice,
          total_price: totalPrice, // Fixed: use total_price instead of total
        }
      })
      
      console.log('🔍 Debug - Final lineItems:', lineItems)
      
      return {
        step: 2, // Skip to review step
        isAiGenerating: false,
        aiProgress: 100,
        selectedMedications: preselectedMeds,
        supplier: aiResult.supplier_suggestion || 'Manager', // Default supplier
        deliveryDate: deliveryDate.toISOString().split('T')[0], // YYYY-MM-DD format
        notes: `AI-generated PO from inventory selection. ${aiResult.reasoning || ''}`.trim(),
        lineItems,
        aiRecommendations: aiResult,
      }
    } else if (aiResult) {
      console.warn('🚨 AI result exists but has no items or empty items array:', aiResult)
    }
    
    return {
      step: preselectedMeds.length > 0 ? 1 : 0, // Skip to AI analysis if meds preselected
      isAiGenerating: false,
      aiProgress: 0,
      selectedMedications: preselectedMeds,
      supplier: '',
      deliveryDate: '',
      notes: '',
      lineItems: [],
    }
  }, [withAIResult, fromInventory])

  // Initialize state with medication IDs from URL
  const [state, setState] = useState<POGenerationState>(initializeState)

  const { data: suppliers } = useSuppliers()
  const { data: inventory } = useInventory()
  const { data: medicationDetail } = useMedication(
    preselectedMedication || '',
    !!preselectedMedication
  )
  const createPOMutation = useCreatePurchaseOrder()
  
  // AI PO Generation hook
  const {
    generatePO: generateAIPO,
    isGenerating: isAIGenerating,
    progress: aiProgress,
    result: aiResult,
    status: aiStatus,
    resetGeneration: resetAI
  } = useAIPOGeneration()

  // Watch for URL parameter changes and re-initialize state
  useEffect(() => {
    console.log('🔍 Debug - URL params changed, checking if re-initialization needed')
    console.log('🔍 Debug - fromInventory:', fromInventory, 'withAIResult:', withAIResult)
    
    // Re-initialize state when navigating from inventory with AI results
    if (fromInventory && withAIResult) {
      console.log('🔍 Debug - Re-initializing state due to inventory navigation with AI results')
      const newState = initializeState()
      setState(newState)
    }
  }, [fromInventory, withAIResult, initializeState])

  // Auto-advance to AI analysis if medications are preselected, and auto-trigger AI if from inventory
  useEffect(() => {
    console.log('🔍 Debug - useEffect triggered')
    console.log('  - state.selectedMedications:', state.selectedMedications)
    console.log('  - state.step:', state.step)
    console.log('  - fromInventory:', fromInventory)
    console.log('  - withAIResult:', withAIResult)
    
    // Auto-advance to step 1 if medications are preselected but no AI results yet
    if (state.selectedMedications.length > 0 && state.step === 0) {
      console.log('🔍 Debug - Auto-advancing to step 1 because we have preselected medications')
      setState(prev => ({
        ...prev,
        step: 1,
      }))
    }
    
    // Auto-trigger AI generation if we're coming from inventory with medications but no results
    if (fromInventory && !withAIResult && state.selectedMedications.length > 0 && state.step === 1 && !state.aiRecommendations && !state.isAiGenerating) {
      console.log('🔍 Debug - Auto-triggering AI generation for inventory selection')
      startAIGeneration()
    }
  }, [state.selectedMedications, state.step, fromInventory, withAIResult, state.aiRecommendations, state.isAiGenerating, startAIGeneration])

  const startAIGeneration = useCallback(async () => {
    console.log('🔍 Debug - startAIGeneration called')
    console.log('  - state.selectedMedications:', state.selectedMedications)
    console.log('  - state.selectedMedications length:', state.selectedMedications?.length)
    
    // Validate that we have medication IDs
    if (!state.selectedMedications || state.selectedMedications.length === 0) {
      console.error('❌ No medications selected for AI generation')
      return
    }
    
    // Reset AI state and trigger real AI generation
    resetAI()
    
    // Convert selected medication IDs to numbers for the API
    const medicationIds = state.selectedMedications.map(id => parseInt(id))
    
    console.log('🔍 Debug - Converted medication IDs for API:', medicationIds)
    
    // Validate converted IDs
    const validIds = medicationIds.filter(id => !isNaN(id) && id > 0)
    if (validIds.length === 0) {
      console.error('❌ No valid medication IDs after conversion')
      return
    }
    
    console.log('🔍 Debug - Sending valid medication_ids to API:', validIds)
    
    // Start real AI generation with selected medications
    generateAIPO({
      days_forecast: 30,
      category_filter: undefined,
      store_ids: undefined,
      medication_ids: validIds,
    })
  }, [state.selectedMedications, generateAIPO, resetAI])

  // Update state when AI generation completes
  useEffect(() => {
    if (aiResult && aiStatus === 'completed') {
      setState(prev => ({
        ...prev,
        isAiGenerating: false,
        aiProgress: 100,
        aiRecommendations: aiResult,
        lineItems: aiResult.items.map(item => ({
          medication_id: item.medication_id.toString(),
          quantity: item.suggested_quantity,
          unit_price: inventory?.items?.find(m => m.id.toString() === item.medication_id.toString())?.unit_cost || 10,
          total:
            item.suggested_quantity *
            (inventory?.items?.find(m => m.id.toString() === item.medication_id.toString())?.unit_cost || 10),
        })),
        supplier: aiResult.supplier_suggestion || suppliers?.[0]?.name || 'PharmaCorp Supply',
      }))
      
      // Clean up session storage after using the data
      if (fromInventory) {
        sessionStorage.removeItem('selectedMedicationIds')
      }
    }
  }, [aiResult, aiStatus, inventory, suppliers, fromInventory])

  // Sync AI generation state with component state
  useEffect(() => {
    setState(prev => ({
      ...prev,
      isAiGenerating: isAIGenerating,
      aiProgress: aiProgress,
    }))
  }, [isAIGenerating, aiProgress])

  // Auto-submit PO when coming from inventory with complete AI results
  useEffect(() => {
    if (fromInventory && withAIResult && state.step === 2 && state.lineItems.length > 0 && !createPOMutation.isPending) {
      console.log('🔍 Debug - Auto-submitting PO from inventory flow')
      // Small delay to show the results briefly before auto-submitting
      const timer = setTimeout(() => {
        handleSubmit()
      }, 2000) // 2 second delay
      
      return () => clearTimeout(timer)
    }
  }, [fromInventory, withAIResult, state.step, state.lineItems.length, createPOMutation.isPending])

  // Cleanup effect - remove sessionStorage on component unmount
  useEffect(() => {
    return () => {
      if (withAIResult && sessionStorage.getItem('aiGenerationResult')) {
        sessionStorage.removeItem('aiGenerationResult')
        console.log('🔍 Debug - Cleaned up AI result from sessionStorage on component unmount')
      }
    }
  }, [withAIResult])

  const handleNext = async () => {
    if (state.step === 1 && !state.aiRecommendations) {
      await startAIGeneration()
    }
    setState(prev => ({ ...prev, step: Math.min(prev.step + 1, steps.length - 1) }))
  }

  const handlePrevious = () => {
    setState(prev => ({ ...prev, step: Math.max(prev.step - 1, 0) }))
  }

  const handleSubmit = async () => {
    try {
      // Use hardcoded defaults for inventory-generated POs
      const today = new Date()
      const defaultDeliveryDate = new Date(today)
      defaultDeliveryDate.setDate(today.getDate() + 10) // 10 days from today
      
      const poData: PurchaseOrderCreate = {
        supplier: state.supplier || 'Manager', // Hardcoded default
        line_items: state.lineItems,
        notes: state.notes || 'AI-generated purchase order from inventory selection',
        delivery_date: state.deliveryDate || defaultDeliveryDate.toISOString().split('T')[0],
        ai_generated: true,
      }

      console.log('🔍 Debug - Creating PO with data:', poData)
      const result = await createPOMutation.mutateAsync(poData)
      
      // Clean up session storage on successful PO creation
      if (withAIResult) {
        sessionStorage.removeItem('aiGenerationResult')
        console.log('🔍 Debug - Cleaned up AI result from sessionStorage after successful PO creation')
      }
      
      // Show success message
      console.log('✅ PO created successfully:', result)
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
              <ShoppingCart className="h-8 w-8 text-blue-600" />
              Create Purchase Order
            </h1>
            <p className="text-muted-foreground">
              Intelligent purchase order generation and optimization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
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
                  Select medications for your purchase order, or analyze your inventory
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
              <Sparkles className="h-5 w-5 text-blue-600" />
              Analysis & Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {state.isAiGenerating ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
                  <span className="font-medium">Processing your inventory...</span>
                </div>
                <Progress value={state.aiProgress} className="h-2" />
                <div className="grid gap-2 text-sm text-muted-foreground">
                  <div>🔍 Reviewing current stock levels and usage patterns</div>
                  <div>📊 Calculating future demand based on historical data</div>
                  <div>⚡ Optimizing quantities for cost efficiency</div>
                  <div>🏪 Selecting optimal suppliers based on pricing and lead times</div>
                </div>
              </div>
            ) : state.aiRecommendations ? (
              <div className="space-y-4">
                <Alert>
                  <Sparkles className="h-4 w-4" />
                  <AlertDescription>
                    Analysis complete - recommendations generated
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
              <Button onClick={startAIGeneration} size="lg" className="w-full">
                <Sparkles className="h-5 w-5 mr-2" />
                Generate Recommendations
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
              {fromInventory && withAIResult && (
                <Badge variant="secondary" className="ml-2">
                  Auto-Generated from Inventory
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Auto-submission indicator */}
            {fromInventory && withAIResult && (
              <Alert className="mb-4">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <AlertDescription>
                  AI analysis complete! Auto-submitting purchase order in a few seconds...
                </AlertDescription>
              </Alert>
            )}
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
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                This purchase order was generated with intelligent optimization for optimal inventory
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
