""" 解析前に持っていたデータを作業前クレンジングするための処理ファイル
[前提]
- カルテデータはexcelで送付されました(=SJIS)
[ゴール]
- UT8
- TSV
- 改行コード LF
- ヘッダーなし
- インデックスなし
"""
from __future__ import unicode_literals
import re
import unicodedata
from pathlib import Path
import pandas as pd


def unicode_normalize(cls, s):
    """Neologd プレ処理"""
    pt = re.compile('([{}]+)'.format(cls))

    def norm(c):
        return unicodedata.normalize('NFKC', c) if pt.match(c) else c

    s = ''.join(norm(x) for x in re.split(pt, s))
    s = re.sub('－', '-', s)
    return s


def remove_extra_spaces(s):
    """Neologd プレ処理"""
    s = re.sub('[ 　]+', ' ', s)
    blocks = ''.join(('\u4E00-\u9FFF',  # CJK UNIFIED IDEOGRAPHS
                      '\u3040-\u309F',  # HIRAGANA
                      '\u30A0-\u30FF',  # KATAKANA
                      '\u3000-\u303F',  # CJK SYMBOLS AND PUNCTUATION
                      '\uFF00-\uFFEF'   # HALFWIDTH AND FULLWIDTH FORMS
                      ))
    basic_latin = '\u0000-\u007F'

    def remove_space_between(cls1, cls2, s):
        """Neologd プレ処理"""
        p = re.compile('([{}]) ([{}])'.format(cls1, cls2))
        while p.search(s):
            s = p.sub(r'\1\2', s)
        return s

    s = remove_space_between(blocks, blocks, s)
    s = remove_space_between(blocks, basic_latin, s)
    s = remove_space_between(basic_latin, blocks, s)
    return s


def normalize_neologd(s):
    """Neologd プレ処理"""
    s = s.strip()
    s = unicode_normalize('０-９Ａ-Ｚａ-ｚ｡-ﾟ', s)

    def maketrans(f, t):
        return {ord(x): ord(y) for x, y in zip(f, t)}

    s = re.sub('[˗֊‐‑‒–⁃⁻₋−]+', '-', s)  # normalize hyphens
    s = re.sub('[﹣－ｰ—―─━ー]+', 'ー', s)  # normalize choonpus
    s = re.sub('[~∼∾〜〰～]', '', s)  # remove tildes
    s = s.translate(
        maketrans('!"#$%&\'()*+,-./:;<=>?@[¥]^_`{|}~｡､･｢｣',
              '！”＃＄％＆’（）＊＋，－．／：；＜＝＞？＠［￥］＾＿｀｛｜｝〜。、・「」'))

    s = remove_extra_spaces(s)
    s = unicode_normalize('！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝〜', s)  # keep ＝,・,「,」
    s = re.sub('[’]', '\'', s)
    s = re.sub('[”]', '"', s)
    return s


# 作業前ファイル
source_file = Path.cwd().joinpath('202001.xlsx')
# 吐き出しファイル
result_file = Path.cwd().joinpath('cleansing-completed.tsv')

# Excelファイルの読み込み
df = pd.read_excel(source_file, engine='openpyxl')
# 改行コードの修正
change_indention = df.replace('_x000D_', '', regex=True)

# neologd 前処理
with open(result_file, mode='w', encoding='utf8') as f:
    for column_name, row in change_indention.iterrows():
        if row['タイトル'] == '診療録':
            # 診療録のみを抽出し、内容カラムにneologd前処理をかける
            exclude_space = remove_extra_spaces(row['内容'])
            normalize_detail = normalize_neologd(exclude_space)

            # TSV書き込み
            write_data = [row['患者番号'], str(row['登録日時']), row['タイトル'], '"' + normalize_detail + '"']
            f.writelines('\t'.join(write_data) + '\n')

        else:
            print(row['タイトル'] + ' skip')
