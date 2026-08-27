"""공통 유틸 — 모일 곳 데이터 수집"""
import json, os, pathlib, urllib.request, urllib.error

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "out"
RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)

def get(url, referer=None, timeout=40):
    """공공 API는 UA 없으면 WAF에 막히는 곳이 있어 항상 붙인다."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def get_json(url, referer=None, timeout=40):
    return json.loads(get(url, referer, timeout).decode("utf-8"))

def save(obj, name, where=OUT):
    p = where / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장 → {p.relative_to(ROOT)}")
    return p

def need_key(env, how):
    k = os.environ.get(env)
    if not k:
        raise SystemExit(f"환경변수 {env} 가 없습니다.\n  발급: {how}\n  실행: {env}=발급받은키 python3 {os.path.basename(__import__('sys').argv[0])}")
    return k
