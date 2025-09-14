"""
PDF Report Generator Service
Generates professional PDF reports with AI insights using ReportLab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    KeepTogether,
    Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import Dict, List, Any, Optional
import io
from loguru import logger


class NumberedCanvas(canvas.Canvas):
    """Canvas for adding page numbers"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page numbers to each page"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Draw page numbers"""
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        self.drawRightString(
            letter[0] - 0.5 * inch,
            0.5 * inch,
            f"Page {self._pageNumber} of {page_count}",
        )
        # Add generation timestamp
        self.drawString(
            0.5 * inch,
            0.5 * inch,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )


class PDFReportGenerator:
    """Generates professional PDF reports with AI insights"""

    def __init__(self):
        """Initialize PDF generator with styles"""
        self.styles = self._create_styles()
        logger.info("PDFReportGenerator initialized")

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles"""
        styles = getSampleStyleSheet()

        # Custom title style
        styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=styles["Title"],
                fontSize=24,
                textColor=HexColor("#1a1a1a"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        # Custom heading styles
        styles.add(
            ParagraphStyle(
                name="CustomHeading1",
                parent=styles["Heading1"],
                fontSize=18,
                textColor=HexColor("#2c3e50"),
                spaceAfter=20,
                spaceBefore=20,
                leftIndent=0,
            )
        )

        styles.add(
            ParagraphStyle(
                name="CustomHeading2",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=HexColor("#34495e"),
                spaceAfter=12,
                spaceBefore=12,
                leftIndent=0,
            )
        )

        # Executive summary style
        styles.add(
            ParagraphStyle(
                name="ExecutiveSummary",
                parent=styles["Normal"],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceBefore=6,
                spaceAfter=12,
                leftIndent=20,
                rightIndent=20,
                textColor=HexColor("#2c3e50"),
            )
        )

        # Insight style
        styles.add(
            ParagraphStyle(
                name="Insight",
                parent=styles["Normal"],
                fontSize=10,
                bulletIndent=20,
                leftIndent=35,
                spaceAfter=6,
            )
        )

        # Recommendation style
        styles.add(
            ParagraphStyle(
                name="Recommendation",
                parent=styles["Normal"],
                fontSize=10,
                bulletIndent=20,
                leftIndent=35,
                spaceAfter=8,
                textColor=HexColor("#27ae60"),
            )
        )

        # Warning style
        styles.add(
            ParagraphStyle(
                name="Warning",
                parent=styles["Normal"],
                fontSize=10,
                bulletIndent=20,
                leftIndent=35,
                spaceAfter=6,
                textColor=HexColor("#e74c3c"),
            )
        )

        # Footer style
        styles.add(
            ParagraphStyle(
                name="Footer",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            )
        )

        return styles

    def generate_report_pdf(
        self,
        template: Dict[str, Any],
        data: List[Dict[str, Any]],
        ai_insights: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate PDF report with AI insights

        Args:
            template: Report template configuration
            data: Report data
            ai_insights: AI-generated insights (optional)

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build story (content)
        story = []

        # Add cover page
        story.extend(self._create_cover_page(template))
        story.append(PageBreak())

        # Add executive summary if AI insights available
        if ai_insights and ai_insights.get("executive_summary"):
            story.extend(self._create_executive_summary(ai_insights))
            story.append(PageBreak())

        # Add data section
        story.extend(self._create_data_section(template, data))

        # Add AI insights section if available
        if ai_insights:
            story.append(PageBreak())
            story.extend(self._create_ai_insights_section(ai_insights))

        # Build PDF
        doc.build(story, canvasmaker=NumberedCanvas)

        # Get PDF content
        pdf = buffer.getvalue()
        buffer.close()

        logger.info(f"Generated PDF report: {template.get('name', 'Report')}")
        return pdf

    def _create_cover_page(self, template: Dict[str, Any]) -> List:
        """Create cover page elements"""
        elements = []

        # Add spacing
        elements.append(Spacer(1, 2 * inch))

        # Title
        title = template.get("name", "Report")
        elements.append(Paragraph(title, self.styles["CustomTitle"]))

        # Description
        if template.get("description"):
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(template["description"], self.styles["BodyText"]))

        # Report metadata
        elements.append(Spacer(1, 1 * inch))

        # Create styles for metadata table
        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=HexColor("#7f8c8d"),
            alignment=TA_RIGHT,
        )

        meta_value_style = ParagraphStyle(
            "MetaValue",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=HexColor("#2c3e50"),
            alignment=TA_LEFT,
        )

        metadata = [
            [Paragraph("Report Type:", meta_label_style), Paragraph(template.get("type", "General").title(), meta_value_style)],
            [Paragraph("Generated:", meta_label_style), Paragraph(datetime.now().strftime("%B %d, %Y at %I:%M %p"), meta_value_style)],
            [Paragraph("Format:", meta_label_style), Paragraph("PDF with AI Insights", meta_value_style)],
            [Paragraph("Frequency:", meta_label_style), Paragraph(template.get("frequency", "On-demand").title(), meta_value_style)],
        ]

        metadata_table = Table(metadata, colWidths=[2 * inch, 3 * inch])
        metadata_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements.append(metadata_table)

        return elements

    def _create_executive_summary(self, ai_insights: Dict[str, Any]) -> List:
        """Create executive summary section"""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles["CustomHeading1"]))
        elements.append(Spacer(1, 12))

        # Add executive summary text
        summary = ai_insights.get("executive_summary", "")
        if summary:
            # Split into paragraphs if needed
            paragraphs = summary.split("\n\n") if "\n\n" in summary else [summary]
            for para in paragraphs:
                if para.strip():
                    elements.append(
                        Paragraph(para.strip(), self.styles["ExecutiveSummary"])
                    )
                    elements.append(Spacer(1, 6))

        # Add key metrics if available
        if ai_insights.get("confidence_score"):
            elements.append(Spacer(1, 12))
            confidence = ai_insights["confidence_score"]
            confidence_color = (
                HexColor("#27ae60")
                if confidence > 0.7
                else HexColor("#f39c12")
                if confidence > 0.4
                else HexColor("#e74c3c")
            )

            confidence_text = f"<font color='{confidence_color}'>Analysis Confidence: {confidence:.0%}</font>"
            elements.append(Paragraph(confidence_text, self.styles["BodyText"]))

        return elements

    def _create_data_section(
        self, template: Dict[str, Any], data: List[Dict[str, Any]]
    ) -> List:
        """Create data section with tables"""
        elements = []

        elements.append(Paragraph("Report Data", self.styles["CustomHeading1"]))
        elements.append(Spacer(1, 12))

        if not data:
            elements.append(
                Paragraph("No data available for this report.", self.styles["BodyText"])
            )
            return elements

        # Create data table
        table_data = self._prepare_table_data(
            data[:50]
        )  # Limit to first 50 rows for PDF

        if table_data:
            # Create table
            col_widths = self._calculate_column_widths(table_data[0])
            data_table = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Apply table style
            data_table.setStyle(self._get_table_style())

            elements.append(data_table)

            # Add note if data was truncated
            if len(data) > 50:
                elements.append(Spacer(1, 12))
                elements.append(
                    Paragraph(
                        f"<i>Note: Showing first 50 of {len(data)} total records</i>",
                        self.styles["BodyText"],
                    )
                )

        return elements

    def _create_ai_insights_section(self, ai_insights: Dict[str, Any]) -> List:
        """Create AI insights section"""
        elements = []

        elements.append(
            Paragraph("AI Insights & Analysis", self.styles["CustomHeading1"])
        )
        elements.append(Spacer(1, 12))

        # Key Insights
        if ai_insights.get("insights"):
            elements.append(Paragraph("Key Insights", self.styles["CustomHeading2"]))
            for insight in ai_insights["insights"][:10]:  # Limit to 10 insights
                elements.append(Paragraph(f"• {insight}", self.styles["Insight"]))
            elements.append(Spacer(1, 12))

        # Patterns & Trends
        if ai_insights.get("patterns"):
            elements.append(
                Paragraph("Identified Patterns", self.styles["CustomHeading2"])
            )
            for pattern in ai_insights["patterns"][:8]:
                if isinstance(pattern, dict):
                    desc = pattern.get("description", "Pattern identified")
                    conf = pattern.get("confidence", "medium")
                    elements.append(
                        Paragraph(
                            f"• {desc} <i>(Confidence: {conf})</i>",
                            self.styles["Insight"],
                        )
                    )
                else:
                    elements.append(Paragraph(f"• {pattern}", self.styles["Insight"]))
            elements.append(Spacer(1, 12))

        # Anomalies
        if ai_insights.get("anomalies"):
            elements.append(
                Paragraph("Anomalies Detected", self.styles["CustomHeading2"])
            )
            for anomaly in ai_insights["anomalies"][:5]:
                if isinstance(anomaly, dict):
                    desc = anomaly.get("description", "Anomaly detected")
                    severity = anomaly.get("severity", "medium")
                    color = "#e74c3c" if severity in ["critical", "high"] else "#f39c12"
                    elements.append(
                        Paragraph(
                            f"<font color='{color}'>⚠ {desc} - Severity: {severity.upper()}</font>",
                            self.styles["Warning"],
                        )
                    )
                else:
                    elements.append(Paragraph(f"⚠ {anomaly}", self.styles["Warning"]))
            elements.append(Spacer(1, 12))

        # Predictions
        if ai_insights.get("predictions"):
            elements.append(
                Paragraph("Predictive Analysis", self.styles["CustomHeading2"])
            )
            for pred in ai_insights["predictions"][:6]:
                if isinstance(pred, dict):
                    desc = pred.get("prediction", "Prediction")
                    timeframe = pred.get("timeframe", "Future")
                    confidence = pred.get("confidence", "medium")
                    elements.append(
                        Paragraph(
                            f"📈 {desc} <i>({timeframe}, Confidence: {confidence})</i>",
                            self.styles["Insight"],
                        )
                    )
                else:
                    elements.append(Paragraph(f"📈 {pred}", self.styles["Insight"]))
            elements.append(Spacer(1, 12))

        # Risk Assessment
        if ai_insights.get("risk_assessment"):
            risk = ai_insights["risk_assessment"]
            elements.append(Paragraph("Risk Assessment", self.styles["CustomHeading2"]))

            risk_level = risk.get("overall_risk_level", "medium")
            risk_color = (
                "#e74c3c"
                if risk_level in ["critical", "high"]
                else "#f39c12"
                if risk_level == "medium"
                else "#27ae60"
            )

            elements.append(
                Paragraph(
                    f"<font color='{risk_color}'>Overall Risk Level: {risk_level.upper()}</font>",
                    self.styles["BodyText"],
                )
            )

            if risk.get("risk_factors"):
                elements.append(Spacer(1, 6))
                for factor in risk["risk_factors"][:5]:
                    if isinstance(factor, dict):
                        desc = factor.get("factor", "Risk factor")
                        severity = factor.get("severity", "medium")
                        elements.append(
                            Paragraph(
                                f"• {desc} (Severity: {severity})",
                                self.styles["Insight"],
                            )
                        )
            elements.append(Spacer(1, 12))

        # Recommendations
        if ai_insights.get("recommendations"):
            elements.append(Paragraph("Recommendations", self.styles["CustomHeading2"]))
            for i, rec in enumerate(ai_insights["recommendations"][:10], 1):
                elements.append(Paragraph(f"{i}. {rec}", self.styles["Recommendation"]))
            elements.append(Spacer(1, 12))

        # Action Items
        if ai_insights.get("action_items"):
            elements.append(Paragraph("Action Items", self.styles["CustomHeading2"]))

            # Create style for action table cells
            action_wrap_style = ParagraphStyle(
                "ActionWrapStyle",
                parent=self.styles["Normal"],
                fontSize=9,
                leading=11,
                wordWrap=1,
                splitLongWords=1,
            )

            # Headers wrapped in Paragraphs
            action_data = [[
                Paragraph("Priority", action_wrap_style),
                Paragraph("Action", action_wrap_style),
                Paragraph("Owner", action_wrap_style),
                Paragraph("Timeline", action_wrap_style)
            ]]

            for item in ai_insights["action_items"][:8]:
                if isinstance(item, dict):
                    # Wrap all cells in Paragraphs for proper text wrapping
                    action_data.append(
                        [
                            Paragraph(item.get("priority", "Medium").upper(), action_wrap_style),
                            Paragraph(item.get("action", "Action required"), action_wrap_style),
                            Paragraph(item.get("owner", "TBD"), action_wrap_style),
                            Paragraph(item.get("timeline", "TBD"), action_wrap_style),
                        ]
                    )

            if len(action_data) > 1:
                action_table = Table(
                    action_data, colWidths=[1 * inch, 3 * inch, 1.5 * inch, 1 * inch]
                )
                action_table.setStyle(self._get_action_table_style())
                elements.append(action_table)

        # Quick Wins
        if ai_insights.get("quick_wins"):
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Quick Wins", self.styles["CustomHeading2"]))
            for win in ai_insights["quick_wins"][:5]:
                if isinstance(win, dict):
                    action = win.get("action", "Quick action")
                    impact = win.get("impact", "Positive impact")
                    elements.append(
                        Paragraph(
                            f"✓ {action} - <i>{impact}</i>", self.styles["Insight"]
                        )
                    )

        return elements

    def _prepare_table_data(self, data: List[Dict[str, Any]]) -> List[List]:
        """Prepare data for table format"""
        if not data:
            return []

        # Get headers from first row
        headers = list(data[0].keys())

        # Create style for wrapping text with proper word wrapping
        wrap_style = ParagraphStyle(
            "WrapStyle",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=11,
            wordWrap=1,  # Enable word wrapping
            splitLongWords=1,  # Split long words if necessary
        )

        # Create header style with bold and proper wrapping
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=wrap_style,
            fontName="Helvetica-Bold",
            fontSize=10,
            alignment=TA_CENTER,
        )

        # Format headers and wrap in Paragraphs
        formatted_headers = [
            Paragraph(h.replace("_", " ").title(), header_style) for h in headers
        ]

        # Create table data
        table_data = [formatted_headers]

        # Add data rows - wrap ALL cells in Paragraph objects
        for row in data:
            row_data = []
            for header in headers:
                value = row.get(header, "")

                # Format different types
                if isinstance(value, float):
                    # Format numbers
                    if (
                        "price" in header.lower()
                        or "cost" in header.lower()
                        or "amount" in header.lower()
                    ):
                        value = f"${value:,.2f}"
                    elif "percent" in header.lower() or "rate" in header.lower():
                        value = f"{value:.1f}%"
                    else:
                        value = f"{value:,.2f}"
                elif isinstance(value, int):
                    value = f"{value:,}"
                elif value is None:
                    value = "-"
                else:
                    value = str(value)  # Don't truncate, let wrapping handle it

                # ALWAYS wrap in Paragraph for consistent word wrapping
                # This ensures proper text flow and prevents overflow
                row_data.append(Paragraph(str(value), wrap_style))

            table_data.append(row_data)

        return table_data

    def _calculate_column_widths(self, headers: List) -> List[float]:
        """Calculate column widths based on header content"""
        num_cols = len(headers)
        available_width = 6.5 * inch  # Total available width

        # Extract text from Paragraph objects if needed
        header_texts = []
        for h in headers:
            if hasattr(h, 'text'):
                # It's a Paragraph object
                header_texts.append(h.text)
            else:
                header_texts.append(str(h))

        # Calculate relative widths based on header length
        # with minimum and maximum constraints
        min_width = 0.8 * inch
        max_width = 2.0 * inch

        # Calculate initial widths based on header text length
        initial_widths = []
        for text in header_texts:
            # Estimate width based on character count
            # Approximate 7 points per character at 9pt font
            estimated_width = len(text) * 7
            # Convert points to inches (72 points = 1 inch)
            width_inches = (estimated_width / 72.0) * inch
            # Apply min/max constraints
            width = max(min_width, min(width_inches * 1.5, max_width))
            initial_widths.append(width)

        # Scale to fit available width
        total_width = sum(initial_widths)
        if total_width > available_width:
            # Scale down proportionally
            scale_factor = available_width / total_width
            return [w * scale_factor for w in initial_widths]
        elif total_width < available_width * 0.9:  # If using less than 90% of space
            # Scale up proportionally, but not too much
            scale_factor = min(1.3, available_width / total_width)
            return [w * scale_factor for w in initial_widths]
        else:
            return initial_widths

    def _get_table_style(self) -> TableStyle:
        """Get standard table style"""
        return TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Data rows
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Alternating row colors
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, HexColor("#ecf0f1")],
                ),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LINEBELOW", (0, 0), (-1, 0), 2, HexColor("#2c3e50")),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )

    def _get_action_table_style(self) -> TableStyle:
        """Get action items table style"""
        return TableStyle(
            [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#27ae60")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Data rows
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),  # Priority column
                ("ALIGN", (1, 1), (1, -1), "LEFT"),  # Action column
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),  # Owner and Timeline
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LINEBELOW", (0, 0), (-1, 0), 2, HexColor("#27ae60")),
                # Padding
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )

    def generate_analytics_pdf(
        self,
        data: Dict[str, Any],
        ai_insights: Optional[Dict[str, Any]] = None,
        time_range: str = "30d",
    ) -> bytes:
        """Generate PDF for analytics dashboard export"""

        # Create a template for analytics
        template = {
            "name": "Analytics Dashboard Report",
            "description": f"Comprehensive analytics for {time_range} period",
            "type": "analytics_dashboard",
            "frequency": "on-demand",
        }

        # Flatten analytics data for table format
        flattened_data = []

        # Add KPIs as data
        if data.get("kpis"):
            kpis = data["kpis"].get("kpis", {})
            flattened_data.append(
                {
                    "metric": "Key Performance Indicators",
                    "total_revenue": kpis.get("totalRevenue", 0),
                    "total_orders": kpis.get("totalOrders", 0),
                    "avg_order_value": kpis.get("avgOrderValue", 0),
                    "low_stock_items": kpis.get("lowStockItems", 0),
                    "on_time_delivery": kpis.get("onTimeDeliveries", 0),
                }
            )

        # Add other metrics as needed
        # This is simplified - you can expand based on your needs

        return self.generate_report_pdf(template, flattened_data, ai_insights)
