#!/bin/bash

if [ -z "$1" ]; then
    echo "用法: $0 <json文件路径>"
    echo "示例: $0 /mnt/vepfs01/output/yifeng/resources/frontdesk/20260118_cotrain_pi05_dual6w_ft_inve_writ_wo_dual_pp_train.json"
    exit 1
fi

JSON_FILE="$1"

cd /mnt/vepfs01/output/yifeng/resources/frontdesk && python3 -c "
import json
import sys
from pathlib import Path
import pyarrow.parquet as pq
from tqdm import tqdm

json_file = Path('$JSON_FILE')
if not json_file.exists():
    print(f'错误: JSON 文件不存在: {json_file}')
    sys.exit(1)

root = json_file.parent
with open(json_file) as f:
    datasets = json.load(f)

checked = 0
problems = []
skipped = 0

for ds_path in tqdm(datasets.keys(), desc='验证中'):
    full_path = root / ds_path
    if not full_path.exists() or not (full_path / 'meta/episodes.jsonl').exists():
        skipped += 1
        continue

    checked += 1
    try:
        total_from_meta = 0
        with open(full_path / 'meta/episodes.jsonl') as f:
            for line in f:
                total_from_meta += json.loads(line)['length']

        parquet_files = list((full_path / 'data').glob('**/*.parquet'))
        total_from_parquet = 0
        for p in parquet_files:
            try:
                total_from_parquet += len(pq.read_table(p))
            except:
                problems.append(ds_path)
                break
        else:
            if total_from_meta != total_from_parquet:
                problems.append(ds_path)
    except:
        problems.append(ds_path)

print(f'')
print(f'已检查: {checked} 个, 跳过: {skipped} 个')
if problems:
    print(f'❌ 还有 {len(problems)} 个问题')
else:
    print(f'✅ 所有已生成的 {checked} 个数据集都正常!')
"
