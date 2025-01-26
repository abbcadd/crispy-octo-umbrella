from typing import List, Dict

class BenchmarkAnalyzer:
    def __init__(self):
        self.data_api = DataAPI()
        
    def compare_with_benchmark(self, portfolio_values: List[Dict], 
                             benchmark_code: str = '000300') -> Dict:
        """与基准比较"""
        # 获取基准数据
        benchmark_data = self.data_api.get_index_data(benchmark_code)
        
        # 计算相对指标
        return {
            'alpha': self._calculate_alpha(portfolio_values, benchmark_data),
            'beta': self._calculate_beta(portfolio_values, benchmark_data),
            'information_ratio': self._calculate_ir(portfolio_values, benchmark_data),
            'tracking_error': self._calculate_te(portfolio_values, benchmark_data)
        } 