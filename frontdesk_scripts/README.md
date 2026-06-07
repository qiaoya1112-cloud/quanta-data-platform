# Frontdesk 数据处理脚本集

这套脚本是一条完整的「机器人训练数据准备流水线」：从服务端导出 LeRobot 数据集 →
切分训练/验证集 → 配置采样比例 → 统计与质检。

`.sh` 负责「配置 + 批量调度」，`.py` 负责「实际干活」；`GROUP_RULES` 是贯穿采样与统计环节的分组主线。

---

## 1. 各文件用途

| # | 文件 | 类型 | 角色 | 用途 / 核心逻辑 | 关键参数·配置 |
|---|---|---|---|---|---|
| 1 | **export_dataset.py** | py 引擎 | 导出 | 通用导出底座：调后端 `export_dataset` 接口 → 下载 parquet+视频 → 生成 LeRobot meta → 修复索引。功能最全（含 SaaS 登录、POST API、中文标注、dagger_type、session 共享） | `--task-ids` / `--include-unchecked` / `--dagger-type` / `--user` / `--password` |
| 2 | **export_dataset_normal_text_feature_split.py** | py 引擎 | 导出 | "普通数据"导出器，是 #1 的精简变体（无登录/POST/中文）。被 #4 的 .sh 调用 | `--group-by-features` / `--fetch-annotations` |
| 3 | **export_dataset_dagger.py** | py 引擎 | 导出 | "DAgger 数据"导出器。比 #2 多了 dagger_type 过滤 + 子集重编号（`_reindex_after_filter`：过滤后重排 episode/chunk、重算 total_frames/tasks、清理空目录）、中文→英文任务名转换。被 #5 的 .sh 调用 | `--dagger-type policy/teleop`、`--action-field` |
| 4 | **export_dataset_normal_text_feature_split.sh** | sh 驱动 | 导出调度 | 批处理调度：顶部用 `FILE_NAME_MAP/SUBDIR_MAP/DEVICE_MAP` 关联数组配任务清单，循环"任务×设备"拼参数调 #2；装 ffmpeg；为每个数据集生成 `{名:1}` 采样权重 JSON | `ANNOTATED_ONLY` / `INCLUDE_UNCHECKED` / `GROUP_BY_FEATURE` |
| 5 | **export_dataset_dagger.sh** | sh 驱动 | 导出调度 | 同 #4，但调 #3，专门导 DAgger 数据；输出目录加 `$DAGGER_TYPE` 层 | `DAGGER_TYPE="teleop"`、`ACTION_FIELD` |
| 6 | **batch_split_datasets.py** | py 引擎 | 切分 | 把数据集随机切 train/val：按 `train_ratio` 划分 episode → 重编号 → 改写 meta（info/episodes/stats/dataset.json）→ 输出 `_split/train`、`_split/val` 及 `*_train.json`/`*_val.json`。视频默认软链接省空间 | `--train-ratio 0.95 --seed 42 --force` |
| 7 | **batch_split_datasets.sh** | sh 驱动 | 切分调度 | #6 的命令行包装：配默认参数、校验文件、交互确认后调 #6 | `--input-json` / `--root` / `--train-ratio` |
| 8 | **adjust_sampling_ratio.py** | py 算法 | 采样比例 | 核心算法：读 `{数据集:权重}` JSON + 各数据集帧数 → 按 `GROUP_RULES` 分组 → 按 `GROUP_CONFIG` 设占比（固定占比/相对权重）→ power-law(`alpha`) 组内分配 → 算出采样权重写回 JSON | `INPUT_JSON/OUTPUT_JSON`、`GROUP_RULES`、`GROUP_CONFIG` |
| 9 | **analyze_sampling_frames.py** | py 分析 | 采样验证 | #8 的配套：算"权重占比 vs 帧数占比 vs 实际采样帧数占比"，按主类别/组/子类别多维汇总 → 打印+导出 CSV。验证权重配得对不对 | `CONFIG_JSON/OUTPUT_CSV`、`GROUP_RULES` |
| 10 | **dataset_statistics.py** | py 统计 | 统计 | 全面统计：扫 parquet 统计每个 task_folder 总帧数、每个 prompt 的帧数占比+对应 recording_id 列表、换算时长 → 详细 CSV + 汇总 CSV。下钻到 prompt/recording 粒度 | `--input/--output/--summary`、`FPS=30` |
| 11 | **check_chinese.py** | py 质检 | 质检 | 扫各数据集 `tasks.jsonl`，用正则 `[一-鿿]` 查英文标注里混入的中文，报告+导出 JSON | `input_json -v --export` |
| 12 | **check_evalset_split.sh** | sh 质检 | 质检 | 内嵌 Python：对比每个数据集 `episodes.jsonl` 记录帧数 vs 实际 parquet 行数，查数据完整性/缺帧 | `<json文件路径>` |

**关键依赖关系**

