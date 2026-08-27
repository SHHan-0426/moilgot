# 모일 곳 (moilgot)

무료·실비 공간을 조건으로 좁혀 찾아주는 검색 사이트. 대상은 소모임·단체 운영자.

- 기획안: `docs/기획안-v1.1.html` (아티팩트: https://claude.ai/code/artifact/1dfc1873-025a-4b17-8d44-e1191e49ebcb)
- Phase 0 실사 결과: `docs/phase0-결과.md`

## 현재 상태 (2026.8.27)

**Phase 1 검색 화면 동작 중.** `site/index.html` — 서울 **513곳**(무료 304 · 실비 209),
그중 **100곳**은 예약 링크가 붙는 B층이다.

로컬에서 보기:
```bash
python3 -m http.server 8788 --directory site
```

### Phase 0 결론
- 서울 예약 API 1,288건 중 무료 256 → 모임용 실내 122 → 접수중 99. 구로·마포·서초 3개 구가 61% 편중
- 수도권 표준데이터 무료+실비 1,378건 (서울 425 / 경기 740 / 인천 213)
- **날짜 단위 빈자리 필드는 어느 소스에도 없다** → A층 제외
- B층이 얇아 **C층(시설정보+전화)이 사이트의 본체**
- 체육시설 포함 결정(8.27): 서울 +11건, 경기 +329, 인천 +124 → Phase 2에서 효과가 크다

## 수집기

```bash
python3 tools/collect_gyeonggi.py            # 키 불필요
python3 tools/collect_incheon.py             # 키 불필요 (스크래핑)
SEOUL_KEY=<키> python3 tools/collect_seoul.py
DATA_KEY=<키>  python3 tools/collect_standard.py
```

### 인증키 발급 (운영자만 가능)

| 환경변수 | 발급처 | 용도 |
|---|---|---|
| `SEOUL_KEY` | data.seoul.go.kr 로그인 → 인증키 신청 | 서울 1,288건 전량 + 무료 비율 확정 |
| `DATA_KEY` | data.go.kr → 15013117 활용신청 | 전국 표준데이터 → 수도권 무료·실비 건수 |

## 데이터 파이프라인

```
collect_seoul.py     서울 공공서비스예약 전량      → data/out/seoul_raw.json
collect_standard.py  전국 표준데이터 전량          → data/out/standard_all.json
        ↓
build_dataset.py     서울만 병합·정규화·중복제거   → data/out/seoul_spaces.json
        ↓
site/data/seoul_spaces.json  (사이트가 그대로 읽음)
```

## 주의

- `openapi.gg.go.kr`는 User-Agent 없으면 WAF가 차단한다. `tools/common.py`가 항상 붙인다.
- 표준데이터 `rntfee`는 자유 텍스트다(`평일:66000+주말:85800`, `10,000원`). `tools/fees.py`가 처리하며
  대표값은 **최저가**이고 원문을 화면에 함께 보여준다.
- 서울 예약 API에는 서울 밖 산하 시설(남양주·고양)과 공간이 아닌 서비스(수송버스 등)가 섞여 있다.
  `build_dataset.py`가 자치구 화이트리스트와 키워드로 거른다.

## 다음 할 일

- [ ] 수집 자동화 (GitHub Actions 일 1회 → JSON 커밋)
- [ ] 지역 랜딩 페이지 자동 생성 (`/노원구/무료-회의실`)
- [ ] 정보 오류 신고 버튼
- [ ] Phase 2 — 경기·인천 확대 (체육시설 포함 시 +453건)
- [ ] 배포 (Netlify)
