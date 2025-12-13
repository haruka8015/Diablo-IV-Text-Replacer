#!/bin/bash

# manifest.jsonからバージョンを取得
VERSION=$(grep -o '"version": "[^"]*"' sources/manifest.json | cut -d'"' -f4)

if [ -z "$VERSION" ]; then
    echo "Error: バージョンをmanifest.jsonから取得できませんでした"
    exit 1
fi

echo "バージョン $VERSION のリリースzipを作成します..."

# tempディレクトリを作成（存在しない場合）
mkdir -p temp

# 一時的にDiablo_Translateディレクトリを作成してzipを生成
cd temp && \
mkdir -p Diablo_Translate && \
cp -r ../sources/* Diablo_Translate/ && \
zip -r "Diablo_Translate_${VERSION}.zip" Diablo_Translate && \
rm -rf Diablo_Translate

echo "完了: temp/Diablo_Translate_${VERSION}.zip"