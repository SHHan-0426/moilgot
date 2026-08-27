"""전국공공시설개방정보표준데이터 수집 → 수도권 필터 → 무료/실비 집계.

  DATA_KEY='<일반 인증키>' python3 tools/collect_standard.py

Encoding / Decoding 어느 쪽을 넣어도 된다. 스크립트가 두 형태를 다 시도해 되는 쪽을 쓴다.

엔드포인트(공공데이터포털 상세페이지에서 확인):
  https://api.data.go.kr/openapi/tn_pubr_public_pblfclt_opn_info_api
  개발단계·운영단계 모두 자동승인 / 개발계정 트래픽 10,000 / numOfRows 최대 1000
지역 필터 파라미터가 없어 전량을 받아 주소로 거른다.
"""
import collections, os, urllib.parse
from common import get_json, save

URL = "https://api.data.go.kr/openapi/tn_pubr_public_pblfclt_opn_info_api"
CAPITAL = ("서울", "경기", "인천")
PER = 1000

# 인증키를 Encoding/Decoding 중 어느 쪽으로 받았든 그냥 되게 한다.
# 포털 화면이 '일반 인증키' 하나만 보여주는 경우도 있어 형태를 따지지 않는다.
_MODE = {"v": None}   # None=미정, "quote"=원본키(인코딩 필요), "raw"=이미 인코딩된 키

def _url(key, page, rows, mode):
    rest = f"pageNo={page}&numOfRows={rows}&type=json"
    sk = urllib.parse.quote(key, safe="") if mode == "quote" else key
    return f"{URL}?serviceKey={sk}&{rest}"

def _looks_auth_error(d):
    s = str(d)
    return any(w in s for w in (
        "SERVICE_KEY_IS_NOT_REGISTERED", "인증키", "SERVICE ERROR",
        "APPLICATION_ERROR", "UNREGISTERED", "LIMITED_NUMBER"))

def call(key, page, rows=PER):
    modes = [_MODE["v"]] if _MODE["v"] else ["quote", "raw"]
    last = None
    for m in modes:
        try:
            d = get_json(_url(key, page, rows, m))
        except Exception as e:
            last = e
            continue
        if _looks_auth_error(d) and _MODE["v"] is None:
            last = RuntimeError(str(d)[:200])
            continue
        if _MODE["v"] is None:
            _MODE["v"] = m
            print(f"  인증키 형태: {'원본(Decoding)' if m == 'quote' else '인코딩됨(Encoding)'} 로 인식")
        return d
    raise SystemExit(
        "인증키가 거부됐습니다. 두 형태 모두 시도했습니다.\n"
        "  · 활용신청이 '승인' 상태인지 확인하세요 (자동승인이지만 반영에 몇 분 걸릴 수 있습니다)\n"
        "  · 키 앞뒤 공백이나 줄바꿈이 섞이지 않았는지 확인하세요\n"
        f"  · 마지막 응답: {last}")

def unwrap(d):
    """응답 껍데기가 버전마다 조금씩 달라 방어적으로 벗긴다."""
    body = d.get("response", {}).get("body", d.get("body", d))
    items = body.get("items", [])
    if isinstance(items, dict):
        items = items.get("item", [])
    total = int(body.get("totalCount", 0) or 0)
    return total, (items if isinstance(items, list) else [items])

def addr(r):
    return str(r.get("rdnmadr") or r.get("lnmadr") or "").strip()

def won(s):
    d = "".join(c for c in str(s or "") if c.isdigit())
    return int(d) if d else None

def classify(r):
    """무료 / 실비(1만원 이하) / 유료 로 나눈다."""
    paid = str(r.get("pchrgUseYn") or "").strip().upper()
    fee = won(r.get("rntfee"))
    if paid in ("N", "무료") or fee == 0:
        return "무료"
    if fee is not None and fee <= 10000:
        return "실비"
    return "유료" if (paid in ("Y", "유료") or fee) else "미상"

def main():
    key = os.environ.get("DATA_KEY")
    if not key:
        raise SystemExit(__doc__)
    total, first = unwrap(call(key, 1))
    if not total:
        raise SystemExit("총건수 0 — 활용신청 승인 여부를 확인하세요.")
    print(f"  전국 총 {total:,}건 수집 시작")
    rows = list(first)
    page = 2
    while len(rows) < total:
        _, got = unwrap(call(key, page))
        if not got:
            break
        rows += got
        print(f"    {len(rows):,}/{total:,}")
        page += 1
    save(rows, "standard_all.json")

    cap = [r for r in rows if addr(r).startswith(CAPITAL)]
    buckets = collections.Counter(classify(r) for r in cap)
    sido = collections.Counter(addr(r).split()[0] for r in cap if addr(r))
    target = [r for r in cap if classify(r) in ("무료", "실비")]
    sigungu = collections.Counter(
        " ".join(addr(r).split()[:2]) for r in target if len(addr(r).split()) > 1)
    filled = lambda f: sum(1 for r in target if str(r.get(f) or "").strip())

    print(f"\n  === 결과 ===")
    print(f"  전국 {len(rows):,} / 수도권 {len(cap):,}  {dict(sido)}")
    print(f"  수도권 요금 분포: {dict(buckets)}")
    print(f"  무료+실비 = {len(target):,}건")
    for f in ("latitude", "aceptncPosblCo", "phoneNumber", "weekdayOperOpenHhmm"):
        print(f"    채워짐 {f:22} {filled(f):,}/{len(target):,}")
    print(f"  시군구 상위: {sigungu.most_common(12)}")
    gate = "통과" if len(target) >= 1500 else "미달 — 서울 단독으로 시작"
    print(f"\n  판단 게이트(1,500건): {gate}")

    save({"전국": len(rows), "수도권": len(cap), "시도분포": dict(sido),
          "요금분포": dict(buckets), "무료실비": len(target),
          "시군구": dict(sigungu), "게이트": gate}, "standard_summary.json")
    save(target, "capital_free_cheap.json")

if __name__ == "__main__":
    main()
