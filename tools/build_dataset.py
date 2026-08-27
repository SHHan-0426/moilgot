"""서울 데이터셋 구축 — 표준데이터(C층) + 서울 예약 API(B층) 병합.

  python3 tools/build_dataset.py

입력  data/out/standard_all.json, data/out/seoul_raw.json
출력  data/out/seoul_spaces.json  (사이트가 그대로 읽는 형태)

체육시설 포함 방침(2026.8.27 결정)에 따라 실내·체육을 모두 담고 category 로 구분한다.
"""
import datetime, json, math, os, re, sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from fees import classify
from common import ROOT, OUT, save

SEOUL_GU = {
    '종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구',
    '노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구',
    '관악구','서초구','강남구','송파구','강동구',
}
# 서울 대략 경계 (밖에 있는 서울시 산하 시설을 걸러낸다)
SEOUL_BBOX = (37.41, 37.72, 126.76, 127.19)

# 공간 대관이 아닌 서비스가 예약 API에 섞여 있다 (수송버스, 물품 대여 등)
NOT_A_SPACE = re.compile(r'수송버스|셔틀|버스\s*예약|공구\s*대여|물품\s*대여|자전거\s*대여|'
                         r'주차|무인민원|증명서|상담\s*예약|검진|접종')

_TEL = re.compile(r'0\d{1,2}-\d{3,4}-\d{4}|\d{4}-\d{4}')

def tel_of(raw):
    """'장소,이용: 02-3780-0551/예약: 02-3780-0873' 같은 자유 텍스트에서 첫 번호를 뽑는다."""
    s = str(raw or '').strip()
    if not s: return None, None
    m = _TEL.search(s)
    return (m.group(0) if m else None), s

# 이름 앞뒤에 붙는 '(26.8월)' '(8월)' 같은 회차 표시를 떼어낸다
_MONTH = re.compile(r'^\s*\(\s*(?:\d{2}\s*\.)?\s*\d{1,2}\s*월[^)]*\)\s*|'
                    r'\s*\(\s*(?:\d{2}\s*\.)?\s*\d{1,2}\s*월[^)]*\)\s*$')

def clean_name(s):
    s = str(s or '')
    prev = None
    while prev != s:
        prev = s
        s = _MONTH.sub('', s).strip()
    return s

def in_seoul(lat, lng):
    a, b, c, d = SEOUL_BBOX
    return a <= lat <= b and c <= lng <= d

SPORT = re.compile(r'테니스|족구|배드민턴|배드맨턴|농구|축구|풋살|야구|게이트볼|수영|체육관|'
                   r'경기장|골프|탁구|헬스|운동장|스쿼시|볼링|당구|씨름|검도|국궁|양궁|롤러|빙상')
INDOOR = re.compile(r'회의실|다목적실|강의실|강당|세미나|교육장|모임|열람|동아리|공연장|전시|'
                    r'시청각|카페|주민공유|청년공간|프로그램실|문화교실|연습실|스튜디오')

def category(*texts):
    t = ' '.join(str(x or '') for x in texts)
    if INDOOR.search(t): return '실내'
    if SPORT.search(t):  return '체육'
    return '기타'

def num(v):
    d = re.sub(r'[^\d]', '', str(v or ''))
    return int(d) if d else None

def hhmm(v):
    s = str(v or '').strip()
    m = re.match(r'^(\d{1,2}):?(\d{2})$', s)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else None

def sigungu(addr):
    p = str(addr or '').split()
    if len(p) < 2: return None
    # '서울특별시 디지털로19길' 같은 파싱 이상치를 거른다
    return p[1] if re.search(r'(시|군|구)$', p[1]) else None

