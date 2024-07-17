import json
import sys
import os

def sort_and_filter_json(input_file, remove_duplicates=False):
    # ファイルの存在を確認
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"File {input_file} not found.")
    
    # JSONファイルを読み込む
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # ソートする
    sorted_data = sorted(data.items(), key=lambda item: (-len(item[0]), item[0]))
    
    # 出力ファイル名を作成
    output_file = f"{os.path.splitext(input_file)[0]}_sorted.json"
    
    last_key = None
    last_value = None
    unique_data = {}
    
    # ソートされた結果をフィルタリングしながら書き込む
    with open(output_file, 'w', encoding='utf-8') as f:
        if remove_duplicates:
            for key, value in sorted_data:
                if key == last_key and value == last_value:
                    continue
                unique_data[key] = value
                last_key = key
                last_value = value
        else:
            unique_data = dict(sorted_data)
        
        json.dump(unique_data, f, ensure_ascii=False, indent=4)
    
    print(f"Sorted JSON has been saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sort_and_filter_json.py <input_json_file> [--remove-duplicates]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    remove_duplicates = '--remove-duplicates' in sys.argv
    
    try:
        sort_and_filter_json(input_file, remove_duplicates)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
