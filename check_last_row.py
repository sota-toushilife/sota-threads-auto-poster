import os, json, gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

rows = sheet.get_all_values()
header = rows[0]
col_sched = header.index("投稿日時")
col_status = header.index("状態")

# 投稿前の最後の日時を確認
unposted = []
for i, row in enumerate(rows[1:], start=2):
    if len(row) > col_status and row[col_status].strip() == "投稿前":
        sched = row[col_sched].strip() if len(row) > col_sched else ""
        if sched:
            unposted.append(sched)

print(f"総行数（ヘッダー除く）: {len(rows)-1}")
print(f"投稿前の件数: {len(unposted)}")
if unposted:
    print(f"最初の投稿前: {unposted[0]}")
    print(f"最後の投稿前: {unposted[-1]}")
