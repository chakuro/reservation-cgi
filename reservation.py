#!/usr/bin/env python3
#coding: utf-8

# モジュールのインポート
import sys
import os
import io
import cgi
import csv
import re
import mojimoji
from datetime import datetime as dt
from datetime import timedelta as td
from jinja2 import Environment, FileSystemLoader

# 環境設定
script_dir = os.path.dirname(__file__)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# マシンと所属の読み込み
with open("{}/settings/machines.txt".format(script_dir), "r", encoding="utf-8") as f:
    machines = [x.rstrip("\n") for x in f]
with open("{}/settings/lab.txt".format(script_dir), "r", encoding="utf-8") as f:
    lab_list = [x.rstrip("\n") for x in f]
for item in machines:
    os.makedirs("./history/{}".format(item).encode("utf-8"), exist_ok=True)

# 今日の日付の読み込みと、「今日-10日」?「今日+30日」の日付リストの作成
today = dt.now()
today_query = today.strftime('%Y%m%d')
today_label = today.strftime('%m/%d (%a)')
dlist_query = [(today + td(days=i)).strftime('%Y%m%d') for i in range(-10,30)]
dlist_label = [(today + td(days=i)).strftime('%m/%d (%a)') for i in range(-10,30)]

# エラーメッセージ欄を用意
message = ""

# # # ユーザーによって選択されたパラメータを取得 # # #
form = cgi.FieldStorage()
# 予約内容の取得
start = mojimoji.zen_to_han(form.getvalue("start", ""))
end = mojimoji.zen_to_han(form.getvalue("end", ""))
name = form.getvalue("name", "")
lab = form.getvalue("lab", "")
memo = form.getvalue("memo", " ")
# 日付とマシンの取得
selected_machine = form.getvalue("selected_machine", "%s" % machines[0])
selected_date_query = form.getvalue("selected_date", today_query)
selected_date_label = dt.strptime(selected_date_query, "%Y%m%d").strftime('%m/%d (%a)')
# どのボタンが押されたかの判定を取得
reg_switch = form.getvalue("reg_switch", None)
del_switch = form.getvalue("del_switch", None)
del_id = form.getvalue("delete", None)

# # # 予定登録モード # # #
if reg_switch == "1":
    check_result = 0

    # hhmm表記で入力された場合はhh:mm表記へ変換
    if re.fullmatch("\d{4}", start) is not None:
        start = start[0:2] + ':' + start[2:4]
    if re.fullmatch("\d{4}", end) is not None:
        end = end[0:2] + ':' + end[2:4]

    # 入力書式判定
    if re.fullmatch("\d{2}:\d{2}", start) is None or int(start.replace(":", "")) > 2400 or int(start[3:5]) >= 60:
        message += "開始時刻を正しく入力してください(例 04:55)"
        check_result += 1
    elif re.fullmatch("\d{2}:\d{2}", end) is None or int(end.replace(":", "")) > 2400 or int(end[3:5]) >= 60:
        message += "終了時刻を正しく入力してください(例 07:25)"
        check_result += 1
    elif name == "":
        message += "名前を入力してください"
        check_result += 1
    elif lab == "":
        message += "内線番号を入力してください"
        check_result += 1
    else:
        start_num = int(start.replace(":", ""))
        end_num = int(end.replace(":", ""))
        if start_num >= end_num:
            message += "終了時刻は開始時刻よりも遅い時間を指定して下さい。 "
            check_result += 1

        # 予定重複判定
        with open("{}/history/{}/{}.csv".format(script_dir, selected_machine, selected_date_query).encode("utf-8"), "r", encoding="utf-8") as f:
            log_start_list = [int(row[1].replace(':', '')) for row in csv.reader(f)]
            f.seek(0)
            log_end_list = [int(row[2].replace(':', '')) for row in csv.reader(f)]
        for (log_start,log_end) in zip(log_start_list,log_end_list):
            if start_num < log_start and end_num <= log_start:
                pass
            elif start_num >= log_end and end_num > log_end:
                pass
            else:
                message += "予定が重複しています。 時刻を変更してください。"
                check_result += 1
                break

    # ログファイルへの予定の書き込み
    if check_result == 0:
        with open("{}/history/count.txt".format(script_dir), "r+", encoding="utf-8") as f:
            count = int(f.read())
            f.seek(0)
            f.write(str(count+1))
        new_log = [count+1,start,end,name,lab,memo]
        with open("{}/history/{}/{}.csv".format(script_dir, selected_machine, selected_date_query).encode("utf-8"), "a", encoding="utf-8") as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(new_log)

    # 開始時刻・終了時刻・備考欄を空白に戻すための調整
    start = ""
    end = ""
    memo = ""

# # # 予定削除モード # # #
elif del_switch == "1":
    # 削除すべきデータの抽出
    with open("{}/history/{}/{}.csv".format(script_dir, selected_machine, selected_date_query).encode("utf-8"), "r", encoding="utf-8") as f:
        deleted_data = [row for row in csv.reader(f) if row[0] == del_id]
        f.seek(0)
        alive_data = [row for row in csv.reader(f) if row[0] != del_id]

    # 削除完了後のデータの作成
    with open("{}/history/{}/{}.csv".format(script_dir, selected_machine, selected_date_query).encode("utf-8"), "w", encoding="utf-8") as f:
        for row in alive_data:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(row)

    # 削除データのフォームへの代入
    start = deleted_data[0][1]
    end = deleted_data[0][2]
    name = deleted_data[0][3]
    lab = deleted_data[0][4]
    memo = deleted_data[0][5]

# # # html描画モード # # #
# 予約の読み込み
with open("{}/history/{}/{}.csv".format(script_dir, selected_machine, selected_date_query).encode("utf-8"), "a+", encoding="utf-8") as f:
    f.seek(0)
    data_id = [row for row in csv.reader(f)]
data_time = data_id[:]
data_time.sort(key=lambda x: x[1])

# jinja2へのパラメータ受け渡しとhtml描画
env = Environment(loader=FileSystemLoader(script_dir))
tpl = env.get_template("reservation.html")
html = tpl.render(
                    machines=machines,
                    selected_machine=selected_machine,
                    dlist_label=dlist_label,
                    dlist_query=dlist_query,
                    selected_date_query=str(selected_date_query),
                    selected_date_label=selected_date_label,
                    message=message,
                    start=start,
                    end=end,
                    name=name,
                    memo=memo,
                    lab_list=lab_list,
                    lab=lab,
                    data_time=data_time)
print("Content-type: text/html\n")
print(html)
