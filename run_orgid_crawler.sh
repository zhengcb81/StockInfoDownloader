#!/bin/bash

# 巨潮资讯网组织ID爬虫启动脚本
# 作者: Manus
# 日期: 2025-05-17

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查必要的Python包
echo "检查必要的Python包..."
python3 -c "import selenium" 2>/dev/null || {
    echo "安装selenium包..."
    pip3 install selenium
}

# 检查Chrome WebDriver
echo "检查Chrome WebDriver..."
if ! command -v chromedriver &> /dev/null; then
    echo "警告: 未找到chromedriver，可能需要手动安装"
    echo "请访问 https://chromedriver.chromium.org/downloads 下载与您的Chrome浏览器版本匹配的WebDriver"
fi

# 检查参数
if [ $# -lt 1 ]; then
    echo "使用方法: $0 [选项]"
    echo "选项:"
    echo "  --output <文件路径>     输出文件路径，默认为stock_orgid_mapping.json"
    echo "  --start <索引>         起始索引，默认为0"
    echo "  --end <索引>           结束索引，默认为1000"
    echo "  --batch-size <数量>    每批处理的股票数量，默认为10"
    echo "  --save-interval <数量> 保存间隔，默认为10"
    echo "  --headless             使用无头模式"
    echo "  --debug                启用调试模式"
    exit 1
fi

echo "开始爬取A股股票代码对应的组织ID..."

# 运行Python脚本
python3 orgid_crawler.py "$@"

echo "爬取完成"
