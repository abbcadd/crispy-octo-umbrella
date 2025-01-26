from pydantic import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """应用配置"""
    
    # 基本配置
    PROJECT_NAME: str = "Fund Portfolio Optimizer"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # 数据配置
    DATA_CACHE_DIR: str = "data/cache"
    STATIC_DIR: str = "app/static"
    STATIC_URL: str = "/static"
    
    # 回测配置
    DEFAULT_INITIAL_CAPITAL: float = 1_000_000
    DEFAULT_TRADE_COST: float = 0.0015
    
    # 优化配置
    DEFAULT_RISK_AVERSION: float = 2.0
    MAX_POSITION_SIZE: float = 0.4
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings() 