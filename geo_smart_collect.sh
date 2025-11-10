#!/bin/bash
# 地理位置智能阈值收集脚本
# 根据节点地理位置动态调整延迟阈值

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数
WORK_DIR="/root/downloads/aggregator"
VENV_PYTHON="${WORK_DIR}/venv/bin/python"
GIST_INFO="GIST_INFO"
GITHUB_TOKEN="GITHUB_TOKEN"

# 线程数
THREADS=400

# 基础延迟阈值(ms) - 将根据地理位置动态调整
# 香港: 800ms, 日本: 1200ms, 新加坡: 1200ms
# 美西: 1800ms, 美东: 2200ms, 欧洲: 2800ms
BASE_DELAY=2500

# 测试URL - 使用全球CDN
TEST_URL="https://cloudflare.com/cdn-cgi/trace"

# 输出格式
TARGETS="clash"

# 最小流量要求(GB)
MIN_FLOW=10

# 最小有效期(小时)
MIN_LIFE=72

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  地理位置智能阈值代理收集器${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# 检查工作目录
if [ ! -d "$WORK_DIR" ]; then
    echo -e "${RED}❌ 工作目录不存在: $WORK_DIR${NC}"
    exit 1
fi

# 检查 Python 虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Python 虚拟环境不存在: $VENV_PYTHON${NC}"
    exit 1
fi

# 检查 collect_geo.py 是否存在
if [ ! -f "${WORK_DIR}/subscribe/collect_geo.py" ]; then
    echo -e "${RED}❌ collect_geo.py 不存在${NC}"
    echo -e "${YELLOW}请确保已将 collect_geo.py 和 geo_threshold.py 复制到 subscribe/ 目录${NC}"
    exit 1
fi

# 检查 geo_threshold.py 是否存在
if [ ! -f "${WORK_DIR}/subscribe/geo_threshold.py" ]; then
    echo -e "${RED}❌ geo_threshold.py 不存在${NC}"
    echo -e "${YELLOW}请确保已将 geo_threshold.py 复制到 subscribe/ 目录${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 环境检查通过${NC}"
echo ""

# 显示配置
echo -e "${YELLOW}配置信息:${NC}"
echo "  工作目录: $WORK_DIR"
echo "  线程数: $THREADS"
echo "  基础延迟阈值: ${BASE_DELAY}ms (动态调整)"
echo "  测试URL: $TEST_URL"
echo "  最小流量: ${MIN_FLOW}GB"
echo "  最小有效期: ${MIN_LIFE}小时"
echo ""

echo -e "${YELLOW}地理位置阈值策略:${NC}"
echo "  🇭🇰 港澳台: 800ms (最严格)"
echo "  🇯🇵 日本/韩国/新加坡: 1200ms"
echo "  🇻🇳 东南亚: 1500ms"
echo "  🇺🇸 美国西海岸: 1800ms"
echo "  🇺🇸 美国东部/加拿大: 2200ms"
echo "  🇬🇧 欧洲: 2800ms"
echo "  🌍 其他地区: 3500ms"
echo "  ⚡ 专线/IPLC: 降低20%阈值"
echo ""

# 确认执行
read -p "$(echo -e ${GREEN}是否开始收集? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 开始收集...${NC}"
echo ""

# 进入工作目录
cd "$WORK_DIR" || exit 1

# 执行收集脚本
"$VENV_PYTHON" -u subscribe/collect_geo.py \
  -n "$THREADS" \
  -d "$BASE_DELAY" \
  -e \
  -g "$GIST_INFO" \
  -k "$GITHUB_TOKEN" \
  -t "$TARGETS" \
  -u "$TEST_URL" \
  -f "$MIN_FLOW" \
  -l "$MIN_LIFE"

# 检查执行结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=====================================${NC}"
    echo -e "${GREEN}  ✅ 收集完成！${NC}"
    echo -e "${GREEN}=====================================${NC}"
    echo ""
    echo -e "${BLUE}订阅链接已上传到 GitHub Gist${NC}"
    echo -e "${YELLOW}Gist ID: $(echo $GIST_INFO | cut -d'/' -f2)${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}=====================================${NC}"
    echo -e "${RED}  ❌ 收集失败${NC}"
    echo -e "${RED}=====================================${NC}"
    echo ""
    exit 1
fi

