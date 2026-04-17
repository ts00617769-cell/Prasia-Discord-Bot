import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import random
import datetime
import pytz
import json
import datetime
import google.generativeai as genai
import csv
import re
import json
import datetime
import sqlite3


# 💡 關鍵：從外部模組匯入我們分離出去的靜態資料
from game_data import GAP_BOSS_SCHEDULE, WEEKDAY_NAMES, item_names, item_rates, item_map

# 1. 加載環境變數
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ⚠️ 自動提醒頻道 ID
REMINDER_CHANNEL_ID = 1477964998818140326
# 🛡️ 請換成你們公會真正的「打寶區」頻道 ID 目前用測試頻道
LOOT_CHANNEL_ID = 1477966312411107493

# 2. 機器人初始化
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. 背景工作：10 分鐘前自動提醒 ---
@tasks.loop(minutes=1)
async def auto_boss_reminder():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(tz)
    ten_mins_later = now + datetime.timedelta(minutes=10)
    target_hour = ten_mins_later.hour
    target_minute = ten_mins_later.minute
    weekday = ten_mins_later.weekday()

    if target_minute == 0 and target_hour in GAP_BOSS_SCHEDULE.get(weekday, []):
        channel = bot.get_channel(REMINDER_CHANNEL_ID)
        if channel:
            time_str = "點、".join(map(str, GAP_BOSS_SCHEDULE[weekday])) + "點"
            embed = discord.Embed(
                title="🕒 時空縫隙首領召喚提醒",
                description=f"**10 分鐘後** 將開始召喚首領！\n\n今天召喚時段\n✅ **{time_str}**",
                color=discord.Color.red()
            )
            await channel.send(content="@everyone", embed=embed)

# --- 4. 事件監聽 ---
@bot.event
async def on_ready():
    print(f'{bot.user} 已成功登入 Discord！')
    if not auto_boss_reminder.is_running():
        auto_boss_reminder.start()

# --- 5. 指令：時空查詢 ---
@bot.command(name="時空", help="顯示今天的時空縫隙召喚時間表。")
async def gap_boss_info(ctx):
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(tz)
    today_index = now.weekday() 
    today_name = WEEKDAY_NAMES[today_index]
    times = GAP_BOSS_SCHEDULE.get(today_index, [])
    
    if not times:
        await ctx.send(f"📅 今天是 {today_name}，目前沒有設定召喚。")
        return

    time_str = "點、".join(map(str, times)) + "點"
    embed = discord.Embed(
        title=f"🕒 時空縫隙首領召喚時間表",
        description=f"今天是 **{today_name}**",
        color=discord.Color.purple()
    )
    embed.add_field(name="今天召喚時段", value=f"✅ **{time_str}**", inline=False)
    embed.set_footer(text=f"伺服器目前時間：{now.strftime('%H:%M')}")
    await ctx.send(embed=embed)

# --- 6. 指令：抽卡 ---
@bot.command(name='抽卡', help='結果透過私訊傳送，最高 1000 抽。')
async def gacha(ctx, num_pulls: int = 10):
    if not 0 < num_pulls <= 1000:
        await ctx.send(f"{ctx.author.mention} 抽卡次數須在 1-1000 之間！", delete_after=5)
        return

    rarity_colors = {
        "傳說": 0xa335ee, "英雄": 0xff0000, "稀有": 0x0070dd, "高級": 0x1eff00, "一般": 0x9d9d9d
    }

    results = [item_map[random.choices(item_names, weights=item_rates, k=1)[0]] for _ in range(num_pulls)]

    summary = {}
    for res in results:
        rarity = res["rarity"]
        if rarity not in summary: summary[rarity] = []
        summary[rarity].append(res["name"])

    response_lines = [f"**--- 您的 {num_pulls} 抽結果 ---**"]
    high_rarity_embeds = []

    for r in ["傳說", "英雄", "稀有", "高級", "一般"]:
        if r in summary:
            response_lines.append(f"**{r}** ({len(summary[r])} 張):")
            if r in ["傳說", "英雄"]:
                for item_name in summary[r]:
                    response_lines.append(f"- {item_name}")
                    e = discord.Embed(
                        title="✨ 恭喜抽到頂級物品！",
                        description=f"**{item_name}** ({r})",
                        color=rarity_colors.get(r, 0xffffff)
                    )
                    high_rarity_embeds.append(e)
            else:
                for item_name in summary[r]:
                    response_lines.append(f"- {item_name}")

    full_response = "\n".join(response_lines)

    try:
        if len(full_response) > 2000:
            chunks = [full_response[i:i+1900] for i in range(0, len(full_response), 1900)]
            for chunk in chunks: await ctx.author.send(chunk)
        else:
            await ctx.author.send(full_response)

        for embed in high_rarity_embeds: await ctx.author.send(embed=embed)
        await ctx.send(f"✅ {ctx.author.mention} {num_pulls} 抽結果已送達私訊！", delete_after=5)
    except discord.Forbidden:
        await ctx.send(f"❌ {ctx.author.mention} 我無法傳私訊給你，請開啟隱私設定。")

