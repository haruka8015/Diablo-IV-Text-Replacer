import sys
import os
import re
from collections import defaultdict

def find_duplicate_keys(input_file):
    # ファイルの存在を確認
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"File {input_file} not found.")
    
    # JSONファイルをテキストとして読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    key_pattern = re.compile(r'"(.*?)"\s*:')
    key_counts = defaultdict(int)
    
    # 各行からキーを抽出し、カウントする
    for line in lines:
        match = key_pattern.search(line)
        if match:
            key = match.group(1)
            key_counts[key] += 1
    
    # 重複しているキーを抽出
    duplicate_keys = [key for key, count in key_counts.items() if count > 1]
    
    if duplicate_keys:
        print("Duplicate keys found:")
        for key in duplicate_keys:
            print(key)
    else:
        print("No duplicate keys found.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_duplicate_keys.py <input_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        find_duplicate_keys(input_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
