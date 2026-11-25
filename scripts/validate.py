# -*- coding: utf-8 -*-
"""校验专业库目录结构与 Markdown 元信息，供本地与 GitHub Actions 使用。

用法：python scripts/validate.py
有任何 error 时退出码为 1。
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

LEVELS = ["大专", "本科", "硕士", "博士"]
REQUIRED_FILES = ["生存指南.md", "避坑指南.md"]
REQUIRED_KEYS = ["层次", "专业代码", "状态", "维护人", "最近更新", "依据"]
STATUS = {"初稿", "已校订", "待更新"}
BAD_CHARS = set('\\/:*?"<>|')
CODE_RE = re.compile(r"^\d{4,8}[TK]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

errors = []
warnings = []
stats = {}


def parse_front_matter(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    block = text[3:end].strip("\n")
    body = text[end + 4:]
    meta = {}
    for line in block.splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    return meta, body


def check_file(path, level, major):
    rel = os.path.relpath(path, ROOT)
    try:
        text = open(path, encoding="utf-8").read()
    except Exception as e:
        errors.append(f"{rel}: 读取失败 {e}")
        return
    meta, body = parse_front_matter(text)
    if meta is None:
        errors.append(f"{rel}: 缺少 YAML front matter")
        return
    for k in REQUIRED_KEYS:
        if k not in meta:
            errors.append(f"{rel}: 缺少字段 {k}")
    if meta.get("层次") and meta["层次"] != level:
        errors.append(f"{rel}: 层次={meta['层次']} 与所在目录 {level} 不一致")
    code = meta.get("专业代码", "")
    if code and not CODE_RE.match(code):
        errors.append(f"{rel}: 专业代码格式异常 {code}")
    if meta.get("状态") and meta["状态"] not in STATUS:
        errors.append(f"{rel}: 状态 {meta['状态']} 不在 {sorted(STATUS)} 内")
    if meta.get("最近更新") and not DATE_RE.match(meta["最近更新"]):
        errors.append(f"{rel}: 最近更新应为 YYYY-MM-DD")
    if not meta.get("维护人"):
        errors.append(f"{rel}: 维护人为空")
    if len(body.strip()) < 300:
        errors.append(f"{rel}: 正文过短（{len(body.strip())} 字），疑似空文件")


def main():
    total_major = 0
    for level in LEVELS:
        ldir = os.path.join(ROOT, level)
        if not os.path.isdir(ldir):
            errors.append(f"缺少一级目录：{level}")
            continue
        groups = [d for d in os.listdir(ldir) if os.path.isdir(os.path.join(ldir, d))]
        if not groups:
            errors.append(f"{level} 下没有大类目录")
            continue
        majors = 0
        for g in groups:
            gdir = os.path.join(ldir, g)
            if any(c in BAD_CHARS for c in g):
                errors.append(f"{level}/{g}: 目录名含非法字符")
            sub = [d for d in os.listdir(gdir) if os.path.isdir(os.path.join(gdir, d))]
            if not sub:
                warnings.append(f"{level}/{g}: 大类下没有专业目录")
            for m in sub:
                majors += 1
                mdir = os.path.join(gdir, m)
                if any(c in BAD_CHARS for c in m):
                    errors.append(f"{level}/{g}/{m}: 目录名含非法字符")
                if len(m) > 60:
                    warnings.append(f"{level}/{g}/{m}: 目录名超过 60 字")
                files = [f for f in os.listdir(mdir) if f.lower().endswith(".md")]
                for need in REQUIRED_FILES:
                    if need not in files:
                        errors.append(f"{level}/{g}/{m}: 缺少 {need}")
                extra = [f for f in files if f not in REQUIRED_FILES]
                if extra:
                    warnings.append(f"{level}/{g}/{m}: 额外文件 {', '.join(extra)}")
                for need in REQUIRED_FILES:
                    p = os.path.join(mdir, need)
                    if os.path.exists(p):
                        check_file(p, level, m)
        stats[level] = (len(groups), majors)
        total_major += majors

    print("目录统计：")
    for k in LEVELS:
        if k in stats:
            print(f"  {k}: {stats[k][0]} 个大类 / {stats[k][1]} 个专业目录")
    print(f"合计 {total_major} 个专业目录，{total_major * 2} 个 Markdown 文件")

    if warnings:
        print(f"\n警告 {len(warnings)} 条：")
        for w in warnings[:40]:
            print("  ! " + w)
    if errors:
        print(f"\n错误 {len(errors)} 条：")
        for e in errors[:60]:
            print("  x " + e)
        print("\n校验未通过")
        return 1
    print("\n校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
