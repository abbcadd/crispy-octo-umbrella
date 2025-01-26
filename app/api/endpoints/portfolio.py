from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
from strategy.portfolio_opt import PortfolioOptimizer
from strategy.risk_model import RiskModel
from app.api import deps

router = APIRouter()

class OptimizationRequest(BaseModel):
    fund_pool: List[str]
    method: str = 'mean_variance'
    risk_aversion: float = 2.0
    constraints: Optional[Dict] = None

class PortfolioAnalysisRequest(BaseModel):
    portfolio: Dict[str, float]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@router.post("/optimize")
async def optimize_portfolio(
    request: OptimizationRequest,
    optimizer: PortfolioOptimizer = Depends(deps.get_optimizer)
):
    """优化投资组合"""
    try:
        result = optimizer.optimize(
            fund_codes=request.fund_pool,
            method=request.method,
            risk_aversion=request.risk_aversion,
            constraints=request.constraints
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_portfolio(
    request: PortfolioAnalysisRequest,
    risk_model: RiskModel = Depends(deps.get_risk_model),
    data_api = Depends(deps.get_data_api)
):
    """分析投资组合"""
    try:
        risk_metrics = risk_model.calculate_risk_metrics(request.portfolio)
        market_status = data_api.get_market_status()
        
        performance = {}
        for code, weight in request.portfolio.items():
            fund_perf = data_api.get_fund_performance(code)
            for metric, value in fund_perf.items():
                performance[metric] = performance.get(metric, 0) + value * weight
                
        return {
            "status": "success",
            "data": {
                "risk_metrics": risk_metrics,
                "market_status": market_status,
                "performance": performance
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 