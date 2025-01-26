from datetime import datetime, timedelta
import pandas as pd

class DataAPI:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=24)  # 缓存24小时
        
    def get_fund_nav(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取基金净值数据（带缓存）"""
        cache_key = f"nav_{fund_code}_{start_date}_{end_date}"
        
        # 检查缓存
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if datetime.now() - cache_time < self.cache_duration:
                return cached_data
                
        # 获取数据
        nav_data = self._fetch_fund_nav(fund_code, start_date, end_date)
        
        # 更新缓存
        self.cache[cache_key] = (nav_data, datetime.now())
        
        return nav_data 