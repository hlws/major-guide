# -*- coding: utf-8 -*-
import os, sys, ssl, urllib.request, tempfile
from pypdf import PdfReader

URLS = {
    "benke": "https://www.gov.cn/zhengce/zhengceku/202403/P020240319510440670420.pdf",
    "zhuanke": "http://zwfw.hrss.yn.gov.cn/Uploads/NewsPhoto/2026-01-23/c6564d02-d2ab-4ed3-a046-2b7290ec8fcb.pdf",
    "yanjiusheng": "http://www.moe.gov.cn/srcsite/a22/moe_833/202209/w020220914572994461110.pdf",
}

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE, exist_ok=True)

def download(key, url):
    pdf_path = os.path.join(CACHE, key + ".pdf")
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 10000:
        return pdf_path
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "*/*",
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(pdf_path, "wb") as f:
            f.write(r.read())
    except Exception:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r, open(pdf_path, "wb") as f:
            f.write(r.read())
    return pdf_path

def extract(key, url):
    pdf_path = download(key, url)
    txt_path = os.path.join(CACHE, key + ".txt")
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception as e:
            pages.append("")
    text = "\n".join(pages)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(key, "pages:", len(reader.pages), "chars:", len(text), "->", txt_path)
    return text

if __name__ == "__main__":
    for k, u in URLS.items():
        try:
            t = extract(k, u)
            print("=" * 20, k, "sample", "=" * 20)
            print(t[:1200].replace("\n", " | "))
        except Exception as e:
            print("FAIL", k, repr(e))