def dist_m(a, b):
    (la1, lo1), (la2, lo2) = a, b
    R = 6371000.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2-la1), math.radians(lo2-lo1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(min(1, math.sqrt(h)))

def norm_name(s):
    return re.sub(r'[\s()\[\]<>·,./\-]', '', str(s or '')).lower()

# ---------- 1) 표준데이터 (C층) ----------
def from_standard(rows):
    out = []
    for r in rows:
        addr = str(r.get('rdnmadr') or r.get('lnmadr') or '').strip()
        if not addr.startswith('서울'): continue
        gu = sigungu(addr)
        if gu and gu not in SEOUL_GU: continue
        kind, fee = classify(r.get('pchrgUseYn'), r.get('rntfee'))
        if kind not in ('무료', '실비'): continue
        try:
            lat, lng = float(r['latitude']), float(r['longitude'])
        except (TypeError, ValueError, KeyError):
            continue
        name = str(r.get('openFcltyNm') or '').strip()
        out.append({
            'name': name,
            'place': str(r.get('openLcNm') or '').strip() or None,
            'category': category(r.get('openFcltyType'), name),
            'fclty_type': str(r.get('openFcltyType') or '').strip() or None,
            'sigungu': gu, 'addr': addr, 'lat': lat, 'lng': lng,
            'fee_kind': kind, 'fee_min': fee,
            'fee_raw': str(r.get('rntfee') or '').strip() or None,
            'fee_std_hours': num(r.get('useStdrTime')),
            'fee_over_unit': num(r.get('excessUseUnitTime')),
            'fee_over': num(r.get('excessRntfee')),
            'capacity': num(r.get('aceptncPosblCo')),
            'area': str(r.get('ar') or '').strip() or None,
            'open': hhmm(r.get('weekdayOperOpenHhmm')),
            'close': hhmm(r.get('weekdayOperColseHhmm')),
            'closed_day': str(r.get('rstde') or '').strip() or None,
            'facilities': str(r.get('etcFclty') or '').strip() or None,
            'apply': str(r.get('sbscrptnMthSe') or '').strip() or None,
            'tel': tel_of(r.get('phoneNumber'))[0],
            'tel_label': tel_of(r.get('phoneNumber'))[1],
            'homepage': str(r.get('homepageUrl') or '').strip() or None,
            'org': str(r.get('institutionNm') or '').strip() or None,
            'tier': 'C', 'status': None, 'reserve_url': None, 'rcpt_end': None,
            'source': '표준데이터',
            'checked': str(r.get('referenceDate') or '').strip() or None,
        })
    return out

# ---------- 2) 서울 예약 API (B층) ----------
def from_seoul(rows):
    """같은 공간이 월별 서비스로 쪼개져 있어 (장소, 소분류)로 접는다."""
    free = [r for r in rows if str(r.get('PAYATNM', '')).strip().startswith('무료')]
    rank = {'접수중': 0, '안내중': 1, '예약일시중지': 2, '예약마감': 3, '접수종료': 4}
    groups = collections.defaultdict(list)
    for r in free:
        groups[(r.get('PLACENM'), r.get('MINCLASSNM'))].append(r)
    out = []
    for (place, cls_), items in groups.items():
        items.sort(key=lambda r: (rank.get(r.get('SVCSTATNM'), 9),
                                  -len(str(r.get('RCPTENDDT') or ''))))
        r = items[0]
        try:
            lat, lng = float(r['Y']), float(r['X'])
        except (TypeError, ValueError, KeyError):
            continue
        name = clean_name(r.get('SVCNM'))
        area = str(r.get('AREANM') or '').strip()
        # 서울시 API에는 산하 시설이라 서울 밖(남양주·고양 등)도 섞여 있다.
        # 자치구명이 서울 25개가 아니면 제외하고, 빈 값은 좌표로 판단한다.
        if area and area not in SEOUL_GU:
            continue
        if NOT_A_SPACE.search(name) or not in_seoul(lat, lng):
            continue
        out.append({
            'name': name, 'place': str(place or '').strip() or None,
            'category': category(cls_, name), 'fclty_type': cls_,
            'sigungu': area or None,
            'addr': None, 'lat': lat, 'lng': lng,
            'fee_kind': '무료', 'fee_min': 0, 'fee_raw': str(r.get('PAYATNM') or ''),
            'fee_std_hours': None, 'fee_over_unit': None, 'fee_over': None,
            'capacity': None, 'area': None,
            'open': hhmm(r.get('V_MIN')), 'close': hhmm(r.get('V_MAX')),
            'closed_day': None, 'facilities': None,
            'apply': '온라인 예약',
            'tel': tel_of(r.get('TELNO'))[0], 'tel_label': tel_of(r.get('TELNO'))[1],
            'homepage': None, 'org': str(place or '').strip() or None,
            'tier': 'B', 'status': r.get('SVCSTATNM'),
            'reserve_url': r.get('SVCURL'),
            'rcpt_end': str(r.get('RCPTENDDT') or '')[:10] or None,
            'variants': len(items),
            'source': '서울 공공서비스예약',
            'checked': None,
        })
    return out

# ---------- 3) 병합 ----------
def merge(cs, bs, radius_m=120):
    """좌표 120m 이내 + 이름/장소 토큰이 겹치면 같은 공간으로 본다."""
    merged, used = list(cs), set()
    for i, b in enumerate(bs):
        hit = None
        for c in merged:
            if dist_m((b['lat'], b['lng']), (c['lat'], c['lng'])) > radius_m:
                continue
            nb, nc = norm_name(b['name']), norm_name(c['name'])
            pb, pc = norm_name(b['place']), norm_name(c['place'])
            if nb and nc and (nb in nc or nc in nb): hit = c; break
            if pb and pc and (pb in pc or pc in pb): hit = c; break
            if pb and nc and (pb in nc or nc in pb): hit = c; break
        if hit:
            used.add(i)
            hit['tier'] = 'B'
            for k in ('status', 'reserve_url', 'rcpt_end'):
                hit[k] = b[k]
            hit['source'] = '표준데이터 + 서울 공공서비스예약'
        else:
            merged.append(b)
    return merged, len(used)

def guard(rows, min_ratio=0.7):
    """API가 일시적으로 반쪽만 응답할 때 기존 데이터를 덮어쓰지 않도록 막는다."""
    prev_path = ROOT / 'site' / 'data' / 'seoul_spaces.json'
    if not prev_path.exists():
        return
    try:
        prev = len(json.loads(prev_path.read_text(encoding='utf-8')))
    except Exception:
        return
    if prev and len(rows) < prev * min_ratio:
        raise SystemExit(
            f"중단: 이번 수집 {len(rows)}건이 기존 {prev}건의 {min_ratio:.0%}에 못 미칩니다.\n"
            f"  API 장애일 수 있습니다. 기존 데이터를 유지하고 종료합니다.\n"
            f"  의도한 축소라면 MIN_RATIO 환경변수를 낮춰 다시 실행하세요.")
    print(f"  안전장치 통과 ({prev} → {len(rows)}건)")


def main():
    std = json.load(open(OUT / 'standard_all.json', encoding='utf-8'))
    seoul = json.load(open(OUT / 'seoul_raw.json', encoding='utf-8'))
    api_rows = seoul['ListPublicReservationInstitution'] + seoul['ListPublicReservationSport']

    cs = from_standard(std)
    bs = from_seoul(api_rows)
    print(f"  표준데이터 서울 무료·실비  {len(cs)}건 (C층)")
    print(f"  예약 API 무료 → 공간 단위  {len(bs)}건 (B층)")

    rows, overlap = merge(cs, bs)
    print(f"  좌표·이름으로 매칭된 중복   {overlap}건")

    # 예약 API에 자치구가 빈 건이 있다. 2km 안의 가장 가까운 시설에서 빌려온다.
    known = [r for r in rows if r['sigungu']]
    filled = 0
    for r in rows:
        if r['sigungu']:
            continue
        best, bd = None, 2000
        for k in known:
            d = dist_m((r['lat'], r['lng']), (k['lat'], k['lng']))
            if d < bd:
                best, bd = k, d
        if best:
            r['sigungu'] = best['sigungu']
            r['sigungu_guessed'] = True
            filled += 1
    print(f"  자치구를 좌표로 채운 건     {filled}건")
    print(f"  최종 {len(rows)}건")

    for i, r in enumerate(rows):
        r['id'] = f"s{i+1:04d}"

    guard(rows, float(os.environ.get('MIN_RATIO', '0.7')))
    print(f"\n  층: {dict(collections.Counter(r['tier'] for r in rows))}")
    print(f"  요금: {dict(collections.Counter(r['fee_kind'] for r in rows))}")
    print(f"  종류: {dict(collections.Counter(r['category'] for r in rows))}")
    known = [r for r in rows if r['sigungu']]
    print(f"  자치구 있는 건 {len(known)}/{len(rows)} · 상위 "
          f"{collections.Counter(r['sigungu'] for r in known).most_common(8)}")
    cap = [r['capacity'] for r in rows if r['capacity']]
    print(f"  수용인원 있는 건 {len(cap)}/{len(rows)}")
    print(f"  예약 링크 있는 건 {sum(1 for r in rows if r['reserve_url'])}")
    save(rows, 'seoul_spaces.json')

    kst = datetime.timezone(datetime.timedelta(hours=9))
    meta = {
        'updated': datetime.datetime.now(kst).strftime('%Y-%m-%d %H:%M'),
        'total': len(rows),
        'tier_b': sum(1 for r in rows if r['tier'] == 'B'),
        'free': sum(1 for r in rows if r['fee_kind'] == '무료'),
        'region': '서울',
    }
    save(meta, 'meta.json')
    # 사이트가 읽는 위치로 복사한다
    site = ROOT / 'site' / 'data'
    if site.is_dir():
        for n in ('seoul_spaces.json', 'meta.json'):
            (site / n).write_text((OUT / n).read_text(encoding='utf-8'), encoding='utf-8')
        print(f"  site/data 갱신")

if __name__ == '__main__':
    main()
