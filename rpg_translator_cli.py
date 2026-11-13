# -*- coding: utf-8 -*-
"""
RPG Maker MV / MZ JSON 命令列翻譯工具 (CLI)
支援自動化腳本或伺服器批次作業。
"""

import os
import sys
import argparse
from rpg_translator_core import RPGProjectManager

def main():
    parser = argparse.ArgumentParser(description="RPG Maker MV / MZ JSON 命令列翻譯工具")
    parser.add_argument("--dir", required=True, help="RPG Maker 遊戲的 data 資料夾路徑")
    parser.add_argument("--action", choices=["translate", "export", "import", "backup", "restore"], default="translate", help="執行的操作")
    parser.add_argument("--engine", choices=["claude", "google", "openai"], default="claude", help="翻譯引擎 (claude, google 或 openai)")
    parser.add_argument("--src", default="ja", help="來源語言 (預設: ja)")
    parser.add_argument("--tgt", default="zh-TW", help="目標語言 (預設: zh-TW)")
    parser.add_argument("--file", help="匯出或匯入時的 JSON 檔案路徑")
    parser.add_argument("--backup-dir", help="還原時指定的備份目錄")
    parser.add_argument("--api-key", default="", help="Claude / LLM API Key (亦可讀取環境變數 ANTHROPIC_API_KEY)")
    parser.add_argument("--base-url", default="", help="API Base URL (預設 Claude: https://api.anthropic.com/v1)")
    parser.add_argument("--model", default="", help="Model 名稱 (預設 Claude: claude-3-5-haiku-20241022)")

    args = parser.parse_args()

    data_dir = os.path.abspath(args.dir)
    if not os.path.isdir(data_dir):
        print(f"錯誤: 找不到目錄 {data_dir}")
        sys.exit(1)

    manager = RPGProjectManager(data_dir)

    if args.action == "backup":
        bk = manager.create_backup()
        print(f"備份建立完成: {bk}")

    elif args.action == "restore":
        if not args.backup_dir or not os.path.isdir(args.backup_dir):
            print("錯誤: 請使用 --backup-dir 指定備份目錄")
            sys.exit(1)
        manager.restore_backup(args.backup_dir)
        print(f"已從備份成功還原: {args.backup_dir}")

    elif args.action == "export":
        out_file = args.file or os.path.join(data_dir, "extracted_texts.json")
        print(f"正在抽取並匯出文本至 {out_file}...")
        manager.export_to_json(out_file)
        print(f"匯出完成: {out_file}")

    elif args.action == "import":
        if not args.file or not os.path.isfile(args.file):
            print("錯誤: 請使用 --file 指定要匯入的 JSON 檔案路徑")
            sys.exit(1)
        print("正在建立備份...")
        bk = manager.create_backup()
        print(f"備份已儲存: {bk}")
        print(f"正在匯入 {args.file} 並寫回遊戲...")
        def progress(c, t, msg):
            print(f"[{c}/{t}] {msg}")
        manager.import_from_json(args.file, progress_cb=progress)
        print("匯入完成！")

    elif args.action == "translate":
        print("步驟 1: 建立遊戲資料安全備份...")
        bk = manager.create_backup()
        print(f"備份完成: {bk}")

        api_key = args.api_key
        if not api_key:
            if args.engine == "claude":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            elif args.engine == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")

        base_url = args.base_url
        model = args.model
        if args.engine == "claude":
            if not base_url:
                base_url = "https://api.anthropic.com/v1"
            if not model:
                model = "claude-3-5-haiku-20241022"
        elif args.engine == "openai":
            if not base_url:
                base_url = "https://api.openai.com/v1"
            if not model:
                model = "gpt-4o-mini"

        print(f"步驟 2: 開始自動翻譯 (引擎: {args.engine}, 模型: {model or '預設'}, {args.src} -> {args.tgt})...")
        def progress(c, t, msg):
            pct = int((c / t) * 100) if t > 0 else 0
            print(f"\r[{pct}%] {msg}", end="", flush=True)

        manager.auto_translate(
            engine_type=args.engine,
            src_lang=args.src,
            tgt_lang=args.tgt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            progress_cb=progress
        )
        print("\n\n翻譯完成！遊戲 JSON 已更新。")

if __name__ == "__main__":
    main()
