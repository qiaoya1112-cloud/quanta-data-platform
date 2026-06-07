#!/bin/bash
# 批量数据集切分脚本
# 用于批量切分 LeRobot 数据集为训练集和验证集

# =============================================================================
# 配置区域 - 根据需要修改以下参数
# =============================================================================

# 输入 JSON 配置文件路径
INPUT_JSON="/mnt/vepfs01/output/yifeng/resources/frontdesk/20260214_cotrain_inve_writ_wo_dual_pp.json"

# 数据集根目录
ROOT="/mnt/vepfs01/output/yifeng/resources/frontdesk"

# 训练集比例（0.0 - 1.0），默认 0.9 (90% 训练集, 10% 验证集)
TRAIN_RATIO=0.95

# 随机种子
SEED=42

# 是否强制重新切分（即使已存在切分也重新处理）
FORCE=""

# 是否显示详细日志
VERBOSE=""

# =============================================================================
# 命令行参数解析（可选覆盖上述默认配置）
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-json)
            INPUT_JSON="$2"
            shift 2
            ;;
        --root)
            ROOT="$2"
            shift 2
            ;;
        --train-ratio)
            TRAIN_RATIO="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --force|-f)
            FORCE="--force"
            shift
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --input-json PATH    输入 JSON 配置文件路径"
            echo "  --root PATH          数据集根目录"
            echo "  --train-ratio RATIO  训练集比例 (默认: 0.9)"
            echo "  --seed SEED          随机种子 (默认: 42)"
            echo "  --force, -f          强制重新切分（不跳过已存在的）"
            echo "  --verbose, -v        显示详细日志"
            echo "  --help, -h           显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --input-json /path/to/cotrain.json --root /path/to/datasets"
            echo "  $0 --train-ratio 0.95 --force"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# =============================================================================
# 验证配置
# =============================================================================

# 检查输入 JSON 文件是否存在
if [ ! -f "$INPUT_JSON" ]; then
    echo "错误: 输入 JSON 文件不存在: $INPUT_JSON"
    exit 1
fi

# 检查数据集根目录是否存在
if [ ! -d "$ROOT" ]; then
    echo "错误: 数据集根目录不存在: $ROOT"
    exit 1
fi

# 检查 batch_split_datasets.py 脚本是否存在
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPLIT_SCRIPT="${SCRIPT_DIR}/batch_split_datasets.py"

if [ ! -f "$SPLIT_SCRIPT" ]; then
    echo "错误: 找不到 batch_split_datasets.py 脚本: $SPLIT_SCRIPT"
    exit 1
fi

# =============================================================================
# 显示配置信息
# =============================================================================

echo "=========================================="
echo "批量数据集切分配置"
echo "=========================================="
echo "输入 JSON:     $INPUT_JSON"
echo "数据集根目录:  $ROOT"
echo "训练集比例:    $TRAIN_RATIO"
echo "随机种子:      $SEED"
echo "强制重新切分:  $([ -n "$FORCE" ] && echo "是" || echo "否")"
echo "详细日志:      $([ -n "$VERBOSE" ] && echo "是" || echo "否")"
echo "=========================================="
echo ""

# 统计数据集数量
DATASET_COUNT=$(python3 -c "import json; print(len(json.load(open('$INPUT_JSON'))))")
echo "共 $DATASET_COUNT 个数据集待处理"
echo ""

# =============================================================================
# 确认执行
# =============================================================================

read -p "确认开始批量切分数据集? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消操作"
    exit 0
fi

# =============================================================================
# 执行切分
# =============================================================================

echo ""
echo "开始批量切分数据集..."
echo ""

python3 "$SPLIT_SCRIPT" \
    --input-json "$INPUT_JSON" \
    --root "$ROOT" \
    --train-ratio "$TRAIN_RATIO" \
    --seed "$SEED" \
    $FORCE \
    $VERBOSE

# =============================================================================
# 检查执行结果
# =============================================================================

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "批量数据集切分完成!"
    echo "=========================================="

    # 显示输出文件
    INPUT_STEM=$(basename "$INPUT_JSON" .json)
    INPUT_DIR=$(dirname "$INPUT_JSON")
    echo "训练集配置: ${INPUT_DIR}/${INPUT_STEM}_train.json"
    echo "验证集配置: ${INPUT_DIR}/${INPUT_STEM}_val.json"
    echo "=========================================="
else
    echo ""
    echo "错误: 批量数据集切分失败!"
    exit 1
fi
