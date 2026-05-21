"""
지오코딩 실패 204건 재시도 — 주소 정제 후 카카오 API 재요청
"""

import re
import time
import warnings
import requests
import pandas as pd
from pathlib import Path

warnings.filterwarnings('ignore')

OUT     = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
API_KEY = "287af499d084a4348f618fd0173fb7ff"
URL     = "https://dapi.kakao.com/v2/local/search/address.json"
HEADERS = {"Authorization": f"KakaoAK {API_KEY}"}

# ── 1. 파일 읽기 ───────────────────────────────────────────────
print("[ 1. 파일 읽기 ]")
df_fail = pd.read_excel(OUT / '지오코딩_실패목록.xlsx')
df_main = pd.read_excel(OUT / '서울_노인복지시설_좌표.xlsx')
print(f"  실패 목록: {len(df_fail)}건")
print(f"  메인 파일: {len(df_main)}건")


# ── 2. 주소 정제 함수 (강화) ──────────────────────────────────
def clean_retry(addr):
    """
    층수·호수·빌딩명·특수기호를 제거하고 핵심 도로명주소만 남김
    """
    if pd.isna(addr):
        return None, 'EMPTY'

    addr = str(addr).strip()

    # 숫자만인 완전 오염 데이터
    if re.match(r'^\d+$', addr):
        return None, 'INVALID_DATA'

    # 대괄호 [동명] 제거  예: 홍은제1동[홍은동] → 홍은제1동
    addr = re.sub(r'\[[^\]]*\]', '', addr)

    # 괄호 안 내용 제거  예: (쌍문동, 춘광빌딩) → ''
    addr = re.sub(r'\s*\(.*?\)', '', addr)

    # ── 층수 제거 ──────────────────────────────────────────────
    # 복합: 지,1,2~4,8층 / 1~5층 / 3,4층 / 4~6층
    addr = re.sub(r'\s*(?:지하?|B)?\s*\d+\s*[,~\.]\s*[\d,~\.]+\s*층', '', addr, flags=re.IGNORECASE)
    # 단순: N층 / BN층
    addr = re.sub(r'\s*(?:지하?|B)?\s*\d+\s*층', '', addr, flags=re.IGNORECASE)
    # 지하층 표기 (번지/행정동의 '지'는 보존): (?<!번) (?<!동) 제외
    addr = re.sub(r'(?<![번동])\s*지\s*[\d,]+\s*중?\s*\d*', '', addr)
    # 잔여 '중N' (지1중1층 처리 후)
    addr = re.sub(r'(?<=\d)중\d*', '', addr)
    # 잔여 쉼표+숫자+층
    addr = re.sub(r',\s*\d+\s*층', '', addr)

    # ── 호수 제거 (도로번호 54-4 보존, 번지N호·동N호 패턴 처리) ──
    # 동N호 → 동 (예: 7동104호 → 7동)
    addr = re.sub(r'(?<=동)\d+호', '', addr)
    # 번지 뒤 호수 (예: 72번지 7호 → 72번지)
    addr = re.sub(r'(?<=번지)\s+\d+호', '', addr)
    # 쉼표로 구분된 복합 호수: 207, 307호 / 101, B102호
    addr = re.sub(r'\s+[A-Za-z]?\d+(?:[,~]+\s*[A-Za-z]?\d+)+호', '', addr)
    # 숫자-숫자호: 402-1호 / B102호
    addr = re.sub(r'\s+[A-Za-z]?\d+[-]\d+호', '', addr)
    # 3자리 이상 단독 숫자호: 207호, 345호
    addr = re.sub(r'\s+[A-Za-z]?\d{3,}호', '', addr)
    # 잔여 쉼표+숫자호
    addr = re.sub(r',\s*[A-Za-z]?\d+호', '', addr)

    # 도로명 뒤 쉼표+숫자 잔여: "만리재로 99, 2, 3층" → ", 2" 제거
    addr = re.sub(r',\s*\d+\s*$', '', addr.rstrip())

    # 마침표 비정상: .장로.2길 → 장로.2길 (숫자 앞 마침표는 유지)
    addr = re.sub(r'^\s*\.+', '', addr)
    addr = re.sub(r'\.(?=[^\d])', '', addr)

    # 중복 공백·앞뒤 공백 정리
    addr = re.sub(r'\s{2,}', ' ', addr).strip()
    addr = addr.rstrip(',').strip()

    if not addr:
        return None, 'EMPTY_AFTER_CLEAN'

    # 서울 외 주소는 접두어 없이 그대로
    non_seoul = ['경기도', '강원', '충청', '전라', '경상', '인천', '부산', '대구']
    if not addr.startswith('서울') and not any(x in addr for x in non_seoul):
        addr = '서울특별시 ' + addr

    return addr, 'CLEANED'


