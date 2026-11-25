# -*- coding: utf-8 -*-
"""解析三份官方专业目录 PDF 文本，输出 catalog.json"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "cache")
DATA_DIR = os.path.join(ROOT, "data")

MENLEI = {
    "01": "哲学", "02": "经济学", "03": "法学", "04": "教育学", "05": "文学",
    "06": "历史学", "07": "理学", "08": "工学", "09": "农学", "10": "医学",
    "11": "军事学", "12": "管理学", "13": "艺术学", "14": "交叉学科",
}

CODE_RE = re.compile(r"^\d{4,8}[TK]*$")
NUM_RE = re.compile(r"^\d{1,3}$")


def normalize_degree(parts):
    """PDF 列宽换行会把“经济学”拆成“经”“济学”，这里合并单字碎片。"""
    tokens = [t for t in re.split(r"[,，]", ",".join(parts)) if t]
    out = []
    buf = ""
    for t in tokens:
        t = buf + t
        buf = ""
        if len(t) <= 2 and not t.endswith("学"):
            buf = t
            continue
        out.append(t)
    if buf:
        out.append(buf)
    return ",".join(out)


def parse_benke(path):
    lines = [l.strip() for l in open(path, encoding="utf-8")]
    rows = []
    n = len(lines)
    for i in range(n - 3):
        if not NUM_RE.match(lines[i]):
            continue
        cat, code, name = lines[i + 1], lines[i + 2], lines[i + 3]
        if not (cat.endswith("类") and CODE_RE.match(code) and name):
            continue
        if not re.match(r"^\d{6,7}[TK]*$", code):
            continue
        if name in ("专业名称", "门类、专业类"):
            continue
        # 学位授予门类：从 name 之后收集，直到出现 四年/五年
        degree_parts, duration = [], ""
        for j in range(i + 4, min(i + 12, n)):
            t = lines[j]
            if t in ("四年", "五年"):
                duration = t
                break
            if re.match(r"^(四年|五年),", t):
                duration = "四年" if t.startswith("四年") else "五年"
                break
            if re.match(r"^\d{4}$", t) or NUM_RE.match(t) or t.endswith("类"):
                break
            degree_parts.append(t)
        degree = normalize_degree(degree_parts)
        rows.append({
            "门类": MENLEI.get(code[:2], ""),
            "专业类": cat,
            "code": code,
            "name": name,
            "degree": degree,
            "duration": duration or "四年",
        })
    return rows


def parse_zhuanke(path):
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    rows = []
    big, small = "", ""
    for l in lines:
        m = re.match(r"^(\d{2})([^\d].+大类)$", l)
        if m:
            big = m.group(2)
            continue
        m = re.match(r"^(\d{4})([^\d].+类)$", l)
        if m:
            small = m.group(2)
            continue
        m = re.match(r"^(\d{1,3})\s+(\d{6}[TK]?)\s+(.+)$", l)
        if m:
            rows.append({"大类": big, "专业类": small, "code": m.group(2), "name": m.group(3).strip()})
    return rows


def parse_yanjiusheng(path):
    raw = [l.strip() for l in open(path, encoding="utf-8") if l.strip()]
    # 合并被换行截断的括号内容
    lines = []
    buf = ""
    for l in raw:
        if buf:
            buf += l
            if "）" in l:
                lines.append(buf)
                buf = ""
            continue
        if "（" in l and "）" not in l:
            buf = l
            continue
        lines.append(l)
    if buf:
        lines.append(buf)

    starts = False
    rows = []
    men = ""
    for l in lines:
        if l == "01 哲学":
            starts = True
        if not starts:
            continue
        m = re.match(r"^(\d{2})\s+(\S+)$", l)
        if m and m.group(1) in MENLEI:
            men = MENLEI[m.group(1)]
            continue
        m = re.match(r"^(\d{4})\s+(.+)$", l)
        if m and men:
            code, rest = m.group(1), m.group(2).strip()
            only_master = rest.endswith("*")
            rest_clean = rest.rstrip("*").strip()
            note = ""
            mm = re.match(r"^(.+?)（(.+)）$", rest_clean)
            if mm:
                base, note = mm.group(1).strip(), mm.group(2).strip()
            else:
                base = rest_clean
            rows.append({
                "门类": men,
                "code": code,
                "name": base,
                "kind": "专业学位类别" if code[2] in ("5", "6") else "一级学科",
                "note": note,
                "only_master": only_master,
            })
    # 目录中以“同时设专业学位类别”形式出现的类别，补充为独立记录
    extra = [
        {"门类": "医学", "code": "1051", "name": "临床医学", "kind": "专业学位类别",
         "note": "与一级学科临床医学同时设置", "only_master": False},
        {"门类": "医学", "code": "1052", "name": "口腔医学", "kind": "专业学位类别",
         "note": "与一级学科口腔医学同时设置", "only_master": False},
        {"门类": "医学", "code": "1055", "name": "药学", "kind": "专业学位类别",
         "note": "与一级学科药学同时设置", "only_master": False},
    ]
    for e in extra:
        if not any(r["code"] == e["code"] for r in rows):
            rows.append(e)
    return rows


def main():
    benke = parse_benke(os.path.join(CACHE, "benke.txt"))
    zhuanke = parse_zhuanke(os.path.join(CACHE, "zhuanke.txt"))
    yjs = parse_yanjiusheng(os.path.join(CACHE, "yanjiusheng.txt"))

    # 去重（同名同代码只留一条）
    def dedup(rows):
        seen, out = set(), []
        for r in rows:
            k = (r.get("专业类") or r.get("大类"), r["code"], r["name"])
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return out

    benke, zhuanke, yjs = dedup(benke), dedup(zhuanke), dedup(yjs)

    print("本科:", len(benke), "专业；专业类:", len({r['专业类'] for r in benke}),
          "；门类:", sorted({r['门类'] for r in benke}))
    print("专科:", len(zhuanke), "专业；大类:", len({r['大类'] for r in zhuanke}),
          "；专业类:", len({r['专业类'] for r in zhuanke}))
    print("研究生 一级学科:", len([r for r in yjs if r['kind'] == '一级学科']),
          "专业学位类别:", len([r for r in yjs if r['kind'] == '专业学位类别']),
          "仅硕士:", len([r for r in yjs if r['only_master']]))
    print("本科样例:", benke[:2], benke[-2:])
    print("专科样例:", zhuanke[:2], zhuanke[-2:])
    print("研究生样例:", yjs[:3], yjs[-3:])

    data = {
        "本科": benke,
        "大专": zhuanke,
        "硕士": yjs,
        "博士": [r for r in yjs if not r["only_master"]],
    }
    out = os.path.join(DATA_DIR, "catalog.json")
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()
