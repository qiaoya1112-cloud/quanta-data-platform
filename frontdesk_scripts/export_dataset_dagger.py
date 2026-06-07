#!/usr/bin/env python3
"""
LeRobot 数据集导出工具

该脚本支持从服务端导出一个或多个 collection，并合并为一个 LeRobot 数据集。

使用示例：
    # 导出单个 collection
    python export_dataset.py --collection-ids 123 --output-dir ./output --api-url https://quanta.i.spirit-ai.com

    # 导出多个 collection 并合并
    python export_dataset.py --collection-ids 123 456 789 --output-dir ./output --api-url https://quanta.i.spirit-ai.com

    # 带任务名称前缀验证
    python export_dataset.py --collection-ids 123 456 --output-dir ./output --task-name-prefix "pick_and_place"

    # 按任务ID过滤导出
    python export_dataset.py --task-ids 1 2 --output-dir ./output

    # 按采集设备序列号过滤导出
    python export_dataset.py --tasks-ids 1 --capture-devices "moz1-01" "moz1-y02" --output-dir ./output

    # 按操作员ID过滤导出
    python export_dataset.py --task-ids 1 --operators "张三" "李四" --output-dir ./output

    # 按日期范围过滤导出 (注意：to_date 是包含的，即导出到to_date的23点59分59秒)
    python export_dataset.py --task-ids 1 --from-date 2025-01-01 --to-date 2025-01-02 --output-dir ./output

    # 按精确时间点过滤导出
    python export_dataset.py --task-ids 1 --from-timestamp "2025-01-01 10:30:00" --to-timestamp "2025-01-02 15:45:30" --output-dir ./output

    # 仅导出质检不合格的数据
    python export_dataset.py --task-ids 1 --invalid-only --output-dir ./output

    # 包含未质检且未标记为采集失误的数据
    python export_dataset.py --task-ids 1 --include-unchecked --output-dir ./output

    # 指定标注版本导出
    python export_dataset.py --task-ids 123 --annotation-version 2 --output-dir ./output

    # 使用旧逻辑导出（默认使用新逻辑）
    python export_dataset.py --task-ids 1 --old --output-dir ./output
"""  # noqa: E501

