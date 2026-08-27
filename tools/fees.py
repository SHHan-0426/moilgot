"""사용료 파싱 — 표준데이터의 rntfee 는 자유 텍스트다.

실제로 들어 있는 모양들:
  '10000'                        단일 금액
  '10,000원'                     쉼표 + 단위
  '평일:66000+주말:85800'         구분자 +
  '(성인)4000+(군경/청소년)3500'   대상별
  '오전(9~13) 3000+오후(13~17) 4000'  시간대별
  '(평일) 30000원(2h)+(주말) 40000원(2h)+기준시간 초과시 20퍼센트...'

시간·인원·퍼센트 같은 잡음이 섞이므로 '금액 후보 중 최저가'를 대표값으로 쓰되,
원문을 그대로 화면에 같이 보여준다. 아는 척하지 않기 위해서다.
"""
import re

# '0원'은 앞에 숫자가 붙지 않을 때만 무료로 본다. 그렇지 않으면 '70000원'의 끝 '0원'에 걸린다.
_FREE = re.compile(r'무료|무상|없음(?!\s*음)|(?<![\d,])0\s*원')
_NOISE_CTX = re.compile(r'퍼센트|%|시간|분|명|인|층|㎡|평')

def parse_fee(raw):
    """returns (최저금액|None, 무료여부)"""
    s = str(raw or '').strip()
    if not s:
        return None, False
    # 숫자 사이 쉼표 제거: '10,000' -> '10000'
    s2 = re.sub(r'(?<=\d),(?=\d)', '', s)
    if _FREE.search(s2):
        return 0, True
    nums = [int(n) for n in re.findall(r'\d+', s2)]
    # 100원 미만은 시간·인원·비율 같은 잡음으로 본다
    cand = [n for n in nums if n >= 100]
    if not cand:
        return (0, True) if nums and max(nums) == 0 else (None, False)
    return min(cand), False

def classify(paid_yn, raw, cheap_limit=10000):
    """무료 / 실비 / 유료 / 미상"""
    paid = str(paid_yn or '').strip().upper()
    fee, free_text = parse_fee(raw)
    if paid in ('N', '무료') or free_text or fee == 0:
        return '무료', (fee if fee is not None else 0)
    if fee is None:
        return ('유료', None) if paid in ('Y', '유료') else ('미상', None)
    return ('실비' if fee <= cheap_limit else '유료'), fee
