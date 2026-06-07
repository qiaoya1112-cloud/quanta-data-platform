#!/bin/bash

# 使用关联数组定义任务配置（bash 4.0+）

# 定义每个任务ID对应的文件名
declare -A FILE_NAME_MAP
# FILE_NAME_MAP["535"]="20251021_pickplacevp1022_pickshelf_lrm_hrpi2_yhvp_1"
# FILE_NAME_MAP["536"]="20251021_pickplacevp1022_placeshelf_lmr_hrpi2_yhvp_2"
# FILE_NAME_MAP["537"]="20251021_pickplacevp1022_placeanywheredesk_lrbt_hrpi2_yhvp_3"
# FILE_NAME_MAP["578"]="20251031_1106basedata_laystand_moz1"
# FILE_NAME_MAP["564"]="20251030_1106basedata_laystand_moz1"
# FILE_NAME_MAP["562"]="20251029_1106basedata_laystand_moz1"
# FILE_NAME_MAP["561"]="20251028_1106basedata_laystand_moz1"
# FILE_NAME_MAP["547"]="20251023_pushpulldrawer_moz1"
# FILE_NAME_MAP["517"]="20251019_pickplacevp1020_picktable_lrfb_hrpi2_yhvp_1"
# # FILE_NAME_MAP["518"]="20251019_pickplacevp1020_picktable_rc_hrpi2_yhvp_2"
# FILE_NAME_MAP["519"]="20251019_pickplacevp1020_pickshelf_lrm_hrpi2_yhvp_3"
# FILE_NAME_MAP["520"]="20251019_pickplacevp1020_pickegg_singlecr_hrpi2_yhvp_4"
# FILE_NAME_MAP["521"]="20251019_pickplacevp1020_pickegg_doublecr_hrpi2_yhvp_5"
# FILE_NAME_MAP["522"]="20251019_pickplacevp1020_placeegg_singlecr_hrpi2_yhvp_6"
# FILE_NAME_MAP["523"]="20251019_pickplacevp1020_placeegg_doublecr_hrpi2_yhvp_7"
# FILE_NAME_MAP["524"]="20251019_pickplacevp1020_placedrawer_singleumr_hrpi2_yhvp_8"
# # FILE_NAME_MAP["525"]="20251019_pickplacevp1020_placedrawer_doubleumr_hrpi2_yhvp_9"
# FILE_NAME_MAP["526"]="20251019_pickplacevp1020_placecupshelf_singlecr_hrpi2_yhvp_10"
# FILE_NAME_MAP["527"]="20251019_pickplacevp1020_placecupshelf_doublecr_hrpi2_yhvp_11"
# FILE_NAME_MAP["528"]="20251019_pickplacevp1020_placealloc_double_hrpi2_yhvp_12"
# FILE_NAME_MAP["529"]="20251019_pickplacevp1020_placeshelf_mn_hrpi2_yhvp_13"
# FILE_NAME_MAP["530"]="20251019_pickplacevp1020_placeplate_mn_hrpi2_yhvp_14"
# FILE_NAME_MAP["531"]="20251019_pickplacevp1020_placemul_lrtb_hrpi2_yhvp_15"
# FILE_NAME_MAP["630"]="20251109_office_water_triangle_moz1_yh_v2"
# FILE_NAME_MAP["707"]="20251117_force_cftest_mozWB"
# FILE_NAME_MAP["695"]="20251116_demodailytrain_office_watertriangle_moz1WB"
# FILE_NAME_MAP["693"]="20251116_demodailytrain_office_pickwater_moz1WB"
# FILE_NAME_MAP["689"]="20251115_demodailytrain_office_pickwater_moz1WB"
# FILE_NAME_MAP["680"]="20251114_demodailytrain_office_pickwater_moz1WB"


# FILE_NAME_MAP["715"]="20251118_FrontDeskDemo_WBWB_tissuwipethrow"
# FILE_NAME_MAP["722"]="20251119_FrontDeskDemo_WBWB_tissuwipethrow"

# FILE_NAME_MAP["744"]="20251120_liftwater_1_forcecontrol_17_new"

