Param(
    [switch]$Reinstall
)

$ErrorActionPreference = "Stop"

# 计算路径
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$VenvPath = Join-Path $RepoRoot ".venv"
$Requirements = Join-Path $RepoRoot "requirements.txt"
$Config = Join-Path $RepoRoot "config.toml"
$ConfigTemplate = Join-Path $RepoRoot "config-template.toml"
$MainPy = Join-Path $RepoRoot "main.py"

Write-Host "[启动] 仓库目录: $RepoRoot"

function Get-PythonCmd {
    if (Get-Command py -ErrorAction SilentlyContinue) { return "py -3" }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
    else { throw "未找到 Python，请先安装 Python 3" }
}

# 创建或重建虚拟环境
if (Test-Path $VenvPath) {
    if ($Reinstall) {
        Write-Host "[启动] 重新创建虚拟环境 .venv"
        Remove-Item -Recurse -Force $VenvPath
    }
}
if (-not (Test-Path $VenvPath)) {
    $py = Get-PythonCmd
    Write-Host "[启动] 创建虚拟环境: $VenvPath"
    & $py -m venv $VenvPath
}

# 激活虚拟环境
$Activate = Join-Path $VenvPath "Scripts/Activate.ps1"
if (-not (Test-Path $Activate)) { throw "虚拟环境损坏或缺少激活脚本: $Activate" }
. $Activate

# 升级 pip
Write-Host "[启动] 升级 pip"
python -m pip install --upgrade pip

# 安装依赖
if (Test-Path $Requirements) {
    Write-Host "[启动] 安装依赖: requirements.txt"
    python -m pip install -r $Requirements
}
else {
    Write-Host "[启动] 未找到 requirements.txt，跳过依赖安装"
}

# 准备配置文件
if (-not (Test-Path $Config) -and (Test-Path $ConfigTemplate)) {
    Write-Host "[启动] 生成默认配置 config.toml"
    Copy-Item -Force $ConfigTemplate $Config
}

# 运行程序
if (-not (Test-Path $MainPy)) { throw "未找到入口文件: $MainPy" }
Write-Host "[启动] 正在运行 Maicraft-Mai ... (Ctrl+C 退出)"
python $MainPy