# ── 3. 지오코딩 함수 ──────────────────────────────────────────
def geocode(address):
    if not address:
        return None, None, 'EMPTY'
    try:
        r = requests.get(
            URL,
            params={'query': address, 'size': 1},
            headers=HEADERS,
            timeout=10
        )
    except requests.exceptions.Timeout:
        return None, None, 'TIMEOUT'
    except requests.exceptions.ConnectionError:
        return None, None, 'CONNECTION_ERROR'

    if r.status_code == 429:
        time.sleep(1.0)
        return geocode(address)
    if r.status_code != 200:
        return None, None, f'HTTP_{r.status_code}'

    docs = r.json().get('documents', [])
    if not docs:
        return None, None, 'NO_RESULT'

    lon = float(docs[0].get('x', 0))
    lat = float(docs[0].get('y', 0))
    if lon == 0 and lat == 0:
        return None, None, 'ZERO_COORD'
    return lat, lon, 'OK'


# ── 4. 재시도 실행 ────────────────────────────────────────────
print("\n[ 2. 주소 정제 + 재시도 ]")
print(f"  총 {len(df_fail)}건 처리 시작\n")

retry_results = []
n_ok = n_fail = n_skip = 0

for i, row in df_fail.iterrows():
    raw_addr = row['주소']
    cleaned, flag = clean_retry(raw_addr)

    if flag in ('INVALID_DATA', 'EMPTY_AFTER_CLEAN', 'EMPTY'):
        lat, lon, reason = None, None, flag
        n_skip += 1
    else:
        lat, lon, reason = geocode(cleaned)

        # 여전히 실패 시 구+시설명 fallback
        if reason == 'NO_RESULT':
            if pd.notna(row.get('자치구')) and pd.notna(row.get('시설명')):
                fb = f"서울특별시 {row['자치구']} {row['시설명']}"
                lat, lon, reason = geocode(fb)
                if reason == 'OK':
                    reason = 'OK_FALLBACK'

        if reason.startswith('OK'):
            n_ok += 1
        else:
            n_fail += 1

        time.sleep(0.1)

    retry_results.append({
        'idx_in_main': row.name if hasattr(row, 'name') else i,
        '시설유형':    row.get('시설유형', ''),
        '자치구':      row.get('자치구', ''),
        '시설명':      row.get('시설명', ''),
        '주소_원본':   raw_addr,
        '주소_정제':   cleaned,
        '위도':        lat,
        '경도':        lon,
        '결과':        reason,
    })

    done = len(retry_results)
    if done % 50 == 0 or done == len(df_fail):
        print(f"  {done:3d}/{len(df_fail)} 완료 | 성공 {n_ok} / 실패 {n_fail} / 스킵 {n_skip}")

df_retry = pd.DataFrame(retry_results)


# ── 5. 메인 파일 업데이트 ─────────────────────────────────────
print("\n[ 3. 메인 파일 업데이트 ]")

# 성공한 건만 메인 파일에 반영 (시설명+자치구+주소로 매칭)
updated = 0
for _, row in df_retry.iterrows():
    if not str(row['결과']).startswith('OK'):
        continue
    mask = (
        (df_main['시설명'] == row['시설명']) &
        (df_main['자치구'] == row['자치구']) &
        (df_main['주소']   == row['주소_원본'])
    )
    if mask.sum() > 0:
        df_main.loc[mask, '위도']           = row['위도']
        df_main.loc[mask, '경도']           = row['경도']
        df_main.loc[mask, '지오코딩_결과']  = row['결과']
        updated += mask.sum()

print(f"  메인 파일 업데이트: {updated}건")

# 서울 좌표 범위 검수
out_of_range = (
    df_main['위도'].notna() &
    ((df_main['위도'] < 37.4) | (df_main['위도'] > 37.7) |
     (df_main['경도'] < 126.8) | (df_main['경도'] > 127.2))
)
if out_of_range.sum():
    print(f"  ⚠️  서울 범위 이탈: {out_of_range.sum()}건 → 좌표 제거")
    df_main.loc[out_of_range, ['위도','경도']] = None
    df_main.loc[out_of_range, '지오코딩_결과'] = 'OUT_OF_RANGE'

# 저장
df_main.to_excel(OUT / '서울_노인복지시설_좌표.xlsx', index=False)
print(f"  → 서울_노인복지시설_좌표.xlsx 저장 완료")

# 재시도 결과도 별도 저장
df_retry.to_excel(OUT / '지오코딩_재시도_결과.xlsx', index=False)
print(f"  → 지오코딩_재시도_결과.xlsx 저장 완료")


# ── 6. 최종 요약 ──────────────────────────────────────────────
print("\n[ 최종 요약 ]")
print("  ■ 재시도 결과:")
print(df_retry['결과'].value_counts().to_string())

total_ok = df_main['위도'].notna().sum()
total    = len(df_main)
print(f"\n  ■ 전체 메인 파일:")
print(f"    좌표 확보: {total_ok}건 / {total}건 ({total_ok/total*100:.1f}%)")
print(df_main['지오코딩_결과'].value_counts().to_string())

# 여전히 실패인 건
still_fail = df_main[df_main['위도'].isna()][
    ['시설유형','자치구','시설명','주소','지오코딩_결과']
]
if len(still_fail):
    still_fail.to_excel(OUT / '지오코딩_최종실패.xlsx', index=False)
    print(f"\n  최종 실패 {len(still_fail)}건 → 지오코딩_최종실패.xlsx")
