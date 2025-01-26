from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from fastapi.staticfiles import StaticFiles

from data_module import DataAPI
from strategy.portfolio_opt import PortfolioOptimizer
from strategy.risk_model import RiskModel
from backtest.simulator import BacktestSimulator
from visualization.efficient_frontier import EfficientFrontier
from visualization.portfolio_tree import PortfolioTree

# 创建FastAPI应用
app = FastAPI(
    title="基金组合优化系统",
    description="基于量化方法的基金投资组合优化系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 在 FastAPI 应用初始化后添加以下代码
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化组件
data_api = DataAPI()
optimizer = PortfolioOptimizer()
risk_model = RiskModel()
simulator = BacktestSimulator()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 请求模型定义
class OptimizationRequest(BaseModel):
    fund_pool: List[str]
    method: str = 'mean_variance'
    risk_aversion: float = 2.0
    constraints: Optional[Dict] = None

class BacktestRequest(BaseModel):
    fund_pool: List[str]
    start_date: str
    end_date: str
    strategy_params: Optional[Dict] = None

class PortfolioAnalysisRequest(BaseModel):
    portfolio: Dict[str, float]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@app.get("/")
async def root():
    """API根路径"""
    return {"message": "基金组合优化系统API"}

@app.get("/funds")
async def get_fund_list(fund_type: Optional[str] = None):
    """获取基金列表"""
    try:
        funds = data_api.get_fund_list(fund_type)
        return {"status": "success", "data": funds}
    except Exception as e:
        logger.error(f"获取基金列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fund/{fund_code}")
async def get_fund_info(fund_code: str):
    """获取基金详细信息"""
    try:
        info = data_api.get_fund_info(fund_code)
        if not info:
            raise HTTPException(status_code=404, detail="基金不存在")
        return {"status": "success", "data": info}
    except Exception as e:
        logger.error(f"获取基金信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize")
async def optimize_portfolio(request: OptimizationRequest):
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
        logger.error(f"组合优化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """执行回测"""
    try:
        result = simulator.run_backtest(
            fund_pool=request.fund_pool,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_params=request.strategy_params
        )
        
        # 转换DataFrame为可JSON序列化的格式
        if 'portfolio_value' in result:
            result['portfolio_value'] = result['portfolio_value'].to_dict()
        if 'positions' in result:
            result['positions'] = result['positions'].to_dict()
        if 'trades' in result:
            result['trades'] = result['trades'].to_dict()
            
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"回测执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    """分析投资组合"""
    try:
        # 计算风险指标
        risk_metrics = risk_model.calculate_risk_metrics(request.portfolio)
        
        # 获取市场状态
        market_status = data_api.get_market_status()
        
        # 计算组合绩效
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
        logger.error(f"组合分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/market/status")
async def get_market_status():
    """获取市场状态"""
    try:
        status = data_api.get_market_status()
        return {"status": "success", "data": status}
    except Exception as e:
        logger.error(f"获取市场状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/visualization/efficient-frontier")
async def get_efficient_frontier(fund_pool: List[str]):
    """生成有效前沿图"""
    try:
        ef = EfficientFrontier()
        image_path = f"static/efficient_frontier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ef.plot_efficient_frontier(fund_pool, save_path=image_path)
        return {"status": "success", "data": {"image_url": image_path}}
    except Exception as e:
        logger.error(f"生成有效前沿图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/visualization/portfolio-tree")
async def get_portfolio_tree(portfolio: Dict[str, float]):
    """生成组合树状图"""
    try:
        pt = PortfolioTree()
        image_path = f"static/portfolio_tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pt.plot_portfolio_tree(portfolio, save_path=image_path)
        return {"status": "success", "data": {"image_url": image_path}}
    except Exception as e:
        logger.error(f"生成组合树状图失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 