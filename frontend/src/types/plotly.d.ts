declare module 'react-plotly.js' {
  import { Component } from 'react'
  import { PlotData, Layout, Config } from 'plotly.js'

  export interface PlotParams {
    data: PlotData[]
    layout?: Partial<Layout>
    config?: Partial<Config>
    style?: React.CSSProperties
    className?: string
    useResizeHandler?: boolean
    onInitialized?: (
      figure: { data: PlotData[]; layout: Partial<Layout> },
      graphDiv: HTMLElement
    ) => void
    onUpdate?: (
      figure: { data: PlotData[]; layout: Partial<Layout> },
      graphDiv: HTMLElement
    ) => void
    onPurge?: (figure: { data: PlotData[]; layout: Partial<Layout> }, graphDiv: HTMLElement) => void
    onError?: (err: Error) => void
    onRelayout?: (eventData: any) => void
    onRestyle?: (eventData: any) => void
    onHover?: (eventData: any) => void
    onUnhover?: (eventData: any) => void
    onClick?: (eventData: any) => void
    onSelected?: (eventData: any) => void
    onSelecting?: (eventData: any) => void
    onDeselect?: (eventData: any) => void
    onDoubleClick?: (eventData: any) => void
    revision?: number
    onAnimatingFrame?: (eventData: any) => void
    onAnimated?: (eventData: any) => void
    onLegendClick?: (eventData: any) => void
    onLegendDoubleClick?: (eventData: any) => void
  }

  export default class Plot extends Component<PlotParams> {}
}
