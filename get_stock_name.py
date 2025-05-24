import requests
import os
import json

def get_stock_name(stock_code, mapping_file='stock_orgid_mapping.json'):
    """
    通过股票代码查询A股股票名称，优先查本地映射表，查不到再用腾讯财经接口。
    参数：
        stock_code (str): 6位数字股票代码（如："600000"）
        mapping_file (str): 本地映射表文件路径，默认'stock_orgid_mapping.json'
    返回：
        str: 股票名称，若查询失败返回错误信息
    """
    # 清洗输入数据
    code = str(stock_code).strip()
    
    # 验证输入有效性
    if not code.isdigit() or len(code) != 6:
        return "错误：请输入6位数字股票代码"
    
    # 1. 优先查本地映射表
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            if code in mapping and 'name' in mapping[code]:
                return mapping[code]['name']
        except Exception:
            pass
    
    # 2. 查不到再用腾讯财经接口
    exchange = 'sh' if code.startswith(('6', '5', '9')) else 'sz'
    
    # 构造请求URL
    url = f'https://qt.gtimg.cn/q={exchange}{code}'
    
    try:
        # 添加headers模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'  # 腾讯接口使用GBK编码
        
        # 解析返回数据
        data = response.text
        parts = data.split('~')
        
        if len(parts) > 1 and parts[1]:
            return parts[1]
        else:
            return "错误：股票代码不存在"
        
    except requests.exceptions.RequestException as e:
        return f"网络请求失败：{str(e)}"
    except Exception as e:
        return f"发生错误：{str(e)}"