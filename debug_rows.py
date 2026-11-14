"""
スプシの実際の日付フォーマットとステータスを確認するデバッグスクリプト
"""
import os, json, gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_CREDENTIALS_JSON),
    scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
)
sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).sheet1
rows = sheet.get_all_values()
header = rows[0]
print("ヘッダー:", header[:6])

col_sched  = header.index("投稿日時")
col_status = header.index("状態")
col_weekday = header.index("曜日")
col_body   = header.index("投稿文")

# 行65〜75の内容を表示
print("\n--- 行65〜75のデータ ---")
for i, row in enumerate(rows[64:75], start=65):
    sched  = row[col_sched]  if len(row)>col_sched  else ""
    status = row[col_status] if len(row)>col_status else ""
    wd     = row[col_weekday] if len(row)>col_weekday else ""
    body   = (row[col_body][:30] if len(row)>col_body else "")
    print(f"行{i}: sched={repr(sched)} status={repr(status)} 曜日={repr(wd)} body={repr(body)}")

# ステータス集計
from collections import Counter
status_counts = Counter(r[col_status].strip() if len(r)>col_status else "" for r in rows[1:])
print("\nステータス集計:", dict(status_counts))

# 日付パース失敗行数
import re
from datetime import datetime
fail_count = 0
for r in rows[1:]:
    s = r[col_sched].strip() if len(r)>col_sched else ""
    if not s: continue
    try:
        datetime.strptime(s, "%Y/%m/%d %H:%M")
    except:
        try:
            datetime.strptime(s, "%Y-%m-%d %H:%M")
        except:
            fail_count += 1
            if fail_count <= 3:
                print(f"パース失敗例: {repr(s)}")
print(f"日付パース失敗: {fail_count}件")
