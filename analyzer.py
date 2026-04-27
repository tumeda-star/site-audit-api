import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_PAGES = 30
TIMEOUT = 5
MAX_WORKERS = 10

EXCLUDE_EXT = (
    ".jpg",".jpeg",".png",".gif",".svg",".webp",
    ".pdf",".zip",".rar",".mp4",".mp3",".css",".js",".ico"
)

# ==============================
# URL正規化（重複防止）
# ==============================
def normalize(url):
    p = urlparse(url)
    path = p.path.rstrip("/")
    if path.endswith("index.html"):
        path = path[:-11]
    return f"{p.scheme}://{p.netloc}{path}"

# ==============================
# AST（スラッシュ制御）
# ==============================
def add_slash(url, mode):
    if mode == "AST":
        parsed = urlparse(url)
        last = parsed.path.split("/")[-1]
        if "." not in last and not url.endswith("/"):
            return url + "/"
    return url

# ==============================
# 外部リンク判定
# ==============================
def is_external(url, base_domain):
    return urlparse(url).netloc != base_domain

# ==============================
# 前後10文字付き
# ==============================
def extract_context(pattern, text):
    results = []
    for m in re.finditer(pattern, text):
        s = max(0, m.start()-10)
        e = m.end()+10
        results.append(text[s:e])
    return results

# ==============================
# 並列リンクチェック
# ==============================
def check_links(session, links):
    results = []

    def check(url):
        try:
            r = session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code >= 400:
                return url
        except:
            return url
        return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = [exe.submit(check, u) for u in links]
        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    return results

# ==============================
# メイン
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

        url = normalize(queue.pop(0))

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
        # 表記ゆれ（前後付き）
        # ==========================
        for t in extract_context(r"[Ａ-Ｚａ-ｚ０-９]+", text):
            results.append({"page": url, "type": "zenkaku_eisuji", "detail": t})

        for t in extract_context(r"[ｦ-ﾟ]+", text):
            results.append({"page": url, "type": "hankaku_katakana", "detail": t})

        for t in extract_context(r"\u3000", text):
            results.append({"page": url, "type": "zenkaku_space", "detail": t})

        # ==========================
        # リンク収集
        # ==========================
        links = []

        for a in soup.find_all("a", href=True):

            href = a.get("href")

            if href.startswith(("mailto:", "tel:", "#", "javascript:")):
                continue

            full = urljoin(url, href)
            full = add_slash(full, mode)

            if any(full.lower().endswith(ext) for ext in EXCLUDE_EXT):
                continue

            full = normalize(full)

            # 内部リンク
            if urlparse(full).netloc == base_domain:
                if full not in visited:
                    queue.append(full)

            # 外部_blankチェック
            if is_external(full, base_domain):
                if a.get("target") != "_blank":
                    results.append({
                        "page": url,
                        "type": "external_blank_missing",
                        "detail": full
                    })

            links.append(full)

        # ==========================
        # 並列リンクチェック
        # ==========================
        broken_links = check_links(session, links)

        for link in broken_links:
            results.append({
                "page": url,
                "type": "broken_link",
                "detail": link
            })

    return results
