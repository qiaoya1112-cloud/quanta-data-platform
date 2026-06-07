#!/usr/bin/env python3
"""
分析202510_all_dual和其他数据的采样比例与帧数占比
"""

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def extract_subcategory(dataset_key: str) -> str:
    """
    提取子类别：前两级目录，去掉机器人ID后缀和dataset子目录
    例如: writingdesk/1000_20251225_Pick&PlaceEverything_Visual_Prompt_FrontDeskDemo_Moz1WB_moz1-k02/dataset_0_30_b3b18ea8f1498d16
    -> writingdesk/1000_20251225_Pick&PlaceEverything_Visual_Prompt_FrontDeskDemo_Moz1WB
    """
    parts = dataset_key.split("/")

    if len(parts) < 2:
        return dataset_key

    # 取前两级
    category = parts[0]
    subcategory_raw = parts[1]

    # 去掉机器人ID后缀 (如 _moz1-k02, _moz1-y04, _hrpi2, _HRPI 等)
    # 常见模式: _moz1-xxx, _hrpi-xxx, _hrpi2, _HRPI, _WB, _Moz1WB 等
    # 我们保留任务名称，去掉机器人实例ID
    subcategory = re.sub(r'_moz1-[a-z0-9]+$', '', subcategory_raw, flags=re.IGNORECASE)
    subcategory = re.sub(r'_hrpi\d*-[a-z0-9]+$', '', subcategory, flags=re.IGNORECASE)

    return f"{category}/{subcategory}"


def match_group(dataset_key: str, group_rules: Dict[str, any]) -> str:
    """
    根据 GROUP_RULES 匹配数据集所属的组

    Args:
        dataset_key: 数据集路径/名称
        group_rules: {组名: 关键词} 或 {组名: [关键词列表]}

    Returns:
        匹配的组名，未匹配则返回 "_other"
    """
    for group_name, keywords in group_rules.items():
        # 支持单个关键词或关键词列表
        if isinstance(keywords, str):
            keywords = [keywords]
        if any(kw in dataset_key for kw in keywords):
            return group_name
    return "_other"


# ============================================================================
# GROUP_RULES 配置（与 adjust_sampling_ratio.py 保持一致）
# ============================================================================
GROUP_RULES = {
    "human_interaction": "Humaninteraction",
    "pick_place": ["v6_FrontDeskDemo/851_20251208_NoReset_VisualPrompt_PickPlace", "202510_all_dual", "pickplace_visualprompt_09vpALL","WB_pp_reset"],
    "drawer": ["drawer"],
    "insert": ["Insert_V2","insertflower","PlaceTableware","PlaceFlatware"],
    "insert_dagger": ["Insert_dagger","Insertflower_dagger"],
    "makesandwich": ["Makesandwich"],
    "stack": ["Stack"],
    "waterflowers": ["WaterFlower"],
    "PourWater": ["PourWater"],
    "sweep": ["sweep"],
    "TossToyIntoBox": ["TossToyIntoBox"],
    "candy": ["candy"],
    "wipe_new": ["wipe_new","Wipe"],
    "PourTrash": ["PourTrash"],
    "writing_desk_vp": ["1000_20251225_Pick&PlaceEverything_Visual_Prompt","1011_20251228_Pick&PlaceEverything_VisualPrompt",
                        "1026_20251230_PickPlaceEverythingWithBookshelf_VisualPrompt","20260109_PickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                        "20260110_ObstacleAvoidingPickPlaceEverythingWithBookshelf_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB_V2",
                        "20260113_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB",
                        "1165_20260116_DrawerOpened_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB","PickPlaceEverythingWithBookshelf_WritingDesk",
                        "PickPlaceBookWithBookshelf_WritingDesk"],
    "writing_desk_scoop": ["1014_20251228_ScoopNuts","1076_20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1077_20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB","1090_20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1168_20260116_DrawerOpened_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1239_20260125_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB","ScoopNutsTwoHands_WritingDesk","BowlScoopNutsTwoHands_WritingDesk"],
    "writing_desk_penholder": ["1015_20251228_PenHolder","PenHolder_WritingDesk"],
    "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt","20251212_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB","20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1138_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1146_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "20260116_DrawerOpened_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1186_20260119_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1215_20260122_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "BookWithBookend_VisualPrompt", "Bookend_VisualPrompt_WritingDesk"],
    "dagger_book": ["1073_20260109_writingdesk_v1_book_WBWB_dagger","1170_20260115_writingdesk_v1_takebook_WBWB_dagger"],
    "dagger_pp": ["1078_20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"],
    "scoop_tea": ["20251216_ScoopTea_FrontDeskDemo_Moz1WB"],
    "AdjustBowlPosition": ["1091_20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"],
    "WipeSpillArea": ["1098_20260112_WipeSpillArea_WritingDesk_FrontDeskDemo","20260113_WipeSpillArea_WritingDesk_FrontDeskDemo"],
    "PickStackedBowls": ["1099_20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"],
    "PrepareForSnack": ["20251218_PrepareForSnack_FrontDeskDemo_Moz1WB"],
    "PenHolder": ["20251218_PenHolder_FrontDeskDemo_Moz1WB"],
    "tie_knot": ["1151_20260115_TieKnot__Moz1WB"],
    "twist_bottle_cap": ["20260122_TwistBottleCap_Moz1WB"],
    "cocktail": ["Cocktail","CupName_PromptReseach_Demo","CocktailUmbrella_PromptReseach_Demo"],
    "basketball": ["basketball"],
}


