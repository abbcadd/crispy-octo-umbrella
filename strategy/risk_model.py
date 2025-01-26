import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
from data_module import DataAPI

class RiskModel:
    """风险模型"""
    
    def __init__(self):
        self.data_api = DataAPI()
        self.logger = logging.getLogger(__name__)
        
    def calculate_risk_metrics(self, portfolio: Dict[str, float]) -> Dict:
        """计算风险指标"""
        try:
            # 获取收益率数据
            returns_data = pd.DataFrame()
            for fund_code, weight in portfolio.items():
                nav_df = self.data_api.get_fund_nav(fund_code)
                if not nav_df.empty:
                    returns = nav_df['nav'].pct_change().fillna(0)
                    returns.name = fund_code
                    returns.index = nav_df['date']
                    returns_data = pd.concat([returns_data, returns], axis=1)
            
            if returns_data.empty:
                return {}
                
            # 计算组合收益率
            portfolio_returns = returns_data.dot(pd.Series(portfolio))
            
            # 计算风险指标
            metrics = {
                'volatility': returns_data.std() * np.sqrt(252),  # 年化波动率
                'var': self._calculate_var(portfolio_returns),
                'cvar': self._calculate_cvar(portfolio_returns),
                'tail_risk': self._calculate_tail_risk(returns_data),
                'risk_contribution': self._calculate_risk_contribution(returns_data, portfolio)
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"计算风险指标失败: {str(e)}")
            return {}
            
    def stress_test(self,
                   portfolio: Dict[str, float],
                   scenarios: List[Dict] = None) -> Dict:
        """
        压力测试
        
        Args:
            portfolio: 基金代码和权重的字典
            scenarios: 压力情景列表
            
        Returns:
            Dict包含各情景下的损益
        """
        try:
            if scenarios is None:
                scenarios = self._get_default_scenarios()
                
            results = {}
            for scenario in scenarios:
                scenario_return = self._calculate_scenario_return(portfolio, scenario)
                results[scenario['name']] = round(scenario_return * 100, 2)  # 转换为百分比
                
            return results
            
        except Exception as e:
            self.logger.error(f"压力测试失败: {str(e)}")
            return {}
            
    def _get_portfolio_returns(self,
                             portfolio: Dict[str, float],
                             lookback_period: int) -> pd.Series:
        """获取组合历史收益率"""
        try:
            returns_data = pd.DataFrame()
            
            for code, weight in portfolio.items():
                nav_df = self.data_api.get_fund_nav(code)
                if not nav_df.empty:
                    returns = nav_df['nav'].pct_change()
                    returns_data[code] = returns * weight
                    
            if returns_data.empty:
                return pd.Series()
                
            portfolio_returns = returns_data.sum(axis=1)
            return portfolio_returns.tail(lookback_period)
            
        except Exception as e:
            self.logger.error(f"获取组合收益率失败: {str(e)}")
            return pd.Series()
            
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算VaR"""
        if returns.empty:
            return np.nan
        return -np.percentile(returns, (1 - confidence) * 100)
            
    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """计算CVaR"""
        if returns.empty:
            return np.nan
        var = self._calculate_var(returns, confidence)
        return -returns[returns <= -var].mean()
            
    def _calculate_tail_risk(self, returns: pd.Series) -> float:
        """计算尾部风险"""
        try:
            # 使用偏度和峰度评估尾部风险
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            # 综合指标：负偏度和超额峰度的加权和
            tail_risk = abs(skewness) + (kurtosis - 3) / 10
            return round(tail_risk, 2)
        except:
            return 0
            
    def _calculate_risk_contribution(self,
                                   returns: pd.Series,
                                   portfolio: Dict[str, float]) -> Dict[str, float]:
        """计算风险贡献"""
        try:
            weights = np.array(list(portfolio.values()))
            codes = list(portfolio.keys())
            
            # 获取各基金收益率数据
            fund_returns = pd.DataFrame()
            for code in codes:
                nav_df = self.data_api.get_fund_nav(code)
                if not nav_df.empty:
                    fund_returns[code] = nav_df['nav'].pct_change()
                    
            if fund_returns.empty:
                return {}
                
            # 计算协方差矩阵
            cov_matrix = fund_returns.cov().values
            
            # 计算组合波动率
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            # 计算边际风险贡献
            mrc = np.dot(cov_matrix, weights) / portfolio_vol
            
            # 计算风险贡献
            rc = weights * mrc
            rc_pct = rc / rc.sum() * 100  # 转换为百分比
            
            return dict(zip(codes, [round(x, 2) for x in rc_pct]))
            
        except Exception as e:
            self.logger.error(f"计算风险贡献失败: {str(e)}")
            return {}
            
    def _get_default_scenarios(self) -> List[Dict]:
        """获取默认压力测试情景"""
        return [
            {
                'name': '股灾情景',
                'market_change': -0.20,  # 市场下跌20%
                'volatility_multiplier': 2.0  # 波动率翻倍
            },
            {
                'name': '债灾情景',
                'interest_rate_change': 0.03,  # 利率上升300bp
                'credit_spread_change': 0.02  # 信用利差上升200bp
            },
            {
                'name': '流动性危机',
                'redemption_rate': 0.30,  # 赎回率30%
                'bid_ask_spread_multiplier': 3.0  # 买卖价差扩大3倍
            }
        ]
        
    def _calculate_scenario_return(self,
                                 portfolio: Dict[str, float],
                                 scenario: Dict) -> float:
        """计算压力情景下的组合收益"""
        try:
            total_return = 0
            
            for code, weight in portfolio.items():
                # 获取基金信息
                fund_info = self.data_api.get_fund_info(code)
                
                # 根据基金类型和情景参数估算损失
                if '股票' in fund_info.get('type', ''):
                    if 'market_change' in scenario:
                        total_return += weight * scenario['market_change']
                elif '债券' in fund_info.get('type', ''):
                    if 'interest_rate_change' in scenario:
                        duration = fund_info.get('duration', 3)  # 默认久期为3年
                        total_return += weight * (-duration * scenario['interest_rate_change'])
                        
                # 考虑流动性影响
                if 'redemption_rate' in scenario:
                    liquidity_cost = weight * scenario['redemption_rate'] * 0.01  # 假设赎回成本为1%
                    total_return -= liquidity_cost
                    
            return total_return
            
        except Exception as e:
            self.logger.error(f"计算情景收益失败: {str(e)}")
            return 0 