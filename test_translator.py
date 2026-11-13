# -*- coding: utf-8 -*-
import os
import json
import shutil
import unittest
from rpg_translator_core import ControlCodeMasker, RPGDataExtractor, RPGProjectManager

class TestRPGTranslator(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)

        # 模擬 Map001.json
        self.map_data = {
            "displayName": "始まりの町",
            "events": [
                None,
                {
                    "id": 1,
                    "name": "EV001",
                    "note": "<custom_plugin_tag: 123>",
                    "pages": [
                        {
                            "list": [
                                {"code": 101, "parameters": ["Actor1", 0, 0, 2, "村長"]},
                                {"code": 401, "parameters": ["\\C[1]旅人\\C[0]よ、よくぞ参られた。"]},
                                {"code": 401, "parameters": ["この町で\\V[10]ゴールド集めてきてくれ。"]},
                                {"code": 102, "parameters": [["引き受ける", "断る"], 0, 1, 2, 0]},
                                {"code": 402, "parameters": [0, "引き受ける"]},
                                {"code": 401, "parameters": ["恩に着るぞ！"]},
                                {"code": 108, "parameters": ["<plugin_comment: do_not_touch>"]},
                                {"code": 355, "parameters": ["$gameParty.gainGold(100);"]},
                                {"code": 0, "parameters": []}
                            ]
                        }
                    ]
                }
            ]
        }
        with open(os.path.join(self.test_dir, "Map001.json"), "w", encoding="utf-8") as f:
            json.dump(self.map_data, f, ensure_ascii=False)

        # 模擬 Actors.json
        self.actors_data = [
            None,
            {
                "id": 1,
                "name": "ハロルド",
                "nickname": "新米剣士",
                "profile": "伝説の勇者を目指す少年。",
                "characterName": "Actor1",
                "note": "<PluginTag: do_not_touch>"
            }
        ]
        with open(os.path.join(self.test_dir, "Actors.json"), "w", encoding="utf-8") as f:
            json.dump(self.actors_data, f, ensure_ascii=False)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_masking(self):
        text = r"\C[1]勇者\C[0]よ、\V[12]ゴールド！ \. \! \>即時\<"
        masked, tags = ControlCodeMasker.mask(text)
        restored = ControlCodeMasker.unmask(masked, tags)
        self.assertEqual(text, restored)

    def test_extraction(self):
        manager = RPGProjectManager(self.test_dir)
        all_texts = manager.extract_all_texts()
        
        self.assertIn("Map001.json", all_texts)
        self.assertIn("Actors.json", all_texts)

        # 檢查 Map001 抽取的文字
        map_texts = [txt for loc, txt in all_texts["Map001.json"]]
        self.assertIn("始まりの町", map_texts)
        self.assertIn("村長", map_texts)
        self.assertIn(r"\C[1]旅人\C[0]よ、よくぞ参られた。", map_texts)
        self.assertIn("引き受ける", map_texts)
        self.assertIn("断る", map_texts)

        # 確保外掛標籤、註釋、腳本沒有被抽取！
        self.assertNotIn("<custom_plugin_tag: 123>", map_texts)
        self.assertNotIn("<plugin_comment: do_not_touch>", map_texts)
        self.assertNotIn("$gameParty.gainGold(100);", map_texts)

        # 檢查 Actors 抽取的文字
        actor_texts = [txt for loc, txt in all_texts["Actors.json"]]
        self.assertIn("ハロルド", actor_texts)
        self.assertIn("新米剣士", actor_texts)
        self.assertNotIn("Actor1", actor_texts) # 圖片檔名不抽
        self.assertNotIn("<PluginTag: do_not_touch>", actor_texts) # note 不抽

    def test_export_and_import(self):
        manager = RPGProjectManager(self.test_dir)
        export_path = os.path.join(self.test_dir, "export.json")
        manager.export_to_json(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 模擬手動翻譯
        for item in data:
            if item["src"] == "始まりの町":
                item["dst"] = "起始之鎮"
            elif item["src"] == "村長":
                item["dst"] = "村長大人"
            elif item["src"] == "ハロルド":
                item["dst"] = "哈洛德"

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        # 匯入寫回
        manager.import_from_json(export_path)

        # 檢查 Map001.json
        with open(os.path.join(self.test_dir, "Map001.json"), "r", encoding="utf-8") as f:
            map_res = json.load(f)
        self.assertEqual(map_res["displayName"], "起始之鎮")
        self.assertEqual(map_res["events"][1]["pages"][0]["list"][0]["parameters"][4], "村長大人")
        # 確保外掛標籤依然完整
        self.assertEqual(map_res["events"][1]["note"], "<custom_plugin_tag: 123>")

        # 檢查 Actors.json
        with open(os.path.join(self.test_dir, "Actors.json"), "r", encoding="utf-8") as f:
            actor_res = json.load(f)
        self.assertEqual(actor_res[1]["name"], "哈洛德")
        self.assertEqual(actor_res[1]["characterName"], "Actor1")

    def test_backup_and_restore(self):
        manager = RPGProjectManager(self.test_dir)
        backup_dir = manager.create_backup()
        self.assertTrue(os.path.exists(backup_dir))

        # 修改原始檔案
        with open(os.path.join(self.test_dir, "Map001.json"), "w", encoding="utf-8") as f:
            json.dump({"broken": True}, f)

        # 還原
        manager.restore_backup(backup_dir)
        with open(os.path.join(self.test_dir, "Map001.json"), "r", encoding="utf-8") as f:
            restored_data = json.load(f)
        self.assertEqual(restored_data["displayName"], "始まりの町")

        # 清除備份目錄
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)

if __name__ == "__main__":
    unittest.main()
