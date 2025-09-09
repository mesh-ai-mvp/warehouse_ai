# AI-Powered Purchase Order Generation

This system implements a multi-agent AI system for intelligent purchase order generation using LangGraph and OpenAI.

## Features

### Three Specialized AI Agents

1. **Demand Forecasting Agent**
   - Analyzes 90-day consumption history
   - Uses moving average with trend analysis
   - Considers reorder points and safety stock
   - Generates 3-month demand forecasts

2. **Context Adjustment Agent**
   - Applies seasonal adjustments (flu season, summer, holidays)
   - Category-specific modifications (Chronic, Intermittent, Sporadic)
   - External event considerations
   - Validates against stock constraints

3. **Supplier Optimization Agent**
   - Multi-criteria scoring (price, lead time, status)
   - Intelligent order splitting for risk mitigation
   - Considers supplier reliability and availability
   - Optimizes for cost and delivery time

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure OpenAI API Key

Add your OpenAI API key to the `.env` file:

```env
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Run Database Migrations

```bash
uv run python src/db_migrations.py
```

This creates the necessary AI metadata tables.

### 4. Start the Application

```bash
uv run python src/main.py
```

## Usage

### Generating AI Purchase Orders

1. **Select Medications**
   - Navigate to the main inventory page
   - Use checkboxes to select medications needing reorder
   - Selected count appears in the action bar

2. **Click "Generate PO"**
   - System checks AI configuration
   - Launches multi-agent workflow
   - Shows real-time progress for each agent

3. **Review AI Reasoning**
   - View confidence scores for each agent
   - Expandable reasoning sections show decision points
   - Summary displays total items, cost, and lead time

4. **Proceed to Create PO**
   - Form auto-populates with AI suggestions
   - AI badge indicates generated content
   - Reasoning panel shows agent decisions
   - Manual adjustments allowed before submission

## Configuration

### config/config.ini

Adjust AI behavior through configuration:

```ini
[ai_agents]
model_name = gpt-4o-mini
temperature = 0.7
forecast_horizon_months = 3

[seasonal_adjustments]
# Monthly demand multipliers
january = 1.1
february = 1.15
# ... etc

[supplier_preferences]
enable_order_splitting = true
max_suppliers_per_order = 3
```

## API Endpoints

### Generate AI PO
```
POST /api/purchase-orders/generate-ai
Body: { "medication_ids": [1, 2, 3] }
```

### Check Generation Status
```
GET /api/purchase-orders/ai-status/{session_id}
```

### Get AI Result
```
GET /api/purchase-orders/ai-result/{session_id}
```

### Create PO from AI Result
```
POST /api/purchase-orders/create-from-ai
Body: { "ai_result": {...}, "meta": {...} }
```

## Architecture

### Workflow Orchestration
- LangGraph StateGraph for agent coordination
- Sequential execution: Forecast → Adjust → Optimize
- Shared state management across agents
- Async processing with timeout protection

### Caching
- 5-minute TTL for identical requests
- In-memory cache for performance
- Automatic cache invalidation

### Error Handling
- Graceful fallback to statistical methods if LLM fails
- Timeout protection (30 seconds max)
- Detailed error messages for debugging

## Database Schema

### ai_po_sessions
- Tracks AI generation sessions
- Stores agent outputs and reasoning
- Links to created purchase orders

### ai_po_metadata
- Associates POs with AI sessions
- Records generation metrics
- Maintains confidence scores

## Performance

- Generation time: 5-10 seconds typical
- Supports up to 50 medications per request
- Concurrent request handling
- Rate limiting: 60 requests/minute

## Troubleshooting

### "AI not configured" Error
- Verify OPENAI_API_KEY in .env file
- Check API key validity
- Ensure proper file permissions

### Slow Generation
- Check OpenAI API status
- Reduce number of selected items
- Verify network connectivity

### Missing Forecasts
- Ensure consumption history exists
- Check medication data completeness
- Verify database migrations ran

## Future Enhancements

- Historical PO analysis for learning
- Custom agent training on company data
- Real-time market price integration
- Advanced demand prediction models
- Multi-warehouse coordination