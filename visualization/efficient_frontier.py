import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from data_module import DataAPI
from strategy.portfolio_opt import PortfolioOptimizer

class EfficientFrontier:
    """有效前沿可视化"""
    
    def __init__(self):
        self.data_api = DataAPI()
        self.optimizer = PortfolioOptimizer()
        # 设置绘图样式
        sns.set_style("whitegrid")
        
    def plot_efficient_frontier(self, fund_pool: List[str]):
        """绘制有效前沿"""
        plt.figure(figsize=(12, 8))
        
        # 生成随机组合
        returns, risks, sharpe_ratios = self._generate_portfolios(fund_pool)
        
        # 绘制散点图
        sc = plt.scatter(risks, returns, c=sharpe_ratios, cmap='viridis', 
                        marker='o', s=10, alpha=0.3)
        
        # 添加颜色条
        plt.colorbar(sc, label='Sharpe Ratio')
        
        # 绘制个别资产点
        self._plot_individual_assets(fund_pool)
        
        # 绘制资本市场线
        self._plot_capital_market_line(returns, risks)
        
        plt.xlabel('Expected Volatility')
        plt.ylabel('Expected Return')
        plt.title('Efficient Frontier')
        plt.grid(True, alpha=0.3)
        
        return plt.gcf()
    
    def plot_portfolio_composition(self, 
                                 weights: Dict[str, float],
                                 title: Optional[str] = None) -> None:
        """绘制投资组合构成
        
        Args:
            weights: 投资组合权重字典
            title: 图表标题
        """
        try:
            # 准备数据
            labels = list(weights.keys())
            sizes = list(weights.values())
            
            # 创建饼图
            plt.figure(figsize=(10, 8))
            plt.pie(sizes, 
                   labels=labels,
                   autopct='%1.1f%%',
                   startangle=90)
            
            # 设置图形属性
            if title:
                plt.title(title)
            else:
                plt.title('Portfolio Composition')
            
            # 确保饼图是圆形
            plt.axis('equal')
            
            # 显示图形
            plt.show()
            
        except Exception as e:
            plt.close()  # 确保关闭图形
            raise Exception(f"绘制投资组合构成失败: {str(e)}") 