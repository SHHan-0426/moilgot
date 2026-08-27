"""전국공공시설개방정보표준데이터 수집 → 수도권 필터 → 무료/실비 집계.

  DATA_KEY='<일반 인증키 Decoding>' python3 tools/collect_standard.py

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

def call(key, page, rows=PER):
    q = urllib.parse.urlencode({
        "serviceKey": key, "pageNo": page, "numOfRows": rows, "type": "json"
    })
    return get_json(f"{URL}?{q}")

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
        raise SystemExit("총건수 0 — 인증키(Decoding 값)와 활용신청 승인 여부를 확인하세요.")
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
