#!/usr/bin/env python3
"""
批量数据集切分工具

根据 JSON 配置文件批量切分 LeRobot 数据集为训练集和验证集。
输出两个新的 JSON 文件，分别用于训练和验证。

使用示例：
    python3 batch_split_datasets.py \
        --input-json /path/to/cotrain.json \
        --root /mnt/vepfs01/output/yifeng/resources/frontdesk \
        --train-ratio 0.9

输出：
    - {input_json}_train.json  (训练集配置)
    - {input_json}_val.json    (验证集配置)
    - 每个数据集的 _split/train 和 _split/val 目录
    在原数据集同级目录下，创建 {数据集名}_split/train 和 {数据集名}_split/val
"""

import argparse
import json
import logging
import os
import random
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

# 设置日志
logging.basicConfig(
    level=logging.WARNING,  # 默认只显示警告及以上
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 主模块显示 INFO 级别


class DatasetSplitter:
    """LeRobot数据集切分器"""

    def __init__(self, input_dir: Path, output_train_dir: Path, output_val_dir: Path, use_symlink: bool = True) -> None:
        """初始化切分器

        Args:
            input_dir: 原始数据集目录
            output_train_dir: 训练集输出目录
            output_val_dir: 验证集输出目录
            use_symlink: 是否使用软链接（默认True，节省空间）
        """
        self.input_dir = input_dir
        self.output_train_dir = output_train_dir
        self.output_val_dir = output_val_dir
        self.use_symlink = use_symlink

        # 验证输入目录
        self._validate_input_dataset()

        # 创建输出目录结构
        self._create_output_directories()

    def _validate_input_dataset(self) -> None:
        """验证输入数据集的完整性"""
        required_files = [
            "dataset.json",
            "meta/info.json",
            "meta/episodes.jsonl",
            "meta/episodes_stats.jsonl",
            "meta/tasks.jsonl",
        ]

        for file_path in required_files:
            full_path = self.input_dir / file_path
            if not full_path.exists():
                msg = f"缺少必要文件: {full_path}"
                raise FileNotFoundError(msg)

        logger.debug(f"输入数据集验证通过: {self.input_dir}")

    def _create_output_directories(self) -> None:
        """创建输出目录结构"""
        for output_dir in [self.output_train_dir, self.output_val_dir]:
            for subdir in ["meta", "data", "videos"]:
                (output_dir / subdir).mkdir(parents=True, exist_ok=True)

        logger.debug(f"创建输出目录: {self.output_train_dir}, {self.output_val_dir}")

    def split_dataset(self, train_ratio: float, seed: int = 42) -> tuple[bool, bool]:
        """切分数据集

        Args:
            train_ratio: 训练集比例 (0.0 - 1.0)
            seed: 随机种子

        Returns:
            (成功与否, val是否有数据)
        """
        random.seed(seed)
        if not (0.0 < train_ratio < 1.0):
            msg = f"训练集比例必须在 0.0 和 1.0 之间: {train_ratio}"
            raise ValueError(msg)

        logger.debug(f"开始切分数据集: {self.input_dir}，训练集比例: {train_ratio}")

        # 1. 读取原始数据集信息
        dataset_info = self._load_dataset_info()
        episodes = self._load_episodes()
        episode_stats = self._load_episode_stats()
        info = self._load_info()

        # 2. 按比例切分episodes，得到索引
        train_indices, val_indices = self._split_episodes(
            len(episodes),
            train_ratio,
        )

        logger.debug(
            f"切分结果: 训练集 {len(train_indices)} episodes, 验证集 {len(val_indices)} episodes",
        )

        # 检查 val 是否为空
        val_has_data = len(val_indices) > 0
        if not val_has_data:
            logger.warning(f"数据集 {self.input_dir.name} 只有 {len(episodes)} episodes，val 集为空，跳过 val 目录创建")

        # 3. 根据索引切分数据
        train_episodes = [episodes[i].copy() for i in train_indices]
        val_episodes = [episodes[i].copy() for i in val_indices] if val_has_data else []
        train_episode_stats = [episode_stats[i].copy() for i in train_indices]
        val_episode_stats = [episode_stats[i].copy() for i in val_indices] if val_has_data else []

        # 获取 recording_ids（如果存在）
        train_recording_ids = []
        val_recording_ids = []
        if "recording_ids" in dataset_info:
            train_recording_ids = [dataset_info["recording_ids"][i] for i in train_indices]
            val_recording_ids = [dataset_info["recording_ids"][i] for i in val_indices]

        # 重新编号 episode_index
        for i, episode in enumerate(train_episodes):
            episode["episode_index"] = i
        for i, episode in enumerate(val_episodes):
            episode["episode_index"] = i

        # 4. 处理训练集
        logger.debug("处理训练集...")
        self._process_subset(
            train_indices,
            train_episodes,
            train_episode_stats,
            info,
            self.output_train_dir,
            "train",
        )

        # 5. 处理验证集（仅当有数据时）
        if val_has_data:
            logger.debug("处理验证集...")
            self._process_subset(
                val_indices,
                val_episodes,
                val_episode_stats,
                info,
                self.output_val_dir,
                "val",
            )
        else:
            # 清理空的 val 目录
            if self.output_val_dir.exists():
                shutil.rmtree(self.output_val_dir)

        # 6. 生成切分信息文件
        split_info_files = [self.output_train_dir / "split_info.json"]
        if val_has_data:
            split_info_files.append(self.output_val_dir / "split_info.json")

        for split_info_file in split_info_files:
            self._save_split_info(
                train_ratio,
                len(episodes),
                len(train_episodes),
                len(val_episodes),
                train_recording_ids,
                val_recording_ids,
                split_info_file,
            )

        logger.debug(f"数据集切分完成: {self.input_dir}")
        return True, val_has_data

    def _load_dataset_info(self) -> dict[str, Any]:
        """加载dataset.json"""
        dataset_json_path = self.input_dir / "dataset.json"
        with open(dataset_json_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _load_episodes(self) -> list[dict[str, Any]]:
        """加载episodes.jsonl"""
        episodes = []
        episodes_file = self.input_dir / "meta" / "episodes.jsonl"
        with open(episodes_file, encoding="utf-8") as f:
            for line in f:
                episodes.append(json.loads(line.strip()))
        return episodes

    def _load_episode_stats(self) -> list[dict[str, Any]]:
        """加载episodes_stats.jsonl"""
        episode_stats = []
        stats_file = self.input_dir / "meta" / "episodes_stats.jsonl"
        with open(stats_file, encoding="utf-8") as f:
            for line in f:
                episode_stats.append(json.loads(line.strip()))
        return episode_stats

    def _load_info(self) -> dict[str, Any]:
        """加载info.json"""
        info_file = self.input_dir / "meta" / "info.json"
        with open(info_file, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    def _split_episodes(
        self,
        total_episodes: int,
        train_ratio: float,
    ) -> tuple[list[int], list[int]]:
        """随机切分episodes，生成索引列表

        Args:
            total_episodes: 总episode数量
            train_ratio: 训练集比例

        Returns:
            (train_indices, val_indices) - 训练集和验证集的原始索引列表
        """
        train_indices = []
        val_indices = []

        for i in range(total_episodes):
            if random.random() < train_ratio:
                train_indices.append(i)
            else:
                val_indices.append(i)

        return train_indices, val_indices

    def _process_subset(
        self,
        original_index: list[int],
        episodes: list[dict[str, Any]],
        episode_stats: list[dict[str, Any]],
        original_info: dict[str, Any],
        output_dir: Path,
        subset_name: str,
    ) -> None:
        """处理单个子集（训练集或验证集）"""
        # 1. 处理meta文件
        self._process_meta_files(original_index, episodes, episode_stats, original_info, output_dir, subset_name)

        # 2. 处理data文件
        # self._process_data_files(len(episodes), original_index, original_info, output_dir)#todo 取消注释

        # 3. 处理videos文件
        # self._process_video_files(len(episodes), original_index, original_info, output_dir)

    def _process_meta_files(
        self,
        original_index: list[int],
        episodes: list[dict[str, Any]],
        episode_stats: list[dict[str, Any]],
        original_info: dict[str, Any],
        output_dir: Path,
        subset_name: str,
    ) -> None:
        """处理元数据文件"""
        meta_dir = output_dir / "meta"

        # 0. 拷贝原始 dataset.json 并生成重新编号后的 dataset.json
        original_dataset_file = self.input_dir / "dataset.json"
        target_dataset_file = output_dir / "original_dataset.json"
        shutil.copy2(original_dataset_file, target_dataset_file)

        with open(original_dataset_file, encoding="utf-8") as f:
            dataset_json: dict[str, Any] = json.load(f)

        # 用 episodes 列表（已重新编号）替换 dataset.json 中的 episodes，
        # 使 episode_index 与切分后 parquet 中的值保持一致
        if "episodes" in dataset_json:
            # episodes 参数已在调用方重新编号（episode_index = 0, 1, 2, ...）
            dataset_json["episodes"] = episodes

        # 过滤 recording_ids，只保留当前子集对应的条目
        if "recording_ids" in dataset_json:
            all_recording_ids = dataset_json["recording_ids"]
            dataset_json["recording_ids"] = [all_recording_ids[i] for i in original_index]

        # 过滤并重新编号 episode_stats
        if "episode_stats" in dataset_json:
            all_episode_stats = dataset_json["episode_stats"]
            new_episode_stats = []
            for new_idx, orig_idx in enumerate(original_index):
                stat = all_episode_stats[orig_idx].copy()
                stat["episode_index"] = new_idx
                new_episode_stats.append(stat)
            dataset_json["episode_stats"] = new_episode_stats

        # 过滤并重新编号 files（按 episode index 过滤，path 中的 episode_XXXXXX 重新编号）
        if "files" in dataset_json:
            chunks_size = dataset_json.get("info", {}).get("chunks_size", 100) if isinstance(dataset_json.get("info"), dict) else 100
            # 按原始 episode index 分组
            ep_files: dict[int, list[dict]] = {}
            for file_entry in dataset_json["files"]:
                m = re.search(r"episode_(\d+)", file_entry["path"])
                if m:
                    ep_idx = int(m.group(1))
                    ep_files.setdefault(ep_idx, []).append(file_entry)

            new_files = []
            for new_idx, orig_idx in enumerate(original_index):
                new_chunk = new_idx // chunks_size
                for file_entry in ep_files.get(orig_idx, []):
                    new_entry = file_entry.copy()
                    # 替换 chunk 编号和 episode 编号
                    new_path = re.sub(
                        r"chunk-\d+",
                        f"chunk-{new_chunk:03d}",
                        file_entry["path"],
                    )
                    new_path = re.sub(
                        r"episode_\d+",
                        f"episode_{new_idx:06d}",
                        new_path,
                    )
                    new_entry["path"] = new_path
                    # download_url 中的路径也更新（如果存在）
                    if "download_url" in new_entry and new_entry["download_url"]:
                        url = new_entry["download_url"]
                        url = re.sub(r"chunk-\d+", f"chunk-{new_chunk:03d}", url)
                        url = re.sub(r"episode_\d+", f"episode_{new_idx:06d}", url)
                        new_entry["download_url"] = url
                    new_files.append(new_entry)
            dataset_json["files"] = new_files

        new_dataset_file = output_dir / "dataset.json"
        with open(new_dataset_file, "w", encoding="utf-8") as f:
            json.dump(dataset_json, f, ensure_ascii=False, indent=2)
        print(f"新的dataset.json文件 {new_dataset_file}")

        # 1. 生成episodes.jsonl
        episodes_file = meta_dir / "episodes.jsonl"
        with open(episodes_file, "w", encoding="utf-8") as f:
            for i, episode in enumerate(episodes):
                episode["episode_index"] = i
                f.write(json.dumps(episode, ensure_ascii=False) + "\n")

        # 2. 生成episodes_stats.jsonl
        stats_file = meta_dir / "episodes_stats.jsonl"
        with open(stats_file, "w", encoding="utf-8") as f:
            for i, stats in enumerate(episode_stats):
                stats["episode_index"] = i
                f.write(json.dumps(stats, ensure_ascii=False) + "\n")

        # 3. 复制tasks.jsonl
        original_tasks_file = self.input_dir / "meta" / "tasks.jsonl"
        target_tasks_file = meta_dir / "tasks.jsonl"
        shutil.copy2(original_tasks_file, target_tasks_file)

        # 4. 更新info.json
        new_info = original_info.copy()
        new_info["total_episodes"] = len(episodes)
        new_info["total_frames"] = sum(episode["length"] for episode in episodes)

        # 统计 chunk 数
        chunks_size = original_info.get("chunks_size", 100)
        total_chunks = (len(episodes) + chunks_size - 1) // chunks_size
        new_info["total_chunks"] = total_chunks

        # 统计视频数量
        input_videos_dir = self.input_dir / "videos"
        camera_names = set()
        if input_videos_dir.exists():
            for chunk_dir in input_videos_dir.glob("chunk-*"):
                for camera_dir in chunk_dir.iterdir():
                    if camera_dir.is_dir():
                        camera_names.add(camera_dir.name)
        num_cameras = len(camera_names)
        new_info["total_videos"] = len(episodes) * num_cameras

        # splits 字段
        new_info["splits"] = {subset_name: f"0:{len(episodes)}"}

        info_file = meta_dir / "info.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(new_info, f, ensure_ascii=False, indent=2)

        logger.debug(f"生成元数据文件: {meta_dir}")

    def _process_data_files(
        self,
        num_episodes: int,
        original_index: list[int],
        original_info: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """处理parquet数据文件"""
        logger.debug(f"处理 {num_episodes} 个episode的数据文件...")

        chunks_size = original_info.get("chunks_size", 100)
        global_index_counter = 0

        for new_episode_idx in range(num_episodes):
            original_episode_idx = original_index[new_episode_idx]

            # 找到原始parquet文件
            original_chunk_id = original_episode_idx // chunks_size
            original_parquet_file = (
                self.input_dir
                / "data"
                / f"chunk-{original_chunk_id:03d}"
                / f"episode_{original_episode_idx:06d}.parquet"
            )

            if not original_parquet_file.exists():
                logger.warning(f"找不到原始parquet文件: {original_parquet_file}")
                continue

            # 确定新的文件位置
            new_chunk_id = new_episode_idx // chunks_size
            new_chunk_dir = output_dir / "data" / f"chunk-{new_chunk_id:03d}"
            new_chunk_dir.mkdir(parents=True, exist_ok=True)

            new_parquet_file = new_chunk_dir / f"episode_{new_episode_idx:06d}.parquet"
            if new_parquet_file.exists():
                logger.debug(f"数据文件已存在: {new_parquet_file}")
                continue

            # 读取并更新parquet文件
            df = pd.read_parquet(original_parquet_file)

            # 更新episode_index
            df["episode_index"] = new_episode_idx

            # 更新全局index
            episode_length = len(df)
            df["index"] = range(global_index_counter, global_index_counter + episode_length)
            global_index_counter += episode_length

            # 保存新的parquet文件
            df.to_parquet(new_parquet_file, index=False)

            logger.debug(f"处理数据文件: {original_parquet_file} -> {new_parquet_file}")

    def _process_video_files(
        self,
        num_episodes: int,
        original_index: list[int],
        original_info: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """处理视频文件"""
        logger.debug(f"处理 {num_episodes} 个episode的视频文件...")

        chunks_size = original_info.get("chunks_size", 100)
        input_videos_dir = self.input_dir / "videos"

        if not input_videos_dir.exists():
            logger.warning(f"视频目录不存在: {input_videos_dir}")
            return

        # 获取所有camera名称
        camera_names = set()
        for chunk_dir in input_videos_dir.glob("chunk-*"):
            for camera_dir in chunk_dir.iterdir():
                if camera_dir.is_dir():
                    camera_names.add(camera_dir.name)

        logger.debug(f"发现相机: {sorted(camera_names)}")

        for new_episode_idx in range(num_episodes):
            original_episode_idx = original_index[new_episode_idx]

            # 确定原始和新的chunk目录
            original_chunk_id = original_episode_idx // chunks_size
            new_chunk_id = new_episode_idx // chunks_size

            original_chunk_dir = input_videos_dir / f"chunk-{original_chunk_id:03d}"
            new_chunk_dir = output_dir / "videos" / f"chunk-{new_chunk_id:03d}"

            # 为每个相机复制视频文件
            for camera_name in camera_names:
                original_camera_dir = original_chunk_dir / camera_name
                new_camera_dir = new_chunk_dir / camera_name
                new_camera_dir.mkdir(parents=True, exist_ok=True)

                # 查找原始视频文件
                original_video_pattern = f"episode_{original_episode_idx:06d}.*"
                original_video_files = list(original_camera_dir.glob(original_video_pattern))

                for original_video_file in original_video_files:
                    # 构造新的视频文件名
                    suffix = original_video_file.suffix
                    new_video_file = new_camera_dir / f"episode_{new_episode_idx:06d}{suffix}"

                    # 使用 lexists 检查（包括断开的软链接）
                    if os.path.lexists(new_video_file):
                        logger.debug(f"视频文件已存在: {new_video_file}")
                        continue

                    if self.use_symlink:
                        # 使用软链接，节省空间和时间
                        try:
                            os.symlink(original_video_file.resolve(), new_video_file)
                        except FileExistsError:
                            logger.debug(f"视频文件已存在(并发): {new_video_file}")
                            continue
                        logger.debug(f"链接视频: {original_video_file} -> {new_video_file}")
                    else:
                        # 复制视频文件
                        shutil.copy2(original_video_file, new_video_file)
                        logger.debug(f"复制视频: {original_video_file} -> {new_video_file}")

    def _save_split_info(
        self,
        train_ratio: float,
        original_total_episodes: int,
        train_episodes_count: int,
        val_episodes_count: int,
        train_recording_ids: list,
        val_recording_ids: list,
        split_info_file: Path,
    ) -> None:
        """保存切分信息"""
        split_info = {
            "train_ratio": train_ratio,
            "original_total_episodes": original_total_episodes,
            "train_episodes_count": train_episodes_count,
            "val_episodes_count": val_episodes_count,
            "train_recording_ids": train_recording_ids,
            "val_recording_ids": val_recording_ids,
        }

        with open(split_info_file, "w", encoding="utf-8") as f:
            json.dump(split_info, f, ensure_ascii=False, indent=2)

        logger.debug(f"保存切分信息: {split_info_file}")


class BatchDatasetSplitter:
    """批量数据集切分器"""

    def __init__(
        self,
        input_json: Path,
        root: Path,
        train_ratio: float,
        output_dir: Path | None = None,
        seed: int = 42,
        use_symlink: bool = True,
    ) -> None:
        """初始化批量切分器

        Args:
            input_json: 输入的 JSON 配置文件路径
            root: 数据集根目录
            train_ratio: 训练集比例
            output_dir: 输出目录（默认与输入 JSON 同目录）
            seed: 随机种子
            use_symlink: 是否使用软链接（默认True，节省空间）
        """
        self.input_json = Path(input_json)
        self.root = Path(root)
        self.train_ratio = train_ratio
        self.output_dir = Path(output_dir) if output_dir else self.input_json.parent
        self.seed = seed
        self.use_symlink = use_symlink

        # 加载配置
        self._load_config()

    def _load_config(self) -> None:
        """加载 JSON 配置文件"""
        if not self.input_json.exists():
            raise FileNotFoundError(f"输入 JSON 文件不存在: {self.input_json}")

        with open(self.input_json, encoding="utf-8") as f:
            self.config: dict[str, float] = json.load(f)

        logger.debug(f"加载配置文件: {self.input_json}，共 {len(self.config)} 个数据集")

    def split_all(self, skip_existing: bool = True) -> tuple[dict, dict]:
        """批量切分所有数据集

        Args:
            skip_existing: 是否跳过已存在的切分

        Returns:
            (train_config, val_config) - 训练集和验证集的配置字典
        """
        train_config = {}
        val_config = {}

        failed_datasets = []
        skipped_datasets = []
        processed_datasets = []

        video_mode = "复制" if not self.use_symlink else "软链接"
        print(f"开始批量切分 {len(self.config)} 个数据集，训练集比例: {self.train_ratio}，视频: {video_mode}")

        for dataset_path, weight in tqdm(self.config.items(), desc="切分数据集"):
            full_path = self.root / dataset_path

            # 构建切分后的路径
            # 输出到数据集所在目录下的 _split 子目录
            parent_dir = full_path.parent
            dataset_name = full_path.name
            split_base_dir = parent_dir / f"{dataset_name}_split"
            train_dir = split_base_dir / "train"
            val_dir = split_base_dir / "val"

            # 构建新的相对路径
            train_rel_path = str(Path(dataset_path).parent / f"{Path(dataset_path).name}_split" / "train")
            val_rel_path = str(Path(dataset_path).parent / f"{Path(dataset_path).name}_split" / "val")

            # 检查是否已存在切分
            train_exists = (train_dir / "meta" / "info.json").exists()
            val_exists = (val_dir / "meta" / "info.json").exists()
            # 额外检查 val 目录是否真的有数据
            val_has_parquet = val_exists and len(list((val_dir / "data").glob("**/*.parquet"))) > 0 if val_exists else False

            if skip_existing and train_exists:
                logger.debug(f"跳过已存在的切分: {dataset_path}")
                skipped_datasets.append(dataset_path)
                train_config[train_rel_path] = weight
                # 只有当 val 目录存在且有数据时才加入 val_config
                if val_has_parquet:
                    val_config[val_rel_path] = weight
                continue

            # 验证原始数据集存在
            if not full_path.exists():
                logger.error(f"数据集不存在: {full_path}")
                failed_datasets.append((dataset_path, "数据集不存在"))
                continue

            # 执行切分
            try:
                splitter = DatasetSplitter(full_path, train_dir, val_dir, use_symlink=self.use_symlink)
                success, val_has_data = splitter.split_dataset(self.train_ratio, self.seed)
                processed_datasets.append(dataset_path)
                train_config[train_rel_path] = weight
                # 只有当 val 有数据时才加入 val_config
                if val_has_data:
                    val_config[val_rel_path] = weight
                else:
                    logger.info(f"跳过空 val: {dataset_path} (episodes 太少)")
            except Exception as e:
                logger.error(f"切分失败 {dataset_path}: {e}")
                failed_datasets.append((dataset_path, str(e)))

        # 打印汇总信息
        print("\n" + "=" * 50)
        print("批量切分完成!")
        print(f"  ✓ 成功处理: {len(processed_datasets)} 个数据集")
        print(f"  → 跳过已存在: {len(skipped_datasets)} 个数据集")
        print(f"  ✗ 处理失败: {len(failed_datasets)} 个数据集")

        if failed_datasets:
            print("\n失败的数据集:")
            for ds, err in failed_datasets:
                print(f"  - {ds}: {err}")

        print("=" * 50)

        return train_config, val_config

    def save_output_jsons(self, train_config: dict, val_config: dict) -> tuple[Path, Path]:
        """保存输出的 JSON 文件

        Args:
            train_config: 训练集配置
            val_config: 验证集配置

        Returns:
            (train_json_path, val_json_path)
        """
        # 构建输出文件名
        input_stem = self.input_json.stem
        train_json_path = self.output_dir / f"{input_stem}_train.json"
        val_json_path = self.output_dir / f"{input_stem}_val.json"

        # 保存训练集 JSON
        with open(train_json_path, "w", encoding="utf-8") as f:
            json.dump(train_config, f, ensure_ascii=False, indent=2)

        # 保存验证集 JSON
        with open(val_json_path, "w", encoding="utf-8") as f:
            json.dump(val_config, f, ensure_ascii=False, indent=2)

        return train_json_path, val_json_path

    def run(self, skip_existing: bool = True) -> tuple[Path, Path]:
        """执行批量切分并保存结果

        Args:
            skip_existing: 是否跳过已存在的切分

        Returns:
            (train_json_path, val_json_path)
        """
        train_config, val_config = self.split_all(skip_existing)
        return self.save_output_jsons(train_config, val_config)


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="批量切分 LeRobot 数据集为训练集和验证集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 基本使用
    python3 batch_split_datasets.py \\
        --input-json /path/to/cotrain.json \\
        --root /mnt/vepfs01/output/yifeng/resources/frontdesk \\
        --train-ratio 0.9

    # 强制重新切分（不跳过已存在的）
    python3 batch_split_datasets.py \\
        --input-json /path/to/cotrain.json \\
        --root /mnt/vepfs01/output/yifeng/resources/frontdesk \\
        --train-ratio 0.9 \\
        --force

输出:
    - {input_json}_train.json  (训练集配置)
    - {input_json}_val.json    (验证集配置)
    - 每个数据集的 _split/train 和 _split/val 目录
        """,
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        required=True,
        help="输入的 JSON 配置文件路径（包含数据集路径和权重）",
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="数据集根目录",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.9,
        help="训练集比例 (0.0 - 1.0)，默认 0.9",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="输出目录（默认与输入 JSON 同目录）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子，默认 42",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新切分（不跳过已存在的切分）",
    )
    parser.add_argument(
        "--copy-video",
        action="store_true",
        help="复制视频文件而不是使用软链接（默认使用软链接）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )
    return parser.parse_args()


def main() -> None:
    """主函数"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        # 创建批量切分器并执行
        batch_splitter = BatchDatasetSplitter(
            input_json=args.input_json,
            root=args.root,
            train_ratio=args.train_ratio,
            output_dir=args.output_dir,
            seed=args.seed,
            use_symlink=not args.copy_video,
        )

        train_json, val_json = batch_splitter.run(skip_existing=not args.force)

        print("\n输出文件:")
        print(f"  训练集: {train_json}")
        print(f"  验证集: {val_json}")

    except KeyboardInterrupt:
        logger.warning("用户中断操作")
        sys.exit(1)
    except Exception:
        logger.exception("操作失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
