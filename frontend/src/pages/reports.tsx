import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DateRangePicker } from "@/components/ui/date-range-picker"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { 
  FileText, 
  Download, 
  Plus, 
  Eye, 
  Edit, 
  Trash2, 
  Calendar, 
  Mail,
  Settings,
  BarChart3,
  PieChart,
  LineChart,
  Table,
  Filter,
  Save,
  Play,
  Copy
} from "lucide-react"
import { format } from "date-fns"
// Define our own DateRange type since react-day-picker v9 doesn't export it directly
type DateRange = {
  from: Date | undefined
  to?: Date | undefined
}

interface ReportTemplate {
  id: string
  name: string
  description: string
  type: 'inventory' | 'financial' | 'supplier' | 'consumption' | 'custom'
  lastRun?: string
  frequency: 'manual' | 'daily' | 'weekly' | 'monthly'
  format: 'pdf' | 'excel' | 'csv'
  recipients: string[]
  parameters: Record<string, any>
  chartTypes: string[]
}

interface ReportField {
  id: string
  name: string
  type: 'text' | 'number' | 'date' | 'boolean' | 'select'
  category: 'medication' | 'supplier' | 'order' | 'inventory' | 'financial'
  required: boolean
}

const mockReportTemplates: ReportTemplate[] = [
  {
    id: '1',
    name: 'Inventory Stock Report',
    description: 'Current stock levels and reorder points',
    type: 'inventory',
    lastRun: '2024-01-10T10:30:00Z',
    frequency: 'daily',
    format: 'pdf',
    recipients: ['warehouse@company.com', 'manager@company.com'],
    parameters: { includeExpired: true, lowStockOnly: false },
    chartTypes: ['bar', 'pie']
  },
  {
    id: '2',
    name: 'Monthly Financial Summary',
    description: 'Revenue, expenses, and profitability analysis',
    type: 'financial',
    lastRun: '2024-01-01T00:00:00Z',
    frequency: 'monthly',
    format: 'excel',
    recipients: ['finance@company.com'],
    parameters: { includeForecasts: true },
    chartTypes: ['line', 'area']
  },
  {
    id: '3',
    name: 'Supplier Performance',
    description: 'On-time delivery and quality metrics',
    type: 'supplier',
    frequency: 'weekly',
    format: 'pdf',
    recipients: ['procurement@company.com'],
    parameters: { minOrderThreshold: 1000 },
    chartTypes: ['bar', 'scatter']
  },
  {
    id: '4',
    name: 'Consumption Trends',
    description: 'Historical consumption patterns and forecasts',
    type: 'consumption',
    frequency: 'weekly',
    format: 'excel',
    recipients: ['planning@company.com'],
    parameters: { timeRange: '90d', includeForecasts: true },
    chartTypes: ['line', 'area']
  }
]

const availableFields: ReportField[] = [
  { id: 'med_name', name: 'Medication Name', type: 'text', category: 'medication', required: true },
  { id: 'med_category', name: 'Category', type: 'select', category: 'medication', required: false },
  { id: 'current_stock', name: 'Current Stock', type: 'number', category: 'inventory', required: false },
  { id: 'reorder_point', name: 'Reorder Point', type: 'number', category: 'inventory', required: false },
  { id: 'unit_cost', name: 'Unit Cost', type: 'number', category: 'financial', required: false },
  { id: 'supplier_name', name: 'Supplier Name', type: 'text', category: 'supplier', required: false },
  { id: 'last_order_date', name: 'Last Order Date', type: 'date', category: 'order', required: false },
  { id: 'expiry_date', name: 'Expiry Date', type: 'date', category: 'medication', required: false },
]

