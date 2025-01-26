import logging
from typing import List, Dict
import pandas as pd

class BacktestAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_performance(self, portfolio_values: List[Dict], trades: List[Dict]) -> Dict:
        """分析回测结果"""
        metrics = {
            'basic_metrics': self._calculate_basic_metrics(portfolio_values),
            'risk_metrics': self._calculate_risk_metrics(portfolio_values),
            'trading_metrics': self._analyze_trades(trades),
            'monthly_returns': self._calculate_monthly_returns(portfolio_values)
        }
        return metrics
        
    def _calculate_basic_metrics(self, portfolio_values: List[Dict]) -> Dict:
        """计算基础指标"""
        nav_df = pd.DataFrame(portfolio_values)
        returns = nav_df['value'].pct_change()
        
        return {
            'total_return': self._calculate_total_return(nav_df),
            'annual_return': self._calculate_annual_return(returns),
            'monthly_returns': self._calculate_monthly_returns(nav_df),
            'win_rate': self._calculate_win_rate(returns)
        } 