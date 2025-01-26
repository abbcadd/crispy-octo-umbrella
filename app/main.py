from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.endpoints import funds, portfolio, backtest, visualization
from pydantic import BaseModel
from typing import List, Dict
import uvicorn

app = FastAPI(
    title="Fund Portfolio Optimizer",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# 注册路由
app.include_router(funds.router, prefix=f"{settings.API_V1_PREFIX}/funds", tags=["funds"])
app.include_router(portfolio.router, prefix=f"{settings.API_V1_PREFIX}/portfolio", tags=["portfolio"])
app.include_router(backtest.router, prefix=f"{settings.API_V1_PREFIX}/backtest", tags=["backtest"])
app.include_router(visualization.router, prefix=f"{settings.API_V1_PREFIX}/visualization", tags=["visualization"])

class OptimizationRequest(BaseModel):
    fund_codes: List[str]
    start_date: str
    end_date: str
    risk_aversion: float = 2.0
    method: str = "mean_variance"

@app.post("/api/optimize")
async def optimize_portfolio(request: OptimizationRequest):
    try:
        optimizer = PortfolioOptimizer()
        result = optimizer.optimize(
            fund_codes=request.fund_codes,
            method=request.method,
            risk_aversion=request.risk_aversion
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
async def root():
    return {
        "message": "Welcome to Fund Portfolio Optimization System",
        "version": settings.VERSION
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 