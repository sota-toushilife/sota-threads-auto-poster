"""
スレッズ自動投稿管理シート 構造変換スクリプト
旧: scheduled_at / body / posted / post_id
新: 投稿日時 / 曜日 / 投稿文 / 状態 / 投稿ID / 投稿URL /
    再生数 / 閲覧者数 / プロフアクセス数 / フォロー数 / いいね数 /
    いいね率 / 返信率 / シェア率 / 引用率 / 再投稿率
"""
import os, json, gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

NEW_HEADERS = [
    "投稿日時", "曜日", "投稿文", "状態", "投稿ID", "投稿URL",
    "再生数", "閲覧者数", "プロフアクセス数", "フォロー数", "いいね数",
    "いいね率", "返信率", "シェア率", "引用率", "再投稿率"
]

WEEKDAY_MAP = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def parse_datetime(s):
    for fmt in ["%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=JST)
        except ValueError:
            continue
    return None

def main():
    sheet = get_sheet()
    rows = sheet.get_all_values()
    header = rows[0]

    print(f"現在のヘッダー: {header}")
    print(f"行数: {len(rows)}")

    # 旧ヘッダーの列インデックス（0-based）
    try:
        old_sched  = header.index("scheduled_at")
        old_body   = header.index("body")
        old_posted = header.index("posted")
        old_id     = header.index("post_id")
    except ValueError as e:
        print(f"旧ヘッダーが見つかりません: {e}")
        print("すでに変換済みの可能性があります。終了します。")
        return

    # 全データを読み込む
    data_rows = rows[1:]  # ヘッダーを除いたデータ行

    # 新しいシートデータを構築
    # 新ヘッダー行
    new_rows = [NEW_HEADERS]

    for row in data_rows:
        sched    = row[old_sched].strip()  if old_sched < len(row) else ""
        body     = row[old_body].strip()   if old_body < len(row) else ""
        posted   = row[old_posted].strip() if old_posted < len(row) else ""
        post_id  = row[old_id].strip()     if old_id < len(row) else ""

        # 曜日を計算
        weekday = ""
        dt = parse_datetime(sched)
        if dt:
            weekday = WEEKDAY_MAP.get(dt.weekday(), "")

        # 状態を変換
        if posted.upper() == "TRUE":
            status = "投稿済み"
        else:
            status = "投稿前"

        new_row = [
            sched,     # 投稿日時
            weekday,   # 曜日
            body,      # 投稿文
            status,    # 状態
            post_id,   # 投稿ID
            "",        # 投稿URL（既存分は空、今後自動取得）
            "",        # 再生数
            "",        # 閲覧者数
            "",        # プロフアクセス数
            "",        # フォロー数
            "",        # いいね数
            "",        # いいね率
            "",        # 返信率
            "",        # シェア率
            "",        # 引用率
            "",        # 再投稿率
        ]
        new_rows.append(new_row)

    # シートをクリアして新データを書き込む
    print("シートをクリア中...")
    sheet.clear()
    print("新データを書き込み中...")
    # A1から書き込み
    sheet.update(f"A1:{chr(ord('A') + len(NEW_HEADERS) - 1)}{len(new_rows)}", new_rows)

    # ヘッダー行を太字に（オプション）
    print("完了！")
    print(f"ヘッダー: {NEW_HEADERS}")
    print(f"データ行数: {len(new_rows) - 1}")

if __name__ == "__main__":
    main()
