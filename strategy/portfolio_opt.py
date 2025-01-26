import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import cvxopt
from cvxopt import matrix, solvers
import logging
from data_module import DataAPI

class PortfolioOptimizer:
    """投资组合优化器"""
    
    def __init__(self):
        self.data_api = DataAPI()
        self.logger = logging.getLogger(__name__)
        # 设置cvxopt求解器参数
        solvers.options['show_progress'] = False
        
    def optimize(self,
                fund_codes: List[str],
                method: str = 'mean_variance',
                risk_aversion: float = 2.0,
                constraints: Dict = None) -> Dict:
        """
        执行投资组合优化
        
        Args:
            fund_codes: 候选基金代码列表
            method: 优化方法，可选 'mean_variance', 'risk_parity', 'min_variance'
            risk_aversion: 风险厌恶系数
            constraints: 约束条件字典
            
        Returns:
            Dict包含权重和优化结果统计
        """
        try:
            # 获取基金历史净值数据
            returns_data = self._get_returns_data(fund_codes)
            if returns_data.empty:
                return {}
                
            # 根据方法选择优化策略
            if method == 'mean_variance':
                weights = self._mean_variance_optimize(returns_data, risk_aversion, constraints)
            elif method == 'risk_parity':
                weights = self._risk_parity_optimize(returns_data, constraints)
            elif method == 'min_variance':
                weights = self._min_variance_optimize(returns_data, constraints)
            else:
                raise ValueError(f"不支持的优化方法: {method}")
                
            # 计算组合统计指标
            stats = self._calculate_portfolio_stats(returns_data, weights)
            
            return {
                'weights': dict(zip(fund_codes, weights)),
                'stats': stats
            }
            
        except Exception as e:
            self.logger.error(f"投资组合优化失败: {str(e)}")
            return {}
            
    def _get_returns_data(self, fund_codes: List[str]) -> pd.DataFrame:
        """获取基金收益率数据"""
        try:
            returns_data = pd.DataFrame()
            
            for fund_code in fund_codes:
                # 获取基金净值数据
                nav_df = self.data_api.get_fund_nav(fund_code)
                
                if nav_df.empty:
                    continue
                    
                # 使用净值计算收益率
                returns = nav_df['nav'].pct_change()
                returns.name = fund_code
                returns.index = nav_df['date']
                
                # 添加到返回数据中
                returns_data = pd.concat([returns_data, returns], axis=1)
            
            if returns_data.empty:
                self.logger.warning("无法获取任何基金的收益率数据")
            
            return returns_data
            
        except Exception as e:
            self.logger.error(f"获取收益率数据失败: {str(e)}")
            return pd.DataFrame()
            
    def _mean_variance_optimize(self,
                              returns: pd.DataFrame,
                              risk_aversion: float,
                              constraints: Optional[Dict] = None) -> np.ndarray:
        """均值方差优化"""
        try:
            n = len(returns.columns)
            returns_mean = returns.mean().values
            returns_cov = returns.cov().values
            
            # 构建二次规划问题
            P = matrix(2 * risk_aversion * returns_cov)
            q = matrix(-returns_mean)
            
            # 约束条件：权重和为1
            A = matrix(1.0, (1, n))
            b = matrix(1.0)
            
            # 权重非负约束
            G = matrix(-np.eye(n))
            h = matrix(0.0, (n, 1))
            
            # 添加自定义约束
            if constraints:
                if 'max_weight' in constraints:
                    G = matrix(np.vstack([-np.eye(n), np.eye(n)]))
                    h = matrix(np.hstack([np.zeros(n), np.ones(n) * constraints['max_weight']]))
                    
            # 求解优化问题
            sol = solvers.qp(P, q, G, h, A, b)
            
            if sol['status'] != 'optimal':
                raise Exception("优化求解失败")
                
            return np.array(sol['x']).flatten()
            
        except Exception as e:
            self.logger.error(f"均值方差优化失败: {str(e)}")
            return np.array([1/n] * n)  # 返回等权重
            
    def _risk_parity_optimize(self,
                            returns: pd.DataFrame,
                            constraints: Optional[Dict] = None) -> np.ndarray:
        """风险平价优化"""
        try:
            n = len(returns.columns)
            returns_cov = returns.cov().values
            
            def risk_parity_objective(x):
                """风险平价目标函数"""
                portfolio_risk = np.sqrt(np.dot(x.T, np.dot(returns_cov, x)))
                risk_contributions = x * (np.dot(returns_cov, x)) / portfolio_risk
                risk_diffs = risk_contributions - risk_contributions.mean()
                return np.sum(risk_diffs ** 2)
            
            # 初始猜测值
            x0 = np.array([1/n] * n)
            
            # 约束条件
            bounds = [(0, 1) for _ in range(n)]
            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
            
            # 使用scipy优化
            from scipy.optimize import minimize
            result = minimize(risk_parity_objective, x0,
                            method='SLSQP',
                            bounds=bounds,
                            constraints=constraints)
                            
            if not result.success:
                raise Exception("风险平价优化失败")
                
            return result.x
            
        except Exception as e:
            self.logger.error(f"风险平价优化失败: {str(e)}")
            return np.array([1/n] * n)
            
    def _min_variance_optimize(self,
                             returns: pd.DataFrame,
                             constraints: Optional[Dict] = None) -> np.ndarray:
        """最小方差优化"""
        try:
            n = len(returns.columns)
            returns_cov = returns.cov().values
            
            # 构建二次规划问题
            P = matrix(returns_cov)
            q = matrix(0.0, (n, 1))
            
            # 约束条件：权重和为1
            A = matrix(1.0, (1, n))
            b = matrix(1.0)
            
            # 权重非负约束
            G = matrix(-np.eye(n))
            h = matrix(0.0, (n, 1))
            
            # 添加自定义约束
            if constraints:
                if 'max_weight' in constraints:
                    G = matrix(np.vstack([-np.eye(n), np.eye(n)]))
                    h = matrix(np.hstack([np.zeros(n), np.ones(n) * constraints['max_weight']]))
                    
            # 求解优化问题
            sol = solvers.qp(P, q, G, h, A, b)
            
            if sol['status'] != 'optimal':
                raise Exception("最小方差优化失败")
                
            return np.array(sol['x']).flatten()
            
        except Exception as e:
            self.logger.error(f"最小方差优化失败: {str(e)}")
            return np.array([1/n] * n)
            
    def _calculate_portfolio_stats(self,
                                 returns: pd.DataFrame,
                                 weights: np.ndarray) -> Dict:
        """计算组合统计指标"""
        try:
            portfolio_returns = returns.dot(weights)
            
            stats = {
                'annual_return': portfolio_returns.mean() * 252 * 100,  # 年化收益率(%)
                'annual_volatility': portfolio_returns.std() * np.sqrt(252) * 100,  # 年化波动率(%)
                'sharpe_ratio': (portfolio_returns.mean() * 252) / (portfolio_returns.std() * np.sqrt(252)),  # 夏普比率
                'max_drawdown': self._calculate_max_drawdown(portfolio_returns) * 100  # 最大回撤(%)
            }
            
            return {k: round(v, 2) for k, v in stats.items()}
            
        except Exception as e:
            self.logger.error(f"计算组合统计指标失败: {str(e)}")
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