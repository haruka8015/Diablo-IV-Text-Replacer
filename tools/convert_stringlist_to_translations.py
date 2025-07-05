#!/usr/bin/env python3
"""
StringList_en.json と StringList_jp.json から translations.json を生成するスクリプト
Diablo IVの各シーズンのStringListファイルに対応
"""

import json
import sys
import re
from collections import OrderedDict
import os

def load_json(filename):
    """JSONファイルを読み込む"""
    print(f"Loading {filename}...")
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(data, filename):
    """辞書をJSONファイルとして保存（キーの長さ順にソート）"""
    # キーの長さで降順ソート（長いキーを優先）、同じ長さはアルファベット順
    sorted_data = OrderedDict(sorted(data.items(), key=lambda x: (-len(x[0]), x[0])))
    
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(sorted_data, file, ensure_ascii=False, indent=4)
    print(f"Saved {len(sorted_data)} translations to {filename}")

def is_usable_translation(key, value):
    """変換が実際に使用可能かチェック"""
    # 改行を含む場合は除外（HTMLでは分割される）
    if '\r\n' in key:
        return False
    
    # ゲーム固有のフォーマットタグを含む場合は除外
    if any(tag in key for tag in ['{c_', '{/c}', '{icon:', '{/', '{VALUE', '{vALUE', '{Value']):
        return False
    
    # 非常に長い文字列は除外（200文字以上）
    if len(key) >= 200:
        return False
    
    # 複雑すぎる正規表現は除外（特殊文字が多すぎる）
    special_chars = len(re.findall(r'[\\()|[\]{}+*?^$.]', key))
    if special_chars > 10:
        return False
    
    # 空の値は除外
    if not value or not value.strip():
        return False
    
    return True

def filter_translations(translations):
    """使用可能な変換のみをフィルタリング"""
    filtered = {}
    rejected_count = 0
    
    for key, value in translations.items():
        if is_usable_translation(key, value):
            filtered[key] = value
        else:
            rejected_count += 1
    
    print(f"Filtered out {rejected_count} unusable translations")
    return filtered

def clean_value(value):
    """値のクリーニング（色タグや不要な記号を除去）"""
    if not value:
        return ""
    
    # カラータグを除去しつつ、内容は残す
    value = re.sub(r'\{c_\w+\}(.*?)\{/c\}', r'\1', value)
    value = re.sub(r'\{c:[0-9A-Fa-f]{6,8}\}(.*?)\{/c:[0-9A-Fa-f]{6,8}\}', r'\1', value)
    value = re.sub(r'\{c:[0-9A-Fa-f]{6,8}\}(.*?)\{/c\}', r'\1', value)
    
    # その他のタグを除去
    value = re.sub(r'\{/c_\w+\}', '', value)
    value = re.sub(r'\{c_\w+\}', '', value)
    value = re.sub(r'\{/c\}', '', value)
    
    return value.strip()

def create_regex_pattern(eng_value, jp_value):
    """英語と日本語の値から正規表現パターンを作成"""
    # 数値プレースホルダーを検出
    placeholders = re.findall(r'\{VALUE\d*%?\}|\{s\d+\}|\[(.*?)\]', eng_value)
    
    if not placeholders:
        return None, None
    
    # 正規表現パターンを作成
    pattern = eng_value
    replacement = jp_value
    
    # プレースホルダーを正規表現に変換
    for i, placeholder in enumerate(placeholders):
        if placeholder.startswith('{VALUE'):
            # 数値パターン（カンマ区切りの数値も含む）
            pattern = pattern.replace(placeholder, r'([+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\.\d+)')
            replacement = replacement.replace(placeholder, f'${i+1}')
        elif placeholder.startswith('{s'):
            # 文字列パターン
            pattern = pattern.replace(placeholder, r'(.*?)')
            replacement = replacement.replace(placeholder, f'${i+1}')
        elif placeholder.startswith('[') and placeholder.endswith(']'):
            # 範囲パターン [X-Y]
            pattern = pattern.replace(f'[{placeholder}]', r'\[(\d+)-(\d+)\]')
            replacement = replacement.replace(f'[{placeholder}]', '[$1-$2]')
    
    return pattern, replacement

