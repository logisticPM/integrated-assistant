# FFmpeg 自动安装脚本
# 该脚本会自动下载、解压并设置 FFmpeg 的环境变量

$ErrorActionPreference = "Stop"

# 日志函数
function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "$timestamp - $Level - $Message"
}

# 创建临时目录
$tempDir = Join-Path $env:TEMP "ffmpeg_install"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
}

# 设置下载 URL 和目标路径
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ffmpegZip = Join-Path $tempDir "ffmpeg.zip"
$ffmpegExtractPath = Join-Path $tempDir "extract"
$ffmpegInstallPath = "C:\ffmpeg"

Write-Log "开始下载 FFmpeg..."

try {
    # 下载 FFmpeg
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip
    Write-Log "FFmpeg 下载完成"

    # 创建解压目录
    if (-not (Test-Path $ffmpegExtractPath)) {
        New-Item -ItemType Directory -Path $ffmpegExtractPath | Out-Null
    }

    # 解压文件
    Write-Log "正在解压 FFmpeg..."
    Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtractPath -Force
    
    # 获取解压后的 FFmpeg 目录名称
    $extractedDir = Get-ChildItem -Path $ffmpegExtractPath | Where-Object { $_.PSIsContainer } | Select-Object -First 1
    
    # 创建安装目录
    if (Test-Path $ffmpegInstallPath) {
        Write-Log "FFmpeg 目录已存在，正在删除..." "WARN"
        Remove-Item -Path $ffmpegInstallPath -Recurse -Force
    }
    
    # 移动文件到安装目录
    Write-Log "正在安装 FFmpeg 到 $ffmpegInstallPath..."
    New-Item -ItemType Directory -Path $ffmpegInstallPath | Out-Null
    Copy-Item -Path (Join-Path $extractedDir.FullName "*") -Destination $ffmpegInstallPath -Recurse
    
    # 设置环境变量
    Write-Log "正在设置环境变量..."
    $binPath = Join-Path $ffmpegInstallPath "bin"
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not $currentPath.Contains($binPath)) {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$binPath", "Machine")
        Write-Log "已将 $binPath 添加到系统 PATH 环境变量"
    } else {
        Write-Log "$binPath 已在系统 PATH 环境变量中" "WARN"
    }
    
    # 更新当前会话的 PATH
    $env:Path = "$env:Path;$binPath"
    
    # 验证安装
    Write-Log "正在验证 FFmpeg 安装..."
    try {
        $ffmpegVersion = & "$binPath\ffmpeg.exe" -version
        Write-Log "FFmpeg 安装成功！"
        Write-Log "版本信息: $($ffmpegVersion[0])"
    } catch {
        Write-Log "无法验证 FFmpeg 安装，请重启终端后再次尝试" "ERROR"
    }
    
} catch {
    Write-Log "安装过程中发生错误: $_" "ERROR"
    exit 1
} finally {
    # 清理临时文件
    Write-Log "正在清理临时文件..."
    if (Test-Path $ffmpegZip) {
        Remove-Item -Path $ffmpegZip -Force
    }
    if (Test-Path $ffmpegExtractPath) {
        Remove-Item -Path $ffmpegExtractPath -Recurse -Force
    }
}

Write-Log "FFmpeg 安装完成！"
Write-Log "请重启命令提示符或 PowerShell 窗口以使环境变量生效"
