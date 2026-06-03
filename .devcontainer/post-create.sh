#!/usr/bin/env bash
# Devcontainer 初回作成時のセットアップ
# - Python 依存パッケージのインストール
# - azd ai agent 拡張のインストール (0.1.34-preview 以上)
set -euo pipefail

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing workshop Python packages"
pip install -r .devcontainer/requirements.txt

echo "==> Installing azd ai agent extension (azure.ai.agents)"
# 既にインストール済みでも失敗扱いにしない (再ビルド時のため)
azd ext install azure.ai.agents || azd ext upgrade azure.ai.agents || true

echo "==> Versions"
python --version
az --version | head -n 1
azd version
gh --version | head -n 1
azd ext list || true

echo "==> Done. 次に 'az login' と 'azd auth login' を実行してください。"
