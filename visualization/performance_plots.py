class PerformancePlotter:
    def plot_performance_dashboard(self, backtest_results: Dict):
        """绘制回测结果仪表板"""
        plt.figure(figsize=(15, 10))
        
        # 净值曲线
        plt.subplot(2, 2, 1)
        self._plot_nav_curve(backtest_results['portfolio_values'])
        
        # 月度收益热力图
        plt.subplot(2, 2, 2)
        self._plot_monthly_returns_heatmap(backtest_results['monthly_returns'])
        
        # 回撤分析
        plt.subplot(2, 2, 3)
        self._plot_drawdown_analysis(backtest_results['portfolio_values'])
        
        # 交易分析
        plt.subplot(2, 2, 4)
        self._plot_trade_analysis(backtest_results['trades']) 