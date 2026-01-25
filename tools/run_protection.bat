@echo off
chcp 65001 > nul
echo ========================================
echo  保护expected_results目录脚本
echo ========================================
echo.

REM 设置Python编码环境
set PYTHONIOENCODING=utf-8

REM 运行保护脚本（默认使用dry-run模式预览）
echo 正在检查目录结构...
python tools\protect_expected_results.py --dry-run

echo.
echo 如果目录结构正确，可以使用以下命令锁定目录：
echo   python tools\protect_expected_results.py --lock
echo.
echo 提示：可以将此脚本添加到Windows任务计划程序定期运行
echo.

pause