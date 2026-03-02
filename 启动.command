#!/bin/bash
# 双击此文件即可启动英语听力TTS工具（macOS）

cd "$(dirname "$0")"

echo "========================================="
echo "  🎧 英语听力 TTS 工具 - 正在启动..."
echo "========================================="

# 检查并安装依赖
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 首次使用，正在安装依赖（约1-2分钟）..."
    pip3 install -r requirements.txt
fi

echo ""
echo "✅ 依赖已就绪，正在打开浏览器..."
echo "   （如未自动打开，请手动访问 http://localhost:8501）"
echo ""

# 启动 streamlit
python3 -m streamlit run app.py --server.headless false
