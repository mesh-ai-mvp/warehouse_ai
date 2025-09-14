"""
Main FastAPI application for inventory management POC
"""

import os
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from api.analytics import router as analytics_router
from api.reports import router as reports_router
from api.routes import data_loader
from api.routes import router as api_router
from api.warehouse_routes import router as warehouse_router
from api.warehouse_routes_optimized import router as warehouse_optimized_router
from api.websocket_routes import router as websocket_router


def build_frontend():
    """Build the React frontend (for development only)"""
    # In production/Docker, frontend is pre-built during image build
    frontend_dir = os.path.join(os.path.dirname(BASE_DIR), "frontend")
    if not os.path.exists(frontend_dir):
        logger.warning(f"Frontend directory not found: {frontend_dir}")
        logger.info("Assuming frontend is pre-built (production mode)")
        return True

    logger.info("Building React frontend for development...")
    try:
        # Build the frontend
        result = subprocess.run(
            ["npm", "run", "build"], cwd=frontend_dir, capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error(f"Frontend build failed: {result.stderr}")
            return False
        logger.success("Frontend build completed successfully")
        return True
    except Exception as e:
        logger.warning(f"Failed to build frontend (development mode): {e}")
        logger.info("Assuming frontend is pre-built (production mode)")
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    try:
        # Build frontend first (development mode)
        build_frontend()

        data_loader.load_all_data()
        logger.success("Data loaded successfully")
        logger.info(f"Loaded {len(data_loader.medications)} medications")
        logger.info(f"Loaded {len(data_loader.suppliers)} suppliers")

        # Initialize report templates
        data_loader.initialize_report_templates()
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise

    yield

    # Shutdown (if needed)
    logger.info("Application shutdown")


# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Inventory Management POC",
    description="Warehouse inventory management system",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount API routes
app.include_router(api_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
# Prefer optimized warehouse routes when overlapping paths exist
app.include_router(warehouse_optimized_router)  # Optimized warehouse routes
app.include_router(warehouse_router)
app.include_router(websocket_router)  # WebSocket routes

# Serve React build files
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(FRONTEND_DIST_DIR, "assets")),
    name="assets",
)


@app.get("/favicon.ico")
async def favicon():
    """Serve favicon from React build"""
    favicon_path = os.path.join(FRONTEND_DIST_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    from fastapi.responses import Response

    return Response(content="", media_type="image/x-icon")


# Catch-all route to serve React app for client-side routing
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve the React app for all non-API routes"""
    # If the request is for a file that exists, serve it directly
    if full_path and not full_path.startswith("api"):
        file_path = os.path.join(FRONTEND_DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

    # Otherwise, serve the React app's index.html for client-side routing
    index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            content="<h1>Frontend not built</h1><p>Please build the frontend first: cd frontend && npm run build</p>",
            status_code=503,
        )


if __name__ == "__main__":
    logger.info("Starting Inventory Management POC")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("API documentation at: http://localhost:8000/docs")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["./"])
