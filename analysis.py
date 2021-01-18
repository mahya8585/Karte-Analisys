""" 形態素解析モデル検証
[前提]
- UT8(BOMなし)
- TSV
- 改行コード LF
- ヘッダーなし
- インデックスなし
"""
from pathlib import Path
import csv
import MeCab
import datetime
import re
import json


def analysis_mecab(text):
    # neologd 辞書の読み込み(今回はWin10上のWSLから呼び出します)
    dir_dic_neologd = Path('/', 'usr', 'lib', 'x86_64-linux-gnu', 'mecab', 'dic', 'mecab-ipadic-neologd')
    mec = MeCab.Tagger('-Ochasen -d ' + str(dir_dic_neologd))
    words_analysis = mec.parse(text)

    # MeCabから返ってくるデータのうち、必要なものだけにとりあえず凝縮
    words = []
    for wa in words_analysis.split('\n'):
        information = wa.split('\t')
        if len(information) == 6:
            wai = '\t'.join([information[0], information[2], information[3]])
            words.append(wai)

    return words


def get_date(normalization_word, karte_date):
    """パラメータが日付情報か否かの判定をおこなう"""
    # TODO 本来はきちんと解析処理を利用して判定すべきであるが、今回は突貫コーディングのためif文で回避することとする。情報の性質上、過去日付の判定をおこなう
    yesterday_list = ['昨日', '昨夜']
    day_before_yesterday_list = ['一昨日', '一昨夜']
    today_list = ['本日', '今朝', '今日']

    writing_date = datetime.datetime.strptime(karte_date, '%Y-%m-%d %H:%M:%S')
    date_format = '%Y-%m-%d'

    if re.match('[0-9]{1,2}月[0-9]{1,2}日', normalization_word) is None:
        # 日付様式の単語ではなかった場合、今日・昨日・一昨日などの単語を含んでいないか検証を行う。含んでいた場合は応じた日付を返却する
        if normalization_word in yesterday_list:
            # 昨日
            yesterday = writing_date - datetime.timedelta(days=1)
            return yesterday.strftime(date_format)

        elif normalization_word in day_before_yesterday_list:
            # 一昨日
            day_before_yesterday = writing_date - datetime.timedelta(days=2)
            return day_before_yesterday.strftime(date_format)
        elif normalization_word in today_list:
            # 本日
            return karte_date
        else:
            return None
    else:
        # 日付様式のデータだった場合は本日付を返却する
        change_date_format = datetime.datetime.strptime(normalization_word, '%m月%d日')
        # TODO 年跨ぎの日付(e.g. 記録日2021年1月1日、症状発生日2020年12月31日 etc.) のケースについては現在未対応。
        return datetime.datetime(year=writing_date.year, month=change_date_format.month, day=change_date_format.day)


def get_body_temperature(normalization_word, appear_date):
    """体温情報を取得する。今回はX度もしくはX℃の記載のデータを取得する。結果は形態素解析結果に依存する"""

    def pattern1(nw):
        return re.match('[3,4][0-9][.][0-9][℃,"度"]', normalization_word)

    def pattern2(nw):
        return re.match('[3,4][0-9][℃,"度"]', normalization_word)

    if pattern1(normalization_word) is None and pattern2(normalization_word) is None:
        return None
    else:
        # いづれかの体温表記パターンに合致した場合は体温データの数値のみ返却する
        body_temperature = re.sub('[℃,"度"]', '', normalization_word)
        # TODO 返却データ型をFHIR準拠にしたい。後ほど確認する。とりあえず暫定出力
        return {'body_temperature': body_temperature, 'appear_date': appear_date}


def main():
    """ メインハンドラー
    """
    # 作業前ファイル
    source_file = Path.cwd().joinpath('cleansing-completed.tsv')

    # ファイルの読み込み
    with open(source_file, 'r', encoding='utf8') as source_tsv:
        tsv_file = csv.reader(source_tsv, delimiter='\t', doublequote=True, lineterminator='\n')

        cnt = 0
        for row in tsv_file:
            cnt = cnt + 1
            for line in row[3].split('\n'):
                # 「内容」項目を形態素解析
                morphological_analysis = analysis_mecab(line)

                appear_date = row[1]
                body_temperature = 0.0
                cough = False
                for word_info in morphological_analysis:
                    normalization_word = word_info.split('\t')[1]
                    # 日付抽出
                    result_date = get_date(normalization_word, row[1])
                    if result_date is not None:
                        appear_date = str(result_date)

                    # 熱判定
                    body_temperature = get_body_temperature(normalization_word, appear_date)
                    if body_temperature is not None:
                        print('CNT: ' + str(cnt) + '\t熱情報: ' + json.dumps(body_temperature) + '\t記入日: ' + row[1])

                    # TODO 咳判定


if __name__ == '__main__':
    main()
