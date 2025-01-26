from .fund_loader import FundLoader
from .market_loader import MarketDataLoader
from .risk_free import RiskFreeRateLoader
import logging
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class DataAPI:
    """数据层统一访问接口"""
    
    def __init__(self):
        self.fund_loader = FundLoader()
        self.market_loader = MarketDataLoader()
        self.risk_free_loader = RiskFreeRateLoader()
        self.logger = logging.getLogger(__name__)
        
    def get_fund_list(self, fund_type: str = None) -> list:
        """获取基金列表"""
        return self.fund_loader.get_fund_list(fund_type)
        
    def get_fund_info(self, fund_code: str) -> dict:
        """获取基金基本信息"""
        return self.fund_loader.get_fund_info(fund_code)
        
    def get_fund_nav(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取基金净值数据"""
        return self.fund_loader.get_fund_nav(fund_code, start_date, end_date)
        
    def get_fund_portfolio(self, fund_code: str) -> dict:
        """获取基金持仓数据"""
        return self.fund_loader.get_fund_portfolio(fund_code)
        
    def get_index_data(self, index_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数行情数据"""
        return self.market_loader.get_index_data(index_code, start_date, end_date)
        
    def get_market_status(self) -> dict:
        """获取市场状态"""
        return self.market_loader.get_market_status()
        
    def get_risk_free_rate(self, rate_type: str = 'shibor') -> float:
        """获取无风险利率"""
        return self.risk_free_loader.get_current_rate(rate_type)
        
    def get_fund_manager_info(self, fund_code: str) -> dict:
        """获取基金经理信息"""
        return self.fund_loader.get_fund_manager_info(fund_code)
        
    def get_fund_fee(self, fund_code: str) -> dict:
        """获取基金费率信息"""
        return self.fund_loader.get_fund_fee(fund_code)
        
    def get_fund_performance(self, fund_code: str) -> dict:
        """获取基金绩效指标"""
        try:
            # 获取基金净值数据
            nav_df = self.get_fund_nav(fund_code)
            if nav_df.empty:
                return {}
                
            # 获取同期市场基准数据
            benchmark_df = self.get_index_data('000300')
            
            # 获取无风险利率
            risk_free_rate = self.get_risk_free_rate()
            
            # 计算各项指标
            performance = {
                'annual_return': self._calculate_annual_return(nav_df),
                'volatility': self._calculate_volatility(nav_df),
                'max_drawdown': self._calculate_max_drawdown(nav_df),
                'sharpe_ratio': self._calculate_sharpe_ratio(nav_df, risk_free_rate),
                'benchmark_beta': self._calculate_beta(nav_df, benchmark_df),
                'tracking_error': self._calculate_tracking_error(nav_df, benchmark_df)
            }
            
            return performance
            
        except Exception as e:
            self.logger.error(f"计算基金{fund_code}绩效指标失败: {str(e)}")
            return {}
            
    def _calculate_annual_return(self, nav_df: pd.DataFrame) -> float:
        """计算年化收益率"""
        try:
            total_days = (nav_df['date'].max() - nav_df['date'].min()).days
            total_return = nav_df['nav'].iloc[-1] / nav_df['nav'].iloc[0] - 1
            annual_return = (1 + total_return) ** (365 / total_days) - 1
            return round(annual_return * 100, 2)
        except:
            return 0
            
    def _calculate_volatility(self, nav_df: pd.DataFrame) -> float:
        """计算波动率"""
        try:
            daily_returns = nav_df['nav'].pct_change()
            annual_vol = daily_returns.std() * np.sqrt(252)
            return round(annual_vol * 100, 2)
        except:
            return 0
            
    def _calculate_max_drawdown(self, nav_df: pd.DataFrame) -> float:
        """计算最大回撤"""
        try:
            nav_series = nav_df['nav']
            running_max = nav_series.expanding().max()
            drawdown = (nav_series - running_max) / running_max
            max_drawdown = drawdown.min()
            return round(max_drawdown * 100, 2)
        except:
            return 0
            
    def _calculate_sharpe_ratio(self, nav_df: pd.DataFrame, risk_free_rate: float) -> float:
        """计算夏普比率"""
        try:
            daily_returns = nav_df['nav'].pct_change()
            excess_returns = daily_returns - risk_free_rate / 252
            sharpe = np.sqrt(252) * excess_returns.mean() / daily_returns.std()
            return round(sharpe, 2)
        except:
            return 0
            
    def _calculate_beta(self, nav_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
        """计算贝塔系数"""
        try:
            # 确保日期对齐
            merged_df = pd.merge(nav_df, benchmark_df, on='date', suffixes=('_fund', '_bench'))
            fund_returns = merged_df['nav'].pct_change()
            bench_returns = merged_df['close'].pct_change()
            beta = fund_returns.cov(bench_returns) / bench_returns.var()
            return round(beta, 2)
        except:
            return 1
            
    def _calculate_tracking_error(self, nav_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> float:
        """计算跟踪误差"""
        try:
            merged_df = pd.merge(nav_df, benchmark_df, on='date', suffixes=('_fund', '_bench'))
            fund_returns = merged_df['nav'].pct_change()
            bench_returns = merged_df['close'].pct_change()
            tracking_diff = fund_returns - bench_returns
            tracking_error = tracking_diff.std() * np.sqrt(252)
            return round(tracking_error * 100, 2)
        except:
            return 0 