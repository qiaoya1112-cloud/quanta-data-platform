"""
具身数据管理平台 - Demo Version
Embodied Data Management Platform (interactive prototype)

Framework: Flask + HTML/CSS (inline templates), Ant Design v4 theme (primary #1F80A0)
参考「Quanta 双盲评测平台」的代码规则与样式规则编写。这是交互演示 demo,非生产级应用。

三大模块:
  一、数据湖        (recording 级原料池, 左树右Tab)
  二、数据集        (生成+管理, 左树右Tab, 新建走列表按钮)
  三、自动化任务    (算子广场 / 任务编排 / 任务执行)

Usage:
  pip install flask
  python3 data_platform.py
  # Open http://localhost:5002
"""

import os
import json
import datetime
import re
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)
app.secret_key = "embodied-data-platform-demo"

# ════════════════════════════════════════════════════════════════
# Section 1: Mock Data
# ════════════════════════════════════════════════════════════════

# —— 数据湖: recording 级原料 (按 task 聚合) ——
TASKS = [
    {"id": "t1", "name": "clean_the_whiteboard", "zh": "擦白板"},
    {"id": "t2", "name": "tidy_the_desk", "zh": "整理桌面"},
    {"id": "t3", "name": "water_the_plant", "zh": "浇花"},
]

# recording: 1 条采集 ≈ 1 episode (parquet + 3 路 mp4)
RECORDINGS = [
    # task t1
    {"id": 120489, "task": "t1", "collection": 3635, "robot": "moz1", "type": "采集", "frames": 1434, "fps": 30, "dur": 47.8, "at": "2026-05-21 10:12", "qa": "pass", "life": "active"},
    {"id": 120502, "task": "t1", "collection": 3635, "robot": "moz1", "type": "采集", "frames": 1042, "fps": 30, "dur": 34.7, "at": "2026-05-21 10:31", "qa": "pass", "life": "active"},
    {"id": 120513, "task": "t1", "collection": 3635, "robot": "moz1", "type": "采集", "frames": 979, "fps": 30, "dur": 32.6, "at": "2026-05-21 10:48", "qa": "warn", "life": "active"},
    {"id": 120521, "task": "t1", "collection": 3653, "robot": "moz1", "type": "dagger", "frames": 56, "fps": 30, "dur": 1.9, "at": "2026-05-22 09:05", "qa": "fail", "life": "quarantined"},
    {"id": 120532, "task": "t1", "collection": 3653, "robot": "moz1", "type": "采集", "frames": 1310, "fps": 30, "dur": 43.7, "at": "2026-05-22 09:24", "qa": "pass", "life": "active"},
    # task t2
    {"id": 121005, "task": "t2", "collection": 3702, "robot": "moz1", "type": "采集", "frames": 1188, "fps": 30, "dur": 39.6, "at": "2026-05-24 14:02", "qa": "pass", "life": "active"},
    {"id": 121014, "task": "t2", "collection": 3702, "robot": "moz1", "type": "采集", "frames": 1402, "fps": 30, "dur": 46.7, "at": "2026-05-24 14:20", "qa": "pass", "life": "active"},
    {"id": 121023, "task": "t2", "collection": 3702, "robot": "moz1", "type": "test", "frames": 905, "fps": 30, "dur": 30.2, "at": "2026-05-24 14:39", "qa": "warn", "life": "active"},
    # task t3
    {"id": 121120, "task": "t3", "collection": 3760, "robot": "moz1", "type": "采集", "frames": 1521, "fps": 30, "dur": 50.7, "at": "2026-05-27 11:10", "qa": "pass", "life": "active"},
    {"id": 121131, "task": "t3", "collection": 3760, "robot": "moz1", "type": "采集", "frames": 1098, "fps": 30, "dur": 36.6, "at": "2026-05-27 11:28", "qa": "pass", "life": "active"},
]

