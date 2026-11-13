# -*- coding: utf-8 -*-
"""
RPG Maker MV / MZ JSON 翻譯核心模組
支援遊戲對話、選單、資料庫文本的安全抽取、控制符保護、批次翻譯與回填。
"""

import os
import re
import json
import time
import shutil
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict, Tuple, Optional, Callable, Any

# ==========================================
# 控制碼保護器 (Control Code Masker)
# ==========================================
class ControlCodeMasker:
    """
    保護 RPG Maker 專用控制碼 (如 \\V[1], \\N[1], \\C[2], \\I[45], \\., \\!, \\> 等)
    在翻譯前轉換為臨時佔位符，翻譯完成後精確還原，避免遊戲崩潰或顯示異常。
    """
    PATTERN = re.compile(
        r'('
        r'\\[a-zA-Z]+\[[^\]\r\n]*\]|'  # 帶參數的指令：\C[1], \V[2], \FS[24]
        r'\\[.\$|!><^\\{}]|'           # 單符號指令：\., \|, \!, \>, \<, \^, \{, \}, \$, \\
        r'\\[a-zA-Z]+(?=[^a-zA-Z]|$)'  # 單字母指令：\G
        r')'
    )
    RESTORE_PATTERN = re.compile(r'___\s*TAG\s*_\s*(\d+)\s*___', re.IGNORECASE)

    @classmethod
    def mask(cls, text: str) -> Tuple[str, List[str]]:
        if not text:
            return text, []
        tags = []
        def repl(match):
            idx = len(tags)
            tags.append(match.group(0))
            return f'___TAG_{idx}___'
        masked_text = cls.PATTERN.sub(repl, text)
        return masked_text, tags

    @classmethod
    def unmask(cls, text: str, tags: List[str]) -> str:
        if not text or not tags:
            return text
        def repl(match):
            idx = int(match.group(1))
            if 0 <= idx < len(tags):
                return tags[idx]
            return match.group(0)
        return cls.RESTORE_PATTERN.sub(repl, text)


