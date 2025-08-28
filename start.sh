#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$REPO_ROOT"

PY="python3"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="python"
fi

VENV_DIR=".venv"

if [[ "${1:-}" == "--reinstall" && -d "$VENV_DIR" ]]; then
  echo "[启动] 重新创建虚拟环境 $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[启动] 创建虚拟环境 $VENV_DIR"
  "$PY" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "[启动] 升级 pip"
"$PY" -m pip install --upgrade pip

if [[ -f requirements.txt ]]; then
  echo "[启动] 安装依赖 requirements.txt"
  "$PY" -m pip install -r requirements.txt
else
  echo "[启动] 未找到 requirements.txt，跳过依赖安装"
fi

if [[ ! -f config.toml && -f config-template.toml ]]; then
  echo "[启动] 生成默认配置 config.toml"
  cp -f config-template.toml config.toml
fi

echo "[启动] 正在运行 Maicraft-Mai ... (Ctrl+C 退出)"
exec "$PY" main.py