# FILE_NAME_MAP["741"]="20251120_FrontDeskDemo_WBWB_insertflower"

# FILE_NAME_MAP["740"]="20251119_FrontDeskDemo_WBWB_WaterFlowers_V1"
# FILE_NAME_MAP["735"]="20251120_FrontDeskDemo_WBWB_Humaninteraction"
# FILE_NAME_MAP["733"]="20251120_FrontDeskDemo_WBWB_sweep_y06"
# FILE_NAME_MAP["725"]="20251119_FrontDeskDemo_WBWB_drawer"
# FILE_NAME_MAP["724"]="20251119_FrontDeskDemo_WBWB_StackDish"

# FILE_NAME_MAP["749"]="20251121_FrontDeskDemo_WBWB_Microwave_dagger"
# FILE_NAME_MAP["757"]="20251122_FrontDeskDemo_WBWB_Microwave_dagger"
# FILE_NAME_MAP["763"]="20251123_FrontDeskDemo_WBWB_Microwave_dagger"
# FILE_NAME_MAP["775"]="20251124_FrontDeskDemo_WBWB_Microwave_dagger"

# FILE_NAME_MAP["788"]="20251125_FrontDeskDemo_WBWB_Microwave_dagger"
# FILE_NAME_MAP["825"]="20251202_FrontDeskDemo_WBWB_Insert_dagger_valid"

# FILE_NAME_MAP["963"]="20251221_norollback_FrontDeskDemo_WBWB_Insertflower_dagger_v2"

# FILE_NAME_MAP["1073"]="20260109_writingdesk_v1_book_WBWB_dagger"
# FILE_NAME_MAP["1078"]="20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"

# FILE_NAME_MAP["957"]="20251219_rollback_FrontDeskDemo_WBWB_pickcandy_dagger_v2"

# FILE_NAME_MAP["1170"]="20260115_writingdesk_v1_takebook_WBWB_dagger"
# FILE_NAME_MAP["1169"]="20260115_writingdesk_v1_putback_book_WBWB_dagger"


# FILE_NAME_MAP["825"]="20251202_FrontDeskDemo_WBWB_Insert_dagger"
# FILE_NAME_MAP["949"]="20251219_norollback_FrontDeskDemo_WBWB_Insertflower_dagger"
# FILE_NAME_MAP["950"]="20251219_rollback_FrontDeskDemo_WBWB_Insertflower_dagger"
# FILE_NAME_MAP["1169"]="20260115_writingdesk_v1_putback_book_WBWB_dagger"
# FILE_NAME_MAP["1170"]="20260115_writingdesk_v1_takebook_WBWB_dagger"

# FILE_NAME_MAP["1354"]="20260130_MakeOden_CCTVDemo_pi05_0929wb_dagger"


# FILE_NAME_MAP["1752"]="20260302_SkewerFruits_newnorm_v1v2_Moz1WB_dagger"
# FILE_NAME_MAP["1924"]="20260306_SkewerFruits_V3_Moz1WB_dagger-1"
# FILE_NAME_MAP["1927"]="20260306_SkewerFruits_V3_Moz1WB_dagger-2"


# FILE_NAME_MAP["2626"]="20260319_SkewerFruits_new_V4_Moz1WB_dagger-1"
# FILE_NAME_MAP["2627"]="20260319_SkewerFruits_new_V4_Moz1WB_dagger-2"

# FILE_NAME_MAP["3414"]="20260331_SkewerFruits_V5_Moz1WB_dagger-1"
FILE_NAME_MAP["3415"]="20260331_SkewerFruits_V5_Moz1WB_dagger-2"




# 定义每个任务ID对应的子目录（可选，如果某个ID没有定义，会使用默认值从文件名提取）
declare -A SUBDIR_MAP
# SUBDIR_MAP["749"]="MicroWave/dagger_test"
# SUBDIR_MAP["757"]="MicroWave/dagger_test"
# SUBDIR_MAP["763"]="MicroWave/dagger_test"
# SUBDIR_MAP["757"]="MicroWave/dagger"
# SUBDIR_MAP["775"]="MicroWave/dagger/all"
# SUBDIR_MAP["788"]="MicroWave/dagger"
# SUBDIR_MAP["825"]="Insert/dagger"
# SUBDIR_MAP["825"]="Insert/dagger/all"
# SUBDIR_MAP["963"]="Insert/dagger"

