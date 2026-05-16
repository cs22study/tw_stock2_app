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
    """將股價資料填入 HTML 模板，並輸出為 index.html"""
    table_rows = ""
    for r in results:
        # 根據漲跌決定顏色樣式
        color_class = "text-dark"
        if '+' in r['change']:
            color_class = "text-danger fw-bold"  # 紅色代表漲
        elif '-' in r['change'] and r['change'] != "-":
            color_class = "text-success fw-bold" # 綠色代表跌

        table_rows += f"""
        <tr>
            <td>{r['code']}</td>
            <td>{r['name']}</td>
            <td class="fw-bold">{r['price']}</td>
            <td class="{color_class}">{r['change']}</td>
            <td>{r['time']}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>台股即時股價看板</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">📊 台股即時股價看板</h4>
                        <span class="badge bg-secondary">自動更新</span>
                    </div>
                    <div class="card-body">
                        <p class="text-muted">最後更新時間：{now_str}</p>
                        <div class="table-responsive">
                            <table class="table table-hover align-middle">
                                <thead class="table-dark">
                                    <tr>
                                        <th>股票代號</th>
                                        <th>股票名稱</th>
                                        <th>即時股價</th>
                                        <th>漲跌幅</th>
                                        <th>資料時間</th>
                                    </tr>
                                 Populated by Python 
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
    print("網頁 index.html 生成成功！")

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
