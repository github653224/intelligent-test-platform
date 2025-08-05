#!/bin/bash

echo "🚀 启动AI智能自动化测试平台..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cat > .env << EOF
# AI模型配置
OPENAI_API_KEY=your_openai_api_key_here

# 数据库配置
POSTGRES_PASSWORD=password

# 服务端口
BACKEND_PORT=8000
AI_ENGINE_PORT=8001
FRONTEND_PORT=3000
OLLAMA_PORT=11434
EOF
    echo "⚠️  请编辑 .env 文件，设置你的OpenAI API密钥"
fi

# 启动服务
echo "🔧 启动Docker服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo "✅ 服务启动完成！"
echo ""
echo "🌐 访问地址："
echo "  前端应用: http://localhost:3000"
echo "  后端API: http://localhost:8000"
echo "  AI引擎: http://localhost:8001"
echo "  API文档: http://localhost:8000/docs"
echo ""
echo "📚 使用说明："
echo "  1. 打开浏览器访问 http://localhost:3000"
echo "  2. 在AI引擎页面测试各项功能"
echo "  3. 查看API文档了解接口详情"
echo ""
echo "🛑 停止服务：docker-compose down" 