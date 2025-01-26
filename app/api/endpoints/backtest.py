from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
from backtest.simulator import BacktestSimulator
from app.api import deps
import cProfile
import pstats
import io
import logging

router = APIRouter()

class BacktestRequest(BaseModel):
    fund_pool: List[str]
    start_date: str
    end_date: str
    strategy_params: Optional[Dict] = None

@router.post("/run")
async def run_backtest(
    request: BacktestRequest,
    simulator: BacktestSimulator = Depends(deps.get_simulator)
):
    """执行回测"""
    profiler = cProfile.Profile() # 创建性能分析器
    profiler.enable() # 启动性能分析

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
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        profiler.disable() # 停止性能分析
        s = io.StringIO() # 创建StringIO对象用于存储性能分析结果
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative') # 创建Stats对象并按cumulative time排序
        ps.print_stats(20) # 打印前20行最耗时的函数
        logging.info("性能分析结果:\n" + s.getvalue()) # 将性能分析结果输出到日志 