import akshare as ak  # 金融数据接口库
import pandas as pd  # 数据分析库
import logging # 日志记录
import re
from typing import Optional
from datetime import datetime, timedelta


class FundLoader:
    """加载基金数据"""
    def __init__(self):
        self.logger = logging.getLogger(__name__) # 初始化日志记录器
        self.cache = {}
        self.cache_expiry = timedelta(hours=1)  # 缓存有效期为1小时
    
    def get_fund_list(self, fund_type: Optional[str] = None) -> list:
        """获取基金列表（带缓存）"""
        cache_key = f"fund_list_{fund_type}"
        if cache_key in self.cache and datetime.now() - self.cache[cache_key]['timestamp'] < self.cache_expiry:
            return self.cache[cache_key]['data']

        try:
            # 确保 fund_type 是有效的字符串或 None
            if fund_type is not None and not isinstance(fund_type, str):
                raise ValueError("fund_type 必须是字符串或 None")
            
            # 根据 fund_type 获取基金列表
            if fund_type:
                # 假设我们有一个根据基金类型过滤的逻辑
                funds = self._fetch_funds_by_type(fund_type)
            else:
                # 获取所有基金
                funds = self._fetch_all_funds()
            
            # 更新缓存
            self.cache[cache_key] = {'data': funds, 'timestamp': datetime.now()}
            return funds
        
        except Exception as e:
            self.logger.error(f"获取基金列表失败: {str(e)}")
            raise

    def get_fund_info(self, fund_code: str) -> dict:
        """获取基金基本信息

        Args:
            fund_code (str): 基金代码

        Returns:
            dict: 基本信息
        """
        try:
            info = ak.fund_individual_basic_info_xq(fund_code)
            return{
                'fund_code': info.value[0],
                'fund_name': info.value[1],
                'fund_type': info.value[8],
                'establishment_date': info.value[3],
                'size': info.value[4],
                'manager': info.value[6],
                'company': info.value[5],
                'benchmark': info.value[13]
            }
        except Exception as e:
            self.logger.error(f"获取基金{fund_code}信息失败:{str(e)}")
            return {}
        

    def get_fund_nav(self, fund_code: str,
                    start_date: str = None,
                    end_date: str = None) -> pd.DataFrame:
        """获取基金一段时间内的净值数据

        Args:
            fund_code (str): 基金代码
            start_date (str, optional): 开始时间. Defaults to None.
            end_date (str, optional): 结束时间. Defaults to None.

        Returns:
            pd.DataFrame: 基金净值数据，包含 '净值日期', '单位净值', '累计净值' 等列
        """
        try:
            # 添加重试机制
            for retry in range(3):
                try:
                    # 获取单位净值数据
                    nav_data_unit = ak.fund_open_fund_info_em(fund_code, '单位净值走势')
                    if not isinstance(nav_data_unit, pd.DataFrame):
                        raise ValueError("获取到的单位净值数据格式不正确")
                        
                    # 获取累计净值数据
                    nav_data_cumulative = ak.fund_open_fund_info_em(fund_code, '累计净值走势')
                    if not isinstance(nav_data_cumulative, pd.DataFrame):
                        raise ValueError("获取到的累计净值数据格式不正确")
                        
                    # 合并数据
                    nav_data = pd.merge(nav_data_unit, nav_data_cumulative, 
                                      on='净值日期', suffixes=('', '_累计'))
                    
                    # 重命名列
                    nav_data = nav_data.rename(columns={
                        '净值日期': 'date',
                        '单位净值': 'nav',
                        '累计净值': 'cumulative_nav'
                    })
                    
                    # 转换日期格式
                    nav_data['date'] = pd.to_datetime(nav_data['date'])
                    
                    # 确保数值列为float类型
                    nav_data['nav'] = pd.to_numeric(nav_data['nav'], errors='coerce')
                    nav_data['cumulative_nav'] = pd.to_numeric(nav_data['cumulative_nav'], errors='coerce')
                    
                    # 过滤日期范围
                    if start_date and end_date:
                        nav_data = nav_data[
                            (nav_data['date'] >= pd.to_datetime(start_date)) &
                            (nav_data['date'] <= pd.to_datetime(end_date))
                        ]
                    
                    # 按日期排序
                    nav_data = nav_data.sort_values('date')
                    
                    return nav_data
                    
                except Exception as e:
                    if 'html' in str(e).lower() or 'unexpected token' in str(e).lower():
                        self.logger.warning(f"第{retry + 1}次获取基金{fund_code}数据失败，可能是网络问题，将重试")
                        continue
                    else:
                        raise e
                        
            self.logger.error(f"获取基金{fund_code}数据失败，已重试{retry + 1}次")
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"获取基金{fund_code}失败：{str(e)}")
            return pd.DataFrame()
        

    def get_fund_portfolio(self, fund_code: str, time: str) -> dict:
        """获取某一年的持仓数据
        比率返回的时占基金市值比率,可能存在大于1的情况
        Args:
            fund_code (str): 基金代码

        Returns:
            dict: 持仓数据
        """
        try:
            portfoilo_bond = ak.fund_portfolio_bond_hold_em(fund_code, time)
            portfoilo_industry = ak.fund_portfolio_industry_allocation_em(fund_code, time)
            portfoilo_stock = ak.fund_portfolio_hold_em(fund_code, time)
            return{
                'fund_code' : fund_code,
                'report_date': time, 
                'stock_ratio' : portfoilo_stock['占净值比例'].sum(),
                'bond_ratio' : portfoilo_bond['占净值比例'].sum(),
                'top_ten_stock' : list(portfoilo_stock['股票名称'][:10]),
                'top_three_industry' : [list(portfoilo_industry[:3]['行业类别']), list(portfoilo_industry[:3]['占净值比例'])]
                }
        except Exception as e:
            self.logger.error(f'获取基金{fund_code}失败：{str(e)}')
            return {}
        
    def get_fund_fee(self, fund_code: str) -> dict:
        """获取基金费率信息
        
        Args:
            fund_code (str): 基金代码
            
        Returns:
            dict: 包含各类费率的字典
        """
        fee_dict = {
            "管理费率": 0.0,
            "托管费率": 0.0,
            "销售服务费率": 0.0,
            "申购费率": {
                "原费率": 0.0,
                "优惠费率": 0.0
            },
            "赎回费率": 0.0
        }
        
        try:
            # 获取运作费用
            operation_fee = ak.fund_fee_em(symbol=fund_code, indicator="运作费用")
            if not operation_fee.empty:
                fee_dict["管理费率"] = self._parse_percentage(operation_fee.iloc[0]["管理费率"])
                fee_dict["托管费率"] = self._parse_percentage(operation_fee.iloc[0]["托管费率"])
                fee_dict["销售服务费率"] = self._parse_percentage(operation_fee.iloc[0]["销售服务费率"])
                
            # 获取申购费率
            purchase_fee = ak.fund_fee_em(symbol=fund_code, indicator="申购费率")
            if not purchase_fee.empty:
                # 获取小额投资的费率（通常是第一行）
                fee_dict["申购费率"]["原费率"] = self._parse_percentage(purchase_fee.iloc[0]["原费率"])
                fee_dict["申购费率"]["优惠费率"] = self._parse_percentage(purchase_fee.iloc[0]["天天基金优惠费率"])
                
            # 获取赎回费率
            redemption_fee = ak.fund_fee_em(symbol=fund_code, indicator="赎回费率")
            if not redemption_fee.empty:
                fee_dict["赎回费率"] = self._parse_percentage(redemption_fee.iloc[0]["费率"])
                
            return fee_dict
            
        except Exception as e:
            self.logger.error(f"获取基金{fund_code}费率失败：{str(e)}")
            return fee_dict
        
    def _fetch_all_funds(self) -> list:
        """获取所有基金列表"""
        try:
            fund_list = ak.fund_name_em()
            if not fund_list.empty:
                # 过滤无效基金代码
                valid_funds = fund_list[fund_list['基金代码'].str.match(r'^\d{6}$')]  # 确保基金代码为6位数字
                return valid_funds['基金代码'].tolist()
            else:
                self.logger.warning("获取到的基金列表为空")
                return []
        except Exception as e:
            self.logger.error(f"获取所有基金列表失败: {str(e)}")
            raise

    def _fetch_funds_by_type(self, fund_type: str) -> list:
        """根据基金类型获取基金列表"""
        try:
            # 使用 akshare 获取所有基金数据
            fund_list = ak.fund_name_em()
            if not fund_list.empty:
                # 检查列名，确保 '基金类型' 列存在
                if '基金类型' not in fund_list.columns:
                    # 如果列名不同，尝试其他可能的列名
                    possible_columns = ['基金类型', 'type', 'fund_type']
                    for col in possible_columns:
                        if col in fund_list.columns:
                            # 根据基金类型过滤
                            filtered_funds = fund_list[fund_list[col] == fund_type]
                            if not filtered_funds.empty:
                                # 返回基金代码列表
                                return filtered_funds['基金代码'].tolist()
                            else:
                                self.logger.warning(f"没有找到类型为 {fund_type} 的基金")
                                return []
                    raise KeyError("无法找到基金类型列")
                else:
                    # 根据基金类型过滤
                    filtered_funds = fund_list[fund_list['基金类型'] == fund_type]
                    if not filtered_funds.empty:
                        # 返回基金代码列表
                        return filtered_funds['基金代码'].tolist()
                    else:
                        self.logger.warning(f"没有找到类型为 {fund_type} 的基金")
                        return []
            else:
                self.logger.warning("获取到的基金列表为空")
                return []
        except Exception as e:
            self.logger.error(f"根据类型获取基金列表失败: {str(e)}")
            raise
        