def extract_attribute_descriptions(eng_data, jp_data):
    """AttributeDescriptions.stl から変換ルールを抽出"""
    translations = {}
    
    eng_attrs = eng_data.get('AttributeDescriptions.stl', {})
    jp_attrs = jp_data.get('AttributeDescriptions.stl', {})
    
    for key, eng_value in eng_attrs.items():
        if key not in jp_attrs:
            continue
            
        jp_value = jp_attrs[key]
        
        # 値をクリーニング
        eng_clean = clean_value(eng_value)
        jp_clean = clean_value(jp_value)
        
        if not eng_clean or not jp_clean or eng_clean == jp_clean:
            continue
        
        # 正規表現パターンの作成を試みる
        pattern, replacement = create_regex_pattern(eng_value, jp_value)
        
        if pattern and replacement:
            # 正規表現パターンとして追加
            translations[pattern] = replacement
        else:
            # 単純な置換として追加
            translations[eng_clean] = jp_clean
    
    return translations

def extract_item_names(eng_data, jp_data):
    """アイテム名の変換ルールを抽出"""
    translations = {}
    
    # アイテムタイプのパターン
    item_patterns = [
        r'^ItemType_.*\.stl$',
        r'^Item_.*_Unique.*\.stl$',
        r'^Item_.*_Legendary.*\.stl$',
        r'^Item_Rune_.*\.stl$'
    ]
    
    for key in eng_data:
        # アイテム関連のキーをチェック
        if not any(re.match(pattern, key) for pattern in item_patterns):
            continue
            
        if key not in jp_data:
            continue
            
        eng_item = eng_data[key]
        jp_item = jp_data[key]
        
        # Nameフィールドを抽出
        if isinstance(eng_item, dict) and 'Name' in eng_item and isinstance(jp_item, dict) and 'Name' in jp_item:
            eng_name = clean_value(eng_item['Name'])
            jp_name = clean_value(jp_item['Name'])
            
            if eng_name and jp_name and eng_name != jp_name:
                translations[eng_name] = jp_name
    
    return translations

def extract_powers_and_aspects(eng_data, jp_data):
    """パワーと化身の変換ルールを抽出"""
    translations = {}
    
    # パワーと化身のパターン
    power_patterns = [
        r'^Power_.*\.stl$',
        r'^Affix_legendary_.*\.stl$',
        r'^Affix_S05_BSK_.*\.stl$',
        r'^Affix_x1_legendary_.*\.stl$',
        r'^CollectiblePower_.*\.stl$'
    ]
    
    for key in eng_data:
        if not any(re.match(pattern, key) for pattern in power_patterns):
            continue
            
        if key not in jp_data:
            continue
            
        eng_power = eng_data[key]
        jp_power = jp_data[key]
        
        # NameまたはnameフィールドをチェックPower_*)
        name_field = 'Name' if 'Name' in eng_power else 'name' if 'name' in eng_power else None
        
        if name_field and isinstance(eng_power, dict) and isinstance(jp_power, dict):
            eng_name = clean_value(eng_power.get(name_field, ''))
            jp_name = clean_value(jp_power.get(name_field, ''))
            
            if eng_name and jp_name and eng_name != jp_name:
                # 基本形を追加
                translations[eng_name] = jp_name
                
            # Ultimate（奥義）のMod（スキル強化）も抽出
            if 'Ultimate' in key:
                for mod_key in eng_power:
                    if 'Mod' in mod_key and '_Name' in mod_key:
                        eng_mod = clean_value(eng_power.get(mod_key, ''))
                        jp_mod = clean_value(jp_power.get(mod_key, ''))
                        if eng_mod and jp_mod and eng_mod != jp_mod:
                            translations[eng_mod] = jp_mod
                
                # Aspectバリエーションを追加（Affixの場合）
                if key.startswith('Affix_'):
                    # "of XXX" 形式
                    if eng_name.startswith('of '):
                        translations[f"Aspect {eng_name}"] = f"{jp_name}化身"
                    else:
                        translations[f"{eng_name} Aspect"] = f"{jp_name}化身"
    
    return translations

def extract_skill_names(eng_data, jp_data):
    """スキル名の変換ルールを抽出"""
    translations = {}
    
    # スキル関連のパターン
    skill_patterns = [
        r'^Skill_.*\.stl$',
        r'^SkillTagNames\.stl$'
    ]
    
    for key in eng_data:
        if not any(re.match(pattern, key) for pattern in skill_patterns):
            continue
            
        if key not in jp_data:
            continue
            
        eng_skills = eng_data[key]
        jp_skills = jp_data[key]
        
        if isinstance(eng_skills, dict) and isinstance(jp_skills, dict):
            for sub_key, eng_value in eng_skills.items():
                if sub_key in jp_skills:
                    eng_clean = clean_value(str(eng_value))
                    jp_clean = clean_value(str(jp_skills[sub_key]))
                    
                    if eng_clean and jp_clean and eng_clean != jp_clean:
                        translations[eng_clean] = jp_clean
    
    return translations