export function Reports() {
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null)
  const [isBuilderOpen, setIsBuilderOpen] = useState(false)
  const [selectedFields, setSelectedFields] = useState<string[]>([])
  const [reportName, setReportName] = useState('')
  const [reportDescription, setReportDescription] = useState('')
  const [dateRange, setDateRange] = useState<DateRange | undefined>()
  const [reportFormat, setReportFormat] = useState<'pdf' | 'excel' | 'csv'>('pdf')
  const [reportFrequency, setReportFrequency] = useState<'manual' | 'daily' | 'weekly' | 'monthly'>('manual')
  const [chartTypes, setChartTypes] = useState<string[]>(['bar'])

  const { data: reports, isLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: () => Promise.resolve(mockReportTemplates),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const handleRunReport = async (template: ReportTemplate) => {
    console.log('Running report:', template.name)
    // Implement report generation
  }

  const handleExportReport = async (template: ReportTemplate, format: string) => {
    console.log('Exporting report:', template.name, 'as', format)
    // Implement export functionality
  }

  const handleDeleteReport = (templateId: string) => {
    console.log('Deleting report:', templateId)
    // Implement delete functionality
  }

  const handleSaveCustomReport = () => {
    const newReport: ReportTemplate = {
      id: Date.now().toString(),
      name: reportName,
      description: reportDescription,
      type: 'custom',
      frequency: reportFrequency,
      format: reportFormat,
      recipients: [],
      parameters: { dateRange, selectedFields },
      chartTypes: chartTypes
    }
    console.log('Saving custom report:', newReport)
    setIsBuilderOpen(false)
  }

  const toggleField = (fieldId: string) => {
    setSelectedFields(prev => 
      prev.includes(fieldId) 
        ? prev.filter(id => id !== fieldId)
        : [...prev, fieldId]
    )
  }

  const toggleChartType = (chartType: string) => {
    setChartTypes(prev => 
      prev.includes(chartType) 
        ? prev.filter(type => type !== chartType)
        : [...prev, chartType]
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Reports</h1>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-32 bg-muted rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Reports</h1>
          <p className="text-muted-foreground">Generate and manage custom reports for your pharmaceutical operations</p>
        </div>
        <Dialog open={isBuilderOpen} onOpenChange={setIsBuilderOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Report
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Custom Report Builder</DialogTitle>
              <DialogDescription>
                Build a custom report with the fields and visualizations you need
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* Report Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="report-name">Report Name</Label>
                  <Input
                    id="report-name"
                    value={reportName}
                    onChange={(e) => setReportName(e.target.value)}
                    placeholder="Enter report name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="report-format">Export Format</Label>
                  <Select value={reportFormat} onValueChange={(value: any) => setReportFormat(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="excel">Excel</SelectItem>
                      <SelectItem value="csv">CSV</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="report-description">Description</Label>
                <Input
                  id="report-description"
                  value={reportDescription}
                  onChange={(e) => setReportDescription(e.target.value)}
                  placeholder="Enter report description"
                />
              </div>

              {/* Date Range */}
              <div className="space-y-2">
                <Label>Date Range</Label>
                <DateRangePicker date={dateRange} onDateChange={setDateRange} />
              </div>

              {/* Field Selection */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Data Fields</h3>
                  <Badge variant="secondary">{selectedFields.length} selected</Badge>
                </div>
                
                <ScrollArea className="h-48 border rounded p-4">
                  <div className="space-y-3">
                    {['medication', 'inventory', 'supplier', 'order', 'financial'].map((category) => (
                      <div key={category}>
                        <h4 className="font-medium mb-2 capitalize text-muted-foreground">{category}</h4>
                        <div className="space-y-2 pl-4">
                          {availableFields
                            .filter(field => field.category === category)
                            .map(field => (
                              <div key={field.id} className="flex items-center space-x-2">
                                <Checkbox
                                  id={field.id}
                                  checked={selectedFields.includes(field.id)}
                                  onCheckedChange={() => toggleField(field.id)}
                                />
                                <Label htmlFor={field.id} className="text-sm">
                                  {field.name}
                                  {field.required && <span className="text-red-500 ml-1">*</span>}
                                </Label>
                              </div>
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>

              {/* Chart Types */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Visualizations</h3>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: 'bar', name: 'Bar Chart', icon: BarChart3 },
                    { id: 'line', name: 'Line Chart', icon: LineChart },
                    { id: 'pie', name: 'Pie Chart', icon: PieChart },
                    { id: 'table', name: 'Table', icon: Table },
                  ].map(chart => (
                    <Button
                      key={chart.id}
                      variant={chartTypes.includes(chart.id) ? "default" : "outline"}
                      size="sm"
                      onClick={() => toggleChartType(chart.id)}
                    >
                      <chart.icon className="h-4 w-4 mr-2" />
                      {chart.name}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Schedule */}
              <div className="space-y-2">
                <Label>Schedule</Label>
                <Select value={reportFrequency} onValueChange={(value: any) => setReportFrequency(value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                    <SelectItem value="monthly">Monthly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setIsBuilderOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSaveCustomReport} disabled={!reportName || selectedFields.length === 0}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Report
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Report Templates */}
      <Tabs defaultValue="templates" className="space-y-6">
        <TabsList>
          <TabsTrigger value="templates">Report Templates</TabsTrigger>
          <TabsTrigger value="scheduled">Scheduled Reports</TabsTrigger>
          <TabsTrigger value="history">Report History</TabsTrigger>
        </TabsList>

        <TabsContent value="templates">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {reports?.map((template) => (
              <Card key={template.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{template.name}</CardTitle>
                      <CardDescription>{template.description}</CardDescription>
                    </div>
                    <Badge variant={template.type === 'custom' ? 'secondary' : 'default'}>
                      {template.type}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Format:</span>
                    <Badge variant="outline">{template.format.toUpperCase()}</Badge>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Schedule:</span>
                    <Badge variant="outline" className="capitalize">{template.frequency}</Badge>
                  </div>

                  {template.lastRun && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Last run:</span>
                      <span>{format(new Date(template.lastRun), 'MMM d, yyyy')}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Recipients:</span>
                    <span>{template.recipients.length}</span>
                  </div>

                  <Separator />

                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" onClick={() => handleRunReport(template)}>
                      <Play className="h-3 w-3 mr-1" />
                      Run
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setSelectedTemplate(template)}>
                      <Eye className="h-3 w-3 mr-1" />
                      Preview
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleExportReport(template, template.format)}>
                      <Download className="h-3 w-3 mr-1" />
                      Export
                    </Button>
                    <Button size="sm" variant="outline">
                      <Copy className="h-3 w-3 mr-1" />
                      Clone
                    </Button>
                    {template.type === 'custom' && (
                      <Button size="sm" variant="outline" onClick={() => handleDeleteReport(template.id)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="scheduled">
          <Card>
            <CardHeader>
              <CardTitle>Scheduled Reports</CardTitle>
              <CardDescription>Manage automated report generation and delivery</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {reports?.filter(r => r.frequency !== 'manual').map(report => (
                  <div key={report.id} className="flex items-center justify-between p-4 border rounded">
                    <div>
                      <h4 className="font-semibold">{report.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Runs {report.frequency} • Delivers to {report.recipients.length} recipients
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>{report.frequency}</Badge>
                      <Button size="sm" variant="outline">
                        <Settings className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Report History</CardTitle>
              <CardDescription>View and download previously generated reports</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Mock history data */}
                {[
                  { name: 'Inventory Stock Report', date: '2024-01-10T10:30:00Z', size: '2.4 MB', format: 'PDF' },
                  { name: 'Monthly Financial Summary', date: '2024-01-01T00:00:00Z', size: '1.8 MB', format: 'Excel' },
                  { name: 'Supplier Performance', date: '2024-01-08T09:00:00Z', size: '856 KB', format: 'PDF' },
                  { name: 'Consumption Trends', date: '2024-01-07T15:30:00Z', size: '1.2 MB', format: 'Excel' },
                ].map((historyItem, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded">
                    <div>
                      <h4 className="font-semibold">{historyItem.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Generated on {format(new Date(historyItem.date), 'MMM d, yyyy at h:mm a')} • {historyItem.size}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{historyItem.format}</Badge>
                      <Button size="sm" variant="outline">
                        <Download className="h-4 w-4 mr-1" />
                        Download
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}