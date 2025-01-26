from data_module import DataAPI
from strategy.portfolio_opt import PortfolioOptimizer
from strategy.risk_model import RiskModel
from backtest.simulator import BacktestSimulator
from visualization.efficient_frontier import EfficientFrontier
import logging
import matplotlib
matplotlib.use('TkAgg')  # 在导入 pyplot 之前设置后端
import matplotlib.pyplot as plt

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """主程序入口"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 初始化各个模块
    data_api = DataAPI()
    optimizer = PortfolioOptimizer()
    risk_model = RiskModel()
    simulator = BacktestSimulator()
    ef_viz = EfficientFrontier()
    
    # 设置基金池
    fund_pool = [
        '110011',  # 易方达中小盘混合
        '163406',  # 兴全合润混合
        '519697'   # 交银优势行业混合
    ]
    
    try:
        # 1. 获取基金数据
        logger.info("正在获取基金数据...")
        fund_info_list = []
        for fund_code in fund_pool:
            fund_info = data_api.get_fund_info(fund_code)
            if fund_info:
                fund_info_list.append(fund_info)
                logger.info(f"基金 {fund_code} 信息: {fund_info}")
            else:
                logger.warning(f"无法获取基金 {fund_code} 的信息")
        
        if not fund_info_list:
            raise ValueError("无法获取任何基金信息")
        
        # 2. 执行投资组合优化
        logger.info("正在执行投资组合优化...")
        opt_result = optimizer.optimize(
            fund_codes=fund_pool,
            method='mean_variance',
            risk_aversion=2.0
        )
        
        if not opt_result:
            raise ValueError("投资组合优化失败")
            
        logger.info(f"优化结果: {opt_result}")
        
        # 3. 计算风险指标
        logger.info("正在计算风险指标...")
        risk_metrics = risk_model.calculate_risk_metrics(opt_result['weights'])
        logger.info(f"风险指标: {risk_metrics}")
        
        # 4. 执行回测
        logger.info("正在执行回测...")
        backtest_results = simulator.run_backtest(
            fund_pool=fund_pool,
            start_date='2023-01-01',
            end_date='2023-12-31',
            strategy_params={'method': 'mean_variance'}
        )
        
        if backtest_results and 'performance' in backtest_results:
            logger.info(f"回测结果: {backtest_results['performance']}")
        else:
            logger.warning("回测未能生成有效结果")
        
        # 5. 绘制可视化图表
        if opt_result and 'weights' in opt_result:
            logger.info("正在生成可视化图表...")
            try:
                plt.switch_backend('TkAgg')
                ef_viz.plot_efficient_frontier(fund_pool)
                plt.show()
                ef_viz.plot_portfolio_composition(opt_result['weights'])
                plt.show()
            except Exception as viz_error:
                logger.error(f"可视化生成失败: {str(viz_error)}")
        
        # 优化结果展示
        if opt_result and 'weights' in opt_result:
            logger.info("\n投资组合配置:")
            for fund_code, weight in opt_result['weights'].items():
                fund_info = data_api.get_fund_info(fund_code)
                logger.info(f"{fund_info['fund_name']}({fund_code}): {weight*100:.2f}%")
            
            logger.info("\n组合统计:")
            for metric, value in opt_result['stats'].items():
                logger.info(f"{metric}: {value:.2f}")

        # 回测结果展示
        if backtest_results:
            logger.info("\n回测表现:")
            for metric, value in backtest_results['performance'].items():
                if isinstance(value, float):
                    logger.info(f"{metric}: {value:.2f}%")
                else:
                    logger.info(f"{metric}: {value}")
        
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        raise  # 重新抛出异常，以便查看完整的错误堆栈

if __name__ == "__main__":
    main() 