import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  FileText,
  Download,
  Edit,
  Calendar,
  Mail,
  Settings,
  Filter,
} from 'lucide-react'
import { format } from 'date-fns'
// Define our own DateRange type since react-day-picker v9 doesn't export it directly
type DateRange = {
  from: Date | undefined
  to?: Date | undefined
}

interface ReportTemplate {
  id: string
  name: string
  description: string
  type: 'inventory' | 'financial' | 'supplier' | 'consumption' | 'warehouse_optimization' | 'custom'
  lastRun?: string
  frequency: 'manual' | 'daily' | 'weekly' | 'monthly'
  format: 'pdf' | 'excel' | 'csv'
  recipients: string[]
  parameters: Record<string, any>
  chartTypes: string[]
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
    chartTypes: ['bar', 'pie'],
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
    chartTypes: ['line', 'area'],
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
    chartTypes: ['bar', 'scatter'],
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
    chartTypes: ['line', 'area'],
  },
  {
    id: '5',
    name: 'Warehouse Chaos Dashboard',
    description: 'AI-powered analysis of warehouse inefficiencies',
    type: 'warehouse_optimization',
    lastRun: '2024-01-10T09:00:00Z',
    frequency: 'daily',
    format: 'pdf',
    recipients: ['warehouse@company.com', 'operations@company.com'],
    parameters: { analysis_type: 'full', include_ai_insights: true },
    chartTypes: ['gauge', 'heatmap', 'bar'],
  },
  {
    id: '6',
    name: 'Placement Efficiency Report',
    description: 'Product placement optimization and consolidation',
    type: 'warehouse_optimization',
    frequency: 'weekly',
    format: 'excel',
    recipients: ['warehouse@company.com'],
    parameters: { focus: 'placement', include_simulation: true },
    chartTypes: ['scatter', 'sankey'],
  },
  {
    id: '7',
    name: 'FIFO Compliance Report',
    description: 'Expiry management and FIFO compliance monitoring',
    type: 'warehouse_optimization',
    lastRun: '2024-01-10T08:00:00Z',
    frequency: 'daily',
    format: 'pdf',
    recipients: ['compliance@company.com', 'quality@company.com'],
    parameters: { focus: 'compliance', alert_threshold_days: 30 },
    chartTypes: ['timeline', 'pie'],
  },
  {
    id: '8',
    name: 'Movement Optimization Report',
    description: 'Picking path and movement pattern optimization',
    type: 'warehouse_optimization',
    frequency: 'weekly',
    format: 'pdf',
    recipients: ['operations@company.com'],
    parameters: { focus: 'movement', include_layout_changes: true },
    chartTypes: ['flow', 'line'],
  },
  {
    id: '9',
    name: 'Comprehensive Warehouse Optimization',
    description: 'Complete AI-driven warehouse optimization with ROI',
    type: 'warehouse_optimization',
    frequency: 'monthly',
    format: 'pdf',
    recipients: ['management@company.com', 'operations@company.com'],
    parameters: {
      analysis_type: 'full',
      include_simulation: true,
      include_ai_insights: true,
      generate_action_plan: true
    },
    chartTypes: ['dashboard', 'waterfall', 'gantt'],
  },
]


