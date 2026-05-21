"""
노인복지시설 주소 → 카카오 지오코딩 (위도/경도 변환)
"""

import time
import re
import warnings
import requests
import pandas as pd
from pathlib import Path

warnings.filterwarnings('ignore')

BASE    = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석/통계자료")
OUT     = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
API_KEY = "287af499d084a4348f618fd0173fb7ff"
URL     = "https://dapi.kakao.com/v2/local/search/address.json"
HEADERS = {"Authorization": f"KakaoAK {API_KEY}"}

# ── 1. 파일 읽기 ───────────────────────────────────────────────
print("[ 1. 파일 읽기 ]")
raw = pd.read_excel(BASE / '노인복지시설_서울_2025.xlsx', header=None)
header = raw.iloc[1].tolist()
df = raw.iloc[2:].copy()
df.columns = header
df = df.loc[:, df.columns.notna()].reset_index(drop=True)
print(f"  총 {len(df)}행 로드 완료")
print(f"  주소 결측: {df['주소'].isnull().sum()}건")

# ── 2. 주소 정제 함수 ──────────────────────────────────────────
def clean_address(addr):
    """괄호 안 동명 제거, 앞뒤 공백 정리, 서울특별시 접두어 추가"""
    if pd.isna(addr):
        return None
    addr = str(addr).strip()
    addr = re.sub(r'\s*\(.*?\)', '', addr).strip()   # (삼성동) 제거
    addr = re.sub(r'\s+', ' ', addr)                 # 중복 공백 제거
    if not addr.startswith('서울'):
        addr = '서울특별시 ' + addr
    return addr

# ── 3. 지오코딩 함수 ──────────────────────────────────────────
def geocode(address):
    """
    Returns (lat, lon, reason)
    성공: (float, float, 'OK')
    실패: (None, None, 오류사유)
    """
    if not address:
        return None, None, '주소없음'

    try:
        resp = requests.get(
            URL,
            params={'query': address, 'size': 1},
            headers=HEADERS,
            timeout=10
        )
    except requests.exceptions.Timeout:
        return None, None, 'TIMEOUT'
    except requests.exceptions.ConnectionError:
        return None, None, 'CONNECTION_ERROR'

    if resp.status_code == 401:
        return None, None, 'API_KEY_INVALID'
    if resp.status_code == 429:
        return None, None, 'RATE_LIMIT'
    if resp.status_code != 200:
        return None, None, f'HTTP_{resp.status_code}'

    data = resp.json()
    docs = data.get('documents', [])
    if not docs:
        return None, None, 'NO_RESULT'

    doc = docs[0]
    lon = float(doc.get('x', 0))
    lat = float(doc.get('y', 0))
    if lon == 0 and lat == 0:
        return None, None, 'ZERO_COORD'
    return lat, lon, 'OK'

# ── 4. 전체 지오코딩 실행 ─────────────────────────────────────
print("\n[ 2. 지오코딩 시작 ]")
print(f"  총 {len(df)}건 / 요청 간격 0.1초 / 예상 시간 ~{len(df)*0.1/60:.0f}분")

lats, lons, reasons = [], [], []
n_ok = n_fail = 0

for i, row in df.iterrows():
    raw_addr  = row['주소']
    clean_addr = clean_address(raw_addr)

    lat, lon, reason = geocode(clean_addr)

    # 1차 실패 시 자치구 + 시설명으로 재시도
    if reason == 'NO_RESULT' and pd.notna(row.get('시설명')) and pd.notna(row.get('자치구')):
        fallback = f"서울특별시 {row['자치구']} {row['시설명']}"
        lat, lon, reason = geocode(fallback)
        if reason == 'OK':
            reason = 'OK_FALLBACK'

    # RATE_LIMIT은 1회 재시도 (0.5초 대기)
    if reason == 'RATE_LIMIT':
        time.sleep(0.5)
        lat, lon, reason = geocode(clean_addr)

    lats.append(lat)
    lons.append(lon)
    reasons.append(reason)

    if reason.startswith('OK'):
        n_ok += 1
    else:
        n_fail += 1

    # 100건마다 진행상황 출력
    done = i + 1
    if done % 100 == 0 or done == len(df):
        pct = done / len(df) * 100
        print(f"  {done:4d}/{len(df)} 완료 ({pct:.1f}%) | 성공 {n_ok} / 실패 {n_fail}")

    time.sleep(0.1)

# ── 5. 결과 컬럼 추가 ─────────────────────────────────────────
df['위도'] = lats
df['경도'] = lons
df['지오코딩_결과'] = reasons

# 서울 좌표 범위 벗어난 건 검수
out_of_range = (
    df['위도'].notna() &
    ((df['위도'] < 37.4) | (df['위도'] > 37.7) |
     (df['경도'] < 126.8) | (df['경도'] > 127.2))
)
if out_of_range.sum() > 0:
    print(f"\n  ⚠️  서울 좌표 범위 벗어난 건: {out_of_range.sum()}건")
    print(df[out_of_range][['시설명','주소','위도','경도']].to_string())
    df.loc[out_of_range, ['위도','경도']] = None
    df.loc[out_of_range, '지오코딩_결과'] = 'OUT_OF_RANGE'

# ── 6. 결과 저장 ──────────────────────────────────────────────
out_path = OUT / '서울_노인복지시설_좌표.xlsx'
df.to_excel(out_path, index=False)
print(f"\n[ 3. 저장 완료 ]")
print(f"  → {out_path}")

# ── 7. 요약 ────────────────────────────────────────────────────
print("\n[ 결과 요약 ]")
summary = df['지오코딩_결과'].value_counts()
print(summary.to_string())
print(f"\n  최종 성공: {df['위도'].notna().sum()}건 / 전체 {len(df)}건")
print(f"  성공률: {df['위도'].notna().sum()/len(df)*100:.1f}%")

# 실패 상세
fail_df = df[df['위도'].isna()][['시설유형','자치구','시설명','주소','지오코딩_결과']]
if len(fail_df):
    fail_path = OUT / '지오코딩_실패목록.xlsx'
    fail_df.to_excel(fail_path, index=False)
    print(f"\n  실패 목록 저장: {fail_path}")
    print(f"  실패 상위 10건:")
    print(fail_df.head(10).to_string(index=False))
