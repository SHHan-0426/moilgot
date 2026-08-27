"""전국공공시설개방정보표준데이터 수집 → 수도권 필터 → 무료/실비 집계.

  DATA_KEY=<공공데이터포털 일반 인증키(Decoding)> python3 tools/collect_standard.py

발급: https://www.data.go.kr 로그인 → '전국공공시설개방정보표준데이터'(15013117) 활용신청
      → 마이페이지에서 일반 인증키 확인 (자동승인, 보통 즉시)
"""
import collections, os, sys, urllib.parse
from common import get_json, save

# standard.do 페이지에서 추출한 uddi 후보들. 실제 유효한 것 하나를 찾아 쓴다.
UDDIS = [
    "2a35c6a2-c4c4-425a-aedd-f493773c10c5",
    "3b66c4a4-7b4e-4ee5-a27c-d6eaeaff6e61",
    "688eb213-6dfd-4081-b45c-b652ced5b3c7",
    "6c97d303-954e-446f-8f5d-c23ee3e69026",
    "b39f467b-e557-40dd-90bc-e467292fa031",
    "e10af8b9-4d76-4ff1-acb7-b198ed84f5cf",
    "ec5daebb-05fd-4321-be81-fb29a3cf5c65",
]
BASE = "https://api.odcloud.kr/api/15013117/v1/uddi:{}"
CAPITAL = ("서울", "경기", "인천")

def call(uddi, key, page, per):
    q = urllib.parse.urlencode({"page": page, "perPage": per, "serviceKey": key})
    return get_json(BASE.format(uddi) + "?" + q)

def find_uddi(key):
    for u in UDDIS:
        try:
            d = call(u, key, 1, 1)
            if d.get("totalCount", 0) > 0:
                print(f"  유효 uddi: {u} (총 {d['totalCount']:,}건)")
                return u, d["totalCount"]
        except Exception as e:
            continue
    raise SystemExit("유효한 uddi 를 찾지 못했습니다. data.go.kr 상세페이지에서 확인 후 UDDIS 에 추가하세요.")

def addr_of(r):
    for k in r:
        if "도로명주소" in k or "지번주소" in k or k.endswith("주소"):
            v = r.get(k)
            if v:
                return str(v)
    return ""

def fee_of(r):
    paid = next((r[k] for k in r if "유료사용여부" in k), "")
    fee = next((r[k] for k in r if k.endswith("사용료") or k == "사용료"), "")
    return str(paid).strip(), str(fee).strip()

def to_won(s):
    digits = "".join(ch for ch in str(s) if ch.isdigit())
    return int(digits) if digits else None

def main():
    key = os.environ.get("DATA_KEY")
    if not key:
        raise SystemExit(__doc__)
    uddi, total = find_uddi(key)
    rows, page, per = [], 1, 1000
    while len(rows) < total:
        d = call(uddi, key, page, per)
        got = d.get("data", [])
        if not got:
            break
        rows += got
        print(f"    {len(rows):,}/{total:,}")
        page += 1
    save(rows, "standard_all.json")

    cap = [r for r in rows if addr_of(r).startswith(CAPITAL)]
    free, cheap = [], []
    for r in cap:
        paid, fee = fee_of(r)
        won = to_won(fee)
        if paid.startswith("무료") or won == 0:
            free.append(r)
        elif won is not None and won <= 10000:
            cheap.append(r)
    sido = collections.Counter(addr_of(r).split()[0] for r in cap)
    print(f"\n  === 결과 ===")
    print(f"  전국 {len(rows):,}건 / 수도권 {len(cap):,}건 {dict(sido)}")
    print(f"  수도권 무료 {len(free):,}건 · 실비(1만원 이하) {len(cheap):,}건")
    print(f"  → 판단 게이트(1,500건): {'통과' if len(free)+len(cheap) >= 1500 else '미달 — 범위 축소 검토'}")
    save({"전국": len(rows), "수도권": len(cap), "시도분포": dict(sido),
          "무료": len(free), "실비": len(cheap)}, "standard_summary.json")
    save(free + cheap, "capital_free_cheap.json")

if __name__ == "__main__":
    main()
