# 모일 곳 (moilgot)

무료·실비 공간을 조건으로 좁혀 찾아주는 검색 사이트. 대상은 소모임·단체 운영자.

- 기획안: `docs/기획안-v1.1.html` (아티팩트: https://claude.ai/code/artifact/1dfc1873-025a-4b17-8d44-e1191e49ebcb)
- Phase 0 실사 결과: `docs/phase0-결과.md`

## 현재 상태 (2026.8.27)

Phase 0 데이터 실사 완료. **서울 단독으로 시작하는 것으로 결론.**
경기 API는 49건·2년 미갱신·요금 필드 없음. 인천은 통합기관 7곳.
날짜 단위 빈자리 필드는 어느 소스에도 없어 A층은 v1에서 제외.

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

## 주의

`openapi.gg.go.kr`는 User-Agent 없으면 WAF가 차단한다. `tools/common.py`가 항상 붙인다.
