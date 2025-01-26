from pydantic import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "基金组合优化系统"
    
    # 数据配置
    DATA_CACHE_DIR: str = "data/cache"
    STATIC_DIR: str = "static"
    
    # 回测配置
    DEFAULT_INITIAL_CAPITAL: float = 1_000_000
    DEFAULT_TRADE_COST: float = 0.0015
    
    # 优化配置
    DEFAULT_RISK_AVERSION: float = 2.0
    MAX_POSITION_SIZE: float = 0.4
    
    class Config:
        case_sensitive = True

settings = Settings() 