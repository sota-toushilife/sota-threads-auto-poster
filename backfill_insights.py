"""
インサイトバックフィルスクリプト
再生数が空で投稿IDがある行を全て対象にインサイトを取得・書き込みする
"""
import os, json, time, gspread, requests
from google.oauth2.service_account import Credentials

THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

H_SCHED   = "投稿日時"
H_STATUS  = "状態"
H_VIEWS   = "再生数"
H_REACH   = "閲覧者数"
H_LIKES   = "いいね数"
H_LIKE_R  = "いいね率"
H_REPLY_R = "返信率"
H_SHARE_R = "シェア率"
H_QUOTE_R = "引用率"
H_REPOST_R= "再投稿率"
H_ID      = "投稿ID"
STATUS_DONE = "投稿済み"

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def col_index(header, name):
    try: return header.index(name) + 1
    except ValueError: return None

def get_insights(post_id):
    # Threads Media Insights API で有効なpost-levelメトリクスのみ指定
    # follows/profile_visits はアカウントレベルのみ → 含めるとAPIエラーになる
    metrics = "views,likes,replies,reposts,quotes"
    try:
        resp = requests.get(
            f"https://graph.threads.net/v1.0/{post_id}/insights",
            params={"metric": metrics, "access_token": THREADS_ACCESS_TOKEN}
        )
        data = resp.json()
        if "error" in data:
            print(f"インサイト取得エラー: {data['error']['message']}")
            return None
        result = {}
        for item in data.get("data", []):
            name = item["name"]
            if "total_value" in item:
                result[name] = item["total_value"].get("value", 0)
            elif "values" in item and item["values"]:
                result[name] = item["values"][-1].get("value", 0)
            else:
                result[name] = 0
        return result
    except Exception as e:
        print(f"インサイト取得失敗: {e}")
        return None

def main():
    sheet = get_sheet()
    rows = sheet.get_all_values()
    header = rows[0]

    c_status   = col_index(header, H_STATUS)
    c_id       = col_index(header, H_ID)
    c_views    = col_index(header, H_VIEWS)
    c_reach    = col_index(header, H_REACH)
    c_likes    = col_index(header, H_LIKES)
    c_like_r   = col_index(header, H_LIKE_R)
    c_reply_r  = col_index(header, H_REPLY_R)
    c_share_r  = col_index(header, H_SHARE_R)
    c_quote_r  = col_index(header, H_QUOTE_R)
    c_repost_r = col_index(header, H_REPOST_R)
    c_sched    = col_index(header, H_SCHED)

    filled = 0
    for i, row in enumerate(rows[1:], start=2):
        # 投稿済み かつ 投稿ID あり かつ 再生数が空 の行のみ対象
        status = row[c_status - 1].strip() if c_status and len(row) >= c_status else ""
        if status != STATUS_DONE:
            continue
        post_id = row[c_id - 1].strip() if c_id and len(row) >= c_id else ""
        if not post_id:
            continue
        views_val = row[c_views - 1].strip() if c_views and len(row) >= c_views else ""
        if views_val:
            print(f"行{i}: インサイト取得済み (views={views_val})、スキップ")
            continue

        sched = row[c_sched - 1].strip() if c_sched and len(row) >= c_sched else "?"
        print(f"行{i}: {sched} → インサイト取得中 (post_id={post_id})")
        insights = get_insights(post_id)
        if insights is None:
            print(f"行{i}: 取得失敗")
            continue

        views = insights.get("views", 0)
        likes = insights.get("likes", 0)
        replies = insights.get("replies", 0)
        quotes = insights.get("quotes", 0)
        reposts = insights.get("reposts", 0)

        def rate(n, d):
            return round(n / d * 100, 2) if d > 0 else 0

        updates = []
        if c_views:    updates.append((i, c_views,    views))
        if c_reach:    updates.append((i, c_reach,    views))
        if c_likes:    updates.append((i, c_likes,    likes))
        if c_like_r:   updates.append((i, c_like_r,   rate(likes, views)))
        if c_reply_r:  updates.append((i, c_reply_r,  rate(replies, views)))
        if c_quote_r:  updates.append((i, c_quote_r,  rate(quotes, views)))
        if c_repost_r: updates.append((i, c_repost_r, rate(reposts, views)))

        for row_n, col_n, val in updates:
            sheet.update_cell(row_n, col_n, val)
            time.sleep(0.1)  # レート制限対策

        print(f"行{i}: 書き込み完了 views={views}, likes={likes}, replies={replies}")
        filled += 1
        time.sleep(1)  # API負荷軽減

    print(f"完了: {filled}件のインサイトをバックフィル")

if __name__ == "__main__":
    main()