# ==========================================
# RPG Maker JSON 解析與抽取器
# ==========================================
class RPGDataExtractor:
    """
    針對 RPG Maker MV / MZ 的 data/*.json 進行定向安全抽取與回填。
    絕不破壞圖片檔名、音效檔名、腳本或外掛標籤 (note)。
    """

    @staticmethod
    def is_translatable(text: Any) -> bool:
        if not isinstance(text, str):
            return False
        text = text.strip()
        if not text:
            return False
        # 若只包含純數字、純符號或空行則不需翻譯
        if re.fullmatch(r'[\d\s\-_.,!?:;#*+~=@$%^&()\[\]{}|\\/<>]+', text):
            return False
        return True

    @classmethod
    def process_event_list(cls, event_list: List[Dict], callback: Callable[[str, str], str], is_apply: bool = False) -> List[Tuple[str, str]]:
        """
        處理事件指令清單 (Map events, CommonEvents, Troops)
        code 101: 顯示文字設定 (MZ parameters[4] 為發言者姓名)
        code 401: 顯示文字 (對話內文)
        code 102: 顯示選項 (parameters[0] 為選項字串陣列)
        code 402: 選項分歧 (parameters[1] 為選項字串，保持編輯器一致)
        code 405: 滾動文字
        code 320: 更改角色姓名
        code 324: 更改角色稱號
        code 325: 更改角色個人簡介
        """
        extracted = []
        if not isinstance(event_list, list):
            return extracted

        for i, cmd in enumerate(event_list):
            if not isinstance(cmd, dict):
                continue
            code = cmd.get('code')
            params = cmd.get('parameters', [])

            # 101: 顯示文字 (MZ 專用 speakerName: parameters[4])
            if code == 101 and len(params) >= 5 and isinstance(params[4], str) and params[4].strip():
                orig = params[4]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_101_speaker"
                    if is_apply:
                        params[4] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 401: 對話文字
            elif code == 401 and len(params) > 0 and isinstance(params[0], str):
                orig = params[0]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_401"
                    if is_apply:
                        params[0] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 102: 選項
            elif code == 102 and len(params) > 0 and isinstance(params[0], list):
                for ch_idx, choice in enumerate(params[0]):
                    if isinstance(choice, str) and cls.is_translatable(choice):
                        loc = f"cmd_{i}_code_102_opt_{ch_idx}"
                        if is_apply:
                            params[0][ch_idx] = callback(loc, choice)
                        else:
                            extracted.append((loc, choice))

            # 402: 選項分歧顯示 (When [Choice])
            elif code == 402 and len(params) > 1 and isinstance(params[1], str):
                orig = params[1]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_402"
                    if is_apply:
                        params[1] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 405: 滾動文字
            elif code == 405 and len(params) > 0 and isinstance(params[0], str):
                orig = params[0]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_405"
                    if is_apply:
                        params[0] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 320: 更改姓名
            elif code == 320 and len(params) > 1 and isinstance(params[1], str):
                orig = params[1]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_320_name"
                    if is_apply:
                        params[1] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 324: 更改稱號
            elif code == 324 and len(params) > 1 and isinstance(params[1], str):
                orig = params[1]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_324_nickname"
                    if is_apply:
                        params[1] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

            # 325: 更改簡介
            elif code == 325 and len(params) > 1 and isinstance(params[1], str):
                orig = params[1]
                if cls.is_translatable(orig):
                    loc = f"cmd_{i}_code_325_profile"
                    if is_apply:
                        params[1] = callback(loc, orig)
                    else:
                        extracted.append((loc, orig))

        return extracted

    @classmethod
    def process_file_data(cls, filename: str, data: Any, callback: Callable[[str, str], str], is_apply: bool = False) -> List[Tuple[str, str]]:
        """
        依檔名處理特定 RPG Maker JSON 資料結構。
        """
        extracted = []
        base_name = os.path.basename(filename)

        # 1. 地圖檔 (MapXXX.json)
        if re.match(r'^Map\d+\.json$', base_name, re.IGNORECASE):
            if isinstance(data, dict):
                # 地圖顯示名稱
                disp_name = data.get('displayName')
                if cls.is_translatable(disp_name):
                    loc = "displayName"
                    if is_apply:
                        data['displayName'] = callback(loc, disp_name)
                    else:
                        extracted.append((loc, disp_name))

                # 事件清單
                events = data.get('events', [])
                if isinstance(events, list):
                    for ev_idx, ev in enumerate(events):
                        if not isinstance(ev, dict):
                            continue
                        pages = ev.get('pages', [])
                        if isinstance(pages, list):
                            for p_idx, page in enumerate(pages):
                                if not isinstance(page, dict):
                                    continue
                                ev_list = page.get('list', [])
                                res = cls.process_event_list(ev_list, callback, is_apply)
                                if not is_apply:
                                    for loc, txt in res:
                                        extracted.append((f"events[{ev_idx}].pages[{p_idx}].{loc}", txt))

        # 2. 公共事件 (CommonEvents.json)
        elif base_name.lower() == 'commonevents.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    ev_list = item.get('list', [])
                    res = cls.process_event_list(ev_list, callback, is_apply)
                    if not is_apply:
                        for loc, txt in res:
                            extracted.append((f"[{idx}].{loc}", txt))

        # 3. 戰鬥部隊 (Troops.json)
        elif base_name.lower() == 'troops.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    pages = item.get('pages', [])
                    if isinstance(pages, list):
                        for p_idx, page in enumerate(pages):
                            if not isinstance(page, dict):
                                continue
                            ev_list = page.get('list', [])
                            res = cls.process_event_list(ev_list, callback, is_apply)
                            if not is_apply:
                                for loc, txt in res:
                                    extracted.append((f"[{idx}].pages[{p_idx}].{loc}", txt))

        # 4. 地圖列表資訊 (MapInfos.json)
        elif base_name.lower() == 'mapinfos.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    name = item.get('name')
                    if cls.is_translatable(name):
                        loc = f"[{idx}].name"
                        if is_apply:
                            item['name'] = callback(loc, name)
                        else:
                            extracted.append((loc, name))

        # 5. 角色 (Actors.json)
        elif base_name.lower() == 'actors.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    for field in ['name', 'nickname', 'profile']:
                        val = item.get(field)
                        if cls.is_translatable(val):
                            loc = f"[{idx}].{field}"
                            if is_apply:
                                item[field] = callback(loc, val)
                            else:
                                extracted.append((loc, val))

        # 6. 職業 (Classes.json)
        elif base_name.lower() == 'classes.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    name = item.get('name')
                    if cls.is_translatable(name):
                        loc = f"[{idx}].name"
                        if is_apply:
                            item['name'] = callback(loc, name)
                        else:
                            extracted.append((loc, name))

        # 7. 技能與道具、武器、防具
        elif base_name.lower() in ['skills.json', 'items.json', 'weapons.json', 'armors.json']:
            fields = ['name', 'description']
            if base_name.lower() == 'skills.json':
                fields.extend(['message1', 'message2'])
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    for field in fields:
                        val = item.get(field)
                        if cls.is_translatable(val):
                            loc = f"[{idx}].{field}"
                            if is_apply:
                                item[field] = callback(loc, val)
                            else:
                                extracted.append((loc, val))

        # 8. 敵人 (Enemies.json)
        elif base_name.lower() == 'enemies.json':
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    val = item.get('name')
                    if cls.is_translatable(val):
                        loc = f"[{idx}].name"
                        if is_apply:
                            item['name'] = callback(loc, val)
                        else:
                            extracted.append((loc, val))

        # 9. 狀態 (States.json)
        elif base_name.lower() == 'states.json':
            fields = ['name', 'message1', 'message2', 'message3', 'message4']
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        continue
                    for field in fields:
                        val = item.get(field)
                        if cls.is_translatable(val):
                            loc = f"[{idx}].{field}"
                            if is_apply:
                                item[field] = callback(loc, val)
                            else:
                                extracted.append((loc, val))

        # 10. 系統設定 (System.json)
        elif base_name.lower() == 'system.json':
            if isinstance(data, dict):
                # 遊戲標題與貨幣單位
                for field in ['gameTitle', 'currencyUnit']:
                    val = data.get(field)
                    if cls.is_translatable(val):
                        loc = field
                        if is_apply:
                            data[field] = callback(loc, val)
                        else:
                            extracted.append((loc, val))

                # 類型名單 (armorTypes, elements, equipTypes, skillTypes, weaponTypes)
                for type_field in ['armorTypes', 'elements', 'equipTypes', 'skillTypes', 'weaponTypes']:
                    arr = data.get(type_field)
                    if isinstance(arr, list):
                        for idx, val in enumerate(arr):
                            if cls.is_translatable(val):
                                loc = f"{type_field}[{idx}]"
                                if is_apply:
                                    arr[idx] = callback(loc, val)
                                else:
                                    extracted.append((loc, val))

                # 常用術語 (terms)
                terms = data.get('terms', {})
                if isinstance(terms, dict):
                    for sub in ['basic', 'commands', 'params']:
                        arr = terms.get(sub)
                        if isinstance(arr, list):
                            for idx, val in enumerate(arr):
                                if cls.is_translatable(val):
                                    loc = f"terms.{sub}[{idx}]"
                                    if is_apply:
                                        arr[idx] = callback(loc, val)
                                    else:
                                        extracted.append((loc, val))
                    # 提示訊息
                    msgs = terms.get('messages', {})
                    if isinstance(msgs, dict):
                        for k, val in msgs.items():
                            if cls.is_translatable(val):
                                loc = f"terms.messages.{k}"
                                if is_apply:
                                    msgs[k] = callback(loc, val)
                                else:
                                    extracted.append((loc, val))

        return extracted


