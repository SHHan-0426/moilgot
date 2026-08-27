"""인천 온라인통합예약 대관/대여 목록 수집.

data.go.kr 의 '인천광역시_통합예약안내'는 API 유형이 LINK 라서 REST 명세가 없다.
그래서 서버 렌더링되는 목록 페이지를 직접 파싱한다.
주의: 통합회원 탭에 올라오는 기관만 잡힌다. 군·구와 공단은 각자 별도 시스템이다.
"""
import re, html
from common import get, save

LIST = "https://www.incheon.go.kr/res/RE020101"

def strip_tags(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s))

def parse(text):
    """'... 접수중 기관 X 장소 Y 일자 신청 A ~ B 운영 C ~ D 문의 T' 패턴을 뽑는다."""
    pat = re.compile(
        r"(?P<name>[^ ].{0,90}?)\s*(?P<status>접수중|접수마감|접수예정|접수종료)\s*"
        r"기관\s*(?P<org>.+?)\s*장소\s*(?P<place>.+?)\s*"
        r"일자\s*신청\s*(?P<rcpt>[\d\-: ]+~[\d\-: ]+)\s*"
        r"운영\s*(?P<oper>[\d\-]+\s*~\s*[\d\-]+)\s*"
        r"문의\s*(?P<tel>[\d\-]+)")
    return [m.groupdict() for m in pat.finditer(text)]

def main():
    raw = get(LIST).decode("utf-8", "replace")
    text = strip_tags(raw)
    items = parse(text)
    print(f"  1페이지에서 {len(items)}건 파싱")
    orgs = re.search(r"운영기관\s*전체\s*(.+?)\s*검색어", text)
    if orgs:
        print(f"  통합회원 운영기관: {orgs.group(1)}")
    print("  ! 목록에 사용료(무료/유료) 정보가 없다 — 상세 페이지나 전화 확인 필요")
    for it in items[:3]:
        print(f"    - [{it['status']}] {it['name'][:40]} / {it['org']} / 운영 {it['oper']}")
    save({"수집": len(items), "items": items}, "incheon_rent.json")

if __name__ == "__main__":
    main()
