import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from typing import Dict, List
import seaborn as sns
from data_module import DataAPI


class PortfolioTree:
    """投资组合树状图可视化"""

    def __init__(self):
        self.data_api = DataAPI()
        sns.set_style("whitegrid")  # 使用 seaborn 设置样式

    def plot_portfolio_tree(self,
                            portfolio: Dict[str, float],
                            risk_contribution: Dict[str, float] = None,
                            save_path: str = None) -> None:
        """
        绘制投资组合树状图

        Args:
            portfolio: 基金代码和权重的字典
            risk_contribution: 风险贡献度字典
            save_path: 图片保存路径
        """
        try:
            # 创建图形对象
            G = nx.Graph()

            # 添加节点
            self._add_nodes(G, portfolio, risk_contribution)

            # 添加边
            self._add_edges(G, portfolio)

            # 绘制图形
            plt.figure(figsize=(15, 10))

            # 设置布局
            pos = nx.spring_layout(G, k=1, iterations=50)

            # 绘制节点
            self._draw_nodes(G, pos, portfolio, risk_contribution)

            # 绘制边
            nx.draw_networkx_edges(G, pos, alpha=0.2)

            # 添加标签
            self._add_labels(G, pos, portfolio)

            plt.title('Portfolio Structure Tree')
            plt.axis('off')

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            else:
                plt.show()

        except Exception as e:
            print(f"绘制组合树状图失败: {str(e)}")

    def _add_nodes(self,
                   G: nx.Graph,
                   portfolio: Dict[str, float],
                   risk_contribution: Dict[str, float] = None):
        """添加节点"""
        # 添加中心节点
        G.add_node('Portfolio', type='center')

        # 添加资产类型节点
        asset_types = self._get_asset_types(portfolio.keys())
        for asset_type in asset_types:
            G.add_node(asset_type, type='asset_type')
            G.add_edge('Portfolio', asset_type)

        # 添加基金节点
        for code in portfolio:
            fund_info = self.data_api.get_fund_info(code)
            asset_type = fund_info.get('type', 'Other')
            G.add_node(code,
                       type='fund',
                       weight=portfolio[code],
                       risk=risk_contribution.get(code, 0) if risk_contribution else 0)
            G.add_edge(asset_type, code)

    def _add_edges(self, G: nx.Graph, portfolio: Dict[str, float]):
        """添加边"""
        # 计算相关性
        returns_data = pd.DataFrame()
        for code in portfolio:
            nav_df = self.data_api.get_fund_nav(code)
            if not nav_df.empty:
                returns_data[code] = nav_df['unit_nav'].pct_change() # 用的单位净值

        if not returns_data.empty:
            corr_matrix = returns_data.corr()

            # 添加基金间的边（基于相关性）
            for i in portfolio:
                for j in portfolio:
                    if i < j:
                        correlation = abs(corr_matrix.loc[i, j])
                        if correlation > 0.5:  # 只显示强相关的边
                            G.add_edge(i, j, weight=correlation)

    def _draw_nodes(self,
                    G: nx.Graph,
                    pos: Dict,
                    portfolio: Dict[str, float],
                    risk_contribution: Dict[str, float] = None):
        """绘制节点"""
        # 绘制不同类型的节点
        node_colors = []
        node_sizes = []

        for node in G.nodes():
            if G.nodes[node]['type'] == 'center':
                node_colors.append('lightblue')
                node_sizes.append(3000)
            elif G.nodes[node]['type'] == 'asset_type':
                node_colors.append('lightgreen')
                node_sizes.append(2000)
            else:  # fund nodes
                node_colors.append('orange')
                weight = G.nodes[node]['weight']
                node_sizes.append(1000 * weight)

        nx.draw_networkx_nodes(G, pos,
                               node_color=node_colors,
                               node_size=node_sizes,
                               alpha=0.7)

    def _add_labels(self,
                    G: nx.Graph,
                    pos: Dict,
                    portfolio: Dict[str, float]):
        """添加标签"""
        labels = {}
        for node in G.nodes():
            if G.nodes[node]['type'] == 'center':
                labels[node] = 'Portfolio'
            elif G.nodes[node]['type'] == 'asset_type':
                labels[node] = node
            else:  # fund nodes
                weight = G.nodes[node]['weight']
                risk = G.nodes[node].get('risk', 0)
                labels[node] = f"{node}\n{weight:.1%}"
                if risk > 0:
                    labels[node] += f"\nRisk: {risk:.1%}"

        nx.draw_networkx_labels(G, pos, labels, font_size=8)

    def _get_asset_types(self, fund_codes: List[str]) -> List[str]:
        """获取资产类型"""
        asset_types = set()
        for code in fund_codes:
            fund_info = self.data_api.get_fund_info(code)
            asset_types.add(fund_info.get('type', 'Other'))
        return list(asset_types)
