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
    "投稿日時", "曜日", "投稿文", "状態", "投稿URL",
    "再生数", "閲覧者数", "プロフアクセス数", "フォロー数", "いいね数",
    "いいね率", "返信率", "シェア率", "引用率", "再投稿率", "投稿ID"
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

    # ヘッダーが既にNEW_HEADERSと一致しているか確認
    if header == NEW_HEADERS:
        print("すでに最新の列順です。終了します。")
        return

    # 全データを読み込む
    data_rows = rows[1:]  # ヘッダーを除いたデータ行

    # 旧ヘッダー（英語）か新ヘッダー（日本語・旧順）かを判定して列マップを作る
    def get_col(h, name, fallback=None):
        try:
            return h.index(name)
        except ValueError:
            return fallback

    # 英語ヘッダー（初回変換前）
    if "scheduled_at" in header:
        idx_sched   = get_col(header, "scheduled_at")
        idx_body    = get_col(header, "body")
        idx_posted  = get_col(header, "posted")
        idx_post_id = get_col(header, "post_id")
        idx_url     = None
        old_format  = True
    else:
        # 日本語ヘッダー（列順が違う旧版）
        idx_sched   = get_col(header, "投稿日時")
        idx_body    = get_col(header, "投稿文")
        idx_posted  = get_col(header, "状態")
        idx_post_id = get_col(header, "投稿ID")
        idx_url     = get_col(header, "投稿URL")
        old_format  = False

    # 既存のインサイト列を列名→インデックスでマップ
    insight_cols = ["再生数","閲覧者数","プロフアクセス数","フォロー数","いいね数",
                    "いいね率","返信率","シェア率","引用率","再投稿率"]
    insight_idx = {name: get_col(header, name) for name in insight_cols}

    # 新しいシートデータを構築
    new_rows = [NEW_HEADERS]

    for row in data_rows:
        def cv(idx):
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        sched   = cv(idx_sched)
        body    = cv(idx_body)
        posted  = cv(idx_posted)
        post_id = cv(idx_post_id)
        url     = cv(idx_url)

        # 曜日を計算
        weekday = ""
        dt = parse_datetime(sched)
        if dt:
            weekday = WEEKDAY_MAP.get(dt.weekday(), "")

        # 状態を変換（英語の場合）
        if old_format:
            if posted.upper() == "TRUE":
                status = "投稿済み"
            else:
                status = "投稿前"
        else:
            status = posted  # すでに日本語

        new_row = [
            sched,
            weekday,
            body,
            status,
            url,
        ] + [cv(insight_idx.get(name)) for name in insight_cols] + [
            post_id,  # 投稿ID（一番右）
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
