#!/usr/bin/env python3
"""
检查数据集 tasks.jsonl 文件中是否包含中文字符
"""

import json
import argparse
import re
from pathlib import Path
from collections import defaultdict


def contains_chinese(text):
    """检查文本是否包含中文字符"""
    # Unicode范围：中文汉字 一-鿿
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(chinese_pattern.search(text))


def find_chinese_chars(text):
    """找出文本中的所有中文字符"""
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return chinese_pattern.findall(text)


def check_tasks_file(tasks_file):
    """检查单个 tasks.jsonl 文件"""
    if not tasks_file.exists():
        return None, []

    results = []

    try:
        with open(tasks_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    task_data = json.loads(line)
                    task_text = task_data.get('task', '')

                    if contains_chinese(task_text):
                        chinese_chars = find_chinese_chars(task_text)
                        results.append({
                            'line': line_num,
                            'task_index': task_data.get('task_index', '?'),
                            'task': task_text,
                            'chinese': chinese_chars
                        })
                except json.JSONDecodeError:
                    continue

        return len(results) > 0, results

    except Exception as e:
        return None, [{'error': str(e)}]


def main():
    parser = argparse.ArgumentParser(
        description='检查数据集 tasks.jsonl 文件中的中文字符',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python check_chinese.py input.json
  python check_chinese.py input.json -v
  python check_chinese.py input.json --export report.json
        """
    )

    parser.add_argument('input_json', help='输入JSON文件路径')
    parser.add_argument('-b', '--base-path', default='.', help='数据集基础路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser.add_argument('--export', type=str, help='导出报告到JSON文件')

    args = parser.parse_args()

    try:
        # 读取数据集列表
        input_file = Path(args.input_json)
        with open(input_file, 'r') as f:
            data = json.load(f)

        dataset_names = list(data.keys()) if isinstance(data, dict) else data
        base_path = Path(args.base_path)

        print(f"🔍 检查 {len(dataset_names)} 个数据集的 tasks.jsonl 文件...")
        print("=" * 80)

        # 统计结果
        has_chinese = []
        no_chinese = []
        file_not_found = []
        errors = []

        detailed_report = {}

        for dataset_name in dataset_names:
            tasks_file = base_path / dataset_name / "meta" / "tasks.jsonl"

            if not tasks_file.exists():
                file_not_found.append(dataset_name)
                if args.verbose:
                    print(f"⚠ 文件不存在: {dataset_name}")
                continue

            has_cn, results = check_tasks_file(tasks_file)

            if has_cn is None:
                errors.append(dataset_name)
                if args.verbose:
                    print(f"❌ 读取错误: {dataset_name}")
                    if results:
                        print(f"   {results[0].get('error', '')}")
            elif has_cn:
                has_chinese.append(dataset_name)
                detailed_report[dataset_name] = results

                if args.verbose:
                    print(f"\n⚠️  包含中文: {dataset_name}")
                    for item in results:
                        print(f"   行 {item['line']} (task_index={item['task_index']})")
                        print(f"   任务: {item['task']}")
                        print(f"   中文: {', '.join(item['chinese'])}")
                else:
                    print(f"⚠️  包含中文: {dataset_name}")
            else:
                no_chinese.append(dataset_name)
                if args.verbose:
                    print(f"✓ 无中文: {dataset_name}")

        # 打印汇总
        print("\n" + "=" * 80)
        print("📊 检查结果汇总:")
        print("=" * 80)
        print(f"✅ 无中文字符: {len(no_chinese)} 个")
        print(f"⚠️  包含中文字符: {len(has_chinese)} 个")
        print(f"⚠  文件不存在: {len(file_not_found)} 个")
        print(f"❌ 读取错误: {len(errors)} 个")

        # 显示包含中文的数据集列表
        if has_chinese:
            print("\n" + "=" * 80)
            print("⚠️  包含中文字符的数据集:")
            print("=" * 80)
            for dataset_name in has_chinese:
                results = detailed_report.get(dataset_name, [])
                print(f"\n📁 {dataset_name} ({len(results)} 个任务)")
                if not args.verbose:
                    # 非详细模式下也显示具体任务
                    for item in results[:3]:  # 只显示前3个
                        print(f"   • {item['task']}")
                        print(f"     中文: {', '.join(item['chinese'])}")
                    if len(results) > 3:
                        print(f"   ... 还有 {len(results) - 3} 个")

        print("=" * 80)

        # 导出报告
        if args.export:
            export_data = {
                'summary': {
                    'total': len(dataset_names),
                    'no_chinese': len(no_chinese),
                    'has_chinese': len(has_chinese),
                    'file_not_found': len(file_not_found),
                    'errors': len(errors)
                },
                'datasets_with_chinese': detailed_report,
                'datasets_without_chinese': no_chinese,
                'datasets_not_found': file_not_found,
                'datasets_with_errors': errors
            }

            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"\n✅ 报告已导出到: {args.export}")

        # 返回状态码
        return 0 if len(has_chinese) == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    exit(main())
