import os, json, gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

HEADERS = ["投稿日時","曜日","投稿文","状態","投稿URL",
           "再生数","閲覧者数","プロフアクセス数","フォロー数","いいね数",
           "いいね率","返信率","シェア率","引用率","再投稿率","投稿ID"]

WEEKDAY_MAP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}

# 10/28 10:00 JST に挿入
dt = datetime(2026, 10, 28, 10, 0, tzinfo=JST)
sched_str = dt.strftime("%Y-%m-%d %H:%M")
weekday = WEEKDAY_MAP[dt.weekday()]

body = """同棲のために、NISAから30万円引き出した。

積み立て額150万円が
気づいたら210万円になってた。

その含み益から
退去費用・初期費用として30万円を使った。

「NISAは絶対売るな」って言う人もいる。
でも俺はそう思わない。

必要なときに、必要なことにお金を使える。
それが資産形成の本質だと思う。

お金を増やすのは、人生を豊かにするため。
守るためじゃなく、使うため。

みんなは何のためにNISA積み立ててる？

#NISA #新NISA #資産形成 #投資初心者 #積立NISA"""

creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

rows = sheet.get_all_values()
header = rows[0]

# 重複チェック
existing = {r[header.index("投稿日時")].strip() for r in rows[1:] if r}
if sched_str in existing:
    print(f"すでに存在: {sched_str}")
else:
    new_row = [sched_str, weekday, body, "投稿前", "", "", "", "", "", "", "", "", "", "", "", ""]
    sheet.append_rows([new_row], value_input_option="USER_ENTERED")
    print(f"追加完了: {sched_str} ({weekday})")
