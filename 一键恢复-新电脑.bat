@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 足球分析模型 · 一键恢复（新电脑）

echo ============================================================
echo   足球分析模型 一键恢复（新电脑版）
echo   数据源：github.com/lc815814/football-report
echo   说明：自动安装 Git / 下载项目 / 安装依赖 / 生成报告
echo ============================================================
echo.

rem ============ 1. Git 检查 ============
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/5] 未检测到 Git，正在自动安装（约 1-2 分钟）...
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements --silent --disable-interactivity
    where git >nul 2>nul
    if !errorlevel! neq 0 (
        echo.
        echo   Git 安装失败或尚未生效，请重启电脑后再运行本脚本。
        pause
        exit /b 1
    )
) else (
    echo [1/5] Git 已就绪
)

rem ============ 2. Python 检查 ============
set "PYCMD=python"
%PYCMD% --version >nul 2>nul
if %errorlevel% neq 0 (
    set "PYCMD=py -3"
    !PYCMD! --version >nul 2>nul
)
if %errorlevel% neq 0 (
    echo [2/5] 未检测到 Python。
    echo   请先安装 Python 3.10 或更高版本：https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"，装好后重新双击本脚本。
    pause
    exit /b 1
)
echo [2/5] Python 已就绪：%PYCMD%
%PYCMD% --version

rem ============ 3. 选择目录并下载项目 ============
set "DIR=%CD%\football_report"
set /p INPUT="[3/5] 安装到哪个文件夹？（直接回车 = %DIR%）: "
if not "%INPUT%"=="" set "DIR=%INPUT%"

if exist "%DIR%\.git" (
    echo   目录已存在，正在更新到最新版...
    git -C "%DIR%" pull
) else if exist "%DIR%" (
    echo   错误：目录 %DIR% 已存在但不是本项目仓库，请换一个目录后重试。
    pause
    exit /b 1
) else (
    echo   正在下载项目到 %DIR% ...
    git clone https://github.com/lc815814/football-report.git "%DIR%"
    if errorlevel 1 (
        echo   下载失败，请检查网络后重试。
        pause
        exit /b 1
    )
)
cd /d "%DIR%"

rem ============ 4. 安装依赖 ============
echo [4/5] 安装 Python 依赖（首次约 2-3 分钟，优先国内镜像）...
%PYCMD% -m pip install -r football_model\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo   镜像安装失败，改用默认源重试...
    %PYCMD% -m pip install -r football_model\requirements.txt
)

rem ============ 5. 生成报告 ============
echo [5/5] 正在生成足球分析报告（约 1 分钟）...
%PYCMD% football_model\generate_report.py
if errorlevel 1 (
    echo.
    echo   报告生成失败，请把上方错误信息发给豆包排查。
    pause
    exit /b 1
)
copy /y football_model\football_analysis_report.html index.html >nul

echo.
echo ============================================================
echo    恢复完成！
echo    报告已生成：%DIR%\index.html
echo ============================================================
start "" "index.html"
echo.
echo  下一步（可选）：
echo   1. 让每日 14:15 自动更新 → 在豆包里说"重建足球定时任务"
echo   2. 让本机更新自动发布到线上 → 首次推送时按提示登录 GitHub 即可
echo.
pause
