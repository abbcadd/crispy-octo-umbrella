from typing import Generator
from data_module import DataAPI
from strategy.portfolio_opt import PortfolioOptimizer
from strategy.risk_model import RiskModel
from backtest.simulator import BacktestSimulator

def get_data_api() -> Generator:
    """获取数据API实例"""
    data_api = DataAPI()
    try:
        yield data_api
    finally:
        pass

def get_optimizer() -> Generator:
    """获取优化器实例"""
    optimizer = PortfolioOptimizer()
    try:
        yield optimizer
    finally:
        pass

def get_risk_model() -> Generator:
    """获取风险模型实例"""
    risk_model = RiskModel()
    try:
        yield risk_model
    finally:
        pass

def get_simulator() -> Generator:
    """获取回测模拟器实例"""
    simulator = BacktestSimulator()
    try:
        yield simulator
    finally:
        pass 