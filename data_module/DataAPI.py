import functools

class DataAPI:
    def __init__(self):
        # ... (初始化代码)

    def get_funds_history_batch(self, fund_codes, start_date, end_date):
        """批量获取多个基金的历史数据 (示例，需要根据你的数据源API调整)"""
        batch_data = {}
        # 构建批量请求参数 (假设数据源API接受 fund_codes 列表)
        params = {
            "fund_codes": fund_codes,
            "start_date": start_date,
            "end_date": end_date
        }
        # 调用数据源API批量获取数据 (示例，需要替换为你的实际API请求代码)
        response = self.data_source_api.fetch_batch_history(params)
        if response.status_code == 200:
            batch_raw_data = response.json()
            # 处理批量数据，将数据按 fund_code 组织到 batch_data 字典中
            for raw_fund_data in batch_raw_data: # 假设数据源返回的是基金数据列表
                fund_code = raw_fund_data["fund_code"]
                history_data = self.process_raw_data(raw_fund_data) # 处理原始数据
                batch_data[fund_code] = history_data
            return batch_data
        else:
            raise Exception(f"批量获取基金历史数据失败: {response.status_code}")

    @functools.lru_cache(maxsize=128) # 将缓存装饰器应用到 get_fund_history 函数
    def get_fund_history(self, fund_code, start_date, end_date):
        """获取基金历史数据 (已添加缓存)"""
        # ... (数据获取代码)
        # ...
        return history_data

    @functools.lru_cache(maxsize=128) # 添加 lru_cache 装饰器，设置缓存大小
    def get_fund_history_old(self, fund_code, start_date, end_date):
        """获取基金历史数据 (已添加缓存)"""
        # ... (数据获取代码)
        # 在函数内部，如果缓存命中，直接返回缓存结果，否则执行数据获取逻辑，并将结果存入缓存
        # ...
        return history_data 