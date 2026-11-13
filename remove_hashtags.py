"""
投稿前ステータスの投稿からハッシュタグをすべて削除するスクリプト
"""
import os
import re
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def remove_hashtags(text: str) -> str:
    """ハッシュタグ行・ブロックをすべて削除する"""
    if not text:
        return text
    # 行ごとに処理して #で始まる行を削除
    lines = text.split("\n")
    cleaned = [line for line in lines if not re.match(r'\s*#\S+', line)]
    # 末尾の空行を整理
    result = "\n".join(cleaned).rstrip()
    return result

def main():
    creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    gc = gspread.authorize(creds)

    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    all_rows = sheet.get_all_values()

    if not all_rows:
        print("データなし")
        return

    headers = all_rows[0]
    try:
        col_status = headers.index("ステータス")
        col_body = headers.index("投稿本文")
    except ValueError as e:
        print(f"ヘッダーが見つかりません: {e}")
        print(f"ヘッダー一覧: {headers}")
        return

    updates = []
    count = 0
    for i, row in enumerate(all_rows[1:], start=2):
        status = row[col_status] if col_status < len(row) else ""
        body = row[col_body] if col_body < len(row) else ""

        if status == "投稿前" and body:
            new_body = remove_hashtags(body)
            if new_body != body:
                # gspreadのA1記法: 行番号i, 列番号(col_body+1)
                col_letter = chr(ord('A') + col_body)
                updates.append({
                    "range": f"{col_letter}{i}",
                    "values": [[new_body]]
                })
                count += 1

    print(f"ハッシュタグ削除対象: {count}件")

    if updates:
        sheet.spreadsheet.values_batch_update({
            "valueInputOption": "RAW",
            "data": updates
        })
        print(f"完了: {count}件のハッシュタグを削除しました")
    else:
        print("削除対象なし（すでにハッシュタグなし）")

if __name__ == "__main__":
    main()
