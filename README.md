# Prasia-Discord-Bot
交叉王提醒，星座運勢，練成模擬，抽卡模擬，抽數字，塔羅牌占卜
# 🤖 波拉西亞戰記 公會專屬 Discord 助理 (Prasia Guild Bot)

這是一個專為 MMORPG《波拉西亞戰記》公會量身打造的 Discord 自動化與互動機器人。
為了解決公會管理繁瑣、遊戲資訊不對稱等問題，本專案結合了**非同步網頁爬蟲**、**本地端 SQLite 快取機制**，以及 **Discord UI 互動按鈕**，提供公會成員 0 延遲的流暢體驗。目前已透過 Docker 容器化部署於 NAS 伺服器，達成 24/7 高可用性運作。

## ✨ 核心亮點功能 (Features)

* **⚡ 超高速星座運勢 (SQLite 快取機制)**
  開發非同步爬蟲 (aiohttp + BeautifulSoup) 抓取每日運勢，並實作本地端 SQLite 快取邏輯。有效避免對外部網站的重複請求，並解決了繁體中文網頁常見的 Big5 / UTF-8 解碼衝突，將回應時間從 3 秒壓縮至 0.1 秒內。
* **🧠 100 題互動式心理測驗 (Discord Button UI)**
  捨棄傳統的文字輸入，實作 `discord.ui.View` 與動態按鈕 (Buttons)。系統會讀取本地的 `quiz.json` 題庫，並根據「當日日期」透過演算法每天自動輪替題目。測驗結果使用 `ephemeral=True` 屬性，實現如「悄悄話」般的絕佳隱私體驗。
* **🕒 時空縫隙首領排程自動推播**
  透過 `discord.ext.tasks` 建立背景常駐排程。系統會自動換算台北時區 (pytz)，於每日特定的首領重生前 10 分鐘，自動發送 Embed 訊息標記全體成員準備集結。
* **🎲 遊戲機率模擬器 (抽卡 / 鍊成)**
  內建機率演算法與 Discord Embed 視覺化排版，完美模擬遊戲內高風險的「糾結鍊成」與「最高 1000 抽」系統，並透過顏色分類稀有度，增加公會群組的互動樂趣。

## 🛠️ 技術棧 (Tech Stack)

* **程式語言：** Python 3.12
* **核心框架：** `discord.py`
* **資料處理與爬蟲：** `aiohttp`, `BeautifulSoup4`, `json`
* **資料庫：** SQLite3 (本地快取)
* **架構與部署：** Docker, Linux (Synology NAS), `python-dotenv` 環境變數分離

## 📂 專案結構 (Directory Structure)

```text
Prasia-Discord-Bot/
├── bot.py                # 機器人主程式邏輯
├── game_data.py          # 靜態遊戲資料與首領排程設定檔
├── quiz.json             # 100 題動態輪替心理測驗題庫
├── .env.example          # 環境變數範例檔 (機密脫敏)
├── requirements.txt      # Python 依賴套件清單
└── README.md             # 專案說明文件
<img width="594" height="429" alt="image" src="https://github.com/user-attachments/assets/780a9d11-7510-4381-8fc7-b42b8214d701" />
<img width="486" height="194" alt="image" src="https://github.com/user-attachments/assets/b8382dbd-0e69-4bb9-90ad-9167241ef28c" />
<img width="291" height="198" alt="image" src="https://github.com/user-attachments/assets/10dc5f56-eda1-4ebb-b5c4-820929c885c3" />
<img width="374" height="182" alt="image" src="https://github.com/user-attachments/assets/fab6487a-be2d-4891-af2e-a0b9b664be87" />


