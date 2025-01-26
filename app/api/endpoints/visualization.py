from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from datetime import datetime
from visualization.efficient_frontier import EfficientFrontier
from visualization.portfolio_tree import PortfolioTree
from app.core.config import settings

router = APIRouter()

@router.get("/efficient-frontier")
async def get_efficient_frontier(fund_pool: List[str]):
    """生成有效前沿图"""
    try:
        ef = EfficientFrontier()
        image_path = f"{settings.STATIC_DIR}/efficient_frontier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ef.plot_efficient_frontier(fund_pool, save_path=image_path)
        return {"status": "success", "data": {"image_url": f"{settings.STATIC_URL}/{image_path}"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio-tree")
async def get_portfolio_tree(portfolio: Dict[str, float]):
    """生成组合树状图"""
    try:
        pt = PortfolioTree()
        image_path = f"{settings.STATIC_DIR}/portfolio_tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pt.plot_portfolio_tree(portfolio, save_path=image_path)
        return {"status": "success", "data": {"image_url": f"{settings.STATIC_URL}/{image_path}"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 