# --- 7. 指令：純數字抽獎 ---
@bot.command(name="抽", help="隨機抽取一個數字。用法：!抽 100 (代表抽 1~100)")
async def draw_number(ctx, max_val: int = 100):
    if max_val <= 1:
        await ctx.send(f"{ctx.author.mention} 抽獎範圍至少要大於 1 喔！")
        return
    
    lucky_number = random.randint(1, max_val)
    
    embed = discord.Embed(
        title="🎲 隨機抽號碼",
        description=f"從 **1 ~ {max_val}** 之中...",
        color=discord.Color.blue()
    )
    embed.add_field(name="抽出的幸運號碼是：", value=f"✨ **{lucky_number}**", inline=False)
    embed.set_footer(text=f"由 {ctx.author.display_name} 啟動抽獎")
    await ctx.send(embed=embed)

# --- 8. 指令：功能介紹 ---
@bot.command(name="指令", help="顯示所有可用的機器人指令。")
async def help_menu(ctx):
    embed = discord.Embed(
        title="🤖 波拉西亞助手 - 指令操作手冊",
        description="歡迎使用公會專用機器人，以下是目前可用的指令：",
        color=discord.Color.blue()
    )
    embed.add_field(name="🕒 !時空", value="顯示今天的「時空縫隙首領」召喚時間表。", inline=False)
    embed.add_field(name="💎 !抽卡 [次數]", value="模擬抽卡（最高 1000 抽），僅 **傳說/英雄** 會顯示彩色框框。", inline=False)
    embed.add_field(name="🎲 !抽 [數字]", value="隨機抽取一個數字（預設 1~100），適合分配王團獎勵。", inline=False)
    embed.add_field(name="🧪 !鍊成 [階級]", value="模擬四合一鍊成（每柱 60% 過，連過四柱成功）。", inline=False)
    embed.add_field(name="🔮 !塔羅", value="抽取今日專屬的塔羅牌，預測遊戲運勢（每日重置）。", inline=False)
    embed.add_field(name="🧠 !測驗", value="每日輪替的公會專屬心理測驗！看看你的真實性格。", inline=False)
    
    # 👇 新增的星座指令說明 👇
    embed.add_field(name="🌌 !星座 [星座名稱]", value="查詢今日真實的星座運勢（例如：!星座 天蠍座，超高速快取版）。", inline=False)
    
    embed.set_footer(text=f"由 {ctx.author.display_name} 請求查詢")
    await ctx.send(embed=embed)

# --- 9. 指令：鍊成系統 ---
@bot.command(name="鍊成", help="模擬四合一鍊成。用法：!鍊成 英雄")
async def alchemy(ctx, rarity: str):
    tiers = {"一般": "高級", "高級": "稀有", "稀有": "英雄", "英雄": "傳說", "傳說": "神話"}
    if rarity not in tiers:
        await ctx.send(f"❌ {ctx.author.mention} 請輸入正確的階級：一般、高級、稀有、英雄、傳說")
        return

    target_rarity = tiers[rarity]
    success_rate = 0.6
    results = []
    total_success = True

    for i in range(1, 5):
        if random.random() < success_rate:
            results.append(f"第 {i} 柱：✅ 成功")
        else:
            results.append(f"第 {i} 柱：❌ 失敗")
            total_success = False
            break

    if total_success:
        rarity_colors = {"神話": 0xffd700, "傳說": 0xa335ee, "英雄": 0xff0000, "稀有": 0x0070dd, "高級": 0x1eff00}
        description = "\n".join(results) + f"\n\n🎊 **恭喜！鍊成成功！**\n獲得：**{target_rarity}** 品質"
        
        if target_rarity in ["英雄", "傳說", "神話"]:
            embed = discord.Embed(title="✨ 鍊成進階成功！", description=description, color=rarity_colors.get(target_rarity, 0xffffff))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"✅ {ctx.author.mention} 鍊成成功！獲得：**{target_rarity}**")
    else:
        fail_msg = "\n".join(results) + f"\n\n崩了... 鍊成失敗，素材已消失。"
        await ctx.send(f"💀 {ctx.author.mention} {fail_msg}")

