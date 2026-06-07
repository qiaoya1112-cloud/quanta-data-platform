#!/usr/bin/env python3
"""
    python dataset_statistics.py --input <json_file> [--output <csv_file>]
"""

import json
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import glob
import os
from tqdm import tqdm


BASE_DIR = Path("/mnt/vepfs01/output/yifeng/resources/frontdesk")

# 参考 adjust_sampling_ratio.py, 可加
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
                        "1165_20260116_DrawerOpened_PickPlaceEverythingWithBookshelf_WritingDesk_FrontDeskDemo_Moz1WB"],
    "writing_desk_scoop": ["1014_20251228_ScoopNuts","1076_20260109_ScoopNutsHuman_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1077_20260109_ScoopNuts_WritingDesk_FrontDeskDemo_Moz1WB","1090_20260112_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1168_20260116_DrawerOpened_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB",
                            "1239_20260125_ScoopNutsTwoHands_WritingDesk_FrontDeskDemo_Moz1WB"],
    "writing_desk_penholder": ["1015_20251228_PenHolder"],
    "writing_desk_bookwithbookend": ["1028_20251231_BookWithBookend_VisualPrompt","20251212_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "20251225_Book_VisualPrompt_NewWritingDesk_FrontDeskDemo_Moz1WB","20251228_Book_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1138_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1146_20260114_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1166_20260116_DrawerOpened_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1186_20260119_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB",
                                    "1215_20260122_BookWithBookend_VisualPrompt_WritingDesk_FrontDeskDemo_Moz1WB"],
    "dagger_book": ["1073_20260109_writingdesk_v1_book_WBWB_dagger","1170_20260115_writingdesk_v1_takebook_WBWB_dagger"],
    "dagger_pp": ["1078_20260109_writingdesk_v1_pickbowlplate_WBWB_dagger"],
    "scoop_tea": ["20251216_ScoopTea_FrontDeskDemo_Moz1WB"],
    "AdjustBowlPosition": ["1091_20260112_AdjustBowlPosition_WritingDesk_FrontDeskDemo"],
    "WipeSpillArea": ["1098_20260112_WipeSpillArea_WritingDesk_FrontDeskDemo"],
    "PickStackedBowls": ["1099_20260112_PickStackedBowls_WritingDesk_FrontDeskDemo"],
    "PrepareForSnack": ["20251218_PrepareForSnack_FrontDeskDemo_Moz1WB"],
    "PenHolder": ["20251218_PenHolder_FrontDeskDemo_Moz1WB"],
    "tie_knot": ["1151_20260115_TieKnot__Moz1WB"],

}

FPS = 30


def get_task_folder(dataset_path: str) -> str:
    """
    获取数据集的 task 文件夹路径（不包含 dataset_xxx 子文件夹）

    例如:
    - "writingdesk_0117/xxx/dataset_0_30_xxx" -> "writingdesk_0117/xxx"
    - "v6_FrontDeskDemo/xxx" -> "v6_FrontDeskDemo/xxx"
    """
    parts = dataset_path.split('/')
    if parts[-1].startswith('dataset_'):
        return '/'.join(parts[:-1])
    return dataset_path


def load_info_json(dataset_path: str) -> Dict[str, Any]:
    """加载数据集的 info.json"""
    info_path = BASE_DIR / dataset_path / "meta" / "info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"找不到 info.json: {info_path}")
    with open(info_path, 'r') as f:
        return json.load(f)


