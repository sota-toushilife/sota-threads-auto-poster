import os, json, time, gspread, requests
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "17841473819180137")
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

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

def parse_datetime(s):
    """複数フォーマットに対応した日付パース（Sheetsの日本語ロケール対応）"""
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

def main():
    now_jst = datetime.now(JST)
    print(f"実行時刻(JST): {now_jst.strftime('%Y-%m-%d %H:%M:%S')}")
    sheet = get_sheet()
    rows = sheet.get_all_values()
    header = rows[0]
    col_scheduled = header.index("scheduled_at")
    col_body = header.index("body")
    col_posted = header.index("posted")
    col_post_id = header.index("post_id")
    posted_count = 0
    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= col_posted: continue
        scheduled_at = row[col_scheduled].strip()
        body = row[col_body].strip()
        posted = row[col_posted].strip().upper() if len(row) > col_posted else ""
        if posted == "TRUE": continue
        if not scheduled_at or not body: continue
        sched_dt = parse_datetime(scheduled_at)
        if sched_dt is None:
            print(f"行{i}: 日付パース失敗 '{scheduled_at}'")
            continue
        diff = abs((now_jst - sched_dt).total_seconds())
        print(f"行{i}: {scheduled_at} -> 差分{diff:.0f}秒")
        if diff > 900: continue
        print(f"行{i}: 投稿実行中...")
        post_id = post_to_threads(body)
        sheet.update_cell(i, col_posted + 1, "TRUE")
        sheet.update_cell(i, col_post_id + 1, post_id)
        print(f"行{i}: 投稿完了 post_id={post_id}")
        posted_count += 1
    print(f"完了: {posted_count}件投稿")

if __name__ == "__main__":
    main()
