import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import logging
from typing import Optional, Dict, Union

class RiskFreeRateLoader:
    """无风险利率数据加载器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}  # 添加缓存过期时间
        self.cache_duration = timedelta(hours=1)  # 缓存时间为1小时
        self.logger = logging.getLogger(__name__)
        self.rate_types = {
            'shibor': 'SHIBOR',
            'treasury': '国债收益率',
            'repo': '银行间质押式回购利率'
        }
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache_expiry:
            return False
        return datetime.now() < self.cache_expiry[cache_key]
        
    def get_shibor_rate(self, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """获取SHIBOR利率数据"""
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
            cache_key = f"shibor_{start_date}_{end_date}"
            if cache_key in self.cache and self._is_cache_valid(cache_key):
                return self.cache[cache_key]
                
            try:
                # 获取不同期限的SHIBOR数据
                periods = {
                    'on': '隔夜',
                    '1w': '1周',
                    '2w': '2周',
                    '1m': '1月',
                    '3m': '3月',
                    '6m': '6月',
                    '9m': '9月',
                    '1y': '1年'
                }
                
                result_df = pd.DataFrame()
                
                for col, period in periods.items():
                    df = ak.rate_interbank(
                        market="上海银行同业拆借市场",
                        symbol="Shibor人民币",
                        indicator=period
                    )
                    
                    if not df.empty:
                        # 检查并获取日期列
                        date_col = None
                        for possible_col in ['日期', '报告日', 'date', '时间']:
                            if possible_col in df.columns:
                                date_col = possible_col
                                break
                                
                        rate_col = None
                        for possible_col in ['利率', 'rate', '收盘价', '值']:
                            if possible_col in df.columns:
                                rate_col = possible_col
                                break
                                
                        if date_col and rate_col:
                            if result_df.empty:
                                result_df['date'] = pd.to_datetime(df[date_col])
                            result_df[col] = pd.to_numeric(df[rate_col].str.replace('%', ''), errors='coerce') / 100
                        else:
                            self.logger.warning(f"无法找到日期或利率列: {df.columns.tolist()}")
                
                if result_df.empty:
                    self.logger.warning("获取到的SHIBOR数据为空")
                    return pd.DataFrame()
                
                # 过滤日期范围
                result_df = result_df[
                    (result_df['date'] >= pd.to_datetime(start_date)) & 
                    (result_df['date'] <= pd.to_datetime(end_date))
                ]
                
                # 按日期排序
                result_df = result_df.sort_values('date')
                
                # 更新缓存
                if not result_df.empty:
                    self.cache[cache_key] = result_df
                    self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
                
                return result_df
                
            except Exception as e:
                self.logger.error(f"SHIBOR API调用失败: {str(e)}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取SHIBOR数据失败: {str(e)}")
            return pd.DataFrame()
            
    def get_treasury_yield(self, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """获取国债收益率数据"""
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
            cache_key = f"treasury_{start_date}_{end_date}"
            if cache_key in self.cache and self._is_cache_valid(cache_key):
                return self.cache[cache_key]
                
            try:
                # 使用正确的API调用
                df = ak.bond_zh_us_rate(start_date=start_date.replace('-', ''))
                
                if df.empty:
                    self.logger.warning("获取到的国债收益率数据为空")
                    return pd.DataFrame()
                
                # 创建新的DataFrame以匹配所需格式
                result_df = pd.DataFrame()
                result_df['date'] = pd.to_datetime(df['日期'])
                
                # 构建所需的利率数据
                # 由于API没有3m和6m的数据，我们用2年期数据插值
                result_df['3m'] = df['中国国债收益率2年'] / 4  # 简单估算
                result_df['6m'] = df['中国国债收益率2年'] / 2  # 简单估算
                result_df['1y'] = df['中国国债收益率2年']  # 用2年期代替
                result_df['3y'] = df['中国国债收益率2年']
                result_df['5y'] = df['中国国债收益率5年']
                result_df['7y'] = (df['中国国债收益率5年'] + df['中国国债收益率10年']) / 2  # 插值
                result_df['10y'] = df['中国国债收益率10年']
                result_df['30y'] = df['中国国债收益率30年']
                
                # 过滤日期范围
                result_df = result_df[
                    (result_df['date'] >= pd.to_datetime(start_date)) & 
                    (result_df['date'] <= pd.to_datetime(end_date))
                ]
                
                # 确保所有利率列为数值类型
                rate_columns = ['3m', '6m', '1y', '3y', '5y', '7y', '10y', '30y']
                for col in rate_columns:
                    result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
                
                # 更新缓存
                if not result_df.empty:
                    self.cache[cache_key] = result_df
                    self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
                    
                return result_df
                
            except Exception as e:
                self.logger.error(f"国债收益率API调用失败: {str(e)}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取国债收益率数据失败: {str(e)}")
            return pd.DataFrame()
            
    def get_repo_rate(self,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """获取银行间质押式回购利率"""
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
            cache_key = f"repo_{start_date}_{end_date}"
            if cache_key in self.cache and self._is_cache_valid(cache_key):
                return self.cache[cache_key]
                
            try:
                # 使用正确的API调用
                df = ak.repo_rate_hist(start_date=start_date.replace('-', ''),
                                     end_date=end_date.replace('-', ''))
                
                if not df.empty:
                    df = self._process_repo_data(df)
                    self.cache[cache_key] = df
                    self.cache_expiry[cache_key] = datetime.now() + self.cache_duration
                    
                return df
                
            except Exception as e:
                self.logger.error(f"回购利率API调用失败: {str(e)}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"获取回购利率数据失败: {str(e)}")
            return pd.DataFrame()
            
    def get_current_rate(self, rate_type: str = 'shibor') -> float:
        """获取当前无风险利率（年化）
        
        Args:
            rate_type: 利率类型，可选 'shibor', 'treasury', 'repo'
            
        Returns:
            年化利率，如 0.0235 表示 2.35%
        """
        try:
            if rate_type not in self.rate_types:
                raise ValueError(f"不支持的利率类型: {rate_type}")
                
            df = None
            if rate_type == 'shibor':
                df = self.get_shibor_rate()
                if not df.empty:
                    # 使用3个月SHIBOR利率
                    return float(df.iloc[-1]['3m']) / 100
            elif rate_type == 'treasury':
                df = self.get_treasury_yield()
                if not df.empty:
                    # 使用1年期国债收益率
                    return float(df.iloc[-1]['1y']) / 100
            else:  # repo
                df = self.get_repo_rate()
                if not df.empty:
                    # 使用7天回购利率
                    return float(df.iloc[-1]['7d']) / 100
                    
            # 如果获取失败，返回默认值
            self.logger.warning(f"获取{self.rate_types[rate_type]}失败，使用默认值2%")
            return 0.02
            
        except Exception as e:
            self.logger.error(f"获取当前利率失败: {str(e)}")
            return 0.02
            
    def _process_shibor_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理SHIBOR数据"""
        try:
            # 检查数据是否为空
            if df.empty:
                return pd.DataFrame()
            
            # 检查列名
            self.logger.info(f"原始列名: {df.columns.tolist()}")
            
            # 重命名列 - 更新列名映射
            column_mapping = {
                '报告期': 'date',
                '隔夜': 'on',
                '1周': '1w',
                '2周': '2w',
                '1月': '1m',
                '3月': '3m',
                '6月': '6m',
                '9月': '9m',
                '1年': '1y',
                # 添加英文列名映射
                'date': 'date',
                'ON': 'on',
                '1W': '1w',
                '2W': '2w',
                '1M': '1m',
                '3M': '3m',
                '6M': '6m',
                '9M': '9m',
                '1Y': '1y'
            }
            
            # 重命名前先复制一份数据
            df = df.copy()
            
            # 重命名列
            df.columns = [column_mapping.get(col, col) for col in df.columns]
            
            # 确保必要的列存在
            required_columns = ['date', 'on', '1w', '2w', '1m', '3m', '6m', '9m', '1y']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.logger.error(f"缺少必要的列: {missing_columns}")
                return pd.DataFrame()
            
            # 转换日期列
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            # 转换利率列为数值类型
            rate_columns = ['on', '1w', '2w', '1m', '3m', '6m', '9m', '1y']
            for col in rate_columns:
                if col in df.columns:
                    # 处理百分比符号
                    if df[col].dtype == object:
                        df[col] = df[col].str.replace('%', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.error(f"处理SHIBOR数据失败: {str(e)}")
            return pd.DataFrame()
            
    def _process_treasury_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理国债收益率数据"""
        try:
            if df.empty:
                return pd.DataFrame()
            
            # 检查列名
            self.logger.info(f"原始国债收益率数据列名: {df.columns.tolist()}")
            
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '收盘': 'close',
                '3月期': '3m',
                '6月期': '6m',
                '1年期': '1y',
                '3年期': '3y',
                '5年期': '5y',
                '7年期': '7y',
                '10年期': '10y',
                '30年期': '30y'
            }
            df = df.rename(columns=column_mapping)
            
            # 转换日期列
            df['date'] = pd.to_datetime(df['date'])
            
            # 转换利率列为数值类型
            rate_columns = ['3m', '6m', '1y', '3y', '5y', '7y', '10y', '30y']
            for col in rate_columns:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].str.replace('%', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            self.logger.error(f"处理国债收益率数据失败: {str(e)}")
            return pd.DataFrame()
            
    def _process_repo_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理回购利率数据"""
        try:
            # 重命名列
            column_mapping = {
                '日期': 'date',
                '隔夜': 'on',
                '7天': '7d',
                '14天': '14d',
                '1月': '1m',
                '3月': '3m',
                '6月': '6m',
                '9月': '9m'
            }
            df = df.rename(columns=column_mapping)
            
            # 转换日期列
            df['date'] = pd.to_datetime(df['date'])
            
            # 转换利率列为数值类型
            rate_columns = ['on', '7d', '14d', '1m', '3m', '6m', '9m']
            for col in rate_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].str.replace('%', ''), errors='coerce')
                
            return df
            
        except Exception as e:
            self.logger.error(f"处理回购利率数据失败: {str(e)}")
            return pd.DataFrame()