# SUBDIR_MAP["1073"]="writingdesk/dagger"
# SUBDIR_MAP["1078"]="writingdesk/dagger"

# SUBDIR_MAP["957"]="candy/dagger"

# SUBDIR_MAP["1169"]="writingdesk/dagger"

# SUBDIR_MAP["1170"]="writingdesk/dagger"

# SUBDIR_MAP["825"]="writingdesk_0130/dagger"
# SUBDIR_MAP["949"]="writingdesk_0130/dagger"
# SUBDIR_MAP["950"]="writingdesk_0130/dagger"
# SUBDIR_MAP["1169"]="writingdesk_0130/dagger"
# SUBDIR_MAP["1170"]="writingdesk_0130/dagger"


# SUBDIR_MAP["1354"]="cctv/dagger"

# SUBDIR_MAP["1752"]="cctv/dagger"

# SUBDIR_MAP["1924"]="cctv/dagger"
# SUBDIR_MAP["1927"]="cctv/dagger"



# SUBDIR_MAP["1752"]="skewer_0312/dagger"
# SUBDIR_MAP["1924"]="skewer_0312/dagger"
# SUBDIR_MAP["1927"]="skewer_0312/dagger"



# SUBDIR_MAP["2626"]="skewer_0322/dagger"
# SUBDIR_MAP["2627"]="skewer_0322/dagger"

# SUBDIR_MAP["3414"]="skewer_0404/dagger"
SUBDIR_MAP["3415"]="skewer_0404/dagger"

# 定义每个任务ID对应的设备号列表（可选，如果某个ID没有定义，会使用空字符串）
# 多个设备用空格分隔，例如: DEVICE_MAP["757"]="moz1-y05 moz1-y08 moz1-y13"
declare -A DEVICE_MAP
# DEVICE_MAP["757"]="moz1-y15"



# 定义每个任务ID对应的 prompt（可选，如果某个ID没有定义，会使用默认值）
declare -A PROMPT_MAP
# PROMPT_MAP["393"]="Place three bottles into a triangle"
# PROMPT_MAP["247"]="Prompt for task 247"
# PROMPT_MAP["252"]="Prompt for task 252"

DEFAULT_PREFIX="/mnt/vepfs01/output"


GROUP_BY_FEATURE=true

# 默认 prompt（当某个任务ID在 PROMPT_MAP 中没有定义时使用）
DEFAULT_PROMPT="Default prompt for all tasks"

DOWNLOAD_DATASET=true
GENERATE_SAMPLE_WEIGHTS=true
GENERATE_PROMPT=false
FETCH_ANNOTATIONS=false
GENERATE_DATASET_STATISTICS=true

# 选择使用 action 还是 action_english
ACTION_FIELD="action_english"  # 可选: "action" 或 "action_english"

# DAgger 类型过滤（可选）
# 设置为非空值以按 dagger_type 过滤，例如 "policy" 或 "teleop"
# 留空则不过滤
DAGGER_TYPE="teleop"  # 可选: "policy", "teleop" 或其他值，留空表示不过滤
# DAGGER_TYPE=""  # 可选: "policy", "teleop" 或其他值，留空表示不过滤

# 读取参数
PREFIX="${1:-$DEFAULT_PREFIX}"
BASE_OUTPUT_DIR="$PREFIX/yuhang/dagger/dataset_collection"

# 数据筛选选项
ANNOTATED_ONLY=false      # true: 只导出有标注的数据; false: 导出所有数据
INCLUDE_UNCHECKED=false    # true: 包含未质检的数据; false: 不包含未质检的数据
INVALID_ONLY=false        # true: 只导出质检不合格的数据; false: 不限制

