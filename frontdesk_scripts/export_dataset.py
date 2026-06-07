#!/usr/bin/env python3
"""
LeRobot 数据集导出工具

该脚本支持从服务端导出一个或多个 collection，并合并为一个 LeRobot 数据集。如果您是saas用户，请在导出命令行中添加--user phone_number --password password来登录。
"""

from __future__ import annotations

import argparse
import json
import logging
import math
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

    def __init__(
        self,
        output_dir: Path,
        api_base_url: str,
        session: requests.Session | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.api_base_url = api_base_url.rstrip("/")
        self.session = session if session is not None else requests.Session()
        self._create_directory_structure()

    def _login(self, identifier: str, password: str) -> None:
        login_url = f"{self.api_base_url}/api/v2/public/login"
        payload = {
            "identifier": identifier,
            "password": password,
        }

        def _raise_login_error(msg: str) -> None:
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"正在登录: {identifier}")

        try:
            response = self.session.post(login_url, json=payload, timeout=30)
            if response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNAUTHORIZED):
                error_msg = response.json().get("message", "登录失败")
                _raise_login_error(f"登录失败: {error_msg}")
            response.raise_for_status()

            response_data = response.json()
            if "data" not in response_data:
                _raise_login_error("登录响应格式错误: 缺少 data 字段")

            data = response_data["data"]
            access_token = data.get("access_token")
            if not access_token:
                _raise_login_error("登录响应格式错误: 缺少 access_token 字段")

            self.session.headers["Authorization"] = f"Bearer {access_token}"
            logger.info("登录成功")

        except requests.RequestException:
            logger.exception("登录请求失败")
            raise
        except ValueError:
            raise

    def _create_directory_structure(self) -> None:
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
        fetch_annotations_from_api: bool = False,
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
        use_chinese_annotation: bool = False,
        collection_batch_size: int = 30,
        use_post_api: bool = False,
        dagger_type: str | None = None,
    ) -> bool:
        logger.info(f"开始导出采集批次: {collection_ids}")

        dataset_json_path = self.output_dir / "dataset.json"
        if dataset_json_path.exists():
            with open(dataset_json_path, encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            if use_post_api:
                dataset = self._fetch_dataset_post(
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
                    collection_batch_size,
                    dagger_type,
                )
            else:
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
                    collection_batch_size,
                    dagger_type,
                )

            with open(self.output_dir / "dataset.json", "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)

        task_names = dataset["task_name"].split("+")
        if not all(task_name.startswith(task_name_prefix) for task_name in task_names):
            msg = f"任务名称不匹配: {dataset['task_name']} != {task_name_prefix}"
            raise ValueError(msg)

        logger.info(
            f"获取到数据集信息: {len(dataset['episodes'])} 个episodes, {len(dataset['files'])} 个文件",
        )

        if fetch_annotations:
            annotations_json_path = self.output_dir / "annotations.json"
            if annotations_json_path.exists():
                with open(annotations_json_path, encoding="utf-8") as f:
                    annotations = json.load(f)
                    count = sum(1 for _, annotation in annotations.items() if annotation is not None)
                    logger.info(f"从 {annotations_json_path} 加载了 {count} 个标注结果")
                    annotations = {int(k): v for k, v in annotations.items()}
            else:
                if fetch_annotations_from_api:
                    logger.info("从 API 接口拉取标注结果...")
                    try:
                        annotations = self._fetch_annotations_concurrently(
                            dataset["recording_ids"],
                            max_workers=10,
                            max_retries=3,
                        )
                        count = sum(1 for _, annotation in annotations.items() if annotation is not None)
                        logger.info(f"从 API 拉取了 {count} 个标注结果")
                        with open(annotations_json_path, "w", encoding="utf-8") as f:
                            json.dump(annotations, f, ensure_ascii=False, indent=2)
                        logger.info(f"标注结果已保存到: {annotations_json_path}")
                    except Exception:
                        logger.exception("从 API 拉取标注结果失败")
                        return False
                else:
                    logger.info("从 dataset.json 中提取标注数据...")
                    try:
                        annotations = self._extract_annotations_from_dataset(dataset)
                        count = sum(1 for _, annotation in annotations.items() if annotation is not None)
                        logger.info(f"从 dataset.json 提取了 {count} 个标注结果")
                        with open(annotations_json_path, "w", encoding="utf-8") as f:
                            json.dump(annotations, f, ensure_ascii=False, indent=2)
                        logger.info(f"标注结果已保存到: {annotations_json_path}")
                    except Exception:
                        logger.exception("从 dataset.json 提取标注数据失败")
                        return False
        else:
            annotations = {}

        self._generate_meta_files(dataset, annotations, use_chinese_annotation)

        if dry_run:
            logger.info("dry_run 模式，跳过下载数据文件")
            return True

        failed_files = self._download_files(dataset["files"])

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

        if fetch_annotations:
            self._reset_task_index_with_annotation(
                dataset,
                annotations,
                use_chinese_annotation,
            )
        else:
            self._reset_task_index(dataset)

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
        collection_batch_size: int = 30,
        dagger_type: str | None = None,
    ) -> dict[str, Any]:
        params = []

        for cid in collection_ids:
            params.append(f"collection_ids={cid}")

        if task_ids:
            for tid in task_ids:
                params.append(f"task_ids={tid}")

        if capture_devices:
            for device in capture_devices:
                params.append(f"capture_devices={device}")

        if operators:
            for operator in operators:
                params.append(f"operators={urllib.parse.quote(operator)}")

        if use_tos_internal_endpoint:
            params.append("use_tos_internal_endpoint=true")

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

        if dagger_type:
            params.append(f"dagger_type={dagger_type}")

        params.append(f"old={'true' if old else 'false'}")
        params.append(f"batch_size={collection_batch_size}")

        url = f"{self.api_base_url}/api/v1/data_collections/collections/export_dataset?{'&'.join(params)}"
        logger.info(f"调用 GET API: {url}")

        try:
            response = self.session.get(url, timeout=300)
            if response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY):
                raise ValueError(response.json())
            response.raise_for_status()
            dataset: dict[str, Any] = response.json()["data"]
        except requests.RequestException:
            logger.exception("API调用失败")
            raise
        else:
            return dataset

    def _extract_annotations_from_dataset(
        self,
        dataset: dict[str, Any],
    ) -> dict[int, dict[str, Any] | None]:
        annotations = {}

        for idx, episode in enumerate(dataset["episodes"]):
            recording_id = dataset["recording_ids"][idx]

            annotation = episode.get("annotation")
            if annotation is None:
                annotations[recording_id] = None
                logger.debug(f"Recording {recording_id} 没有标注数据")
                continue

            annotation_data = annotation.get("annotation_data")
            if annotation_data is None:
                annotations[recording_id] = None
                logger.debug(f"Recording {recording_id} 的 annotation_data 为空")
                continue

            if not isinstance(annotation_data, dict):
                logger.warning(
                    f"Recording {recording_id} 的 annotation_data 格式不正确: {type(annotation_data)}"
                )
                annotations[recording_id] = None
                continue

            required_fields = ["version", "data"]
            missing_fields = [field for field in required_fields if field not in annotation_data]
            if missing_fields:
                logger.warning(
                    f"Recording {recording_id} 的 annotation_data 缺少必要字段: {missing_fields}"
                )
                annotations[recording_id] = None
                continue

            if annotation.get("id") is not None:
                annotation_data["id"] = annotation.get("id")
            if annotation.get("created_at") is not None:
                annotation_data["created_at"] = annotation.get("created_at")
            if annotation_data.get("annotator_name") is None:
                annotation_data["annotator_name"] = annotation.get("annotator_name")

            annotations[recording_id] = annotation_data
            logger.debug(f"成功提取 Recording {recording_id} 的标注数据")

        return annotations

    def _fetch_dataset_post(
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
        collection_batch_size: int = 30,
        dagger_type: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_base_url}/api/v1/data_collections/collections/export_dataset"
        logger.info(f"调用 POST API: {url}")

        payload: dict[str, Any] = {
            "collection_ids": collection_ids,
            "use_tos_internal_endpoint": use_tos_internal_endpoint,
            "annotated_only": annotated_only,
            "invalid_only": invalid_only,
            "include_unchecked": include_unchecked,
            "use_task_prompt_as_default": use_task_prompt_as_default,
            "old": old,
            "batch_size": collection_batch_size,
        }

        if task_ids:
            payload["task_ids"] = task_ids
        if capture_devices:
            payload["capture_devices"] = capture_devices
        if operators:
            payload["operators"] = operators
        if from_date:
            payload["from_date"] = from_date.strftime("%Y-%m-%d")
        if to_date:
            payload["to_date"] = to_date.strftime("%Y-%m-%d")
        if from_timestamp:
            payload["from_timestamp"] = from_timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        if to_timestamp:
            payload["to_timestamp"] = to_timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        if recording_limit:
            payload["recording_limit"] = recording_limit
        if annotation_version:
            payload["annotation_version"] = annotation_version
        if dagger_type:
            payload["dagger_type"] = dagger_type

        try:
            response = self.session.post(url, json=payload, timeout=300)
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
        actions = []
        if annotation.get("version") == "3.0.0":
            actions = annotation["data"]
        elif "annotation" in annotation:
            actions = [
                {
                    "start_time": action["start"],
                    "end_time": action["end"],
                    "action": action["description"],
                }
                for action in annotation["annotation"]["actionAnnotationList"]
            ]
        return actions

    def _get_action_name(
        self,
        action: dict[str, str],
        use_chinese: bool = False,
    ) -> str:
        if use_chinese:
            return action.get("action") or action.get("action_english", "unknown")
        return action.get("action_english") or action.get("action", "unknown")

    def _generate_meta_files(
        self,
        dataset: dict[str, Any],
        annotations: dict[int, dict[str, Any] | None],
        use_chinese_annotation: bool = False,
    ) -> None:
        logger.info("生成元数据文件...")

        if annotations:
            tasks: set[str] = set()
            for annotation in annotations.values():
                if annotation is None:
                    continue
                actions = self._extract_actions_from_annotation(annotation)
                tasks.update(self._get_action_name(action, use_chinese_annotation) for action in actions)

            for idx, episode in enumerate(dataset["episodes"]):
                recording_id = dataset["recording_ids"][idx]
                annotation = annotations.get(recording_id)
                if annotation is None:
                    episode["tasks"] = ["unknown"]
                    continue
                actions = self._extract_actions_from_annotation(annotation)
                episode_tasks = [
                    self._get_action_name(action, use_chinese_annotation) for action in actions
                ]
                episode["tasks"] = episode_tasks
                tasks.update(episode_tasks)
            dataset["tasks"] = [{"task_index": 0, "task": "unknown"}]
            dataset["tasks"].extend(
                [{"task_index": idx + 1, "task": task} for idx, task in enumerate(sorted(tasks))],
            )
            dataset["info"]["total_tasks"] = len(dataset["tasks"])

        info_json_path = self.meta_dir / "info.json"
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(dataset["info"], f, ensure_ascii=False, indent=2)
        logger.info(f"生成 info.json: {info_json_path}")

        tasks_jsonl_path = self.meta_dir / "tasks.jsonl"
        with open(tasks_jsonl_path, "w", encoding="utf-8") as f:
            for task_data in dataset["tasks"]:
                f.write(json.dumps(task_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 tasks.jsonl: {tasks_jsonl_path} ({len(dataset['tasks'])} 个任务)")

        episodes_jsonl_path = self.meta_dir / "episodes.jsonl"
        with open(episodes_jsonl_path, "w", encoding="utf-8") as f:
            for episode_data in dataset["episodes"]:
                f.write(json.dumps(episode_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 episodes.jsonl: {episodes_jsonl_path}")

        episodes_stats_jsonl_path = self.meta_dir / "episodes_stats.jsonl"
        with open(episodes_stats_jsonl_path, "w", encoding="utf-8") as f:
            for stats_data in dataset["episode_stats"]:
                f.write(json.dumps(stats_data, ensure_ascii=False) + "\n")
        logger.info(f"生成 episodes_stats.jsonl: {episodes_stats_jsonl_path}")

    def _download_files(self, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        logger.info(f"准备下载 {len(files)} 个文件")

        failed_files = []

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
        file_path = file_info["path"]
        download_url = file_info["download_url"]

        target_path = self.output_dir / file_path

        if target_path.exists() and target_path.stat().st_size > 0:
            logger.debug(f"文件已存在，跳过下载: {target_path}")
            return

        target_path.parent.mkdir(parents=True, exist_ok=True)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(download_url, stream=True, timeout=60)
                response.raise_for_status()

                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                logger.debug(f"下载成功: {target_path}")

            except Exception as e:
                if target_path.exists():
                    target_path.unlink()

                if attempt < max_retries - 1:
                    logger.warning(
                        f"下载文件失败 (尝试 {attempt + 1}/{max_retries}): {file_path}, 错误: {e}",
                    )
                    time.sleep(2**attempt)
                else:
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
        url = f"{self.api_base_url}/api/v1/data_collections/recordings/{recording_id}/latest_annotation"

        for attempt in range(max_retries + 1):
            try:
                response = session.get(url, timeout=30)
                if response.status_code == HTTPStatus.NOT_FOUND:
                    logger.debug(f"Recording {recording_id} 没有标注结果")
                    return recording_id, None

                response.raise_for_status()
                annotation_data = response.json()

                if (annotation_data.get("version") == "3.0.0" and not annotation_data["data"]) or (
                    "annotation" in annotation_data
                    and not annotation_data["annotation"]["actionAnnotationList"]
                ):
                    logger.debug(f"Recording {recording_id} 没有标注结果")
                    return recording_id, None

                logger.debug(f"成功获取 Recording {recording_id} 的标注结果")

            except requests.RequestException:
                if attempt < max_retries:
                    wait_time = 2**attempt
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
        logger.info(f"开始并发拉取 {len(recording_ids)} 个录制的标注结果")

        annotations = {}
        session = requests.Session()

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_recording = {
                    executor.submit(
                        self._fetch_single_annotation,
                        session,
                        recording_id,
                        max_retries,
                    ): recording_id
                    for recording_id in recording_ids
                }

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
        for task in dataset["tasks"]:
            if task["task"] == task_name:
                return int(task["task_index"])
        return 0

    def _reset_task_index(
        self,
        dataset: dict[str, Any],
    ) -> None:
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
                task_id_mapping = {
                    int(task_id): self._get_task_index(dataset, task_name)
                    for task_id, task_name in task_id_map.items()
                }
                df["task_index"] = df["task_index"].map(task_id_mapping).fillna(0).astype(int)
            else:
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
        use_chinese_annotation: bool = False,
    ) -> None:
        fps = dataset["info"]["fps"]
        for idx in range(dataset["info"]["total_episodes"]):
            recording_id = dataset["recording_ids"][idx]
            annotation = annotations.get(recording_id)
            if annotation is None:
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
                    start_frame = math.floor(action["start_time"] * fps)
                    end_frame = math.ceil(action["end_time"] * fps)
                    task_index = self._get_task_index(
                        dataset,
                        self._get_action_name(action, use_chinese_annotation),
                    )
                    df.loc[start_frame:end_frame, "task_index"] = task_index
            df.to_parquet(parquet_path, index=False)


def fix_parquet_indices(dataset_dir: Path) -> bool:
    logger.info(f"开始修复数据集中的parquet文件: {dataset_dir}")

    episodes_file = dataset_dir / "meta" / "episodes.jsonl"
    if not episodes_file.exists():
        logger.error(f"未找到episodes元数据文件: {episodes_file}")
        return False

    episode_lengths = {}
    with open(episodes_file, encoding="utf-8") as f:
        for line in f:
            episode_data = json.loads(line.strip())
            episode_idx = episode_data["episode_index"]
            episode_length = episode_data["length"]
            episode_lengths[episode_idx] = episode_length

    logger.info(f"加载了 {len(episode_lengths)} 个episode的元数据")

    data_dir = dataset_dir / "data"
    if not data_dir.exists():
        logger.warning(f"数据目录不存在: {data_dir}")
        return False

    episode_files = list(data_dir.glob("chunk-*/episode_*.parquet"))

    if not episode_files:
        logger.warning(f"在 {data_dir} 中未找到episode_*.parquet文件")
        return False

    logger.info(f"找到 {len(episode_files)} 个episode文件")

    episode_info = []
    for file_path in episode_files:
        try:
            chunk_id = int(file_path.parent.name.split("-")[1])
            filename = file_path.stem
            if filename.startswith("episode_"):
                episode_idx = int(filename[8:])
                episode_info.append((chunk_id, episode_idx, file_path))
            else:
                logger.warning(f"文件名格式不符合预期: {file_path}")
        except ValueError:
            logger.warning(f"无法解析episode索引: {file_path}")

    episode_info.sort(key=lambda x: (x[0], x[1]))

    if len(episode_info) != len(episode_lengths):
        logger.error(f"文件数量与元数据不一致！实际: {len(episode_info)}, 预期: {len(episode_lengths)}")
        return False

    global_index_counter = 0
    validation_errors = 0

    for chunk_id, episode_idx, file_path in episode_info:
        logger.debug(f"处理Episode {episode_idx} (chunk {chunk_id}): {file_path}")

        try:
            df = pd.read_parquet(file_path)
            actual_length = len(df)

            if actual_length == 0:
                logger.warning(f"文件为空，跳过: {file_path}")
                continue

            expected_length = episode_lengths.get(episode_idx)
            if expected_length is not None and actual_length != expected_length:
                logger.error(
                    f"Episode {episode_idx} 行数不匹配！实际: {actual_length}, 预期: {expected_length}",
                )
                validation_errors += 1
            else:
                logger.debug(f"Episode {episode_idx} 行数验证通过: {actual_length}")

            if "episode_index" not in df.columns:
                logger.warning(f"文件中没有episode_index列，跳过: {file_path}")
                continue

            df["episode_index"] = episode_idx
            df["index"] = range(global_index_counter, global_index_counter + actual_length)

            df.to_parquet(file_path, index=False)

            logger.debug(
                f"Episode {episode_idx}: {actual_length} 行, "
                f"index范围: {global_index_counter} ~ {global_index_counter + actual_length - 1}",
            )

            global_index_counter += actual_length

        except Exception:
            logger.exception(f"处理Episode {episode_idx}文件失败: {file_path}")
            raise

    if validation_errors > 0:
        logger.warning(f"修复完成，但发现 {validation_errors} 个行数验证错误！")
    else:
        logger.info("修复完成，所有episode文件行数验证通过！")

    logger.info(f"总共处理 {len(episode_info)} 个episode文件，全局index总数: {global_index_counter}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过API导出 LeRobot 数据集")
    parser.add_argument("--task-name-prefix", type=str, required=False, default="")
    parser.add_argument("--collection-ids", type=int, nargs="*", required=False, default=[])
    parser.add_argument("--task-ids", type=int, nargs="*", default=[])
    parser.add_argument("--capture-devices", type=str, nargs="*", default=[])
    parser.add_argument("--operators", type=str, nargs="*", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--api-url", type=str, default="https://quanta.i.spirit-ai.com")
    parser.add_argument("--no-fix-indices", action="store_true")
    parser.add_argument("--use-tos-internal-endpoint", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--fetch-annotations", action="store_true")
    parser.add_argument("--fetch-annotations-from-api", action="store_true")
    parser.add_argument("--from-date", type=lambda x: datetime.strptime(x, "%Y-%m-%d").date())
    parser.add_argument("--to-date", type=lambda x: datetime.strptime(x, "%Y-%m-%d").date())
    parser.add_argument("--from-timestamp", type=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
    parser.add_argument("--to-timestamp", type=lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S"))
    parser.add_argument("--annotated-only", action="store_true")
    parser.add_argument("--invalid-only", action="store_true")
    parser.add_argument("--include-unchecked", action="store_true")
    parser.add_argument("--use-task-prompt-as-default", action="store_true")
    parser.add_argument("--recording-limit", type=int)
    parser.add_argument("--annotation-version", type=int)
    parser.add_argument("--dagger-type", type=str, choices=["policy", "teleop"], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--old", action="store_true")
    parser.add_argument("--group-by-features", action="store_true")
    parser.add_argument("--use-chinese-annotation", action="store_true")
    parser.add_argument("--user", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--collection-batch-size", type=int, default=30)
    parser.add_argument("--use-post-api", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.collection_ids and not args.task_ids:
        logger.error("collection_ids 和 task_ids 不能同时为空")
        sys.exit(1)

    if args.use_task_prompt_as_default and args.fetch_annotations:
        logger.error("不能同时指定 use_task_prompt_as_default 和 fetch_annotations")
        sys.exit(1)

    if args.group_by_features and not args.task_ids:
        logger.error("--group-by-features 需要指定 --task-ids")
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        auto_fix = not args.no_fix_indices

        if args.group_by_features:
            export_with_grouping(args, auto_fix)
        else:
            exporter = APIDatasetExporter(args.output_dir, args.api_url)

            if args.user and args.password:
                try:
                    exporter._login(args.user, args.password)
                except (requests.RequestException, ValueError) as e:
                    logger.error(f"登录失败: {e}")
                    sys.exit(1)
            elif args.user or args.password:
                logger.error("--user 和 --password 必须同时提供")
                sys.exit(1)

            ok = exporter.export_collections(
                args.collection_ids,
                task_ids=args.task_ids if args.task_ids else None,
                capture_devices=args.capture_devices if args.capture_devices else None,
                operators=args.operators if args.operators else None,
                auto_fix_indices=auto_fix,
                task_name_prefix=args.task_name_prefix,
                use_tos_internal_endpoint=args.use_tos_internal_endpoint,
                fetch_annotations=args.fetch_annotations,
                fetch_annotations_from_api=args.fetch_annotations_from_api,
                from_date=args.from_date,
                to_date=args.to_date,
                from_timestamp=getattr(args, "from_timestamp", None),
                to_timestamp=getattr(args, "to_timestamp", None),
                annotated_only=args.annotated_only,
                invalid_only=args.invalid_only,
                include_unchecked=args.include_unchecked,
                use_task_prompt_as_default=args.use_task_prompt_as_default,
                recording_limit=args.recording_limit,
                annotation_version=args.annotation_version,
                dry_run=args.dry_run,
                use_chinese_annotation=args.use_chinese_annotation,
                old=args.old,
                collection_batch_size=args.collection_batch_size,
                use_post_api=args.use_post_api,
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
    session: requests.Session | None = None,
) -> dict[str, Any]:
    api_base_url = api_base_url.rstrip("/")

    if session is None:
        session = requests.Session()

    params = []

    for tid in task_ids:
        params.append(f"task_ids={tid}")

    if capture_devices:
        for device in capture_devices:
            params.append(f"capture_devices={device}")

    if operators:
        for operator in operators:
            params.append(f"operators={urllib.parse.quote(operator)}")

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
        response = session.get(url, timeout=60)
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
    session = requests.Session()

    if args.user and args.password:
        try:
            temp_exporter = APIDatasetExporter(args.output_dir, args.api_url, session)
            temp_exporter._login(args.user, args.password)
        except (requests.RequestException, ValueError) as e:
            logger.error(f"登录失败: {e}")
            sys.exit(1)
    elif args.user or args.password:
        logger.error("--user 和 --password 必须同时提供")
        sys.exit(1)

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
        session=session,
    )

    groups = groups_result.get("groups", [])
    total_groups = groups_result.get("total_groups", 0)
    total_collections = groups_result.get("total_collections", 0)

    logger.info(f"共 {total_collections} 个 collections，分为 {total_groups} 组")

    if not groups:
        logger.warning("没有找到任何 collections")
        return

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, group in enumerate(groups):
        features = group.get("features")
        features_hash = group.get("features_hash", f"group_{i}")
        collection_ids = group.get("collection_ids", [])
        collection_count = group.get("collection_count", len(collection_ids))

        features_len = len(features) if features else 0
        group_dir_name = f"dataset_{i}_{features_len}_{features_hash}"

        logger.info(f"\n{'=' * 60}")
        logger.info(f"处理分组 {i + 1}/{total_groups}: {group_dir_name}")
        logger.info(f"  包含 {collection_count} 个 collections: {collection_ids}")

        if not features:
            logger.warning("  跳过: features 为空，无法导出")
            skip_count += 1
            continue

        group_output_dir = args.output_dir / group_dir_name
        logger.info(f"  输出目录: {group_output_dir}")

        try:
            exporter = APIDatasetExporter(group_output_dir, args.api_url, session)
            ok = exporter.export_collections(
                collection_ids=collection_ids,
                task_ids=None,
                capture_devices=args.capture_devices if args.capture_devices else None,
                operators=args.operators if args.operators else None,
                auto_fix_indices=auto_fix,
                task_name_prefix=args.task_name_prefix,
                use_tos_internal_endpoint=args.use_tos_internal_endpoint,
                fetch_annotations=args.fetch_annotations,
                fetch_annotations_from_api=args.fetch_annotations_from_api,
                from_date=args.from_date,
                to_date=args.to_date,
                from_timestamp=getattr(args, "from_timestamp", None),
                to_timestamp=getattr(args, "to_timestamp", None),
                annotated_only=args.annotated_only,
                invalid_only=args.invalid_only,
                include_unchecked=args.include_unchecked,
                use_task_prompt_as_default=args.use_task_prompt_as_default,
                recording_limit=args.recording_limit,
                annotation_version=args.annotation_version,
                dry_run=args.dry_run,
                use_chinese_annotation=args.use_chinese_annotation,
                old=args.old,
                collection_batch_size=args.collection_batch_size,
                use_post_api=args.use_post_api,
                dagger_type=args.dagger_type,
            )
            if ok:
                logger.info("  导出成功!")
                success_count += 1
            else:
                logger.error("  导出失败!")
                fail_count += 1

        except Exception as e:
            logger.exception(f"  导出异常: {e}")
            fail_count += 1

    logger.info(f"\n{'=' * 60}")
    logger.info("分组导出完成!")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  跳过: {skip_count}")
    logger.info(f"  失败: {fail_count}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
