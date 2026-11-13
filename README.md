# RPG Maker MV / MZ JSON 遊戲翻譯神器

專為 **RPG Maker MV** 與 **RPG Maker MZ** 打造的 JSON 文本安全抽取、翻譯與回填工具。

---

## 🌟 特色亮點

1. **視覺化 GUI 視窗介面**：提供簡潔直觀的桌面視窗，點擊即可選擇遊戲目錄、一鍵全自動翻譯。
2. **控制碼智慧保護**：RPG Maker 獨有的文字代碼（如 `\C[1]` 顏色、`\V[12]` 變數、`\N[1]` 角色名、`\I[45]` 圖標、`\.`、`\!` 停頓符號等），翻譯時會自動加上安全遮罩，防止被翻譯引擎竄改導致遊戲報錯崩潰。
3. **定向安全抽取**：
   - 僅抽取對話（401）、選項（102/402）、滾動文字（405）、角色名稱、道具與技能描述、系統訊息等。
   - **絕不更動** 圖片名稱（`characterName`）、音效名稱（`BGM/SE`）、註釋（108/408）、腳本指令（355）以及外掛標籤（`note`）。
4. **多種翻譯模式**：
   - **Google 翻譯（免費、免註冊、免 API Key）**：內建直接呼叫，開箱即用，推薦初次使用首選。
   - **Claude 頂級遊戲在地化**：支援 Anthropic Claude 3.7 Sonnet / 3.5 系列模型與自訂輸入，專門調校 RPG 冒險遊戲情境提示詞，保留生動語感與角色性格。
   - **其他相容 AI 模型**：支援相容 OpenAI 協定的 API（Gemini、ChatGPT、DeepSeek、Ollama 等，可自由輸入模型名稱）。
   - **字典匯出 / 匯入**：可將所有不重複文本匯出為標準 JSON 檔案，交由人工校對或丟給 ChatGPT/Claude 批次翻譯後一鍵套用。
5. **翻譯快取記憶**：相同的語句（如「はい」、「いいえ」）自動共用翻譯，大幅節省時間；即使翻譯途中中斷，下次也會自動續傳。
6. **一鍵安全備份與還原**：每次寫入前自動在遊戲目錄外建立時間戳記備份，隨時可一鍵無損還原。

---

## 📁 檔案結構說明

```text
rpg_maker_translator/
├── run_gui.bat            # Windows 一鍵啟動捷徑 (雙擊即可執行)
├── rpg_translator_gui.py  # 視覺化視窗主程式
├── rpg_translator_core.py # 核心抽取、遮蔽、快取與寫入引擎
├── rpg_translator_cli.py  # 命令列指令工具 (適合批次作業)
└── README.md              # 使用教學與說明文件
```

---

## 🚀 快速開始使用

### 步驟 1：啟動程式
在 Windows 上直接雙擊 **`run_gui.bat`** 即可開啟介面。
（或在終端機輸入：`python rpg_translator_gui.py`）

### 步驟 2：選擇遊戲的 `data` 資料夾
點擊「瀏覽選擇」，找到遊戲的資料夾：
- **RPG Maker MV**（已打包遊戲）：通常位於 `遊戲目錄/www/data/`
- **RPG Maker MZ** 或未打包 MV 專案：通常位於 `遊戲目錄/data/`
*小技巧：直接選取遊戲根目錄，程式也會自動替您辨識尋找內部的 `data` 資料夾！*

### 步驟 3：選擇翻譯方式
- **方式 A：一鍵全自動翻譯**
  1. 選擇來源語言（如 `ja` 日文）與目標語言（如 `zh-TW` 繁體中文）。
  2. 選擇「Google 翻譯（免費）」或填入您的「AI API Key」。
  3. 點擊 **「🚀 一鍵自動翻譯遊戲」**，系統將自動備份並開始逐句翻譯回填。
- **方式 B：匯出文本至 JSON (適合人工潤飾或使用 ChatGPT/Claude/DeepSeek)**
  1. 點擊 **「💾 匯出待翻譯文本 (JSON)」**，儲存為 `extracted.json`。
  2. 檔案格式如下：
     ```json
     [
       {
         "id": 1,
         "src": "旅人よ、よくぞ参られた。",
         "dst": ""
       }
     ]
     ```
  3. 在 `dst` 填入翻譯後的文字（可用文字編輯器、翻譯工具或丟給 AI 批次填寫）。
  4. 點擊 **「📥 匯入已翻譯文本 (JSON)」**，系統會自動備份並將翻譯套用回遊戲！

---

## 💻 命令列模式 (CLI)

如果您偏好使用指令或自動化批次處理：

```bash
# 查看幫助
python rpg_translator_cli.py --help

# 免費 Google 自動翻譯
python rpg_translator_cli.py --dir "C:\MyGame\www\data" --action translate --engine google --src ja --tgt zh-TW

# 匯出待翻譯文字
python rpg_translator_cli.py --dir "C:\MyGame\www\data" --action export --file my_texts.json

# 匯入翻譯結果
python rpg_translator_cli.py --dir "C:\MyGame\www\data" --action import --file my_texts.json

# 建立手動備份
python rpg_translator_cli.py --dir "C:\MyGame\www\data" --action backup
```

---

## 💡 RPG Maker 漢化重要避坑指南

1. **字型顯示為方塊（豆腐塊）或缺字**：
   - 部分日版遊戲有鎖定專用日文字型（如 MS Gothic 或內嵌日文字型）。
   - **解決方法**：開啟遊戲目錄下的 `fonts/gamefont.css`，將字型名稱替換為系統內建的微軟正黑體：
     ```css
     @font-face {
       font-family: GameFont;
       src: local("Microsoft JhengHei"), local("微軟正黑體");
     }
     ```
2. **文字溢出對話框**：
   - 中文文字寬度與日文不同，若發現對話框文字超出邊界，可以使用換行符號調整，或安裝 RPG Maker 常見的自動換行外掛（如 `YEP_MessageCore`）。
3. **還原遊戲**：
   - 每次翻譯或匯入時，系統皆會在遊戲外層建立 `data_backup_YYYYMMDD_HHMMSS` 資料夾。
   - 若遇到任何問題，點擊介面上的「🔄 還原備份」並選取該備份資料夾即可無損還原。
