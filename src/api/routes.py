"""
API routes for inventory management
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import sys
import os

# Add parent directory to path to import data_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_loader import DataLoader

# Initialize router
router = APIRouter()

# Global data loader instance
data_loader = DataLoader()


@router.get("/inventory")
async def get_inventory(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query("", description="Search term"),
    category: Optional[str] = Query("", description="Category filter"),
    supplier: Optional[str] = Query("", description="Supplier filter"),
    stock_level: Optional[str] = Query("", description="Stock level filter"),
):
    """Get paginated inventory data with filters"""
    try:
        result = data_loader.get_inventory_data(
            page=page,
            page_size=page_size,
            search=search,
            category=category,
            supplier=supplier,
            stock_level=stock_level,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/medication/{med_id}")
async def get_medication_details(med_id: int):
    """Get detailed information for a specific medication"""
    try:
        details = data_loader.get_medication_details(med_id)
        if not details:
            raise HTTPException(status_code=404, detail="Medication not found")
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
async def get_filter_options():
    """Get available filter options"""
    try:
        return data_loader.get_filter_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