# 安装 ffmpeg（只需执行一次）
bash -lc 'set -e; if ! command -v ffmpeg >/dev/null 2>&1; then (sudo -n apt-get update -y && sudo -n apt-get install -y ffmpeg) || (apt-get update -y && apt-get install -y ffmpeg) || true; fi; if ! command -v ffmpeg >/dev/null 2>&1; then mkdir -p "$HOME/.local/bin"; workdir=$(mktemp -d); cd "$workdir"; URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz; if command -v curl >/dev/null 2>&1; then curl -L "$URL" -o ffmpeg.tar.xz; else wget -O ffmpeg.tar.xz "$URL"; fi; tar -xf ffmpeg.tar.xz; d=$(find . -maxdepth 1 -type d -name "ffmpeg-*-amd64-static" | head -n1); cp "$d/ffmpeg" "$HOME/.local/bin/ffmpeg"; chmod +x "$HOME/.local/bin/ffmpeg"; echo "Installed static ffmpeg to $HOME/.local/bin/ffmpeg"; fi; export PATH="$HOME/.local/bin:$PATH"; ffmpeg -version | head -n1 | cat; echo "Encoders (h264):"; ffmpeg -hide_banner -encoders 2>/dev/null | grep -E "libx264|h264" | cat'

# 循环处理每个任务 - 手动指定任务ID列表以确保按顺序处理
# 将所有任务ID存储到数组中
TASK_ID_LIST=("${!FILE_NAME_MAP[@]}")

# 先打印所有的任务ID用于调试
echo "============================================"
echo "所有配置的任务ID: ${TASK_ID_LIST[@]}"
echo "任务ID数量: ${#TASK_ID_LIST[@]}"
echo "============================================"

# 统计总任务数（任务ID x 设备数）
total_tasks=0
for TASK_IDS in "${TASK_ID_LIST[@]}"; do
    if [ -n "${DEVICE_MAP[$TASK_IDS]}" ]; then
        # 统计该任务的设备数量
        device_count=$(echo "${DEVICE_MAP[$TASK_IDS]}" | wc -w)
        total_tasks=$((total_tasks + device_count))
    else
        total_tasks=$((total_tasks + 1))
    fi
done

echo "============================================"
echo "总任务数: $total_tasks"
echo "============================================"

current_task=0

