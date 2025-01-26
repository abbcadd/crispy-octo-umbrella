import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

class PerformanceMetrics:
    """绩效评估指标计算"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def calculate_metrics(self,
                        returns: pd.Series,
                        benchmark_returns: Optional[pd.Series] = None,
                        risk_free_rate: float = 0.02) -> Dict:
        """
        计算绩效评估指标
        
        Args:
            returns: 收益率序列
            benchmark_returns: 基准收益率序列
            risk_free_rate: 无风险利率
            
        Returns:
            Dict包含各项绩效指标
        """
        try:
            metrics = {}
            
            # 基础收益指标
            metrics.update(self._calculate_return_metrics(returns))
            
            # 风险调整收益指标
            metrics.update(self._calculate_risk_adjusted_metrics(returns, risk_free_rate))
            
            # 相对基准指标
            if benchmark_returns is not None:
                metrics.update(self._calculate_relative_metrics(returns, benchmark_returns))
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"计算绩效指标失败: {str(e)}")
            return {}
            
    def _calculate_return_metrics(self, returns: pd.Series) -> Dict:
        """计算收益相关指标"""
        try:
            metrics = {
                'total_return': (returns + 1).prod() - 1,  # 总收益率
                'annual_return': (1 + returns).prod() ** (252/len(returns)) - 1,  # 年化收益率
                'monthly_returns': returns.resample('M').apply(lambda x: (1 + x).prod() - 1),  # 月度收益率
                'positive_months': (returns > 0).sum() / len(returns),  # 正收益月份占比
                'best_month': returns.max(),  # 最佳月度收益
                'worst_month': returns.min(),  # 最差月度收益
                'avg_monthly_return': returns.mean() * 21  # 平均月度收益
            }
            
            return {k: round(float(v) * 100, 2) if isinstance(v, (float, np.float64)) else v 
                   for k, v in metrics.items()}
                   
        except Exception as e:
            self.logger.error(f"计算收益指标失败: {str(e)}")
            return {}
            
    def _calculate_risk_adjusted_metrics(self,
                                       returns: pd.Series,
                                       risk_free_rate: float) -> Dict:
        """计算风险调整收益指标"""
        try:
            # 计算超额收益
            excess_returns = returns - risk_free_rate/252
            
            # 计算波动率
            volatility = returns.std() * np.sqrt(252)
            
            # 计算下行波动率
            downside_returns = returns[returns < 0]
            downside_vol = downside_returns.std() * np.sqrt(252)
            
            metrics = {
                'volatility': volatility * 100,  # 年化波动率
                'downside_volatility': downside_vol * 100,  # 下行波动率
                'sharpe_ratio': excess_returns.mean() / returns.std() * np.sqrt(252),  # 夏普比率
                'sortino_ratio': excess_returns.mean() / downside_vol * np.sqrt(252),  # 索提诺比率
                'calmar_ratio': self._calculate_calmar_ratio(returns),  # 卡玛比率
                'max_drawdown': self._calculate_max_drawdown(returns) * 100  # 最大回撤
            }
            
            return {k: round(v, 2) for k, v in metrics.items()}
            
        except Exception as e:
            self.logger.error(f"计算风险调整指标失败: {str(e)}")
            return {}
            
    def _calculate_relative_metrics(self,
                                  returns: pd.Series,
                                  benchmark_returns: pd.Series) -> Dict:
        """计算相对基准指标"""
        try:
            # 对齐日期
            returns = returns.reindex(benchmark_returns.index)
            
            # 计算超额收益
            excess_returns = returns - benchmark_returns
            tracking_error = excess_returns.std() * np.sqrt(252)
            
            # 计算贝塔
            covariance = returns.cov(benchmark_returns)
            variance = benchmark_returns.var()
            beta = covariance / variance
            
            # 计算阿尔法
            alpha = (returns.mean() - beta * benchmark_returns.mean()) * 252
            
            metrics = {
                'alpha': alpha * 100,  # 阿尔法
                'beta': beta,  # 贝塔
                'r_squared': returns.corr(benchmark_returns) ** 2,  # R方
                'tracking_error': tracking_error * 100,  # 跟踪误差
                'information_ratio': (excess_returns.mean() * 252) / tracking_error,  # 信息比率
                'capture_ratio_up': self._calculate_capture_ratio(returns, benchmark_returns, True),  # 上行捕获率
                'capture_ratio_down': self._calculate_capture_ratio(returns, benchmark_returns, False)  # 下行捕获率
            }
            
            return {k: round(v, 2) for k, v in metrics.items()}
            
        except Exception as e:
            self.logger.error(f"计算相对指标失败: {str(e)}")
            return {}
            
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """计算最大回撤"""
        try:
            cum_returns = (1 + returns).cumprod()
            running_max = cum_returns.expanding().max()
            drawdowns = (cum_returns - running_max) / running_max
            return abs(drawdowns.min())
        except:
            return 0
            
    def _calculate_calmar_ratio(self, returns: pd.Series) -> float:
        """计算卡玛比率"""
        try:
            annual_return = (1 + returns).prod() ** (252/len(returns)) - 1
            max_drawdown = self._calculate_max_drawdown(returns)
            return annual_return / max_drawdown if max_drawdown != 0 else 0
        except:
            return 0
            
    def _calculate_capture_ratio(self,
                               returns: pd.Series,
                               benchmark_returns: pd.Series,
                               up: bool = True) -> float:
        """计算上下行捕获率"""
        try:
            if up:
                mask = benchmark_returns > 0
            else:
                mask = benchmark_returns < 0
                
            returns_filtered = returns[mask]
            benchmark_filtered = benchmark_returns[mask]
            
            if len(returns_filtered) == 0:
                return 1.0
                
            return (1 + returns_filtered).prod() / (1 + benchmark_filtered).prod()
            
        except Exception as e:
            self.logger.error(f"计算捕获率失败: {str(e)}")
            return 1.0 