# --- 10. 指令：今日塔羅運勢 ---
@bot.command(name="塔羅", help="抽取今日專屬的大阿爾克那塔羅牌。")
async def daily_tarot(ctx):
    today_str = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y%m%d')
    seed = f"tarot_{ctx.author.id}_{today_str}"
    random.seed(seed)
    
    tarot_cards = {
        "🃏 0. 愚者 (The Fool)": "正位：放下得失心，適合隨手單抽，常有意外驚喜。\n逆位：切忌上頭！絕對不要把留著保底的鑽石拿去亂抽。",
        "✨ 1. 魔術師 (The Magician)": "正位：創造力爆發！鍊成系統成功率體感大增，四柱連過不是夢。\n逆位：素材準備不足，建議先囤貨，不要輕易點鍊成。",
        "📜 2. 女祭司 (The High Priestess)": "正位：直覺敏銳，適合冷靜分析王團掉落機率，精準出手。\n逆位：判斷失誤機率高，分配戰利品或抽卡建議聽從盟友建議，別盲衝。",
        "👑 3. 皇后 (The Empress)": "正位：豐收之日！打怪掉寶率體感上升，適合長時間掛機農資源。\n逆位：資源消耗過快，點裝備或鍊成容易傾家蕩產，請守住錢包。",
        "🛡️ 4. 皇帝 (The Emperor)": "正位：掌控全局！今晚首領戰你將是 MVP，指揮若定，戰利品滿滿。\n逆位：過度固執會吃虧，如果鍊成連爆兩柱就該收手，別硬剛機率。",
        "🗝️ 5. 教皇 (The Hierophant)": "正位：貴人相助，非常適合找公會裡的「歐洲人」幫你代抽。\n逆位：不宜盲從玄學，什麼綠色乖乖今天可能都無效，回歸基本面吧。",
        "💞 6. 戀人 (The Lovers)": "正位：完美契合！跟固定團友組隊打寶會有意想不到的好運。\n逆位：組隊溝通易有摩擦，或是裝備分配可能出現分歧，請保持和氣。",
        "⚔️ 7. 戰車 (The Chariot)": "正位：勇往直前！據點戰大殺四方，氣勢如虹，抽卡也適合大保底硬抽。\n逆位：衝動是魔鬼，方向錯誤的堅持只會讓素材全部化為烏有。",
        "🦁 8. 力量 (Strength)": "正位：以柔克剛，面對 12.96% 的鍊成機率也能穩住心態，最終迎來金光。\n逆位：耐心見底，容易因為連續出綠光而崩潰，建議遠離抽卡介面。",
        "🏮 9. 隱者 (The Hermit)": "正位：低調發大財，深夜獨自一人在冷門頻道單抽，出紫機率高。\n逆位：太過孤立無援，有問題多在頻道問問大家，別自己瞎摸索。",
        "🎡 10. 命運之輪 (Wheel of Fortune)": "正位：迎來轉機！適合直接挑戰 !抽卡 1000，紫光與金光即將降臨。\n逆位：運勢陷入泥沼，今天非酋體質發揮到極致，請安分守己。",
        "⚖️ 11. 正義 (Justice)": "正位：一分耕耘一分收穫，適合去解每日任務，抽卡機率完全照官方走。\n逆位：覺得系統特別坑？沒錯，今天不適合跟機率拼搏。",
        "⏳ 12. 倒吊人 (The Hanged Man)": "正位：以退為進，現在不是抽卡的好時機，把資源留給下一個卡池。\n逆位：無謂的犧牲，為了衝戰力硬點裝備只會換來一場空。",
        "💀 13. 死神 (Death)": "正位：置之死地而後生！雖然可能先爆幾件裝備，但隨後必迎來大突破。\n逆位：泥足深陷，拒絕接受失敗只會越賠越多，該停損了。",
        "🌊 14. 節制 (Temperance)": "正位：資源管理大師！見好就收，只要抽到一張英雄就馬上停手。\n逆位：慾望失控，容易把辛苦農來的鑽石在五分鐘內花光。",
        "😈 15. 惡魔 (The Devil)": "正位：受到致命誘惑！雖然風險極高，但如果敢賭一把大的，或許有奇效。\n逆位：被貪念反噬，小心因為貪圖一時戰力提升而賠上全部素材。",
        "⚡ 16. 高塔 (The Tower)": "正位：大凶！絕對不要點鍊成，點下去四柱必崩，傾家蕩產。\n逆位：雖然會經歷小失敗（例如單抽全綠），但能避開大災難。",
        "🌟 17. 星星 (The Star)": "正位：大吉！希望之光照耀，傳說與英雄機率大幅提升，請直接開抽。\n逆位：好運稍微延遲，建議晚上首領戰打完之後再來抽卡。",
        "🌙 18. 月亮 (The Moon)": "正位：充滿未知與不安，官方機率今天似乎特別詭異，建議觀望。\n逆位：迷霧散去，終於看清官方的套路，今天是當免費仔的好日子。",
        "☀️ 19. 太陽 (The Sun)": "正位：極吉！陽光普照，全身上下充滿歐洲人的氣息，想抽什麼就抽什麼！\n逆位：雖然熱情減退，現在依然有小收穫，適合抽個 10 抽試試手氣。",
        "🎺 20. 審判 (Judgement)": "正位：過去的累積迎來回報，之前的非氣將一次洗刷，準備迎接紫光。\n逆位：還債時刻，之前太歐的話，今天可能會遇到連續保底的懲罰。",
        "🌍 21. 世界 (The World)": "正位：完美圓滿！心想事成，缺什麼裝備今天就能打到或抽到，大圓滿！\n逆位：距離目標只差最後一哩路，可能鍊成卡在最後一柱，請保持平常心。"
    }
    
    drawn_card = random.choice(list(tarot_cards.keys()))
    interpretation_full = tarot_cards[drawn_card]
    
    parts = interpretation_full.split("\n逆位：")
    upright_text = parts[0].replace("正位：", "").strip()
    reversed_text = parts[1].strip() if len(parts) > 1 else "無逆位解釋"

    is_upright = random.choice([True, False])
    
    if is_upright:
        final_title = f"**{drawn_card} (正位)**"
        final_desc = upright_text
    else:
        final_title = f"**{drawn_card} (逆位) 🙃**"
        final_desc = reversed_text

    random.seed()
    
    embed = discord.Embed(
        title="🔮 塔羅神諭 - 今日遊戲運勢",
        description=f"{ctx.author.mention} 抽出的命運之牌是：",
        color=discord.Color.dark_purple()
    )
    embed.add_field(name=final_title, value=final_desc, inline=False)
    embed.set_footer(text="※ 命運掌握在自己手中，塔羅僅指引方向。")
    
    await ctx.send(embed=embed)
