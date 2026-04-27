import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.auth import HTTPBasicAuth

MAX_PAGES = 30
TIMEOUT = 5

EXCLUDE_EXT = (
    ".jpg",".jpeg",".png",".gif",".svg",".webp",
    ".pdf",".zip",".rar",".mp4",".mp3",".css",".js",".ico"
)

# ==============================
# スラッシュ制御（AST対応）
# ==============================
def add_slash(url, mode):
    if mode == "AST":
        parsed = urlparse(url)
        last = parsed.path.split("/")[-1]

        # ファイルは除外
        if "." not in last:
            if not url.endswith("/"):
                return url + "/"
    return url


# ==============================
# 外部リンク判定
# ==============================
def is_external(url, base_domain):
    return urlparse(url).netloc != base_domain


# ==============================
# メイン処理
# ==============================
def run_analysis(start_url, username=None, password=None, mode="IPP"):

    visited = set()
    queue = [start_url]
    base_domain = urlparse(start_url).netloc

    results = []

    session = requests.Session()

    if username and password:
        session.auth = HTTPBasicAuth(username, password)

    while queue and len(visited) < MAX_PAGES:

        url = queue.pop(0)

        if url in visited:
            continue

        visited.add(url)

        try:
            res = session.get(url, timeout=TIMEOUT)
        except:
            continue

        if "text/html" not in res.headers.get("Content-Type", ""):
            continue

        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # ==========================
        # 表記ゆれ検出
        # ==========================
        for m in re.finditer(r"[Ａ-Ｚａ-ｚ０-９]+", text):
            results.append({
                "page": url,
                "type": "text_issue",
                "detail": m.group()
            })

        for m in re.finditer(r"[ｦ-ﾟ]+", text):
            results.append({
                "page": url,
                "type": "text_issue",
                "detail": m.group()
            })

        if "\u3000" in text:
            results.append({
                "page": url,
                "type": "text_issue",
                "detail": "全角スペースあり"
            })

        # ==========================
        # リンク処理
        # ==========================
        for a in soup.find_all("a", href=True):

            href = a.get("href")

            if not href:
                continue

            if href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue

            full = urljoin(url, href)

            if any(full.lower().endswith(ext) for ext in EXCLUDE_EXT):
                continue

            # AST対応
            full = add_slash(full, mode)

            # ==========================
            # クロール追加（内部リンク）
            # ==========================
            if urlparse(full).netloc == base_domain:
                if full not in visited:
                    queue.append(full)

            # ==========================
            # _blankチェック
            # ==========================
            if is_external(full, base_domain):
                if a.get("target") != "_blank":
                    results.append({
                        "page": url,
                        "type": "external_blank_missing",
                        "detail": full
                    })

            # ==========================
            # リンク切れチェック
            # ==========================
            try:
                r = session.head(full, timeout=TIMEOUT, allow_redirects=True)
                if r.status_code >= 400:
                    results.append({
                        "page": url,
                        "type": "broken_link",
                        "detail": full
                    })
            except:
                results.append({
                    "page": url,
                    "type": "broken_link",
                    "detail": full
                })

    return results