# 巨潮资讯网投资者关系活动记录表下载工具

## 项目概述

本项目提供了一套完整的工具，用于自动下载巨潮资讯网上的投资者关系活动记录表PDF文件。该工具包含两个主要组件：

1. **组织ID爬虫**：自动遍历A股股票代码，获取每个股票对应的组织ID，并生成映射表
2. **PDF下载器**：根据股票代码和组织ID，自动下载投资者关系活动记录表PDF文件

## 功能特点

- 自动获取股票代码对应的组织ID
- 支持多种提取策略，最大化获取成功率
- 自动下载投资者关系活动记录表PDF文件
- 支持日期范围筛选和多种配置选项
- 完整的错误处理和日志记录

## 安装要求

- Python 3.6+
- 必要的Python库：
  - requests
  - beautifulsoup4
  - selenium (用于组织ID爬虫)
- Chrome浏览器和ChromeDriver (用于组织ID爬虫)

安装依赖：

```bash
pip install requests beautifulsoup4 selenium
```

## 使用说明

### 1. 组织ID爬虫

首先运行组织ID爬虫，生成股票代码与组织ID的映射表：

```bash
python orgid_crawler.py [选项]
```

**选项**：
- `--output <文件路径>` - 指定输出文件路径，默认为`stock_orgid_mapping.json`
- `--start <索引>` - 起始索引，默认为0
- `--end <索引>` - 结束索引，默认为1000
- `--batch-size <数量>` - 每批处理的股票数量，默认为10
- `--save-interval <数量>` - 保存间隔，默认为10
- `--headless` - 使用无头模式
- `--debug` - 启用调试模式
- `--test` - 测试模式，只处理一个股票代码
- `--stock-code <代码>` - 指定要处理的股票代码，仅在测试模式下有效

**示例**：

```bash
# 测试模式，处理单个股票代码
python orgid_crawler.py --test --stock-code 300010 --debug

# 批量处理前100只股票
python orgid_crawler.py --start 0 --end 100 --batch-size 10 --save-interval 10
```

### 2. PDF下载器

使用PDF下载器下载投资者关系活动记录表：

```bash
python cninfo_activity_downloader.py --stock-code <股票代码> [选项]
```

**选项**：
- `--stock-code <代码>` - 股票代码（必需）
- `--org-id <ID>` - 组织ID，如果不提供则自动获取
- `--save-dir <目录>` - 指定保存文件的目录，默认为`downloads`
- `--mapping-file <文件路径>` - 股票代码与组织ID的映射文件，默认为`stock_orgid_mapping.json`
- `--start-date <日期>` - 开始日期，格式为yyyy-MM-dd
- `--end-date <日期>` - 结束日期，格式为yyyy-MM-dd
- `--max-pages <页数>` - 最大查询页数，默认为10
- `--debug` - 启用调试模式

**示例**：

```bash
# 下载特定股票的投资者关系活动记录表
python cninfo_activity_downloader.py --stock-code 300010

# 指定日期范围和组织ID
python cninfo_activity_downloader.py --stock-code 300010 --org-id 9900008267 --start-date 2024-01-01 --end-date 2025-05-17
```

### 3. 使用Shell脚本

为了方便使用，项目提供了两个Shell脚本：

```bash
# 运行组织ID爬虫
./run_orgid_crawler.sh [股票代码] [选项]

# 运行PDF下载器
./run_cninfo_downloader.sh [股票代码] [选项]
```

## 注意事项

1. **组织ID爬虫需要在本地环境运行**：由于需要使用Chrome浏览器和WebDriver，组织ID爬虫需要在本地具备完整GUI或无头浏览器支持的环境下运行。

2. **获取组织ID的方法**：如果自动获取组织ID失败，您可以通过以下方式手动获取：
   - 在巨潮资讯网搜索该股票
   - 在URL中找到"orgId=xxxxxxxxx"参数
   - 使用`--org-id`参数传递给下载器

3. **投资者关系活动记录表的可用性**：并非所有公司都有公开的投资者关系活动记录表，某些股票可能查询不到相关记录。

4. **API限制**：巨潮资讯网可能有API访问频率限制，如果遇到访问被拒绝的情况，请适当增加请求间隔。

## 故障排除

1. **无法初始化WebDriver**：
   - 确保已安装Chrome浏览器和对应版本的ChromeDriver
   - 检查ChromeDriver是否在系统PATH中
   - 尝试使用`--headless`选项

2. **无法获取组织ID**：
   - 使用`--debug`选项查看详细日志
   - 尝试手动获取组织ID并使用`--org-id`参数

3. **无法下载PDF文件**：
   - 检查网络连接
   - 确认该公司是否有投资者关系活动记录表
   - 尝试调整日期范围
   - 使用`--debug`选项查看详细日志

## 文件说明

- `orgid_crawler.py` - 组织ID爬虫主程序
- `cninfo_activity_downloader.py` - PDF下载器主程序
- `run_orgid_crawler.sh` - 组织ID爬虫启动脚本
- `run_cninfo_downloader.sh` - PDF下载器启动脚本
- `stock_orgid_mapping.json` - 股票代码与组织ID的映射文件（运行爬虫后生成）
- `README.md` - 使用说明文档

## 开发者信息

本工具由Manus开发，用于自动化获取A股上市公司的投资者关系活动记录表。

如有任何问题或建议，请随时提出。

## 组织ID查找API（orgid_utils.py）

本项目提供了统一的API函数`get_org_id_by_code`用于根据证券代码获取巨潮资讯网组织ID，便于在各类脚本和模块中调用。

### 用法

```python
from orgid_utils import get_org_id_by_code

org_id = get_org_id_by_code('300010')
print(org_id)
```

### 参数说明
- `stock_code` (str): 证券代码，如'300010'。
- `force_run` (bool, 可选): 是否强制重新爬取org id，默认False。若为True则无视本地映射表，直接爬取。
- `mapping_file` (str, 可选): 映射表文件路径，默认'stock_orgid_mapping.json'。
- `headless` (bool, 可选): 是否无头模式运行浏览器，默认True。

### 返回值
- 返回org id字符串，若获取失败则返回None。

### 典型场景
- 推荐在下载器、批量数据处理等脚本中直接调用该API，无需关心底层爬虫细节。