CAMERAS = ["cam_high", "cam_left_wrist", "cam_right_wrist"]
# 14 维双臂特征 (左臂7 + 右臂7), 用于轨迹预览曲线分组
ARM_DIMS = {
    "左臂关节 (leftarm_state/cmd_joint_pos)": ["joint0", "joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
    "右臂关节 (rightarm_state/cmd_joint_pos)": ["joint0", "joint1", "joint2", "joint3", "joint4", "joint5", "joint6"],
    "夹爪 (gripper_cmd/state_pos)": ["left_gripper", "right_gripper"],
}

# —— episode 标签体系 (场景 / 技能 / 质量) ——
TAG_DEFS = [
    ("sc_whiteboard", "白板区", "场景"), ("sc_desk", "桌面", "场景"), ("sc_plant", "绿植区", "场景"),
    ("sk_wipe", "擦拭", "技能"), ("sk_pick", "抓取", "技能"), ("sk_place", "放置", "技能"), ("sk_pour", "倒水", "技能"),
    ("q_high", "高质量", "质量"), ("q_review", "待复核", "质量"),
]
TAG_LABEL = {tid: lab for tid, lab, grp in TAG_DEFS}
TAG_GROUP_ORDER = ["场景", "技能", "质量"]
TASK_TAGS = {
    "t1": ["sc_whiteboard", "sk_wipe"],
    "t2": ["sc_desk", "sk_pick", "sk_place"],
    "t3": ["sc_plant", "sk_pour", "sk_pick"],
}

def rec_tags(r):
    """每条 recording(=episode) 的标签: 场景+技能(按 task) + 质量(按质检)。"""
    tags = list(TASK_TAGS.get(r["task"], []))
    tags.append("q_high" if r["qa"] == "pass" else "q_review")
    return tags

def rec_tag_labels(r):
    return [TAG_LABEL[t] for t in rec_tags(r)]

# —— 标签体系 (标签管理页) ——
TAG_SYSTEM = {
    "version": "1.0.0",
    "dimensions": [
        {"name": "动作标签", "en": "Action Tags", "desc": "机器人可执行的原子动作", "leaves": [
            "拿取", "放置", "放入", "取出", "抽出", "取下", "捡起", "靠放", "放倒", "立起", "叠放", "扔", "递送", "换持",
            "移动", "拖拽", "推动", "拉动", "旋转", "翻转", "复位", "交换", "折叠", "展开", "平铺", "撑开", "抚平", "拉直",
            "卷", "挤", "拧干", "打结", "打开", "关闭", "拉开", "推开", "翻开", "掀起", "拧开", "拉上", "合上", "拆分",
            "安装", "插入", "扣紧", "拧紧", "组装", "贴", "揭下", "倒", "搅拌", "翻炒", "刮", "切", "剥", "撕", "泡", "撒",
            "盖", "穿戴", "套", "包裹", "浇水", "磨", "铲", "清洗", "冲洗", "刷洗", "搓洗", "擦拭", "扫", "清理", "启动",
            "按压", "拨动", "调整", "整理", "收纳", "抖动", "拍打", "悬挂", "书写"]},
        {"name": "场景标签", "en": "Scene Tags", "desc": "采集/任务所处场景", "leaves": [
            "厨房", "客厅", "卧室", "书房", "餐厅", "卫生间", "阳台", "玄关"]},
        {"name": "物体标签", "en": "Object Tags", "desc": "操作对象的物体分类", "groups": [
            {"category": "包装类", "items": ["包装袋", "包装盒", "湿巾包装袋", "酒精棉片包装袋", "塑料袋", "纸盒", "纸袋", "礼品盒", "快递盒", "泡沫盒", "保鲜袋", "密封袋"]},
            {"category": "容器类", "items": ["塑料杯", "陶瓷杯", "玻璃杯", "马克杯", "保温杯", "纸杯", "编织篮", "收纳篮", "托盘", "餐盘", "碗", "碟子", "盒子", "罐子", "瓶子", "水壶", "茶壶", "花瓶", "垃圾桶", "收纳盒"]},
            {"category": "工具类", "items": ["剪刀", "螺丝刀", "钳子", "扳手", "笔", "铅笔", "记号笔", "刷子", "夹子", "订书机", "胶带", "胶水", "尺子", "美工刀", "锤子", "起子", "镊子", "量杯", "漏斗"]},
            {"category": "布料类", "items": ["布块", "毛巾", "抹布", "垫子", "桌垫", "餐巾", "手帕", "围裙", "袖套", "地毯", "窗帘", "床单", "枕套", "被套", "衣服", "T恤", "裤子", "袜子", "手套"]},
            {"category": "机械类", "items": ["机械臂", "金属架", "链条", "齿轮", "螺丝", "螺母", "弹簧", "轴承", "电机", "传感器", "电路板", "导线", "插头", "开关", "按钮"]},
            {"category": "日用品", "items": ["钥匙串", "挂绳", "雨伞", "鞋子", "皮鞋", "运动鞋", "拖鞋", "皮带", "钱包", "手表", "眼镜", "手机", "充电器", "耳机", "遥控器", "电池", "灯泡", "蜡烛", "香皂", "洗发水", "牙刷", "牙膏", "梳子", "镜子"]},
            {"category": "食物类", "items": ["面包", "芝士片", "水果", "苹果", "香蕉", "橙子", "葡萄", "蔬菜", "番茄", "黄瓜", "胡萝卜", "土豆", "肉类", "鸡肉", "牛肉", "鱼", "虾", "鱼豆腐", "木签", "饼干", "蛋糕", "糖果", "巧克力", "薯片", "坚果", "饮料", "牛奶", "果汁"]},
            {"category": "文具类", "items": ["书本", "笔记本", "文件夹", "信封", "便签", "回形针", "图钉", "橡皮", "修正带", "计算器", "印章", "名片", "卡片"]},
            {"category": "厨房用品", "items": ["锅", "平底锅", "炒锅", "汤锅", "刀", "菜刀", "水果刀", "砧板", "筷子", "勺子", "叉子", "铲子", "漏勺", "打蛋器", "开瓶器", "保鲜膜", "锡纸", "烤盘", "微波炉盒"]},
            {"category": "电子产品", "items": ["手机", "平板", "笔记本电脑", "键盘", "鼠标", "U盘", "硬盘", "相机", "音箱", "耳机", "充电宝", "数据线", "适配器"]},
            {"category": "玩具类", "items": ["积木", "拼图", "玩偶", "毛绒玩具", "小汽车", "球", "魔方", "飞盘", "风筝", "气球"]},
            {"category": "办公用品", "items": ["文件", "文件夹", "档案袋", "打印纸", "复印纸", "标签", "胶带座", "笔筒", "名片夹", "证件", "工牌"]},
        ]},
    ],
}

# —— 数据集管理: 业务语义目录 (用户可自建管理) ——
V2_FOLDERS = ["预训练", "后训练", "自定义01", "自定义02"]
V2_FOLDER_MAP = {
    "预训练": ["ds1", "ds4", "ds5", "ds6"],
    "后训练": ["ds2", "ds7", "ds8", "ds9"],
    "自定义01": ["ds3", "ds10"],
    "自定义02": ["ds11", "ds12"],
}

# —— 数据集: 生成成品 ——
DATASETS = [
    {
        "id": "ds1", "name": "clean_whiteboard_v3", "version": "v3", "type": "train",
        "robot": "moz1", "fps": 30, "episodes": 48, "frames": 52310, "quality": "pass",
        "status": "生效中", "tos": "tos://embodied/datasets/clean_whiteboard_v3/",
        "created": "2026-05-28 16:40", "owner": "joanna.qiao",
        "recordings": [120489, 120502, 120532], "tasks": ["t1"],
        "recipe": {"groups": [{"name": "擦白板-采集", "weight": 1.0, "frames": 52310, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.95, "seed": 42},
        "src": "采集任务 #3635 / #3653", "used_by": ["train_job_0421 (Spirit v1.6-beta)", "train_job_0455 (Spirit v1.6-rc1)"],
    },
    {
        "id": "ds2", "name": "tidy_desk_mix_v1", "version": "v1", "type": "train",
        "robot": "moz1", "fps": 30, "episodes": 36, "frames": 41880, "quality": "warn",
        "status": "待发布", "tos": "—",
        "created": "2026-06-01 09:15", "owner": "joanna.qiao",
        "recordings": [121005, 121014], "tasks": ["t2"],
        "recipe": {"groups": [{"name": "整理桌面-采集", "weight": 0.7, "frames": 29300, "ratio": 0.7}, {"name": "整理桌面-dagger", "weight": 0.3, "frames": 12580, "ratio": 0.3}], "alpha": 0.6, "train_ratio": 0.9, "seed": 7},
        "src": "采集任务 #3702", "used_by": [],
    },
    {
        "id": "ds3", "name": "whiteboard_eval_bench", "version": "v1", "type": "eval-benchmark",
        "robot": "moz1", "fps": 30, "episodes": 12, "frames": 13200, "quality": "pass",
        "status": "生效中", "tos": "tos://embodied/datasets/whiteboard_eval_bench/",
        "created": "2026-05-30 18:02", "owner": "joanna.qiao",
        "recordings": [120513], "tasks": ["t1"],
        "recipe": {"groups": [{"name": "擦白板-留出评测", "weight": 1.0, "frames": 13200, "ratio": 1.0}], "alpha": 1.0, "train_ratio": 0.0, "seed": 42},
        "src": "专用评测采集 #3653", "used_by": ["eval_job_0510 (双盲评测)"],
    },
    {"id": "ds4", "name": "whiteboard_pretrain_mix", "version": "v2", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 52, "frames": 56800, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/whiteboard_pretrain_mix/",
     "created": "2026-05-26 14:10", "owner": "Lance Li", "recordings": [120489, 120502, 120532], "tasks": ["t1"],
     "recipe": {"groups": [{"name": "擦白板-采集", "weight": 1.0, "frames": 56800, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.95, "seed": 42},
     "src": "采集任务 #3635 / #3653", "used_by": ["train_job_0388 (Spirit v1.5)"]},
    {"id": "ds5", "name": "desk_pretrain", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 30, "frames": 35200, "quality": "warn", "status": "待发布", "tos": "—",
     "created": "2026-05-29 11:42", "owner": "Wei Zhang", "recordings": [121005, 121014], "tasks": ["t2"],
     "recipe": {"groups": [{"name": "整理桌面-采集", "weight": 1.0, "frames": 35200, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.95, "seed": 1},
     "src": "采集任务 #3702", "used_by": []},
    {"id": "ds6", "name": "plant_pour_pretrain", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 26, "frames": 31900, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/plant_pour_pretrain/",
     "created": "2026-05-31 09:20", "owner": "Min Chen", "recordings": [121120, 121131], "tasks": ["t3"],
     "recipe": {"groups": [{"name": "浇花-采集", "weight": 1.0, "frames": 31900, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.95, "seed": 3},
     "src": "采集任务 #3760", "used_by": []},
    {"id": "ds7", "name": "whiteboard_sft", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 24, "frames": 26400, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/whiteboard_sft/",
     "created": "2026-06-02 16:05", "owner": "joanna.qiao", "recordings": [120513, 120532], "tasks": ["t1"],
     "recipe": {"groups": [{"name": "擦白板-精选", "weight": 1.0, "frames": 26400, "ratio": 1.0}], "alpha": 0.8, "train_ratio": 0.95, "seed": 42},
     "src": "采集任务 #3653", "used_by": ["train_job_0461 (Spirit v1.6-rc1)"]},
    {"id": "ds8", "name": "desk_dagger_sft", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 18, "frames": 19800, "quality": "warn", "status": "待发布", "tos": "—",
     "created": "2026-06-03 10:30", "owner": "Wei Zhang", "recordings": [121023], "tasks": ["t2"],
     "recipe": {"groups": [{"name": "整理桌面-dagger", "weight": 1.0, "frames": 19800, "ratio": 1.0}], "alpha": 0.8, "train_ratio": 0.9, "seed": 11},
     "src": "DAgger 采集 #3702", "used_by": []},
    {"id": "ds9", "name": "mix_finetune", "version": "v2", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 40, "frames": 44200, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/mix_finetune/",
     "created": "2026-06-03 19:50", "owner": "joanna.qiao", "recordings": [120489, 121005], "tasks": ["t1", "t2"],
     "recipe": {"groups": [{"name": "擦白板", "weight": 0.5, "frames": 22100, "ratio": 0.5}, {"name": "整理桌面", "weight": 0.5, "frames": 22100, "ratio": 0.5}], "alpha": 0.6, "train_ratio": 0.95, "seed": 42},
     "src": "采集任务 #3635 / #3702", "used_by": ["train_job_0470 (Spirit v1.6-rc1)"]},
    {"id": "ds10", "name": "custom_eval_set", "version": "v1", "type": "eval-benchmark", "robot": "moz1", "fps": 30,
     "episodes": 10, "frames": 11000, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/custom_eval_set/",
     "created": "2026-06-01 13:00", "owner": "Min Chen", "recordings": [121131], "tasks": ["t3"],
     "recipe": {"groups": [{"name": "浇花-留出评测", "weight": 1.0, "frames": 11000, "ratio": 1.0}], "alpha": 1.0, "train_ratio": 0.0, "seed": 42},
     "src": "专用评测采集 #3760", "used_by": ["eval_job_0521 (双盲评测)"]},
    {"id": "ds11", "name": "ablation_small", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 8, "frames": 8800, "quality": "warn", "status": "待发布", "tos": "—",
     "created": "2026-06-04 08:15", "owner": "Lance Li", "recordings": [120502], "tasks": ["t1"],
     "recipe": {"groups": [{"name": "擦白板-小样本", "weight": 1.0, "frames": 8800, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.9, "seed": 99},
     "src": "采集任务 #3635", "used_by": []},
    {"id": "ds12", "name": "smoke_test", "version": "v1", "type": "train", "robot": "moz1", "fps": 30,
     "episodes": 6, "frames": 6600, "quality": "pass", "status": "生效中", "tos": "tos://embodied/datasets/smoke_test/",
     "created": "2026-06-04 09:02", "owner": "joanna.qiao", "recordings": [121014], "tasks": ["t2"],
     "recipe": {"groups": [{"name": "整理桌面-冒烟", "weight": 1.0, "frames": 6600, "ratio": 1.0}], "alpha": 0.6, "train_ratio": 0.95, "seed": 5},
     "src": "采集任务 #3702", "used_by": []},
]

# DOCTOR 质检检查项 (复用 episode_stats / check 脚本逻辑)
def doctor_checks(quality):
    base = [
        ("Metadata & Format Compliance", "pass", "info.json / 字段 schema 校验通过"),
        ("Temporal Consistency", "pass", "时间戳单调, 无跳变"),
        ("Frame Integrity (掉帧)", "pass", "meta 帧数 = parquet 行数 (check_evalset_split)"),
        ("Frozen Action (冻结动作)", "pass", "无某维 std≈0 (psi 维已知全 0, 已豁免)"),
        ("Camera Resolution", "pass", "三路相机均 240×320 一致"),
        ("Annotation 合规 (中文混入)", "pass", "tasks.jsonl 无中文混入 (check_chinese)"),
    ]
    if quality == "warn":
        base[3] = ("Frozen Action (冻结动作)", "warn", "2 个 episode 右臂全程 std≈0, 疑似静止, 建议复核")
        base[2] = ("Frame Integrity (掉帧)", "warn", "1 个 episode meta 1402 / parquet 1399, 缺 3 帧")
    if quality == "fail":
        base[2] = ("Frame Integrity (掉帧)", "fail", "缺帧严重, 必须修复")
    return base

# —— 自动化任务: 算子 / 编排 / 执行 ——
# 算子 = frontdesk_scripts 里一个「原子处理能力」的封装 (调度类 .sh 不作算子, 归任务编排)
OPERATORS = [
    # 切分
    {"id": "op_split", "name": "切分 Split", "ident": "batch_split", "script": "batch_split_datasets.py", "cat": "切分", "creator": "joanna.qiao",
     "desc": "把数据集随机切 train/val: 按 train_ratio 划分 episode → 重编号 → 改写 meta(info/episodes/stats) → 输出 _split/train、_split/val 及清单 JSON",
     "params": "--train-ratio 0.95 / --seed 42 / --force",
     "returns": "_split/train、_split/val + xxx_train.json / xxx_val.json 清单",
     "io_in": "LeRobot 数据集 + 权重清单 JSON", "io_out": "train/val 数据集 + 清单"},
    # 配方
    {"id": "op_sample", "name": "采样配比 Sampling", "ident": "adjust_sampling", "script": "adjust_sampling_ratio.py", "cat": "配方", "creator": "Wei Zhang",
     "desc": "采样比例核心算法: 读权重 JSON + 各数据集帧数 → GROUP_RULES 分组 → GROUP_CONFIG 设占比 → power-law(alpha) 组内分配 → 写回采样权重",
     "params": "INPUT_JSON / GROUP_RULES / GROUP_CONFIG",
     "returns": "{数据集: 调整后采样权重} JSON",
     "io_in": "{数据集: 权重} JSON", "io_out": "{数据集: 采样权重} JSON"},
    {"id": "op_sample_verify", "name": "采样验证 Validate", "ident": "analyze_sampling", "script": "analyze_sampling_frames.py", "cat": "配方", "creator": "Wei Zhang",
     "desc": "采样配套验证: 算「权重占比 vs 帧数占比 vs 实际采样帧数占比」, 按主类别/组/子类别多维汇总 → 打印 + 导出 CSV",
     "params": "CONFIG_JSON / OUTPUT_CSV / GROUP_RULES",
     "returns": "占比对比 CSV (权重/帧数/实际采样)",
     "io_in": "{数据集: 权重} JSON", "io_out": "占比对比 CSV"},
    # 统计
    {"id": "op_stats", "name": "统计 Statistics", "ident": "dataset_stats", "script": "dataset_statistics.py", "cat": "统计", "creator": "Min Chen",
     "desc": "全面统计: 扫 parquet 统计每 task_folder 总帧数、每 prompt 帧数占比+recording 列表、换算时长 → 详细 CSV + 汇总 CSV",
     "params": "--input / --output / --summary",
     "returns": "详细 CSV + 汇总 CSV",
     "io_in": "{数据集: 权重} JSON", "io_out": "统计 CSV"},
    # 质检
    {"id": "op_check_chinese", "name": "中文标注质检", "ident": "check_chinese", "script": "check_chinese.py", "cat": "质检", "creator": "joanna.qiao",
     "desc": "扫各数据集 tasks.jsonl, 用正则查英文标注里混入的中文, 报告 + 导出 JSON (退出码区分有无中文)",
     "params": "input_json / -v / --export",
     "returns": "含中文的数据集报告 JSON + 退出码(0/1/2)",
     "io_in": "LeRobot 数据集 (tasks.jsonl)", "io_out": "质检报告 JSON"},
    {"id": "op_check_evalset", "name": "完整性质检", "ident": "check_evalset", "script": "check_evalset_split.py", "cat": "质检", "creator": "Min Chen",
     "desc": "对比每个数据集 episodes.jsonl 记录帧数 vs 实际 parquet 行数, 查数据完整性 / 缺帧",
     "params": "input_json",
     "returns": "一致性报告: 已检查/跳过数 + 缺帧数据集列表",
     "io_in": "LeRobot 数据集 (episodes.jsonl + parquet)", "io_out": "完整性报告"},
]

PIPELINES = [
    {"id": "pl1", "name": "标准训练数据流水线", "creator": "joanna.qiao", "status": "已保存", "updated": "2026-06-03 18:22",
     "stages": ["op_split", "op_sample", "op_sample_verify", "op_check_evalset", "op_check_chinese"],
     "schedules": ["每天 02:00", "每周一 06:00"],
     "desc": "导出 → 切分 → 配比 → 采样验证 → 完整性质检 → 中文质检, 一键生成训练就绪数据集"},
    {"id": "pl2", "name": "DAgger 数据流水线", "creator": "Wei Zhang", "status": "已保存", "updated": "2026-06-02 10:05",
     "stages": ["op_check_evalset", "op_stats"],
     "schedules": ["每天 22:00"],
     "desc": "DAgger 导出 → 完整性质检 → 统计"},
]

RUNS = [
    {"id": "run_0612a", "pipeline": "pl1", "name": "标准训练数据流水线", "target": "clean_whiteboard_v4", "status": "running", "progress": 62, "stage": "采样配比 (3/5)", "at": "2026-06-04 01:40", "dur": "进行中 8m", "trigger": "manual", "by": "joanna.qiao"},
    {"id": "run_0611b", "pipeline": "pl1", "name": "标准训练数据流水线", "target": "tidy_desk_mix_v1", "status": "done", "progress": 100, "stage": "完成", "at": "2026-06-01 09:02", "dur": "13m 24s", "trigger": "scheduled"},
    {"id": "run_0610c", "pipeline": "pl2", "name": "DAgger 数据流水线", "target": "whiteboard_dagger_v2", "status": "failed", "progress": 40, "stage": "质检 Doctor (FAIL: 缺帧)", "at": "2026-05-31 20:11", "dur": "4m 02s", "trigger": "scheduled"},
    {"id": "run_0609d", "pipeline": "pl1", "name": "标准训练数据流水线", "target": "whiteboard_eval_bench", "status": "done", "progress": 100, "stage": "完成", "at": "2026-05-30 17:50", "dur": "9m 41s", "trigger": "manual", "by": "Min Chen"},
]

# ════════════════════════════════════════════════════════════════
# Section 2: HTML / CSS Templates
# ════════════════════════════════════════════════════════════════

BASE_CSS = """
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif; }
.ant-btn,.ant-input,.ant-select-selector,.ant-card,.ant-tag,.ant-alert,.ant-table-wrapper { border-radius:8px !important; }
.ant-btn-primary,.ant-btn-primary:focus { background:#1F80A0; border-color:#1F80A0; }
.ant-btn-primary:hover { background:#176a88; border-color:#176a88; }
a { color:#1F80A0; text-decoration:none; } a:hover { color:#176a88; }

/* ── Layout ── */
.q-layout { display:flex; min-height:calc(100vh - 52px); background:#001529; }
/* ── 顶部导航 ── */
.top-nav { position:fixed; top:0; left:0; right:0; height:52px; background:#001529; display:flex; align-items:center; gap:0; padding:0; z-index:200; }
.top-nav .tn-brand { width:192px; box-sizing:border-box; padding:0 16px; flex:none; display:flex; align-items:center; gap:10px; color:rgba(255,255,255,0.92); font-weight:600; font-size:15px; }
.top-nav .tn-brand .logo-icon { width:30px; height:30px; background:linear-gradient(135deg,#1F80A0,#36cfc9); border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:15px; font-weight:700; color:#fff; }
.top-nav .tn-nav { display:flex; align-items:center; gap:8px; height:100%; }
.top-nav .tn-item { position:relative; display:flex; align-items:center; height:100%; padding:0 8px; color:rgba(255,255,255,0.6); font-size:14px; cursor:pointer; transition:color 0.15s; }
.top-nav .tn-item:hover { color:rgba(255,255,255,0.9); }
.top-nav .tn-item.active { color:#fff; font-weight:600; }
.top-nav .tn-item.active::after { content:''; position:absolute; left:50%; transform:translateX(-50%); bottom:0; width:18px; height:3px; background:#1F80A0; border-radius:2px; }
.top-nav .tn-sep { width:1px; height:18px; background:rgba(255,255,255,0.16); margin:0 8px; }
.top-nav .tn-right { margin-left:auto; margin-right:20px; color:rgba(255,255,255,0.55); font-size:12px; border:1px solid rgba(255,255,255,0.22); padding:2px 12px; border-radius:11px; letter-spacing:0.5px; }
.q-layout { padding-top:52px; }
.q-sider { width:192px; min-width:192px; background:#001529; position:fixed; top:52px; left:0; bottom:0; z-index:100; display:flex; flex-direction:column; overflow-y:auto; }
.q-sider .logo { height:64px; display:flex; align-items:center; gap:10px; padding:0 16px; border-bottom:1px solid rgba(255,255,255,0.08); }
.q-sider .logo-icon { width:36px; height:36px; background:linear-gradient(135deg,#1F80A0,#36cfc9); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700; color:#fff; }
.q-sider .logo-text { font-size:14px; font-weight:600; color:rgba(255,255,255,0.9); }
.q-sider .nav-section { padding:8px 0; flex:1; }
.q-sider .nav-label { padding:14px 24px 4px; font-size:11px; color:rgba(255,255,255,0.35); text-transform:uppercase; letter-spacing:0.8px; font-weight:600; }
.q-sider .nav-item { display:flex; align-items:center; gap:10px; padding:10px 24px; color:rgba(255,255,255,0.65); font-size:14px; transition:all 0.2s; margin:2px 8px; border-radius:6px; }
.q-sider .nav-item:hover { color:#fff; background:rgba(255,255,255,0.06); }
.q-sider .nav-item.active { color:#fff; background:#1F80A0; }
.q-sider .nav-item .icon { width:16px; text-align:center; }
.q-sider .nav-item.sub { padding-left:40px; font-size:13px; }
.q-sider .user-block { padding:12px 16px; border-top:1px solid rgba(255,255,255,0.08); display:flex; align-items:center; gap:10px; }
.q-sider .user-avatar { width:32px; height:32px; border-radius:50%; background:#1F80A0; color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:600; }
.q-sider .user-name { color:rgba(255,255,255,0.85); font-size:13px; font-weight:500; }
.q-sider .user-role { color:rgba(255,255,255,0.35); font-size:11px; }

.q-main { margin-left:192px; flex:1; min-width:0; background:#f0f2f5; min-height:calc(100vh - 52px); border-top-left-radius:8px; transition:margin-left 0.2s, margin-right 0.22s; }
.q-sider { transition:width 0.2s, min-width 0.2s; }
/* 折叠按钮: 底部用户旁, 仅图标 */
.sider-collapse-btn { margin-left:auto; cursor:pointer; color:rgba(255,255,255,0.45); width:26px; height:26px; display:flex; align-items:center; justify-content:center; border-radius:6px; font-size:15px; flex:none; }
.sider-collapse-btn:hover { color:#fff; background:rgba(255,255,255,0.08); }
.sc-exp { display:none; }
/* 折叠态: icon rail (只留图标) */
body.sider-collapsed .q-sider { width:64px; min-width:64px; }
body.sider-collapsed .q-main { margin-left:64px; }
body.sider-collapsed .logo-text,
body.sider-collapsed .nav-label,
body.sider-collapsed .nav-txt,
body.sider-collapsed .user-info { display:none; }
body.sider-collapsed .nav-item { justify-content:center; padding-left:0; padding-right:0; gap:0; }
body.sider-collapsed .logo { justify-content:center; padding:0; }
body.sider-collapsed .user-block { flex-direction:column; gap:10px; padding:12px 0; }
body.sider-collapsed .sider-collapse-btn { margin-left:0; }
body.sider-collapsed .sc-col { display:none; }
body.sider-collapsed .sc-exp { display:inline; }
.q-header { background:#fff; padding:0 24px; height:48px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #f0f0f0; position:sticky; top:0; z-index:50; }
.q-header .crumb { font-size:14px; color:rgba(0,0,0,0.45); }
.q-header .crumb b { color:rgba(0,0,0,0.85); font-weight:500; }
.q-content { padding:24px; }

/* ── Stat cards ── */
.stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:16px; margin-bottom:24px; }
.stat-card { background:#fff; border-radius:8px; padding:18px 22px; border:1px solid #f0f0f0; }
.stat-card .stat-label { font-size:13px; color:rgba(0,0,0,0.45); margin-bottom:4px; }
.stat-card .stat-value { font-size:28px; font-weight:600; color:rgba(0,0,0,0.85); }
.stat-card .stat-sub { font-size:12px; color:rgba(0,0,0,0.45); margin-top:4px; }

/* ── Card ── */
.card { background:#fff; border-radius:8px; border:1px solid #f0f0f0; padding:20px 24px; margin-bottom:16px; }
.card h3 { font-size:16px; font-weight:500; margin:0 0 16px; color:rgba(0,0,0,0.85); }
.card h4 { font-size:14px; font-weight:500; margin:0 0 12px; color:rgba(0,0,0,0.85); }
.muted { color:rgba(0,0,0,0.45); font-size:13px; }

/* ── Filter bar ── */
.filter-bar { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
.filter-bar input,.filter-bar select { padding:5px 12px; height:34px; border:1px solid #d9d9d9; border-radius:8px; font-size:14px; color:rgba(0,0,0,0.85); outline:none; background:#fff; }
.filter-bar input:focus,.filter-bar select:focus { border-color:#1F80A0; box-shadow:0 0 0 2px rgba(31,128,160,0.12); }
/* ---- 数据查询: 筛选区 ---- */
.q-filters { position:relative; background:#fff; border:1px solid #f0f0f0; border-radius:10px; padding:18px 20px; margin-bottom:16px; }
.q-filter-row { display:flex; gap:14px 18px; flex-wrap:wrap; align-items:flex-end; }
.q-field { display:flex; flex-direction:column; gap:6px; }
.q-field > label { font-size:12px; color:rgba(0,0,0,0.45); padding-left:1px; }
.q-field select, .q-field input:not([type=checkbox]) { height:36px; min-width:158px; box-sizing:border-box; border:1px solid #e2e4e8; border-radius:8px; padding:0 12px; font-size:13.5px; color:rgba(0,0,0,0.85); background:#fff; outline:none; }
.q-field select { padding-right:32px; cursor:pointer; -webkit-appearance:none; appearance:none; background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.4' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>"); background-repeat:no-repeat; background-position:right 12px center; }
.q-field select:hover, .q-field input:hover { border-color:#bcc0c6; }
.q-field select:focus, .q-field input:focus { border-color:#1F80A0; box-shadow:0 0 0 2px rgba(31,128,160,0.12); }
.q-field select.has-value, .q-field input.has-value { border-color:#1F80A0; color:#1F80A0; background-color:#f3f9fb; }
/* 字段内多选下拉 */
.q-field .ms-wrap .ms-trigger { height:36px; min-width:158px; border-color:#e2e4e8; }
.q-field .ms-wrap .ms-trigger.has-value { border-color:#1F80A0; color:#1F80A0; background:#f3f9fb; }
.ms-grp { padding:8px 14px 3px; font-size:11px; color:rgba(0,0,0,0.4); font-weight:600; }
.q-table-scroll { overflow-x:auto; }
.q-table-scroll table { min-width:760px; }
.q-table-scroll th, .q-table-scroll td { white-space:nowrap; }
.q-table-scroll td .tg { white-space:nowrap; }
/* 时间区间 */
.q-range { display:flex; align-items:center; gap:8px; }
.q-range input[type=date] { min-width:140px; }
.q-range-sep { color:rgba(0,0,0,0.35); }
.q-actions { display:flex; gap:8px; margin-left:auto; align-items:flex-end; }
.q-field.grow { flex:1 1 240px; min-width:220px; }
.q-field.grow > input, .q-field.grow .ms-wrap, .q-field.grow .ms-wrap .ms-trigger { width:100%; }
/* 高级筛选行: 各项撑满整行 */
.q-adv-row .q-field { flex:1 1 0; min-width:0; }
.q-adv-row .q-field select, .q-adv-row .q-field > input, .q-adv-row .q-field .ms-wrap, .q-adv-row .q-field .ms-wrap .ms-trigger { width:100%; min-width:0; }
.q-adv-row .q-field .q-range { width:100%; }
.q-adv-row .q-field .q-range input { flex:1; min-width:0; }
.drawer-body .q-adv-row { margin-top:14px; }
.q-filter-tools { display:flex; gap:8px; align-items:center; justify-content:flex-end; margin-top:14px; padding-top:14px; border-top:1px solid #f0f0f0; }
.tools-divider { width:1px; height:22px; background:#e2e4e8; margin:0 6px; }
.q-adv-note { flex-basis:100%; font-size:12px; margin-top:2px; }
/* 配方助手 */
.rc-intro { font-size:12.5px; color:rgba(0,0,0,0.6); line-height:1.7; margin-bottom:8px; }
.rc-sec { font-size:13px; font-weight:600; color:rgba(0,0,0,0.85); margin:18px 0 10px; padding-left:8px; border-left:3px solid #1F80A0; display:flex; gap:8px; align-items:baseline; }
.rc-sec .muted { font-weight:400; font-size:12px; }
.rc-row { margin-bottom:14px; }
.rc-label { display:flex; justify-content:space-between; font-size:13px; margin-bottom:5px; }
.rc-label .rc-pct { color:#1F80A0; font-weight:600; font-family:'SF Mono',Menlo,monospace; }
.rc-track { position:relative; height:6px; background:#eef2f4; border-radius:3px; cursor:ew-resize; }
.rc-base-mark { position:absolute; top:-3px; bottom:-3px; width:2px; background:#c2ccd2; left:50%; }
.rc-fill { position:absolute; left:0; top:0; height:100%; background:linear-gradient(90deg,#3aa6c4,#1F80A0); border-radius:3px; min-width:6px; }
.rc-handle { position:absolute; right:-6px; top:50%; width:12px; height:12px; margin-top:-6px; background:#fff; border:2px solid #1F80A0; border-radius:50%; box-shadow:0 1px 3px rgba(0,0,0,0.2); cursor:ew-resize; }
.rc-sub { font-size:11.5px; color:rgba(0,0,0,0.4); margin-top:4px; }
.rc-sub b { color:rgba(0,0,0,0.7); }
.rc-foot { border-top:1px solid #f0f0f0; padding:14px 16px; display:flex; flex-direction:column; gap:10px; }
.rc-count { font-size:14px; color:rgba(0,0,0,0.85); }
.rc-count b { color:#1F80A0; font-size:18px; }
.ai-fab, .recipe-btn { display:inline-flex; align-items:center; gap:6px; height:34px; padding:0 14px; border-radius:8px; border:1px solid #e2e4e8; cursor:pointer; font-size:13.5px; color:rgba(0,0,0,0.7); background:#fff; }
.ai-fab:hover, .recipe-btn:hover { border-color:#1F80A0; color:#1F80A0; background:#f7fbfc; }
.ai-fab span, .recipe-btn span { font-size:14px; }
.ai-fab .ic-ai { color:#9b59b6; }
/* ---- AI 辅助 侧栏 (固定推开, 不占页面宽度, 满屏高) ---- */
.ai-side { position:fixed; top:52px; right:0; bottom:0; width:0; overflow:hidden; background:#fff; border-left:1px solid #eee; box-shadow:-6px 0 24px rgba(0,0,0,0.07); transition:width 0.22s ease; z-index:1000; }
.ai-side.active { width:400px; }
.ai-inner { position:absolute; top:0; right:0; width:400px; height:100%; display:flex; flex-direction:column; }
.q-main.ai-pushed { margin-right:400px; }
.ai-head { display:flex; align-items:center; justify-content:space-between; padding:15px 18px; border-bottom:1px solid #f0f0f0; font-size:15px; }
.ai-body { flex:1; overflow-y:auto; padding:18px 16px; display:flex; flex-direction:column; gap:16px; background:#fafbfc; }
.ai-msg { display:flex; flex-direction:column; gap:8px; }
.ai-msg.ai-bot { align-items:flex-start; }
.ai-msg.ai-user { align-items:flex-end; }
.ai-bubble { padding:10px 14px; border-radius:12px; font-size:13.5px; line-height:1.6; max-width:90%; }
.ai-bot .ai-bubble { background:#fff; color:rgba(0,0,0,0.82); border:1px solid #eee; border-top-left-radius:3px; }
.ai-user .ai-bubble { background:#1F80A0; color:#fff; border-top-right-radius:3px; }
.ai-chips { display:flex; flex-wrap:wrap; gap:7px; }
.ai-chip { font-size:12px; padding:5px 11px; border:1px solid #cfe4ec; color:#1F80A0; background:#fff; border-radius:14px; cursor:pointer; }
.ai-chip:hover { background:#e6f4f8; }
.ai-sql { align-self:stretch; background:#1e1e1e; color:#d4d4d4; padding:11px 13px; border-radius:8px; font-size:12px; line-height:1.55; overflow-x:auto; white-space:pre; margin:0; font-family:'SF Mono',Menlo,monospace; }
.ai-run { align-self:flex-start; height:30px; padding:0 14px; font-size:13px; }
.ai-input { position:relative; border-top:1px solid #f0f0f0; padding:12px 14px; }
.ai-input textarea { width:100%; min-height:44px; max-height:120px; border:1px solid #d9d9d9; border-radius:8px; padding:9px 44px 9px 12px; font-size:13.5px; outline:none; resize:none; font-family:inherit; line-height:1.5; box-sizing:border-box; }
.ai-input textarea:focus { border-color:#1F80A0; }
.ai-send { position:absolute; right:24px; bottom:21px; width:28px; height:28px; border:none; border-radius:7px; background:#1F80A0; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:14px; line-height:1; }
.ai-send:hover { background:#176a88; }
.btn { display:inline-flex; align-items:center; gap:6px; height:34px; padding:0 16px; border-radius:8px; font-size:14px; cursor:pointer; border:1px solid #d9d9d9; background:#fff; color:rgba(0,0,0,0.85); }
.btn:hover { border-color:#1F80A0; color:#1F80A0; }
.btn-primary { background:#1F80A0; border-color:#1F80A0; color:#fff; }
.btn-primary:hover { background:#176a88; border-color:#176a88; color:#fff; }
.btn-secondary { background:#fff; border-color:#1F80A0; color:#1F80A0; }
.btn-secondary:hover { background:#e6f4f8; border-color:#176a88; color:#176a88; }
/* 多选下拉 (创建人) */
.ms-wrap { position:relative; }
.ms-trigger { height:34px; min-width:120px; padding:5px 28px 5px 12px; border:1px solid #d9d9d9; border-radius:8px; font-size:14px; color:rgba(0,0,0,0.65); background:#fff; cursor:pointer; display:flex; align-items:center; position:relative; }
.ms-trigger:hover { border-color:#1F80A0; }
.ms-trigger::after { content:''; position:absolute; right:11px; top:50%; border:5px solid transparent; border-top-color:#bfbfbf; transform:translateY(-2px); }
.ms-label { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.ms-panel { display:none; position:absolute; top:calc(100% + 4px); left:0; min-width:160px; background:#fff; border:1px solid #f0f0f0; border-radius:8px; box-shadow:0 6px 16px rgba(0,0,0,0.08); z-index:100; padding:4px 0; }
.ms-wrap.open .ms-panel { display:block; }
.ms-panel label { display:flex; align-items:center; gap:8px; padding:6px 14px; font-size:13px; cursor:pointer; color:rgba(0,0,0,0.8); }
.ms-panel label:hover { background:#fafafa; }
.ms-panel input { accent-color:#1F80A0; }

/* ── Table ── */
.ant-table { width:100%; border-collapse:collapse; font-size:14px; background:#fff; }
.ant-table thead th { background:#fafafa; padding:9px 16px; font-weight:500; color:rgba(0,0,0,0.85); text-align:left; border-bottom:1px solid #f0f0f0; white-space:nowrap; }
.ant-table tbody td { padding:9px 16px; border-bottom:1px solid #f0f0f0; color:rgba(0,0,0,0.65); vertical-align:middle; }
.ant-table tbody tr:hover td { background:#fafafa; }
.actions-cell { white-space:nowrap; }
/* 统一行高 = 两行 */
.row2 tbody td { vertical-align:middle; }
.row2 .desc-clamp { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.5; min-height:42px; }

/* ── Tags / status ── */
.tag { display:inline-block; padding:1px 8px; border-radius:4px; font-size:12px; line-height:20px; border:1px solid transparent; }
.tag-blue { color:#1F80A0; background:#e6f4f8; border-color:#8dcde0; }
.tag-gray { color:#8c8c8c; background:#f5f5f5; border-color:#e8e8e8; }
.tag-purple { color:#722ed1; background:#f9f0ff; border-color:#d3adf7; }
.tag-orange { color:#ad6800; background:#fffbe6; border-color:#ffe58f; }
.qa { display:inline-flex; align-items:center; gap:5px; font-size:13px; }
.qa::before { content:''; width:7px; height:7px; border-radius:50%; }
.qa-pass { color:#389e0d; } .qa-pass::before { background:#52c41a; }
.qa-warn { color:#d48806; } .qa-warn::before { background:#faad14; }
.qa-fail { color:#cf1322; } .qa-fail::before { background:#ff4d4f; }

/* ── Tree + Tab split layout (左树右Tab, 两面板各自独立滚动) ── */
.split { display:flex; gap:16px; align-items:stretch; height:calc(100vh - 96px); }
.tree-panel { width:300px; min-width:300px; background:#fff; border:1px solid #f0f0f0; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; transition:width 0.2s,min-width 0.2s; }
.th-left { display:flex; align-items:center; gap:8px; min-width:0; }
.th-actions { display:flex; align-items:center; gap:8px; }
.tp-toggle { cursor:pointer; color:#1F80A0; font-size:15px; flex:none; width:18px; text-align:center; }
.tp-toggle:hover { color:#176a88; }
.tp-toggle .sc-exp { display:none; }
.tree-panel.tp-collapsed { width:34px; min-width:34px; }
/* 折叠: 仅保留头部的 toggle icon (展开/收起合一) */
.tree-panel.tp-collapsed > *:not(.tree-head) { display:none; }
.tree-panel.tp-collapsed .tree-head { justify-content:center; padding:10px 0; }
.tree-panel.tp-collapsed .th-title, .tree-panel.tp-collapsed .th-actions { display:none; }
.tree-panel.tp-collapsed .sc-col { display:none; }
.tree-panel.tp-collapsed .sc-exp { display:inline; }
.tree-panel .tree-head { padding:10px 14px; border-bottom:1px solid #f0f0f0; font-size:13px; font-weight:600; color:rgba(0,0,0,0.85); display:flex; justify-content:space-between; align-items:center; }
.tree-panel .tree-search { padding:8px 10px; border-bottom:1px solid #f5f5f5; }
.tree-panel .tree-search input { width:100%; box-sizing:border-box; height:30px; padding:4px 10px; border:1px solid #d9d9d9; border-radius:6px; font-size:13px; outline:none; }
.tree-body { flex:1; overflow-y:auto; padding:6px 0; }
.tree-grp { padding:7px 14px; font-size:13px; color:rgba(0,0,0,0.85); cursor:pointer; display:flex; align-items:center; gap:6px; font-weight:500; }
.tree-grp:hover { background:#fafafa; }
.tree-grp .caret { font-size:10px; color:rgba(0,0,0,0.35); transition:transform 0.2s; display:inline-block; }
.tree-grp.collapsed .caret { transform:rotate(-90deg); }
.tree-leaf { padding:6px 14px 6px 34px; font-size:13px; color:rgba(0,0,0,0.65); display:block; border-left:2px solid transparent; }
.tree-leaf:hover { background:#fafafa; color:#1F80A0; }
.tree-leaf.active { background:#e6f4f8; color:#1F80A0; border-left-color:#1F80A0; font-weight:500; }
.tree-leaf .sub { color:rgba(0,0,0,0.35); font-size:11px; }
.tree-modes { display:flex; gap:4px; padding:8px 10px; border-bottom:1px solid #f5f5f5; }
.tree-mode { flex:1; text-align:center; font-size:12px; padding:5px 0; border-radius:6px; cursor:pointer; color:rgba(0,0,0,0.55); }
.tree-mode:hover { background:#f5f5f5; }
.tree-mode.active { background:#e6f4f8; color:#1F80A0; font-weight:500; }
.tg { display:inline-block; padding:0 6px; font-size:11px; line-height:17px; border-radius:3px; background:#eef3f8; color:#5b7083; margin-right:3px; }
.tree-children.collapsed { display:none; }
.tree-grp .folder-act { margin-left:auto; color:rgba(0,0,0,0.25); font-size:14px; padding:0 4px; border-radius:4px; }
.tree-grp .folder-act:hover { color:#1F80A0; background:#eef3f8; }
.tree-grp { justify-content:flex-start; }

.detail-panel { flex:1; min-width:0; background:#fff; border:1px solid #f0f0f0; border-radius:8px; height:100%; overflow-y:auto; }
.detail-head { padding:16px 24px; border-bottom:1px solid #f0f0f0; display:flex; justify-content:space-between; align-items:flex-start; }
.detail-head .dh-title { font-size:18px; font-weight:600; color:rgba(0,0,0,0.85); display:flex; align-items:center; gap:10px; }
.ver-select { font-size:13px; font-weight:400; padding:3px 8px; border:1px solid #d9d9d9; border-radius:6px; color:rgba(0,0,0,0.7); background:#fff; cursor:pointer; outline:none; }
.ver-select:hover { border-color:#1F80A0; }
.detail-head .dh-meta { font-size:12px; color:rgba(0,0,0,0.45); margin-top:6px; display:flex; gap:18px; flex-wrap:wrap; }

/* ── Tabs ── */
.tabs { display:flex; gap:4px; padding:0 24px; border-bottom:1px solid #f0f0f0; position:sticky; top:0; background:#fff; z-index:5; }
.tab { padding:11px 14px; font-size:14px; color:rgba(0,0,0,0.65); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; }
.tab:hover { color:#1F80A0; }
.tab.active { color:#1F80A0; border-bottom-color:#1F80A0; font-weight:500; }
.tab-pane { display:none; padding:24px; }
.tab-pane.active { display:block; }
/* 数据预览 Tab: episode 列表 与 右侧内容各自滚动 (固定高度区) */
#pane-preview .preview-split { height:calc(100vh - 230px); }
#pane-preview .ep-strip { height:100%; max-height:none; }
#pane-preview .preview-main { height:100%; overflow-y:auto; padding-right:4px; }

/* ── Descriptions (key-value) ── */
.desc-grid { display:grid; grid-template-columns:max-content 1fr; gap:0; border:1px solid #f0f0f0; border-radius:8px; overflow:hidden; }
.desc-grid .dk { background:#fafafa; padding:10px 16px; font-size:13px; color:rgba(0,0,0,0.45); border-bottom:1px solid #f0f0f0; border-right:1px solid #f0f0f0; white-space:nowrap; }
.desc-grid .dv { padding:10px 16px; font-size:13px; color:rgba(0,0,0,0.85); border-bottom:1px solid #f0f0f0; }

/* ── Camera + curve preview ── */
.camera-row { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:16px; }
.camera-cell { position:relative; background:#141414; height:150px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:rgba(255,255,255,0.35); flex-direction:column; gap:6px; font-size:12px; }
.camera-cell .cam-label { position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.6); color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; }
.play-bar { display:flex; align-items:center; gap:12px; background:#fafafa; border:1px solid #f0f0f0; border-radius:8px; padding:8px 14px; margin-bottom:16px; font-size:13px; color:rgba(0,0,0,0.65); }
.play-bar .play-btn { width:30px; height:30px; border-radius:50%; background:#1F80A0; color:#fff; display:flex; align-items:center; justify-content:center; cursor:pointer; }
.play-bar .track { flex:1; height:6px; background:#e8e8e8; border-radius:3px; position:relative; }
.play-bar .track .cursor { position:absolute; left:38%; top:-3px; width:2px; height:12px; background:#1F80A0; }
.kbd { display:inline-block; padding:1px 6px; border:1px solid #d9d9d9; border-bottom-width:2px; border-radius:4px; font-size:11px; color:rgba(0,0,0,0.55); background:#fafafa; }
.frame-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:8px; }
.frame-thumb { aspect-ratio:4/3; background:linear-gradient(135deg,#2b3a4a,#1a2530); border-radius:6px; display:flex; align-items:center; justify-content:center; color:rgba(255,255,255,0.4); font-size:11px; position:relative; }
.frame-thumb .ft-tag { position:absolute; bottom:4px; left:4px; background:rgba(0,0,0,0.55); color:#fff; padding:0 5px; border-radius:3px; font-size:10px; }

/* ── Episode strip (lerobot 风格) ── */
.preview-split { display:flex; gap:16px; align-items:flex-start; }
.ep-strip { width:150px; min-width:150px; max-height:600px; overflow-y:auto; border:1px solid #f0f0f0; border-radius:8px; }
.ep-strip .ep-head { padding:9px 14px; font-size:11px; color:rgba(0,0,0,0.45); text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #f5f5f5; position:sticky; top:0; background:#fff; }
.ep-item { padding:8px 14px; font-size:13px; color:rgba(0,0,0,0.65); cursor:pointer; border-left:2px solid transparent; border-bottom:1px solid #fafafa; }
.ep-item:hover { background:#fafafa; }
.ep-item.active { background:#e6f4f8; color:#1F80A0; border-left-color:#1F80A0; font-weight:500; }
.ep-item .er { font-size:11px; color:rgba(0,0,0,0.35); margin-top:2px; }
.preview-main { flex:1; min-width:0; }
.lang-instr { background:#fafafa; border:1px solid #f0f0f0; border-radius:8px; padding:13px 18px; margin:16px 0; }
.lang-instr .li-label { font-size:11px; color:rgba(0,0,0,0.45); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; }
.lang-instr .li-text { font-size:16px; color:rgba(0,0,0,0.85); }
.combine-btn { float:right; font-size:12px; color:rgba(0,0,0,0.55); border:1px solid #d9d9d9; border-radius:6px; padding:3px 10px; cursor:pointer; }
.combine-btn:hover { border-color:#1F80A0; color:#1F80A0; }

/* ── 轨迹工具条 + 视图 ── */
.traj-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 0; border-bottom:1px solid #f0f0f0; margin-bottom:12px; }
.traj-tabs { display:flex; gap:6px; align-items:center; }
.tbtn { padding:5px 14px; border:1px solid #d9d9d9; border-radius:6px; background:#fff; font-size:13px; cursor:pointer; color:rgba(0,0,0,0.65); }
.tbtn:hover { border-color:#1F80A0; color:#1F80A0; }
.tbtn.on { background:#1F80A0; border-color:#1F80A0; color:#fff; }
.tbar-sep { width:1px; height:18px; background:#e8e8e8; margin:0 4px; }
.traj-play { display:flex; gap:8px; }
.traj-play .pbtn { width:30px; height:30px; border:1px solid #e0e0e0; border-radius:6px; background:#fff; cursor:pointer; color:#1F80A0; display:flex; align-items:center; justify-content:center; font-size:14px; }
.traj-play .pbtn:hover { border-color:#1F80A0; }
.traj-legend { display:flex; gap:14px; font-size:12px; color:rgba(0,0,0,0.6); }
.traj-legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:middle; }
.traj-grid { width:100%; border-collapse:collapse; table-layout:fixed; }
.traj-grid th { font-size:13px; font-weight:600; color:rgba(0,0,0,0.8); text-align:center; padding:6px 10px; border-bottom:1px solid #f0f0f0; }
.traj-grid th.rlab, .traj-grid td.rlab { width:34px; }
.traj-grid td { padding:3px 10px; border-bottom:1px solid #fafafa; vertical-align:middle; }
.traj-grid td.rlab { font-size:12px; color:rgba(0,0,0,0.45); text-align:center; }
.traj-grid { height:100%; }
.spark { width:100%; height:100%; min-height:18px; display:block; }
.base-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; height:100%; }
.base-card { border:1px solid #f0f0f0; border-radius:8px; padding:14px; height:100%; box-sizing:border-box; }
.base-card canvas { width:100% !important; height:100% !important; }
/* 切 tab 时下方区域定高, 内部图表随容器拉伸填满 */
.traj-views { height:340px; overflow:hidden; }
.traj-views .tview { height:100%; }
.moz-view { display:flex; flex-direction:column; }
/* ── 3D Replay ── */
.moz-stage { position:relative; flex:1; min-height:0; border:1px solid #f0f0f0; border-radius:8px; overflow:hidden; background:#fbfcfd; }
.moz-floor { position:absolute; left:50%; top:58%; width:1400px; height:1400px; margin-left:-700px;
  transform:translateY(-34%) perspective(720px) rotateX(60deg);
  background-image:linear-gradient(#e3e8ee 1px,transparent 1px),linear-gradient(90deg,#e3e8ee 1px,transparent 1px);
  background-size:50px 50px; }
.moz-axis-y { position:absolute; left:54%; top:40%; color:#52c41a; font-size:13px; }
.moz-robot { position:absolute; left:50%; top:48%; transform:translate(-50%,-60%); z-index:2; }
.moz-info-wrap { position:absolute; right:14px; top:14px; width:300px; z-index:3; }
.moz-info { background:#fff; border:1px solid #e8eef3; border-radius:10px; padding:12px 14px; box-shadow:0 4px 16px rgba(0,0,0,0.06); max-height:420px; overflow-y:auto; }
.moz-info-wrap.collapsed .moz-info { display:none; }
.moz-collapse { position:absolute; left:-26px; top:8px; width:24px; height:38px; border:1px solid #d9e3ea; border-right:none; border-radius:8px 0 0 8px; background:#fff; color:#1F80A0; cursor:pointer; font-size:14px; }
.moz-collapse:hover { background:#f0f9fb; }
.mz-row { margin-bottom:9px; }
.mz-k { font-size:12px; color:rgba(0,0,0,0.55); margin-bottom:3px; }
.mz-v { font-size:12px; font-family:monospace; color:rgba(0,0,0,0.82); border:1px solid #eef1f4; border-radius:6px; padding:5px 8px; background:#fafbfc; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.traj-slider { width:100%; margin-top:16px; accent-color:#1F80A0; }

/* ── 可视化分析 (标题层级: L1 区块 > L2 模块 > L3 子标题 > L4 图表) ── */
.va-section { margin-top:24px; border-top:1px solid #f0f0f0; padding-top:16px; }
.va-title, .va-h { font-size:15px; font-weight:600; color:rgba(0,0,0,0.82); margin:28px 0 14px; padding-bottom:8px; border-bottom:1px solid #f0f0f0; }
.va-title { margin-top:6px; }
.va-sub { font-size:13px; font-weight:600; color:rgba(0,0,0,0.6); margin:16px 0 6px; }
.va-ct { font-size:12px; font-weight:400; color:rgba(0,0,0,0.45); margin-bottom:5px; }
.va-box { height:190px; }
.va-box-lg { height:210px; margin-bottom:12px; }
.va-box canvas { width:100% !important; height:100% !important; }
.va-grid2 { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-bottom:18px; }
.va-trail { height:380px; border:1px solid #f0f0f0; border-radius:8px; background:#fff; }
.va-trail canvas { width:100%; height:100%; display:block; }
.va-trailbar { display:flex; gap:8px; margin-bottom:8px; justify-content:flex-end; }
.va-trailfoot { display:flex; justify-content:space-between; align-items:center; margin-top:8px; }
.va-legend2 { display:flex; gap:16px; font-size:12px; color:rgba(0,0,0,0.6); }
.va-legend2 i { display:inline-block; width:14px; height:3px; border-radius:2px; margin-right:5px; vertical-align:middle; }
.va-armtoggle { display:flex; gap:6px; margin-bottom:14px; }
.va-params { background:#fafbfc; border:1px solid #f0f0f0; border-radius:8px; padding:10px 14px; font-size:13px; color:rgba(0,0,0,0.7); margin-bottom:14px; }
.va-params input { accent-color:#1F80A0; vertical-align:middle; }

/* ── Progress ── */
.progress-bar { height:6px; background:#f0f0f0; border-radius:100px; overflow:hidden; width:140px; display:inline-block; vertical-align:middle; }
.progress-bar-fill { height:100%; border-radius:100px; background:#1F80A0; }
.progress-bar-fill.warn { background:#faad14; }
.progress-bar-fill.fail { background:#ff4d4f; }

/* ── Doctor banner ── */
.doctor-banner { padding:12px 18px; border-radius:8px; font-size:14px; margin-bottom:16px; display:flex; align-items:center; gap:10px; }
.doctor-banner.pass { background:#f6ffed; border:1px solid #b7eb8f; color:#389e0d; }
.doctor-banner.warn { background:#fffbe6; border:1px solid #ffe58f; color:#d48806; }
.doctor-banner.fail { background:#fff2f0; border:1px solid #ffccc7; color:#cf1322; }
.check-row { display:flex; align-items:center; gap:12px; padding:10px 14px; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:8px; font-size:13px; }
.check-row .badge { font-size:11px; font-weight:600; padding:1px 8px; border-radius:4px; min-width:42px; text-align:center; }
.check-row .badge.pass { color:#389e0d; background:#f6ffed; }
.check-row .badge.warn { color:#d48806; background:#fffbe6; }
.check-row .badge.fail { color:#cf1322; background:#fff2f0; }
.check-row .cname { font-weight:500; color:rgba(0,0,0,0.85); min-width:230px; }
.check-row .cdesc { color:rgba(0,0,0,0.45); }
.check-row .check-pct { margin-left:auto; display:flex; align-items:center; gap:8px; white-space:nowrap; }
.check-row .cp-bar { width:84px; height:6px; background:#f0f0f0; border-radius:3px; overflow:hidden; }
.check-row .cp-bar i { display:block; height:100%; border-radius:3px; }
.check-row .cp-bar.ok i { background:#52c41a; }
.check-row .cp-bar.warn i { background:#faad14; }
.check-row .cp-bar.bad i { background:#ff4d4f; }
.check-row .cp-num { font-size:12px; color:rgba(0,0,0,0.55); min-width:34px; text-align:right; }
.drawer.qp-drawer { width:1200px; max-width:92vw; }
.qp-wrap .ep-strip { display:none; }
.qp-wrap .va-section { display:none; }
.qp-wrap .preview-split { display:block; }
.qp-wrap .preview-main { padding:0; }
.sched-badge { display:inline-flex; align-items:center; justify-content:center; min-width:22px; height:22px; padding:0 6px; border-radius:11px; background:#e6f4f8; color:#1F80A0; font-size:12px; font-weight:600; cursor:default; }
.sch-group { border:1px solid #f0f0f0; border-radius:8px; padding:6px 12px; margin-bottom:10px; background:#fafbfc; }
.sch-group-head { display:flex; align-items:center; font-size:12px; font-weight:600; color:rgba(0,0,0,0.65); padding:6px 0 2px; }
.sch-group-head .sch-del { margin-left:auto; color:#bfbfbf; cursor:pointer; font-weight:400; }
.sch-group-head .sch-del:hover { color:#ff4d4f; }
.sch-group .param-table td { border-bottom:none; padding:5px 0; }
.param-mode { display:inline-flex; border:1px solid #e2e4e8; border-radius:6px; overflow:hidden; margin-bottom:10px; }
.param-mode .pm-btn { border:none; background:#fff; padding:4px 12px; font-size:12.5px; cursor:pointer; color:rgba(0,0,0,0.6); }
.param-mode .pm-btn.active { background:#1F80A0; color:#fff; }
.proc-params-area { height:240px; overflow-y:auto; }
.ds-hint { background:#f3f9fb; border:1px solid #cfe4ec; border-radius:8px; padding:10px 14px; font-size:13px; color:rgba(0,0,0,0.7); line-height:1.6; margin-bottom:16px; }
.ds-hint a { color:#1F80A0; }

/* ── Recipe bars ── */
.recipe-row { display:flex; align-items:center; gap:12px; margin-bottom:10px; font-size:13px; }
.recipe-row .rname { width:160px; color:rgba(0,0,0,0.85); }
.recipe-row .rbar { flex:1; height:22px; background:#f5f5f5; border-radius:4px; overflow:hidden; position:relative; }
.recipe-row .rbar .fill { height:100%; background:#1F80A0; display:flex; align-items:center; padding-left:8px; color:#fff; font-size:12px; }

/* ── 标签构成 饼图 (一行三个) ── */
.pie-row { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.pie-cell { border:1px solid #f0f0f0; border-radius:8px; padding:12px 12px 8px; }
.pie-title { text-align:center; font-weight:600; font-size:13px; color:rgba(0,0,0,0.75); margin-bottom:6px; }
.pie-box { position:relative; height:200px; }
.pie-legend { width:100%; border-collapse:collapse; margin-top:10px; font-size:12px; }
.pie-legend td { padding:4px 4px; border-bottom:1px solid #fafafa; color:rgba(0,0,0,0.72); }
.pie-legend td.pct { text-align:right; color:rgba(0,0,0,0.45); white-space:nowrap; }
.pie-legend i { display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:6px; vertical-align:middle; }
@media (max-width:1100px){ .pie-row { grid-template-columns:1fr; } }

/* ── 标签构成 树 ── */
.tagtree-grp { font-size:13px; font-weight:600; color:#1F80A0; margin:16px 0 8px; display:flex; align-items:center; gap:6px; }
.tagtree-grp .caret-d { font-size:10px; color:rgba(0,0,0,0.3); }
.tagtree-row { display:flex; align-items:center; gap:12px; margin-bottom:8px; padding-left:20px; font-size:13px; }
.tagtree-row .ttname { width:120px; color:rgba(0,0,0,0.75); }

/* ── Wizard steps ── */
.steps { display:flex; gap:0; margin-bottom:24px; }
.step { flex:1; text-align:center; position:relative; padding:8px 0; }
.step .sn { width:28px; height:28px; border-radius:50%; background:#f0f0f0; color:rgba(0,0,0,0.45); display:inline-flex; align-items:center; justify-content:center; font-size:13px; font-weight:600; }
.step.active .sn { background:#1F80A0; color:#fff; }
.step.done .sn { background:#e6f4f8; color:#1F80A0; }
.step .st { font-size:13px; color:rgba(0,0,0,0.65); margin-top:6px; }
.step.active .st { color:#1F80A0; font-weight:500; }
.step::after { content:''; position:absolute; top:21px; left:60%; width:80%; height:1px; background:#f0f0f0; }
.step:last-child::after { display:none; }

/* ── Operator cards ── */
.op-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
.op-card { background:#fff; border:1px solid #f0f0f0; border-radius:8px; padding:16px 18px; transition:all 0.2s; }
.op-card:hover { border-color:#1F80A0; box-shadow:0 2px 10px rgba(31,128,160,0.1); }
.op-card .op-name { font-size:15px; font-weight:600; color:rgba(0,0,0,0.85); margin-bottom:4px; display:flex; align-items:center; gap:8px; }
.op-card .op-script { font-size:12px; color:#1F80A0; background:#e6f4f8; padding:1px 6px; border-radius:4px; font-family:monospace; }
.op-card .op-desc { font-size:13px; color:rgba(0,0,0,0.55); margin:8px 0; line-height:1.5; }
.op-card .op-params { font-size:12px; color:rgba(0,0,0,0.35); font-family:monospace; }

/* ── DAG / 工作流画布 ── */
.dag { display:flex; align-items:center; gap:8px; flex-wrap:wrap; padding:18px; background:#fafafa; border:1px solid #f0f0f0; border-radius:8px; }
.dag-node { background:#fff; border:1px solid #8dcde0; border-radius:8px; padding:10px 14px; font-size:13px; color:rgba(0,0,0,0.85); text-align:center; min-width:110px; }
.dag-node .dn-cat { font-size:11px; color:#1F80A0; }
.dag-arrow { color:#bfbfbf; font-size:18px; }

/* ── Workflow canvas (画布编辑器) ── */
.wf-topbar { display:flex; align-items:center; justify-content:space-between; background:#fff; border:1px solid #f0f0f0; border-radius:8px; padding:10px 16px; margin-bottom:12px; }
.wf-title { display:flex; align-items:center; gap:10px; font-size:16px; font-weight:600; color:rgba(0,0,0,0.85); }
.wf-title .back { color:rgba(0,0,0,0.45); text-decoration:none; font-size:18px; }
.wf-tabs { display:flex; gap:4px; }
.wf-tab { padding:5px 14px; border-radius:6px; font-size:14px; cursor:pointer; color:rgba(0,0,0,0.65); }
.wf-tab.active { background:#e6f4f8; color:#1F80A0; font-weight:500; }
.wf-actions { display:flex; gap:8px; }
/* ---- 自由画布 (free-form DAG canvas) ---- */
.wf-stage { display:flex; gap:0; height:calc(100vh - 200px); }
.wf-canvas { position:relative; flex:1; background:#fafbfc; background-image:radial-gradient(#e1e4e8 1px, transparent 1px); background-size:18px 18px; border:1px solid #f0f0f0; border-radius:8px; overflow:hidden; }
.wf-pan { position:absolute; left:0; top:0; transform-origin:0 0; }
.wf-edges { position:absolute; left:0; top:0; width:4000px; height:3000px; overflow:visible; pointer-events:none; z-index:1; }
.wf-edges path.edge { pointer-events:stroke; cursor:pointer; }
.wf-node { position:absolute; width:220px; background:#fff; border:1px solid #e8e8e8; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.06); z-index:2; user-select:none; }
.wf-node.sel { border-color:#1F80A0; box-shadow:0 4px 16px rgba(31,128,160,0.22); }
.wf-node-head { display:flex; align-items:center; gap:8px; padding:11px 13px; font-weight:600; font-size:14px; color:rgba(0,0,0,0.85); border-bottom:1px solid #f5f5f5; cursor:move; }
.wf-node-del { margin-left:auto; color:rgba(0,0,0,0.25); cursor:pointer; font-size:16px; line-height:1; padding:0 2px; }
.wf-node-del:hover { color:#ff4d4f; }
.wf-node-ic { width:22px; height:22px; border-radius:6px; background:#e6f4f8; color:#1F80A0; display:flex; align-items:center; justify-content:center; font-size:12px; flex:none; }
.wf-node-row { display:flex; padding:6px 13px; font-size:12px; align-items:center; }
.wf-node-row .k { color:rgba(0,0,0,0.4); width:40px; flex:none; }
.wf-node-row .v { color:rgba(0,0,0,0.75); flex:1; text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.wf-port { position:absolute; top:50%; width:13px; height:13px; margin-top:-6.5px; border-radius:50%; background:#fff; border:2px solid #9ec3d6; cursor:crosshair; z-index:3; }
.wf-port:hover { border-color:#1F80A0; background:#1F80A0; }
.wf-port.in { left:-7px; }
.wf-port.out { right:-7px; }
.wf-empty { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; color:rgba(0,0,0,0.3); gap:10px; z-index:0; }
.wf-hint { position:absolute; left:16px; top:14px; font-size:12px; color:rgba(0,0,0,0.38); background:rgba(255,255,255,0.7); padding:4px 10px; border-radius:6px; z-index:4; }
.wf-toolbar { position:absolute; left:16px; bottom:16px; display:flex; align-items:center; gap:6px; background:#fff; border:1px solid #f0f0f0; border-radius:8px; padding:6px 10px; box-shadow:0 2px 8px rgba(0,0,0,0.08); z-index:4; }
.wf-toolbar .zbtn { width:26px; height:26px; border:none; background:none; cursor:pointer; color:rgba(0,0,0,0.55); border-radius:5px; font-size:15px; }
.wf-toolbar .zbtn:hover { background:#f5f5f5; }
.wf-toolbar .zlvl { font-size:13px; color:rgba(0,0,0,0.65); min-width:42px; text-align:center; }
.wf-toolbar .sep { width:1px; height:18px; background:#f0f0f0; margin:0 4px; }
/* ---- 右侧节点配置面板 ---- */
.wf-config { width:0; flex:none; background:#fff; border:1px solid #f0f0f0; border-left:none; border-radius:0 8px 8px 0; overflow:hidden; transition:width 0.18s; display:flex; flex-direction:column; }
.wf-config.open { width:340px; border-left:1px solid #f0f0f0; }
.wf-config-head { display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid #f5f5f5; font-size:15px; }
.wf-config-body { flex:1; overflow:auto; padding:6px 16px 16px; }
.wf-cfg-sec { font-size:13px; font-weight:600; color:rgba(0,0,0,0.85); margin:16px 0 6px; padding-left:8px; border-left:3px solid #1F80A0; }
.wf-cfg-row { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding:7px 0; font-size:13px; border-bottom:1px dashed #f5f5f5; }
.wf-cfg-row > span:first-child { color:rgba(0,0,0,0.45); flex:none; }
.wf-cfg-row.lft { justify-content:flex-start; }
.wf-cfg-row.lft > span:first-child { width:62px; }
.wf-cfg-row.lft > :last-child { flex:1; text-align:left; }
.wf-cfg-col { padding:7px 0; font-size:13px; border-bottom:1px dashed #f5f5f5; }
.wf-cfg-col > span { color:rgba(0,0,0,0.45); display:block; margin-bottom:5px; }
.wf-cfg-code { margin:0; background:#1e1e1e; color:#d4d4d4; font-family:'SF Mono',Menlo,monospace; font-size:11.5px; line-height:1.55; padding:8px 10px; border-radius:6px; white-space:pre-wrap; word-break:break-all; }
.wf-cfg-sec { display:flex; align-items:center; gap:8px; }
.wf-sec-tag { font-weight:400; font-size:11px; padding:1px 7px; border-radius:4px; }
.wf-sec-tag.ro { color:rgba(0,0,0,0.4); background:#f0f0f0; }
.wf-sec-tag.ed { color:#1F80A0; background:#e6f4f8; }
.wf-sec-link { margin-left:auto; font-size:12px; color:#1F80A0; cursor:pointer; font-weight:400; }
.wf-param-sub { display:flex; align-items:center; gap:8px; font-size:12px; color:rgba(0,0,0,0.55); margin:6px 0 2px; }
.wf-param { padding:8px 0; border-bottom:1px dashed #f5f5f5; }
.wf-param-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; }
.wf-param-k { font-family:'SF Mono',Menlo,monospace; font-size:12px; color:rgba(0,0,0,0.78); }
.wf-param-src { font-size:11px; border:1px solid #e8e8e8; border-radius:4px; padding:1px 4px; outline:none; cursor:pointer; background:#fafafa; color:rgba(0,0,0,0.45); }
.wf-param-src.ov { color:#1F80A0; background:#e6f4f8; border-color:#bfe0ec; }
.wf-param-src.rf { color:#9b59b6; background:#f6edfa; border-color:#e3cdee; }
.wf-param-v { width:100%; box-sizing:border-box; height:30px; padding:3px 9px; border:1px solid #d9d9d9; border-radius:6px; outline:none; font-size:12.5px; font-family:'SF Mono',Menlo,monospace; }
.wf-param-v:focus { border-color:#1F80A0; }
.fp-key, .fp-val { width:100%; box-sizing:border-box; height:30px; padding:3px 8px; border:1px solid #d9d9d9; border-radius:6px; outline:none; font-family:'SF Mono',Menlo,monospace; font-size:12px; }
.fp-key:focus, .fp-val:focus { border-color:#1F80A0; }
.fp-key:disabled, .fp-val:disabled { background:#f5f5f5; color:rgba(0,0,0,0.4); cursor:not-allowed; }
.param-table { width:100%; border-collapse:collapse; }
.param-table td { padding:7px 0; border-bottom:1px dashed #f5f5f5; vertical-align:top; }
.param-table td.pk { width:120px; padding:13px 12px 0 0; color:rgba(0,0,0,0.6); font-size:13px; }
.param-table input, .param-table select { width:100%; box-sizing:border-box; height:32px; padding:4px 9px; border:1px solid #d9d9d9; border-radius:6px; outline:none; font-size:13px; background:#fff; }
.param-table input:focus, .param-table select:focus { border-color:#1F80A0; }
.param-table input:disabled { background:#f5f5f5; color:rgba(0,0,0,0.4); cursor:not-allowed; }
.param-table .hint { margin-top:4px; }
.switch { position:relative; display:inline-block; width:40px; height:22px; vertical-align:middle; }
.switch input { opacity:0; width:0; height:0; }
.switch .slider { position:absolute; cursor:pointer; inset:0; background:#bfbfbf; border-radius:22px; transition:0.2s; }
.switch .slider::before { content:''; position:absolute; height:16px; width:16px; left:3px; bottom:3px; background:#fff; border-radius:50%; transition:0.2s; }
.switch input:checked + .slider { background:#1F80A0; }
.switch input:checked + .slider::before { transform:translateX(18px); }
.foot-check { margin-right:auto; display:flex; align-items:center; gap:6px; font-size:13px; color:rgba(0,0,0,0.65); cursor:pointer; }
.foot-check input { cursor:pointer; }
.wf-config-foot { display:flex; gap:8px; justify-content:flex-end; padding:12px 16px; border-top:1px solid #f5f5f5; }

/* ── 标签管理 树表 ── */
.tg-table td { padding:7px 16px; }
.tg-name { display:flex; align-items:center; gap:6px; }
.tg-caret { cursor:pointer; font-size:10px; color:rgba(0,0,0,0.35); transition:transform 0.15s; display:inline-block; width:14px; text-align:center; }
.tg-caret.open { transform:rotate(90deg); }
.tg-caret-none { display:inline-block; width:14px; }
.tg-dim { color:#1F80A0; font-weight:600; }
.tg-l2 { font-weight:600; color:rgba(0,0,0,0.85); }
.tg-l3 { color:rgba(0,0,0,0.6); }
.tg-en { color:rgba(0,0,0,0.3); font-size:12px; margin-left:4px; }
.tg-badge { display:inline-block; min-width:22px; text-align:center; background:#f0f0f0; border-radius:10px; padding:1px 8px; font-size:12px; color:#888; }
.tg-ops span { cursor:pointer; color:rgba(0,0,0,0.3); margin-right:12px; font-size:14px; }
.tg-ops span:hover { color:#1F80A0; }
.tg-ops .del:hover { color:#ff4d4f; }

/* ── Toast ── */
.q-toast { position:fixed; top:24px; left:50%; transform:translate(-50%,-12px); min-width:240px; background:#fff; color:rgba(0,0,0,0.85); padding:12px 18px; border-radius:10px; font-size:14px; z-index:9999; opacity:0; box-shadow:0 6px 24px rgba(0,0,0,0.12); border:1px solid #f0f0f0; border-left:4px solid #1F80A0; transition:opacity 0.25s,transform 0.25s; }
.q-toast.show { opacity:1; transform:translate(-50%,0); }

/* ── Drawer ── */
.drawer-mask { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:300; }
.drawer-mask.active { display:block; }
.drawer { position:fixed; top:0; right:0; bottom:0; width:560px; max-width:94vw; background:#fff; box-shadow:-6px 0 16px rgba(0,0,0,0.08); transform:translateX(100%); transition:transform 0.3s cubic-bezier(0.23,1,0.32,1); display:flex; flex-direction:column; z-index:301; }
.drawer-mask.active .drawer { transform:translateX(0); }
.drawer-head { padding:16px 24px; border-bottom:1px solid #f0f0f0; display:flex; justify-content:space-between; align-items:center; }
.drawer-head h3 { margin:0; font-size:16px; color:rgba(0,0,0,0.85); }
.drawer-close { cursor:pointer; color:rgba(0,0,0,0.45); font-size:18px; background:none; border:none; line-height:1; }
.drawer-close:hover { color:rgba(0,0,0,0.85); }
.drawer-body { padding:20px 24px; flex:1; overflow-y:auto; }
.drawer-foot { padding:12px 24px; border-top:1px solid #f0f0f0; display:flex; justify-content:flex-end; gap:8px; }
/* ── Modal (居中弹窗) ── */
.modal-mask { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:320; align-items:center; justify-content:center; }
.modal-mask.active { display:flex; }
.modal-box { background:#fff; border-radius:12px; max-height:86vh; display:flex; flex-direction:column; box-shadow:0 16px 56px rgba(0,0,0,0.2); overflow:hidden; }
.q-pager { display:flex; align-items:center; justify-content:space-between; margin-top:14px; }
.q-pager .pg-btns { display:flex; gap:6px; }
.pg-btn { min-width:30px; height:30px; padding:0 8px; border:1px solid #e2e4e8; background:#fff; border-radius:6px; font-size:13px; cursor:pointer; color:rgba(0,0,0,0.7); }
.pg-btn:hover { border-color:#1F80A0; color:#1F80A0; }
.pg-btn.active { background:#1F80A0; border-color:#1F80A0; color:#fff; }
.fg { margin-bottom:14px; }
.fg label { display:block; font-size:13px; color:rgba(0,0,0,0.85); margin-bottom:5px; }
.fg label .req { color:#ff4d4f; margin-right:2px; }
.fg input, .fg select, .fg textarea { width:100%; box-sizing:border-box; padding:6px 11px; border:1px solid #d9d9d9; border-radius:8px; font-size:14px; outline:none; font-family:inherit; background:#fff; }
.fg input:focus, .fg select:focus, .fg textarea:focus { border-color:#1F80A0; box-shadow:0 0 0 2px rgba(31,128,160,0.12); }
.fg textarea { min-height:60px; resize:vertical; }
.fg .hint { font-size:12px; color:rgba(0,0,0,0.35); margin-top:3px; }
.fg-row { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
/* 新建算子抽屉: 加宽 + 表单一行一列 */
.op-drawer { width:680px; }
.op-drawer .fg-row { grid-template-columns:1fr; }
/* 脚本编辑器样式 (入口脚本 / 出入参) */
.fg textarea.code-editor { font-family:'SF Mono',Monaco,Menlo,Consolas,monospace; font-size:12.5px; background:#1e1e1e; color:#d4d4d4; border-color:#2a2a2a; line-height:1.7; tab-size:2; white-space:pre; overflow:auto; min-height:64px; }
.fg textarea.code-editor:focus { border-color:#1F80A0; box-shadow:0 0 0 2px rgba(31,128,160,0.2); }
.fg textarea.code-editor::placeholder { color:rgba(255,255,255,0.28); }
.op-pick { padding:10px 12px; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:8px; cursor:pointer; transition:all 0.15s; }
.op-pick:hover { border-color:#1F80A0; background:#f7fbfc; }
.section-label { font-size:12px; color:#1F80A0; font-weight:600; margin:18px 0 12px; padding-bottom:5px; border-bottom:1px solid #f0f0f0; }
.section-label:first-child { margin-top:0; }
"""

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} - Quanta</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/antd@4.24.16/dist/antd.min.css">
<style>""" + BASE_CSS + """</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>
<header class="top-nav">
  <div class="tn-brand"><div class="logo-icon">Q</div><span>Quanta</span></div>
  <nav class="tn-nav">
    <a class="tn-item {{ 'active' if top=='data' }}" href="/query">数据</a>
    <a class="tn-item" href="#" onclick="toast('Demo: 训练模块占位');return false;">训练</a>
    <a class="tn-item" href="#" onclick="toast('Demo: 部署模块占位');return false;">部署</a>
    <a class="tn-item" href="#" onclick="toast('Demo: 评测模块占位');return false;">评测</a>
    <span class="tn-sep"></span>
    <a class="tn-item {{ 'active' if top=='asset' }}" href="/tags">资产</a>
    <a class="tn-item" href="#" onclick="toast('Demo: 资源模块占位');return false;">资源</a>
  </nav>
  <div class="tn-right">demo</div>
</header>
<div class="q-layout">
<aside class="q-sider">
  {% if top=='data' %}
  <nav class="nav-section">
    <div class="nav-label">数据准备</div>
    <a href="/query" class="nav-item {{ 'active' if active=='query' }}"><span class="icon">&#9906;</span><span class="nav-txt">数据查询</span></a>
    <a href="/datasets" class="nav-item {{ 'active' if active=='datasets' }}"><span class="icon">&#9776;</span><span class="nav-txt">数据集管理</span></a>
    <div class="nav-label">自动化任务</div>
    <a href="/operators" class="nav-item {{ 'active' if active=='operators' }}"><span class="icon">&#9881;</span><span class="nav-txt">算子管理</span></a>
    <a href="/pipelines" class="nav-item {{ 'active' if active=='pipelines' }}"><span class="icon">&#9783;</span><span class="nav-txt">任务管理</span></a>
    <a href="/runs" class="nav-item {{ 'active' if active=='runs' }}"><span class="icon">&#9654;</span><span class="nav-txt">执行记录</span></a>
  </nav>
  {% elif top=='asset' %}
  <nav class="nav-section">
    <div class="nav-label">资产</div>
    <a href="/tags" class="nav-item {{ 'active' if active=='tags' }}"><span class="icon">&#9873;</span><span class="nav-txt">标签管理</span></a>
  </nav>
  {% else %}
  <nav class="nav-section"></nav>
  {% endif %}
  <div class="user-block">
    <div class="user-avatar">J</div>
    <div class="user-info"><div class="user-name">joanna.qiao</div><div class="user-role">数据工程师</div></div>
    <span class="sider-collapse-btn" onclick="toggleSider()" title="折叠/展开菜单"><span class="sc-col">&#171;</span><span class="sc-exp">&#187;</span></span>
  </div>
</aside>
<main class="q-main">
  <div class="q-content">""" + "{{ content|safe }}" + """</div>
</main>
</div>
<div class="q-toast" id="toast"></div>
<script>
function toast(msg){ var t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show'); setTimeout(function(){t.classList.remove('show');},2200); }
function msUpdate(cb){
  var wrap=cb.closest('.ms-wrap'); var checked=wrap.querySelectorAll('input:checked'); var n=checked.length;
  var trig=wrap.querySelector('.ms-trigger'); var base=trig.getAttribute('data-base')||''; var lab=wrap.querySelector('.ms-label');
  trig.classList.toggle('has-value', n>0);
  if(!n){ lab.textContent=base; return; }
  var names=[]; checked.forEach(function(c){ names.push(c.parentNode.textContent.trim()); });
  lab.textContent=names.join(', ');
  if(lab.scrollWidth > lab.clientWidth + 1){ lab.textContent=base+' ('+n+')'; }
}
document.addEventListener('click', function(e){ document.querySelectorAll('.ms-wrap.open').forEach(function(w){ if(!w.contains(e.target)) w.classList.remove('open'); }); });
function openDrawerById(id){ document.getElementById(id).classList.add('active'); }
function closeDrawerById(id){ document.getElementById(id).classList.remove('active'); }
function switchTab(el, pane){
  var tabs=el.parentNode.querySelectorAll('.tab'); tabs.forEach(function(t){t.classList.remove('active');}); el.classList.add('active');
  var root=el.closest('.detail-panel')||document; root.querySelectorAll('.tab-pane').forEach(function(p){p.classList.remove('active');});
  var target=root.querySelector('#pane-'+pane); if(target) target.classList.add('active');
  if(window._charts && window._charts[pane]) window._charts[pane]();
  try{ localStorage.setItem('detailTab', pane); }catch(e){}
}
function toggleTree(el){ el.classList.toggle('collapsed'); var ch=el.nextElementSibling; if(ch&&ch.classList.contains('tree-children')) ch.classList.toggle('collapsed'); }
function toggleSider(){ document.body.classList.toggle('sider-collapsed'); try{localStorage.setItem('siderCollapsed', document.body.classList.contains('sider-collapsed')?'1':'0');}catch(e){} }
function toggleTP(el){ var p=el.closest('.tree-panel'); if(p){ p.classList.toggle('tp-collapsed'); try{localStorage.setItem('tpCollapsed', p.classList.contains('tp-collapsed')?'1':'0');}catch(e){} } }
(function(){ try{ if(localStorage.getItem('siderCollapsed')==='1') document.body.classList.add('sider-collapsed');
  if(localStorage.getItem('tpCollapsed')==='1'){ var p=document.querySelector('.tree-panel'); if(p) p.classList.add('tp-collapsed'); } }catch(e){} })();
// 重载后恢复上次选中的详情 Tab (切换 episode/数据集 不回到第一个)
// 用 DOMContentLoaded 确保此时 window._charts 已定义, 图表能正常渲染; URL 带 tab 参数时跳过
document.addEventListener('DOMContentLoaded', function(){ try{
  if(/[?&]tab=/.test(location.search)) return;
  var t=localStorage.getItem('detailTab'); if(!t) return;
  var tabs=document.querySelectorAll('.tab');
  for(var i=0;i<tabs.length;i++){ var oc=tabs[i].getAttribute('onclick')||''; if(oc.indexOf("'"+t+"'")>=0){ tabs[i].click(); break; } }
}catch(e){} });
</script>
{{ extra_script|safe if extra_script else '' }}
</body>
</html>"""


def render_page(title, content, active="", breadcrumb=None, extra_script=None, top="data"):
    return render_template_string(BASE_TEMPLATE, title=title, content=content,
                                  active=active, breadcrumb=breadcrumb, extra_script=extra_script, top=top)


# ════════════════════════════════════════════════════════════════
# Section 3: Helpers
# ════════════════════════════════════════════════════════════════

def task_name(tid):
    for t in TASKS:
        if t["id"] == tid:
            return t["name"] + " (" + t["zh"] + ")"
    return tid

def qa_html(qa):
    m = {"pass": ("qa-pass", "PASS"), "warn": ("qa-warn", "WARN"), "fail": ("qa-fail", "FAIL")}
    c, t = m.get(qa, ("qa-pass", "PASS"))
    return f'<span class="qa {c}">{t}</span>'

def ds_type_tag(t):
    m = {"train": ("tag-blue", "train"), "val": ("tag-orange", "val"), "eval-benchmark": ("tag-purple", "eval-benchmark")}
    c, txt = m.get(t, ("tag-gray", t))
    return f'<span class="tag {c}">{txt}</span>'

def get_rec(rid):
    for r in RECORDINGS:
        if r["id"] == rid:
            return r
    return None

def get_ds(did):
    for d in DATASETS:
        if d["id"] == did:
            return d
    return None

def task_instr(tid):
    m = {"t1": "Clean the whiteboard", "t2": "Tidy the desk", "t3": "Water the plant"}
    return m.get(tid, tid)

def dataset_episodes(d):
    """数据集: 展开到 episode/recording 维度 (每个 episode ← 一条原始 recording)。"""
    recs = d["recordings"]
    n = min(d["episodes"], 12)
    instr = task_instr(d["tasks"][0])
    eps = []
    for i in range(n):
        rid = recs[i % len(recs)]
        r = get_rec(rid)
        tags = rec_tag_labels(r) if r else []
        eps.append({"idx": i, "rec": rid, "length": r["frames"] if r else 1200, "instr": instr, "tags": tags})
    return eps

def recs_to_episodes(recs, instr=None):
    """把一组 recording 转成 episode 列表 (用于数据湖右侧 strip)。"""
    eps = []
    for i, r in enumerate(recs):
        eps.append({"idx": i, "rec": r["id"], "length": r["frames"],
                    "instr": instr or task_instr(r["task"]), "tags": rec_tag_labels(r)})
    return eps


def _dataset_recs(d):
    return [r for r in (get_rec(i) for i in d["recordings"]) if r]

def dataset_prompt_composition(d):
    """数据集按 prompt(任务指令) 的帧数构成。"""
    recs = _dataset_recs(d)
    total = sum(r["frames"] for r in recs) or 1
    by = {}
    for r in recs:
        by[r["task"]] = by.get(r["task"], 0) + r["frames"]
    return [{"name": task_instr(t), "ratio": fr / total} for t, fr in sorted(by.items(), key=lambda x: -x[1])]

def dataset_tag_composition(d):
    """数据集按标签(场景/技能/质量) 的帧数构成 (标签可重叠, 占比可 >100%)。"""
    recs = _dataset_recs(d)
    total = sum(r["frames"] for r in recs) or 1
    by = {}
    for r in recs:
        for lab in rec_tag_labels(r):
            by[lab] = by.get(lab, 0) + r["frames"]
    return [{"name": lab, "ratio": fr / total} for lab, fr in sorted(by.items(), key=lambda x: -x[1])]

def comp_rows_html(items, total_frames):
    html = ""
    for it in items:
        pct = round(it["ratio"] * 100)
        fr = int(it["ratio"] * total_frames)
        html += (f'<div class="recipe-row"><div class="rname">{it["name"]}</div>'
                 f'<div class="rbar"><div class="fill" style="width:{min(max(pct,4),100)}%">{pct}%</div></div>'
                 f'<div class="muted">{fr:,}f</div></div>')
    return html or '<div class="muted">—</div>'

_TAG_GROUP = {tid: grp for tid, lab, grp in TAG_DEFS}

def dataset_tag_tree(d):
    """数据集标签按 维度(场景/技能/质量) → 标签 的树状构成 + 帧数占比。"""
    recs = _dataset_recs(d)
    total = sum(r["frames"] for r in recs) or 1
    by = {}
    for r in recs:
        for tid in rec_tags(r):
            by[tid] = by.get(tid, 0) + r["frames"]
    groups = {}
    for tid, fr in by.items():
        groups.setdefault(_TAG_GROUP.get(tid, "其他"), []).append(
            {"name": TAG_LABEL.get(tid, tid), "ratio": fr / total})
    out = []
    for grp in TAG_GROUP_ORDER:
        if grp in groups:
            out.append({"group": grp, "tags": sorted(groups[grp], key=lambda x: -x["ratio"])})
    return out

def tag_tree_html(d):
    html = ""
    for g in dataset_tag_tree(d):
        html += (f'<div class="tagtree-grp"><span class="caret-d">&#9662;</span>{g["group"]} '
                 f'<span class="muted" style="font-weight:400;font-size:12px;">{len(g["tags"])} 个标签</span></div>')
        for t in g["tags"]:
            pct = round(t["ratio"] * 100)
            fr = int(t["ratio"] * d["frames"])
            html += (f'<div class="tagtree-row"><div class="ttname">{t["name"]}</div>'
                     f'<div class="rbar"><div class="fill" style="width:{min(max(pct,4),100)}%">{pct}%</div></div>'
                     f'<div class="muted">{fr:,}f</div></div>')
    return html or '<div class="muted">—</div>'


# 通用: lerobot 风格 episode 级预览 (数据湖 + 数据集详情共用)
# 术语/结构对齐 out_182_unchecked: Episode / cam_high·cam_left_wrist·cam_right_wrist /
#   leftarm·rightarm_state(cmd)_joint_pos / LANGUAGE INSTRUCTION
def preview_block(prefix, eps):
    ep0 = eps[0]
    ep_items = ""
    for e in eps:
        ep_items += (f'<div class="ep-item {"active" if e["idx"]==0 else ""}" onclick="window.setEp_{prefix}({e["idx"]})">'
                     f'Episode {e["idx"]}<div class="er">{e["length"]:,}f · #{e["rec"]}</div></div>')
    cams = "".join(
        f'<div class="camera-cell"><span class="cam-label">{c}</span>'
        f'&#9658; 240×320</div>'
        for c in CAMERAS
    )
    html = f"""
    <div class="preview-split">
      <div class="ep-strip" id="{prefix}_strip">
        <div class="ep-head">Episodes ({len(eps)})</div>
        {ep_items}
      </div>
      <div class="preview-main">
        <!-- ① 三视角视频 -->
        <div class="camera-row">{cams}</div>

        <!-- ② 轨迹 -->
        <div class="traj-bar">
          <div class="traj-tabs">
            <button class="tbtn" id="{prefix}_btn_LeftArm" onclick="window.clickArm_{prefix}('LeftArm')">LeftArm</button>
            <button class="tbtn" id="{prefix}_btn_Torso" onclick="window.clickArm_{prefix}('Torso')">Torso</button>
            <button class="tbtn" id="{prefix}_btn_RightArm" onclick="window.clickArm_{prefix}('RightArm')">RightArm</button>
            <span class="tbar-sep"></span>
            <button class="tbtn" id="{prefix}_btn_Base" onclick="window.setMode_{prefix}('base')">Base</button>
            <button class="tbtn" id="{prefix}_btn_Moz" onclick="window.setMode_{prefix}('moz')">3D Replay</button>
          </div>
          <div class="traj-play">
            <button class="pbtn" onclick="toast('Demo: 播放')">&#9658;</button>
            <button class="pbtn" onclick="toast('Demo: 重置')">&#8635;</button>
          </div>
          <div class="traj-legend" id="{prefix}_legend"></div>
        </div>

        <div class="traj-views">
        <div class="tview" id="{prefix}_armView"></div>

        <div class="tview" id="{prefix}_baseView" style="display:none;">
          <div class="base-grid">
            <div class="base-card"><canvas id="{prefix}_baseSpeed" height="220"></canvas></div>
            <div class="base-card"><canvas id="{prefix}_baseXY" height="220"></canvas></div>
          </div>
        </div>

        <div class="tview moz-view" id="{prefix}_mozView" style="display:none;">
          <div style="display:flex;gap:8px;margin-bottom:10px;flex:none;">
            <button class="tbtn on">&#9673; Joint</button>
            <button class="tbtn" onclick="toast('Demo: 运动朝向')">&#9650; 运动朝向</button>
          </div>
          <div class="moz-stage">
            <div class="moz-floor"></div>
            <div class="moz-axis-y">Y</div>
            <div class="moz-robot">
              <svg width="74" height="128" viewBox="0 0 74 128">
                <ellipse cx="37" cy="120" rx="28" ry="6" fill="rgba(0,0,0,0.08)"/>
                <rect x="17" y="92" width="40" height="24" rx="5" fill="#cfd4d9"/>
                <rect x="22" y="84" width="30" height="10" rx="3" fill="#c2c8ce"/>
                <rect x="30" y="58" width="14" height="30" rx="4" fill="#c7ccd2"/>
                <rect x="25" y="36" width="24" height="26" rx="7" fill="#cdd2d8"/>
                <circle cx="37" cy="24" r="10" fill="#cdd2d8"/>
                <rect x="17" y="38" width="7" height="24" rx="3.5" fill="#bcc2c8"/>
                <rect x="50" y="38" width="7" height="24" rx="3.5" fill="#bcc2c8"/>
              </svg>
            </div>
            <div class="moz-info-wrap" id="{prefix}_mozWrap">
              <button class="moz-collapse" onclick="document.getElementById('{prefix}_mozWrap').classList.toggle('collapsed')">&raquo;</button>
              <div class="moz-info" id="{prefix}_mozInfo"></div>
            </div>
          </div>
        </div>
        </div><!-- /traj-views -->

        <input type="range" class="traj-slider" min="0" max="100" value="38" oninput="this.title=this.value+'%'">

        <!-- ③ 可视化分析 -->
        <div class="va-section">
          <div class="va-title">可视化分析 <span class="muted" style="font-weight:400;font-size:12px;">轨迹拖尾 / 速度·加速度 / 延迟·抖动</span></div>
          <div id="{prefix}_vaStart" style="padding:18px 0;">
            <button class="btn-primary btn" onclick="window.vaStart_{prefix}()">&#9654; 开始分析</button>
            <span class="muted" style="font-size:12px;margin-left:10px;">基于位置数据计算速度/加速度、延迟与抖动, 点击后加载</span>
          </div>
          <div id="{prefix}_vaContent" style="display:none;"></div>
        </div>
      </div>
    </div>
    """
    eps_json = json.dumps(eps)
    js = _PREVIEW_JS.replace("__PREFIX__", prefix).replace("__EPS__", eps_json)
    return html + js


_PREVIEW_JS = """
<script>
(function(){
  var EPS = __EPS__, PREFIX = "__PREFIX__";
  var mode = 'arm';                       // arm | base | moz
  var arms = new Set(['LeftArm','RightArm']);
  var curEp = 0, baseCharts = [], mozSrc = 'STATE';
  var ARM_ROWS = ['X','Y','Z','r','p','y','G'];
  var ARM_ORDER = ['LeftArm','Torso','RightArm'];

  // —— SVG sparkline: State(绿) + Cmd(蓝, 滞后) ——
  function spark(seed, a, r){
    var w=200, h=38, n=46, ptS=[], ptC=[];
    for(var i=0;i<n;i++){
      var x=(i/(n-1)*w);
      var vC=Math.sin(i/4 + seed*0.6 + a*1.3 + r*0.9)*0.7 + Math.sin(i/2 + r)*0.15;
      var vS=Math.sin((i-2)/4 + seed*0.6 + a*1.3 + r*0.9)*0.7 + Math.sin((i-2)/2 + r)*0.15;
      ptC.push(x.toFixed(1)+','+((0.5 - vC/2)*h*0.8 + h*0.1).toFixed(1));
      ptS.push(x.toFixed(1)+','+((0.5 - vS/2)*h*0.8 + h*0.1).toFixed(1));
    }
    return '<svg class="spark" viewBox="0 0 200 38" preserveAspectRatio="none">'+
      '<polyline points="'+ptC.join(' ')+'" fill="none" stroke="#1F80A0" stroke-width="1.2" vector-effect="non-scaling-stroke"/>'+
      '<polyline points="'+ptS.join(' ')+'" fill="none" stroke="#52c41a" stroke-width="1.2" vector-effect="non-scaling-stroke"/></svg>';
  }
  function renderArm(){
    var order = ARM_ORDER.filter(function(a){ return arms.has(a); });
    var html = '<table class="traj-grid"><thead><tr><th class="rlab"></th>';
    order.forEach(function(a){ html += '<th>'+a+'</th>'; });
    html += '</tr></thead><tbody>';
    ARM_ROWS.forEach(function(rn, ri){
      html += '<tr><td class="rlab">'+rn+'</td>';
      order.forEach(function(a, ai){
        if(rn==='G' && a==='Torso') html += '<td></td>';
        else html += '<td>'+spark(curEp, ai, ri)+'</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById(PREFIX+'_armView').innerHTML = html;
  }
  function renderBase(){
    baseCharts.forEach(function(c){c.destroy();}); baseCharts=[];
    var L=Array.from({length:60},function(_,i){return i;});
    function ser(sd,amp,lag){ return L.map(function(i){ return Math.sin((i-lag)/8 + sd)*amp; }); }
    var sp=document.getElementById(PREFIX+'_baseSpeed');
    if(sp) baseCharts.push(new Chart(sp,{type:'line',data:{labels:L,datasets:[
      {label:'State X',data:ser(curEp,0.4,0),borderColor:'#52c41a',borderWidth:1,pointRadius:0},
      {label:'State Y',data:ser(curEp+1,0.3,0),borderColor:'#95de64',borderWidth:1,pointRadius:0},
      {label:'Cmd X',data:ser(curEp,0.4,2),borderColor:'#1F80A0',borderWidth:1,borderDash:[3,2],pointRadius:0},
      {label:'Cmd Y',data:ser(curEp+1,0.3,2),borderColor:'#69c0ff',borderWidth:1,borderDash:[3,2],pointRadius:0}
    ]},options:{animation:false,responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:12,font:{size:10}}}},scales:{y:{title:{display:true,text:'Speed'},ticks:{font:{size:9}}},x:{ticks:{font:{size:9}}}}}}));
    var xy=document.getElementById(PREFIX+'_baseXY');
    if(xy){ var path=L.map(function(i){ return {x:Math.cos(i/9+curEp)*0.03+0.11, y:Math.sin(i/9+curEp)*0.03+0.11}; });
      baseCharts.push(new Chart(xy,{type:'scatter',data:{datasets:[
        {label:'State轨迹',data:path,borderColor:'#52c41a',backgroundColor:'#52c41a',showLine:true,pointRadius:0,borderWidth:1.5},
        {label:'Cmd轨迹',data:path.map(function(p){return{x:p.x+0.004,y:p.y+0.004};}),borderColor:'#1F80A0',backgroundColor:'#1F80A0',showLine:true,pointRadius:0,borderWidth:1.5,borderDash:[3,2]}
      ]},options:{animation:false,responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:12,font:{size:10}}}},scales:{x:{title:{display:true,text:'X(m)'},ticks:{font:{size:9}}},y:{title:{display:true,text:'Y'},ticks:{font:{size:9}}}}}}));
    }
  }
  function fmt(arr){ return arr.map(function(v){return v.toFixed(3);}).join(', '); }
  function renderMoz(){
    var d=(mozSrc==='CMD')?0.012:0, e=curEp*0.002;
    var rows=[
      ['左臂关节位置', fmt([0,0,0,0,0,0,0])],
      ['右臂关节位置', fmt([0,0,0,0,0,0,0])],
      ['左臂笛卡尔', fmt([0.215+d+e,-0.261+d,-0.052,-1.138,-1.654,-1.176])],
      ['右臂笛卡尔', fmt([-0.174-d+e,-0.292,-0.050,-1.370,-1.308,-0.968])],
      ['躯干关节位置', fmt([0,0,0,0,0,0,0])],
      ['躯干笛卡尔', fmt([-0.001,-0.000,1.094,0.360,0.069,-0.010])],
      ['底盘速度', fmt([0,0,0])],
      ['底盘位置','N/A'], ['底盘角度','N/A']
    ];
    var el=document.getElementById(PREFIX+'_mozInfo');
    if(el) el.innerHTML=rows.map(function(r){
      return '<div class="mz-row"><div class="mz-k">'+r[0]+':</div><div class="mz-v">'+r[1]+'</div></div>'; }).join('');
  }
  window['mozSrc_'+PREFIX]=function(s){
    mozSrc=s;
    var a=document.getElementById(PREFIX+'_mozState'), b=document.getElementById(PREFIX+'_mozCmd');
    if(a) a.classList.toggle('on', s==='STATE'); if(b) b.classList.toggle('on', s==='CMD');
    renderMoz();
  };
  function updateUI(){
    ['LeftArm','Torso','RightArm'].forEach(function(a){
      var b=document.getElementById(PREFIX+'_btn_'+a);
      if(b) b.classList.toggle('on', mode==='arm' && arms.has(a));
    });
    var bb=document.getElementById(PREFIX+'_btn_Base'); if(bb) bb.classList.toggle('on', mode==='base');
    var bm=document.getElementById(PREFIX+'_btn_Moz'); if(bm) bm.classList.toggle('on', mode==='moz');
    document.getElementById(PREFIX+'_armView').style.display = mode==='arm'?'':'none';
    document.getElementById(PREFIX+'_baseView').style.display = mode==='base'?'':'none';
    document.getElementById(PREFIX+'_mozView').style.display = mode==='moz'?'':'none';
    var lg=document.getElementById(PREFIX+'_legend');
    if(lg){
      if(mode==='arm') lg.innerHTML='<span><i style="background:#1F80A0"></i>CMD</span><span><i style="background:#52c41a"></i>State</span>';
      else if(mode==='moz') lg.innerHTML='<button class="tbtn '+(mozSrc==='STATE'?'on':'')+'" id="'+PREFIX+'_mozState" onclick="window.mozSrc_'+PREFIX+'(\\'STATE\\')">STATE</button>'+
                                         '<button class="tbtn '+(mozSrc==='CMD'?'on':'')+'" id="'+PREFIX+'_mozCmd" onclick="window.mozSrc_'+PREFIX+'(\\'CMD\\')">CMD</button>';
      else lg.innerHTML='';
    }
  }
  window['setMode_'+PREFIX]=function(m){ mode=m; updateUI(); if(m==='base') renderBase(); if(m==='moz') renderMoz(); };
  window['clickArm_'+PREFIX]=function(a){
    if(mode!=='arm'){ mode='arm'; arms=new Set([a]); }
    else if(arms.has(a)){ if(arms.size>1) arms.delete(a); }
    else arms.add(a);
    updateUI(); renderArm();
  };
  window['setEp_'+PREFIX]=function(i){
    curEp=i;
    var items=document.querySelectorAll('#'+PREFIX+'_strip .ep-item');
    items.forEach(function(e,idx){ e.classList.toggle('active', idx===i); });
    if(mode==='arm') renderArm(); else if(mode==='base') renderBase(); else if(mode==='moz') renderMoz();
  };
  // ════ 可视化分析 ════
  var vaArm='left', velCharts=[], latCharts=[];
  function rnd(s){ var x=Math.sin(s*12.9898)*43758.5453; return x-Math.floor(x); }
  function gam(sd,scale){ var u=rnd(sd)+0.001; return Math.max(0,(-Math.log(u))*scale*(0.5+rnd(sd*1.7+3))); }
  function gss(sd,s){ var u=rnd(sd)+1e-4,v=rnd(sd*2.1+7); return Math.sqrt(-2*Math.log(u))*Math.cos(6.2832*v)*s; }
  function samp(n,fn){ var a=[]; for(var i=0;i<n;i++)a.push(fn(i)); return a; }
  function tline(n,sd,base,amp,abs){ var a=[]; for(var i=0;i<n;i++){ var v=base+amp*Math.sin(i/9+sd)+amp*0.6*Math.sin(i/3+sd*2)+amp*0.5*(rnd(i+sd)-0.5); a.push(abs?Math.abs(v):v);} return a; }
  function destroyArr(arr){ arr.forEach(function(c){try{c.destroy();}catch(e){}}); arr.length=0; }

  function makeTime(arr,id,series,color,xl,yl){
    var ctx=document.getElementById(id); if(!ctx)return;
    arr.push(new Chart(ctx,{type:'line',data:{labels:series.map(function(_,i){return (i*0.2).toFixed(0);}),
      datasets:[{label:'State',data:series,borderColor:color,borderWidth:1,pointRadius:0}]},
      options:{animation:false,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:12,font:{size:10}}}},
        scales:{x:{title:{display:true,text:xl},ticks:{font:{size:9},maxTicksLimit:9}},y:{title:{display:true,text:yl},ticks:{font:{size:9}}}}}}));
  }
  var mlPlugin={id:'ml',afterDraw:function(ch){ var o=ch.$ml; if(!o)return; var ca=ch.chartArea,c=ch.ctx;
    [['mean','#cf1322'],['median','#389e0d']].forEach(function(k){ var px=ca.left+(o[k[0]]-o.mn)/(o.mx-o.mn)*(ca.right-ca.left);
      c.save(); c.strokeStyle=k[1]; c.setLineDash([5,4]); c.beginPath(); c.moveTo(px,ca.top); c.lineTo(px,ca.bottom); c.stroke(); c.restore(); }); }};
  function makeHist(arr,id,samps,color,label,unit){
    var ctx=document.getElementById(id); if(!ctx)return;
    var mn=Math.min.apply(null,samps),mx=Math.max.apply(null,samps),bins=30,w=(mx-mn)/bins||1,cnt=new Array(bins).fill(0);
    samps.forEach(function(v){ var b=Math.floor((v-mn)/w); if(b<0)b=0; if(b>=bins)b=bins-1; cnt[b]++; });
    var labels=[]; for(var i=0;i<bins;i++)labels.push((mn+i*w).toFixed(2));
    var mean=samps.reduce(function(s,x){return s+x;},0)/samps.length;
    var srt=samps.slice().sort(function(a,b){return a-b;}), median=srt[Math.floor(srt.length/2)];
    var ch=new Chart(ctx,{type:'bar',data:{labels:labels,datasets:[{label:label,data:cnt,backgroundColor:color}]},
      options:{animation:false,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:12,font:{size:10},
        generateLabels:function(c){ var d=Chart.defaults.plugins.legend.labels.generateLabels(c);
          d.push({text:'均值: '+mean.toFixed(3),fillStyle:'#cf1322'},{text:'中位数: '+median.toFixed(3),fillStyle:'#389e0d'}); return d; }}}},
        scales:{x:{title:{display:true,text:unit},ticks:{font:{size:9},maxTicksLimit:8}},y:{title:{display:true,text:'频数'},ticks:{font:{size:9}}}}},plugins:[mlPlugin]});
    ch.$ml={mean:mean,median:median,mn:mn,mx:mx}; ch.update(); arr.push(ch);
  }
  function renderVel(){
    destroyArr(velCharts);
    var sd=(vaArm==='left'?1:5)+curEp, N=400;
    makeTime(velCharts,PREFIX+'_lv_t',tline(N,sd,0.2,0.18,true),'#ff4d4f','时间 (s)','线速度 (m/s)');
    makeHist(velCharts,PREFIX+'_lv_cmd',samp(2000,function(i){return gam(i+sd,0.12);}),'#2f54eb','CMD','线速度 (m/s)');
    makeHist(velCharts,PREFIX+'_lv_st',samp(2000,function(i){return gam(i+sd,0.12);}),'#ff4d4f','State','线速度 (m/s)');
    makeTime(velCharts,PREFIX+'_av_t',tline(N,sd+1,0.7,0.6,true),'#faad14','时间 (s)','角速度 (rad/s)');
    makeHist(velCharts,PREFIX+'_av_cmd',samp(2000,function(i){return gam(i+sd+1,0.45);}),'#52c41a','CMD','角速度 (rad/s)');
    makeHist(velCharts,PREFIX+'_av_st',samp(2000,function(i){return gam(i+sd+1,0.45);}),'#faad14','State','角速度 (rad/s)');
    makeTime(velCharts,PREFIX+'_la_t',tline(N,sd+2,0,1.2,false),'#ff7875','时间 (s)','线加速度 (m/s²)');
    makeHist(velCharts,PREFIX+'_la_cmd',samp(2000,function(i){return gss(i+sd+2,1.0);}),'#91d5ff','CMD','线加速度 (m/s²)');
    makeHist(velCharts,PREFIX+'_la_st',samp(2000,function(i){return gss(i+sd+2,1.0);}),'#ff7875','State','线加速度 (m/s²)');
    makeTime(velCharts,PREFIX+'_aa_t',tline(N,sd+3,0,8,false),'#ffa940','时间 (s)','角加速度 (rad/s²)');
    makeHist(velCharts,PREFIX+'_aa_cmd',samp(2000,function(i){return gss(i+sd+3,7);}),'#95de64','CMD','角加速度 (rad/s²)');
    makeHist(velCharts,PREFIX+'_aa_st',samp(2000,function(i){return gss(i+sd+3,7);}),'#ffa940','State','角加速度 (rad/s²)');
  }
  function makeLat(arr,id,base,lag,aligned){
    var ctx=document.getElementById(id); if(!ctx)return;
    var labels=base.map(function(_,i){return (i*0.2).toFixed(0);});
    var cmd=base.map(function(v,i){return v+0.008*Math.sin(i/5);});
    var state=base.map(function(v,i){return (i-lag>=0?base[i-lag]:base[0])+0.008*Math.sin(i/5);});
    var bands=[]; if(aligned){ for(var i=0;i<base.length;i++){ if(rnd(i+curEp)>0.62) bands.push(i); } }
    var bandP={id:'bd',afterDraw:function(ch){ if(!aligned)return; var x=ch.scales.x,ca=ch.chartArea,c=ch.ctx; c.save(); c.fillStyle='rgba(255,77,79,0.10)';
      bands.forEach(function(i){ var px=x.getPixelForValue(labels[i]); c.fillRect(px-1,ca.top,3,ca.bottom-ca.top); }); c.restore(); }};
    arr.push(new Chart(ctx,{type:'line',data:{labels:labels,datasets:[
      {label:'CMD',data:cmd,borderColor:'#2f54eb',borderWidth:1,pointRadius:0},
      {label:'State',data:state,borderColor:'#ff4d4f',borderWidth:1,pointRadius:0}]},
      options:{animation:false,maintainAspectRatio:false,plugins:{legend:{labels:{boxWidth:12,font:{size:9}}}},
        scales:{x:{title:{display:true,text:'时间(秒)'},ticks:{font:{size:9},maxTicksLimit:7}},y:{title:{display:true,text:'位置 (m)'},ticks:{font:{size:9}}}}},plugins:[bandP]}));
  }
  function renderLat(){
    destroyArr(latCharts);
    var sd=10+curEp,N=400, xr=tline(N,sd,0.2,0.08,false), yr=tline(N,sd+1,-0.45,0.06,false);
    makeLat(latCharts,PREFIX+'_lat_xr',xr,2,false); makeLat(latCharts,PREFIX+'_lat_xa',xr,2,true);
    makeLat(latCharts,PREFIX+'_lat_yr',yr,2,false); makeLat(latCharts,PREFIX+'_lat_ya',yr,2,true);
  }
  // 轨迹拖尾 (custom 3D canvas, 带坐标轴)
  var trailTimer=null,trailIdx=200,trailSpeed=1,trailPath=null;
  var XR=[-0.4,0.4], YR=[-0.6,0.2], ZR=[-0.2,0.2];
  function buildTrail(){
    var n=200, Lc=[],Ls=[],Rc=[],Rs=[];
    for(var i=0;i<n;i++){
      var t=i/n;
      var lx=-0.05+0.16*Math.sin(i/14+curEp)*Math.exp(-t*0.25), ly=-0.32+0.10*Math.cos(i/18+curEp), lz=0.0+0.12*Math.sin(i/10+curEp);
      Ls.push({x:lx,y:ly,z:lz}); Lc.push({x:lx+0.012,y:ly+0.010,z:lz+0.008});
      var rx=0.10+0.16*Math.sin(i/12+curEp+1)*Math.exp(-t*0.25), ry=-0.30+0.10*Math.cos(i/16+curEp+1), rz=0.08+0.12*Math.sin(i/11+curEp+1);
      Rs.push({x:rx,y:ry,z:rz}); Rc.push({x:rx+0.012,y:ry+0.010,z:rz+0.008});
    }
    trailPath={Lc:Lc,Ls:Ls,Rc:Rc,Rs:Rs};
  }
  function drawTrail(){
    var cv=document.getElementById(PREFIX+'_trail'); if(!cv||!trailPath)return;
    var W=cv.width=cv.clientWidth||700, H=cv.height=380, c=cv.getContext('2d'); c.clearRect(0,0,W,H);
    var ex=[0.86,0.5], ey=[-0.86,0.5], ez=[0,-1], s=Math.min(W,H)*0.62, ox=W*0.46, oy=H*0.60;
    function P(x,y,z){ return [ox+(x*ex[0]+y*ey[0]+z*ez[0])*s, oy+(x*ex[1]+y*ey[1]+z*ez[1])*s]; }
    function L(a,b,col,w){ c.beginPath(); c.strokeStyle=col; c.lineWidth=w; c.moveTo(a[0],a[1]); c.lineTo(b[0],b[1]); c.stroke(); }
    var g, x, y, z;
    for(g=0;g<=4;g++){ x=XR[0]+(XR[1]-XR[0])*g/4; L(P(x,YR[0],ZR[0]),P(x,YR[1],ZR[0]),'#eef1f4',1);
                       y=YR[0]+(YR[1]-YR[0])*g/4; L(P(XR[0],y,ZR[0]),P(XR[1],y,ZR[0]),'#eef1f4',1); }
    for(g=0;g<=4;g++){ z=ZR[0]+(ZR[1]-ZR[0])*g/4; L(P(XR[0],YR[0],z),P(XR[0],YR[1],z),'#f2f5f8',1); L(P(XR[0],YR[1],z),P(XR[1],YR[1],z),'#f2f5f8',1); }
    for(g=0;g<=4;g++){ x=XR[0]+(XR[1]-XR[0])*g/4; L(P(x,YR[1],ZR[0]),P(x,YR[1],ZR[1]),'#f2f5f8',1);
                       y=YR[0]+(YR[1]-YR[0])*g/4; L(P(XR[0],y,ZR[0]),P(XR[0],y,ZR[1]),'#f2f5f8',1); }
    L(P(XR[0],YR[0],ZR[0]),P(XR[1],YR[0],ZR[0]),'#9aa3ad',1.3);
    L(P(XR[0],YR[0],ZR[0]),P(XR[0],YR[1],ZR[0]),'#9aa3ad',1.3);
    L(P(XR[0],YR[0],ZR[0]),P(XR[0],YR[0],ZR[1]),'#9aa3ad',1.3);
    c.fillStyle='#888'; c.font='11px sans-serif';
    var xe=P(XR[1],YR[0],ZR[0]); c.fillText('X (m)',xe[0]+4,xe[1]+12);
    var ye=P(XR[0],YR[1],ZR[0]); c.fillText('Y (m)',ye[0]-40,ye[1]+12);
    var ze=P(XR[0],YR[0],ZR[1]); c.fillText('Z (m)',ze[0]-36,ze[1]-2);
    c.fillStyle='#aab'; c.font='9px sans-serif';
    for(g=0;g<=4;g++){ x=XR[0]+(XR[1]-XR[0])*g/4; var px=P(x,YR[0],ZR[0]); c.fillText(x.toFixed(1),px[0]-6,px[1]+13); }
    for(g=0;g<=4;g++){ y=YR[0]+(YR[1]-YR[0])*g/4; var py=P(XR[0],y,ZR[0]); c.fillText(y.toFixed(1),py[0]-24,py[1]+9); }
    for(g=0;g<=4;g++){ z=ZR[0]+(ZR[1]-ZR[0])*g/4; var pz=P(XR[0],YR[0],z); c.fillText(z.toFixed(1),pz[0]-24,pz[1]+3); }
    function path(arr,col,up){ c.beginPath(); c.strokeStyle=col; c.lineWidth=2;
      for(var i=0;i<up&&i<arr.length;i++){ var q=P(arr[i].x,arr[i].y,arr[i].z); i?c.lineTo(q[0],q[1]):c.moveTo(q[0],q[1]); } c.stroke();
      if(up>0){ var h=arr[Math.min(up-1,arr.length-1)], hp=P(h.x,h.y,h.z); c.fillStyle=col; c.beginPath(); c.arc(hp[0],hp[1],3.5,0,6.2832); c.fill(); } }
    path(trailPath.Lc,'#ff4d4f',trailIdx); path(trailPath.Ls,'#2f54eb',trailIdx);
    path(trailPath.Rc,'#389e0d',trailIdx); path(trailPath.Rs,'#fa8c16',trailIdx);
    var fl=document.getElementById(PREFIX+'_frame'); if(fl) fl.textContent='帧: '+Math.min(trailIdx,200);
  }
  window['vaTrail_'+PREFIX]=function(act){
    if(act==='play'){ if(trailTimer)return; trailTimer=setInterval(function(){ trailIdx+=trailSpeed; if(trailIdx>200)trailIdx=0; drawTrail(); },60); }
    else if(act==='pause'){ clearInterval(trailTimer); trailTimer=null; }
    else if(act==='speed'){ trailSpeed=trailSpeed>=4?1:trailSpeed*2; var s=document.getElementById(PREFIX+'_spd'); if(s)s.textContent=trailSpeed+'x'; } };
  window['vaSetArm_'+PREFIX]=function(a){ vaArm=a;
    var l=document.getElementById(PREFIX+'_vaL'),r=document.getElementById(PREFIX+'_vaR');
    if(l)l.classList.toggle('on',a==='left'); if(r)r.classList.toggle('on',a==='right'); renderVel(); };
  function vaHTML(){
    function metric(k,name,unit){
      return '<h5 class="va-sub">'+(vaArm==='left'?'左臂':'右臂')+name+'随时间变化</h5>'+
        '<div class="va-box va-box-lg"><canvas id="'+PREFIX+'_'+k+'_t"></canvas></div>'+
        '<div class="va-grid2">'+
          '<div><div class="va-ct">CMD '+name+'分布</div><div class="va-box"><canvas id="'+PREFIX+'_'+k+'_cmd"></canvas></div></div>'+
          '<div><div class="va-ct">State '+name+'分布</div><div class="va-box"><canvas id="'+PREFIX+'_'+k+'_st"></canvas></div></div>'+
        '</div>';
    }
    return '<h4 class="va-h">轨迹拖尾动画</h4>'+
      '<div class="va-trailbar"><button class="btn" onclick="window.vaTrail_'+PREFIX+'(\\'play\\')">播放</button>'+
        '<button class="btn" onclick="window.vaTrail_'+PREFIX+'(\\'speed\\')">倍速 <span id="'+PREFIX+'_spd">1x</span></button>'+
        '<button class="btn" onclick="window.vaTrail_'+PREFIX+'(\\'pause\\')">暂停</button></div>'+
      '<div class="va-trail"><canvas id="'+PREFIX+'_trail"></canvas></div>'+
      '<div class="va-trailfoot"><span class="muted" id="'+PREFIX+'_frame">帧: 0</span>'+
        '<div class="va-legend2">'+
          '<span><i style="background:#ff4d4f"></i>左臂指令</span><span><i style="background:#2f54eb"></i>左臂状态</span>'+
          '<span><i style="background:#389e0d"></i>右臂指令</span><span><i style="background:#fa8c16"></i>右臂状态</span>'+
        '</div></div>'+
      '<h4 class="va-h">机械臂速度加速度分析</h4>'+
      '<div class="va-armtoggle"><button class="tbtn '+(vaArm==='left'?'on':'')+'" id="'+PREFIX+'_vaL" onclick="window.vaSetArm_'+PREFIX+'(\\'left\\')">左臂</button>'+
        '<button class="tbtn '+(vaArm==='right'?'on':'')+'" id="'+PREFIX+'_vaR" onclick="window.vaSetArm_'+PREFIX+'(\\'right\\')">右臂</button></div>'+
      metric('lv','线速度','m/s')+metric('av','角速度','rad/s')+metric('la','线加速度','m/s²')+metric('aa','角加速度','rad/s²')+
      '<h4 class="va-h">延迟对比与抖动分析</h4>'+
      '<div class="va-params">延迟步数 <b>8</b> &nbsp;·&nbsp; 抖动检测阈值 <b>0.03</b> &nbsp;·&nbsp; 静止数据阈值 <b>0.01</b> &nbsp;·&nbsp; <label><input type="checkbox" checked> 启用抖动检测</label></div>'+
      '<div class="va-ct" style="font-weight:600;margin-bottom:8px;">'+(vaArm==='left'?'左':'右')+'臂状态与指令延迟对比 (抖动率 62.9%, 红色为抖动区间)</div>'+
      '<div class="va-grid2">'+
        '<div><div class="va-ct">X维度 - 原始数据</div><div class="va-box"><canvas id="'+PREFIX+'_lat_xr"></canvas></div></div>'+
        '<div><div class="va-ct">X维度 - 延迟对齐后 (延迟8步)</div><div class="va-box"><canvas id="'+PREFIX+'_lat_xa"></canvas></div></div>'+
        '<div><div class="va-ct">Y维度 - 原始数据</div><div class="va-box"><canvas id="'+PREFIX+'_lat_yr"></canvas></div></div>'+
        '<div><div class="va-ct">Y维度 - 延迟对齐后 (延迟8步)</div><div class="va-box"><canvas id="'+PREFIX+'_lat_ya"></canvas></div></div>'+
      '</div>';
  }
  window['vaStart_'+PREFIX]=function(){
    document.getElementById(PREFIX+'_vaStart').style.display='none';
    var c=document.getElementById(PREFIX+'_vaContent'); c.style.display='block'; c.innerHTML=vaHTML();
    setTimeout(function(){ buildTrail(); trailIdx=200; drawTrail(); renderVel(); renderLat(); }, 40);
  };

  setTimeout(function(){ if(document.getElementById(PREFIX+'_armView')){ updateUI(); renderArm(); } }, 60);
})();
</script>
"""


# ════════════════════════════════════════════════════════════════
# Section 4: Routes
# ════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    # 概览页已去掉, 默认进入「数据查询」
    return redirect("/query")


@app.route("/lake")
def lake():
    mode = request.args.get("mode", "task")        # task | tag | flat
    sel = request.args.get("sel", "")
    if mode not in ("task", "tag", "flat"):
        mode = "task"

    # —— 左树: 三种聚合模式 ——
    pills = "".join(
        f'<a class="tree-mode {"active" if mode==m else ""}" href="/lake?mode={m}">{lab}</a>'
        for m, lab in [("tag", "标签聚合"), ("task", "任务聚合"), ("flat", "平铺")]
    )
    tree = ('<div class="tree-head">'
            '<span class="th-left"><span class="tp-toggle" onclick="toggleTP(this)" title="折叠/展开目录"><span class="sc-col">&laquo;</span><span class="sc-exp">&raquo;</span></span><span class="th-title">数据管理</span></span>'
            '<span class="th-actions">'
            '<a href="#" onclick="toast(\'Demo: 导出入湖任务已提交\');return false;" style="font-size:12px;">+ 导出入湖</a></span></div>'
            f'<div class="tree-modes">{pills}</div>'
            '<div class="tree-search"><input placeholder="搜索..."></div><div class="tree-body">')

    if mode == "task":
        if sel not in [t["id"] for t in TASKS]:
            sel = TASKS[0]["id"]
        for t in TASKS:
            n = len([r for r in RECORDINGS if r["task"] == t["id"]])
            cls = "active" if t["id"] == sel else ""
            tree += (f'<a class="tree-leaf {cls}" style="padding-left:16px;" href="/lake?mode=task&sel={t["id"]}">'
                     f'{t["name"]} <span class="sub">· {n} ep</span></a>')
        recs = [r for r in RECORDINGS if r["task"] == sel]
        tt = next(x for x in TASKS if x["id"] == sel)
        title, sub = tt["name"], tt["zh"]
        scope = f"任务 {tt['name']}"

    elif mode == "tag":
        # 按标签分组(场景/技能/质量), 叶子=标签
        all_tags = [tid for tid, lab, grp in TAG_DEFS
                    if any(tid in rec_tags(r) for r in RECORDINGS)]
        if sel not in all_tags:
            sel = all_tags[0]
        for grp in TAG_GROUP_ORDER:
            grp_tags = [(tid, lab) for tid, lab, g in TAG_DEFS if g == grp and tid in all_tags]
            if not grp_tags:
                continue
            tree += f'<div class="tree-grp" onclick="toggleTree(this)"><span class="caret">&#9656;</span>{grp}</div><div class="tree-children">'
            for tid, lab in grp_tags:
                n = sum(1 for r in RECORDINGS if tid in rec_tags(r))
                cls = "active" if tid == sel else ""
                tree += (f'<a class="tree-leaf {cls}" href="/lake?mode=tag&sel={tid}">'
                         f'{lab} <span class="sub">· {n} ep</span></a>')
            tree += '</div>'
        recs = [r for r in RECORDINGS if sel in rec_tags(r)]
        title, sub = TAG_LABEL.get(sel, sel), "标签"
        scope = f"标签「{TAG_LABEL.get(sel, sel)}」"

    else:  # flat 平铺: 每条 episode 一个叶子
        all_ids = [str(r["id"]) for r in RECORDINGS]
        if sel not in all_ids:
            sel = all_ids[0]
        for r in RECORDINGS:
            cls = "active" if str(r["id"]) == sel else ""
            tags = " ".join(f'<span class="tg">{x}</span>' for x in rec_tag_labels(r)[:2])
            tree += (f'<a class="tree-leaf {cls}" style="padding-left:16px;" href="/lake?mode=flat&sel={r["id"]}">'
                     f'#{r["id"]} <span class="sub">· {r["task"]}</span><div style="margin-top:2px;">{tags}</div></a>')
        rsel = get_rec(int(sel))
        recs = [rsel] if rsel else []
        title, sub = f'Episode #{sel}', (rsel["task"] if rsel else "")
        scope = f"Episode #{sel}"
    tree += '</div>'

    total_frames = sum(r["frames"] for r in recs)
    collections = sorted(set(r["collection"] for r in recs))
    tasks_in = sorted(set(r["task"] for r in recs))
    tag_union = sorted(set(t for r in recs for t in rec_tag_labels(r)))
    eps = recs_to_episodes(recs)

    # 数据预览 Tab
    preview = (f'<div class="tab-pane active" id="pane-preview">'
               f'<div class="muted" style="margin-bottom:12px;">{scope} · 共 {len(recs)} 个 episode，左侧逐个预览</div>'
               f'{preview_block("lake", eps)}</div>')

    # 质检 Tab
    qa_rows = ""
    for i, r in enumerate(recs):
        life_html = "active" if r["life"] == "active" else '<span class="tag tag-orange">已隔离</span>'
        tags = " ".join(f'<span class="tg">{x}</span>' for x in rec_tag_labels(r))
        qa_rows += (f'<tr><td>Ep {i} · #{r["id"]}</td><td>{r["task"]}</td>'
                    f'<td><span class="tag tag-gray">{r["type"]}</span></td>'
                    f'<td>{r["frames"]:,}</td><td>{tags}</td><td>{qa_html(r["qa"])}</td>'
                    f'<td>{life_html}</td></tr>')
    n_pass = sum(1 for r in recs if r["qa"] == "pass")
    n_warn = sum(1 for r in recs if r["qa"] == "warn")
    n_fail = sum(1 for r in recs if r["qa"] == "fail")
    qa = f"""
    <div class="tab-pane" id="pane-qa">
      <div style="display:flex;gap:10px;margin-bottom:14px;">
        <span class="tag" style="color:#389e0d;background:#f6ffed;border-color:#b7eb8f;">PASS {n_pass}</span>
        <span class="tag" style="color:#d48806;background:#fffbe6;border-color:#ffe58f;">WARN {n_warn}</span>
        <span class="tag" style="color:#cf1322;background:#fff2f0;border-color:#ffccc7;">FAIL {n_fail}</span>
      </div>
      <table class="ant-table"><thead><tr><th>Episode</th><th>Task</th><th>类型</th><th>帧数</th><th>标签</th><th>质检</th><th>生命周期</th></tr></thead>
      <tbody>{qa_rows}</tbody></table>
    </div>
    """

    # 基本信息 Tab
    tags_html = "".join(f'<span class="tg">{x}</span>' for x in tag_union) or "—"
    info = f"""
    <div class="tab-pane" id="pane-info">
      <div class="desc-grid">
        <div class="dk">范围</div><div class="dv">{scope}</div>
        <div class="dk">episode 数</div><div class="dv">{len(recs)} 条</div>
        <div class="dk">总帧数</div><div class="dv">{total_frames:,} frames · {round(total_frames/30/60,1) if total_frames else 0} min</div>
        <div class="dk">涉及 task</div><div class="dv">{", ".join(tasks_in) or "—"}</div>
        <div class="dk">涉及标签</div><div class="dv">{tags_html}</div>
        <div class="dk">采集批次</div><div class="dv">{", ".join("#"+str(c) for c in collections) or "—"}</div>
        <div class="dk">本体 / 帧率</div><div class="dv">moz1 · 30 fps</div>
        <div class="dk">相机</div><div class="dv">cam_high · cam_left_wrist · cam_right_wrist (240×320)</div>
      </div>
    </div>
    """
    head = f"""
    <div class="detail-head">
      <div><div class="dh-title">{title} <span class="muted" style="font-size:13px;font-weight:400;">{sub}</span></div>
      <div class="dh-meta"><span>{len(recs)} episodes</span><span>{total_frames:,} frames</span><span>{len(tag_union)} 个标签</span></div></div>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="switchTab(this,'preview')">数据预览</div>
      <div class="tab" onclick="switchTab(this,'qa')">质检</div>
      <div class="tab" onclick="switchTab(this,'info')">基本信息</div>
    </div>
    <div class="pane-wrap">{preview}{qa}{info}</div>
    """
    content = f'<div class="split"><div class="tree-panel">{tree}</div><div class="detail-panel">{head}</div></div>'
    return render_page("数据管理", content, active="lake",
                       breadcrumb=f'数据湖 / 数据管理 / <b>{title}</b>')


DEVICES = ["Moz", "uDAS"]
OPERATORS_LIST = ["Lance Li", "Wei Zhang", "Min Chen"]

def rec_device(r):
    return "Moz" if r["id"] % 2 == 0 else "uDAS"

def rec_operator(r):
    return OPERATORS_LIST[r["id"] % 3]


def build_query_filters():
    """生成与数据查询页一致的筛选字段 (用于新建数据集弹窗)。前两个 grow 加宽。"""
    tag_checks = ""
    for grp in TAG_GROUP_ORDER:
        tag_checks += f'<div class="ms-grp">{grp}</div>'
        for tid, lab, g in TAG_DEFS:
            if g == grp:
                tag_checks += f'<label><input type="checkbox" value="{tid}" onchange="msUpdate(this)">{lab}</label>'
    tag_ms = ('<div class="ms-wrap"><div class="ms-trigger" data-base="标签" onclick="this.closest(\'.ms-wrap\').classList.toggle(\'open\')">'
              '<span class="ms-label">标签</span></div><div class="ms-panel">' + tag_checks + '</div></div>')
    qa_checks = "".join(f'<label><input type="checkbox" value="{v}" onchange="msUpdate(this)">{lab}</label>'
                        for v, lab in [("pass", "合格"), ("fail", "不合格"), ("warn", "操作失误")])
    qa_ms = ('<div class="ms-wrap"><div class="ms-trigger" data-base="全部" onclick="this.closest(\'.ms-wrap\').classList.toggle(\'open\')">'
             '<span class="ms-label">全部</span></div><div class="ms-panel">' + qa_checks + '</div></div>')
    dev = '<select><option value="">全部</option>' + "".join(f'<option>{d}</option>' for d in DEVICES) + '</select>'

    def _ms(base, items):
        checks = "".join(f'<label><input type="checkbox" value="{v}" onchange="msUpdate(this)">{v}</label>' for v in items)
        return ('<div class="ms-wrap"><div class="ms-trigger" data-base="' + base + '" onclick="this.closest(\'.ms-wrap\').classList.toggle(\'open\')">'
                '<span class="ms-label">' + base + '</span></div><div class="ms-panel">' + checks + '</div></div>')
    op = _ms("全部", OPERATORS_LIST)
    typ = _ms("全部", ["normal", "dagger", "test", "eval"])
    rng = '<div class="q-range"><input type="date"><span class="q-range-sep">~</span><input type="date"></div>'
    # 布局: 任务 id 一行, 标签 一行, 采集类型+时间 一行, 质检结果+设备+操作员 一行 (均撑满)
    return (
        '<div class="q-filter-row q-adv-row"><div class="q-field"><label>任务 Task ID</label><input placeholder="如 t1,t2 多个逗号隔开"></div></div>'
        f'<div class="q-filter-row q-adv-row"><div class="q-field"><label>标签</label>{tag_ms}</div></div>'
        f'<div class="q-filter-row q-adv-row"><div class="q-field"><label>采集类型</label>{typ}</div><div class="q-field"><label>采集时间</label>{rng}</div></div>'
        f'<div class="q-filter-row q-adv-row"><div class="q-field"><label>质检结果</label>{qa_ms}</div><div class="q-field"><label>采集设备</label>{dev}</div><div class="q-field"><label>操作员</label>{op}</div></div>'
    )


@app.route("/query")
def query():
    # 筛选条件对齐数据拉取脚本 export_dataset.py 的参数
    f_task = request.args.get("task", "")          # 多个 task id, 逗号隔开
    f_device = request.args.get("device", "")
    f_operators = request.args.getlist("operator")  # 多选操作员
    f_types = request.args.getlist("type")          # 多选采集类型
    f_qas = request.args.getlist("qa")             # 多选: pass/fail/warn
    f_tags = request.args.getlist("tag")           # 多选标签
    f_from = request.args.get("from", "")
    f_to = request.args.get("to", "")
    nl = request.args.get("nl", "")

    task_list = [t.strip() for t in f_task.split(",") if t.strip()]

    # —— 过滤 ——
    res = []
    for r in RECORDINGS:
        if task_list and r["task"] not in task_list:
            continue
        if f_tags and not any(t in rec_tags(r) for t in f_tags):
            continue
        if f_device and rec_device(r) != f_device:
            continue
        if f_operators and rec_operator(r) not in f_operators:
            continue
        if f_types and r["type"] not in f_types:
            continue
        if f_qas and r["qa"] not in f_qas:
            continue
        if f_from and r["at"][:10] < f_from:
            continue
        if f_to and r["at"][:10] > f_to:
            continue
        res.append(r)

    # 展示用结果集: 模拟较大命中量 (用于分页演示), 由筛选结果循环铺开
    disp = [res[i % len(res)] for i in range(47)] if res else []

    # —— 配方助手: 当前筛选结果的 提示词 / 标签 构成 ——
    prompt_counts = {}
    for r in disp:
        prompt_counts[r["task"]] = prompt_counts.get(r["task"], 0) + 1
    prompt_comp = [{"key": k, "label": task_instr(k), "count": c} for k, c in prompt_counts.items()]
    skill_defs = [(tid, lab) for tid, lab, grp in TAG_DEFS if grp == "技能"]
    tag_comp = []
    for tid, lab in skill_defs:
        c = sum(1 for r in disp if tid in rec_tags(r))
        if c:
            tag_comp.append({"key": tid, "label": lab, "count": c})
    recipe_data_js = (f"window._rcPrompt={json.dumps(prompt_comp, ensure_ascii=False)};"
                      f"window._rcTag={json.dumps(tag_comp, ensure_ascii=False)};"
                      f"window._rcBaseN={len(disp)};")
    # 预览抽屉: id → episode 序号 (复用 preview_block 的轨迹组件)
    qprev_map = {r["id"]: {"idx": i, "qa": r["qa"]} for i, r in enumerate(res)}
    recipe_data_js += f"window._qprevMap={json.dumps(qprev_map, ensure_ascii=False)};"
    prev_eps = recs_to_episodes(res) if res else recs_to_episodes([RECORDINGS[0]])

    # —— 生成 SQL (服务端, 反映当前筛选) ——
    qa_sql = {"pass": "PASS", "fail": "FAIL", "warn": "WARN"}
    conds = ["robot_type = 'moz1'"]
    if task_list:
        conds.append("task IN (" + ", ".join(f"'{t}'" for t in task_list) + ")")
    if f_device:
        conds.append(f"capture_device = '{f_device}'")
    if f_operators:
        conds.append("operator IN (" + ", ".join(f"'{o}'" for o in f_operators) + ")")
    if f_types:
        conds.append("type IN (" + ", ".join(f"'{t}'" for t in f_types) + ")")
    if f_qas:
        conds.append("qa_status IN (" + ", ".join(f"'{qa_sql.get(q, q.upper())}'" for q in f_qas) + ")")
    if f_tags:
        for t in f_tags:
            conds.append(f"array_contains(tags, '{TAG_LABEL.get(t, t)}')")
    if f_from:
        conds.append(f"collected_at >= '{f_from}'")
    if f_to:
        conds.append(f"collected_at <= '{f_to}'")
    where = "\n  AND ".join(conds)
    sql = ("SELECT episode_index, recording_id, task, collection_id, capture_device,\n"
           "       operator, frames, duration_s, collected_at, qa_status\n"
           "FROM   lake.recordings\n"
           f"WHERE  {where}\n"
           "ORDER BY collected_at DESC;")

    # —— 选择器 ——
    def sel(name, cur, options, placeholder):
        opts = f'<option value="">{placeholder}</option>'
        for v, lab in options:
            s = " selected" if v == cur else ""
            opts += f'<option value="{v}"{s}>{lab}</option>'
        cls = "has-value" if cur else ""
        return f'<select name="{name}" class="{cls}">{opts}</select>'

    # 任务: 文本输入, 多个 task id 逗号隔开
    task_cls = "has-value" if f_task else ""
    task_input = f'<input name="task" class="{task_cls}" value="{f_task}" placeholder="如 t1,t2 多个逗号隔开">'

    # 多选下拉 (ms-wrap)
    def ms(name, base, items, selected):
        n = len(selected)
        label = f"{base} ({n})" if n else base
        checks = "".join(
            f'<label><input type="checkbox" name="{name}" value="{v}"'
            f'{" checked" if v in selected else ""} onchange="msUpdate(this)">{lab}</label>'
            for v, lab in items)
        return (f'<div class="ms-wrap"><div class="ms-trigger {"has-value" if n else ""}" data-base="{base}" '
                f'onclick="this.closest(\'.ms-wrap\').classList.toggle(\'open\')">'
                f'<span class="ms-label">{label}</span></div><div class="ms-panel">{checks}</div></div>')

    # 标签多选 (按 场景/技能/质量 分组)
    tag_checks = ""
    for grp in TAG_GROUP_ORDER:
        tag_checks += f'<div class="ms-grp">{grp}</div>'
        for tid, lab, g in TAG_DEFS:
            if g == grp:
                ck = " checked" if tid in f_tags else ""
                tag_checks += (f'<label><input type="checkbox" name="tag" value="{tid}"{ck} '
                               f'onchange="msUpdate(this)">{lab}</label>')
    n_tag = len(f_tags)
    tag_ms = (f'<div class="ms-wrap"><div class="ms-trigger {"has-value" if n_tag else ""}" data-base="标签" '
              f'onclick="this.closest(\'.ms-wrap\').classList.toggle(\'open\')">'
              f'<span class="ms-label">{("标签 ("+str(n_tag)+")") if n_tag else "标签"}</span></div>'
              f'<div class="ms-panel">{tag_checks}</div></div>')

    qa_ms = ms("qa", "全部", [("pass", "合格"), ("fail", "不合格"), ("warn", "操作失误")], f_qas)
    dev_sel = sel("device", f_device, [(d, d) for d in DEVICES], "全部")
    op_sel = ms("operator", "全部", [(o, o) for o in OPERATORS_LIST], f_operators)
    type_sel = ms("type", "全部", [("normal", "normal"), ("dagger", "dagger"), ("test", "test"), ("eval", "eval")], f_types)

    # 所有筛选条件默认全部展开 (不再折叠)
    adv_fd = ""

    top_card = f"""
    <div class="q-filters">
      <form method="get" action="/query" id="qform">
        <input type="hidden" name="nl" id="nlField" value="{nl}">
        <div class="q-filter-row">
          <div class="q-field grow"><label>任务 Task ID</label>{task_input}</div>
          <div class="q-field grow"><label>标签</label>{tag_ms}</div>
        </div>
        <div class="q-filter-row q-adv-row" id="advPanel" style="{adv_fd}margin-top:14px;">
          <div class="q-field"><label>质检结果</label>{qa_ms}</div>
          <div class="q-field"><label>采集设备</label>{dev_sel}</div>
          <div class="q-field"><label>操作员</label>{op_sel}</div>
          <div class="q-field"><label>采集类型</label>{type_sel}</div>
          <div class="q-field"><label>采集时间</label>
            <div class="q-range">
              <input type="date" name="from" value="{f_from}">
              <span class="q-range-sep">~</span>
              <input type="date" name="to" value="{f_to}">
            </div>
          </div>
        </div>
        <div class="q-filter-tools">
          <button type="button" class="ai-fab" onclick="aiOpen()"><span class="ic-ai">&#10022;</span> AI 助手</button>
          <button type="button" class="recipe-btn" onclick="recipeOpen()"><span>&#129514;</span> 配方助手</button>
          <span class="tools-divider"></span>
          <a href="/query" class="btn">重置</a>
          <button type="submit" class="btn-primary btn">查询</button>
        </div>
      </form>
    </div>
    """

    # —— AI 辅助 侧栏 (聊天式, 支持多轮; 同排推开, 无遮挡) ——
    ai_panel = f"""
    <aside class="ai-side" id="aiDrawer">
      <div class="ai-inner">
        <div class="ai-head"><b><span class="ic-ai" style="color:#9b59b6;">&#10022;</span> AI 助手</b><button class="drawer-close" onclick="aiClose()">&times;</button></div>
        <div class="ai-body" id="aiMsgs">
          <div class="ai-msg ai-bot">
            <div class="ai-bubble">你好 &#128075; 用自然语言描述你想找的数据, 我帮你翻译成 SQL 并执行。试试这些:</div>
            <div class="ai-chips">
              <span class="ai-chip" onclick="aiSend('擦白板任务、近一周、已质检通过的 episode')">擦白板·近一周·合格</span>
              <span class="ai-chip" onclick="aiSend('Moz 设备、Lance Li 采集、帧数大于 1000 的 episode')">Moz·Lance·帧数&gt;1000</span>
              <span class="ai-chip" onclick="aiSend('近一周采集、操作失误的 episode')">近一周·操作失误</span>
            </div>
          </div>
        </div>
        <div class="ai-input">
          <textarea id="aiInput" placeholder="描述要查询的数据, 回车发送 (Shift+回车换行)" onkeydown="aiKey(event)"></textarea>
          <button class="ai-send" onclick="aiSend()" title="发送">&#10148;</button>
        </div>
      </div>
    </aside>
    """

    # —— 配方助手 侧栏: 提示词/标签构成比例条, 拖动调比例, 按比例随机采样 ——
    recipe_panel = """
    <aside class="ai-side" id="recipeDrawer">
      <div class="ai-inner">
        <div class="ai-head"><b>&#129514; 配方助手</b><button class="drawer-close" onclick="recipeClose()">&times;</button></div>
        <div class="ai-body">
          <div class="rc-intro">基于当前筛选的 <b id="rcBase">0</b> 个 episode。每类权重默认 <b>&times;1</b>(保持原始构成), 拖动调整某类的<b>相对权重</b>(其余不变), 系统按相对比例随机采样。</div>
          <div class="rc-sec">提示词构成 <span class="muted">按任务 prompt</span></div>
          <div id="rcPrompt"></div>
          <div class="rc-sec">标签构成 <span class="muted">按技能标签</span></div>
          <div id="rcTag"></div>
        </div>
        <div class="rc-foot">
          <div class="rc-count">采样后约 <b id="rcCount">0</b> 个 episode <span class="muted" id="rcOf"></span></div>
          <div style="display:flex;gap:8px;justify-content:flex-end;">
            <button class="btn" onclick="recipeReset()">重置</button>
            <button class="btn-primary btn" onclick="recipeApply()">确认采样</button>
          </div>
        </div>
      </div>
    </aside>
    """

    # —— 结果: 按 episode 平铺 (每页 20 条) ——
    PAGE_SIZE = 20
    rows = ""
    for i, r in enumerate(disp):
        pg = i // PAGE_SIZE
        tags = " ".join(f'<span class="tg">{x}</span>' for x in rec_tag_labels(r))
        rows += (f'<tr data-pg="{pg}" style="{"display:none;" if pg else ""}"><td><b>Ep {i}</b></td><td>#{r["id"]}</td><td>{r["task"]}</td>'
                 f'<td>{tags}</td>'
                 f'<td>{rec_device(r)}</td>'
                 f'<td><span class="tag tag-gray">{r["type"]}</span></td>'
                 f'<td>{r["frames"]:,}</td><td>{r["dur"]}s</td>'
                 f'<td><a href="#" onclick="qPreview({r["id"]});return false;">预览</a></td></tr>')
    if not rows:
        rows = '<tr><td colspan="9" class="muted" style="text-align:center;padding:30px;">无匹配 episode, 调整筛选条件试试</td></tr>'
    total_frames = sum(r["frames"] for r in disp)
    n_disp = len(disp)
    n_pages = max(1, (n_disp + PAGE_SIZE - 1) // PAGE_SIZE)
    pager = ""
    if n_pages > 1:
        btns = "".join(
            f'<button class="pg-btn{" active" if p == 0 else ""}" data-p="{p}" onclick="qGoPage({p})">{p+1}</button>'
            for p in range(n_pages))
        pager = (f'<div class="q-pager"><span class="muted" style="font-size:12px;">共 {n_disp} 条 · 每页 {PAGE_SIZE} 条</span>'
                 f'<div class="pg-btns">{btns}</div></div>')
    result_card = f"""
    <div class="card">
      <h3>查询结果 · 按 episode 平铺
        <span class="muted" id="qResMeta" style="font-size:13px;font-weight:400;">默认展示 20 条, 更多请精确查询 · 共 {n_disp} 条命中 · {total_frames:,} frames</span>
        <button class="btn btn-secondary" style="float:right;" onclick="document.getElementById('buildDsDrawer').classList.add('active')">用结果建数据集</button>
      </h3>
      <div class="q-table-scroll">
        <table class="ant-table">
          <thead><tr><th>Episode</th><th>Recording</th><th>Task</th><th>标签</th><th>设备</th><th>类型</th><th>帧数</th><th>时长</th><th>操作</th></tr></thead>
          <tbody id="qbody">{rows}</tbody>
        </table>
      </div>
      {pager}
    </div>
    """

    prev_drawer = f"""
    <div class="drawer-mask" id="qPrevDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer qp-drawer">
        <div class="drawer-head"><h3 id="qPrevTitle">Episode 预览</h3><button class="drawer-close" onclick="document.getElementById('qPrevDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body"><div class="qp-wrap">{preview_block("qprev", prev_eps)}</div></div>
      </div>
    </div>
    """
    build_folder_opts = "".join(f"<option>{f}</option>" for f in V2_FOLDERS)
    build_ds_drawer = f"""
    <div class="modal-mask" id="buildDsDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="modal-box" style="width:460px;">
        <div class="drawer-head"><h3>用结果建数据集</h3><button class="drawer-close" onclick="document.getElementById('buildDsDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="muted" style="font-size:12px;margin-bottom:14px;">将当前查询结果（{n_disp} 个 episode）打包为一个新数据集。</div>
          <div class="fg"><label><span class="req">*</span>数据集名称</label><input placeholder="如 clean_whiteboard_v5"></div>
          <div class="fg"><label><span class="req">*</span>标识</label><input placeholder="英文唯一标识"><div class="hint">全局唯一</div></div>
          <div class="fg"><label>选择目录</label><select>{build_folder_opts}</select></div>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="document.getElementById('buildDsDrawer').classList.remove('active')">取消</button>
          <button class="btn-primary btn" onclick="document.getElementById('buildDsDrawer').classList.remove('active');toast('Demo: 数据集创建成功')">确认创建</button>
        </div>
      </div>
    </div>
    """
    content = top_card + result_card + ai_panel + recipe_panel + prev_drawer + build_ds_drawer
    script = """<script>__RECIPE_DATA__
    function toggleAdv(){
      var p=document.getElementById('advPanel'), b=document.getElementById('advBtn');
      var open=p.style.display!=='none';
      p.style.display=open?'none':'flex';
      b.innerHTML=open?'高级筛选 +':'收起筛选 −';
    }
    function pushMain(on){ var m=document.querySelector('.q-main'); if(m) m.classList.toggle('ai-pushed', on); }
    function aiOpen(){ recipeClose(); document.getElementById('aiDrawer').classList.add('active'); pushMain(true); var i=document.getElementById('aiInput'); if(i) setTimeout(function(){i.focus();},220); }
    function aiClose(){ document.getElementById('aiDrawer').classList.remove('active'); pushMain(false); }
    function aiKey(e){ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); aiSend(); } }
    function aiEsc(s){ return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function msUpdate(cb){
      var wrap=cb.closest('.ms-wrap');
      var checked=wrap.querySelectorAll('input:checked'); var n=checked.length;
      var trig=wrap.querySelector('.ms-trigger'); var base=trig.getAttribute('data-base')||'';
      var lab=wrap.querySelector('.ms-label');
      trig.classList.toggle('has-value', n>0);
      if(!n){ lab.textContent=base; return; }
      var names=[]; checked.forEach(function(c){ names.push(c.parentNode.textContent.trim()); });
      lab.textContent=names.join(', ');
      // 回显放不下时折叠为个数
      if(lab.scrollWidth > lab.clientWidth + 1){ lab.textContent=base+' ('+n+')'; }
    }
    document.addEventListener('DOMContentLoaded', function(){
      document.querySelectorAll('.ms-wrap').forEach(function(w){ var c=w.querySelector('input:checked'); if(c) msUpdate(c); });
    });
    document.addEventListener('click', function(e){
      document.querySelectorAll('.ms-wrap.open').forEach(function(w){ if(!w.contains(e.target)) w.classList.remove('open'); });
    });
    function aiGenSQL(nl){
      var conds=["robot_type = 'moz1'"];
      var te=document.querySelector('input[name=task]'); var tv=te?te.value.trim():'';
      if(tv){ var ts=tv.split(',').map(function(s){return s.trim();}).filter(Boolean); conds.push("task IN ("+ts.map(function(x){return "'"+x+"'";}).join(", ")+")"); }
      else if(/擦白板|whiteboard/.test(nl)) conds.push("task = 'clean_the_whiteboard'");
      if(/moz/i.test(nl)) conds.push("capture_device = 'Moz'");
      if(/udas/i.test(nl)) conds.push("capture_device = 'uDAS'");
      if(/lance/i.test(nl)) conds.push("operator = 'Lance Li'");
      if(/不合格|fail/i.test(nl)) conds.push("qa_status = 'FAIL'");
      else if(/操作失误|warn/i.test(nl)) conds.push("qa_status = 'WARN'");
      else if(/合格|通过|pass/i.test(nl)) conds.push("qa_status = 'PASS'");
      if(/近一周|近7天|近 7 天/.test(nl)) conds.push("collected_at >= DATE_SUB(CURRENT_DATE, 7)");
      var m=nl.match(/帧数(大于|>|超过)\\s*(\\d+)/); if(m) conds.push("frames > "+m[2]);
      return "SELECT episode_index, recording_id, task, collection_id, capture_device,\\n       operator, frames, duration_s, collected_at, qa_status\\nFROM   lake.recordings\\nWHERE  "+conds.join("\\n  AND ")+"\\nORDER BY collected_at DESC;";
    }
    function aiSend(preset){
      var inp=document.getElementById('aiInput');
      var text=(preset!==undefined?preset:inp.value).trim();
      if(!text) return;
      inp.value='';
      var msgs=document.getElementById('aiMsgs');
      msgs.insertAdjacentHTML('beforeend', '<div class="ai-msg ai-user"><div class="ai-bubble">'+aiEsc(text)+'</div></div>');
      var sql=aiGenSQL(text);
      window._aiNL=text;
      msgs.insertAdjacentHTML('beforeend',
        '<div class="ai-msg ai-bot"><div class="ai-bubble">已理解你的描述, 生成如下 SQL:</div>'+
        '<pre class="ai-sql">'+aiEsc(sql)+'</pre>'+
        '<button class="btn-primary btn ai-run" onclick="aiRun()">执行查询 &#8594;</button></div>');
      msgs.scrollTop=msgs.scrollHeight;
    }
    function aiRun(){ document.getElementById('nlField').value=window._aiNL||''; document.getElementById('qform').submit(); }
    function qGoPage(p){
      document.querySelectorAll('#qbody tr').forEach(function(tr){ tr.style.display = (+tr.getAttribute('data-pg')===p)?'':'none'; });
      document.querySelectorAll('.pg-btn').forEach(function(b){ b.classList.toggle('active', +b.getAttribute('data-p')===p); });
      var sc=document.querySelector('.q-table-scroll'); if(sc) sc.scrollTop=0;
    }

    /* ===== Episode 预览抽屉 (复用轨迹组件: 三视频 + 5 tab 轨迹) ===== */
    function qPreview(id){
      var m=(window._qprevMap||{})[id]; if(!m) return;
      var qaMap={pass:['qa-pass','PASS'],warn:['qa-warn','WARN'],fail:['qa-fail','FAIL']};
      var qa=qaMap[m.qa]||qaMap.pass;
      document.getElementById('qPrevTitle').innerHTML='Episode '+m.idx+' 预览 · #'+id+' <span class="qa '+qa[0]+'" style="margin-left:8px;">'+qa[1]+'</span>';
      document.getElementById('qPrevDrawer').classList.add('active');
      if(window.setEp_qprev) window.setEp_qprev(m.idx);
    }

    /* ===== 配方助手 (相对比例: 每类独立权重 ×倍数, 默认 ×1 保持原始构成) ===== */
    var RC={prompt:[], tag:[], baseN:0}; var RC_MAX=2;
    function rcInitGroup(src){ return src.map(function(c){ return {key:c.key,label:c.label,avail:c.count,base:c.count,weight:1}; }); }
    function rcProps(arr){ var tot=0; arr.forEach(function(c){tot+=c.base*c.weight;}); return arr.map(function(c){ return tot>0 ? (c.base*c.weight)/tot : 0; }); }
    function rcGroupTotal(arr,props){ var t=Infinity; arr.forEach(function(c,i){ if(props[i]>0.001) t=Math.min(t, c.avail/props[i]); }); return isFinite(t)?Math.floor(t):0; }
    function recipeOpen(){
      aiClose();
      RC.baseN=window._rcBaseN||0;
      RC.prompt=rcInitGroup(window._rcPrompt||[]);
      RC.tag=rcInitGroup(window._rcTag||[]);
      document.getElementById('rcBase').textContent=RC.baseN;
      rcUpdateCount();
      document.getElementById('recipeDrawer').classList.add('active'); pushMain(true);
    }
    function recipeClose(){ document.getElementById('recipeDrawer').classList.remove('active'); if(!document.getElementById('aiDrawer').classList.contains('active')) pushMain(false); }
    function rcRender(grp,cid,props){
      var arr=RC[grp]; var cnt=window._rcLastCount||0;
      var h=arr.map(function(c,i){
        var fill=Math.round(c.weight/RC_MAX*100), p=props[i];
        return '<div class="rc-row">'+
          '<div class="rc-label"><span>'+c.label+'</span><span class="rc-pct">&times;'+c.weight.toFixed(1)+'</span></div>'+
          '<div class="rc-track" data-grp="'+grp+'" data-i="'+i+'"><div class="rc-base-mark"></div><div class="rc-fill" style="width:'+fill+'%"><span class="rc-handle"></span></div></div>'+
          '<div class="rc-sub">占比 '+Math.round(p*100)+'% · 可用 '+c.avail+' · 采样 <b>'+Math.round(p*cnt)+'</b></div>'+
        '</div>';
      }).join('');
      document.getElementById(cid).innerHTML=h;
    }
    function rcUpdateCount(){
      var pp=rcProps(RC.prompt), tp=rcProps(RC.tag);
      var pt=rcGroupTotal(RC.prompt,pp), tt=rcGroupTotal(RC.tag,tp);
      var cnt=Math.min(pt,tt); if(!isFinite(cnt)) cnt=0;
      window._rcLastCount=cnt;
      document.getElementById('rcCount').textContent=cnt;
      document.getElementById('rcOf').textContent='/ '+RC.baseN+' 个';
      rcRender('prompt','rcPrompt',pp); rcRender('tag','rcTag',tp);
    }
    function rcSetWeight(grp,idx,w){ RC[grp][idx].weight=Math.max(0,Math.min(RC_MAX,w)); rcUpdateCount(); }
    document.addEventListener('mousedown', function(e){
      var track=e.target.closest('.rc-track'); if(!track) return;
      e.preventDefault();
      var grp=track.getAttribute('data-grp'), idx=+track.getAttribute('data-i');
      function move(ev){ var rect=track.getBoundingClientRect(); rcSetWeight(grp,idx,(ev.clientX-rect.left)/rect.width*RC_MAX); }
      move(e);
      function up(){ document.removeEventListener('mousemove',move); document.removeEventListener('mouseup',up); }
      document.addEventListener('mousemove',move); document.addEventListener('mouseup',up);
    });
    function recipeReset(){ RC.prompt.forEach(function(c){c.weight=1;}); RC.tag.forEach(function(c){c.weight=1;}); rcUpdateCount(); document.querySelectorAll('#qbody tr').forEach(function(tr){tr.style.display='';}); toast('已重置配方'); }
    function recipeApply(){
      var target=window._rcLastCount||0;
      var body=document.getElementById('qbody'); if(body){
        var trs=Array.prototype.slice.call(body.querySelectorAll('tr'));
        for(var i=trs.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)); var t=trs[i]; trs[i]=trs[j]; trs[j]=t; }
        trs.forEach(function(tr,i){ tr.style.display = i<target ? '' : 'none'; });
      }
      var hd=document.getElementById('qResMeta'); if(hd) hd.textContent='配方采样后 '+target+' 个 episode';
      recipeClose();
      toast('已按配方随机采样 '+target+' 个 episode');
    }
    </script>"""
    script = script.replace("__RECIPE_DATA__", recipe_data_js)
    return render_page("数据查询", content, active="query",
                       breadcrumb="数据湖 / <b>数据查询</b>", extra_script=script)



# ════════════════════════════════════════════════════════════════
#  数据集管理  (独立副本, 可单独迭代)
# ════════════════════════════════════════════════════════════════

DS_VERSIONS = {}   # ds_id -> [版本记录] (最新在前)
_PROC_SEQ = [0]

def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def ds_versions(d):
    """数据集版本历史: 未发布草稿(最新) + 当前版本 + 历史归档。"""
    if d["id"] not in DS_VERSIONS:
        vtxt = d["version"].lstrip("v")
        n = int(vtxt) if vtxt.isdigit() else 1
        recs = len(d["recordings"])
        notes = {1: "初版采集", 2: "增补采集 + 调整配方", 3: "扩充数据", 4: "修复缺帧"}
        owners = ["Lance Li", "Wei Zhang", "Min Chen"]
        vers = [
            # 未发布草稿 (最新)
            {"version": f"v{n+1}", "created": d["created"], "recordings": recs + 1,
             "status": "待发布", "note": "新增 dagger 数据 (草稿)", "creator": d["owner"]},
            # 当前版本
            {"version": d["version"], "created": d["created"], "recordings": recs,
             "status": "生效中", "note": notes.get(n, "迭代版本"), "creator": d["owner"]},
        ]
        for k in range(n - 1, 0, -1):  # 历史归档
            vers.append({"version": f"v{k}", "created": f"2026-05-{11+k:02d} 10:00",
                         "recordings": max(1, recs - (n - k)), "status": "已归档",
                         "note": notes.get(k, "迭代版本"), "creator": owners[k % len(owners)]})
        DS_VERSIONS[d["id"]] = vers
    return DS_VERSIONS[d["id"]]

@app.route("/datasets")
def datasets():
    sel = request.args.get("sel", "")
    # 默认选中第一个数据集 (在建树前确定, 保证树高亮与详情一致)
    if not sel:
        sel = DATASETS[0]["id"]
    # 业务语义目录 (用户可自建管理), 而非按 train/eval 分
    tree = ('<div class="tree-head">'
            '<span class="th-left"><span class="tp-toggle" onclick="toggleTP(this)" title="折叠/展开目录"><span class="sc-col">&laquo;</span><span class="sc-exp">&raquo;</span></span><span class="th-title">数据集目录</span></span>'
            '<span class="th-actions">'
            '<a href="#" onclick="openDrawerById(\'newFolderDrawer\');return false;" style="font-size:12px;">+ 目录</a>'
            '<a href="#" onclick="openDrawerById(\'newDsDrawer\');return false;" style="font-size:12px;">+ 数据集</a></span></div>')
    tree += '<div class="tree-search"><input placeholder="搜索数据集 / 目录..."></div><div class="tree-body">'
    for folder in V2_FOLDERS:
        dss = [get_ds(i) for i in V2_FOLDER_MAP.get(folder, []) if get_ds(i)]
        tree += (f'<div class="tree-grp" onclick="toggleTree(this)"><span class="caret">&#9656;</span>{folder} '
                 f'<span class="sub" style="color:rgba(0,0,0,0.35);font-weight:400;">({len(dss)})</span>'
                 f'<span class="folder-act" onclick="event.stopPropagation();toast(\'Demo: 管理目录「{folder}」(重命名 / 删除 / 移入数据集)\')">&#8943;</span></div>')
        tree += '<div class="tree-children">'
        if dss:
            for d in dss:
                cls = "active" if d["id"] == sel else ""
                tree += f'<a class="tree-leaf {cls}" href="/datasets?sel={d["id"]}">{d["name"]} <span class="sub">· {d["version"]}</span></a>'
        else:
            tree += '<div class="tree-leaf muted" style="cursor:default;">（空目录）</div>'
        tree += '</div>'
    tree += '</div>'

    if sel == "new":
        right = dataset_new_panel_v2()
    else:
        if not sel:
            sel = DATASETS[0]["id"]
        right = dataset_detail_panel_v2(get_ds(sel) or DATASETS[0], request.args.get("ver", ""))

    folder_opts = "".join(f"<option>{f}</option>" for f in V2_FOLDERS)
    new_folder_drawer = f"""
    <div class="modal-mask" id="newFolderDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="modal-box" style="width:440px;">
        <div class="drawer-head"><h3>新建目录</h3><button class="drawer-close" onclick="closeDrawerById('newFolderDrawer')">&times;</button></div>
        <div class="drawer-body">
          <div class="fg"><label><span class="req">*</span>目录名称</label><input placeholder="如 预训练-扫地"></div>
          <div class="fg"><label><span class="req">*</span>标识</label><input placeholder="英文唯一标识 如 pretrain_sweep"><div class="hint">全局唯一, 用于引用</div></div>
          <div class="fg"><label>上级目录</label><select><option>无 (一级目录)</option>{folder_opts}</select></div>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="closeDrawerById('newFolderDrawer')">取消</button>
          <button class="btn-primary btn" onclick="closeDrawerById('newFolderDrawer');toast('Demo: 已创建目录')">确认创建</button>
        </div>
      </div>
    </div>
    """
    new_ds_drawer = f"""
    <div class="modal-mask" id="newDsDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="modal-box" style="width:780px;max-width:94vw;">
        <div class="drawer-head"><h3>新建数据集</h3><button class="drawer-close" onclick="closeDrawerById('newDsDrawer')">&times;</button></div>
        <div class="drawer-body">
          <div class="ds-hint">&#128161; 可以前往 <a href="/query">数据查询</a> 页面使用 <b>AI 助手</b> 和 <b>配方工具</b>, 筛选想要的数据, 一键生成数据集。</div>
          <div class="section-label">数据集信息</div>
          <div class="fg-row">
            <div class="fg"><label><span class="req">*</span>数据集名称</label><input placeholder="如 clean_whiteboard_v5"></div>
            <div class="fg"><label><span class="req">*</span>标识</label><input placeholder="英文唯一标识"></div>
          </div>
          <div class="fg"><label>目录</label><select>{folder_opts}</select></div>
          <div class="section-label">筛选条件 <span class="muted" style="font-weight:400;font-size:12px;">与数据查询一致</span></div>
          {build_query_filters()}
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="closeDrawerById('newDsDrawer')">取消</button>
          <button class="btn-primary btn" onclick="closeDrawerById('newDsDrawer');toast('Demo: 已按筛选条件生成数据集')">确认创建</button>
        </div>
      </div>
    </div>
    """
    content = (f'<div class="split"><div class="tree-panel">{tree}</div><div class="detail-panel">{right}</div></div>'
               + new_folder_drawer + new_ds_drawer)
    # 处理数据后跳到「版本」Tab 并提示
    landed = request.args.get("tab", "")
    land_js = ("""
      var vt=Array.prototype.slice.call(document.querySelectorAll('.tab')).filter(function(x){return x.textContent.trim()==='版本';})[0];
      if(vt) vt.click();
      toast('处理完成: 已生成新版本');
    """ if landed == "version" else "")
    script = """<script>
    window._charts = {
      info: function(){
        var c=document.getElementById('dsHist');
        if(c && window.Chart && !c._drawn){ c._drawn=true;
          new Chart(c,{type:'bar',
            data:{labels:['<900','900-1100','1100-1300','1300-1500','>1500'],datasets:[{label:'episode 数',data:[3,12,18,11,4],backgroundColor:'#1F80A0'}]},
            options:{plugins:{legend:{display:false}},scales:{y:{ticks:{font:{size:10}}},x:{ticks:{font:{size:10}}}}}});
        }
      },
      compose: function(){
        var pies=window.__tagPies; if(!pies||!window.Chart) return;
        var pal=['#1F80A0','#36cfc9','#faad14','#52c41a','#722ed1','#ff7a45','#13c2c2','#eb2f96','#a0d911','#2f54eb','#ff85c0','#ffc53d'];
        var tot=function(a){return a.reduce(function(s,x){return s+x;},0)||1;};
        var pieLabels={id:'pieLabels', afterDatasetsDraw:function(chart){
          var ctx=chart.ctx, meta=chart.getDatasetMeta(0), ds=chart.data.datasets[0];
          var sum=ds.data.reduce(function(s,x){return s+x;},0)||1;
          ctx.save(); ctx.font='11px sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
          meta.data.forEach(function(arc,i){
            if(ds.data[i]/sum < 0.06) return;        // 太小的扇区不标, 避免重叠
            var ang=(arc.startAngle+arc.endAngle)/2, r=(arc.innerRadius+arc.outerRadius)/2;
            var x=arc.x+Math.cos(ang)*r, y=arc.y+Math.sin(ang)*r;
            ctx.lineWidth=2.5; ctx.strokeStyle='rgba(0,0,0,0.40)'; ctx.strokeText(chart.data.labels[i],x,y);
            ctx.fillStyle='#fff'; ctx.fillText(chart.data.labels[i],x,y);
          });
          ctx.restore();
        }};
        pies.forEach(function(p,i){
          var c=document.getElementById('tagPie'+i); if(!c||c._drawn) return; c._drawn=true;
          var sum=tot(p.vals);
          new Chart(c,{type:'pie',
            data:{labels:p.labels,datasets:[{data:p.vals,backgroundColor:(p.colors||p.labels.map(function(_,j){return pal[j%pal.length];})),borderWidth:1,borderColor:'#fff'}]},
            options:{maintainAspectRatio:false,plugins:{legend:{display:false},
              tooltip:{callbacks:{label:function(x){return x.label+': '+Math.round(x.parsed/sum*100)+'%';}}}}},
            plugins:[pieLabels]});
        });
      }
    };
    document.addEventListener('DOMContentLoaded', function(){""" + land_js + """});
    </script>"""
    return render_page("数据集管理", content, active="datasets",
                       breadcrumb='数据集 / <b>数据集管理</b>', extra_script=script)


def dataset_detail_panel_v2(d, viewed_ver=""):
    eps = dataset_episodes(d)
    preview = (f'<div class="tab-pane active" id="pane-preview">'
               f'<div class="muted" style="margin-bottom:12px;">数据集共 {d["episodes"]} 个 episode，每个 episode ← 一条原始 recording，可在左侧逐条预览</div>'
               f'{preview_block("dsv2", eps)}</div>')
    info = f"""
    <div class="tab-pane" id="pane-info">
      <div class="desc-grid">
        <div class="dk">数据集名称</div><div class="dv">{d['name']}</div>
        <div class="dk">版本</div><div class="dv">{d['version']}</div>
        <div class="dk">本体</div><div class="dv">{d['robot']}</div>
        <div class="dk">规模</div><div class="dv">{d['episodes']} episodes · {d['frames']:,} frames · {round(d['frames']/30/60,1)} min</div>
        <div class="dk">质量</div><div class="dv">{qa_html(d['quality'])}</div>
        <div class="dk">状态</div><div class="dv">{d['status']}</div>
        <div class="dk">Owner</div><div class="dv">{d['owner']}</div>
        <div class="dk">创建时间</div><div class="dv">{d['created']}</div>
        <div class="dk">TOS</div><div class="dv" style="font-family:monospace;font-size:12px;">{d['tos']}</div>
      </div>
    </div>
    """
    prompt_rows = comp_rows_html(dataset_prompt_composition(d), d["frames"])
    # 按一级维度的标签帧数 (三个饼图 + 表格图例)
    _byp = {}
    for r in _dataset_recs(d):
        for tid in rec_tags(r):
            _byp[tid] = _byp.get(tid, 0) + r["frames"]
    _pal = ["#1F80A0", "#36cfc9", "#faad14", "#52c41a", "#722ed1", "#ff7a45",
            "#13c2c2", "#eb2f96", "#a0d911", "#2f54eb", "#ff85c0", "#ffc53d"]
    pies = []
    for grp in TAG_GROUP_ORDER:
        items = sorted([(TAG_LABEL[t], fr) for t, fr in _byp.items() if _TAG_GROUP.get(t) == grp], key=lambda x: -x[1])
        if items:
            total = sum(v for _, v in items) or 1
            labels = [i[0] for i in items]
            vals = [i[1] for i in items]
            colors = [_pal[j % len(_pal)] for j in range(len(items))]
            pcts = [round(v / total * 100) for v in vals]
            pies.append({"group": grp, "labels": labels, "vals": vals, "colors": colors, "pcts": pcts})
    pies_json = json.dumps([{"labels": p["labels"], "vals": p["vals"], "colors": p["colors"]} for p in pies])

    def pie_legend(p):
        rows = "".join(
            f'<tr><td><i style="background:{c}"></i>{lab}</td><td class="pct">{pct}%</td></tr>'
            for lab, c, pct in zip(p["labels"], p["colors"], p["pcts"]))
        return f'<table class="pie-legend"><tbody>{rows}</tbody></table>'

    pie_cells = "".join(
        f'<div class="pie-cell"><div class="pie-title">{p["group"]}</div>'
        f'<div class="pie-box"><canvas id="tagPie{i}"></canvas></div>{pie_legend(p)}</div>'
        for i, p in enumerate(pies))
    compose = f"""
    <div class="tab-pane" id="pane-compose">
      <div class="muted" style="margin-bottom:16px;">数据集共 {d['episodes']} episode · {d['frames']:,} frames · {round(d['frames']/30/60,1)} min</div>
      <h4 class="va-h">Prompt 构成 <span class="muted" style="font-weight:400;font-size:12px;">按任务 prompt 的帧数占比</span></h4>
      {prompt_rows}
      <h4 class="va-h">标签构成 <span class="muted" style="font-weight:400;font-size:12px;">按一级维度分三个饼图 · 各维度内标签的帧数占比</span></h4>
      <div class="pie-row">{pie_cells}</div>
      <script>window.__tagPies={pies_json};</script>
    </div>
    """
    checks = doctor_checks(d["quality"])
    n_ep = d["episodes"] or 1
    def _rule_pct(st, desc):
        if st == "pass":
            return 100
        m = re.search(r"(\d+)\s*个 episode", desc)
        if m:
            return max(0, round((n_ep - int(m.group(1))) / n_ep * 100))
        return 82 if st == "fail" else 96
    crows = ""
    for n, st, dd in checks:
        pct = _rule_pct(st, dd)
        barcls = "ok" if pct >= 99 else ("warn" if pct >= 85 else "bad")
        crows += (f'<div class="check-row"><span class="badge {st}">{st.upper()}</span>'
                  f'<span class="cname">{n}</span><span class="cdesc">{dd}</span>'
                  f'<span class="check-pct"><span class="cp-bar {barcls}"><i style="width:{pct}%"></i></span>'
                  f'<span class="cp-num">{pct}%</span></span></div>')
    banner_txt = {"pass": "检查通过, 可进训练队列", "warn": "部分规则校验不通过", "fail": "必须修复才能用"}[d["quality"]]
    quality = f"""
    <div class="tab-pane" id="pane-quality">
      <div class="doctor-banner {d['quality']}">{d['quality'].upper()} — {banner_txt}</div>
      {crows}
    </div>
    """
    # 上游来源表: 按采集批次分组
    up_groups = {}
    for rid in d["recordings"]:
        r = get_rec(rid)
        if not r:
            continue
        up_groups.setdefault((r["collection"], r["type"]), []).append(rid)
    up_rows = ""
    for (coll, typ), rids in up_groups.items():
        links = " · ".join(f'<a href="/lake?mode=flat&sel={x}">#{x}</a>' for x in rids)
        up_rows += (f'<tr><td>采集任务 task {coll}</td><td><span class="tag tag-gray">{typ}</span></td>'
                    f'<td>{len(rids)}</td><td>{links}</td></tr>')
    if not up_rows:
        up_rows = '<tr><td colspan="4" class="muted">—</td></tr>'

    # 下游引用表: 记录引用的版本
    _pubvers = [v["version"] for v in ds_versions(d) if v["status"] != "待发布"] or [d["version"]]
    down_rows = ""
    for i, u in enumerate(d["used_by"]):
        kind = "评测" if u.startswith("eval") else "训练"
        ver = _pubvers[i % len(_pubvers)]
        down_rows += (f'<tr><td>{u}</td><td><span class="tag tag-gray">{kind}</span></td>'
                      f'<td><b>{ver}</b></td></tr>')
    if not down_rows:
        down_rows = '<tr><td colspan="3" class="muted">暂未被训练/评测任务引用</td></tr>'

    lineage = f"""
    <div class="tab-pane" id="pane-lineage">
      <h4 class="va-h">↑ 上游来源 <span class="muted" style="font-weight:400;font-size:12px;">由以下采集/dagger 任务生成</span></h4>
      <table class="ant-table">
        <thead><tr><th>来源</th><th>类型</th><th>recording 数</th><th>引用 recording</th></tr></thead>
        <tbody>{up_rows}</tbody>
      </table>
      <h4 class="va-h">↓ 下游引用 <span class="muted" style="font-weight:400;font-size:12px;">被以下训练/评测任务引用</span></h4>
      <table class="ant-table">
        <thead><tr><th>任务</th><th>类型</th><th>引用版本</th></tr></thead>
        <tbody>{down_rows}</tbody>
      </table>
    </div>
    """
    vrows = ""
    for v in ds_versions(d):
        if v["status"] == "待发布":
            name_cell = f'<span class="muted">{v["version"]}</span>'
            op = f'<a href="/datasets/{d["id"]}/version/{v["version"]}/publish">发布</a>'
        elif v["status"] == "已归档":
            name_cell = f'<span class="muted">{v["version"]}</span>'
            op = f'<a href="/datasets/{d["id"]}/version/{v["version"]}/rollback">回退</a>'
        else:  # 生效中
            name_cell = (f'<b>{v["version"]}</b> <span class="tag tag-blue">生效中</span>'
                         if v["version"] == d["version"] else f'<span class="muted">{v["version"]}</span>')
            op = '<span class="muted">—</span>'
        vrows += (f'<tr><td>{name_cell}</td><td class="muted">{v.get("note","")}</td>'
                  f'<td>{v["recordings"]}</td><td>{v.get("creator","—")}</td>'
                  f'<td class="muted">{v["created"]}</td><td>{v["status"]}</td>'
                  f'<td class="actions-cell">{op}</td></tr>')
    version = f"""
    <div class="tab-pane" id="pane-version">
      <table class="ant-table"><thead><tr><th>版本</th><th>说明</th><th>recording 数</th><th>创建人</th><th>创建时间</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>{vrows}</tbody></table>
      <div class="muted" style="margin-top:12px;">改配方 / 处理数据 = 出新版本, 被训练引用的版本不可变, 保证实验可复现。</div>
    </div>
    """
    publish_btn = ('<button class="btn-primary btn" onclick="toast(\'Demo: 已开始发布并上传 TOS...\')">发布 / 上传 TOS</button>'
                   if d["status"] != "生效中" else '<button class="btn" onclick="toast(\'生效中, 可被训练任务引用\')">查看 TOS</button>')

    # 处理数据抽屉: 选任务 + 参数(结构化/代码) → 执行生成新版本
    pl_opts = "".join(f'<option value="task|{p["name"]}">{p["name"]}</option>' for p in PIPELINES)
    cur_ver = ds_versions(d)[0]["version"]
    # 每个任务已配置好的参数 key (来自其算子定义, 不可改, 只能填 value)
    task_params = {}
    for p in PIPELINES:
        keys = []
        for sid in p["stages"]:
            op = next((o for o in OPERATORS if o["id"] == sid), None)
            if not op:
                continue
            for item in op["params"].split(" / "):
                k = item.strip().split(" ")[0]
                if k and k not in keys:
                    keys.append(k)
        task_params[p["name"]] = keys
    task_params_js = json.dumps(task_params, ensure_ascii=False)
    drawer = f"""
    <div class="modal-mask" id="procDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="modal-box" style="width:600px;max-width:94vw;">
        <div class="drawer-head"><h3>处理数据 — {d['name']} ({cur_ver})</h3>
          <button class="drawer-close" onclick="document.getElementById('procDrawer').classList.remove('active')">&times;</button></div>
        <form method="post" action="/datasets/{d['id']}/process" style="display:flex;flex-direction:column;min-height:0;flex:1;">
          <div class="drawer-body">
            <div class="section-label">任务</div>
            <div class="fg">
              <select name="op" onchange="procRenderParams()">{pl_opts}</select>
              <div class="hint">在当前数据集 {cur_ver} 上执行该任务, 产出一个新版本</div>
            </div>
            <div class="section-label">处理说明</div>
            <div class="fg"><input name="note" placeholder="本次处理做了什么 (可选)"></div>
            <div class="section-label">请求参数</div>
            <div class="param-mode">
              <button type="button" class="pm-btn active" data-m="struct" onclick="procMode('struct')">结构化</button>
              <button type="button" class="pm-btn" data-m="code" onclick="procMode('code')">代码</button>
            </div>
            <div class="proc-params-area">
              <div id="procStruct">
                <div class="hint" style="margin-bottom:8px;">参数名由所选任务的算子配置决定, 此处仅填写取值。</div>
                <div id="procParamBox"></div>
              </div>
              <div id="procCode" style="display:none;">
                <textarea name="params_code" class="code-editor" style="width:100%;box-sizing:border-box;" rows="8" placeholder="# 命令行参数 / JSON&#10;--train-ratio 0.95 --seed 42"></textarea>
              </div>
            </div>
          </div>
          <div class="drawer-foot">
            <button type="button" class="btn" onclick="document.getElementById('procDrawer').classList.remove('active')">取消</button>
            <button type="submit" class="btn-primary btn">确认执行</button>
          </div>
        </form>
      </div>
      <script>
      function procMode(m){{
        document.getElementById('procStruct').style.display = m==='struct'?'':'none';
        document.getElementById('procCode').style.display = m==='code'?'':'none';
        document.querySelectorAll('.param-mode .pm-btn').forEach(function(b){{ b.classList.toggle('active', b.getAttribute('data-m')===m); }});
      }}
      window._taskParams = {task_params_js};
      function procRenderParams(){{
        var sel=document.querySelector('#procDrawer select[name=op]');
        var name=(sel.value.split('|')[1]||sel.value);
        var keys=(window._taskParams||{{}})[name]||[];
        var box=document.getElementById('procParamBox');
        if(!keys.length){{ box.innerHTML='<div class="muted" style="font-size:12px;padding:4px 0;">该任务无可配置参数</div>'; return; }}
        box.innerHTML='<table class="param-table"><tbody>'+keys.map(function(k){{
          return '<tr><td class="pk" style="font-family:monospace;font-size:12px;color:rgba(0,0,0,0.7);">'+k+'</td>'+
            '<td><input class="fp-val" placeholder="填写值"></td></tr>';
        }}).join('')+'</tbody></table>';
      }}
      procRenderParams();
      </script>
    </div>
    """
    # 版本号下拉 (可切换查看)
    _vlist = ds_versions(d)
    viewed = viewed_ver if any(v["version"] == viewed_ver for v in _vlist) else d["version"]
    _vopts = ""
    for v in _vlist:
        if v["version"] == d["version"] and v["status"] == "生效中":
            lab = f'{v["version"]} · 生效中'
        elif v["status"] == "待发布":
            lab = f'{v["version"]} · 待发布'
        elif v["status"] == "已归档":
            lab = f'{v["version"]} · 已归档'
        else:
            lab = v["version"]
        s = " selected" if v["version"] == viewed else ""
        _vopts += f'<option value="{v["version"]}"{s}>{lab}</option>'
    ver_select = (f'<select class="ver-select" onchange="if(this.value)location.href=\'/datasets?sel={d["id"]}&ver=\'+this.value">'
                  f'{_vopts}</select>')
    head = f"""
    <div class="detail-head">
      <div><div class="dh-title">{d['name']} {ver_select} {qa_html(d['quality'])}</div>
      <div class="dh-meta"><span>{d['episodes']} ep · {d['frames']:,} f</span><span>{d['status']}</span></div></div>
      <div><button class="btn" onclick="document.getElementById('procDrawer').classList.add('active')">&#9881; 处理数据</button> {publish_btn}</div>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="switchTab(this,'preview')">数据预览</div>
      <div class="tab" onclick="switchTab(this,'compose')">构成分析</div>
      <div class="tab" onclick="switchTab(this,'quality')">质量报告</div>
      <div class="tab" onclick="switchTab(this,'lineage')">血缘</div>
      <div class="tab" onclick="switchTab(this,'version')">版本</div>
      <div class="tab" onclick="switchTab(this,'info')">基本信息</div>
    </div>
    <div class="pane-wrap">{preview}{compose}{quality}{lineage}{version}{info}</div>
    {drawer}
    """
    return head


@app.route("/datasets/<did>/version/<ver>/publish")
def datasets_publish(did, ver):
    d = get_ds(did)
    if not d:
        return redirect("/datasets")
    vers = ds_versions(d)
    # 旧的当前发布版 → 归档
    for v in vers:
        if v["version"] == d["version"] and v["status"] == "生效中":
            v["status"] = "已归档"
    # 目标草稿 → 生效中, 成为当前
    for v in vers:
        if v["version"] == ver and v["status"] == "待发布":
            v["status"], v["created"] = "生效中", _now()
            d["version"], d["status"] = ver, "生效中"
    return redirect(f"/datasets?sel={did}&tab=version")


@app.route("/datasets/<did>/version/<ver>/rollback")
def datasets_rollback(did, ver):
    d = get_ds(did)
    if not d:
        return redirect("/datasets")
    vers = ds_versions(d)
    src = next((v for v in vers if v["version"] == ver), None)
    if src:
        nums = [int(v["version"].lstrip("v")) for v in vers if v["version"].lstrip("v").isdigit()]
        newn = (max(nums) + 1) if nums else 1
        vers.insert(0, {"version": f"v{newn}", "created": _now(), "recordings": src["recordings"],
                        "status": "待发布", "note": f"回退自 {ver}", "creator": "joanna.qiao"})
    return redirect(f"/datasets?sel={did}&tab=version")


@app.route("/datasets/<did>/process", methods=["POST"])
def datasets_process(did):
    d = get_ds(did)
    if not d:
        return redirect("/datasets")
    raw = request.form.get("op", "op|处理算子")
    kind, op_name = (raw.split("|", 1) + [""])[:2] if "|" in raw else ("op", raw)
    note = request.form.get("note", "").strip() or f"经「{op_name}」处理生成"
    now = _now()
    # 1) 生成新版本
    vers = ds_versions(d)
    prev = vers[0]["version"]
    try:
        new_ver = "v" + str(int(prev.lstrip("v")) + 1)
    except ValueError:
        new_ver = prev + ".1"
    vers.insert(0, {"version": new_ver, "created": now, "recordings": len(d["recordings"]),
                    "status": "待发布", "note": note, "creator": "joanna.qiao"})
    d["version"], d["created"], d["status"] = new_ver, now, "待发布"
    # 2) 写一条执行记录
    _PROC_SEQ[0] += 1
    RUNS.insert(0, {
        "id": f"proc_{_PROC_SEQ[0]:04d}", "pipeline": "", "name": op_name,
        "target": f"{d['name']} {new_ver}", "status": "done", "progress": 100,
        "stage": "完成", "at": now, "dur": "1m 20s",
    })
    return redirect(f"/datasets?sel={did}&tab=version")


def dataset_new_panel_v2():
    steps = ["筛选", "配方", "切分", "质检门禁", "生成"]
    step_html = ""
    for i, s in enumerate(steps):
        cls = "active" if i == 1 else ("done" if i == 0 else "")
        step_html += f'<div class="step {cls}"><span class="sn">{i+1}</span><div class="st">{s}</div></div>'
    rec_rows = ""
    for r in RECORDINGS[:6]:
        rec_rows += f"""<tr><td><input type="checkbox" checked></td><td>#{r['id']}</td><td>{task_name(r['task'])}</td>
        <td>{r['type']}</td><td>{r['frames']:,}</td><td>{qa_html(r['qa'])}</td></tr>"""
    return f"""
    <div class="detail-head"><div class="dh-title">新建数据集 <span class="tag tag-blue">向导</span></div></div>
    <div style="padding:24px;flex:1;min-height:0;overflow-y:auto;">
      <div class="steps">{step_html}</div>
      <div class="card" style="margin-bottom:16px;">
        <h4>① 筛选 — 从数据湖挑 recording <span class="muted">(三层: 硬指标滑块 / 排行榜+flag / 诊断标签 · 诊断不删)</span></h4>
        <div class="filter-bar">
          <select class="has-value"><option>task: 擦白板</option></select>
          <select class="has-value"><option>类型: 采集</option></select>
          <select class="has-value"><option>质检: PASS</option></select>
          <span class="muted">动作量排行榜 / smoothness 诊断标签可在此 flag 异常</span>
        </div>
        <table class="ant-table"><thead><tr><th></th><th>ID</th><th>Task</th><th>类型</th><th>帧数</th><th>质检</th></tr></thead><tbody>{rec_rows}</tbody></table>
      </div>
      <div class="card" style="margin-bottom:16px;">
        <h4>② 配方 — 采样权重 + 分组 <span class="muted">(右侧实时显示 权重 vs 帧数 vs 实际采样占比 = 采样验证 ⓥ)</span></h4>
        <div class="recipe-row"><div class="rname">擦白板-采集</div><div class="rbar"><div class="fill" style="width:70%">70%</div></div><div class="muted">权重 0.7</div></div>
        <div class="recipe-row"><div class="rname">擦白板-dagger</div><div class="rbar"><div class="fill" style="width:30%">30%</div></div><div class="muted">权重 0.3</div></div>
      </div>
      <div class="card" style="margin-bottom:16px;">
        <h4>③ 切分 — train / val / eval</h4>
        <div class="filter-bar"><select class="has-value"><option>类型: train</option></select>
        <input value="train_ratio = 0.95" style="width:160px;"><input value="seed = 42" style="width:120px;">
        <span class="qa qa-warn">eval 泄漏检查: 通过, 未碰评测集 recording</span></div>
      </div>
      <div class="card" style="margin-bottom:16px;">
        <h4>④ 质检门禁 — DOCTOR <span class="muted">(PASS 才能进训练队列 = 质检 ⓠ)</span></h4>
        <div class="doctor-banner pass">DOCTOR 体检: PASS — 体检通过, 可生成</div>
      </div>
      <button class="btn-primary btn" onclick="toast('Demo: 已提交生成任务, 见执行记录')">⑤ 生成快照</button>
    </div>
    """


@app.route("/operators")
def operators():
    cat_order = ["导出", "切分", "配方", "统计", "质检"]
    cat_color = {"导出": "tag-blue", "切分": "tag-purple", "配方": "tag-orange", "统计": "tag-gray", "质检": "tag-blue"}

    rows = ""
    for cat in cat_order:
        for op in [o for o in OPERATORS if o["cat"] == cat]:
            rows += f"""<tr>
              <td><a href="#" onclick="openOpDetail('{op['id']}');return false;">{op['name']}</a></td>
              <td><span class="op-script">{op['ident']}</span></td>
              <td class="muted" style="max-width:460px;"><span class="desc-clamp">{op['desc']}</span></td>
              <td>{op['creator']}</td>
              <td class="actions-cell"><a href="/pipelines?op={op['id']}">关联任务</a> · <a href="#" onclick="openOpForm('{op['id']}');return false;">编辑</a></td>
            </tr>"""

    ops_js = json.dumps({o["id"]: {"name": o["name"], "ident": o["ident"], "script": o["script"],
                                   "cat": o["cat"], "creator": o["creator"], "desc": o["desc"],
                                   "params": o["params"], "returns": o["returns"]} for o in OPERATORS})

    creator_checks = "".join(
        f'<label><input type="checkbox" value="{c}" onchange="msUpdate(this)">{c}</label>'
        for c in sorted(set(o["creator"] for o in OPERATORS)))
    content = f"""
    <div class="filter-bar">
      <input placeholder="搜索算子名称 / 标识...">
      <div class="ms-wrap">
        <div class="ms-trigger" onclick="this.closest('.ms-wrap').classList.toggle('open')"><span class="ms-label">创建人</span></div>
        <div class="ms-panel">{creator_checks}</div>
      </div>
      <button class="btn-primary btn" onclick="openOpForm('')" style="margin-left:auto;">+ 新建算子</button>
    </div>
    <div class="muted" style="margin-bottom:12px;">每个算子 = 一个「原子处理能力」的封装, 可被任务编排到工作流。</div>
    <table class="ant-table row2">
      <thead><tr><th>名称</th><th>标识</th><th>描述</th><th>创建人</th><th>操作</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <!-- 新建 / 编辑 算子 抽屉 -->
    <div class="drawer-mask" id="opFormDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer op-drawer">
        <div class="drawer-head"><h3 id="opFormTitle">新建算子</h3><button class="drawer-close" onclick="document.getElementById('opFormDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="section-label">基本信息</div>
          <div class="fg"><label><span class="req">*</span>名称</label><input id="of_name" placeholder="如: 通用导出 Export"></div>
          <div class="fg"><label><span class="req">*</span>标识</label><input id="of_ident" placeholder="英文唯一标识, 如 export_dataset"><div class="hint">编排/调用时引用, 全局唯一</div></div>
          <div class="fg"><label>描述</label><textarea id="of_desc" placeholder="算子做什么 / 核心逻辑"></textarea></div>
          <div class="fg"><label>是否启用</label><select id="of_enabled"><option>启用</option><option>停用</option></select></div>

          <div class="section-label">执行配置</div>
          <div class="fg"><label>运行镜像</label><select id="of_image"><option>frontdesk-py3.10:latest</option><option>lerobot-base:v2.1</option><option>自定义...</option></select></div>
          <div class="fg"><label><span class="req">*</span>入口脚本 / 命令</label><textarea id="of_script" class="code-editor" rows="4" placeholder="# 入口脚本 / 命令&#10;python export_dataset.py --task-ids 3635 --include-unchecked"></textarea></div>

          <div class="section-label">接口定义</div>
          <div class="fg"><label>请求参数</label><textarea id="of_params" class="code-editor" rows="4" placeholder="# 每行一个&#10;--task-ids        采集任务 id (必填)&#10;--include-unchecked  含未质检数据"></textarea></div>
          <div class="fg"><label>返回结果</label><textarea id="of_returns" class="code-editor" rows="3" placeholder="# 算子产出&#10;LeRobot 数据集目录 / 报告 JSON / CSV"></textarea></div>
        </div>
        <div class="drawer-foot">
          <label id="of_syncTaskWrap" class="foot-check"><input type="checkbox" id="of_syncTask" checked> 同步创建任务</label>
          <button class="btn" onclick="document.getElementById('opFormDrawer').classList.remove('active')">取消</button>
          <button class="btn btn-secondary" onclick="document.getElementById('opFormDrawer').classList.remove('active');toast('Demo: 已保存')">保存</button>
          <button class="btn-primary btn" id="of_saveNewVer" onclick="document.getElementById('opFormDrawer').classList.remove('active');toast('Demo: 已保存为新版本')">保存为新版本</button>
        </div>
      </div>
    </div>

    <!-- 算子详情 抽屉 -->
    <div class="drawer-mask" id="opDetailDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer op-drawer">
        <div class="drawer-head"><h3 id="opDetailTitle">算子详情</h3><button class="drawer-close" onclick="document.getElementById('opDetailDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body" id="opDetailBody"></div>
        <div class="drawer-foot">
          <button class="btn" onclick="toast('Demo: 运行算子')">运行</button>
          <button class="btn-primary btn" id="opDetailEdit">编辑</button>
        </div>
      </div>
    </div>
    <script>
    window.OPS = {ops_js};
    function msUpdate(cb){{
      var wrap=cb.closest('.ms-wrap'); var n=wrap.querySelectorAll('input:checked').length;
      wrap.querySelector('.ms-label').textContent = n ? ('创建人 ('+n+')') : '创建人';
    }}
    document.addEventListener('click', function(e){{
      document.querySelectorAll('.ms-wrap.open').forEach(function(w){{ if(!w.contains(e.target)) w.classList.remove('open'); }});
    }});
    function openOpForm(id){{
      var o = id ? window.OPS[id] : null;
      document.getElementById('opFormTitle').textContent = o ? '编辑算子' : '新建算子';
      var set=function(k,v){{ document.getElementById(k).value = v||''; }};
      set('of_name', o&&o.name); set('of_ident', o&&o.ident); set('of_desc', o&&o.desc);
      // 脚本/参数/返回结果 格式化为多行
      document.getElementById('of_script').value = o ? ('python ' + o.script) : '';
      document.getElementById('of_params').value = o ? o.params.split(' / ').join('\\n') : '';
      document.getElementById('of_returns').value = o ? o.returns.split(/ \\+ | \\/ /).join('\\n') : '';
      // 「保存为新版本」仅编辑时显示; 「同步创建任务」仅新建时显示, 默认勾选
      document.getElementById('of_saveNewVer').style.display = o ? '' : 'none';
      document.getElementById('of_syncTaskWrap').style.display = o ? 'none' : '';
      document.getElementById('of_syncTask').checked = true;
      document.getElementById('opDetailDrawer').classList.remove('active');
      document.getElementById('opFormDrawer').classList.add('active');
    }}
    function openOpDetail(id){{
      var o=window.OPS[id]; if(!o) return;
      document.getElementById('opDetailTitle').textContent = o.name;
      var rows=[['标识',o.ident],['脚本',o.script],['创建人',o.creator],
                ['描述',o.desc],['请求参数',o.params],['返回结果',o.returns]];
      document.getElementById('opDetailBody').innerHTML =
        '<div class="desc-grid">'+rows.map(function(r){{ return '<div class="dk">'+r[0]+'</div><div class="dv">'+r[1]+'</div>'; }}).join('')+'</div>';
      document.getElementById('opDetailEdit').onclick=function(){{ openOpForm(id); }};
      document.getElementById('opDetailDrawer').classList.add('active');
    }}
    </script>
    """
    return render_page("算子管理", content, active="operators", breadcrumb="自动化任务 / <b>算子管理</b>")


@app.route("/pipelines")
def pipelines():
    f_op = request.args.get("op", "")
    pls = [pl for pl in PIPELINES if not f_op or f_op in pl["stages"]]
    rows = ""
    for pl in pls:
        scheds = pl.get("schedules", [])
        n_sch = len(scheds)
        sch_title = " / ".join(scheds) if scheds else "无周期调度"
        sch_cell = (f'<span class="sched-badge" title="{sch_title}">{n_sch}</span>'
                    if n_sch else '<span class="muted">0</span>')
        rows += f"""<tr>
          <td><b>{pl['name']}</b></td>
          <td class="muted" style="max-width:380px;"><span class="desc-clamp">{pl['desc']}</span></td>
          <td>{len(pl['stages'])} 个算子</td>
          <td>{sch_cell}</td>
          <td>{pl['creator']}</td>
          <td><label class="switch"><input type="checkbox" checked onchange="toast(this.checked?'已启用任务':'已停用任务')"><span class="slider"></span></label></td>
          <td class="muted">{pl['updated']}</td>
          <td class="actions-cell"><a href="/pipelines/{pl['id']}">编辑</a> · <a href="#" onclick="openRun('{pl['name']}');return false;">执行</a></td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="8" class="muted" style="text-align:center;padding:24px;">无匹配任务</td></tr>'
    op_checks = "".join(
        f'<label><input type="checkbox" value="{o["id"]}"{" checked" if o["id"]==f_op else ""} onchange="msUpdate(this)">{o["name"].split(" ")[0]}</label>'
        for o in OPERATORS)
    op_label = ("算子 (1)" if f_op else "算子")
    op_hasval = "has-value" if f_op else ""
    content = f"""
    <div class="filter-bar">
      <input placeholder="搜索任务...">
      <div class="ms-wrap">
        <div class="ms-trigger {op_hasval}" data-base="算子" onclick="this.closest('.ms-wrap').classList.toggle('open')"><span class="ms-label">{op_label}</span></div>
        <div class="ms-panel">{op_checks}</div>
      </div>
      <a href="/pipelines/new" class="btn-primary btn" style="margin-left:auto;">+ 新建任务</a>
    </div>
    <div class="muted" style="margin-bottom:12px;">把算子编排成可复用、可调度的任务, 用于批量重复跑数据集。</div>
    <table class="ant-table row2">
      <thead><tr><th>名称</th><th>描述</th><th>算子数</th><th>周期任务数</th><th>创建人</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <!-- 执行任务: 填写本次运行参数 -->
    <div class="drawer-mask" id="runDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer" style="width:480px;">
        <div class="drawer-head"><h3>执行任务</h3><button class="drawer-close" onclick="document.getElementById('runDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="muted" id="runHint" style="font-size:12px;margin-bottom:14px;line-height:1.6;">提交一次性运行。填写本次运行的流程参数取值, 提交后进度见「执行记录」。</div>
          <div class="section-label">运行参数</div>
          <table class="param-table"><tbody>
            <tr><td class="pk">target_datasets</td><td><input value="pretrain_v3,posttrain_v2,custom_01"><div class="hint">支持多个, 英文逗号分隔</div></td></tr>
            <tr><td class="pk">tos_bucket</td><td><input value="tos://embodied-datasets" disabled><div class="hint">系统内置, 只读</div></td></tr>
          </tbody></table>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="document.getElementById('runDrawer').classList.remove('active')">取消</button>
          <button class="btn-primary btn" onclick="document.getElementById('runDrawer').classList.remove('active');toast('Demo: 已提交执行, 见执行记录')">&#9654; 确认执行</button>
        </div>
      </div>
    </div>
    <script>
    function openRun(name){{
      document.getElementById('runHint').innerHTML = '任务 <b>'+name+'</b> · 提交一次性运行。填写本次运行的流程参数取值, 提交后进度见「执行记录」。';
      document.getElementById('runDrawer').classList.add('active');
    }}
    function msUpdate(cb){{
      var wrap=cb.closest('.ms-wrap'); var n=wrap.querySelectorAll('input:checked').length;
      wrap.querySelector('.ms-label').textContent = n ? ('算子 ('+n+')') : '算子';
    }}
    document.addEventListener('click', function(e){{
      document.querySelectorAll('.ms-wrap.open').forEach(function(w){{ if(!w.contains(e.target)) w.classList.remove('open'); }});
    }});
    </script>
    """
    return render_page("任务管理", content, active="pipelines", breadcrumb="自动化任务 / <b>任务管理</b>")