import argparse
import json
import logging
import math
import shutil
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class APIDatasetExporter:
    """通过API导出LeRobot数据集"""

    def __init__(self, output_dir: Path, api_base_url: str, action_field: str = "action_english") -> None:
        """初始化导出器

        Args:
            output_dir: 输出目录路径
            api_base_url: API服务端基础URL
            action_field: 使用的动作字段名，可选 "action" 或 "action_english"
        """
        self.output_dir = output_dir
        self.api_base_url = api_base_url.rstrip("/")
        self.action_field = action_field
        self.session = requests.Session()

        # 创建目录结构
        self._create_directory_structure()

    def _create_directory_structure(self) -> None:
        """创建 LeRobot 数据集目录结构"""
        self.meta_dir = self.output_dir / "meta"
        self.data_dir = self.output_dir / "data"
        self.videos_dir = self.output_dir / "videos"

        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"创建目录结构: {self.output_dir}")

    def export_collections(
        self,
        collection_ids: list[int],
        task_ids: list[int] | None = None,
        capture_devices: list[str] | None = None,
        operators: list[str] | None = None,
        auto_fix_indices: bool = True,
        task_name_prefix: str = "",
        use_tos_internal_endpoint: bool = False,
        fetch_annotations: bool = False,
        max_retry_count: int = 3,
        from_date: date | None = None,
        to_date: date | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        annotated_only: bool = False,
        invalid_only: bool = False,
        include_unchecked: bool = False,
        use_task_prompt_as_default: bool = False,
        recording_limit: int | None = None,
        annotation_version: int | None = None,
        dry_run: bool = False,
        old: bool = False,
        dagger_type: str | None = None,
    ) -> bool:
        """通过API导出指定采集批次的数据集

        Args:
            collection_ids: 采集批次ID列表
            auto_fix_indices: 是否在导出后自动修复parquet文件的索引
            task_name_prefix: 任务名称前缀
            use_task_prompt_as_default: 是否使用Task的prompt作为默认task值
            annotation_version: 指定标注版本号，仅在单一task_id或collection_id时支持
        """
        logger.info(f"开始导出采集批次: {collection_ids}")

        # 输出目录中存在 dataset.json 时直接加载数据集信息
        dataset_json_path = self.output_dir / "dataset.json"
        if dataset_json_path.exists():
            with open(dataset_json_path, encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            # 调用API获取数据集信息
            dataset = self._fetch_dataset(
                collection_ids,
                task_ids,
                capture_devices,
                operators,
                use_tos_internal_endpoint,
                from_date,
                to_date,
                from_timestamp,
                to_timestamp,
                annotated_only,
                invalid_only,
                include_unchecked,
                use_task_prompt_as_default,
                recording_limit,
                annotation_version,
                old,
            )

            # 本地保存 dataset 信息
            with open(self.output_dir / "dataset.json", "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)

        task_names = dataset["task_name"].split("+")
        if not all(task_name.startswith(task_name_prefix) for task_name in task_names):
            msg = f"任务名称不匹配: {dataset['task_name']} != {task_name_prefix}"
            raise ValueError(msg)

        logger.info(
            f"获取到数据集信息: {len(dataset['episodes'])} 个episodes, {len(dataset['files'])} 个文件",
        )

        # 如果指定了 dagger_type 过滤，则过滤 episodes
        valid_episode_indices: set[int] = set()
        if dagger_type:
            logger.info(f"开始按 dagger_type='{dagger_type}' 过滤数据...")
            for idx, episode in enumerate(dataset["episodes"]):
                ep_dagger_type = episode.get("dagger_type")
                if ep_dagger_type == dagger_type:
                    valid_episode_indices.add(idx)

            logger.info(
                f"过滤后保留 {len(valid_episode_indices)}/{len(dataset['episodes'])} 个episodes (dagger_type={dagger_type})"
            )

            if len(valid_episode_indices) == 0:
                logger.error(f"没有找到任何 dagger_type='{dagger_type}' 的数据")
                return False

        if fetch_annotations:
            annotations_json_path = self.output_dir / "annotations.json"
            if annotations_json_path.exists():
                with open(annotations_json_path, encoding="utf-8") as f:
                    annotations = json.load(f)
                    count = sum(1 for _, annotation in annotations.items() if annotation is not None)
                    logger.info(f"从 {annotations_json_path} 加载了 {count} 个标注结果")
                    annotations = {int(k): v for k, v in annotations.items()}
            else:
                logger.info("开始拉取标注结果...")
                try:
                    annotations = self._fetch_annotations_concurrently(
                        dataset["recording_ids"],
                        max_workers=10,
                        max_retries=3,
                    )
                    count = sum(1 for _, annotation in annotations.items() if annotation is not None)
                    logger.info(f"拉取了 {count} 个标注结果")
                    with open(annotations_json_path, "w", encoding="utf-8") as f:
                        json.dump(annotations, f, ensure_ascii=False, indent=2)
                    logger.info(f"标注结果已保存到: {annotations_json_path}")
                except Exception:
                    logger.exception("从标注结果中获取任务信息失败")
                    return False
        else:
            annotations = {}

        # 生成元数据文件
        # 如果有 dagger_type 过滤，跳过英文转换（在 _reindex_after_filter 中统一处理）
        skip_conversion = bool(dagger_type and valid_episode_indices)
        self._generate_meta_files(dataset, annotations, skip_english_conversion=skip_conversion)

        if dry_run:
            logger.info("dry_run 模式，跳过下载数据文件")
            return True

        # 如果进行了 dagger_type 过滤，则只下载过滤后的文件
        files_to_download = dataset["files"]
        if dagger_type and valid_episode_indices:
            def _parse_episode_idx_from_path(p: str) -> int | None:
                # 解析 "episode_000123" 为 123
                try:
                    base = Path(p).stem
                    if base.startswith("episode_") and len(base) >= 14:
                        return int(base.split("_")[1])
                except Exception:
                    return None
                return None

            old_len = len(files_to_download)
            files_to_download = [
                f for f in files_to_download
                if (lambda eid: eid in valid_episode_indices if eid is not None else False)(_parse_episode_idx_from_path(f.get("path", "")))
            ]
            logger.info(
                f"按 dagger_type 过滤下载文件: episodes={len(valid_episode_indices)} files={len(files_to_download)}/{old_len}"
            )

        # 下载数据文件
        failed_files = self._download_files(files_to_download)

        retry_count = 0
        while failed_files and retry_count < max_retry_count:
            logger.info(f"重试下载 {len(failed_files)} 个文件...")
            failed_files = self._download_files(failed_files)
            retry_count += 1

        if failed_files:
            logger.warning(f"有 {len(failed_files)} 个文件下载失败:")
            for file_info in failed_files:
                logger.warning(f"  - {file_info['path']}")
            logger.error(f"下载完成（有部分文件下载失败）: {self.output_dir}")
            return False

        logger.info(f"下载完成: {self.output_dir}")

        # 若做了过滤与子集下载，则对数据与文件进行重编号并更新元数据
        task_index_already_updated = False
        if dagger_type and valid_episode_indices:
            try:
                self._reindex_after_filter(dataset, valid_episode_indices, dagger_type=dagger_type)
                logger.info("已完成子集重编号与元数据更新")
                task_index_already_updated = True  # 标记已更新 task_index
            except Exception:
                logger.exception("子集重编号失败")
                return False

        # 自动修复parquet文件的索引（若进行了子集重编号，episodes.jsonl 已更新）
        if auto_fix_indices:
            logger.info("开始自动修复parquet文件索引...")
            try:
                ok = fix_parquet_indices(self.output_dir)
                if not ok:
                    logger.error("parquet文件索引修复失败")
                    return False
                logger.info("parquet文件索引修复完成!")
            except Exception:
                logger.exception("修复parquet文件索引时出错，但导出已完成")
                return False

        # 重设每个 episode dataframe 中的 task_index（在修复索引之后进行）
        # 如果已在 _reindex_after_filter() 中更新过，则跳过（避免重复操作）
        if not task_index_already_updated:
            if fetch_annotations:
                self._reset_task_index_with_annotation(dataset, annotations)
            elif use_task_prompt_as_default:
                self._reset_task_index(dataset)

        # 清理空的chunk目录
        try:
            self._prune_empty_chunks()
            logger.info("已清理空的chunk目录")
        except Exception:
            logger.exception("清理空chunk目录失败")

        return True

    def _fetch_dataset(
        self,
        collection_ids: list[int],
        task_ids: list[int] | None = None,
        capture_devices: list[str] | None = None,
        operators: list[str] | None = None,
        use_tos_internal_endpoint: bool = False,
        from_date: date | None = None,
        to_date: date | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        annotated_only: bool = False,
        invalid_only: bool = False,
        include_unchecked: bool = False,
        use_task_prompt_as_default: bool = False,
        recording_limit: int | None = None,
        annotation_version: int | None = None,
        old: bool = False,
    ) -> dict[str, Any]:
        """通过API获取数据集信息

        Args:
            collection_ids: 采集批次ID列表
            task_ids: 任务ID列表
            capture_device_sns: 采集设备序列号列表
            operator_ids: 操作员ID列表
            use_tos_internal_endpoint: 是否使用TOS内网地址

        Returns:
            数据集字典

        Raises:
            requests.RequestException: API调用失败
            ValueError: 响应格式错误
        """
        # 构建查询参数
        params = []

        # 添加collection_ids参数
        for cid in collection_ids:
            params.append(f"collection_ids={cid}")

        # 添加task_ids参数
        if task_ids:
            for tid in task_ids:
                params.append(f"task_ids={tid}")

        # 添加capture_device_sns参数
        if capture_devices:
            for device in capture_devices:
                params.append(f"capture_devices={device}")

        # 添加operator_ids参数
        if operators:
            for operator in operators:
                params.append(f"operators={urllib.parse.quote(operator)}")

        # 添加use_tos_internal_endpoint参数
        if use_tos_internal_endpoint:
            params.append("use_tos_internal_endpoint=true")

        # 添加时间筛选参数
        if from_timestamp:
            params.append(f"from_timestamp={from_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")
        elif from_date:
            params.append(f"from_date={from_date.strftime('%Y-%m-%d')}")

        if to_timestamp:
            params.append(f"to_timestamp={to_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")
        elif to_date:
            params.append(f"to_date={to_date.strftime('%Y-%m-%d')}")

        if annotated_only:
            params.append("annotated_only=true")

        if invalid_only:
            params.append("invalid_only=true")

        if include_unchecked:
            params.append("include_unchecked=true")

        if use_task_prompt_as_default:
            params.append("use_task_prompt_as_default=true")

        if recording_limit:
            params.append(f"recording_limit={recording_limit}")

        if annotation_version:
            params.append(f"annotation_version={annotation_version}")

        # 传递 old 参数到 API
        params.append(f"old={'true' if old else 'false'}")

        url = f"{self.api_base_url}/api/v1/data_collections/collections/export_dataset?{'&'.join(params)}"
        logger.info(f"调用API: {url}")

        try:
            response = self.session.get(url, timeout=1000)
            if response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY):
                raise ValueError(response.json())
            response.raise_for_status()
            dataset: dict[str, Any] = response.json()["data"]
        except requests.RequestException:
            logger.exception("API调用失败")
            raise
        else:
            return dataset

    def _extract_actions_from_annotation(self, annotation: dict[str, Any]) -> list[dict[str, Any]]:
        """从标注数据中提取动作列表，支持新旧版格式

        Args:
            annotation: 标注数据

        Returns:
            动作列表，统一格式为 {"action": str, ...}
        """
        actions = []
        if annotation.get("version") == "3.0.0":
            # 新版标注数据 (类型 RecordAnnotation)
            actions = annotation["data"]
        elif "annotation" in annotation:
            # 旧版标注数据 (类型 VidatData)，转换为新版格式
            actions = [
                {
                    "start_time": action["start"],
                    "end_time": action["end"],
                    "action": action["description"],
                }
                for action in annotation["annotation"]["actionAnnotationList"]
            ]
        return actions

    def _get_action_name(self, action: dict[str, Any]) -> str:
        """获取action的名称，根据action_field配置选择字段

        Args:
            action: 动作字典

        Returns:
            动作名称（根据self.action_field选择使用action_english或action）
        """
        # 根据配置选择使用 action_english 或 action
        if self.action_field == "action_english":
            return action.get("action_english") or action.get("action", "unknown")
        else:
            return action.get("action") or action.get("action_english", "unknown")

    def _generate_meta_files(
        self,
        dataset: dict[str, Any],
        annotations: dict[int, dict[str, Any] | None],
        skip_english_conversion: bool = False,
    ) -> None:
        """生成元数据文件

        Args:
            dataset: 数据集字典
            annotations: 标注数据字典
            skip_english_conversion: 是否跳过英文转换（当需要后续重新生成时设为True）
        """
        logger.info("生成元数据文件...")

        # 使用 annotation 替换 tasks
        if annotations:
            tasks: set[str] = set()
            for annotation in annotations.values():
                if annotation is None:
                    continue
                actions = self._extract_actions_from_annotation(annotation)
                tasks.update(self._get_action_name(action) for action in actions)

            # 更新每个 episode 的 tasks
            for idx, episode in enumerate(dataset["episodes"]):
                recording_id = dataset["recording_ids"][idx]
                annotation = annotations.get(recording_id)
                if annotation is None:
                    episode["tasks"] = ["unknown"]
                    continue
                actions = self._extract_actions_from_annotation(annotation)
                episode_tasks = [self._get_action_name(action) for action in actions]
                episode["tasks"] = episode_tasks
                tasks.update(episode_tasks)
            dataset["tasks"] = [{"task_index": 0, "task": "unknown"}]
            dataset["tasks"].extend(
                [{"task_index": idx + 1, "task": task} for idx, task in enumerate(sorted(tasks))],
            )
            dataset["info"]["total_tasks"] = len(dataset["tasks"])

        # 生成 info.json
        info_json_path = self.meta_dir / "info.json"
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(dataset["info"], f, ensure_ascii=False, indent=2)
        logger.info(f"生成 info.json: {info_json_path}")

        # 生成 tasks.jsonl
        tasks_jsonl_path = self.meta_dir / "tasks.jsonl"
        with open(tasks_jsonl_path, "w", encoding="utf-8") as f:
            for task_data in dataset["tasks"]:
                f.write(json.dumps(task_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 tasks.jsonl: {tasks_jsonl_path} ({len(dataset['tasks'])} 个任务)")

        # 生成 episodes.jsonl
        episodes_jsonl_path = self.meta_dir / "episodes.jsonl"
        with open(episodes_jsonl_path, "w", encoding="utf-8") as f:
            for episode_data in dataset["episodes"]:
                f.write(json.dumps(episode_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 episodes.jsonl: {episodes_jsonl_path}")

        # 生成 episodes_stats.jsonl
        episodes_stats_jsonl_path = self.meta_dir / "episodes_stats.jsonl"
        with open(episodes_stats_jsonl_path, "w", encoding="utf-8") as f:
            for stats_data in dataset["episode_stats"]:
                f.write(json.dumps(stats_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 episodes_stats.jsonl: {episodes_stats_jsonl_path}")

        # 只在不跳过时才进行英文转换（避免重复操作）
        # 当使用 dagger_type 过滤时，会在 _reindex_after_filter() 中统一处理
        if not skip_english_conversion:
            # 备份并处理 tasks.jsonl，将 "中文:英文" 格式转换为只保留英文
            self._process_tasks_to_english_only(tasks_jsonl_path)
            # 处理 episodes.jsonl 中的 tasks 字段，将 "中文:英文" 格式转换为只保留英文
            self._process_episode_tasks_to_english_only(episodes_jsonl_path)

    def _process_tasks_to_english_only(self, tasks_jsonl_path: Path) -> None:
        """备份并处理 tasks.jsonl，将 "中文:英文" 格式转换为只保留英文部分

        Args:
            tasks_jsonl_path: tasks.jsonl 文件路径
        """
        if not tasks_jsonl_path.exists():
            logger.warning(f"tasks.jsonl 不存在，跳过处理: {tasks_jsonl_path}")
            return

        # 备份原始文件
        backup_path = tasks_jsonl_path.with_suffix(".jsonl.backup")
        shutil.copy2(tasks_jsonl_path, backup_path)
        logger.info(f"已备份 tasks.jsonl 到: {backup_path}")

        # 读取并处理
        processed_tasks = []
        with open(tasks_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                task_data = json.loads(line.strip())
                # 处理 task 字段：提取 "中文:英文" 中的英文部分
                original_task = task_data.get("task", "")
                if ":" in original_task:
                    # 分割并取冒号后的英文部分，去除首尾空格
                    english_task = original_task.split(":", 1)[1].strip()
                    task_data["task"] = english_task
                processed_tasks.append(task_data)

        # 写回处理后的文件
        with open(tasks_jsonl_path, "w", encoding="utf-8") as f:
            for task_data in processed_tasks:
                f.write(json.dumps(task_data, ensure_ascii=False) + "\n")

        logger.info(f"已处理 tasks.jsonl，将 {len(processed_tasks)} 个任务转换为英文格式")

    def _process_episode_tasks_to_english_only(self, episodes_jsonl_path: Path) -> None:
        """处理 episodes.jsonl 中的 tasks 字段，将 "中文:英文" 格式转换为只保留英文部分

        Args:
            episodes_jsonl_path: episodes.jsonl 文件路径
        """
        if not episodes_jsonl_path.exists():
            logger.warning(f"episodes.jsonl 不存在，跳过处理: {episodes_jsonl_path}")
            return

        # 备份原始文件
        backup_path = episodes_jsonl_path.with_suffix(".jsonl.backup")
        shutil.copy2(episodes_jsonl_path, backup_path)
        logger.info(f"已备份 episodes.jsonl 到: {backup_path}")

        # 读取并处理
        processed_episodes = []
        with open(episodes_jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                episode_data = json.loads(line.strip())
                # 处理 tasks 字段（列表）：提取每个 "中文:英文" 中的英文部分
                original_tasks = episode_data.get("tasks", [])
                english_tasks = []
                for task in original_tasks:
                    if ":" in task:
                        # 分割并取冒号后的英文部分，去除首尾空格
                        english_task = task.split(":", 1)[1].strip()
                        english_tasks.append(english_task)
                    else:
                        # 如果没有冒号，保持原样
                        english_tasks.append(task)
                episode_data["tasks"] = english_tasks
                processed_episodes.append(episode_data)

        # 写回处理后的文件
        with open(episodes_jsonl_path, "w", encoding="utf-8") as f:
            for episode_data in processed_episodes:
                f.write(json.dumps(episode_data, ensure_ascii=False) + "\n")

        logger.info(f"已处理 episodes.jsonl，将 {len(processed_episodes)} 个episode的tasks转换为英文格式")

    def _reindex_after_filter(
        self,
        dataset: dict[str, Any],
        valid_episode_indices: set[int],
        dagger_type: str | None = None,
    ) -> None:
        """对子集进行重编号并更新 meta/info 与 episodes.jsonl

        - 重新计算 total_episodes、total_videos、splits。
        - 维持 chunks_size 不变（若小于 1 则设为 1000），按该尺寸重新分配 chunk-xxx 目录与 episode_{:06d} 文件名。
        - 同步更新 dataset['episodes'] 的 episode_index 字段。
        - 如果提供了 dagger_type，将其记录到 info.json 中。
        """
        info = dataset["info"]
        chunks_size = int(info.get("chunks_size") or 1000)
        if chunks_size <= 0:
            chunks_size = 1000

        # 生成新的 episode 索引映射 old_idx -> new_idx
        sorted_valid = sorted(valid_episode_indices)
        remap: dict[int, int] = {old: new for new, old in enumerate(sorted_valid)}

        # 更新内存中的 episodes 与 recording_ids（用于后续流程一致）
        # 注意：不在这里写入 episodes.jsonl，因为后面还需要转换格式
        dataset["episodes"] = [
            {**dataset["episodes"][old_idx], "episode_index": remap[old_idx]}
            for old_idx in sorted_valid
        ]
        dataset["recording_ids"] = [
            int(dataset["recording_ids"][old_idx]) for old_idx in sorted_valid
        ]

        # 重写 episodes_stats.jsonl 仅保留子集，更新 episode_index
        episodes_stats_jsonl_path = self.meta_dir / "episodes_stats.jsonl"
        if episodes_stats_jsonl_path.exists() and dataset.get("episode_stats"):
            with open(episodes_stats_jsonl_path, "w", encoding="utf-8") as f:
                for old_idx in sorted_valid:
                    st = dict(dataset["episode_stats"][old_idx])
                    st["episode_index"] = remap[old_idx]
                    f.write(json.dumps(st, ensure_ascii=False) + "\n")

        # 更新 info.json (内存与落盘)
        total_episodes = len(sorted_valid)
        total_chunks = (total_episodes + chunks_size - 1) // chunks_size if total_episodes > 0 else 0

        # 计算总视频流数：features 中 dtype==video 的键数量
        num_video_streams = sum(1 for k, v in info['features'].items() if isinstance(v, dict) and v.get("dtype") == "video")
        total_videos = total_episodes * num_video_streams

        # 更新 info 关键字段
        info["total_episodes"] = total_episodes
        info["total_chunks"] = total_chunks
        info["splits"] = {"train": f"0:{total_episodes}"}
        info["total_videos"] = total_videos

        # 重新分配与重命名 data 与 videos 文件到新 chunk/index 位置（两阶段，避免互相覆盖）
        # 1) parquet: old -> temp, 再 temp -> new
        parquet_moves: list[tuple[Path, Path, Path]] = []  # (old, tmp, new)
        for old_idx in sorted_valid:
            new_idx = remap[old_idx]
            old_chunk = old_idx // chunks_size
            new_chunk = new_idx // chunks_size
            old_parquet = self.output_dir / f"data/chunk-{old_chunk:03d}/episode_{old_idx:06d}.parquet"
            new_parquet = self.output_dir / f"data/chunk-{new_chunk:03d}/episode_{new_idx:06d}.parquet"
            if not old_parquet.exists():
                continue
            if old_parquet.resolve() == new_parquet.resolve():
                continue
            tmp_parquet = old_parquet.with_suffix(old_parquet.suffix + f".tmp_{new_idx:06d}")
            parquet_moves.append((old_parquet, tmp_parquet, new_parquet))

        # 第一阶段：old -> tmp
        for old_p, tmp_p, _ in parquet_moves:
            tmp_p.parent.mkdir(parents=True, exist_ok=True)
            if tmp_p.exists():
                tmp_p.unlink()
            old_p.rename(tmp_p)
        # 第二阶段：tmp -> new
        for _, tmp_p, new_p in parquet_moves:
            new_p.parent.mkdir(parents=True, exist_ok=True)
            if new_p.exists():
                new_p.unlink()
            tmp_p.rename(new_p)

        # 2) 视频: old -> tmp -> new（遍历所有 video_key）
        videos_dir = self.output_dir / "videos"
        if videos_dir.exists():
            video_moves: list[tuple[Path, Path, Path]] = []
            for old_idx in sorted_valid:
                new_idx = remap[old_idx]
                old_chunk = old_idx // chunks_size
                new_chunk = new_idx // chunks_size
                chunk_dir = videos_dir / f"chunk-{old_chunk:03d}"
                if not chunk_dir.exists():
                    continue
                for video_key_dir in chunk_dir.iterdir():
                    if not video_key_dir.is_dir():
                        continue
                    old_mp4 = video_key_dir / f"episode_{old_idx:06d}.mp4"
                    new_dir = videos_dir / f"chunk-{new_chunk:03d}" / video_key_dir.name
                    new_mp4 = new_dir / f"episode_{new_idx:06d}.mp4"
                    if not old_mp4.exists():
                        continue
                    if old_mp4.resolve() == new_mp4.resolve():
                        continue
                    tmp_mp4 = old_mp4.with_suffix(old_mp4.suffix + f".tmp_{new_idx:06d}")
                    video_moves.append((old_mp4, tmp_mp4, new_mp4))
            # old -> tmp
            for old_v, tmp_v, _ in video_moves:
                tmp_v.parent.mkdir(parents=True, exist_ok=True)
                if tmp_v.exists():
                    tmp_v.unlink()
                old_v.rename(tmp_v)
            # tmp -> new
            for _, tmp_v, new_v in video_moves:
                new_v.parent.mkdir(parents=True, exist_ok=True)
                if new_v.exists():
                    new_v.unlink()
                tmp_v.rename(new_v)

        # 计算 total_frames = 所有子集 parquet 的行数之和（按新索引路径）
        try:
            total_frames = 0
            for new_idx in range(total_episodes):
                new_chunk = new_idx // chunks_size
                parquet_path = self.output_dir / f"data/chunk-{new_chunk:03d}/episode_{new_idx:06d}.parquet"
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                    total_frames += int(len(df))
            info["total_frames"] = total_frames
        except Exception:
            logger.exception("统计 total_frames 失败，保持原值")

        # 计算 total_tasks = 数据集中唯一的 tasks 数量，并重新生成 tasks.jsonl
        try:
            # 转换所有 episode 的 tasks 字段为英文格式，同时收集所有唯一任务名（一次循环完成）
            all_tasks = set()
            for ep in dataset["episodes"]:
                original_tasks = ep.get("tasks", [])
                english_tasks = []
                for task in original_tasks:
                    if ":" in task:
                        # 分割并取冒号后的英文部分，去除首尾空格
                        english_task = task.split(":", 1)[1].strip()
                        english_tasks.append(english_task)
                        all_tasks.add(english_task)
                    else:
                        # 如果没有冒号，保持原样
                        english_tasks.append(task)
                        all_tasks.add(task)
                ep["tasks"] = english_tasks

            # 重新生成 tasks 列表（添加 unknown 作为默认任务）
            if all_tasks:
                # 排序任务列表以保持一致性
                sorted_tasks = sorted(all_tasks - {"unknown"})  # 排除 unknown，稍后添加到开头

                # 构建新的 tasks 列表：unknown 始终是 task_index=0
                new_tasks = [{"task_index": 0, "task": "unknown"}]
                new_tasks.extend(
                    [{"task_index": idx + 1, "task": task} for idx, task in enumerate(sorted_tasks)]
                )

                # 更新 dataset["tasks"] 和 info["total_tasks"]
                dataset["tasks"] = new_tasks
                info["total_tasks"] = len(new_tasks)

                # 重新生成 tasks.jsonl
                tasks_jsonl_path = self.meta_dir / "tasks.jsonl"
                with open(tasks_jsonl_path, "w", encoding="utf-8") as f:
                    for task_data in new_tasks:
                        f.write(json.dumps(task_data, ensure_ascii=False) + "\n")
                logger.info(f"已重新生成 tasks.jsonl: {len(new_tasks)} 个任务")

                # 重新写入 episodes.jsonl（使用转换后的英文 tasks）
                episodes_jsonl_path = self.meta_dir / "episodes.jsonl"
                with open(episodes_jsonl_path, "w", encoding="utf-8") as f:
                    for ep in dataset["episodes"]:
                        f.write(json.dumps(ep, ensure_ascii=False) + "\n")
                logger.info(f"已更新 episodes.jsonl 为英文任务名")

                # 更新所有 parquet 文件的 task_index
                logger.info("开始更新 parquet 文件的 task_index...")
                chunks_size = int(info.get("chunks_size") or 1000)

                # 预先构建 task_name -> task_index 的映射，避免重复查找
                task_name_to_index = {task_data["task"]: task_data["task_index"] for task_data in new_tasks}

                updated_count = 0
                for idx in range(len(dataset["episodes"])):
                    chunk_id = idx // chunks_size
                    parquet_path = self.output_dir / f"data/chunk-{chunk_id:03d}/episode_{idx:06d}.parquet"
                    if not parquet_path.exists():
                        logger.warning(f"Parquet 文件不存在，跳过: {parquet_path}")
                        continue

                    # 获取该 episode 的默认任务（使用第一个任务）
                    episode_tasks = dataset["episodes"][idx].get("tasks", ["unknown"])
                    task_name = episode_tasks[0] if episode_tasks else "unknown"

                    # 从预构建的映射中查找 task_index
                    task_index = task_name_to_index.get(task_name, 0)

                    # 更新 parquet 文件
                    df = pd.read_parquet(parquet_path)
                    df["task_index"] = task_index
                    df.to_parquet(parquet_path, index=False)
                    updated_count += 1

                    if updated_count % 50 == 0:  # 每50个输出一次进度
                        logger.debug(f"已更新 {updated_count}/{len(dataset['episodes'])} 个 parquet 文件")

                logger.info(f"已更新所有 parquet 文件的 task_index ({updated_count} 个文件)")
            else:
                info["total_tasks"] = dataset["info"].get("total_tasks", 1)
        except Exception:
            logger.exception("统计 total_tasks 失败，保持原值")

        # 添加 dagger_type 字段（如果提供）
        if dagger_type:
            info["dagger_type"] = dagger_type
            logger.info(f"在 info.json 中记录 dagger_type: {dagger_type}")

        # 最终写回 info.json
        info_json_path = self.meta_dir / "info.json"
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    def _prune_empty_chunks(self) -> None:
        """删除空的 chunk-* 目录。

        - data/chunk-xxx：若无任何 .parquet 文件，则删除该目录
        - videos/chunk-xxx：
          1) 先删除其下空的视频流子目录（如 cam_high、cam_left_wrist 等，无 .mp4 即视为空）
          2) 若整个 chunk 目录内没有任何 .mp4，则删除该 chunk 目录
        """
        # 清理 data 分片
        data_root = self.output_dir / "data"
        if data_root.exists():
            for chunk_dir in sorted(data_root.glob("chunk-*")):
                if not chunk_dir.is_dir():
                    continue
                try:
                    has_parquet = any(p.suffix == ".parquet" for p in chunk_dir.glob("*.parquet"))
                    if not has_parquet:
                        shutil.rmtree(chunk_dir)
                        logger.info(f"已移除空数据分片目录: {chunk_dir}")
                except Exception:
                    logger.exception(f"移除空数据分片目录失败: {chunk_dir}")

        # 清理 videos 分片
        videos_root = self.output_dir / "videos"
        if videos_root.exists():
            for chunk_dir in sorted(videos_root.glob("chunk-*")):
                if not chunk_dir.is_dir():
                    continue
                try:
                    # 先移除空的视频流子目录
                    for sub_dir in list(chunk_dir.iterdir()):
                        if sub_dir.is_dir():
                            has_mp4 = any(f.suffix == ".mp4" for f in sub_dir.glob("*.mp4"))
                            if not has_mp4:
                                shutil.rmtree(sub_dir)
                                logger.debug(f"已移除空视频流目录: {sub_dir}")

                    # 若该 chunk 下无任何 mp4，则移除整个分片目录
                    has_any_mp4 = any(f.suffix == ".mp4" for f in chunk_dir.rglob("*.mp4"))
                    if not has_any_mp4:
                        shutil.rmtree(chunk_dir)
                        logger.info(f"已移除空视频分片目录: {chunk_dir}")
                except Exception:
                    logger.exception(f"移除空视频分片目录失败: {chunk_dir}")

        return

    def _download_files(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """并发下载文件

        Args:
            files: 文件列表，每个文件包含path, type, download_url

        Returns:
            下载失败的文件列表
        """
        logger.info(f"准备下载 {len(files)} 个文件")

        failed_files = []

        # 并发下载
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_file = {
                executor.submit(self._download_single_file, file_info): file_info for file_info in files
            }

            completed = 0
            for future in tqdm(as_completed(future_to_file), total=len(files), desc="下载文件"):
                file_info = future_to_file[future]
                try:
                    future.result()
                    completed += 1
                    logger.debug(f"下载进度: {completed}/{len(files)} - {file_info['path']}")
                except Exception:
                    logger.exception(f"下载失败: {file_info['path']}")
                    failed_files.append(file_info)
        return failed_files

    def _download_single_file(self, file_info: dict[str, Any]) -> None:
        """下载单个文件

        Args:
            file_info: 文件信息字典，包含path, type, download_url
        """
        file_path = file_info["path"]
        download_url = file_info["download_url"]

        # 确定目标路径
        target_path = self.output_dir / file_path

        # 如果文件已存在且大小合理，跳过下载
        if target_path.exists() and target_path.stat().st_size > 0:
            logger.debug(f"文件已存在，跳过下载: {target_path}")
            return

        # 确保目标目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 重试机制：最多重试3次
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 使用预签名URL下载文件
                response = self.session.get(download_url, stream=True, timeout=180)
                response.raise_for_status()

                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                logger.debug(f"下载成功: {target_path}")

            except Exception as e:
                if target_path.exists():
                    target_path.unlink()  # 删除部分下载的文件

                if attempt < max_retries - 1:
                    # 不是最后一次尝试，记录警告并重试
                    logger.warning(
                        f"下载文件失败 (尝试 {attempt + 1}/{max_retries}): {file_path}, 错误: {e}",
                    )
                    time.sleep(2**attempt)  # 指数退避：2^0=1s, 2^1=2s, 2^2=4s
                else:
                    # 最后一次尝试也失败了，抛出异常
                    logger.exception(f"下载文件失败，已重试 {max_retries} 次: {file_path}")
                    raise
            else:
                return

    def _fetch_single_annotation(
        self,
        session: requests.Session,
        recording_id: int,
        max_retries: int = 3,
    ) -> tuple[int, dict[str, Any] | None]:
        """拉取单个 recording 的最新标注结果

        Args:
            session: HTTP会话对象
            api_base_url: API基础URL
            recording_id: 录制ID
            max_retries: 最大重试次数

        Returns:
            (recording_id, annotation_data) 元组，annotation_data为None表示没有标注结果
        """
        url = f"{self.api_base_url}/api/v1/data_collections/recordings/{recording_id}/latest_annotation"

        for attempt in range(max_retries + 1):
            try:
                response = session.get(url, timeout=100)
                if response.status_code == HTTPStatus.NOT_FOUND:
                    logger.debug(f"Recording {recording_id} 没有标注结果")
                    return recording_id, None

                response.raise_for_status()
                annotation_data = response.json()

                # 根据返回结果判断新旧数据版本
                if (annotation_data.get("version") == "3.0.0" and not annotation_data["data"]) or (
                    "annotation" in annotation_data
                    and not annotation_data["annotation"]["actionAnnotationList"]
                ):
                    logger.debug(f"Recording {recording_id} 没有标注结果")
                    return recording_id, None

                logger.debug(f"成功获取 Recording {recording_id} 的标注结果")

            except requests.RequestException:
                if attempt < max_retries:
                    wait_time = 2**attempt  # 指数退避
                    logger.warning(
                        f"拉取 Recording {recording_id} 标注失败 (尝试 {attempt + 1}/{max_retries + 1})"
                        f"{wait_time}秒后重试",
                    )
                    time.sleep(wait_time)
                else:
                    logger.exception(f"拉取 Recording {recording_id} 标注失败，已达最大重试次数")
                    raise
            else:
                return recording_id, annotation_data

        return recording_id, None

    def _fetch_annotations_concurrently(
        self,
        recording_ids: list[int],
        max_workers: int = 10,
        max_retries: int = 3,
    ) -> dict[int, dict[str, Any]]:
        """并发拉取多个 recording 的最新标注结果

        Args:
            api_base_url: API基础URL
            recording_ids: 录制ID列表
            max_workers: 最大并发工作线程数
            max_retries: 每个请求的最大重试次数

        Returns:
            {recording_id: annotation_data} 字典，失败的recording不包含在结果中
        """
        logger.info(f"开始并发拉取 {len(recording_ids)} 个录制的标注结果")

        annotations = {}
        session = requests.Session()

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_recording = {
                    executor.submit(
                        self._fetch_single_annotation,
                        session,
                        recording_id,
                        max_retries,
                    ): recording_id
                    for recording_id in recording_ids
                }

                # 收集结果，使用进度条显示
                with tqdm(
                    total=len(recording_ids),
                    desc="拉取标注结果",
                    unit="recording",
                ) as pbar:
                    for future in as_completed(future_to_recording):
                        recording_id, annotation_data = future.result()
                        if annotation_data is not None:
                            annotations[recording_id] = annotation_data
                        pbar.update(1)

        finally:
            session.close()

        logger.info(f"完成标注拉取，成功获取 {len(annotations)}/{len(recording_ids)} 个录制的标注结果")
        return annotations

    def _get_task_index(
        self,
        dataset: dict[str, Any],
        task_name: str,
    ) -> int:
        """获取任务索引"""
        for task in dataset["tasks"]:
            if task["task"] == task_name:
                return int(task["task_index"])
        return 0

    def _reset_task_index(
        self,
        dataset: dict[str, Any],
    ) -> None:
        """重设每个 episode dataframe 中的 task_index"""
        for idx in range(dataset["info"]["total_episodes"]):
            episode = dataset["episodes"][idx]
            task_id_map = episode.get("task_id_map")

            chunk_id = idx // dataset["info"]["chunks_size"]
            parquet_path = self.output_dir / dataset["info"]["data_path"].format(
                episode_chunk=chunk_id,
                episode_index=idx,
            )
            df = pd.read_parquet(parquet_path)

            if task_id_map:
                # 使用 task_id_map 重设 task_index
                # task_id_map 的 key 是字符串，需要转为整数
                task_id_mapping = {
                    int(task_id): self._get_task_index(dataset, task_name)
                    for task_id, task_name in task_id_map.items()
                }
                df["task_index"] = df["task_index"].map(task_id_mapping).fillna(0).astype(int)
            else:
                # Fallback 逻辑
                if len(episode["tasks"]) != 1:
                    msg = f"Episode {idx} in collection has multiple tasks but no task_id_map."
                    raise ValueError(msg)
                task = episode["tasks"][0]
                task_index = self._get_task_index(dataset, task)
                df.loc[:, "task_index"] = task_index

            df.to_parquet(parquet_path, index=False)

    def _reset_task_index_with_annotation(
        self,
        dataset: dict[str, Any],
        annotations: dict[int, dict[str, Any] | None],
    ) -> None:
        """重设每个 episode dataframe 中的 task_index"""
        fps = dataset["info"]["fps"]
        for idx in range(dataset["info"]["total_episodes"]):
            recording_id = dataset["recording_ids"][idx]
            annotation = annotations.get(recording_id)
            if annotation is None:  # 跳过没有标注的数据
                continue
            chunk_id = idx // dataset["info"]["chunks_size"]
            parquet_path = self.output_dir / dataset["info"]["data_path"].format(
                episode_chunk=chunk_id,
                episode_index=idx,
            )
            df = pd.read_parquet(parquet_path)
            df.loc[:, "task_index"] = 0
            if annotation:
                actions = self._extract_actions_from_annotation(annotation)

                for action in actions:
                    # 使用 floor 和 ceil 确保能覆盖到所有帧，后面的段落起始帧可能会覆盖前面段落的终止帧
                    start_frame = math.floor(action["start_time"] * fps)
                    end_frame = math.ceil(action["end_time"] * fps)
                    task_index = self._get_task_index(dataset, self._get_action_name(action))
                    df.loc[start_frame:end_frame, "task_index"] = task_index
            df.to_parquet(parquet_path, index=False)


def fix_parquet_indices(dataset_dir: Path) -> bool:
    """修复parquet文件中的episode_index和index列

    Args:
        dataset_dir: 数据集根目录路径

    修复规则:
    1. episode_index列应该与对应的episode序号一致
    2. index列应该依次递增，从0开始
    3. 相邻episode要连续，episode 0的index是0~(len(episode 0)-1)，
       episode 1的index是len(episode 0)~(len(episode 0)+len(episode 1)-1)

    优化假设:
    - 每个parquet文件只包含一个episode的数据
    - 文件命名格式: episode_{idx:06d}.parquet
    """
    logger.info(f"开始修复数据集中的parquet文件: {dataset_dir}")

    # 读取episodes元数据以获取每个episode的预期长度
    episodes_file = dataset_dir / "meta" / "episodes.jsonl"
    if not episodes_file.exists():
        logger.error(f"未找到episodes元数据文件: {episodes_file}")
        return False

    # 解析episodes元数据，构建episode长度映射
    episode_lengths = {}
    with open(episodes_file, encoding="utf-8") as f:
        for line in f:
            episode_data = json.loads(line.strip())
            episode_idx = episode_data["episode_index"]
            episode_length = episode_data["length"]
            episode_lengths[episode_idx] = episode_length

    logger.info(f"加载了 {len(episode_lengths)} 个episode的元数据")

    # 找到所有episode parquet文件
    data_dir = dataset_dir / "data"
    if not data_dir.exists():
        logger.warning(f"数据目录不存在: {data_dir}")
        return False

    episode_files = list(data_dir.glob("chunk-*/episode_*.parquet"))

    if not episode_files:
        logger.warning(f"在 {data_dir} 中未找到episode_*.parquet文件")
        return False

    logger.info(f"找到 {len(episode_files)} 个episode文件")

    # 解析文件名获取episode索引，并排序
    episode_info = []
    for file_path in episode_files:
        try:
            # 从文件名解析episode索引: episode_000123.parquet -> 123
            chunk_id = int(file_path.parent.name.split("-")[1])
            filename = file_path.stem  # 去掉.parquet后缀
            if filename.startswith("episode_"):
                episode_idx = int(filename[8:])  # 跳过'episode_'前缀
                episode_info.append((chunk_id, episode_idx, file_path))
            else:
                logger.warning(f"文件名格式不符合预期: {file_path}")
        except ValueError:
            logger.warning(f"无法解析episode索引: {file_path}")

    # 按episode索引排序
    episode_info.sort(key=lambda x: (x[0], x[1]))

    # 检查文件数量是否与元数据一致
    if len(episode_info) != len(episode_lengths):
        logger.error(f"文件数量与元数据不一致！实际: {len(episode_info)}, 预期: {len(episode_lengths)}")
        return False

    # 处理每个episode文件
    global_index_counter = 0
    validation_errors = 0

    for chunk_id, episode_idx, file_path in episode_info:
        logger.debug(f"处理Episode {episode_idx} (chunk {chunk_id}): {file_path}")

        try:
            # 读取parquet文件
            df = pd.read_parquet(file_path)
            actual_length = len(df)

            if actual_length == 0:
                logger.warning(f"文件为空，跳过: {file_path}")
                continue

            # 验证行数是否与元数据一致
            expected_length = episode_lengths.get(episode_idx)
            if expected_length is not None and actual_length != expected_length:
                logger.error(
                    f"Episode {episode_idx} 行数不匹配！实际: {actual_length}, 预期: {expected_length}",
                )
                validation_errors += 1
            else:
                logger.debug(f"Episode {episode_idx} 行数验证通过: {actual_length}")

            # 检查必要的列是否存在
            if "episode_index" not in df.columns:
                logger.warning(f"文件中没有episode_index列，跳过: {file_path}")
                continue

            # 修复episode_index列：确保所有行都是正确的episode索引
            df["episode_index"] = episode_idx

            # 修复index列：为这个episode分配连续的全局索引
            df["index"] = range(global_index_counter, global_index_counter + actual_length)

            # 保存修复后的文件（覆盖原文件）
            df.to_parquet(file_path, index=False)

            logger.debug(
                f"Episode {episode_idx}: {actual_length} 行, "
                f"index范围: {global_index_counter} ~ {global_index_counter + actual_length - 1}",
            )

            global_index_counter += actual_length

        except Exception:
            logger.exception(f"处理Episode {episode_idx}文件失败: {file_path}")
            raise

    # 输出修复结果摘要
    if validation_errors > 0:
        logger.warning(f"修复完成，但发现 {validation_errors} 个行数验证错误！")
    else:
        logger.info("修复完成，所有episode文件行数验证通过！")

    logger.info(f"总共处理 {len(episode_info)} 个episode文件，全局index总数: {global_index_counter}")
    return True


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""

    def _parse_bool(value: str) -> bool:
        """解析布尔值字符串"""
        return str(value).lower() in ("true", "1", "yes")

    parser = argparse.ArgumentParser(description="通过API导出 LeRobot 数据集")
    parser.add_argument(
        "--task-name-prefix",
        type=str,
        required=False,
        default="",
        help="要导出的任务名称，（用来校验导出的数据集是否正确，会判断前缀是否一致）",
    )
    parser.add_argument(
        "--collection-ids",
        type=int,
        nargs="*",
        required=False,
        default=[],
        help="要导出的采集批次ID列表，可以指定多个",
    )
    parser.add_argument(
        "--task-ids",
        type=int,
        nargs="*",
        default=[],
        help="要导出的任务ID列表，可以指定多个",
    )
    parser.add_argument(
        "--capture-devices",
        type=str,
        nargs="*",
        # default=["moz1-y13"],
        default=[],
        help="要导出的采集设备序列号列表，可以指定多个，例如 moz1-01, moz1-y02, 不指定则导出所有设备",
    )
    parser.add_argument(
        "--operators",
        type=str,
        nargs="*",
        default=[],
        help="要导出的操作员姓名列表，可以指定多个，不指定则导出所有操作员",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="导出目录路径",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="https://quanta.i.spirit-ai.com",
        help="API服务端基础URL (默认: https://quanta.i.spirit-ai.com)",
    )
    parser.add_argument(
        "--no-fix-indices",
        action="store_true",
        help="导出后不自动修复parquet文件的索引",
    )
    parser.add_argument(
        "--use-tos-internal-endpoint",
        action="store_true",
        help="使用TOS内网地址下载数据集",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="显示详细日志",
    )
    parser.add_argument(
        "--fetch-annotations",
        action="store_true",
        help="拉取并保存标注数据",
    )
    parser.add_argument(
        "--from-date",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
        help="开始日期（含）",
    )
    parser.add_argument(
        "--to-date",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
        help="结束日期（含）",
    )
    parser.add_argument(
        "--from-timestamp",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
        help="开始时间点（含）格式：YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument(
        "--to-timestamp",
        type=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"),
        help="结束时间点（含）格式：YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument(
        "--annotated-only",
        action="store_true",
        help="只导出有标注的数据",
    )
    parser.add_argument(
        "--invalid-only",
        action="store_true",
        help="只导出质检不合格的数据",
    )
    parser.add_argument(
        "--include-unchecked",
        action="store_true",
        help="包含未质检且未标记为采集失误的数据",
    )
    parser.add_argument(
        "--use-task-prompt-as-default",
        action="store_true",
        help="使用采集任务的prompt作为默认task值"
        "（当不包含标注数据时，导出标注数据时为标注的部分 task 会设置为 unknown）",
    )
    parser.add_argument(
        "--recording-limit",
        type=int,
        help="导出的 episode 数量上限",
    )
    parser.add_argument(
        "--annotation-version",
        type=int,
        help="指定标注版本号，仅在单一task_id或collection_id时支持",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只导出数据集信息，不下载数据文件",
    )
    parser.add_argument(
        "--old",
        action="store_true",
        help="使用旧逻辑（默认使用新逻辑）",
    )
    parser.add_argument(
        "--group-by-features",
        action="store_true",
        help="按 features 分组导出，每个分组导出到单独的子目录（需要指定 --task-ids）",
    )
    parser.add_argument(
        "--action-field",
        type=str,
        choices=["action", "action_english"],
        default="action_english",
        help="选择使用的动作字段名，可选 action 或 action_english (默认: action_english)",
    )
    parser.add_argument(
        "--dagger-type",
        type=str,
        help="按 dagger_type 字段过滤数据，例如 policy 或 teleop",
    )
    return parser.parse_args()


def main() -> None:
    """主函数"""
    args = parse_args()
    if not args.collection_ids and not args.task_ids:
        logger.error("collection_ids 和 task_ids 不能同时为空")
        sys.exit(1)

    if args.use_task_prompt_as_default and args.fetch_annotations:
        logger.error(
            "不能同时指定 use_task_prompt_as_default 和 fetch_annotations",
        )
        sys.exit(1)

    # --group-by-features 需要 --task-ids
    if args.group_by_features and not args.task_ids:
        logger.error("--group-by-features 需要指定 --task-ids")
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 创建导出器并执行导出
        exporter = APIDatasetExporter(args.output_dir, args.api_url, args.action_field)
        auto_fix = not args.no_fix_indices

        if args.group_by_features:
            # 分组导出模式
            export_with_grouping(args, auto_fix)
        else:
            # 原有导出模式
            exporter = APIDatasetExporter(args.output_dir, args.api_url)
            ok = exporter.export_collections(
                args.collection_ids,
                task_ids=args.task_ids if args.task_ids else None,
                capture_devices=args.capture_devices if args.capture_devices else None,
                operators=args.operators if args.operators else None,
                auto_fix_indices=auto_fix,
                task_name_prefix=args.task_name_prefix,
                use_tos_internal_endpoint=args.use_tos_internal_endpoint,
                fetch_annotations=args.fetch_annotations,
                from_date=args.from_date,
                to_date=args.to_date,
                from_timestamp=getattr(args, "from_timestamp", None),
                to_timestamp=getattr(args, "to_timestamp", None),
                annotated_only=args.annotated_only,
                invalid_only=args.invalid_only,
                include_unchecked=args.include_unchecked,
                use_task_prompt_as_default=args.use_task_prompt_as_default,
                recording_limit=args.recording_limit,
                dry_run=args.dry_run,
                dagger_type=args.dagger_type,
            )

            if ok:
                logger.info("数据集导出成功!")
            else:
                logger.error("数据集导出失败!")
                sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("用户中断操作")
        sys.exit(1)
    except Exception:
        logger.exception("操作失败")
        sys.exit(1)

def fetch_groups_by_features(
    api_base_url: str,
    task_ids: list[int],
    capture_devices: list[str] | None = None,
    operators: list[str] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    from_timestamp: datetime | None = None,
    to_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """通过API获取按 features 分组的结果

    Args:
        api_base_url: API服务端基础URL
        task_ids: 任务ID列表
        capture_devices: 采集设备序列号列表
        operators: 操作员列表
        from_date: 开始日期
        to_date: 结束日期
        from_timestamp: 开始时间点
        to_timestamp: 结束时间点

    Returns:
        分组结果字典
    """
    api_base_url = api_base_url.rstrip("/")

    # 构建查询参数
    params = []

    # 添加task_ids参数（必填）
    for tid in task_ids:
        params.append(f"task_ids={tid}")

    # 添加capture_devices参数
    if capture_devices:
        for device in capture_devices:
            params.append(f"capture_devices={device}")

    # 添加operators参数
    if operators:
        for operator in operators:
            params.append(f"operators={urllib.parse.quote(operator)}")

    # 添加时间筛选参数
    if from_timestamp:
        params.append(f"from_timestamp={from_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")
    elif from_date:
        params.append(f"from_date={from_date.strftime('%Y-%m-%d')}")

    if to_timestamp:
        params.append(f"to_timestamp={to_timestamp.strftime('%Y-%m-%dT%H:%M:%S')}")
    elif to_date:
        params.append(f"to_date={to_date.strftime('%Y-%m-%d')}")

    url = f"{api_base_url}/api/v1/data_collections/collections/group_by_features?{'&'.join(params)}"
    logger.info(f"调用分组API: {url}")

    try:
        response = requests.get(url, timeout=60)
        if response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY):
            raise ValueError(response.json())
        response.raise_for_status()
        result: dict[str, Any] = response.json()["data"]
    except requests.RequestException:
        logger.exception("分组API调用失败")
        raise
    else:
        return result

def export_with_grouping(args: argparse.Namespace, auto_fix: bool) -> None:
    """按 features 分组导出

    Args:
        args: 命令行参数
        auto_fix: 是否自动修复索引
    """
    # 获取分组结果
    logger.info("正在获取 features 分组...")
    groups_result = fetch_groups_by_features(
        api_base_url=args.api_url,
        task_ids=args.task_ids,
        capture_devices=args.capture_devices if args.capture_devices else None,
        operators=args.operators if args.operators else None,
        from_date=args.from_date,
        to_date=args.to_date,
        from_timestamp=getattr(args, "from_timestamp", None),
        to_timestamp=getattr(args, "to_timestamp", None),
    )

    groups = groups_result.get("groups", [])
    total_groups = groups_result.get("total_groups", 0)
    total_collections = groups_result.get("total_collections", 0)

    logger.info(f"共 {total_collections} 个 collections，分为 {total_groups} 组")

    if not groups:
        logger.warning("没有找到任何 collections")
        return

    # 统计信息
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, group in enumerate(groups):
        features = group.get("features")
        features_hash = group.get("features_hash", f"group_{i}")
        collection_ids = group.get("collection_ids", [])
        collection_count = group.get("collection_count", len(collection_ids))

        # 计算 features 数量
        features_len = len(features) if features else 0

        # 生成目录名: dataset_{id}_{features数量}_{hash}
        group_dir_name = f"dataset_{i}_{features_len}_{features_hash}"

        logger.info(f"\n{'='*60}")
        logger.info(f"处理分组 {i+1}/{total_groups}: {group_dir_name}")
        logger.info(f"  包含 {collection_count} 个 collections: {collection_ids}")

        # 检查 features 是否为空
        if not features:
            logger.warning(f"  跳过: features 为空，无法导出")
            skip_count += 1
            continue

        # 创建分组输出目录
        group_output_dir = args.output_dir / group_dir_name
        logger.info(f"  输出目录: {group_output_dir}")

        try:
            # 创建导出器并导出
            exporter = APIDatasetExporter(group_output_dir, args.api_url)
            ok = exporter.export_collections(
                collection_ids=collection_ids,
                task_ids=None,  # 已通过 collection_ids 指定
                capture_devices=None,  # 已在分组时筛选
                operators=None,  # 已在分组时筛选
                auto_fix_indices=auto_fix,
                task_name_prefix=args.task_name_prefix,
                use_tos_internal_endpoint=args.use_tos_internal_endpoint,
                fetch_annotations=args.fetch_annotations,
                from_date=None,  # 已在分组时筛选
                to_date=None,  # 已在分组时筛选
                from_timestamp=None,  # 已在分组时筛选
                to_timestamp=None,  # 已在分组时筛选
                annotated_only=args.annotated_only,
                invalid_only=args.invalid_only,
                include_unchecked=args.include_unchecked,
                use_task_prompt_as_default=args.use_task_prompt_as_default,
                recording_limit=args.recording_limit,
                dry_run=args.dry_run,
                dagger_type=args.dagger_type,
            )

            if ok:
                logger.info(f"  导出成功!")
                success_count += 1
            else:
                logger.error(f"  导出失败!")
                fail_count += 1

        except Exception as e:
            logger.exception(f"  导出异常: {e}")
            fail_count += 1

    logger.info(f"\n{'='*60}")
    logger.info("分组导出完成!")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  跳过: {skip_count}")
    logger.info(f"  失败: {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
