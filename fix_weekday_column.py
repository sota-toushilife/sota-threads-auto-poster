"""
投稿日時から正しい曜日を計算して曜日列を上書きするスクリプト
投稿前ステータスの全行を対象
"""
import os, json, gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))
WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]

def main():
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_CREDENTIALS_JSON),
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
    rows = sheet.get_all_values()
    header = rows[0]

    col_sched   = header.index("投稿日時")
    col_status  = header.index("状態")
    col_weekday = header.index("曜日")

    updates = []
    fixed = 0
    for i, row in enumerate(rows[1:], start=2):
        status = row[col_status].strip() if len(row) > col_status else ""
        if status != "投稿前":
            continue
        sched_str = row[col_sched].strip() if len(row) > col_sched else ""
        try:
            sched_dt = datetime.strptime(sched_str, "%Y/%m/%d %H:%M").replace(tzinfo=JST)
        except:
            continue

        correct_wd = WEEKDAYS_JP[sched_dt.weekday()]
        current_wd = row[col_weekday].strip() if len(row) > col_weekday else ""

        if current_wd != correct_wd:
            col_letter = chr(ord('A') + col_weekday)
            updates.append({
                "range": f"{col_letter}{i}",
                "values": [[correct_wd]]
            })
            fixed += 1

    print(f"投稿前合計チェック: {len([r for r in rows[1:] if len(r) > col_status and r[col_status].strip() == '投稿前'])} 件")
    print(f"曜日ズレあり（修正対象）: {fixed} 件")

    if updates:
        sheet.spreadsheet.values_batch_update({
            "valueInputOption": "RAW",
            "data": updates
        })
        print(f"完了: {fixed} 件の曜日列を修正しました")
    else:
        print("曜日ズレなし。修正不要。")

if __name__ == "__main__":
    main()
