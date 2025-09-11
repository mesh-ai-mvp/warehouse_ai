"""
Main FastAPI application for inventory management POC
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes import router as api_router, data_loader
from api.analytics import router as analytics_router
from api.reports import router as reports_router
from loguru import logger
import os
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    try:
        data_loader.load_all_data()
        logger.success("Data loaded successfully")
        logger.info(f"Loaded {len(data_loader.medications)} medications")
        logger.info(f"Loaded {len(data_loader.suppliers)} suppliers")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise

    yield

    # Shutdown (if needed)
    logger.info("Application shutdown")


# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

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

# Serve static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def read_index():
    """Serve the main index page"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/medication/{med_id}")
async def medication_detail_page(med_id: int):
    """Serve medication detail page"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "medication-detail.html"))


@app.get("/create-po")
async def create_po_page():
    """Serve create purchase order page"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "create-po.html"))


@app.get("/purchase-orders")
async def purchase_orders_page():
    """Serve purchase orders list page"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "purchase-orders.html"))


@app.get("/purchase-orders/{po_id}")
async def purchase_order_detail_page(po_id: str):
    """Serve purchase order detail page"""
    return FileResponse(os.path.join(TEMPLATES_DIR, "po-detail.html"))


@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon response to prevent 404 errors"""
    from fastapi.responses import Response

    return Response(content="", media_type="image/x-icon")


if __name__ == "__main__":
    logger.info("Starting Inventory Management POC")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("API documentation at: http://localhost:8000/docs")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["./"])
