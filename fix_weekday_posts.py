"""
曜日にちなんだ投稿を正しい曜日のスロットに移動させるスクリプト。
例：「今日は月曜日」と書いてある投稿 → 月曜日のスロットに移動
"""
import os, json, re, gspread
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]
JST = timezone(timedelta(hours=9))

# 曜日キーワード検出マップ
WEEKDAY_KEYWORDS = {
    0: ["月曜", "Monday", "月曜日"],
    1: ["火曜", "Tuesday", "火曜日"],
    2: ["水曜", "Wednesday", "水曜日"],
    3: ["木曜", "Thursday", "木曜日"],
    4: ["金曜", "Friday", "金曜日"],
    5: ["土曜", "Saturday", "土曜日"],
    6: ["日曜", "Sunday", "日曜日"],
}

def detect_weekday(text):
    """投稿文から曜日を検出。見つかれば0(月)〜6(日)、なければNone"""
    for wd, keywords in WEEKDAY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return wd
    return None

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

    col_sched   = header.index("投稿日時")
    col_status  = header.index("状態")
    col_body    = header.index("投稿文")
    col_weekday = header.index("曜日") if "曜日" in header else None

    now_jst = datetime.now(JST)

    # 未投稿行を収集
    unposted = []
    for i, row in enumerate(rows[1:], start=2):
        status = row[col_status].strip() if len(row) > col_status else ""
        if status != "投稿前":
            continue
        sched_str = row[col_sched].strip() if len(row) > col_sched else ""
        body = row[col_body].strip() if len(row) > col_body else ""
        try:
            for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M"):
                try:
                    sched_dt = datetime.strptime(sched_str, fmt).replace(tzinfo=JST)
                    break
                except ValueError:
                    continue
            else:
                continue
        except:
            continue
        if sched_dt <= now_jst:
            continue
        unposted.append({
            "row": i,
            "sched": sched_dt,
            "body": body,
            "weekday_needed": detect_weekday(body),
        })

    # 曜日指定あり/なしに分離
    weekday_posts = [p for p in unposted if p["weekday_needed"] is not None]
    free_posts    = [p for p in unposted if p["weekday_needed"] is None]

    print(f"未投稿合計: {len(unposted)} 件")
    print(f"  曜日指定あり: {len(weekday_posts)} 件")
    print(f"  曜日指定なし: {len(free_posts)} 件")

    if not weekday_posts:
        print("曜日指定投稿なし。修正不要。")
        return

    # 全スロット一覧（現在より未来のもの）
    all_slots = sorted([p["sched"] for p in unposted])

    # 曜日指定投稿に対して「正しい曜日の最も近いスロット」を割り当て
    # アルゴリズム：
    # 1. 曜日指定投稿を「必要な曜日」でグループ化
    # 2. 各スロットに対してどの投稿を割り当てるか最適化
    # シンプルな実装：スロットを曜日ごとに分けて、曜日指定投稿を優先配置

    slot_weekday_map = {s: s.weekday() for s in all_slots}  # slot -> weekday(0-6)

    # 各スロットに割り当てる投稿bodyを決定
    # まず曜日指定投稿をその曜日のスロットに割り当て
    slot_assignments = {s: None for s in all_slots}

    for wp in weekday_posts:
        needed_wd = wp["weekday_needed"]
        # この曜日のスロットで未割り当てのものを探す（最も早いもの）
        matched = None
        for s in sorted(all_slots):
            if slot_assignments[s] is None and s.weekday() == needed_wd:
                matched = s
                break
        if matched:
            slot_assignments[matched] = wp
            print(f"  曜日一致: {wp['body'][:30]}... → {matched.strftime('%Y/%m/%d(%a) %H:%M')}")
        else:
            # 同じ曜日のスロットがない場合は空きスロットの最初
            for s in sorted(all_slots):
                if slot_assignments[s] is None:
                    slot_assignments[s] = wp
                    print(f"  曜日スロット不足、次の空き: {wp['body'][:30]}... → {s.strftime('%Y/%m/%d(%a) %H:%M')}")
                    break

    # 残りの空きスロットにfree_postsを割り当て
    free_iter = iter(free_posts)
    for s in sorted(all_slots):
        if slot_assignments[s] is None:
            try:
                fp = next(free_iter)
                slot_assignments[s] = fp
            except StopIteration:
                break

    # スプシへの書き込みデータ作成（bodyを入れ替え）
    # 元の行番号→新しいbody/sched の対応表を作る
    # slot_assignments: {new_sched: post_obj(元の行番号とbody)}
    # 元の行番号のスケジュールは変わらない（スロットは固定）
    # bodyだけを入れ替える

    # row -> new_body の対応
    # sched順に並んだスロットと投稿を対応付け
    orig_row_to_slot = {p["row"]: p["sched"] for p in unposted}
    slot_to_orig_row = {p["sched"]: p["row"] for p in unposted}

    # slot_assignments: {slot_dt: post_obj}
    # post_obj["row"] = 元の行番号、post_obj["body"] = 投稿文
    # slot_dt = そのスロットの日時（元々どこかの行のsched）

    # 書き込み：各スロット（行）に対してbodyを上書き
    updates = []
    weekdays_jp = ["月","火","水","木","金","土","日"]
    for slot_dt, post_obj in slot_assignments.items():
        if post_obj is None:
            continue
        target_row = slot_to_orig_row[slot_dt]  # このスロットが元々あった行
        new_body = post_obj["body"]
        # bodyを書き込む
        updates.append({
            "range": f"{chr(65 + col_body)}{target_row}",
            "values": [[new_body]]
        })

    if updates:
        sheet.spreadsheet.values_batch_update({
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": u["range"], "values": u["values"]} for u in updates]
        })
        print(f"\n{len(updates)} 件の投稿文を入れ替えました。")
    else:
        print("変更なし。")

if __name__ == "__main__":
    main()
