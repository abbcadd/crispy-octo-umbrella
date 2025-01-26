import akshare as ak
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Union
from datetime import datetime, timedelta
import logging

class MarketDataLoader:
    """市场行情数据加载器 - 专注基金投资相关的市场指标"""
    
    def __init__(self):
        self.cache = {}
        self.logger = logging.getLogger(__name__)
        
        # 主要指数代码映射
        self.major_indices = {
            '000300': '沪深300',  # 大盘股指数
            '000905': '中证500',  # 中盘股指数
            '000852': '中证1000',  # 小盘股指数
            'h11001': '中债总指数',  # 债券指数
            'h11006': '中债信用债指数',  # 信用债指数
            '000688': '科创50',   # 科技成长
            '000922': '中证红利' # 价值指数
        }
        
    def get_index_data(self, index_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指数数据"""
        try:
            # 如果未指定日期，使用过去90天
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
                
            # 尝试从缓存获取数据
            cache_key = f"{index_code}_{start_date}_{end_date}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # 根据指数代码类型选择不同的API
            if index_code in ['h11001', 'h11006']:  # 债券指数
                try:
                    df = ak.bond_zh_hs_daily(symbol=index_code)
                except:
                    self.logger.error(f"获取债券指数{index_code}数据失败")
                    return pd.DataFrame()
            else:  # 股票指数
                # 确保指数代码格式正确
                clean_code = ''.join(filter(str.isdigit, index_code))
                
                if not clean_code:
                    self.logger.error(f"无效的指数代码: {index_code}")
                    return pd.DataFrame()
                    
                try:
                    # 使用新的API
                    df = ak.index_zh_a_hist(
                        symbol=clean_code,
                        period="daily",
                        start_date=start_date.replace('-', ''),
                        end_date=end_date.replace('-', '')
                    )
                except Exception as e:
                    self.logger.error(f"获取指数数据失败: {str(e)}")
                    return pd.DataFrame()
            
            # 处理数据
            if not df.empty:
                df = self._process_market_data(df)
                
                # 更新缓存
                self.cache[cache_key] = df
                
            return df
            
        except Exception as e:
            self.logger.error(f"获取指数数据失败: {str(e)}")
            return pd.DataFrame()

    def get_market_status(self) -> dict:
        """获取市场状态"""
        try:
            # 获取沪深300最近数据
            df = self.get_index_data('000300')
            
            if df.empty:
                self.logger.warning("无法获取沪深300数据")
                return {
                    'market_trend': 'unknown',
                    'risk_level': 'unknown',
                    'style_rotation': 'unknown',
                    'indices_change': {}
                }
            
            # 确保至少有20天的数据
            if len(df) < 20:
                self.logger.warning("数据量不足20天")
                return {
                    'market_trend': 'unknown',
                    'risk_level': 'unknown',
                    'style_rotation': 'unknown',
                    'indices_change': {}
                }
            
            # 计算市场趋势
            recent_change = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100
            daily_change = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
            
            # 获取风险水平
            current_vol = df['rolling_vol'].iloc[-1]
            avg_vol = df['rolling_vol'].mean()
            risk_level = 'high' if current_vol > avg_vol * 1.2 else 'normal' if current_vol > avg_vol * 0.8 else 'low'
            
            # 获取风格轮动
            style_rotation = self._analyze_style_rotation()
            
            # 构建市场状态字典
            status = {
                'market_trend': self._get_trend_description(recent_change),
                'risk_level': risk_level,
                'style_rotation': style_rotation,
                'indices_change': {
                    '沪深300': {
                        'daily_change': round(daily_change, 2),
                        'volatility': round(float(current_vol) * 100, 2),  # 转换为百分比
                        'momentum': round(float(recent_change), 2)
                    }
                }
            }
            return status
            
        except Exception as e:
            self.logger.error(f"获取市场状态失败: {str(e)}")
            return {
                'market_trend': 'unknown',
                'risk_level': 'unknown',
                'style_rotation': 'unknown',
                'indices_change': {}
            }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        try:
            if df.empty:
                return df
            
            # 确保数据类型正确
            for col in ['open', 'close', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 处理缺失值 - 使用新的方法替代弃用的方法
            df = df.ffill().bfill()
            
            # 计算日收益率
            df['daily_return'] = df['close'].pct_change()
            
            # 计算移动平均线
            for period in [5, 10, 20, 60]:
                df[f'ma{period}'] = df['close'].rolling(window=period, min_periods=1).mean()
            
            # 计算波动率（20日）
            df['rolling_vol'] = df['daily_return'].rolling(window=20, min_periods=1).std() * np.sqrt(252)
            
            # 计算RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14, min_periods=1).mean()
            avg_loss = loss.rolling(window=14, min_periods=1).mean()
            rs = avg_gain / avg_loss.replace(0, np.inf)  # 避免除以零
            df['rsi'] = 100 - (100 / (1 + rs))
            df['rsi'] = df['rsi'].fillna(50)  # 填充NaN值为中性值50
            df['rsi'] = df['rsi'].clip(0, 100)  # 确保RSI在0-100之间
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = exp1 - exp2
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df = df.ffill().fillna(0)
            
            return df
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {str(e)}")
            return df

    def _analyze_style_rotation(self) -> str:
        """分析市场风格轮动"""
        try:
            # 获取大盘和小盘指数数据
            hs300 = self.get_index_data('000300')
            zz1000 = self.get_index_data('000852')
            
            if hs300.empty or zz1000.empty:
                return 'unknown'
            
            # 计算最近20天的相对强度
            hs300_return = hs300['close'].iloc[-1] / hs300['close'].iloc[-20] - 1
            zz1000_return = zz1000['close'].iloc[-1] / zz1000['close'].iloc[-20] - 1
            
            # 计算成长股和价值股的表现
            growth_idx = self.get_index_data('000688')  # 科创50
            value_idx = self.get_index_data('000922')   # 中证红利
            
            if not growth_idx.empty and not value_idx.empty:
                growth_return = growth_idx['close'].iloc[-1] / growth_idx['close'].iloc[-20] - 1
                value_return = value_idx['close'].iloc[-1] / value_idx['close'].iloc[-20] - 1
                
                # 综合判断市场风格
                if growth_return > value_return and hs300_return > zz1000_return:
                    return 'large_growth'
                elif growth_return > value_return and hs300_return <= zz1000_return:
                    return 'small_growth'
                elif growth_return <= value_return and hs300_return > zz1000_return:
                    return 'large_value'
                else:
                    return 'small_value'
            else:
                # 仅基于大小盘判断
                if hs300_return > zz1000_return:
                    return 'large_cap'
                else:
                    return 'small_cap'
                
        except Exception as e:
            self.logger.error(f"风格轮动分析失败: {str(e)}")
            return 'unknown'

    def _get_trend_description(self, change: float) -> str:
        """根据涨跌幅获取趋势描述"""
        if change > 10:
            return 'strong_upward'
        elif change > 5:
            return 'upward'
        elif change > -5:
            return 'sideways'
        elif change > -10:
            return 'downward'
        else:
            return 'strong_downward'

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理异常值"""
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                # 使用3倍标准差法则检测异常值
                mean = df[col].mean()
                std = df[col].std()
                df[col] = df[col].clip(mean - 3*std, mean + 3*std)
        return df

    def _handle_api_error(self, error: Exception, index_code: str, retry_times: int = 3) -> pd.DataFrame:
        """处理API调用异常，支持自动重试"""
        self.logger.error(f"获取指数{index_code}数据失败: {str(error)}")
        
        for i in range(retry_times):
            try:
                self.logger.info(f"第{i+1}次重试获取指数{index_code}数据")
                
                # 根据指数代码选择不同的API
                if index_code.startswith('h'):  # 债券指数
                    df = ak.bond_zh_hs_daily(symbol=index_code)
                else:  # 股票指数
                    # 确保指数代码格式正确
                    clean_code = ''.join(filter(str.isdigit, index_code))
                    
                    if not clean_code:
                        self.logger.error(f"无效的指数代码: {index_code}")
                        return pd.DataFrame()
                        
                    # 添加日期参数
                    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
                    end_date = datetime.now().strftime('%Y%m%d')
                    
                    try:
                        df = ak.index_zh_a_hist(
                            symbol=clean_code,
                            start_date=start_date,
                            end_date=end_date
                        )
                    except:
                        # 如果主API失败，尝试备用API
                        df = ak.stock_zh_index_daily_tx(symbol=clean_code)
                
                if df is not None and not df.empty:
                    return self._calculate_indicators(df)
                
                self.logger.warning(f"第{i+1}次获取数据为空，将重试")
                
            except Exception as e:
                self.logger.error(f"重试失败: {str(e)}")
                continue
                
        return pd.DataFrame()

    def _process_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗和标准化"""
        if df.empty:
            return df
        
        try:
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change',
                '换手率': 'turnover',
                'date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'volume': 'volume',
                '收盘价': 'close',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '成交量(手)': 'volume'
            }
            
            # 检查并重命名列
            df.columns = [column_mapping.get(col, col) for col in df.columns]
            
            # 确保必要的列存在
            required_columns = ['date', 'open', 'close', 'high', 'low']
            if not all(col in df.columns for col in required_columns):
                self.logger.error(f"数据缺少必要的列: {required_columns}")
                return pd.DataFrame()
            
            # 确保日期列为datetime类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 确保数值列为float类型并处理异常值
            numeric_columns = ['open', 'close', 'high', 'low', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    # 移除任何非数值字符
                    if df[col].dtype == object:
                        df[col] = df[col].str.replace('[^\d.]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 处理异常值
            df = self._handle_outliers(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"数据处理失败: {str(e)}")
            return pd.DataFrame()

    def _process_market_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理市场数据"""
        try:
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change',
                '换手率': 'turnover',
                # 添加备用API的列名映射
                'date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'volume': 'volume',
                # 添加债券指数的列名映射
                '收盘价': 'close',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '成交量(手)': 'volume'
            }
            
            # 检查并重命名列
            df.columns = [column_mapping.get(col, col) for col in df.columns]
            
            # 确保必要的列存在
            required_columns = ['date', 'open', 'close', 'high', 'low']
            if not all(col in df.columns for col in required_columns):
                self.logger.error(f"数据缺少必要的列: {required_columns}")
                return pd.DataFrame()
            
            # 确保日期列为datetime类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 确保数值列为float类型并处理异常值
            numeric_columns = ['open', 'close', 'high', 'low', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    # 移除任何非数值字符
                    if df[col].dtype == object:
                        df[col] = df[col].str.replace('[^\d.]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 计算技术指标
            df = self._calculate_indicators(df)
            
            # 按日期排序
            df = df.sort_values('date')
            
            return df
            
        except Exception as e:
            self.logger.error(f"处理市场数据失败: {str(e)}")
            return pd.DataFrame()