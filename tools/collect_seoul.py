"""서울 공공서비스예약 전량 수집 + 무료/유료·자치구 집계.

  SEOUL_KEY=<인증키> python3 tools/collect_seoul.py

인증키 발급(무료·즉시): https://data.seoul.go.kr 로그인 → 인증키 신청
키가 없으면 sample 키로 5건만 받아 필드 점검만 한다.
"""
import collections, sys
from common import get_json, save, OUT
import os

BASE = "http://openapi.seoul.go.kr:8088"
SERVICES = {
    "ListPublicReservationInstitution": "시설대관",
    "ListPublicReservationSport": "체육시설",
    "ListPublicReservationEducation": "교육",
    "ListPublicReservationCulture": "문화행사",
    "ListPublicReservationMedical": "진료",
}
# 공간을 빌리는 것과 직접 관련된 서비스
SPACE_SERVICES = ["ListPublicReservationInstitution", "ListPublicReservationSport"]

def fetch(key, svc, start, end):
    d = get_json(f"{BASE}/{key}/json/{svc}/{start}/{end}/")
    return d[svc]

def fetch_all(key, svc):
    first = fetch(key, svc, 1, 1)
    total = int(first["list_total_count"])
    rows, step = [], (5 if key == "sample" else 1000)
    for s in range(1, total + 1, step):
        e = min(s + step - 1, total)
        try:
            rows += fetch(key, svc, s, e).get("row", [])
        except Exception as ex:
            print(f"    ! {svc} {s}-{e} 실패: {ex}")
            break
        if key == "sample":
            break
    return total, rows

def is_free(pay):
    p = (pay or "").strip()
    return p.startswith("무료")

def main():
    key = os.environ.get("SEOUL_KEY", "sample")
    if key == "sample":
        print("! SEOUL_KEY 없음 → sample 키(5건 제한)로 필드 점검만 수행\n")
    allrows, summary = {}, {}
    for svc, label in SERVICES.items():
        total, rows = fetch_all(key, svc)
        allrows[svc] = rows
        summary[svc] = {"라벨": label, "총건수": total, "수집": len(rows)}
        print(f"  {label:8} 총 {total:5}건 · 수집 {len(rows):5}건")

    space = [r for s in SPACE_SERVICES for r in allrows.get(s, [])]
    if space:
        free = [r for r in space if is_free(r.get("PAYATNM"))]
        gu = collections.Counter(r.get("AREANM", "?") for r in free)
        st = collections.Counter(r.get("SVCSTATNM", "?") for r in space)
        print(f"\n  === 공간대관(시설대관+체육시설) {len(space)}건 ===")
        print(f"  무료 {len(free)}건 ({len(free)*100//max(1,len(space))}%)")
        print(f"  상태 분포: {dict(st)}")
        print(f"  무료 상위 자치구: {gu.most_common(10)}")
        summary["공간대관"] = {
            "합계": len(space), "무료": len(free),
            "상태분포": dict(st), "무료_자치구": dict(gu),
        }
    save(allrows, "seoul_raw.json")
    save(summary, "seoul_summary.json")

if __name__ == "__main__":
    main()