# ==========================================
# 翻譯引擎 (Google Translate, OpenAI/LLM, Cache)
# ==========================================
class TranslationEngine:
    """
    提供自動翻譯、批次翻譯與快取管理。
    """
    def __init__(self, cache_file: str = "translation_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[str, str] = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"快取存檔失敗: {e}")

    def translate_google(self, text: str, src: str = 'ja', tgt: str = 'zh-TW') -> str:
        """
        使用免費 Google 翻譯端點 (無需 API Key)
        """
        if not text.strip():
            return text

        # 控制碼遮蔽
        masked_text, tags = ControlCodeMasker.mask(text)

        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx',
            'sl': src,
            'tl': tgt,
            'dt': 't',
            'q': masked_text
        }
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            full_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    translated = ''.join([item[0] for item in data[0] if item and item[0]])
                    # 還原控制碼
                    restored = ControlCodeMasker.unmask(translated, tags)
                    return restored
            except Exception as e:
                time.sleep(1 + attempt * 2)
                if attempt == 2:
                    raise e
        return text

    def translate_claude(self, text: str, api_key: str, base_url: str = "https://api.anthropic.com/v1", model: str = "claude-3-7-sonnet-20250219", src: str = "日文", tgt: str = "繁體中文") -> str:
        """
        使用 Anthropic Claude 進行高水準 RPG 遊戲文本在地化翻譯
        """
        if not text.strip():
            return text

        masked_text, tags = ControlCodeMasker.mask(text)

        endpoint = base_url.rstrip('/') + '/messages'
        payload = {
            "model": model,
            "max_tokens": 1024,
            "system": f"你是一位頂尖的 RPG Maker 遊戲在地化專家。請將輸入的遊戲文本翻譯成{tgt}（來源語言：{src}）。\n規則：\n1. 絕對保留所有類似 ___TAG_0___ 的標籤與格式控制碼原樣不變，不可增刪或移動空格。\n2. 翻譯語氣自然流暢、符合遊戲角色風格與對話情境。\n3. 直接輸出翻譯後的文本，絕對不要輸出任何多餘的解釋、說明、問候、標點引號或前綴後綴。",
            "messages": [
                {"role": "user", "content": masked_text}
            ]
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            }
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    translated = ""
                    for c in res_data.get('content', []):
                        if c.get('type') == 'text':
                            translated += c.get('text', '')
                    translated = translated.strip()
                    # 去除多餘首尾包裹引號
                    if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith('「') and translated.endswith('」') and not text.startswith('「')):
                        translated = translated[1:-1]
                    restored = ControlCodeMasker.unmask(translated, tags)
                    return restored
            except Exception as e:
                time.sleep(1 + attempt * 2)
                if attempt == 2:
                    raise e
        return text

    def translate_openai(self, text: str, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini", src: str = "日文", tgt: str = "繁體中文") -> str:
        """
        使用 OpenAI 相容格式的 LLM 進行翻譯 (支援 ChatGPT, Claude, Gemini, DeepSeek, Ollama 等)
        """
        if not text.strip():
            return text

        masked_text, tags = ControlCodeMasker.mask(text)

        endpoint = base_url.rstrip('/') + '/chat/completions'
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": f"你是一位專業的 RPG Maker 遊戲在地化翻譯家。請將輸入的文本從{src}翻譯成{tgt}。請保留所有類似 ___TAG_0___ 的標籤原樣不變，保持語氣流暢自然，切勿添加多餘說明或引號。"
                },
                {"role": "user", "content": masked_text}
            ],
            "temperature": 0.3
        }

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        elif 'localhost' in endpoint or '127.0.0.1' in endpoint:
            headers['Authorization'] = 'Bearer ollama'

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )

        for attempt in range(3):
            try:
                # 延長 timeout 至 60 秒以適應本地模型生成速度
                with urllib.request.urlopen(req, timeout=60) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    translated = res_data['choices'][0]['message']['content'].strip()
                    # 去除多餘首尾包裹引號
                    if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith('「') and translated.endswith('」') and not text.startswith('「')):
                        translated = translated[1:-1]
                    restored = ControlCodeMasker.unmask(translated, tags)
                    return restored
            except Exception as e:
                time.sleep(1 + attempt * 2)
                if attempt == 2:
                    raise e
        return text

    def translate_gemini(self, text: str, api_key: str, model: str = "gemini-2.5-flash", src: str = "日文", tgt: str = "繁體中文") -> str:
        """
        使用 Google 官方 Gemini REST API 進行快速高品質遊戲文本翻譯 (支援免費 API Key)
        """
        if not text.strip():
            return text

        masked_text, tags = ControlCodeMasker.mask(text)
        target_model = model if model else "gemini-2.5-flash"
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key.strip()}"

        prompt = (
            f"你是一位頂尖的 RPG Maker 遊戲在地化專家。請將以下文本從{src}翻譯成{tgt}。\n"
            f"規則：\n"
            f"1. 絕對保留所有類似 ___TAG_0___ 的格式標籤原樣不變，不得更動或刪減空格。\n"
            f"2. 翻譯語氣自然流暢、符合遊戲角色性格與冒險世界觀。\n"
            f"3. 直接輸出翻譯後的文本，絕對不要輸出任何多餘的解釋、說明、問候、引號或前綴後綴。\n\n"
            f"待翻譯文本：\n{masked_text}"
        )

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.3
            }
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_data = json.loads(resp.read().decode('utf-8'))
                    candidates = res_data.get('candidates', [])
                    if not candidates:
                        raise ValueError("Gemini 未回傳有效內容")
                    parts = candidates[0].get('content', {}).get('parts', [])
                    translated = "".join(p.get('text', '') for p in parts).strip()
                    if (translated.startswith('"') and translated.endswith('"')) or (translated.startswith('「') and translated.endswith('」') and not text.startswith('「')):
                        translated = translated[1:-1]
                    restored = ControlCodeMasker.unmask(translated, tags)
                    return restored
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8', errors='ignore')
                if e.code == 429:
                    time.sleep(3 + attempt * 3)
                elif e.code in [400, 403]:
                    raise Exception(f"Gemini API Key 無效或權限不足 (HTTP {e.code}): {err_body}")
                else:
                    time.sleep(1 + attempt * 2)
                if attempt == 2:
                    raise Exception(f"Gemini API 請求失敗 ({e.code}): {err_body}")
            except Exception as e:
                time.sleep(1 + attempt * 2)
                if attempt == 2:
                    raise e
        return text