# --- 11. 指令：真實星座運勢 (SQLite 快取版 + Big5 強制破譯) ---
@bot.command(name="星座", help="查詢今日真實的星座運勢 (結合本地端快取機制)。")
async def real_horoscope_cached(ctx, sign: str = None):
    import sqlite3
    import datetime
    import pytz
    import aiohttp
    from bs4 import BeautifulSoup

    zodiac_map = {
        "牡羊座": 0, "金牛座": 1, "雙子座": 2, "巨蟹座": 3,
        "獅子座": 4, "處女座": 5, "天秤座": 6, "天蠍座": 7,
        "射手座": 8, "摩羯座": 9, "水瓶座": 10, "雙魚座": 11
    }

    if sign not in zodiac_map:
        await ctx.send(f"❌ {ctx.author.mention} 請輸入正確的星座！\n👉 可用星座：{', '.join(zodiac_map.keys())}")
        return

    # 取得台北時間的今天日期
    today_str = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d')

    # --- 步驟 1：連接資料庫，檢查是否有快取 ---
    conn = sqlite3.connect('guild_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS horoscope_cache
                 (date TEXT, sign TEXT, content TEXT, 
                  UNIQUE(date, sign))''')
    
    c.execute("SELECT content FROM horoscope_cache WHERE date=? AND sign=?", (today_str, sign))
    cached_result = c.fetchone()

    if cached_result:
        fortune_text = cached_result[0]
        footer_text = "※ 資料來源：本地資料庫快取 (超高速響應 ⚡)"
        conn.close()
    else:
        loading_msg = await ctx.send(f"🛰️ 本地無快取，正在向星象局請求 **{sign}** 今日最新運勢...")
        
        url = f"https://astro.click108.com.tw/daily_0.php?iAstro={zodiac_map[sign]}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    response.raise_for_status() 
                    # 💡 終極正解：用 utf-8 解碼，並「強制忽略」網頁裡寫壞的字元！
                    html_bytes = await response.read()
                    html = html_bytes.decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')
            today_content = soup.find('div', class_='TODAY_CONTENT')
            
            if today_content:
                raw_text = today_content.text.strip()
                fortune_text = raw_text.replace("整體運勢", "**整體運勢**").replace("愛情運勢", "\n\n**愛情運勢**").replace("事業運勢", "\n\n**事業運勢**").replace("財運運勢", "\n\n**財運運勢**")
                
                c.execute("INSERT INTO horoscope_cache (date, sign, content) VALUES (?, ?, ?)", 
                          (today_str, sign, fortune_text))
                conn.commit()
                footer_text = "※ 資料來源：科技紫微網即時連線 (並已存入本地快取 💾)"
            else:
                fortune_text = "⚠️ 星象儀受干擾，無法解析今日運勢。"
                footer_text = "※ 抓取失敗，請稍後重試。"

            conn.close()
            await loading_msg.delete()

        except Exception as e:
            print(f"爬蟲報錯: {e}")
            await loading_msg.edit(content=f"❌ 連線外部星象資料庫失敗，請確認網路狀態。({e})")
            conn.close()
            return

    # --- 步驟 3：發送最終結果 ---
    embed = discord.Embed(
        title=f"🌌 今日真實運勢 - {sign}",
        description=fortune_text[:4000], 
        color=discord.Color.dark_blue()
    )
    embed.set_footer(text=footer_text)
    
    await ctx.send(content=f"✅ {ctx.author.mention}", embed=embed)
# --- 互動按鈕類別 (動態生成) ---
class QuizButton(discord.ui.Button):
    def __init__(self, key, text, style, result_text):
        # 顯示在按鈕上的文字，例如 "A. 拔武器直接開紅"
        super().__init__(label=f"{key}. {text}", style=style)
        self.result_text = result_text

    async def callback(self, interaction: discord.Interaction):
        # ephemeral=True：測驗結果像悄悄話一樣，只有按按鈕的人自己看得到！
        await interaction.response.send_message(self.result_text, ephemeral=True)

# --- 視圖類別 (把按鈕裝進去) ---
class DynamicQuizView(discord.ui.View):
    def __init__(self, question_data):
        super().__init__(timeout=None) # 按鈕不限時
        
        # 定義四種顏色的按鈕風格，依序套用
        styles = [discord.ButtonStyle.danger, discord.ButtonStyle.success, 
                  discord.ButtonStyle.primary, discord.ButtonStyle.secondary]
        
        # 根據 JSON 裡的選項，動態把按鈕加到畫面上
        for i, (key, text) in enumerate(question_data["options"].items()):
            style = styles[i % len(styles)]
            result_text = question_data["results"][key]
            self.add_item(QuizButton(key, text, style, result_text))

# --- 12. 指令：每日心理測驗 ---
@bot.command(name="測驗", help="每日輪替的公會心理測驗！看看你的真實性格。")
async def daily_quiz(ctx):
    try:
        # 讀取本地題庫
        with open('quiz.json', 'r', encoding='utf-8') as f:
            quiz_list = json.load(f)
            
        # 💡 每日輪替核心邏輯：用「今天是今年的第幾天」去取餘數
        day_of_year = datetime.datetime.now().timetuple().tm_yday
        today_index = day_of_year % len(quiz_list)
        today_quiz = quiz_list[today_index]
        
        # 準備發送的題目面板
        embed = discord.Embed(
            title="🔮 波拉西亞每日心理測驗",
            description=f"**{today_quiz['title']}**\n\n*(請點擊下方最符合你直覺的按鈕，測驗結果只有你自己看得到哦！)*",
            color=discord.Color.purple()
        )
        
        # 綁定動態按鈕視圖
        view = DynamicQuizView(today_quiz)
        await ctx.send(embed=embed, view=view)

    except FileNotFoundError:
        await ctx.send("❌ 找不到題庫檔案 (quiz.json)，請聯絡管理員確認系統設定！")
    except Exception as e:
        await ctx.send(f"❌ 讀取題庫發生錯誤：{e}")
# --- 【AI 視覺打寶系統】 ---

# 初始化打寶資料庫
def setup_loot_db():
    conn = sqlite3.connect('guild_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS loot_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  record_date TEXT,
                  record_time TEXT,
                  player TEXT,
                  item TEXT,
                  location TEXT)''')
    conn.commit()
    conn.close()