WF_CANVAS_JS = r"""
(function(){
  var NODES = __NODES__, EDGES = __EDGES__;
  var seq = NODES.length;
  var W = 220, DEF_H = 126;
  var canvas = document.getElementById('wfCanvas');
  var pan = document.getElementById('wfPan');
  var nodesLayer = document.getElementById('wfNodes');
  var edgesSvg = document.getElementById('wfEdges');
  var emptyEl = document.getElementById('wfEmpty');
  var z = 1, panX = 0, panY = 0;
  var selId = null, drag = null, conn = null, panning = null;

  function byId(id){ for(var i=0;i<NODES.length;i++) if(NODES[i].id===id) return NODES[i]; return null; }
  function applyPan(){ pan.style.transform = 'translate('+panX+'px,'+panY+'px) scale('+z+')'; }
  function toLocal(cx, cy){ var r=canvas.getBoundingClientRect(); return { x:(cx-r.left-panX)/z, y:(cy-r.top-panY)/z }; }
  function nodeH(n){ var el=nodesLayer.querySelector('.wf-node[data-id="'+n.id+'"]'); return (el&&el.offsetHeight)||DEF_H; }
  function ports(n){ var h=nodeH(n); return { inp:{x:n.x, y:n.y+h/2}, out:{x:n.x+W, y:n.y+h/2} }; }
  function bezier(s,t){ return 'M'+s.x+' '+s.y+' C '+(s.x+70)+' '+s.y+', '+(t.x-70)+' '+t.y+', '+t.x+' '+t.y; }

  function renderEdges(extra){
    var p='';
    for(var i=0;i<EDGES.length;i++){
      var a=byId(EDGES[i].from), b=byId(EDGES[i].to); if(!a||!b) continue;
      var s=ports(a).out, t=ports(b).inp;
      p+='<path class="edge" data-i="'+i+'" d="'+bezier(s,t)+'" fill="none" stroke="#9ec3d6" stroke-width="2" marker-end="url(#wfArrow)"/>';
    }
    if(extra) p+=extra;
    edgesSvg.innerHTML='<defs><marker id="wfArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#9ec3d6"/></marker></defs>'+p;
  }
  function renderNodes(){
    var h='';
    for(var i=0;i<NODES.length;i++){
      var n=NODES[i];
      h+='<div class="wf-node'+(n.id===selId?' sel':'')+'" data-id="'+n.id+'" style="left:'+n.x+'px;top:'+n.y+'px;">'+
        '<div class="wf-port in" data-port="in" data-id="'+n.id+'"></div>'+
        '<div class="wf-port out" data-port="out" data-id="'+n.id+'"></div>'+
        '<div class="wf-node-head"><span class="wf-node-ic">&#9881;</span>'+n.name+
          '<span class="wf-node-del" data-del="'+n.id+'" title="删除">&times;</span></div>'+
        '<div class="wf-node-row"><span class="k">标识</span><span class="v">'+n.ident+'</span></div>'+
        '<div class="wf-node-row"><span class="k">描述</span><span class="v">'+n.desc+'</span></div>'+
      '</div>';
    }
    nodesLayer.innerHTML=h;
    if(emptyEl) emptyEl.style.display = NODES.length ? 'none' : '';
    renderEdges();
  }

  canvas.addEventListener('mousedown', function(e){
    var del=e.target.getAttribute('data-del');
    if(del){ EDGES=EDGES.filter(function(x){return x.from!==del&&x.to!==del;}); NODES=NODES.filter(function(x){return x.id!==del;}); if(selId===del) wfCloseConfig(); renderNodes(); return; }
    var port=e.target.closest('.wf-port');
    if(port){ conn={from:port.getAttribute('data-id'), side:port.getAttribute('data-port')}; e.preventDefault(); return; }
    var ep=e.target.closest('path.edge');
    if(ep){ var idx=+ep.getAttribute('data-i'); EDGES.splice(idx,1); renderNodes(); return; }
    var nodeEl=e.target.closest('.wf-node');
    if(nodeEl){ var n=byId(nodeEl.getAttribute('data-id')); drag={id:n.id, sx:e.clientX, sy:e.clientY, ox:n.x, oy:n.y, moved:false}; e.preventDefault(); return; }
    panning={sx:e.clientX, sy:e.clientY, ox:panX, oy:panY};
  });
  document.addEventListener('mousemove', function(e){
    if(drag){
      var dx=(e.clientX-drag.sx)/z, dy=(e.clientY-drag.sy)/z;
      if(Math.abs(e.clientX-drag.sx)+Math.abs(e.clientY-drag.sy)>3) drag.moved=true;
      var n=byId(drag.id); n.x=drag.ox+dx; n.y=drag.oy+dy;
      var el=nodesLayer.querySelector('.wf-node[data-id="'+drag.id+'"]'); if(el){ el.style.left=n.x+'px'; el.style.top=n.y+'px'; }
      renderEdges();
    } else if(conn){
      var a=byId(conn.from); var s=conn.side==='out'?ports(a).out:ports(a).inp;
      var m=toLocal(e.clientX,e.clientY);
      renderEdges('<path d="'+bezier(s,m)+'" fill="none" stroke="#1F80A0" stroke-width="2" stroke-dasharray="5 4"/>');
    } else if(panning){
      panX=panning.ox+(e.clientX-panning.sx); panY=panning.oy+(e.clientY-panning.sy); applyPan();
    }
  });
  document.addEventListener('mouseup', function(e){
    if(conn){
      var port=e.target.closest('.wf-port');
      if(port && port.getAttribute('data-port')!==conn.side){
        var other=port.getAttribute('data-id');
        var f = conn.side==='out'?conn.from:other, t = conn.side==='out'?other:conn.from;
        if(f!==t && !EDGES.some(function(x){return x.from===f&&x.to===t;})) EDGES.push({from:f,to:t});
      }
      conn=null; renderNodes(); return;
    }
    if(drag){ if(!drag.moved){ selId=drag.id; openConfig(byId(drag.id)); renderNodes(); } drag=null; return; }
    panning=null;
  });

  function openConfig(n){
    document.getElementById('wfConfig').classList.add('open');
    document.getElementById('wfcName').textContent=n.name+' · 配置';
    document.getElementById('wfcName2').textContent=n.name;
    document.getElementById('wfcIdent').textContent=n.ident||'—';
    document.getElementById('wfcDesc').textContent=n.desc||'—';
    document.getElementById('wfcImage').textContent=n.image||'—';
    document.getElementById('wfcScript').textContent=n.script||'—';
    document.getElementById('wfcReturns').textContent=(n.returns||'—').split(/ \+ | \/ /).join('\n');
    // 参数取值: 算子定义出 schema, 节点填值 (默认=算子默认, 可覆盖/可引用流程变量)
    var items=(n.params||'').split(' / ').filter(Boolean);
    var html=items.map(function(p){
      var sp=p.indexOf(' '); var k=sp>0?p.slice(0,sp):p; var v=sp>0?p.slice(sp+1):'';
      v=v.replace(/"/g,'&quot;');
      return '<div class="wf-param">'+
        '<div class="wf-param-top"><span class="wf-param-k">'+k+'</span>'+
          '<select class="wf-param-src df" onchange="wfSrcChange(this)">'+
            '<option value="df">算子默认</option><option value="ov">本节点覆盖</option><option value="rf">引用流程变量</option></select>'+
        '</div>'+
        '<input class="wf-param-v" value="'+v+'" oninput="wfMarkOv(this)" placeholder="（无默认值 / flag）">'+
      '</div>';
    }).join('');
    document.getElementById('wfcParamsEdit').innerHTML = html || '<div class="muted" style="font-size:12px;padding:4px 0;">该算子无入参</div>';
  }
  window.wfSrcChange=function(sel){
    sel.className='wf-param-src '+sel.value;
    var inp=sel.closest('.wf-param').querySelector('.wf-param-v');
    if(sel.value==='rf' && inp.value.indexOf('${')<0){ inp.value='${target_datasets}'; }
  };
  window.wfMarkOv=function(inp){
    var sel=inp.closest('.wf-param').querySelector('.wf-param-src');
    if(sel.value==='df'){ sel.value='ov'; sel.className='wf-param-src ov'; }
  };
  window.wfAddFlowParam=function(){
    var tb=document.getElementById('flowParamBody');
    var tr=document.createElement('tr');
    tr.innerHTML='<td><input class="fp-key" placeholder="英文标识"></td>'+
      '<td><input class="fp-val" placeholder="变量值"></td>'+
      '<td><a href="#" onclick="wfDelFlowParam(this);return false;" style="color:#bfbfbf;">删</a></td>';
    tb.appendChild(tr);
    tr.querySelector('.fp-key').focus();
  };
  window.wfDelFlowParam=function(a){ var tr=a.closest('tr'); if(tr) tr.remove(); };
  var SCH_CRON={day:'0 2 * * *', hour:'0 * * * *', week:'0 2 * * 1', month:'0 2 1 * *'};
  window.schFreq2=function(sel){
    var grp=sel.closest('.sch-group'); var exp=grp.querySelector('.sch-expr');
    if(sel.value!=='custom') exp.value=SCH_CRON[sel.value]||exp.value;
  };
  window.schAddGroup=function(time){
    var box=document.getElementById('schGroups');
    var n=box.querySelectorAll('.sch-group').length+1;
    var g=document.createElement('div'); g.className='sch-group';
    g.innerHTML='<div class="sch-group-head">调度组 '+n+'<span class="sch-del" onclick="schDelGroup(this)">删除</span></div>'+
      '<table class="param-table"><tbody>'+
      '<tr><td class="pk">调度频率</td><td><select onchange="schFreq2(this)"><option value="day">每天</option><option value="hour">每小时</option><option value="week">每周一</option><option value="month">每月 1 号</option><option value="custom">Cron 自定义</option></select></td></tr>'+
      '<tr><td class="pk">执行时间</td><td><input type="time" value="'+(time||'02:00')+'"></td></tr>'+
      '<tr><td class="pk">Cron 表达式</td><td><input class="sch-expr" value="0 2 * * *" style="font-family:monospace;"></td></tr>'+
      '</tbody></table>';
    box.appendChild(g);
  };
  window.schDelGroup=function(a){ var g=a.closest('.sch-group'); var box=g.parentNode; if(box.querySelectorAll('.sch-group').length<=1){ toast('至少保留一组'); return; } g.remove(); box.querySelectorAll('.sch-group-head').forEach(function(h,i){ h.childNodes[0].nodeValue='调度组 '+(i+1); }); };
  document.addEventListener('DOMContentLoaded', function(){ if(document.getElementById('schGroups')){ schAddGroup('02:00'); schAddGroup('06:00'); } });
  window.wfCloseConfig=function(){ document.getElementById('wfConfig').classList.remove('open'); selId=null; renderNodes(); };
  window.wfDeleteSel=function(){ if(!selId) return; var id=selId; EDGES=EDGES.filter(function(x){return x.from!==id&&x.to!==id;}); NODES=NODES.filter(function(x){return x.id!==id;}); wfCloseConfig(); toast('已删除节点'); };

  var OPS = __OPS__;
  window.wfAddNode=function(opId){
    var o=OPS[opId]; if(!o) return;
    seq++; var id='n'+seq;
    var base=toLocal(canvas.getBoundingClientRect().left+160, canvas.getBoundingClientRect().top+140);
    NODES.push({id:id, name:o.name, ident:o.ident, desc:o.desc, enabled:o.enabled, creator:o.creator,
                image:o.image, script:o.script, params:o.params, returns:o.returns,
                x:base.x+(NODES.length%4)*30, y:base.y+(NODES.length%3)*40});
    document.getElementById('addTaskDrawer').classList.remove('active');
    renderNodes(); toast('已添加算子: '+o.name);
  };
  window.wfZoom=function(d){ z=Math.min(1.6, Math.max(0.4, Math.round((z+d)*10)/10)); document.getElementById('wfZlvl').textContent=Math.round(z*100)+'%'; applyPan(); };
  window.wfFit=function(){ z=1; panX=0; panY=0; document.getElementById('wfZlvl').textContent='100%'; applyPan(); };

  applyPan(); renderNodes();
})();
"""


