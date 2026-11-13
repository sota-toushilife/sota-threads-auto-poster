"""
インサイトデータをJSONで出力するスクリプト（分析用）
"""
import os, json, gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

sheet = get_sheet()
rows = sheet.get_all_values()
header = rows[0]

col_status  = header.index("状態")
col_views   = header.index("再生数")
col_likes   = header.index("いいね数")
col_body    = header.index("投稿文")
col_sched   = header.index("投稿日時")
col_like_r  = header.index("いいね率")
col_reply_r = header.index("返信率")
col_share_r = header.index("シェア率")
col_quote_r = header.index("引用率")
col_repost_r= header.index("再投稿率")

data = []
for row in rows[1:]:
    def g(c):
        return row[c].strip() if len(row) > c else ""
    if g(col_status) != "投稿済み":
        continue
    views_str = g(col_views)
    if not views_str or views_str == "0":
        continue
    try:
        views = int(views_str)
    except:
        continue
    def f(c):
        try: return float(g(c))
        except: return 0.0
    data.append({
        "sched": g(col_sched),
        "body": g(col_body),
        "views": views,
        "likes": int(g(col_likes)) if g(col_likes) else 0,
        "like_rate": f(col_like_r),
        "reply_rate": f(col_reply_r),
        "share_rate": f(col_share_r),
        "quote_rate": f(col_quote_r),
        "repost_rate": f(col_repost_r),
    })

print(json.dumps(data, ensure_ascii=False, indent=2))
