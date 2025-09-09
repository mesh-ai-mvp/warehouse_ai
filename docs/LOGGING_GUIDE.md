# AI PO Generation Logging Guide

## Overview
Comprehensive logging has been implemented for both backend (Python) and frontend (JavaScript) to help debug issues in the AI-powered Purchase Order generation system.

## Backend Logging

### Configuration
- **Module**: `src/ai_agents/logger.py`
- **Format**: `TIMESTAMP - [module.name] - LEVEL - message`
- **Output**: Console (stdout)
- **Levels**: DEBUG, INFO, WARNING, ERROR

### Logger Instances
Each component has its own logger instance:
- `ai_agents.api_handler` - API request handling
- `ai_agents.workflow` - Workflow orchestration
- `ai_agents.forecast` - Demand forecasting agent
- `ai_agents.adjustment` - Context adjustment agent
- `ai_agents.supplier` - Supplier optimization agent

### Key Log Points

#### API Handler (`api_handler.py`)
- Initialization and data loading
- Request validation
- Medication data gathering
- Workflow execution start/end
- Error handling with stack traces
- Session storage

#### Workflow (`workflow.py`)
- Workflow initialization
- Session creation
- Cache checks
- Agent execution
- Timeout handling
- Result transformation

#### Agents
- Agent execution start
- Processing each medication/item
- LLM interactions
- Calculation details
- Completion status

### Example Backend Logs
```
2025-09-09 09:14:50 - [ai_agents.api_handler] - INFO - Starting AI PO generation for 2 medications: [1, 2]
2025-09-09 09:14:50 - [ai_agents.workflow] - INFO - Starting PO generation for session 97e6d4fe-486e-466f-bbd2
2025-09-09 09:14:50 - [ai_agents.forecast] - INFO - Starting forecast generation for 2 medications
2025-09-09 09:14:51 - [ai_agents.forecast] - DEBUG - Completed forecast for Metformin 500mg: 12800.0 units
```

## Frontend Logging

### Configuration
- **Module**: `src/static/js/ai-po-generator.js`
- **Format**: `[AIPOGenerator] message`
- **Output**: Browser console
- **Levels**: log, warn, error

### Key Log Points

#### Initialization
```javascript
console.log('[AIPOGenerator] Initialized');
```

#### PO Generation Flow
- Medication selection validation
- API configuration check
- Request payload details
- Response status and data
- Progress updates
- Error handling with stack traces

#### UI Updates
- Modal show/hide
- Progress bar updates
- Current agent tracking
- Result display
- Toast notifications

### Example Frontend Logs
```javascript
[AIPOGenerator] Starting generation for medications: [1, 2, 3]
[AIPOGenerator] Processing 3 medications
[AIPOGenerator] Checking AI configuration...
[AIPOGenerator] Config status: {configured: true, model: "gpt-4o-mini"}
[AIPOGenerator] Sending request to backend API...
[AIPOGenerator] Request payload: {medication_ids: [1, 2, 3]}
[AIPOGenerator] Response status: 200
[AIPOGenerator] Generation result: {session_id: "abc123", status: "completed", po_items: [...]}
[AIPOGenerator] Generated 3 PO items
[AIPOGenerator] Generation process ended
```

## Debugging Tips

### 1. Enable Browser Console
- Chrome/Edge: F12 → Console tab
- Firefox: Ctrl+Shift+K
- Safari: Cmd+Option+C

### 2. Filter Logs
In browser console, filter by `[AIPOGenerator]` to see only AI-related logs.

### 3. Backend Log Levels
To see DEBUG logs, ensure console handler level is set to DEBUG in `logger.py`.

### 4. Common Issues to Look For

#### Backend
- "OpenAI API key not configured" - Missing API key
- "No valid medications found" - Data loading issue
- "Workflow timeout" - Processing took too long
- "Type is not msgpack serializable" - Numpy serialization issue

#### Frontend
- "No medications selected" - User didn't select items
- "AI not configured" - Backend API key issue
- "Generation already in progress" - Duplicate request
- Network errors - API connectivity issues

### 5. Correlation
Match frontend session IDs with backend logs for end-to-end tracing:
```
Frontend: [AIPOGenerator] Session ID: abc123
Backend: [ai_agents.workflow] - INFO - Starting PO generation for session abc123
```

## Testing Logging

Run a test generation and check both console outputs:

1. **Browser Console**: Open developer tools before clicking "Generate PO"
2. **Backend Console**: Watch the terminal where the FastAPI server is running
3. **Correlation**: Note the session ID to track the request through the system

## Log Retention

Currently, logs are output to console only. For production:
- Consider adding file logging with rotation
- Implement centralized logging (ELK stack, CloudWatch, etc.)
- Add request correlation IDs
- Implement log levels per environment