@app.route("/pipelines/<pid>")
def pipeline_editor(pid):
    pl = next((p for p in PIPELINES if p["id"] == pid), None)
    is_new = pid == "new" or pl is None
    name = "新建任务" if is_new else pl["name"]
    stages = [] if is_new else pl["stages"]

    # 初始节点 (自由画布: 左→右铺开), 以及顺序连线
    init_nodes, init_edges = [], []
    for i, sid in enumerate(stages):
        op = next((o for o in OPERATORS if o["id"] == sid), None)
        if not op:
            continue
        nid = f"n{i}"
        init_nodes.append({
            "id": nid, "name": op["name"].split(" ")[0], "ident": op["ident"],
            "desc": op["desc"], "enabled": "启用", "creator": op["creator"],
            "image": "frontdesk-py3.10:latest", "script": "python " + op["script"],
            "params": op["params"], "returns": op["returns"],
            "x": 60 + i * 280, "y": 150 + (i % 2) * 50,
        })
        if i > 0:
            init_edges.append({"from": f"n{i-1}", "to": nid})
    nodes_json = json.dumps(init_nodes, ensure_ascii=False)
    edges_json = json.dumps(init_edges, ensure_ascii=False)
    ops_map = {o["id"]: {"name": o["name"].split(" ")[0], "ident": o["ident"], "desc": o["desc"],
                         "enabled": "启用", "creator": o["creator"], "image": "frontdesk-py3.10:latest",
                         "script": "python " + o["script"], "params": o["params"], "returns": o["returns"]}
               for o in OPERATORS}
    ops_json = json.dumps(ops_map, ensure_ascii=False)

    # 添加算子抽屉: 点击 → JS 加节点
    op_items = ""
    for o in OPERATORS:
        op_items += (f"""<div class="op-pick" onclick="wfAddNode('{o['id']}')">"""
                     f'<div><b>{o["name"]}</b> <span class="op-script">{o["ident"]}</span></div>'
                     f'<div class="muted" style="font-size:12px;">{o["cat"]} · {o["creator"]}</div></div>')

    content = f"""
    <div class="wf-topbar">
      <div class="wf-title"><a href="/pipelines" class="back">&#8249;</a> 任务: {name} <span style="color:#bfbfbf;font-size:14px;cursor:pointer;" onclick="toast('Demo: 重命名')">&#9998;</span></div>
      <div class="wf-actions">
        <button class="btn" onclick="document.getElementById('flowParamDrawer').classList.add('active')">&#123;&#125; 流程参数</button>
        <button class="btn" onclick="document.getElementById('scheduleDrawer').classList.add('active')">&#9201; 周期调度</button>
        <button class="btn" onclick="toast('Demo: 已保存')">&#128190; 保存</button>
        <button class="btn-primary btn" onclick="document.getElementById('runDrawer').classList.add('active')">&#9654; 执行</button>
      </div>
    </div>
    <div class="wf-stage">
      <div class="wf-canvas" id="wfCanvas">
        <div class="wf-pan" id="wfPan" style="width:4000px;height:3000px;">
          <svg class="wf-edges" id="wfEdges"></svg>
          <div id="wfNodes"></div>
        </div>
        <div class="wf-empty" id="wfEmpty"><div style="font-size:32px;">&#9783;</div><div>画布为空, 点击「+ 添加算子」开始编排</div></div>
        <div class="wf-hint">拖动节点可移动 · 拖动节点右侧锚点到另一节点左侧锚点可连线 · 点击节点查看配置</div>
        <div class="wf-toolbar">
          <button class="zbtn" onclick="wfZoom(-0.1)">&minus;</button>
          <span class="zlvl" id="wfZlvl">100%</span>
          <button class="zbtn" onclick="wfZoom(0.1)">&plus;</button>
          <button class="zbtn" onclick="wfFit()" title="适应画布">&#9974;</button>
          <span class="sep"></span>
          <button class="btn-primary btn" onclick="document.getElementById('addTaskDrawer').classList.add('active')">&plus; 添加算子</button>
        </div>
      </div>

      <div class="wf-config" id="wfConfig">
        <div class="wf-config-head"><b id="wfcName">节点配置</b><button class="drawer-close" onclick="wfCloseConfig()">&times;</button></div>
        <div class="wf-config-body">
          <div class="wf-cfg-sec">基本信息</div>
          <div class="wf-cfg-row lft"><span>名称</span><b id="wfcName2">—</b></div>
          <div class="wf-cfg-row lft"><span>标识</span><span id="wfcIdent" style="font-family:monospace;font-size:12px;">—</span></div>
          <div class="wf-cfg-row lft"><span>描述</span><span id="wfcDesc" style="line-height:1.5;">—</span></div>

          <div class="wf-cfg-sec">运行环境</div>
          <div class="wf-cfg-row lft"><span>运行镜像</span><span id="wfcImage" style="font-size:12px;word-break:break-all;">—</span></div>
          <div class="wf-cfg-col"><span>入口脚本 / 命令</span><pre id="wfcScript" class="wf-cfg-code">—</pre></div>

          <div class="wf-cfg-sec">出入参
            <a class="wf-sec-link" onclick="document.getElementById('flowParamDrawer').classList.add('active')">流程参数 &#8599;</a></div>
          <div class="wf-param-sub">入参取值</div>
          <div id="wfcParamsEdit"></div>
          <div class="wf-param-sub" style="margin-top:12px;">返回结果</div>
          <div class="wf-cfg-col"><pre id="wfcReturns" class="wf-cfg-code">—</pre></div>
        </div>
        <div class="wf-config-foot">
          <button class="btn" onclick="wfDeleteSel()">删除节点</button>
          <button class="btn-primary btn" onclick="toast('Demo: 已保存节点配置')">保存</button>
        </div>
      </div>
    </div>

    <div class="drawer-mask" id="addTaskDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer" style="width:420px;">
        <div class="drawer-head"><h3>添加算子</h3><button class="drawer-close" onclick="document.getElementById('addTaskDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <input placeholder="搜索算子..." style="width:100%;box-sizing:border-box;height:34px;padding:5px 12px;border:1px solid #d9d9d9;border-radius:8px;margin-bottom:12px;outline:none;">
          {op_items}
        </div>
      </div>
    </div>

    <!-- 流程级全局参数: 被多个节点引用, 跑同一流程换不同输入 -->
    <div class="drawer-mask" id="flowParamDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer" style="width:480px;">
        <div class="drawer-head"><h3>流程参数</h3><button class="drawer-close" onclick="document.getElementById('flowParamDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="muted" style="font-size:12px;margin-bottom:14px;line-height:1.6;">流程级全局变量, 被多个节点以 <code>${{变量名}}</code> 引用。改这里 = 同一流程换不同输入跑, 无需逐个节点改。</div>
          <table class="ant-table" style="font-size:13px;">
            <thead><tr><th style="width:150px;">变量名</th><th>值</th><th style="width:60px;"></th></tr></thead>
            <tbody id="flowParamBody">
              <tr><td><input class="fp-key" value="target_datasets" placeholder="英文标识"></td><td><input class="fp-val" value="pretrain_v3,posttrain_v2,custom_01"><div class="hint">支持多个, 英文逗号分隔</div></td><td><a href="#" onclick="wfDelFlowParam(this);return false;" style="color:#bfbfbf;">删</a></td></tr>
              <tr><td><input class="fp-key" value="tos_bucket" disabled></td><td><input class="fp-val" value="tos://embodied-datasets" disabled><div class="hint">系统内置, 只读</div></td><td><span style="color:#d9d9d9;cursor:not-allowed;">删</span></td></tr>
            </tbody>
          </table>
          <button class="btn" style="margin-top:12px;" onclick="wfAddFlowParam()">&plus; 新增变量</button>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="document.getElementById('flowParamDrawer').classList.remove('active')">取消</button>
          <button class="btn-primary btn" onclick="document.getElementById('flowParamDrawer').classList.remove('active');toast('Demo: 已保存流程参数')">保存</button>
        </div>
      </div>
    </div>

    <!-- 执行: 一次性运行, 配置本次调用参数 -->
    <div class="drawer-mask" id="runDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer" style="width:480px;">
        <div class="drawer-head"><h3>执行任务</h3><button class="drawer-close" onclick="document.getElementById('runDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="muted" style="font-size:12px;margin-bottom:14px;line-height:1.6;">提交一次性运行。填写本次运行的流程参数取值并选择资源, 提交后进度见「执行记录」。</div>
          <div class="section-label">运行参数</div>
          <table class="param-table"><tbody>
            <tr><td class="pk">target_datasets</td><td><input value="pretrain_v3,posttrain_v2,custom_01"><div class="hint">支持多个, 英文逗号分隔</div></td></tr>
            <tr><td class="pk">tos_bucket</td><td><input value="tos://embodied-datasets" disabled><div class="hint">系统内置, 只读</div></td></tr>
          </tbody></table>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="document.getElementById('runDrawer').classList.remove('active')">取消</button>
          <button class="btn-primary btn" onclick="document.getElementById('runDrawer').classList.remove('active');toast('Demo: 已提交执行, 见执行记录')">&#9654; 确认执行</button>
        </div>
      </div>
    </div>

    <!-- 周期调度: 定时运行, 配置 cron + 调用参数 -->
    <div class="drawer-mask" id="scheduleDrawer" onclick="if(event.target===this)this.classList.remove('active')">
      <div class="drawer" style="width:480px;">
        <div class="drawer-head"><h3>周期调度</h3><button class="drawer-close" onclick="document.getElementById('scheduleDrawer').classList.remove('active')">&times;</button></div>
        <div class="drawer-body">
          <div class="section-label">调度设置</div>
          <div id="schGroups"></div>
          <button type="button" class="btn" style="margin:4px 0 6px;" onclick="schAddGroup()">&plus; 添加一组</button>
          <table class="param-table"><tbody>
            <tr><td class="pk">生效范围</td><td><div style="display:flex;gap:8px;align-items:center;"><input type="date" value="2026-06-08"><span class="muted">~</span><input type="date"></div></td></tr>
          </tbody></table>
          <div class="section-label">默认运行参数</div>
          <table class="param-table"><tbody>
            <tr><td class="pk">target_datasets</td><td><input value="pretrain_v3,posttrain_v2,custom_01"><div class="hint">支持多个, 英文逗号分隔</div></td></tr>
            <tr><td class="pk">tos_bucket</td><td><input value="tos://embodied-datasets" disabled><div class="hint">系统内置, 只读</div></td></tr>
          </tbody></table>
          <div class="section-label">异常处理</div>
          <table class="param-table"><tbody>
            <tr><td class="pk">失败重试</td><td><select><option>不重试</option><option>1 次</option><option>2 次</option><option>3 次</option></select></td></tr>
            <tr><td class="pk">超时 (分钟)</td><td><input value="120"></td></tr>
            <tr><td class="pk">失败通知</td><td><input placeholder="邮箱, 多个用英文逗号分隔"></td></tr>
          </tbody></table>
        </div>
        <div class="drawer-foot">
          <button class="btn" onclick="document.getElementById('scheduleDrawer').classList.remove('active')">取消</button>
          <button class="btn-primary btn" onclick="document.getElementById('scheduleDrawer').classList.remove('active');toast('Demo: 已保存调度配置')">保存调度</button>
        </div>
      </div>
    </div>
    <script>{WF_CANVAS_JS.replace("__NODES__", nodes_json).replace("__EDGES__", edges_json).replace("__OPS__", ops_json)}</script>
    """
    return render_page(name, content, active="pipelines",
                       breadcrumb=f'自动化任务 / 任务管理 / <b>{name}</b>', extra_script=None)


