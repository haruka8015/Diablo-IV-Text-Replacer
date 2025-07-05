#!/usr/bin/env python3
"""
Chrome拡張機能のビルドツール
既存の命名規則に従ってZIPファイルを作成
"""

import zipfile
import json
import os
import sys
from pathlib import Path
import shutil

def load_manifest():
    """manifest.jsonからバージョン情報を取得"""
    manifest_path = Path('sources/manifest.json')
    if not manifest_path.exists():
        print("Error: sources/manifest.json not found")
        sys.exit(1)
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_extension_zip(output_dir='temp'):
    """拡張機能のZIPファイルを作成"""
    # manifest.jsonを読み込んでバージョンを取得
    manifest = load_manifest()
    version = manifest.get('version', '0.0.0')
    
    # 出力ファイル名
    zip_filename = f"Diablo_Translate_{version}.zip"
    zip_path = Path(output_dir) / zip_filename
    
    # 一時ディレクトリ名（ZIP内のトップレベルディレクトリ）
    temp_dirname = "Diablo_Translate"
    
    print(f"Building extension version {version}...")
    
    # ZIPファイルを作成
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # sourcesディレクトリのすべてのファイルを追加
        sources_dir = Path('sources')
        file_count = 0
        
        for file_path in sources_dir.rglob('*'):
            if file_path.is_file():
                # ZIP内のパスを構築（Diablo_Translate/ファイル名）
                relative_path = file_path.relative_to(sources_dir)
                arcname = f"{temp_dirname}/{relative_path}"
                
                zipf.write(file_path, arcname)
                print(f"  Added: {relative_path}")
                file_count += 1
        
    # ファイルサイズを取得
    file_size = zip_path.stat().st_size / 1024  # KB
    
    print(f"\nBuild complete!")
    print(f"  Output: {zip_path}")
    print(f"  Files: {file_count}")
    print(f"  Size: {file_size:.1f} KB")
    
    return str(zip_path)

def main():
    """メイン処理"""
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = 'temp'
    
    # 出力ディレクトリが存在しない場合は作成
    Path(output_dir).mkdir(exist_ok=True)
    
    # ZIPファイルを作成
    zip_path = create_extension_zip(output_dir)
    
    print("\nUsage:")
    print("  1. Upload this ZIP file to Chrome Web Store Developer Dashboard")
    print("  2. Or install locally by extracting and loading as unpacked extension")

if __name__ == "__main__":
    main()