# 配置
# CONFIG_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260105_cotrain_pi05_onlytext_frontdesk_v6_ft_investor.json"
# CONFIG_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260105_cotrain_pi05_onlytext_frontdesk_v6_ft_writingdesk.json"
# CONFIG_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260106_cotrain_pi05_onlytext_frontdesk_v6new_ft_writingdesk.json"
CONFIG_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260426_cotrain_inve_writ_wo_dual_pp_correct_prompt.json"


# CONFIG_JSON = "/mnt/vepfs01/output/yifeng/resources/frontdesk/1214_cotrain_pi05_onlytext_onlyfrontdesk_v6_adddual_fix_english_debug.json"

BASE_PATH = "/mnt/vepfs01/output/yifeng/resources/frontdesk"
OUTPUT_CSV = "/mnt/vepfs01/output/yifeng/resources/frontdesk/20260426_cotrain_inve_writ_wo_dual_pp_correct_prompt.csv"


def load_config(config_path: str) -> dict:
    """加载配置JSON文件"""
    with open(config_path, 'r') as f:
        return json.load(f)


def get_total_frames(dataset_path: str) -> int:
    """获取数据集的total_frames"""
    info_path = os.path.join(dataset_path, "meta", "info.json")
    if not os.path.exists(info_path):
        print(f"警告: 找不到info.json: {info_path}")
        return 0

    try:
        with open(info_path, 'r') as f:
            info = json.load(f)
        return info.get("total_frames", 0)
    except Exception as e:
        print(f"错误: 读取 {info_path} 失败: {e}")
        return 0


