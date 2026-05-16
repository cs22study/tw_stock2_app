import os
import datetime
import requests
import twstock

# ==================== 變數設定 ====================
# 請在此修改您要查詢的台股股票代號清單
STOCK_LIST = ['0050', '2330', '2317', '2454', '2303']

# 取得 GitHub Actions 傳入的環境變數（用於通知）
LINE_TOKEN = os.getenv('LINE_TOKEN')
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
# ==================================================

def fetch_stock_prices():
    """使用 twstock 查詢多檔股票的即時資訊"""
    results = []
    # 批次查詢股票即時資訊
    stocks_data = twstock.realtime.get(STOCK_LIST)
    
    for code in STOCK_LIST:
        data = stocks_data.get(code)
        if data and data.get('success'):
            info = data['info']
            realtime_data = data['realtime']
            
            # twstock 資料解析
            name = info.get('name', '未知')
            # 優先拿成交價(latest_trade_price)，若盤前或沒成交則拿買進第一檔(best_bid_price)
            current_price = realtime_data.get('latest_trade_price')
            if current_price == '-' or not current_price:
                bids = realtime_data.get('best_bid_price', ['-'])
                current_price = bids[0] if bids else '-'
            
            # 讀取昨日收盤價計算漲跌
            try:
                stock_history = twstock.Stock(code)
                yesterday_close = stock_history.price[-1] if stock_history.price else None
            except Exception:
                yesterday_close = None
                
            # 計算漲跌幅
            change_str = "-"
            if current_price != '-' and yesterday_close:
                change = float(current_price) - float(yesterday_close)
                change_percent = (change / float(yesterday_close)) * 100
                change_str = f"{'+' if change > 0 else ''}{change:.2f} ({'+' if change > 0 else ''}{change_percent:.2f}%)"

            results.append({
                'code': code,
                'name': name,
                'price': current_price,
                'change': change_str,
                'time': info.get('time', '')
            })
        else:
            results.append({
                'code': code, 'name': '查詢失敗', 'price': '-', 'change': '-', 'time': '-'
            })
    return results

def send_notifications(results, now_str):
    """整理股價訊息並發送到 Line 或 Discord"""
    # 組裝訊息文字
    msg_lines = [f"📈 【台股即時股價回報】", f"更新時間：{now_str}", "--------------------"]
    for r in results:
        msg_lines.append(f"🔹 {r['code']} {r['name']}: {r['price']} (漲跌: {r['change']})")
    message = "\n".join(msg_lines)

    # 1. 發送 Line Notify
    if LINE_TOKEN:
        try:
            url = "https://notify-api.line.me/api/notify"
            headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
            payload = {"message": "\n" + message}
            requests.post(url, headers=headers, data=payload)
            print("Line 通知發送成功！")
        except Exception as e:
            print(f"Line 發送失敗: {e}")

    # 2. 發送 Discord Webhook
    if DISCORD_WEBHOOK:
        try:
            payload = {"content": message}
            requests.post(DISCORD_WEBHOOK, json=payload)
            print("Discord 通知發送成功！")
        except Exception as e:
            print(f"Discord 發送失敗: {e}")

def generate_html_page(results, now_str):
    """將股價資料填入 HTML 模板，並輸出為 index.html（科技風版本）"""
    table_rows = ""
    for r in results:
        # 根據漲跌決定霓虹發光顏色與箭頭
        color_style = "color: #e0e0e0;"  # 平盤灰色
        icon = "▬"
        
        if '+' in r['change']:
            color_style = "color: #ff4a5a; text-shadow: 0 0 8px rgba(255, 74, 90, 0.6);"  # 科技紅發光
            icon = "▲"
        elif '-' in r['change'] and r['change'] != "-":
            color_style = "color: #00ff87; text-shadow: 0 0 8px rgba(0, 255, 135, 0.6);"  # 科技綠發光
            icon = "▼"

        table_rows += f"""
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); transition: all 0.3s;">
            <td style="color: #00d2ff; font-weight: bold; font-family: 'Courier New', monospace;">{r['code']}</td>
            <td style="color: #ffffff; font-weight: 500;">{r['name']}</td>
            <td style="color: #ffffff; font-weight: bold; font-family: 'Courier New', monospace;">{r['price']}</td>
            <td style="{color_style} font-family: 'Courier New', monospace;">{icon} {r['change']}</td>
            <td style="color: #8892b0; font-size: 0.9rem;">{r['time']}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ MATRIX STOCK TERMINAL</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #0a0f1d;
            background-image: 
                radial-gradient(at 50% 0%, rgba(0, 210, 255, 0.1) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(138, 43, 226, 0.05) 0px, transparent 50%);
            color: #e2e8f0;
            font-family: 'Segoe UI', system-ui, sans-serif;
            min-height: 100vh;
        }}
        .cyber-panel {{
            background: rgba(16, 24, 48, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 210, 255, 0.2);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37), 0 0 15px rgba(0, 210, 255, 0.1);
            border-radius: 12px;
        }}
        .cyber-header {{
            border-bottom: 2px solid rgba(0, 210, 255, 0.3);
            padding-bottom: 15px;
        }}
        .glitch-text {{
            color: #00d2ff;
            text-shadow: 0 0 10px rgba(0, 210, 255, 0.5);
            font-weight: 800;
            letter-spacing: 2px;
        }}
        .scanline {{
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 0, 0.06));
            z-index: 9999;
            background-size: 100% 4px, 6px 100%;
            pointer-events: none;
            opacity: 0.4;
        }}
        .table {{
            --bs-table-bg: transparent;
            --bs-table-color: #e2e8f0;
            --bs-table-hover-bg: rgba(0, 210, 255, 0.05);
        }}
        .table th {{
            color: #00d2ff !important;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 1px;
            border-bottom: 2px solid rgba(0, 210, 255, 0.3) !important;
        }}
        tr:hover td {{
            color: #fff !important;
        }}
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-9">
                <div class="card cyber-panel p-4">
                    <div class="cyber-header d-flex justify-content-between align-items-center mb-4">
                        <h3 class="mb-0 glitch-text">🖥️ TW_STOCK // TERMINAL</h3>
                        <span class="badge" style="background: rgba(0, 210, 255, 0.2); color: #00d2ff; border: 1px solid #00d2ff; box-shadow: 0 0 8px rgba(0,210,255,0.3);">SYSTEM ONLINE</span>
                    </div>
                    <div class="card-body p-0">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span style="color: #8892b0; font-size: 0.9rem;">
                                <span style="color: #00d2ff;">▶</span> LAST_UPDATE: {now_str}
                            </span>
                            <span style="color: #8892b0; font-size: 0.8rem; font-family: monospace;">CORE_v2.0 // REFRESH_SUCCESS</span>
                        </div>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle mb-0">
                                <thead>
                                    <tr>
                                        <th>CODE</th>
                                        <th>NAME</th>
                                        <th>PRICE</th>
                                        <th>CHG (%)</th>
                                        <th>TIME</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    # 建立輸出資料夾並寫入檔案
    os.makedirs('_site', exist_ok=True)
    with open('_site/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("科技風網頁 index.html 生成成功！")

if __name__ == "__main__":
    # 設定時區為台北時間
    tz_utc8 = datetime.timezone(datetime.timedelta(hours=8))
    now_str = datetime.datetime.now(tz_utc8).strftime('%Y-%m-%d %H:%M:%S')
    
    print("正在抓取台股即時資料...")
    stock_results = fetch_stock_prices()
    
    print("正在發送社群通知...")
    send_notifications(stock_results, now_str)
    
    print("正在建立網頁檔案...")
    generate_html_page(stock_results, now_str)