def merge_with_existing(new_translations, existing_file):
    """既存のtranslations.jsonとマージ"""
    existing = {}
    
    if os.path.exists(existing_file):
        print(f"Loading existing translations from {existing_file}...")
        existing = load_json(existing_file)
        print(f"Found {len(existing)} existing translations")
    
    # 新しい変換を既存の変換とマージ（既存のものを優先）
    merged = new_translations.copy()
    merged.update(existing)  # 既存の変換で上書き
    
    print(f"Merged translations: {len(merged)} total ({len(existing)} existing, {len(new_translations)} new)")
    return merged

def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print("Usage: python convert_stringlist_to_translations.py <output_file> --en <en_file> --jp <jp_file> [options]")
        print("\nRequired:")
        print("  --en <file>      : English StringList file")
        print("  --jp <file>      : Japanese StringList file")
        print("\nOptions:")
        print("  --merge-existing : Merge with existing translations.json")
        print("  --no-filter      : Skip filtering (include all translations)")
        print("\nExamples:")
        print("  # Basic usage")
        print("  python convert_stringlist_to_translations.py output.json --en temp/StringList_en.json --jp temp/StringList_jp.json")
        print("\n  # Merge with existing translations")
        print("  python convert_stringlist_to_translations.py ../sources/translations.json --en temp/S10_StringList_en.json --jp temp/S10_StringList_jp.json --merge-existing")
        return
    
    output_file = sys.argv[1]
    merge_existing = '--merge-existing' in sys.argv
    skip_filter = '--no-filter' in sys.argv
    
    # デフォルトファイルパス
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(os.path.dirname(script_dir), 'temp')
    sources_dir = os.path.join(os.path.dirname(script_dir), 'sources')
    
    # コマンドライン引数からファイルパスを取得
    eng_file = None
    jp_file = None
    
    # 引数を解析
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--en' and i + 1 < len(sys.argv):
            eng_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--jp' and i + 1 < len(sys.argv):
            jp_file = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # デフォルト値を設定（必須）
    if not eng_file or not jp_file:
        print("Error: Both --en and --jp files must be specified")
        print("Example: python convert_stringlist_to_translations.py output.json --en temp/StringList_en.json --jp temp/StringList_jp.json")
        return
    
    existing_translations = os.path.join(sources_dir, 'translations.json')
    
    # ファイルの存在確認
    if not os.path.exists(eng_file):
        print(f"Error: {eng_file} not found")
        return
    if not os.path.exists(jp_file):
        print(f"Error: {jp_file} not found")
        return
    
    # JSONファイルを読み込む
    eng_data = load_json(eng_file)
    jp_data = load_json(jp_file)
    
    print("Extracting translations...")
    
    # 各カテゴリから変換ルールを抽出
    all_translations = {}
    
    # 1. AttributeDescriptions
    print("Extracting attribute descriptions...")
    attr_translations = extract_attribute_descriptions(eng_data, jp_data)
    all_translations.update(attr_translations)
    print(f"  Found {len(attr_translations)} attribute translations")
    
    # 2. アイテム名
    print("Extracting item names...")
    item_translations = extract_item_names(eng_data, jp_data)
    all_translations.update(item_translations)
    print(f"  Found {len(item_translations)} item translations")
    
    # 3. パワーと化身
    print("Extracting powers and aspects...")
    power_translations = extract_powers_and_aspects(eng_data, jp_data)
    all_translations.update(power_translations)
    print(f"  Found {len(power_translations)} power/aspect translations")
    
    # 4. スキル名
    print("Extracting skill names...")
    skill_translations = extract_skill_names(eng_data, jp_data)
    all_translations.update(skill_translations)
    print(f"  Found {len(skill_translations)} skill translations")
    
    print(f"\nTotal new translations extracted: {len(all_translations)}")
    
    # 使用可能な変換のみをフィルタリング（オプション）
    if not skip_filter:
        print("\nFiltering unusable translations...")
        all_translations = filter_translations(all_translations)
        print(f"Usable translations: {len(all_translations)}")
    else:
        print("\nSkipping filter (--no-filter option used)")
    
    # 既存の変換とマージ（オプション）
    if merge_existing:
        all_translations = merge_with_existing(all_translations, existing_translations)
    
    # 保存
    save_json(all_translations, output_file)
    print(f"\nTranslations saved to {output_file}")
    
    # 統計情報を表示
    print("\nTranslation statistics:")
    regex_count = sum(1 for k in all_translations.keys() if any(c in k for c in ['(', ')', '[', ']', '\\', '$', '^', '*', '+', '?', '{', '}']))
    print(f"  - Regular expressions: {regex_count}")
    print(f"  - Simple replacements: {len(all_translations) - regex_count}")

if __name__ == "__main__":
    main()