@app.route("/runs")
def runs():
    # 执行记录: 每行 = 一次任务执行实例 (一个任务里可能含多个算子, 故不展开到算子)
    st_map = {"running": ("qa-warn", "运行中", ""), "done": ("qa-pass", "成功", ""),
              "failed": ("qa-fail", "失败", "fail")}
    pl_creator = {p["id"]: p["creator"] for p in PIPELINES}
    rows = ""
    for r in RUNS:
        cls, label, barcls = st_map[r["status"]]
        if r["trigger"] == "manual":
            trig = '<span class="tag tag-blue">手动触发</span>'
            by = r.get("by", "—")
        else:
            trig = '<span class="tag tag-gray">定时触发</span>'
            by = pl_creator.get(r["pipeline"], "—")
        rows += f"""<tr>
        <td style="font-family:monospace;font-size:12px;">{r['id']}</td>
        <td><b>{r['name']}</b></td>
        <td>{r['target']}</td>
        <td><span class="qa {cls}">{label}</span></td>
        <td>{trig}</td>
        <td>{by}</td>
        <td class="muted">{r['at']}</td>
        <td class="muted">{r['dur']}</td>
        <td class="actions-cell"><a href="#" onclick="toast('Demo: 查看任务日志');return false;">日志</a> · <a href="#" onclick="toast('Demo: 重跑');return false;">重跑</a></td></tr>"""
    n_run = sum(1 for r in RUNS if r["status"] == "running")
    n_fail = sum(1 for r in RUNS if r["status"] == "failed")
    content = f"""
    <div class="filter-bar">
      <select class="has-value"><option value="">全部任务</option><option>标准训练数据流水线</option><option>DAgger 数据流水线</option></select>
      <select class="has-value"><option value="">全部状态</option><option>成功</option><option>运行中</option><option>失败</option></select>
      <select class="has-value"><option value="">全部触发方式</option><option>手动触发</option><option>定时触发</option></select>
      <input placeholder="搜索任务 / 产出数据集...">
    </div>
    <div class="muted" style="margin-bottom:12px;">共 {len(RUNS)} 次执行 · 运行中 {n_run} · 失败 {n_fail} · 每行 = 一次任务执行实例</div>
    <table class="ant-table">
      <thead><tr><th>实例 ID</th><th>任务名称</th><th>产出数据集</th><th>状态</th><th>触发方式</th><th>触发人</th><th>开始时间</th><th>耗时</th><th>操作</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return render_page("执行记录", content, active="runs", breadcrumb="自动化任务 / <b>执行记录</b>")


@app.route("/tags")
def tags():
    dims = TAG_SYSTEM["dimensions"]
    n_dim = len(dims)
    n_l2 = sum(len(d.get("leaves", d.get("groups", []))) for d in dims)
    n_l3 = sum(sum(len(g["items"]) for g in d.get("groups", [])) for d in dims)

    ops = ('<span class="tg-ops">'
           '<span onclick="toast(\'Demo: 复制\')" title="复制">&#10697;</span>'
           '<span onclick="toast(\'Demo: 编辑\')" title="编辑">&#9998;</span>'
           '<span class="del" onclick="toast(\'Demo: 删除\')" title="删除">&#128465;</span>'
           '</span>')

    def row(level, rid, parent, name, en, desc, child_count, has_children, expanded, visible):
        indent = 14 + level * 22
        if has_children:
            caret = (f'<span class="tg-caret {"open" if expanded else ""}" data-caret="{rid}" '
                     f'onclick="tgToggle(\'{rid}\')">&#9656;</span>')
        else:
            caret = '<span class="tg-caret-none"></span>'
        ncls = "tg-dim" if level == 0 else ("tg-l2" if level == 1 else "tg-l3")
        en_html = f'<span class="tg-en">{en}</span>' if en else ''
        badge = f'<span class="tg-badge">{child_count}</span>' if has_children else ''
        disp = '' if visible else 'display:none;'
        return (f'<tr class="tg-row" data-id="{rid}" data-parent="{parent}" style="{disp}">'
                f'<td><div class="tg-name" style="padding-left:{indent}px;">{caret}'
                f'<span class="{ncls}">{name}</span>{en_html}</div></td>'
                f'<td class="muted">{desc or "—"}</td><td>{badge}</td><td>{ops}</td></tr>')

    rows = ""
    for i, d in enumerate(dims):
        did = f"d{i}"
        if "groups" in d:
            n_child = len(d["groups"])
        else:
            n_child = len(d["leaves"])
        # 维度行 (默认展开)
        rows += row(0, did, "", d["name"], d["en"], d["desc"], n_child, True, True, True)
        if "leaves" in d:
            for j, leaf in enumerate(d["leaves"]):
                rows += row(1, f"{did}-{j}", did, leaf, "", "", 0, False, False, True)
        else:
            for j, g in enumerate(d["groups"]):
                gid = f"{did}-{j}"
                # 类目行 (默认收起 → 三级隐藏)
                rows += row(1, gid, did, g["category"], "", "", len(g["items"]), True, False, True)
                for k, it in enumerate(g["items"]):
                    rows += row(2, f"{gid}-{k}", gid, it, "", "", 0, False, False, False)

    content = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
      <div class="muted">标签体系 v{TAG_SYSTEM['version']} · {n_dim} 个维度 · {n_l2} 个二级 · {n_l3} 个三级</div>
      <div style="display:flex;gap:8px;">
        <button class="btn" onclick="tgAll(true)">全部展开</button>
        <button class="btn" onclick="tgAll(false)">全部收起</button>
        <button class="btn-primary btn" onclick="toast('Demo: 新增维度')">+ 新增维度</button>
      </div>
    </div>
    <table class="ant-table tg-table">
      <thead><tr><th>名称</th><th>描述</th><th>子项</th><th>操作</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    script = """<script>
    function tgCollapseDesc(id){
      document.querySelectorAll('[data-parent="'+id+'"]').forEach(function(r){
        r.style.display='none';
        var c=document.querySelector('[data-caret="'+r.getAttribute('data-id')+'"]'); if(c) c.classList.remove('open');
        tgCollapseDesc(r.getAttribute('data-id'));
      });
    }
    function tgToggle(id){
      var caret=document.querySelector('[data-caret="'+id+'"]');
      var expanded=caret.classList.toggle('open');
      document.querySelectorAll('[data-parent="'+id+'"]').forEach(function(r){
        if(expanded){ r.style.display=''; }
        else { tgCollapseDesc(id); }
      });
    }
    function tgAll(expand){
      document.querySelectorAll('.tg-caret').forEach(function(c){ c.classList.toggle('open', expand); });
      document.querySelectorAll('.tg-row').forEach(function(r){
        var p=r.getAttribute('data-parent');
        r.style.display = (expand || p==='') ? '' : 'none';
      });
    }
    </script>"""
    return render_page("标签管理", content, active="tags",
                       breadcrumb="资产 / <b>标签管理</b>", extra_script=script, top="asset")


# ════════════════════════════════════════════════════════════════
# Section 5: Main
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=False)