export function Reports() {
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplate | null>(null)
  const [dateRange, setDateRange] = useState<DateRange | undefined>()
  const [exportLoading, setExportLoading] = useState(false)
  const [exportingReportName, setExportingReportName] = useState<string>('')

  const { data: reports, isLoading } = useQuery({
    queryKey: ['report-templates'],
    queryFn: async () => {
      const response = await fetch('/api/reports/templates')
      if (!response.ok) {
        throw new Error('Failed to fetch report templates')
      }
      const data = await response.json()
      // Transform backend data to match frontend interface
      return data.map((template: any) => ({
        id: template.id.toString(),
        name: template.name,
        description: template.description,
        type: template.type,
        lastRun: template.last_run,
        frequency: template.frequency,
        format: template.format,
        recipients: template.recipients || [],
        parameters: template.parameters || {},
        chartTypes: template.chart_config?.charts?.map((c: any) => c.type) || []
      }))
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const handleRunReport = async (template: ReportTemplate) => {
    console.log('Running report:', template.name)
    // Implement report generation
  }

  const [exportDialogOpen, setExportDialogOpen] = useState(false)

  const handleExportReport = async (template: ReportTemplate, format: string) => {
    setExportDialogOpen(false)
    if (!format) return // User cancelled

    setExportLoading(true)
    setExportingReportName(template.name)
    try {
      // Call the export API endpoint
      const response = await fetch(`/api/reports/templates/${template.id}/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          format: format,
          parameters: template.parameters || {}
        })
      })

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`)
      }

      // Get the blob from response
      const blob = await response.blob()

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url

      // Set filename based on format
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const filename = `${template.name.replace(/\s+/g, '_')}_${timestamp}.${format}`
      a.download = filename

      // Trigger download
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)

      // Clean up
      window.URL.revokeObjectURL(url)

      console.log(`Successfully exported ${template.name} as ${format}`)
    } catch (error) {
      console.error('Error exporting report:', error)
      alert(`Failed to export report: ${error}`)
    } finally {
      setExportLoading(false)
      setExportingReportName('')
    }
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
      chartTypes: chartTypes,
    }
    console.log('Saving custom report:', newReport)
    setIsBuilderOpen(false)
  }

  const toggleField = (fieldId: string) => {
    setSelectedFields(prev =>
      prev.includes(fieldId) ? prev.filter(id => id !== fieldId) : [...prev, fieldId]
    )
  }

  const toggleChartType = (chartType: string) => {
    setChartTypes(prev =>
      prev.includes(chartType) ? prev.filter(type => type !== chartType) : [...prev, chartType]
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
          <p className="text-muted-foreground">
            Generate and manage custom reports for your pharmaceutical operations
          </p>
        </div>
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
            {reports?.map(template => (
              <Card key={template.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div>
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <CardDescription>{template.description}</CardDescription>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Format:</span>
                    <Badge variant="outline">{template.format.toUpperCase()}</Badge>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Schedule:</span>
                    <Badge variant="outline" className="capitalize">
                      {template.frequency}
                    </Badge>
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

                  <div className="flex justify-end">
                    <Dialog
                      open={exportDialogOpen && selectedTemplate?.id === template.id}
                      onOpenChange={(open) => {
                        setExportDialogOpen(open)
                        if (open) setSelectedTemplate(template)
                      }}
                    >
                      <DialogTrigger asChild>
                        <Button
                          size="sm"
                          variant="outline"
                        >
                          <Download className="h-3 w-3 mr-1" />
                          Export
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                          <DialogTitle>Select Export Format</DialogTitle>
                          <DialogDescription>
                            Choose how you want to export "{template.name}"
                          </DialogDescription>
                        </DialogHeader>
                        <div className="flex gap-3 pt-4">
                          <Button
                            variant="outline"
                            className="flex-1"
                            onClick={() => handleExportReport(template, 'csv')}
                          >
                            CSV (Data Only)
                          </Button>
                          <Button
                            className="flex-1"
                            onClick={() => handleExportReport(template, 'pdf')}
                          >
                            PDF (With AI Insights)
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
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
                {reports
                  ?.filter(r => r.frequency !== 'manual')
                  .map(report => (
                    <div
                      key={report.id}
                      className="flex items-center justify-between p-4 border rounded"
                    >
                      <div>
                        <h4 className="font-semibold">{report.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          Runs {report.frequency} • Delivers to {report.recipients.length}{' '}
                          recipients
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
                  {
                    name: 'Inventory Stock Report',
                    date: '2024-01-10T10:30:00Z',
                    size: '2.4 MB',
                    format: 'PDF',
                  },
                  {
                    name: 'Monthly Financial Summary',
                    date: '2024-01-01T00:00:00Z',
                    size: '1.8 MB',
                    format: 'Excel',
                  },
                  {
                    name: 'Supplier Performance',
                    date: '2024-01-08T09:00:00Z',
                    size: '856 KB',
                    format: 'PDF',
                  },
                  {
                    name: 'Consumption Trends',
                    date: '2024-01-07T15:30:00Z',
                    size: '1.2 MB',
                    format: 'Excel',
                  },
                ].map((historyItem, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded">
                    <div>
                      <h4 className="font-semibold">{historyItem.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        Generated on {format(new Date(historyItem.date), 'MMM d, yyyy at h:mm a')} •{' '}
                        {historyItem.size}
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

      {/* Loading overlay for exports */}
      {exportLoading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 flex flex-col items-center space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="text-lg font-medium">Exporting {exportingReportName}...</p>
            <p className="text-sm text-muted-foreground">This may take up to a minute for AI-enhanced PDFs</p>
          </div>
        </div>
      )}
    </div>
  )
}
