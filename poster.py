import os, json, time, random, gspread, requests
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "17841473819180137")
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

# ヘッダー定義
H_SCHED   = "投稿日時"
H_WEEKDAY = "曜日"
H_BODY    = "投稿文"
H_STATUS  = "状態"
H_URL     = "投稿URL"
H_VIEWS   = "再生数"
H_REACH   = "閲覧者数"
H_PROFILE = "プロフアクセス数"
H_FOLLOWS = "フォロー数"
H_LIKES   = "いいね数"
H_LIKE_R  = "いいね率"
H_REPLY_R = "返信率"
H_SHARE_R = "シェア率"
H_QUOTE_R = "引用率"
H_REPOST_R= "再投稿率"
H_ID      = "投稿ID"

STATUS_BEFORE = "投稿前"
STATUS_DONE   = "投稿済み"

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def post_to_threads(text):
    base_url = "https://graph.threads.net/v1.0"
    create_resp = requests.post(f"{base_url}/{THREADS_USER_ID}/threads",
        data={"media_type":"TEXT","text":text,"access_token":THREADS_ACCESS_TOKEN})
    create_data = create_resp.json()
    if "error" in create_data:
        raise Exception(f"コンテナ作成失敗: {create_data['error']['message']}")
    container_id = create_data["id"]
    time.sleep(5)
    publish_resp = requests.post(f"{base_url}/{THREADS_USER_ID}/threads_publish",
        data={"creation_id":container_id,"access_token":THREADS_ACCESS_TOKEN})
    publish_data = publish_resp.json()
    if "error" in publish_data:
        raise Exception(f"公開失敗: {publish_data['error']['message']}")
    return publish_data["id"]

def get_permalink(post_id):
    """投稿のパーマリンクを取得"""
    try:
        resp = requests.get(
            f"https://graph.threads.net/v1.0/{post_id}",
            params={"fields": "permalink", "access_token": THREADS_ACCESS_TOKEN}
        )
        data = resp.json()
        return data.get("permalink", "")
    except Exception as e:
        print(f"パーマリンク取得失敗: {e}")
        return ""

def get_insights(post_id):
    """投稿のインサイトを取得"""
    # Threads Media Insights API で有効なpost-levelメトリクスのみ
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
            # total_value形式またはvalues形式に対応
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

def parse_datetime(s):
    for fmt in [
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=JST)
        except ValueError:
            continue
    return None

def col_index(header, name):
    """ヘッダー名から1-indexedの列番号を返す。なければNone"""
    try:
        return header.index(name) + 1
    except ValueError:
        return None

def main():
    # ランダム遅延 0〜10分（投稿時刻をランダムにずらす）
    delay = random.randint(0, 600)
    print(f"ランダム遅延: {delay}秒")
    time.sleep(delay)

    now_jst = datetime.now(JST)
    print(f"実行時刻(JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')}")

    sheet = get_sheet()
    rows = sheet.get_all_values()
    header = rows[0]

    c_sched    = col_index(header, H_SCHED)
    c_body     = col_index(header, H_BODY)
    c_status   = col_index(header, H_STATUS)
    c_id       = col_index(header, H_ID)
    c_url      = col_index(header, H_URL)
    c_views    = col_index(header, H_VIEWS)
    c_reach    = col_index(header, H_REACH)
    c_profile  = col_index(header, H_PROFILE)
    c_follows  = col_index(header, H_FOLLOWS)
    c_likes    = col_index(header, H_LIKES)
    c_like_r   = col_index(header, H_LIKE_R)
    c_reply_r  = col_index(header, H_REPLY_R)
    c_share_r  = col_index(header, H_SHARE_R)
    c_quote_r  = col_index(header, H_QUOTE_R)
    c_repost_r = col_index(header, H_REPOST_R)

    posted_count = 0
    insight_count = 0

    for i, row in enumerate(rows[1:], start=2):
        if not c_sched or len(row) < c_sched:
            continue
        scheduled_at = row[c_sched - 1].strip()
        if not scheduled_at:
            continue
        sched_dt = parse_datetime(scheduled_at)
        if sched_dt is None:
            print(f"行{i}: 日付パース失敗 '{scheduled_at}'")
            continue

        diff = abs((now_jst - sched_dt).total_seconds())
        overdue = (now_jst - sched_dt).total_seconds()  # 正=過去(遅延), 負=未来
        print(f"行{i}: {scheduled_at} -> 差分{diff:.0f}秒 (overdue={overdue:.0f}秒)")

        # ===== 通常投稿処理 =====
        # GitHub Actionsのcron遅延(最大6h+)に対応するため、
        # 「予定時刻から最大8時間後まで」後追い投稿を許容する
        # 未来の投稿（overdue < 0）は絶対に投稿しない
        # すでに投稿済みの行はスキップ（二重投稿防止）
        if 0 <= overdue <= 28800:  # 0〜8時間以内の遅延を許容
            status = row[c_status - 1].strip() if c_status and len(row) >= c_status else ""
            if status == STATUS_DONE:
                print(f"行{i}: 投稿済みのためスキップ")
                continue
            body = row[c_body - 1].strip() if c_body and len(row) >= c_body else ""
            if not body:
                print(f"行{i}: 投稿文なし、スキップ")
                continue
            print(f"行{i}: 投稿実行中...")
            try:
                post_id = post_to_threads(body)
                if c_status:
                    sheet.update_cell(i, c_status, STATUS_DONE)
                if c_id:
                    sheet.update_cell(i, c_id, post_id)
                # パーマリンク取得・書き込み
                if c_url:
                    permalink = get_permalink(post_id)
                    if permalink:
                        sheet.update_cell(i, c_url, permalink)
                print(f"行{i}: 投稿完了 post_id={post_id}")
                posted_count += 1
            except Exception as e:
                print(f"行{i}: 投稿失敗 - {e}")

        # ===== インサイト書き込み (24時間〜32時間前の投稿) =====
        # GitHub Actions遅延対応: 24h後±8h以内なら取得する
        hours_since_post = (now_jst - sched_dt).total_seconds() / 3600
        if 24 <= hours_since_post <= 32:
            post_id_val = row[c_id - 1].strip() if c_id and len(row) >= c_id else ""
            if not post_id_val:
                continue
            status = row[c_status - 1].strip() if c_status and len(row) >= c_status else ""
            if status != STATUS_DONE:
                continue
            # すでにインサイト取得済みなら skip
            if c_views and len(row) >= c_views and row[c_views - 1].strip():
                print(f"行{i}: インサイト取得済みのためスキップ")
                continue
            print(f"行{i}: インサイト取得中...")
            insights = get_insights(post_id_val)
            if insights is None:
                print(f"行{i}: インサイト取得失敗")
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
            if c_reach:    updates.append((i, c_reach,    views))  # Threads APIはreach非対応のためviewsと同値
            if c_likes:    updates.append((i, c_likes,    likes))
            if c_like_r:   updates.append((i, c_like_r,   rate(likes, views)))
            if c_reply_r:  updates.append((i, c_reply_r,  rate(replies, views)))
            if c_quote_r:  updates.append((i, c_quote_r,  rate(quotes, views)))
            if c_repost_r: updates.append((i, c_repost_r, rate(reposts, views)))
            for row_n, col_n, val in updates:
                sheet.update_cell(row_n, col_n, val)
            print(f"行{i}: インサイト書き込み完了 views={views}, likes={likes}")
            insight_count += 1

    print(f"完了: {posted_count}件投稿, {insight_count}件インサイト更新")

if __name__ == "__main__":
    main()
