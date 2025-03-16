@echo off
echo 正在以管理员权限安装 FFmpeg...
powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0setup_ffmpeg.ps1\"' -Verb RunAs"
echo 安装脚本已启动，请按照提示操作。
pause
