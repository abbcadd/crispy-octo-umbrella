import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from data_module import DataAPI
from strategy.portfolio_opt import PortfolioOptimizer
from strategy.risk_model import RiskModel
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class BacktestSimulator:
    """回测模拟器"""
    
    def __init__(self):
        self.data_api = DataAPI()
        self.optimizer = PortfolioOptimizer()
        self.risk_model = RiskModel()
        self.logger = logging.getLogger(__name__)
        
        # 回测参数
        self.initial_capital = 1_000_000  # 初始资金100万
        self.current_capital = self.initial_capital
        self.rebalance_freq = 'monthly'  # 调仓频率
        self.trade_cost = 0.0015  # 交易成本0.15%
        self.risk_free_rate = 0.02  # 无风险利率2%
        
        # 回测结果
        self.positions = defaultdict(dict)  # 使用defaultdict避免频繁的字典检查
        self.portfolio_value = []  # 使用列表而不是DataFrame以提高追加速度
        self.trades = []  # 使用列表存储交易记录
        self.performance = {}  # 绩效指标
        
        self.max_workers = multiprocessing.cpu_count()  # 使用CPU核心数
        
    def run_backtest(self, fund_pool: List[str], start_date: str, end_date: str,
                    strategy_params: Dict = None) -> Dict:
        """运行回测"""
        try:
            # 预先加载所有需要的数据
            self.fund_pool = fund_pool
            self.strategy_params = strategy_params
            self.nav_data = {}
            
            for fund_code in fund_pool:
                nav_df = self.data_api.get_fund_nav(fund_code, start_date, end_date)
                if not nav_df.empty:
                    self.nav_data[fund_code] = nav_df.set_index('date')
            
            dates = self._get_trading_dates(start_date, end_date)
            if not dates:
                return {}
            
            # 初始化
            self.positions = defaultdict(dict)
            self.portfolio_value = []
            self.trades = []
            self.current_capital = self.initial_capital
            
            # 记录初始净值
            self.portfolio_value.append({
                'date': dates[0],
                'value': 1.0
            })
            
            # 并行处理日期
            self._parallel_process_dates(dates)
            
            # 计算绩效指标
            self._calculate_performance()
            
            return self.performance
            
        except Exception as e:
            self.logger.error(f"回测执行失败: {str(e)}")
            return {}
            
    def _get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """生成交易日序列"""
        try:
            # 获取市场基准数据作为交易日历
            benchmark_data = self.data_api.get_index_data('000300', start_date, end_date)
            return benchmark_data['date'].tolist()
        except:
            return []
            
    def _should_rebalance(self, date: str) -> bool:
        """判断是否需要调仓"""
        if self.rebalance_freq == 'monthly':
            return pd.to_datetime(date).is_month_end
        elif self.rebalance_freq == 'quarterly':
            return pd.to_datetime(date).is_quarter_end
        return False
        
    def _get_target_weights(self,
                          fund_pool: List[str],
                          date: str,
                          strategy_params: Optional[Dict] = None) -> Dict[str, float]:
        """获取目标配置权重"""
        try:
            if strategy_params is None:
                strategy_params = {}
                
            # 使用优化器计算目标权重
            result = self.optimizer.optimize(
                fund_codes=fund_pool,
                method=strategy_params.get('method', 'mean_variance'),
                risk_aversion=strategy_params.get('risk_aversion', 2.0),
                constraints=strategy_params.get('constraints', None)
            )
            
            return result.get('weights', {})
            
        except Exception as e:
            self.logger.error(f"计算目标权重失败: {str(e)}")
            return {}
            
    def _execute_trades(self, date: str, target_weights: Dict[str, float]):
        """执行交易"""
        try:
            # 获取当前持仓市值
            current_positions = {}
            total_value = self.current_capital
            
            for code, amount in self.positions.get(date, {}).items():
                nav_df = self.data_api.get_fund_nav(code)
                if not nav_df.empty:
                    date_nav = nav_df[nav_df['date'] == date]
                    if not date_nav.empty:
                        nav = date_nav['nav'].iloc[0]
                        current_positions[code] = amount * nav
                        total_value += current_positions[code]
            
            # 计算目标持仓
            target_positions = {code: total_value * weight 
                              for code, weight in target_weights.items()}
            
            # 计算交易
            trades = []
            for code in set(list(current_positions.keys()) + list(target_positions.keys())):
                current_value = current_positions.get(code, 0)
                target_value = target_positions.get(code, 0)
                
                if abs(target_value - current_value) > 1:  # 1元以上的差异才交易
                    # 获取基金净值
                    nav_df = self.data_api.get_fund_nav(code)
                    if not nav_df.empty:
                        date_nav = nav_df[nav_df['date'] == date]
                        if not date_nav.empty:
                            nav = date_nav['nav'].iloc[0]
                            
                            # 计算交易数量和成本
                            trade_amount = (target_value - current_value) / nav
                            trade_value = abs(target_value - current_value)
                            trade_cost = trade_value * self.trade_cost
                            
                            trades.append({
                                'date': date,
                                'code': code,
                                'amount': trade_amount,
                                'price': nav,
                                'cost': trade_cost
                            })
                            
                            # 更新持仓
                            if code not in self.positions.get(date, {}):
                                self.positions[date][code] = 0
                            self.positions[date][code] += trade_amount
                            
                            # 更新资金
                            self.current_capital -= (trade_value + trade_cost)
            
            # 记录交易
            self.trades.extend(trades)
            
        except Exception as e:
            self.logger.error(f"执行交易失败: {str(e)}")
            
    def _update_portfolio_value(self, date: str):
        """更新组合净值"""
        try:
            total_value = 0
            
            # 计算各基金市值
            for code, amount in self.positions.get(date, {}).items():
                nav_df = self.data_api.get_fund_nav(code)
                if not nav_df.empty:
                    # 找到对应日期的净值
                    date_nav = nav_df[nav_df['date'] == date]
                    if not date_nav.empty:
                        nav = date_nav['nav'].iloc[0]
                        # 直接使用净值计算，不需要加1
                        total_value += amount * nav
            
            # 如果没有持仓，使用当前资金
            if not self.positions.get(date, {}):
                total_value = self.current_capital
            
            # 记录组合净值
            if total_value > 0:  # 添加验证
                # 计算相对于初始资金的净值
                relative_value = total_value / self.initial_capital
                self.portfolio_value.append({
                    'date': date,
                    'value': relative_value  # 使用相对净值
                })
                
                # 更新当前资金
                self.current_capital = total_value
                
        except Exception as e:
            self.logger.error(f"更新组合净值失败: {str(e)}")
            
    def _calculate_performance(self):
        """计算回测绩效指标"""
        try:
            if not self.portfolio_value:
                self.logger.warning("没有可用的组合净值数据")
                return
            
            # 转换净值数据为DataFrame
            nav_df = pd.DataFrame(self.portfolio_value)
            
            if nav_df.empty:
                self.logger.warning("组合净值数据为空")
                return
            
            # 确保日期列存在
            if 'date' not in nav_df.columns:
                self.logger.error("净值数据缺少日期列")
                return
            
            nav_df.set_index('date', inplace=True)
            
            # 计算收益率序列
            if len(nav_df) < 2:
                self.logger.warning("净值数据点数不足")
                return
            
            returns = nav_df['value'].pct_change().dropna()
            
            if returns.empty:
                self.logger.warning("无法计算收益率")
                return
            
            # 计算各项指标
            try:
                total_return = (nav_df['value'].iloc[-1] / nav_df['value'].iloc[0] - 1) * 100
                annual_return = (1 + total_return/100) ** (252/len(returns)) - 1
                annual_vol = returns.std() * np.sqrt(252)
                sharpe = (annual_return - self.risk_free_rate) / annual_vol if annual_vol != 0 else 0
                max_drawdown = self._calculate_max_drawdown(nav_df['value'])
                
                # 汇总绩效指标
                self.performance = {
                    'total_return': round(total_return, 2),  # 总收益率(%)
                    'annual_return': round(annual_return * 100, 2),  # 年化收益率(%)
                    'annual_volatility': round(annual_vol * 100, 2),  # 年化波动率(%)
                    'sharpe_ratio': round(sharpe, 2),  # 夏普比率
                    'max_drawdown': round(max_drawdown * 100, 2),  # 最大回撤(%)
                    'trade_count': len(self.trades),  # 交易次数
                    'total_cost': round(sum(t['cost'] for t in self.trades), 2)  # 总交易成本
                }
            except Exception as e:
                self.logger.error(f"计算具体指标失败: {str(e)}")
                self.performance = {}
            
        except Exception as e:
            self.logger.error(f"计算绩效指标失败: {str(e)}")
            self.performance = {}
            
    def _calculate_max_drawdown(self, nav_series: pd.Series) -> float:
        """计算最大回撤"""
        try:
            running_max = nav_series.expanding().max()
            drawdown = (nav_series - running_max) / running_max
            return abs(drawdown.min())
        except:
            return 0 

    def _update_portfolio_values(self, dates: List[str]):
        """批量更新组合净值"""
        try:
            # 获取所有基金的净值数据
            nav_data = {}
            for code in set(sum([list(pos.keys()) for pos in self.positions.values()], [])):
                nav_df = self.data_api.get_fund_nav(code)
                if not nav_df.empty:
                    nav_data[code] = nav_df.set_index('date')['nav']
            
            # 向量化计算每个日期的组合价值
            for date in dates:
                total_value = 0
                for code, amount in self.positions.get(date, {}).items():
                    if code in nav_data and date in nav_data[code].index:
                        total_value += amount * nav_data[code][date]
                
                if total_value > 0:
                    relative_value = total_value / self.initial_capital
                    self.portfolio_value.append({
                        'date': date,
                        'value': relative_value
                    })
                    self.current_capital = total_value
                    
        except Exception as e:
            self.logger.error(f"批量更新组合净值失败: {str(e)}") 

    def _parallel_process_dates(self, dates: List[str], chunk_size: int = 30):
        """并行处理日期"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 将日期分成多个块
            date_chunks = [dates[i:i + chunk_size] for i in range(0, len(dates), chunk_size)]
            
            # 并行处理每个块
            futures = [executor.submit(self._process_date_chunk, chunk) 
                      for chunk in date_chunks]
            
            # 等待所有任务完成
            for future in futures:
                future.result()
                
    def _process_date_chunk(self, dates: List[str]):
        """处理一组日期"""
        for date in dates:
            target_weights = self._get_target_weights(self.fund_pool, date, self.strategy_params)
            if target_weights:
                self._execute_trades(date, target_weights)
            self._update_portfolio_value(date) 