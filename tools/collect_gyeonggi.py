"""경기공유서비스_시설대관(TBGSSFACILITY) 수집.

인증키 없이 호출되지만 sample 모드는 5건 제한이다.
GG_KEY 를 주면 전량(총 49건) 수집한다.
발급: https://data.gg.go.kr 회원가입 → 인증키 신청
"""
import collections, os
from common import get_json, save

URL = "https://openapi.gg.go.kr/TBGSSFACILITY"
REF = "https://data.gg.go.kr/"

def fetch(key, idx, size):
    q = f"?Type=json&pIndex={idx}&pSize={size}" + (f"&KEY={key}" if key else "")
    d = get_json(URL + q, referer=REF)
    blk = d["TBGSSFACILITY"]
    return int(blk[0]["head"][0]["list_total_count"]), blk[1].get("row", [])

def main():
    key = os.environ.get("GG_KEY")
    total, _ = fetch(key, 1, 5)
    print(f"  총건수 {total}건" + ("" if key else "  (키 없음 → 5건만 수집)"))
    rows, size = [], (100 if key else 5)
    idx = 1
    while len(rows) < total:
        _, batch = fetch(key, idx, size)
        if not batch:
            break
        rows += batch
        idx += 1
        if not key:
            break
    print(f"  수집 {len(rows)}건")
    print("  ! 이 API에는 사용료(무료/유료) 필드가 없다 — 무료 판별 불가")
    if rows:
        print("  용도:", collections.Counter(r.get("PURPOS") for r in rows).most_common(6))
        print("  예약방법:", collections.Counter(r.get("RSVTN_METH") for r in rows).most_common(6))
    save({"총건수": total, "수집": len(rows), "rows": rows}, "gyeonggi_facility.json")

if __name__ == "__main__":
    main()