setup_loot_db()

@bot.command(name="打寶", help="上傳截圖 + !打寶，AI 自動辨識地點與紫裝。")
async def record_loot(ctx):
    # 頻道權限檢查
    if ctx.channel.id != LOOT_CHANNEL_ID:
        await ctx.send(f"❌ 這裡不是打寶區，請到 <#{LOOT_CHANNEL_ID}> 上傳喔！", delete_after=5)
        return

    # 檢查是否有圖片
    if not ctx.message.attachments:
        await ctx.send(f"❌ {ctx.author.mention} 請同時上傳截圖並輸入 `!打寶`！")
        return

    attachment = ctx.message.attachments[0]
    loading_msg = await ctx.send("👁️ **Gemini AI 視覺引擎啟動中**，正在分析截圖內容...")

    try:
        image_bytes = await attachment.read()
        # --- 這裡開始替換原本宣告 model 的部分 ---
        genai.configure(api_key=gemini_api_key)
        
        # 💡 FAE 的暴力解決法：列出所有可能的型號路徑，讓它自己去試
        model_names = [
            'gemini-1.5-flash',
            'models/gemini-1.5-flash',
            'gemini-1.5-flash-latest',
            'models/gemini-1.5-flash-latest'
        ]
        
        model = None
        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                # 簡單測試一下這個名字行不行
                print(f"✅ 成功找到可用模型: {m_name}")
                break 
            except:
                continue
        
        if model is None:
            await loading_msg.edit(content="❌ 無法載入 Gemini 模型，請檢查 Google AI Studio 設定。")
            return

        # 💡 FAE 的精準提示詞：這些也都要在第一個 try 的縮排內
        prompt = """
        這是一張《波拉西亞戰記》的遊戲截圖。
        1. 找出左上角的地圖名稱（如：被破壞的寺院）。
        2. 從聊天廣播找出所有獲得「紫色或金色物品」的紀錄（時間、玩家ID、物品）。
        3. 嚴格以 JSON 格式回傳：[{"time": "時間", "player": "ID", "item": "物品", "location": "地點"}]
        """
        
        image_part = {'mime_type': attachment.content_type, 'data': image_bytes}
        response = await bot.loop.run_in_executor(None, lambda: model.generate_content([image_part, prompt]))
        
        # 解析 AI 回傳的 JSON
        raw_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        data = json.loads(raw_text)

        if not data:
            await loading_msg.edit(content="⚠️ 沒看到紫裝廣播，是不是截圖不夠清楚？")
            return

        # 寫入 SQLite
        today_str = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d')
        conn = sqlite3.connect('guild_data.db')
        c = conn.cursor()
        
        added_list = []
        for entry in data:
            c.execute("INSERT INTO loot_history (record_date, record_time, player, item, location) VALUES (?, ?, ?, ?, ?)",
                      (today_str, entry['time'], entry['player'], entry['item'], entry['location']))
            added_list.append(f"🔹 `[{entry['time']}]` **{entry['player']}** 於 **{entry['location']}** 獲得 **{entry['item']}**")
            
        conn.commit()
        conn.close()

        await loading_msg.edit(content="✅ **AI 辨識成功！已記入公會資產：**\n" + "\n".join(added_list))

    except Exception as e:
        await loading_msg.edit(content=f"❌ 辨識出錯了... 請確認 Gemini Key 是否正確。({e})")

# --- 【匯出報表功能】 ---
@bot.command(name="打寶報表", help="匯出當月打寶紀錄。")
async def export_loot(ctx, month_str: str = None):
    if not month_str:
        month_str = datetime.datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m')

    conn = sqlite3.connect('guild_data.db')
    c = conn.cursor()
    c.execute("SELECT record_date, record_time, player, item, location FROM loot_history WHERE record_date LIKE ?", (f"{month_str}%",))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await ctx.send(f"📊 {month_str} 目前尚無紀錄。")
        return

    filename = f"Loot_Report_{month_str}.csv"
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['日期', '時間', '玩家ID', '物品名稱', '掉落地點'])
        writer.writerows(rows)

    await ctx.send(f"📊 **{month_str} 公會打寶報表產出完畢！**", file=discord.File(filename))
    os.remove(filename)
# ⚠️ run 永遠在最後一行
bot.run(TOKEN)