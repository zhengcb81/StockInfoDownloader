#!/bin/bash

# 巨潮资讯网投资者关系活动记录表下载器启动脚本
# 作者: Manus
# 日期: 2025-05-17

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查必要的Python包
echo "检查必要的Python包..."
python3 -c "import requests" 2>/dev/null || {
    echo "安装requests包..."
    pip3 install requests
}

# 检查参数
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <股票代码> [选项]"
    echo "选项:"
    echo "  --org-id <组织ID>       股票对应的组织ID，优先使用"
    echo "  --save-dir <目录>       保存文件的目录"
    echo "  --start-date <日期>     开始日期，格式为 yyyy-MM-dd"
    echo "  --end-date <日期>       结束日期，格式为 yyyy-MM-dd"
    echo "  --max-pages <页数>      最大页数，默认为10"
    echo "  --mapping-file <文件>   股票代码与组织ID的映射文件，默认为stock_orgid_mapping.json"
    echo "  --debug                 启用调试模式"
    exit 1
fi

# 提取股票代码
STOCK_CODE=$1
shift

# 检查股票代码格式
if ! [[ $STOCK_CODE =~ ^[0-9]{6}$ ]]; then
    echo "错误: 股票代码必须为6位数字"
    exit 1
fi

# 创建下载目录
DOWNLOAD_DIR="downloads/$STOCK_CODE"
mkdir -p "$DOWNLOAD_DIR"

echo "开始下载 $STOCK_CODE 的投资者关系活动记录表..."
echo "下载结果将保存在 $DOWNLOAD_DIR 目录下"

# 运行Python脚本
python3 cninfo_activity_downloader.py "$STOCK_CODE" "$@"

echo "下载完成"