# ==========================================
# 專案管理器 (備份、翻譯批次、匯出/匯入)
# ==========================================
class RPGProjectManager:
    def __init__(self, data_dir: str):
        self.data_dir = os.path.abspath(data_dir)
        self.engine = TranslationEngine(os.path.join(self.data_dir, "translation_cache.json"))

    def create_backup(self) -> str:
        """建立 data/ 的時間戳記備份"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        parent = os.path.dirname(self.data_dir)
        backup_name = f"data_backup_{timestamp}"
        backup_path = os.path.join(parent, backup_name)
        shutil.copytree(self.data_dir, backup_path, ignore=shutil.ignore_patterns('*.json.bak', 'data_backup*'))
        return backup_path

    def restore_backup(self, backup_path: str):
        """從指定備份目錄還原"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"找不到備份目錄: {backup_path}")
        # 清除現有 json
        for fname in os.listdir(self.data_dir):
            if fname.lower().endswith('.json') and fname != "translation_cache.json":
                os.remove(os.path.join(self.data_dir, fname))
        # 複製還原
        for item in os.listdir(backup_path):
            s = os.path.join(backup_path, item)
            d = os.path.join(self.data_dir, item)
            if os.path.isfile(s) and item.lower().endswith('.json'):
                shutil.copy2(s, d)

    def clear_cache(self):
        """清除快取資料"""
        cache_path = os.path.join(self.data_dir, "translation_cache.json")
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except Exception:
                pass
        self.engine.cache = {}

    def get_json_files(self) -> List[str]:
        """取得 data 目錄下所有 RPG Maker 支援的 json 檔案"""
        target_files = []
        if not os.path.exists(self.data_dir):
            return target_files

        for f in os.listdir(self.data_dir):
            if not f.lower().endswith('.json'):
                continue
            if f.lower() in [
                'actors.json', 'classes.json', 'skills.json', 'items.json',
                'weapons.json', 'armors.json', 'enemies.json', 'states.json',
                'system.json', 'commonevents.json', 'troops.json', 'mapinfos.json'
            ] or re.match(r'^Map\d+\.json$', f, re.IGNORECASE):
                target_files.append(os.path.join(self.data_dir, f))
        return sorted(target_files)

    def extract_all_texts(self) -> Dict[str, List[Tuple[str, str]]]:
        """抽取所有檔案的待翻譯文本，回傳 { 檔案名: [(locator, text), ...] }"""
        all_texts = {}
        for fpath in self.get_json_files():
            fname = os.path.basename(fpath)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                extracted = RPGDataExtractor.process_file_data(fname, data, lambda loc, txt: txt, is_apply=False)
                if extracted:
                    all_texts[fname] = extracted
            except Exception as e:
                print(f"讀取 {fname} 失敗: {e}")
        return all_texts

    def export_to_json(self, output_path: str):
        """匯出待翻譯文本為 JSON 字典檔案"""
        extracted = self.extract_all_texts()
        # 收集所有不重複字串
        unique_texts = {}
        for fname, items in extracted.items():
            for loc, text in items:
                if text not in unique_texts:
                    cached_trans = self.engine.cache.get(text, "")
                    unique_texts[text] = cached_trans

        export_data = [
            {"id": i + 1, "src": src, "dst": dst}
            for i, (src, dst) in enumerate(unique_texts.items())
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def import_from_json(self, input_path: str, progress_cb: Optional[Callable[[int, int, str], None]] = None):
        """從已翻譯的 JSON 檔案匯入並寫回 RPG Maker 遊戲檔案"""
        with open(input_path, 'r', encoding='utf-8') as f:
            trans_list = json.load(f)

        mapping = {}
        for item in trans_list:
            src = item.get('src')
            dst = item.get('dst')
            if src and dst and dst.strip():
                mapping[src] = dst
                self.engine.cache[src] = dst

        self.engine.save_cache()
        self.apply_translations(mapping, progress_cb)

    def apply_translations(self, translation_map: Dict[str, str], progress_cb: Optional[Callable[[int, int, str], None]] = None):
        """將字典替換回遊戲檔案"""
        json_files = self.get_json_files()
        total = len(json_files)

        for idx, fpath in enumerate(json_files):
            fname = os.path.basename(fpath)
            if progress_cb:
                progress_cb(idx + 1, total, f"正在寫入: {fname}")

            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                def replace_func(loc, orig_text):
                    return translation_map.get(orig_text, orig_text)

                RPGDataExtractor.process_file_data(fname, data, replace_func, is_apply=True)

                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"寫入 {fname} 失敗: {e}")

    def auto_translate(
        self,
        engine_type: str = 'google',
        src_lang: str = 'ja',
        tgt_lang: str = 'zh-TW',
        api_key: str = '',
        base_url: str = 'https://api.openai.com/v1',
        model: str = '',
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        error_cb: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, int]:
        """
        全自動翻譯流程：抽取 -> 快取查找 -> 翻譯缺失項 -> 批次儲存快取 -> 寫回 JSON 遊戲檔案
        """
        # 1. 抽取所有文本
        if progress_cb:
            progress_cb(0, 100, "正在掃描抽取 RPG Maker 文本...")
        extracted = self.extract_all_texts()

        # 收集不重複且尚未在快取中的文字
        needed_trans = set()
        for fname, items in extracted.items():
            for loc, text in items:
                cached_val = self.engine.cache.get(text)
                # 若尚未在快取中，或快取值與原文完全相同（通常是先前發生 401 錯誤或中斷留下的殘留），重新加入待翻譯
                if not cached_val or cached_val == text:
                    needed_trans.add(text)

        total_needed = len(needed_trans)
        translated_count = 0
        success_count = 0
        failed_count = 0

        # 2. 進行翻譯
        if total_needed > 0:
            for text in needed_trans:
                if stop_check and stop_check():
                    if progress_cb:
                        progress_cb(translated_count, total_needed, "翻譯已手動停止")
                    break

                try:
                    # 智慧自動檢測：若 Key 以 AIzaSy 開頭，自動導向 Google Gemini
                    effective_engine = engine_type
                    if api_key and api_key.strip().startswith('AIzaSy'):
                        effective_engine = 'gemini'

                    if effective_engine == 'gemini':
                        res = self.engine.translate_gemini(
                            text, api_key=api_key,
                            model=model if model and "gemini" in model.lower() else "gemini-2.5-flash",
                            src="日文" if src_lang == 'ja' else src_lang,
                            tgt="繁體中文" if tgt_lang == 'zh-TW' else tgt_lang
                        )
                    elif effective_engine == 'claude':
                        res = self.engine.translate_claude(
                            text, api_key=api_key,
                            base_url=base_url if base_url else "https://api.anthropic.com/v1",
                            model=model if model else "claude-3-7-sonnet-20250219",
                            src="日文" if src_lang == 'ja' else src_lang,
                            tgt="繁體中文" if tgt_lang == 'zh-TW' else tgt_lang
                        )
                    elif effective_engine in ['openai', 'ollama']:
                        target_base_url = base_url if base_url else ("http://localhost:11434/v1" if effective_engine == 'ollama' else "https://api.openai.com/v1")
                        target_model = model if model else ("qwen2.5:7b" if effective_engine == 'ollama' else "gpt-4o-mini")
                        res = self.engine.translate_openai(
                            text, api_key=api_key,
                            base_url=target_base_url,
                            model=target_model,
                            src="日文" if src_lang == 'ja' else src_lang,
                            tgt="繁體中文" if tgt_lang == 'zh-TW' else tgt_lang
                        )
                    else:
                        res = self.engine.translate_google(text, src=src_lang, tgt=tgt_lang)

                    self.engine.cache[text] = res
                    success_count += 1
                    time.sleep(0.08)  # 防限速微小延遲
                    # 取得翻譯後的中文文本，去除換行
                    disp_text = res.replace('\n', ' ').strip()
                except Exception as e:
                    failed_count += 1
                    err_str = str(e)
                    if "10061" in err_str or "Connection refused" in err_str:
                        err_msg = "連線至本地 Ollama 失敗 (請確認已在 CMD 執行: ollama run qwen2.5:7b)"
                    else:
                        err_msg = f"翻譯失敗: {text[:20]}... 錯誤: {e}"
                    print(err_msg)
                    if error_cb:
                        error_cb(err_msg)
                    disp_text = f"[失敗: {text[:15]}...]"

                translated_count += 1
                if progress_cb:
                    if len(disp_text) > 35:
                        disp_text = disp_text[:35] + "..."
                    progress_cb(translated_count, total_needed, f"翻譯進度 ({translated_count}/{total_needed}) [成功:{success_count} 失敗:{failed_count}]: {disp_text}")

                # 每 30 句儲存一次快取
                if translated_count % 30 == 0:
                    self.engine.save_cache()

            self.engine.save_cache()

        # 3. 寫回所有遊戲檔案
        if progress_cb:
            progress_cb(total_needed, total_needed, "正在將翻譯結果安全寫回遊戲 JSON 檔案...")
        self.apply_translations(self.engine.cache, progress_cb=lambda cur, tot, msg: progress_cb(cur, tot, msg) if progress_cb else None)

        return {
            "total": total_needed,
            "success": success_count,
            "failed": failed_count
        }
