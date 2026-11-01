"""
未投稿の行を1日3投稿（7:00・12:00・19:00）に再配置するスクリプト。
投稿済み行はそのまま。投稿文は変えない。日付だけ詰めて再割り当て。
"""
import os, json, gspread
from datetime import datetime, timezone, timedelta, date
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))
TARGET_HOURS = [7, 12, 19]  # 新スケジュール

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

def main():
    sheet = get_sheet()
    rows = sheet.get_all_values()
    header = rows[0]

    # 列インデックス取得
    col_sched  = header.index("投稿日時")
    col_status = header.index("状態")

    # 現在JST日時
    now_jst = datetime.now(JST)
    today = now_jst.date()

    # 未投稿行の行番号を収集（1-indexed、ヘッダー除く）
    unposted_row_indices = []
    for i, row in enumerate(rows[1:], start=2):
        status = row[col_status].strip() if len(row) > col_status else ""
        if status == "投稿前":
            unposted_row_indices.append(i)

    print(f"未投稿行数: {len(unposted_row_indices)}")

    # 新しいスケジュールを生成（今日以降、1日3スロット）
    # 今日の残りスロットから始める
    new_schedule = []
    check_day = today
    while len(new_schedule) < len(unposted_row_indices):
        for h in TARGET_HOURS:
            slot_dt = datetime(check_day.year, check_day.month, check_day.day, h, 0, 0, tzinfo=JST)
            # 過去のスロットはスキップ（今日の既に過ぎた時間も含む）
            if slot_dt > now_jst:
                new_schedule.append(slot_dt)
                if len(new_schedule) >= len(unposted_row_indices):
                    break
        check_day += timedelta(days=1)

    print(f"生成スケジュール数: {len(new_schedule)}")
    print(f"最初: {new_schedule[0].strftime('%Y/%m/%d %H:%M')}")
    print(f"最後: {new_schedule[-1].strftime('%Y/%m/%d %H:%M')}")

    # スプシに書き込む
    # 曜日マッピング
    weekdays = ["月","火","水","木","金","土","日"]
    col_weekday = header.index("曜日") if "曜日" in header else None

    updates = []
    for row_i, slot_dt in zip(unposted_row_indices, new_schedule):
        date_str = slot_dt.strftime("%Y/%m/%d %H:%M")
        updates.append({
            "range": f"{chr(65 + col_sched)}{row_i}",
            "values": [[date_str]]
        })
        if col_weekday is not None:
            wd = weekdays[slot_dt.weekday()]
            updates.append({
                "range": f"{chr(65 + col_weekday)}{row_i}",
                "values": [[wd]]
            })

    # batch_update で一括書き込み
    sheet.spreadsheet.values_batch_update({
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": u["range"], "values": u["values"]} for u in updates]
    })

    print("書き込み完了！")

if __name__ == "__main__":
    main()