for TASK_IDS in "${TASK_ID_LIST[@]}"; do
    echo "DEBUG: 开始处理任务ID: $TASK_IDS"
    # 从关联数组获取对应的文件名
    FILE_NAME="${FILE_NAME_MAP[$TASK_IDS]}"

    # 从关联数组获取对应的子目录名，如果不存在则从文件名提取
    if [ -n "${SUBDIR_MAP[$TASK_IDS]}" ]; then
        SUBDIR="${SUBDIR_MAP[$TASK_IDS]}"
    else
        # 默认从文件名提取第二个下划线分隔的部分
        SUBDIR=$(echo "$FILE_NAME" | awk -F'_' '{print $2}')
    fi
    SUBDIR="$SUBDIR/$DAGGER_TYPE"
    # 从关联数组获取对应的设备号列表
    if [ -n "${DEVICE_MAP[$TASK_IDS]}" ]; then
        DEVICE_LIST="${DEVICE_MAP[$TASK_IDS]}"
    else
        DEVICE_LIST=""
    fi

    # 从关联数组获取对应的 prompt，如果不存在则使用默认值
    if [ -n "${PROMPT_MAP[$TASK_IDS]}" ]; then
        PROMPT="${PROMPT_MAP[$TASK_IDS]}"
    else
        PROMPT="$DEFAULT_PROMPT"
    fi

    # 如果没有设备列表，创建一个占位符
    if [ -z "$DEVICE_LIST" ]; then
        DEVICE_LIST="__EMPTY__"
    fi

    # 对每个设备进行循环处理
    for DEVICE in $DEVICE_LIST; do
        current_task=$((current_task + 1))

        # 如果 DEVICE 是占位符，设置为空字符串
        if [ "$DEVICE" = "__EMPTY__" ]; then
            DEVICE=""
        fi

        echo "============================================"
        echo "Processing task $current_task/$total_tasks"
        echo "TASK_IDS: $TASK_IDS"
        echo "FILE_NAME: $FILE_NAME"
        echo "SUBDIR: $SUBDIR"
        echo "DEVICE: $DEVICE"
        echo "PROMPT: $PROMPT"
        echo "============================================"

        # 构建输出目录名称：ID_FILE_NAME_DEVICE
        if [ -n "$DEVICE" ]; then
            OUTPUT_DIR_NAME="${TASK_IDS}_${FILE_NAME}_${DEVICE}"
        else
            OUTPUT_DIR_NAME="${TASK_IDS}_${FILE_NAME}"
        fi

        # /mnt/vepfs01/output/yifeng/resources/frontdesk
        # 定义超参数
        # BASE_OUTPUT_DIR="$PREFIX/yuhang/dataset"
        OUTPUT_DIR="$BASE_OUTPUT_DIR/$SUBDIR/${OUTPUT_DIR_NAME}"
        SAMPLE_WEIGHTS_DIR="$BASE_OUTPUT_DIR/$SUBDIR"

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$DOWNLOAD_DATASET" = true ]; then
            echo "Processing task IDs: $TASK_IDS"
            echo "Output directory: $OUTPUT_DIR"

            # 构建设备号参数（如果有的话）
            DEVICE_ARGS=""
            if [ -n "$DEVICE" ]; then
                DEVICE_ARGS="--capture-devices $DEVICE"
            fi

            # 构建数据筛选参数
            FILTER_ARGS=""
            if [ "$FETCH_ANNOTATIONS" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --fetch-annotations"
            fi
            if [ "$ANNOTATED_ONLY" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --annotated-only"
            fi
            if [ "$INCLUDE_UNCHECKED" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --include-unchecked"
            fi
            if [ "$INVALID_ONLY" = true ]; then
                FILTER_ARGS="$FILTER_ARGS --invalid-only"
            fi
            if [ -n "$DAGGER_TYPE" ]; then
                FILTER_ARGS="$FILTER_ARGS --dagger-type $DAGGER_TYPE"
            fi

            GROUP_ARGS=""
            if [ "$GROUP_BY_FEATURE" = true ]; then
                GROUP_ARGS="$GROUP_ARGS --group-by-features"
            fi

            # 统一调用
            python3 $PREFIX/yuhang/dagger/scripts/export_dataset/export_dataset_dagger.py \
            --task-ids $TASK_IDS \
            --output-dir $OUTPUT_DIR \
            --api-url https://quanta.i.spirit-ai.com \
            --use-tos-internal-endpoint \
            --action-field $ACTION_FIELD \
            $DEVICE_ARGS \
            $FILTER_ARGS \
            $GROUP_ARGS
            # --recording-limit 100 \
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$GENERATE_SAMPLE_WEIGHTS" = true ]; then
            # 生成 sample weights 文件
            mkdir -p "$SAMPLE_WEIGHTS_DIR"

            # 构建 JSON 内容 - 使用任务ID_文件名_设备号作为key
            json_content="{\n    \"$OUTPUT_DIR_NAME\":1\n}"

            # 写入文件到 $BASE_OUTPUT_DIR/$SUBDIR/ID_FILE_NAME_DEVICE.json
            echo -e "$json_content" > "$SAMPLE_WEIGHTS_DIR/$OUTPUT_DIR_NAME.json"
            echo "Generated sample weights file: $SAMPLE_WEIGHTS_DIR/$OUTPUT_DIR_NAME.json"
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        if [ "$GENERATE_PROMPT" = true ]; then
            # 只写入 {"task_index": 0, "task": "..."} 这一行到 tasks.jsonl，覆盖原有内容
            tasks_jsonl_path="$OUTPUT_DIR/meta/tasks.jsonl"

            if [ -f "$tasks_jsonl_path" ]; then
                echo "{\"task_index\": 0, \"task\": \"${PROMPT}\"}" > "$tasks_jsonl_path"
                echo "Overwritten with single JSON object: $tasks_jsonl_path"
            else
                echo "Warning: tasks.jsonl not found: $tasks_jsonl_path" >&2
            fi
        fi

        ########################################################################################
        ########################################################################################
        ########################################################################################

        echo "Completed task: $OUTPUT_DIR_NAME"
        echo ""
    done  # 结束设备循环
done  # 结束任务ID循环

echo "============================================"
echo "All tasks completed! Total: $current_task tasks"
echo "============================================"