def load_tasks_jsonl(dataset_path: str) -> Dict[int, str]:
    """
    加载数据集的 tasks.jsonl，返回 {task_index: task_prompt} 映射
    """
    tasks_path = BASE_DIR / dataset_path / "meta" / "tasks.jsonl"
    if not tasks_path.exists():
        raise FileNotFoundError(f"找不到 tasks.jsonl: {tasks_path}")

    tasks = {}
    with open(tasks_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                tasks[data['task_index']] = data['task']
    return tasks


def load_episodes_jsonl(dataset_path: str) -> List[Dict[str, Any]]:
    """加载 episodes.jsonl"""
    episodes_path = BASE_DIR / dataset_path / "meta" / "episodes.jsonl"
    if not episodes_path.exists():
        raise FileNotFoundError(f"找不到 episodes.jsonl: {episodes_path}")

    episodes = []
    with open(episodes_path, 'r') as f:
        for line in f:
            if line.strip():
                episodes.append(json.loads(line))
    return episodes


def get_episode_recording_ids(dataset_path: str) -> Dict[int, int]:
    """
    从 episodes.jsonl 获取 episode_index -> recording_id 的映射
    """
    episodes_path = BASE_DIR / dataset_path / "meta" / "episodes.jsonl"
    if not episodes_path.exists():
        return {}

    episode_to_recording = {}
    with open(episodes_path, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                episode_idx = data.get('episode_index')
                # recording_id 在 annotation 字段中
                annotation = data.get('annotation', {})
                if annotation:
                    recording_id = annotation.get('recording_id')
                    if recording_id is not None:
                        episode_to_recording[episode_idx] = recording_id
    return episode_to_recording


def get_task_recording_ids_from_parquet(dataset_path: str, tasks: Dict[int, str], episode_to_recording: Dict[int, int]) -> Dict[str, List[int]]:
    """
    从 parquet 文件统计每个 task_prompt 对应的 recording_id 列表
    返回 {task_prompt: [recording_id1, recording_id2, ...]}
    """
    data_dir = BASE_DIR / dataset_path / "data"
    if not data_dir.exists():
        return {}

    # 建立 episode_index -> set of task_indices 的映射（一个 episode 可能包含多个 task）
    episode_to_tasks = defaultdict(set)

    for chunk_dir in data_dir.glob("chunk-*"):
        for parquet_file in chunk_dir.glob("episode_*.parquet"):
            try:
                df = pd.read_parquet(parquet_file, columns=['episode_index', 'task_index'])
                if not df.empty:
                    episode_idx = int(df['episode_index'].iloc[0])
                    # 收集该 episode 中所有出现的 task_index
                    unique_task_indices = df['task_index'].unique()
                    for task_idx in unique_task_indices:
                        episode_to_tasks[episode_idx].add(int(task_idx))
            except Exception:
                pass

    # 建立 task_prompt -> recording_ids 的映射
    task_to_recordings = defaultdict(set)

    for episode_idx, task_indices in episode_to_tasks.items():
        recording_id = episode_to_recording.get(episode_idx)
        if recording_id is not None:
            for task_idx in task_indices:
                prompt = tasks.get(task_idx, f"unknown_{task_idx}")
                task_to_recordings[prompt].add(recording_id)

    # 转换为排序后的列表
    return {k: sorted(list(v)) for k, v in task_to_recordings.items()}


def get_task_frames_from_parquet(dataset_path: str) -> Dict[int, int]:
    """
    从 parquet 文件统计每个 task_index 的帧数
    返回 {task_index: frame_count}
    """
    data_dir = BASE_DIR / dataset_path / "data"
    if not data_dir.exists():
        return {}

    task_frames = defaultdict(int)

    # 遍历所有 parquet 文件
    for chunk_dir in data_dir.glob("chunk-*"):
        for parquet_file in chunk_dir.glob("episode_*.parquet"):
            try:
                df = pd.read_parquet(parquet_file, columns=['task_index'])
                # 统计每个 task_index 的帧数
                counts = df['task_index'].value_counts()
                for task_idx, count in counts.items():
                    task_frames[int(task_idx)] += count
            except Exception as e:
                print(f"警告: 读取 {parquet_file} 失败: {e}")

    return dict(task_frames)


def get_group_for_dataset(dataset_path: str) -> str:
    """根据 GROUP_RULES 获取数据集所属的组"""
    for group_name, keywords in GROUP_RULES.items():
        if isinstance(keywords, str):
            keywords = [keywords]
        if any(kw in dataset_path for kw in keywords):
            return group_name
    return "_other"


def frames_to_hours(frames: int, fps: int = FPS) -> float:
    """将帧数转换为小时数"""
    return frames / fps / 3600


def frames_to_time_str(frames: int, fps: int = FPS) -> str:
    """将帧数转换为时间字符串 (HH:MM:SS)"""
    total_seconds = frames / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def collect_dataset_stats(dataset_paths: List[str]) -> Tuple[Dict, Dict]:
    """
    收集所有数据集的统计信息

    Returns:
        task_folder_stats: {task_folder: {
            'total_frames': int,
            'subdatasets': [path1, path2, ...],
            'task_prompts': {task_prompt: frame_count, ...},
            'task_recording_ids': {task_prompt: [recording_id1, ...], ...}
        }}

        dataset_stats: {dataset_path: {
            'total_frames': int,
            'task_prompts': {task_prompt: frame_count, ...},
            'task_recording_ids': {task_prompt: [recording_id1, ...], ...}
        }}
    """
    # 按 task 文件夹分组
    task_folder_to_datasets = defaultdict(list)
    for path in dataset_paths:
        task_folder = get_task_folder(path)
        task_folder_to_datasets[task_folder].append(path)

    task_folder_stats = {}
    dataset_stats = {}

    total_datasets = len(dataset_paths)

    pbar = tqdm(total=total_datasets, desc="处理数据集", unit="个")

    for task_folder, datasets in task_folder_to_datasets.items():
        folder_total_frames = 0
        folder_task_prompts = defaultdict(int)
        folder_task_recording_ids = defaultdict(set)

        for dataset_path in datasets:
            pbar.set_postfix_str(f"{dataset_path[:50]}...")
            try:
                # 加载 info.json 获取总帧数
                info = load_info_json(dataset_path)
                total_frames = info.get('total_frames', 0)

                # 加载 tasks.jsonl 获取 task prompt 映射
                tasks = load_tasks_jsonl(dataset_path)

                # 从 parquet 获取每个 task 的帧数
                task_frames = get_task_frames_from_parquet(dataset_path)

                # 获取 episode -> recording_id 映射
                episode_to_recording = get_episode_recording_ids(dataset_path)

                # 获取 task_prompt -> recording_ids 映射
                task_recording_ids = get_task_recording_ids_from_parquet(
                    dataset_path, tasks, episode_to_recording
                )

                # 转换 task_index 到 task_prompt
                task_prompts = {}
                for task_idx, frame_count in task_frames.items():
                    prompt = tasks.get(task_idx, f"unknown_{task_idx}")
                    task_prompts[prompt] = task_prompts.get(prompt, 0) + frame_count

                # 保存单个数据集统计
                dataset_stats[dataset_path] = {
                    'total_frames': total_frames,
                    'task_prompts': task_prompts,
                    'task_recording_ids': task_recording_ids
                }

                # 累加到 task 文件夹统计
                folder_total_frames += total_frames
                for prompt, frames in task_prompts.items():
                    folder_task_prompts[prompt] += frames

                # 合并 recording_ids
                for prompt, rec_ids in task_recording_ids.items():
                    folder_task_recording_ids[prompt].update(rec_ids)

            except Exception as e:
                tqdm.write(f"警告: 处理 {dataset_path} 失败 - {e}")

            pbar.update(1)

        task_folder_stats[task_folder] = {
            'total_frames': folder_total_frames,
            'subdatasets': datasets,
            'task_prompts': dict(folder_task_prompts),
            'task_recording_ids': {k: sorted(list(v)) for k, v in folder_task_recording_ids.items()}
        }

    pbar.close()
    return task_folder_stats, dataset_stats


def generate_csv_report(
    task_folder_stats: Dict,
    dataset_stats: Dict,
    output_path: str = None
) -> pd.DataFrame:
    """
    生成 CSV 报告

    CSV 格式:
    - group: 分组名称
    - task_folder: task 文件夹路径
    - subdataset: 子数据集路径（如果有的话）
    - total_frames: 总帧数
    - hours: 小时数
    - duration: 时长 (HH:MM:SS)
    - task_prompt: task prompt 名称
    - prompt_frames: 该 prompt 的帧数
    - prompt_ratio: 该 prompt 在当前 task 文件夹中的占比
    - recording_ids: 该 prompt 对应的 recording ID 列表
    """
    rows = []

    # 按组分类 task 文件夹
    group_folders = defaultdict(list)
    for task_folder in task_folder_stats.keys():
        group = get_group_for_dataset(task_folder)
        group_folders[group].append(task_folder)

    # 按组名排序
    sorted_groups = sorted(group_folders.keys(), key=lambda x: (x == "_other", x))

    for group in sorted_groups:
        folders = sorted(group_folders[group])

        for task_folder in folders:
            stats = task_folder_stats[task_folder]
            total_frames = stats['total_frames']
            task_prompts = stats['task_prompts']
            subdatasets = stats['subdatasets']
            task_recording_ids = stats.get('task_recording_ids', {})

            hours = frames_to_hours(total_frames)
            duration = frames_to_time_str(total_frames)

            # 计算每个 prompt 的占比
            sorted_prompts = sorted(task_prompts.items(), key=lambda x: -x[1])

            # 如果没有 task prompt 信息，仍然输出一行基本信息
            if not sorted_prompts:
                rows.append({
                    'group': group,
                    'task_folder': task_folder,
                    'subdataset_count': len(subdatasets),
                    'subdatasets': ', '.join(subdatasets) if len(subdatasets) > 1 else '',
                    'total_frames': total_frames,
                    'hours': round(hours, 4),
                    'duration': duration,
                    'task_prompt': '',
                    'prompt_frames': 0,
                    'prompt_ratio': 0.0,
                    'recording_ids': '',
                    'recording_count': 0
                })
            else:
                for prompt, prompt_frames in sorted_prompts:
                    ratio = prompt_frames / total_frames if total_frames > 0 else 0
                    rec_ids = task_recording_ids.get(prompt, [])
                    rows.append({
                        'group': group,
                        'task_folder': task_folder,
                        'subdataset_count': len(subdatasets),
                        'subdatasets': ', '.join(subdatasets) if len(subdatasets) > 1 else '',
                        'total_frames': total_frames,
                        'hours': round(hours, 4),
                        'duration': duration,
                        'task_prompt': prompt,
                        'prompt_frames': prompt_frames,
                        'prompt_ratio': round(ratio, 4),
                        'recording_ids': ', '.join(str(r) for r in rec_ids),
                        'recording_count': len(rec_ids)
                    })

    df = pd.DataFrame(rows)

    if output_path:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\nCSV 报告已保存到: {output_path}")

    return df


def generate_summary_report(task_folder_stats: Dict, output_path: str = None) -> pd.DataFrame:
    """
    生成汇总报告（每个 task 文件夹一行）
    """
    rows = []

    # 按组分类 task 文件夹
    group_folders = defaultdict(list)
    for task_folder in task_folder_stats.keys():
        group = get_group_for_dataset(task_folder)
        group_folders[group].append(task_folder)

    # 按组名排序
    sorted_groups = sorted(group_folders.keys(), key=lambda x: (x == "_other", x))

    total_all_frames = 0
    total_all_hours = 0

    for group in sorted_groups:
        folders = sorted(group_folders[group])
        group_frames = 0

        for task_folder in folders:
            stats = task_folder_stats[task_folder]
            total_frames = stats['total_frames']
            hours = frames_to_hours(total_frames)
            duration = frames_to_time_str(total_frames)
            subdatasets = stats['subdatasets']
            task_prompts = stats['task_prompts']

            group_frames += total_frames
            total_all_frames += total_frames
            total_all_hours += hours

            rows.append({
                'group': group,
                'task_folder': task_folder,
                'subdataset_count': len(subdatasets),
                'total_frames': total_frames,
                'hours': round(hours, 4),
                'duration': duration,
                'num_prompts': len(task_prompts),
                'top_prompt': max(task_prompts.items(), key=lambda x: x[1])[0] if task_prompts else ''
            })

        # 添加组汇总行
        group_hours = frames_to_hours(group_frames)
        rows.append({
            'group': f"=== {group} 汇总 ===",
            'task_folder': '',
            'subdataset_count': '',
            'total_frames': group_frames,
            'hours': round(group_hours, 4),
            'duration': frames_to_time_str(group_frames),
            'num_prompts': '',
            'top_prompt': ''
        })

    # 添加总汇总行
    rows.append({
        'group': '=== 总计 ===',
        'task_folder': '',
        'subdataset_count': '',
        'total_frames': total_all_frames,
        'hours': round(total_all_hours, 4),
        'duration': frames_to_time_str(total_all_frames),
        'num_prompts': '',
        'top_prompt': ''
    })

    df = pd.DataFrame(rows)

    if output_path:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"汇总报告已保存到: {output_path}")

    return df


def print_statistics_summary(task_folder_stats: Dict, dataset_stats: Dict):
    """打印统计摘要到控制台"""
    print("\n" + "=" * 80)
    print("数据集统计摘要")
    print("=" * 80)

    # 按组统计
    group_stats = defaultdict(lambda: {'frames': 0, 'folders': 0, 'datasets': 0})

    for task_folder, stats in task_folder_stats.items():
        group = get_group_for_dataset(task_folder)
        group_stats[group]['frames'] += stats['total_frames']
        group_stats[group]['folders'] += 1
        group_stats[group]['datasets'] += len(stats['subdatasets'])

    total_frames = sum(s['frames'] for s in group_stats.values())
    total_folders = sum(s['folders'] for s in group_stats.values())
    total_datasets = sum(s['datasets'] for s in group_stats.values())

    sorted_groups = sorted(group_stats.keys(), key=lambda x: (x == "_other", x))

    print(f"\n{'组名':<30} {'文件夹数':>10} {'数据集数':>10} {'帧数':>15} {'时长':>12} {'占比':>8}")
    print("-" * 85)

    for group in sorted_groups:
        s = group_stats[group]
        hours = frames_to_hours(s['frames'])
        duration = frames_to_time_str(s['frames'])
        ratio = s['frames'] / total_frames if total_frames > 0 else 0
        print(f"{group:<30} {s['folders']:>10} {s['datasets']:>10} {s['frames']:>15,} {duration:>12} {ratio:>7.2%}")

    print("-" * 85)
    total_hours = frames_to_hours(total_frames)
    total_duration = frames_to_time_str(total_frames)
    print(f"{'总计':<30} {total_folders:>10} {total_datasets:>10} {total_frames:>15,} {total_duration:>12} {'100.00%':>8}")
    print(f"\n总时长: {total_hours:.2f} 小时 ({total_duration})")


def main():
    global BASE_DIR

    parser = argparse.ArgumentParser(description='数据集统计工具')
    parser.add_argument('--input', '-i', required=True, help='输入的 JSON 文件路径')
    parser.add_argument('--output', '-o', help='输出的 CSV 文件路径（详细报告）')
    parser.add_argument('--summary', '-s', help='输出的汇总 CSV 文件路径')
    parser.add_argument('--base-dir', '-b', default=str(BASE_DIR), help='数据集根目录')

    args = parser.parse_args()

    BASE_DIR = Path(args.base_dir)

    # 加载输入 JSON
    print(f"加载输入文件: {args.input}")
    with open(args.input, 'r') as f:
        input_data = json.load(f)

    dataset_paths = list(input_data.keys())
    print(f"共 {len(dataset_paths)} 个数据集")

    # 收集统计信息
    print("\n开始收集统计信息...")
    task_folder_stats, dataset_stats = collect_dataset_stats(dataset_paths)

    # 打印摘要
    print_statistics_summary(task_folder_stats, dataset_stats)

    # 生成 CSV 报告
    if args.output:
        generate_csv_report(task_folder_stats, dataset_stats, args.output)

    if args.summary:
        generate_summary_report(task_folder_stats, args.summary)

    # 如果没有指定输出文件，默认生成一个
    if not args.output and not args.summary:
        input_path = Path(args.input)
        default_output = input_path.parent / f"{input_path.stem}_statistics.csv"
        default_summary = input_path.parent / f"{input_path.stem}_summary.csv"

        generate_csv_report(task_folder_stats, dataset_stats, str(default_output))
        generate_summary_report(task_folder_stats, str(default_summary))


if __name__ == "__main__":
    main()