def analyze_datasets(config: dict, base_path: str):
    """分析数据集的采样比例和帧数"""

    # 计算权重总和
    total_weight = sum(config.values())

    # 第一遍：收集所有数据集的帧数和权重，计算加权帧数总和
    all_datasets = []
    for dataset_key, weight in config.items():
        dataset_path = os.path.join(base_path, dataset_key)
        frames = get_total_frames(dataset_path)
        weighted_frames = frames * weight  # 实际采样帧数 = 帧数 × 权重
        is_dual = dataset_key.startswith("202510_all_dual/")
        category = dataset_key.split("/")[0]
        subcategory = extract_subcategory(dataset_key)
        group = match_group(dataset_key, GROUP_RULES)  # 使用 GROUP_RULES 匹配组

        all_datasets.append({
            "name": dataset_key,
            "weight": weight,
            "frames": frames,
            "weighted_frames": weighted_frames,
            "is_dual": is_dual,
            "category": category,
            "subcategory": subcategory,
            "group": group,  # 添加组信息
        })

    # 计算总的加权帧数（用于计算实际采样帧数占比）
    total_weighted_frames = sum(ds["weighted_frames"] for ds in all_datasets)
    total_frames_all = sum(ds["frames"] for ds in all_datasets)

    # 为每个数据集添加实际采样帧数占比
    for ds in all_datasets:
        ds["weighted_frame_ratio"] = ds["weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0
        ds["weight_ratio"] = ds["weight"] / total_weight
        ds["frame_ratio"] = ds["frames"] / total_frames_all if total_frames_all > 0 else 0

    # 分组统计
    dual_datasets = [ds for ds in all_datasets if ds["is_dual"]]
    other_datasets = [ds for ds in all_datasets if not ds["is_dual"]]

    # 统计详细信息
    results = {
        "202510_all_dual": {
            "datasets": dual_datasets,
            "total_weight": sum(ds["weight"] for ds in dual_datasets),
            "total_frames": sum(ds["frames"] for ds in dual_datasets),
            "total_weighted_frames": sum(ds["weighted_frames"] for ds in dual_datasets),
        },
        "other": {
            "datasets": other_datasets,
            "total_weight": sum(ds["weight"] for ds in other_datasets),
            "total_frames": sum(ds["frames"] for ds in other_datasets),
            "total_weighted_frames": sum(ds["weighted_frames"] for ds in other_datasets),
        }
    }

    print("=" * 130)
    print("详细统计 - 202510_all_dual 数据集")
    print("=" * 130)
    print(f"{'数据集名称':<60} {'权重':>8} {'权重占比':>10} {'帧数':>12} {'帧数占比':>10} {'加权帧数':>15} {'实际采样占比':>12}")
    print("-" * 130)

    for ds in sorted(dual_datasets, key=lambda x: x["name"]):
        print(f"{ds['name']:<60} {ds['weight']:>8.4f} {ds['weight_ratio']*100:>9.2f}% {ds['frames']:>12,} "
              f"{ds['frame_ratio']*100:>9.2f}% {ds['weighted_frames']:>15,.0f} {ds['weighted_frame_ratio']*100:>11.4f}%")

    print()
    print("=" * 130)
    print("详细统计 - 其他数据集")
    print("=" * 130)
    print(f"{'数据集名称':<60} {'权重':>8} {'权重占比':>10} {'帧数':>12} {'帧数占比':>10} {'加权帧数':>15} {'实际采样占比':>12}")
    print("-" * 130)

    for ds in sorted(other_datasets, key=lambda x: x["name"]):
        print(f"{ds['name']:<60} {ds['weight']:>8.4f} {ds['weight_ratio']*100:>9.2f}% {ds['frames']:>12,} "
              f"{ds['frame_ratio']*100:>9.2f}% {ds['weighted_frames']:>15,.0f} {ds['weighted_frame_ratio']*100:>11.4f}%")

    # 汇总统计
    print()
    print("=" * 130)
    print("汇总统计")
    print("=" * 130)
    print()

    dual_weight_ratio = results["202510_all_dual"]["total_weight"] / total_weight
    dual_frame_ratio = results["202510_all_dual"]["total_frames"] / total_frames_all if total_frames_all > 0 else 0
    dual_weighted_frame_ratio = results["202510_all_dual"]["total_weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0

    other_weight_ratio = results["other"]["total_weight"] / total_weight
    other_frame_ratio = results["other"]["total_frames"] / total_frames_all if total_frames_all > 0 else 0
    other_weighted_frame_ratio = results["other"]["total_weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0

    print(f"{'分类':<20} {'数据集数':>10} {'权重和':>12} {'权重占比':>12} {'帧数':>18} {'帧数占比':>12} {'加权帧数':>18} {'实际采样占比':>14}")
    print("-" * 130)

    print(f"{'202510_all_dual':<20} {len(dual_datasets):>10} {results['202510_all_dual']['total_weight']:>12.4f} "
          f"{dual_weight_ratio*100:>11.2f}% {results['202510_all_dual']['total_frames']:>18,} {dual_frame_ratio*100:>11.2f}% "
          f"{results['202510_all_dual']['total_weighted_frames']:>18,.0f} {dual_weighted_frame_ratio*100:>13.2f}%")

    print(f"{'其他数据':<20} {len(other_datasets):>10} {results['other']['total_weight']:>12.4f} "
          f"{other_weight_ratio*100:>11.2f}% {results['other']['total_frames']:>18,} {other_frame_ratio*100:>11.2f}% "
          f"{results['other']['total_weighted_frames']:>18,.0f} {other_weighted_frame_ratio*100:>13.2f}%")

    print("-" * 130)
    print(f"{'总计':<20} {len(all_datasets):>10} {total_weight:>12.4f} "
          f"{'100.00':>11}% {total_frames_all:>18,} {'100.00':>11}% "
          f"{total_weighted_frames:>18,.0f} {'100.00':>13}%")

    print()
    print("=" * 130)
    print("按主类别分组统计")
    print("=" * 130)

    # 按主类别分组
    category_stats = defaultdict(lambda: {"weight": 0, "frames": 0, "weighted_frames": 0, "count": 0})

    for ds in all_datasets:
        category_stats[ds["category"]]["weight"] += ds["weight"]
        category_stats[ds["category"]]["frames"] += ds["frames"]
        category_stats[ds["category"]]["weighted_frames"] += ds["weighted_frames"]
        category_stats[ds["category"]]["count"] += 1

    print()
    print(f"{'类别':<45} {'数据集数':>8} {'权重和':>10} {'权重占比':>10} {'帧数':>15} {'帧数占比':>10} {'加权帧数':>15} {'实际采样占比':>12}")
    print("-" * 130)

    for category in sorted(category_stats.keys()):
        stats = category_stats[category]
        weight_ratio = stats["weight"] / total_weight
        frame_ratio = stats["frames"] / total_frames_all if total_frames_all > 0 else 0
        weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0

        print(f"{category:<45} {stats['count']:>8} {stats['weight']:>10.4f} "
              f"{weight_ratio*100:>9.2f}% {stats['frames']:>15,} {frame_ratio*100:>9.2f}% "
              f"{stats['weighted_frames']:>15,.0f} {weighted_frame_ratio*100:>11.2f}%")

    # 按 GROUP_RULES 组分组统计
    group_stats = defaultdict(lambda: {"weight": 0, "frames": 0, "weighted_frames": 0, "count": 0, "datasets": []})

    for ds in all_datasets:
        group_stats[ds["group"]]["weight"] += ds["weight"]
        group_stats[ds["group"]]["frames"] += ds["frames"]
        group_stats[ds["group"]]["weighted_frames"] += ds["weighted_frames"]
        group_stats[ds["group"]]["count"] += 1
        group_stats[ds["group"]]["datasets"].append(ds["name"])

    print()
    print("=" * 150)
    print("按 GROUP_RULES 组分组统计")
    print("=" * 150)
    print()
    print(f"{'组名':<40} {'数据集数':>8} {'权重和':>10} {'权重占比':>10} {'帧数':>15} {'帧数占比':>10} {'加权帧数':>15} {'实际采样占比':>12}")
    print("-" * 150)

    for group_name in sorted(group_stats.keys()):
        stats = group_stats[group_name]
        weight_ratio = stats["weight"] / total_weight
        frame_ratio = stats["frames"] / total_frames_all if total_frames_all > 0 else 0
        weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0

        print(f"{group_name:<40} {stats['count']:>8} {stats['weight']:>10.4f} "
              f"{weight_ratio*100:>9.2f}% {stats['frames']:>15,} {frame_ratio*100:>9.2f}% "
              f"{stats['weighted_frames']:>15,.0f} {weighted_frame_ratio*100:>11.2f}%")

    # 按子类别分组统计（保留原有功能）
    subcategory_stats = defaultdict(lambda: {"weight": 0, "frames": 0, "weighted_frames": 0, "count": 0})

    for ds in all_datasets:
        subcategory_stats[ds["subcategory"]]["weight"] += ds["weight"]
        subcategory_stats[ds["subcategory"]]["frames"] += ds["frames"]
        subcategory_stats[ds["subcategory"]]["weighted_frames"] += ds["weighted_frames"]
        subcategory_stats[ds["subcategory"]]["count"] += 1

    print()
    print("=" * 150)
    print("按子类别分组统计（合并机器人ID和dataset子目录）")
    print("=" * 150)
    print()
    print(f"{'子类别':<80} {'数据集数':>8} {'权重和':>10} {'权重占比':>10} {'帧数':>15} {'帧数占比':>10} {'加权帧数':>15} {'实际采样占比':>12}")
    print("-" * 150)

    for subcategory in sorted(subcategory_stats.keys()):
        stats = subcategory_stats[subcategory]
        weight_ratio = stats["weight"] / total_weight
        frame_ratio = stats["frames"] / total_frames_all if total_frames_all > 0 else 0
        weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames if total_weighted_frames > 0 else 0

        print(f"{subcategory:<80} {stats['count']:>8} {stats['weight']:>10.4f} "
              f"{weight_ratio*100:>9.2f}% {stats['frames']:>15,} {frame_ratio*100:>9.2f}% "
              f"{stats['weighted_frames']:>15,.0f} {weighted_frame_ratio*100:>11.2f}%")

    # 添加汇总信息到results
    results["summary"] = {
        "dual": {
            "count": len(dual_datasets),
            "total_weight": results["202510_all_dual"]["total_weight"],
            "weight_ratio": dual_weight_ratio,
            "total_frames": results["202510_all_dual"]["total_frames"],
            "frame_ratio": dual_frame_ratio,
            "total_weighted_frames": results["202510_all_dual"]["total_weighted_frames"],
            "weighted_frame_ratio": dual_weighted_frame_ratio,
        },
        "other": {
            "count": len(other_datasets),
            "total_weight": results["other"]["total_weight"],
            "weight_ratio": other_weight_ratio,
            "total_frames": results["other"]["total_frames"],
            "frame_ratio": other_frame_ratio,
            "total_weighted_frames": results["other"]["total_weighted_frames"],
            "weighted_frame_ratio": other_weighted_frame_ratio,
        },
        "total_weight": total_weight,
        "total_frames": total_frames_all,
        "total_weighted_frames": total_weighted_frames,
    }
    results["category_stats"] = dict(category_stats)
    results["group_stats"] = {k: {kk: vv for kk, vv in v.items() if kk != "datasets"} for k, v in group_stats.items()}  # 不保存 datasets 列表到结果
    results["subcategory_stats"] = dict(subcategory_stats)

    return results


def save_to_csv(results: dict, output_path: str):
    """保存分析结果到CSV文件"""
    summary = results["summary"]
    total_weight = summary["total_weight"]
    total_frames = summary["total_frames"]
    total_weighted_frames = summary["total_weighted_frames"]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig 添加BOM让Excel正确识别
        writer = csv.writer(f)

        # ===== 详细数据集统计 =====
        writer.writerow(["=" * 20 + " 详细数据集统计 " + "=" * 20])
        writer.writerow(["数据集名称", "分类", "组名", "权重", "权重占比(%)", "帧数", "帧数占比(%)", "加权帧数(帧数×权重)", "实际采样占比(%)"])

        # 202510_all_dual 数据集
        for ds in sorted(results["202510_all_dual"]["datasets"], key=lambda x: x["name"]):
            writer.writerow([
                ds["name"],
                "202510_all_dual",
                ds.get("group", "_other"),
                f"{ds['weight']:.6f}",
                f"{ds['weight_ratio'] * 100:.4f}",
                ds["frames"],
                f"{ds['frame_ratio'] * 100:.4f}",
                f"{ds['weighted_frames']:.0f}",
                f"{ds['weighted_frame_ratio'] * 100:.4f}"
            ])

        # 其他数据集
        for ds in sorted(results["other"]["datasets"], key=lambda x: x["name"]):
            writer.writerow([
                ds["name"],
                "其他数据",
                ds.get("group", "_other"),
                f"{ds['weight']:.6f}",
                f"{ds['weight_ratio'] * 100:.4f}",
                ds["frames"],
                f"{ds['frame_ratio'] * 100:.4f}",
                f"{ds['weighted_frames']:.0f}",
                f"{ds['weighted_frame_ratio'] * 100:.4f}"
            ])

        writer.writerow([])  # 空行

        # ===== 汇总统计 =====
        writer.writerow(["=" * 20 + " 汇总统计 " + "=" * 20])
        writer.writerow(["分类", "数据集数量", "权重和", "权重占比(%)", "帧数", "帧数占比(%)", "加权帧数", "实际采样占比(%)"])

        writer.writerow([
            "202510_all_dual",
            summary["dual"]["count"],
            f"{summary['dual']['total_weight']:.4f}",
            f"{summary['dual']['weight_ratio'] * 100:.2f}",
            summary["dual"]["total_frames"],
            f"{summary['dual']['frame_ratio'] * 100:.2f}",
            f"{summary['dual']['total_weighted_frames']:.0f}",
            f"{summary['dual']['weighted_frame_ratio'] * 100:.2f}"
        ])
        writer.writerow([
            "其他数据",
            summary["other"]["count"],
            f"{summary['other']['total_weight']:.4f}",
            f"{summary['other']['weight_ratio'] * 100:.2f}",
            summary["other"]["total_frames"],
            f"{summary['other']['frame_ratio'] * 100:.2f}",
            f"{summary['other']['total_weighted_frames']:.0f}",
            f"{summary['other']['weighted_frame_ratio'] * 100:.2f}"
        ])
        writer.writerow([
            "总计",
            summary["dual"]["count"] + summary["other"]["count"],
            f"{summary['total_weight']:.4f}",
            "100.00",
            summary["total_frames"],
            "100.00",
            f"{summary['total_weighted_frames']:.0f}",
            "100.00"
        ])

        writer.writerow([])  # 空行

        # ===== 按主类别分组统计 =====
        writer.writerow(["=" * 20 + " 按主类别分组统计 " + "=" * 20])
        writer.writerow(["类别", "数据集数量", "权重和", "权重占比(%)", "帧数", "帧数占比(%)", "加权帧数", "实际采样占比(%)"])

        for category in sorted(results["category_stats"].keys()):
            stats = results["category_stats"][category]
            weight_ratio = stats["weight"] / total_weight * 100
            frame_ratio = stats["frames"] / total_frames * 100 if total_frames > 0 else 0
            weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames * 100 if total_weighted_frames > 0 else 0
            writer.writerow([
                category,
                stats["count"],
                f"{stats['weight']:.4f}",
                f"{weight_ratio:.2f}",
                stats["frames"],
                f"{frame_ratio:.2f}",
                f"{stats['weighted_frames']:.0f}",
                f"{weighted_frame_ratio:.2f}"
            ])

        writer.writerow([])  # 空行

        # ===== 按 GROUP_RULES 组分组统计 =====
        writer.writerow(["=" * 20 + " 按 GROUP_RULES 组分组统计 " + "=" * 20])
        writer.writerow(["组名", "数据集数量", "权重和", "权重占比(%)", "帧数", "帧数占比(%)", "加权帧数", "实际采样占比(%)"])

        for group_name in sorted(results["group_stats"].keys()):
            stats = results["group_stats"][group_name]
            weight_ratio = stats["weight"] / total_weight * 100
            frame_ratio = stats["frames"] / total_frames * 100 if total_frames > 0 else 0
            weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames * 100 if total_weighted_frames > 0 else 0
            writer.writerow([
                group_name,
                stats["count"],
                f"{stats['weight']:.4f}",
                f"{weight_ratio:.2f}",
                stats["frames"],
                f"{frame_ratio:.2f}",
                f"{stats['weighted_frames']:.0f}",
                f"{weighted_frame_ratio:.2f}"
            ])

        writer.writerow([])  # 空行

        # ===== 按子类别分组统计 =====
        writer.writerow(["=" * 20 + " 按子类别分组统计（合并机器人ID和dataset子目录） " + "=" * 20])
        writer.writerow(["子类别", "数据集数量", "权重和", "权重占比(%)", "帧数", "帧数占比(%)", "加权帧数", "实际采样占比(%)"])

        for subcategory in sorted(results["subcategory_stats"].keys()):
            stats = results["subcategory_stats"][subcategory]
            weight_ratio = stats["weight"] / total_weight * 100
            frame_ratio = stats["frames"] / total_frames * 100 if total_frames > 0 else 0
            weighted_frame_ratio = stats["weighted_frames"] / total_weighted_frames * 100 if total_weighted_frames > 0 else 0
            writer.writerow([
                subcategory,
                stats["count"],
                f"{stats['weight']:.4f}",
                f"{weight_ratio:.2f}",
                stats["frames"],
                f"{frame_ratio:.2f}",
                f"{stats['weighted_frames']:.0f}",
                f"{weighted_frame_ratio:.2f}"
            ])

    print(f"\n结果已保存到: {output_path}")


def main():
    print("加载配置文件...")
    config = load_config(CONFIG_JSON)
    print(f"共加载 {len(config)} 个数据集配置")
    print()

    results = analyze_datasets(config, BASE_PATH)

    # 保存到CSV
    save_to_csv(results, OUTPUT_CSV)

    print()
    print("=" * 130)
    print("分析完成!")
    print("=" * 130)


if __name__ == "__main__":
    main()
