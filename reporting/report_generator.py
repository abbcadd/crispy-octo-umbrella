class ReportGenerator:
    def generate_report(self, backtest_results: Dict, output_format: str = 'html'):
        """生成回测报告"""
        report = {
            'summary': self._generate_summary(backtest_results),
            'performance_analysis': self._generate_performance_analysis(backtest_results),
            'risk_analysis': self._generate_risk_analysis(backtest_results),
            'trading_analysis': self._generate_trading_analysis(backtest_results)
        }
        
        if output_format == 'html':
            return self._generate_html_report(report)
        elif output_format == 'pdf':
            return self._generate_pdf_report(report) 