- `export_dataset_normal_text_feature_split.sh` → 调 `export_dataset_normal_text_feature_split.py`
- `export_dataset_dagger.sh` → 调 `export_dataset_dagger.py`
- `batch_split_datasets.sh` → 调 `batch_split_datasets.py`
- `#8 / #9 / #10 / #11` 共享一套近似的 `GROUP_RULES` 分组规则

---

## 2. 完整数据处理链路

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  服务端 Quanta API  (quanta.i.spirit-ai.com)                                  │
│  /export_dataset · /group_by_features · /latest_annotation                    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                     │ HTTP 拉取 dataset 信息 + 预签名URL下载
                                     ▼
╔══════════════════════ ① 导出 EXPORT ════════════════════════════════════════╗
║                                                                              ║
║   普通数据                              DAgger 数据                            ║
║   ┌────────────────────────────┐       ┌────────────────────────────┐        ║
║   │ export_dataset_normal_     │       │ export_dataset_dagger.sh   │        ║
║   │   text_feature_split.sh    │       │  (DAGGER_TYPE=teleop)      │        ║
║   │  (配 FILE/SUBDIR/DEVICE_MAP)│       └────────────┬───────────────┘        ║
║   └────────────┬───────────────┘                    │ 循环 task×device       ║
║                │ 循环 task×device                    ▼                        ║
║                ▼                          export_dataset_dagger.py            ║
║   export_dataset_normal_text_             · dagger_type 过滤                  ║
║     feature_split.py                      · 子集重编号 _reindex              ║
║                │                          · 中文→英文任务名                  ║
║                └──────────┬───────────────────────┘                          ║
║                           │   (export_dataset.py = 通用底座/手动单次导出)     ║
║                           ▼                                                   ║
║        产出 LeRobot 数据集：dataset.json + meta/{info,tasks,                  ║
║        episodes,episodes_stats} + data/*.parquet + videos/*.mp4              ║
╚═══════════════════════════════════╤══════════════════════════════════════════╝
                                     │
                                     ▼
╔══════════════════════ ② 切分 SPLIT ═════════════════════════════════════════╗
║   batch_split_datasets.sh  ──调──▶  batch_split_datasets.py                  ║
║   按 train_ratio=0.95 随机划分 → 每个数据集生成 _split/train 、_split/val     ║
║   产出: xxx_train.json  /  xxx_val.json   (供训练用的数据集清单+权重)         ║
╚═══════════════════════════════════╤══════════════════════════════════════════╝
                                     │  {数据集路径: 初始权重} JSON
                                     ▼
╔══════════════════ ③ 配采样比例 SAMPLING ════════════════════════════════════╗
║   adjust_sampling_ratio.py                                                   ║
║   读帧数 → GROUP_RULES 分组 → GROUP_CONFIG 占比 → power-law 分配             ║
║   产出: 调整后的 {数据集: 采样权重} JSON  ──────┐                            ║
╚═════════════════════════════════════════════════╪════════════════════════════╝
                                                   │
                                     ┌─────────────┴──────────────┐
                                     ▼                            ▼
╔════════════ ④ 验证/统计 ANALYZE ═══════╗   ╔════════ ④ 质检 QA ═══════════════╗
║ analyze_sampling_frames.py            ║   ║ check_chinese.py                 ║
║  权重占比 vs 实际采样占比 → CSV       ║   ║  查标注混入中文                  ║
║ dataset_statistics.py                 ║   ║ check_evalset_split.sh           ║
║  帧数/时长/prompt/recording → CSV     ║   ║  查 meta帧数 vs parquet行数一致  ║
╚═══════════════════════════════════════╝   ╚══════════════════════════════════╝
                                     │
                                     ▼
                          ✅ 训练就绪的数据集清单 + 采样权重
                             （喂给模型 co-training）
```

**一句话总览**：`服务端 → ①导出（普通/DAgger 两条线）→ ②切 train/val → ③配采样权重 → ④验证占比 & 质检 → 喂给训练`。

---

## 3. 每个脚本的输入 / 输出

约定：**CLI** = 命令行参数，**读** = 运行时读取的文件，**配置** = 脚本内硬编码配置，**产出** = 生成/写入的文件。

### 导出层

| 文件 | 输入 | 输出 |
|---|---|---|
| **export_dataset.py** | CLI: `--task-ids`/`--collection-ids`/各过滤项/`--output-dir`/`--api-url`（可选 `--user --password`）；读：后端 API（dataset 信息+预签名下载URL）、若已存在则复用 `output_dir/dataset.json` | `output_dir/` 下：`dataset.json`、`annotations.json`(若 `--fetch-annotations`)、`meta/{info.json, tasks.jsonl, episodes.jsonl, episodes_stats.jsonl}`、`data/chunk-*/episode_*.parquet`、`videos/chunk-*/<cam>/episode_*.mp4` |
| **export_dataset_normal_text_feature_split.py** | 同上（无登录/POST/中文选项） | 同上结构的 LeRobot 数据集 |
| **export_dataset_dagger.py** | 同上 + `--dagger-type policy/teleop`、`--action-field` | 同上 + `info.json` 写入 `dagger_type` 字段；额外产 `tasks.jsonl.backup`/`episodes.jsonl.backup`；过滤后重编号并清理空 chunk 目录 |
| **export_dataset_normal_text_feature_split.sh** | CLI: `$1`=PREFIX（默认 `/mnt/vepfs01/output`）；配置：`FILE_NAME_MAP/SUBDIR_MAP/DEVICE_MAP`、各开关 | 调 py → 数据集落到 `PREFIX/yifeng/resources/frontdesk/<SUBDIR>/<ID_名_设备>/`；并为每个数据集生成采样权重 `<同目录>/<ID_名_设备>.json`（内容 `{"名":1}`） |
| **export_dataset_dagger.sh** | 同上，配置含 `DAGGER_TYPE="teleop"`、`ACTION_FIELD` | 调 dagger py → 数据集落到 `PREFIX/yuhang/dagger/dataset_collection/<SUBDIR>/<DAGGER_TYPE>/...`；同样产采样权重 JSON |

### 切分层

| 文件 | 输入 | 输出 |
|---|---|---|
| **batch_split_datasets.py** | CLI: `--input-json`（`{数据集路径:权重}`）、`--root`、`--train-ratio`、`--seed`；读：每个数据集的 `meta/*` 和 `dataset.json` | 每个数据集旁生成 `<名>_split/train/`、`<名>_split/val/`（仅 meta + dataset.json + split_info.json，因 parquet/视频拷贝代码被注释掉了）；并在 input-json 同目录产 `<input>_train.json`、`<input>_val.json` |
| **batch_split_datasets.sh** | CLI 覆盖项（`--input-json/--root/--train-ratio/--force` 等）；交互确认 | 调 py，终端打印 train/val 两个 JSON 的路径 |

> ⚠️ 注意 batch_split_datasets.py：源码里 `_process_data_files` / `_process_video_files` 两行调用被注释了，所以它只切 meta 和生成清单 JSON，不实际搬运 parquet/视频。这是原版状态，按需取消注释才会真正切数据文件。

### 采样比例层

| 文件 | 输入 | 输出 |
|---|---|---|
| **adjust_sampling_ratio.py** | 配置：`INPUT_JSON`（`{数据集:权重}`）、`GROUP_RULES`、`GROUP_CONFIG`；读：各数据集 `meta/info.json` 的 `total_frames` | 写 `OUTPUT_JSON`（`{数据集: 调整后采样权重}`）；终端打印分组采样分析 |
| **analyze_sampling_frames.py** | 配置：`CONFIG_JSON`（`{数据集:权重}`）、`GROUP_RULES`、`BASE_PATH`；读：各 `meta/info.json` | 写 `OUTPUT_CSV`（权重占比/帧数占比/实际采样占比，多维度）；终端打印 |

### 统计 / 质检层

| 文件 | 输入 | 输出 |
|---|---|---|
| **dataset_statistics.py** | CLI: `--input`（`{数据集:权重}`）、`--base-dir`、`--output`、`--summary`；读：各数据集 `meta/{info,tasks,episodes}.jsonl` + `data/*.parquet` | 写详细 CSV（`--output`）+ 汇总 CSV（`--summary`）；都不传则默认生成 `<input>_statistics.csv`、`<input>_summary.csv`；终端打印摘要 |
| **check_chinese.py** | CLI: `input_json`、`--base-path`、`--export`；读：各数据集 `meta/tasks.jsonl` | 终端报告含中文的数据集；可选写 `--export` 指定的 JSON 报告；退出码 0(无中文)/1(有中文)/2(异常) |
| **check_evalset_split.sh** | CLI: `$1`=json 路径；读：各数据集 `meta/episodes.jsonl` + `data/**/*.parquet` | 仅终端输出：已检查/跳过数量、不一致数据集列表（无文件产出） |

### 贯穿全链路的"接口文件"

几乎所有环节都靠两类文件衔接：

- **`{数据集路径: 权重}` 的 JSON** —— 导出阶段每数据集产一个 `{名:1}`，人工汇总成大 JSON 后，依次喂给 切分 → 采样 → 统计 → 质检。
- **LeRobot 数据集目录**（`meta/` + `data/*.parquet` + `videos/*.mp4`）—— 导出产出，后续所有脚本读它的 `info.json`/`episodes.jsonl`/parquet。

---

## 4. 运行环境注意事项

- 这些 `.py` 用了 `list[int] | None` 语法，**需要 Python 3.10+**；若用 3.9 运行需在文件头加 `from __future__ import annotations`。
- 依赖：`pandas`、`requests`、`tqdm`、`pyarrow`（读写 parquet）。
- 导出"未质检"状态的数据（如采集阶段数据）时，需要加 `--include-unchecked`，否则后端默认只返回质检合格的数据，可能返回空。
- 这批文件是从服务器抓取的副本；少数文件末尾换行/注释空白与服务器原版可能有 ±1 行差异，不影响运行。
