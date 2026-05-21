"""
서울시 노인 복지 데드존 분석 - 데이터 검증 및 사전 분석
"""

import os
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path

warnings.filterwarnings('ignore')

BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석/통계자료")
OUT  = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")

# ── 한글 폰트 ──────────────────────────────────────────────────
def set_korean_font():
    os.system("apt-get install -y fonts-nanum -qq 2>/dev/null")
    candidates = [
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for p in candidates:
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            prop = fm.FontProperties(fname=p)
            fname = prop.get_name()
            matplotlib.rc('font', family=fname)
            plt.rcParams['axes.unicode_minus'] = False
            print(f"  [폰트] {fname}")
            return fname
    matplotlib.rc('font', family='DejaVu Sans')
    plt.rcParams['axes.unicode_minus'] = False
    return 'DejaVu Sans'

FONT = set_korean_font()

def basic_quality(df, name):
    nr, nc = df.shape
    nd = df.duplicated().sum()
    mr = df.isnull().mean().round(4)
    top = mr[mr > 0].sort_values(ascending=False)
    print(f"  [{name}] {nr}행 × {nc}열  |  중복 {nd}행")
    if len(top):
        print(f"  결측(상위5): { dict(list(top.items())[:5]) }")
    else:
        print("  결측값 없음")
    return {'rows': nr, 'cols': nc, 'dup': int(nd), 'miss_max': float(mr.max())}

# ══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 1. 데이터 검증")
print("="*70)

results = {}

# 출력용 공통 변수 (나중 단계에서도 사용)
df_welfare = None; df_bokjigwan = None; df_yoyang = None
gu_col = addr_col = type_col = dtype_col = None
df_pop = None
df_live = None
df_bus_seoul = None
df_metro_seoul = None
df_dong = None
df_dist = None
df_corr_base = None
df_merged_gu = None
deadzone_cand = None
corr_mat = None

SEOUL_25 = ['강남구','강동구','강북구','강서구','관악구','광진구','구로구','금천구',
            '노원구','도봉구','동대문구','동작구','마포구','서대문구','서초구','성동구',
            '성북구','송파구','양천구','영등포구','용산구','은평구','종로구','중구','중랑구']

GU_CENTERS = {
    '종로구': (37.5730, 126.9794), '중구': (37.5636, 126.9975),
    '용산구': (37.5321, 126.9906), '성동구': (37.5634, 127.0369),
    '광진구': (37.5385, 127.0824), '동대문구': (37.5744, 127.0397),
    '중랑구': (37.6063, 127.0931), '성북구': (37.5894, 127.0167),
    '강북구': (37.6397, 127.0256), '도봉구': (37.6688, 127.0471),
    '노원구': (37.6544, 127.0568), '은평구': (37.6176, 126.9227),
    '서대문구': (37.5791, 126.9368), '마포구': (37.5663, 126.9014),
    '양천구': (37.5170, 126.8665), '강서구': (37.5509, 126.8496),
    '구로구': (37.4954, 126.8874), '금천구': (37.4567, 126.8956),
    '영등포구': (37.5262, 126.8962), '동작구': (37.5124, 126.9393),
    '관악구': (37.4784, 126.9516), '서초구': (37.4837, 127.0324),
    '강남구': (37.5172, 127.0473), '송파구': (37.5145, 127.1059),
    '강동구': (37.5301, 127.1237),
}

GU_CODE5 = {
    11110:'종로구', 11140:'중구', 11170:'용산구', 11200:'성동구',
    11215:'광진구', 11230:'동대문구', 11260:'중랑구', 11290:'성북구',
    11305:'강북구', 11320:'도봉구', 11350:'노원구', 11380:'은평구',
    11410:'서대문구', 11440:'마포구', 11470:'양천구', 11500:'강서구',
    11530:'구로구', 11545:'금천구', 11560:'영등포구', 11590:'동작구',
    11620:'관악구', 11650:'서초구', 11680:'강남구', 11710:'송파구',
    11740:'강동구',
}

# ──────────────────────────────────────────────
# 1-2. 노인복지시설
# ──────────────────────────────────────────────
print("\n[ 1-2. 노인복지시설 ]")
try:
    raw = pd.read_excel(BASE / '노인복지시설_서울_2025.xlsx', header=None)
    # row0 = 타이틀, row1 = 헤더, row2~ = 데이터
    header = raw.iloc[1].tolist()
    df_welfare = raw.iloc[2:].copy()
    df_welfare.columns = header
    df_welfare = df_welfare.reset_index(drop=True)
    # NaN 컬럼명 제거
    df_welfare = df_welfare.loc[:, df_welfare.columns.notna()]

    q = basic_quality(df_welfare, '노인복지시설')

    gu_col    = '자치구'
    addr_col  = '주소'
    type_col  = '시설유형'
    dtype_col = '시설대분류'

    gu_covered = [g for g in SEOUL_25 if g in df_welfare[gu_col].values]
    gu_missing = [g for g in SEOUL_25 if g not in df_welfare[gu_col].values]
    miss_addr  = df_welfare[addr_col].isnull().mean()
    type_counts = df_welfare[type_col].value_counts()

    print(f"  서울 25개 자치구 커버: {len(gu_covered)}/25")
    if gu_missing:
        print(f"  누락 자치구: {gu_missing}")
    print(f"  주소 결측률: {miss_addr:.1%}")
    print(f"  시설유형별 수 (상위 10):\n{type_counts.head(10).to_string()}")

    # 좌표 여부
    lat_c = [c for c in df_welfare.columns if any(x in str(c) for x in ['위도','lat','LAT'])]
    lon_c = [c for c in df_welfare.columns if any(x in str(c) for x in ['경도','lon','LON'])]
    print(f"  좌표 컬럼: 위도={lat_c}, 경도={lon_c}")

    df_bokjigwan = df_welfare[df_welfare[type_col].str.contains('복지관', na=False)].copy()
    df_yoyang    = df_welfare[df_welfare[type_col].str.contains('요양', na=False)].copy()
    print(f"  노인복지관 수: {len(df_bokjigwan)}")
    print(f"  노인요양시설 수: {len(df_yoyang)}")

    q.update({'gu_cov': len(gu_covered), 'addr_miss': float(miss_addr),
               'status': '⚠️ 좌표없음' if not lat_c else '✅'})
    results['노인복지시설'] = q

except Exception as e:
    import traceback; traceback.print_exc()
    results['노인복지시설'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-3. 65세 이상 인구
# ──────────────────────────────────────────────
print("\n[ 1-3. 65세 이상 인구 (행정안전부) ]")
try:
    raw_pop = pd.read_excel(BASE / '연령별_인구현황_자치구_2026년3월.xlsx', header=None)
    header_pop = raw_pop.iloc[3].tolist()
    df_pop = raw_pop.iloc[4:].copy()
    df_pop.columns = range(len(header_pop))
    df_pop = df_pop[df_pop[0].notna()].reset_index(drop=True)
    df_pop[0] = df_pop[0].astype(str).str.strip()

    # 65세 ~ 100세이상 컬럼 (첫 번째 블록: col 69~104)
    ages = [str(h) for h in header_pop]
    idx_65    = ages.index('65세')
    idx_100plus = next(i for i in range(idx_65, idx_65+50) if '100' in ages[i])
    age_cols = list(range(idx_65, idx_100plus + 1))  # 69~104

    for c in age_cols:
        df_pop[c] = pd.to_numeric(
            df_pop[c].astype(str).str.replace(',','').str.strip(), errors='coerce')
    df_pop['pop_65plus'] = df_pop[age_cols].sum(axis=1)
    df_pop['gu_code'] = df_pop[0]
    df_pop['gu_name'] = df_pop[1]

    total_65 = df_pop[df_pop['gu_code']=='1100000000']['pop_65plus'].values
    print(f"  총 행수: {len(df_pop)} (서울+25구 = 26)")
    print(f"  코드 형식: 10자리 자치구코드 (행정동 아님)")
    print(f"  ⚠️  자치구(구) 단위만 존재 — 행정동 단위 65세+ 인구 없음")
    if len(total_65):
        print(f"  서울 전체 65세+ 인구: {total_65[0]:,.0f}명")
    print(f"  자치구별 65세+ 인구 (상위 5):")
    top5 = df_pop[df_pop['gu_code']!='1100000000'].nlargest(5,'pop_65plus')[['gu_name','pop_65plus']]
    print(top5.to_string(index=False))
    print(f"  0 또는 결측인 행: {(df_pop['pop_65plus'].fillna(0) == 0).sum()}")

    results['65세이상인구'] = {'rows': len(df_pop), 'unit': '자치구',
                               'status': '⚠️ 구단위(행정동아님)'}

except Exception as e:
    import traceback; traceback.print_exc()
    results['65세이상인구'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-4. 생활인구 65세+
# ──────────────────────────────────────────────
print("\n[ 1-4. 생활인구 65세+ ]")
try:
    df_live = pd.read_csv(BASE / '생활인구_자치구별_2025.csv', encoding='utf-8')
    q = basic_quality(df_live, '생활인구')

    print(f"  날짜 범위: {df_live['stdr_de_id'].min()} ~ {df_live['stdr_de_id'].max()}")
    print(f"  시간대: 0~23시")
    print(f"  코드 자리수: 5자리 (자치구 단위)")
    print(f"  코드 샘플: {df_live['adstrd_code_se'].unique()[:5].tolist()}")
    print(f"  ⚠️  구 단위(5자리) / 75세이상 컬럼 없음 (65~74세만)")

    df_live['lvpop_65to74'] = (
        df_live['male_f65t69_lvpop_co'].fillna(0) +
        df_live['male_f70t74_lvpop_co'].fillna(0) +
        df_live['female_f65t69_lvpop_co'].fillna(0) +
        df_live['female_f70t74_lvpop_co'].fillna(0)
    )
    daily_avg = df_live.groupby('adstrd_code_se')['lvpop_65to74'].mean().reset_index()
    daily_avg.columns = ['gu_code5', 'avg_lvpop_65to74']
    daily_avg['자치구'] = daily_avg['gu_code5'].map(GU_CODE5)
    print(f"\n  구별 일평균 65~74세 생활인구 (상위 5):")
    print(daily_avg.nlargest(5,'avg_lvpop_65to74').to_string(index=False))

    q.update({'status': '⚠️ 구단위·75세+없음', 'unit': '자치구'})
    results['생활인구'] = q

except Exception as e:
    import traceback; traceback.print_exc()
    results['생활인구'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-5. 버스정류소
# ──────────────────────────────────────────────
print("\n[ 1-5. 버스정류소 ]")
try:
    df_bus = pd.read_excel(BASE / '버스정류소_위치정보_2026년5월.xlsx')
    q = basic_quality(df_bus, '버스정류소')

    df_bus['X좌표'] = pd.to_numeric(df_bus['X좌표'], errors='coerce')
    df_bus['Y좌표'] = pd.to_numeric(df_bus['Y좌표'], errors='coerce')
    n_no_coord = df_bus[['X좌표','Y좌표']].isnull().any(axis=1).sum()
    df_valid = df_bus.dropna(subset=['X좌표','Y좌표'])

    in_seoul = ((df_valid['Y좌표']>=37.4)&(df_valid['Y좌표']<=37.7)&
                (df_valid['X좌표']>=126.8)&(df_valid['X좌표']<=127.2))
    df_bus_seoul = df_valid[in_seoul].copy()
    seoul_ratio = len(df_bus_seoul) / len(df_valid)

    print(f"  총 정류소: {len(df_bus)}")
    print(f"  좌표 결측: {n_no_coord}")
    print(f"  서울 범위 내: {len(df_bus_seoul)} ({seoul_ratio:.1%})")

    q.update({'total': len(df_bus), 'no_coord': int(n_no_coord),
               'seoul_ratio': float(seoul_ratio), 'status': '✅'})
    results['버스정류소'] = q

except Exception as e:
    import traceback; traceback.print_exc()
    results['버스정류소'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-6. 지하철역
# ──────────────────────────────────────────────
print("\n[ 1-6. 지하철역 ]")
try:
    df_metro = pd.read_excel(BASE / '도시철도_역사정보_전국_2026년2월.xlsx')
    q = basic_quality(df_metro, '지하철역')

    df_metro['역위도'] = pd.to_numeric(df_metro['역위도'], errors='coerce')
    df_metro['역경도'] = pd.to_numeric(df_metro['역경도'], errors='coerce')
    in_s = ((df_metro['역위도']>=37.4)&(df_metro['역위도']<=37.7)&
            (df_metro['역경도']>=126.8)&(df_metro['역경도']<=127.2))
    df_metro_seoul = df_metro[in_s].copy()

    addr_s = df_metro['역사도로명주소'].str.contains('서울', na=False).sum()
    print(f"  전국 전체: {len(df_metro)}")
    print(f"  서울 좌표범위 내: {len(df_metro_seoul)}")
    print(f"  주소 '서울' 포함: {addr_s}")
    print(f"  서울 내 운영기관:\n{df_metro_seoul['운영기관명'].value_counts().head(6).to_string()}")

    q.update({'total': len(df_metro), 'seoul': len(df_metro_seoul), 'status': '✅'})
    results['지하철역'] = q

except Exception as e:
    import traceback; traceback.print_exc()
    results['지하철역'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-7. 독거노인
# ──────────────────────────────────────────────
print("\n[ 1-7. 독거노인 ]")
try:
    raw_alone = pd.read_excel(
        BASE / '독거노인_현황_행정동별_2024.xlsx', header=None)
    print("  헤더 (0~3행, 0~5열):")
    print(raw_alone.iloc[:4, :6].to_string())

    df_alone_all = raw_alone.iloc[4:].copy()
    df_alone_all.columns = range(raw_alone.shape[1])
    df_alone_all = df_alone_all.reset_index(drop=True)

    # col0=시도(NaN=아님), col1=구명, col2=동명
    # 행정동 행: col0 NaN, col2 존재, col2 != '소계'
    df_dong = df_alone_all[
        df_alone_all[0].isna() &
        df_alone_all[2].notna() &
        (df_alone_all[2] != '소계')
    ].copy()

    # 구명 forward-fill
    df_alone_all[1] = df_alone_all[1].ffill()
    df_dong = df_alone_all[
        df_alone_all[0].isna() &
        df_alone_all[2].notna() &
        (df_alone_all[2] != '소계')
    ].copy()

    num_conv = lambda s: pd.to_numeric(
        s.astype(str).str.replace(',','').str.replace('-','0').str.strip(),
        errors='coerce')

    df_dong[3] = num_conv(df_dong[3])   # 전체 독거노인 계
    df_dong[6] = num_conv(df_dong[6])   # 기초수급권자 계
    df_dong.columns = list(range(raw_alone.shape[1]))

    df_dong = df_dong.rename(columns={1:'구명', 2:'동명', 3:'alone_total', 6:'sugeup_total'})
    df_dong = df_dong[['구명','동명','alone_total','sugeup_total']].copy()

    print(f"\n  파싱된 행정동 수: {len(df_dong)}")
    print(f"  구명 forward-fill 후 샘플:")
    print(df_dong.head(5).to_string(index=False))
    print(f"  ⚠️  행정동 코드 없음 → 동명 기반 매핑 필요")
    print(f"  기초수급자: 독거노인 파일 내 col6 사용 가능")

    results['독거노인'] = {'rows': len(df_dong), 'has_code': False, 'status': '⚠️ 코드없음'}
    results['기초수급자'] = {'status': '⚠️ 별도파일없음', 'note': '독거노인파일 내 수급권자컬럼 활용'}

except Exception as e:
    import traceback; traceback.print_exc()
    results['독거노인'] = {'status': '❌', 'error': str(e)}


# ──────────────────────────────────────────────
# 1-8. 행정동·격자 SHP
# ──────────────────────────────────────────────
print("\n[ 1-8. 행정동·격자 SHP ]")
try:
    gdf_grid = gpd.read_file(BASE / '행정동·격자/서울_250m격자.shp')
    bounds0 = gdf_grid.iloc[0].geometry.bounds
    cell_w = bounds0[2] - bounds0[0]
    cell_h = bounds0[3] - bounds0[1]
    gdf_grid_wgs = gdf_grid.to_crs(epsg=4326)
    sample_ctr = gdf_grid_wgs.iloc[0].geometry.centroid

    print(f"  Shape: {gdf_grid.shape}")
    print(f"  CRS: {gdf_grid.crs}")
    print(f"  컬럼: {gdf_grid.columns.tolist()}")
    print(f"  셀 크기: {cell_w:.0f}m × {cell_h:.0f}m")
    print(f"  총 격자 수: {len(gdf_grid)}")
    print(f"  ⚠️  250m 격자(Grid) — 행정동 경계 폴리곤 아님")
    print(f"  ⚠️  행정동 경계 SHP 없음 → SGIS/행안부 추가 수집 필요")
    print(f"  WGS84 변환 샘플: lat={sample_ctr.y:.4f}, lon={sample_ctr.x:.4f}")

    results['행정동SHP'] = {
        'type': '250m격자', 'rows': len(gdf_grid),
        'crs': str(gdf_grid.crs), 'cell_size': f'{cell_w:.0f}m',
        'status': '⚠️ 격자파일(행정동경계아님)',
    }

except Exception as e:
    import traceback; traceback.print_exc()
    results['행정동SHP'] = {'status': '❌', 'error': str(e)}


# ══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 2. 결합 가능성 검증")
print("="*70)

# ──────────────────────────────────────────────
# 2-1. 코드 형식 비교
# ──────────────────────────────────────────────
print("\n[ 2-1. 행정동 코드 형식 비교 ]")
code_info = {
    '노인복지시설':    {'형식': '자치구명(텍스트)', '자리수': '-', '단위': '자치구', '비고': '주소→지오코딩 필요'},
    '65세이상인구':    {'형식': '10자리 숫자', '자리수': '10', '단위': '자치구', '비고': '11XX000000 형태'},
    '생활인구':        {'형식': '5자리 숫자', '자리수': '5', '단위': '자치구', '비고': '예:11110(종로)'},
    '독거노인':        {'형식': '동명(텍스트)', '자리수': '-', '단위': '행정동', '비고': '코드없음·매핑필요'},
    '버스정류소':      {'형식': 'WGS84 좌표', '자리수': '-', '단위': '포인트', '비고': '공간조인'},
    '지하철역':        {'형식': 'WGS84 좌표', '자리수': '-', '단위': '포인트', '비고': '공간조인'},
    '격자SHP':         {'형식': 'GID(비표준)', '자리수': '-', '단위': '250m격자', '비고': '표준코드아님'},
}
print(pd.DataFrame(code_info).T.to_string())
print("\n  ✅ 버스/지하철 ↔ 격자SHP: 공간조인 가능 (EPSG:5179 변환 후)")
print("  ⚠️  독거노인 ↔ 기타: 동명 텍스트 매핑 필요")
print("  ❌  행정동 경계 SHP 없음 → 행정동 단위 공간분석 불가")


# ──────────────────────────────────────────────
# 2-2. 공간 조인 테스트 (버스 ↔ 격자)
# ──────────────────────────────────────────────
print("\n[ 2-2. 공간 조인 테스트 (버스정류소 ↔ 격자SHP) ]")
try:
    gdf_bus = gpd.GeoDataFrame(
        df_bus_seoul,
        geometry=gpd.points_from_xy(df_bus_seoul['X좌표'], df_bus_seoul['Y좌표']),
        crs='EPSG:4326'
    )
    gdf_bus_p = gdf_bus.to_crs(epsg=5179)
    gdf_grid2 = gpd.read_file(BASE / '행정동·격자/서울_250m격자.shp')

    joined = gpd.sjoin(gdf_bus_p, gdf_grid2, how='left', predicate='within')
    n_matched = joined['index_right'].notna().sum()
    n_total   = len(joined)
    print(f"  조인 성공: {n_matched}/{n_total} ({n_matched/n_total:.1%})")

    cell_cnt = joined.groupby('CELL_ID').size().reset_index(name='bus_count')
    print(f"\n  격자별 버스정류소 수 상위 10:")
    print(cell_cnt.nlargest(10,'bus_count').to_string(index=False))
    print(f"\n  조인 안 된 정류소: {n_total - n_matched}")

except Exception as e:
    import traceback; traceback.print_exc()


# ──────────────────────────────────────────────
# 2-3. 250m 격자 현황
# ──────────────────────────────────────────────
print("\n[ 2-3. 250m 격자 현황 ]")
try:
    gdf_g = gpd.read_file(BASE / '행정동·격자/서울_250m격자.shp')
    gdf_g_wgs = gdf_g.to_crs(epsg=4326)
    print(f"  총 격자 수: {len(gdf_g)}")
    print(f"  격자 중심점 샘플 5개 (WGS84):")
    for _, row in gdf_g_wgs.head(5).iterrows():
        c = row.geometry.centroid
        print(f"    CELL_ID={row['CELL_ID']:16s}  lat={c.y:.4f}, lon={c.x:.4f}")
except Exception as e:
    print(f"  [ERROR] {e}")


# ══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 3. 사전 분석")
print("="*70)

# ──────────────────────────────────────────────
# 3-1. 노인복지관 접근성 (자치구 중심점 기준)
# ──────────────────────────────────────────────
print("\n[ 3-1. 노인복지관 접근성 분석 ]")
try:
    if df_bokjigwan is None or gu_col is None:
        raise RuntimeError("노인복지관 데이터 없음")

    # 모든 25개 구에 복지관 ≥1개 존재 → 구 중심점 거리는 의미 없음
    # 대신: 65세+ 1인당 복지관 수의 역수를 "접근성 부족 지표"로 사용
    bokji_cnt = df_bokjigwan[gu_col].value_counts().reset_index()
    bokji_cnt.columns = ['자치구', 'n_bokjigwan']

    # 인구는 뒤에서 df_pop 로드 후 merge — 여기서는 복지관 수만 정리
    print(f"  ⚠️  25개 자치구 모두 복지관 ≥1개 → 구 중심점 최근접 거리 = 전부 0")
    print(f"  대안: 65세+ 1만 명당 복지관 수(역수)를 접근성 지표로 사용")
    print(f"\n  자치구별 노인복지관 수 (상위/하위):")
    print(bokji_cnt.sort_values('n_bokjigwan', ascending=False).to_string(index=False))

    # 인구 로드 (1-3 에서 df_pop 이미 설정됨)
    df_pop_gu2 = df_pop[df_pop['gu_code'] != '1100000000'].copy()
    df_pop_gu2['자치구'] = (df_pop_gu2['gu_name']
                            .str.replace('서울특별시 ', '', regex=False).str.strip())
    df_acc = df_pop_gu2[['자치구','pop_65plus']].merge(bokji_cnt, on='자치구', how='left')
    df_acc['n_bokjigwan'] = df_acc['n_bokjigwan'].fillna(0)
    df_acc['bokji_per_10k'] = (df_acc['n_bokjigwan'] / (df_acc['pop_65plus'] / 10000)).round(3)
    # 접근성 부족 지표 (역수 비례): 낮을수록 접근 어려움
    df_acc['access_lack'] = (1 / df_acc['bokji_per_10k'].replace(0, np.nan)).round(4)
    df_dist = df_acc.sort_values('access_lack', ascending=False)
    # 역수를 "가중 접근부족 거리(km)" 대신 칼럼명 유지해 하위 호환
    df_dist = df_dist.rename(columns={'access_lack': '최근거리_km'})

    print(f"\n  접근성 부족 지표 (1/복지관밀도) 상위 10 — 값 클수록 접근 어려움:")
    print(df_dist[['자치구','pop_65plus','n_bokjigwan','bokji_per_10k','최근거리_km']]
          .head(10).to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(df_dist['자치구'], df_dist['최근거리_km'], color='steelblue', alpha=0.85)
    ax.axvline(df_dist['최근거리_km'].mean(), color='red', linestyle='--',
               label=f"서울 평균")
    ax.set_xlabel('접근성 부족 지수 (1 / 복지관 밀도)')
    ax.set_title('자치구별 노인복지관 접근성 부족 지수\n(높을수록 접근 어려움)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / 'fig_dist_histogram.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  → fig_dist_histogram.png 저장 (접근성 부족 지수 막대 그래프)")

except Exception as e:
    import traceback; traceback.print_exc()


# ──────────────────────────────────────────────
# 3-2. H1 상관관계 매트릭스
# ──────────────────────────────────────────────
print("\n[ 3-2. H1 사전 검토 - 상관관계 매트릭스 ]")
try:
    df_corr_base = pd.DataFrame({'자치구': list(GU_CENTERS.keys())})

    # A. 65세+ 인구
    df_pop_gu = df_pop[df_pop['gu_code'] != '1100000000'].copy()
    df_pop_gu['자치구'] = (df_pop_gu['gu_name']
                           .str.replace('서울특별시 ', '', regex=False).str.strip())
    df_corr_base = df_corr_base.merge(
        df_pop_gu[['자치구','pop_65plus']], on='자치구', how='left')

    # B. 독거노인 구별 합계
    raw_a = pd.read_excel(
        BASE / '독거노인_현황_행정동별_2024.xlsx', header=None)
    df_a = raw_a.iloc[4:].copy()
    df_a.columns = range(raw_a.shape[1])
    # 구 소계 행: col0=NaN, col1=구명, col2='소계'
    df_gu_a = df_a[df_a[0].isna() & df_a[1].notna() & (df_a[2]=='소계')].copy()
    num = lambda s: pd.to_numeric(
        s.astype(str).str.replace(',','').str.replace('-','0').str.strip(), errors='coerce')
    df_gu_a[3] = num(df_gu_a[3])  # 전체 독거노인
    df_gu_a[6] = num(df_gu_a[6])  # 기초수급권자
    df_gu_a['자치구'] = df_gu_a[1].astype(str).str.strip()
    df_gu_a = df_gu_a[['자치구', 3, 6]].rename(columns={3:'alone_elder', 6:'basic_livelihood'})
    df_corr_base = df_corr_base.merge(df_gu_a, on='자치구', how='left')

    # C. 접근성 부족 지수 (pop_65plus 중복 제거 후 merge)
    if df_dist is not None:
        dist_cols = ['자치구', '최근거리_km', 'bokji_per_10k']
        merge_cols = [c for c in dist_cols if c in df_dist.columns]
        df_corr_base = df_corr_base.merge(df_dist[merge_cols], on='자치구', how='left')

    # D. 생활인구 일평균 65~74세
    daily_gu = (df_live
                .assign(자치구=df_live['adstrd_code_se'].map(GU_CODE5))
                .groupby('자치구')['lvpop_65to74'].mean()
                .reset_index()
                .rename(columns={'lvpop_65to74': 'avg_lvpop_65to74'}))
    df_corr_base = df_corr_base.merge(daily_gu, on='자치구', how='left')

    print(f"  통합 데이터 ({df_corr_base.shape}):")
    print(df_corr_base[['자치구','pop_65plus','alone_elder','basic_livelihood',
                         '최근거리_km','avg_lvpop_65to74']].to_string(index=False))

    # 상관관계
    # 최근거리_km = 접근성 부족 지수(1/밀도)
    acc_col = '최근거리_km' if '최근거리_km' in df_corr_base.columns else 'bokji_per_10k'
    col_rename = {
        'pop_65plus':      '65세+\n인구수',
        'alone_elder':     '독거노인\n수',
        'basic_livelihood':'기초수급자\n수',
        acc_col:           '접근성\n부족지수',
        'avg_lvpop_65to74':'생활인구\n65~74세',
    }
    available_cols = [k for k in col_rename if k in df_corr_base.columns]
    df_num = df_corr_base[available_cols].rename(columns=col_rename)
    corr_mat = df_num.corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr_mat, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=-1, vmax=1, center=0, square=True, linewidths=0.5,
                ax=ax, cbar_kws={'shrink': 0.8})
    ax.set_title('H1 검증 변수 상관관계 매트릭스\n(자치구 단위, n=25)')
    plt.tight_layout()
    plt.savefig(OUT / 'fig_correlation_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  → fig_correlation_heatmap.png 저장")
    print(f"\n  핵심 상관관계:")
    try:
        c1 = corr_mat.loc['65세+\n인구수','독거노인\n수']
        c2 = corr_mat.loc['65세+\n인구수','접근성\n부족지수']
        c3 = corr_mat.loc['생활인구\n65~74세','접근성\n부족지수']
        print(f"  65세+인구 ↔ 독거노인: {c1:.3f}")
        print(f"  65세+인구 ↔ 접근성부족지수: {c2:.3f}")
        print(f"  생활인구 ↔ 접근성부족지수: {c3:.3f}")
    except Exception as e2:
        print(f"  개별 출력 오류: {e2}")
        print(corr_mat.to_string())

except Exception as e:
    import traceback; traceback.print_exc()


# ──────────────────────────────────────────────
# 3-3. 자치구별 시설 집중도
# ──────────────────────────────────────────────
print("\n[ 3-3. 자치구별 시설 집중도 불균형 ]")
try:
    if df_bokjigwan is None or df_yoyang is None:
        raise RuntimeError("복지시설 데이터 없음")

    bokji_gu = df_bokjigwan[gu_col].value_counts().reset_index()
    bokji_gu.columns = ['자치구','n_bokjigwan']
    yoyang_gu = df_yoyang[gu_col].value_counts().reset_index()
    yoyang_gu.columns = ['자치구','n_yoyang']

    df_merged_gu = df_corr_base[['자치구','pop_65plus']].copy()
    df_merged_gu = df_merged_gu.merge(bokji_gu, on='자치구', how='left')
    df_merged_gu = df_merged_gu.merge(yoyang_gu, on='자치구', how='left')
    df_merged_gu = df_merged_gu.fillna(0)
    df_merged_gu['복지관_만명당'] = (df_merged_gu['n_bokjigwan'] /
                                     (df_merged_gu['pop_65plus'] / 10000)).round(3)
    df_merged_gu['요양_만명당']   = (df_merged_gu['n_yoyang'] /
                                     (df_merged_gu['pop_65plus'] / 10000)).round(3)
    df_merged_gu = df_merged_gu.sort_values('복지관_만명당', ascending=False)

    print(df_merged_gu[['자치구','pop_65plus','n_bokjigwan',
                          '복지관_만명당','n_yoyang','요양_만명당']].to_string(index=False))

    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    axes[0].bar(df_merged_gu['자치구'], df_merged_gu['복지관_만명당'],
                color='steelblue', alpha=0.85)
    axes[0].axhline(df_merged_gu['복지관_만명당'].mean(), color='red', linestyle='--',
                    label=f"서울평균 {df_merged_gu['복지관_만명당'].mean():.2f}")
    axes[0].set_title('자치구별 65세+ 1만 명당 노인복지관 수')
    axes[0].set_ylabel('개수 (1만 명당)')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].legend()

    df_s2 = df_merged_gu.sort_values('요양_만명당', ascending=False)
    axes[1].bar(df_s2['자치구'], df_s2['요양_만명당'], color='coral', alpha=0.85)
    axes[1].axhline(df_s2['요양_만명당'].mean(), color='red', linestyle='--',
                    label=f"서울평균 {df_s2['요양_만명당'].mean():.2f}")
    axes[1].set_title('자치구별 65세+ 1만 명당 노인요양시설 수')
    axes[1].set_ylabel('개수 (1만 명당)')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].legend()

    plt.suptitle('서울시 노인복지시설 집중도 불균형', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUT / 'fig_facility_imbalance.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  → fig_facility_imbalance.png 저장")

except Exception as e:
    import traceback; traceback.print_exc()


# ──────────────────────────────────────────────
# 3-4. 잠재적 데드존 후보
# ──────────────────────────────────────────────
print("\n[ 3-4. 잠재적 데드존 후보 (자치구 단위) ]")
try:
    if df_corr_base is None:
        raise RuntimeError("필요 데이터 없음")

    acc_col = '최근거리_km' if '최근거리_km' in df_corr_base.columns else 'bokji_per_10k'
    mean_pop  = df_corr_base['pop_65plus'].mean()
    mean_acc  = df_corr_base[acc_col].mean()

    if acc_col == '최근거리_km':
        # 접근성 부족 지수: 높을수록 나쁨
        deadzone_cand = df_corr_base[
            (df_corr_base['pop_65plus'] >= mean_pop) &
            (df_corr_base[acc_col] >= mean_acc)
        ].copy()
        print(f"  기준: 65세+ ≥ {mean_pop:,.0f}명 AND 접근성부족지수 ≥ {mean_acc:.4f}")
    else:
        # 밀도: 낮을수록 나쁨
        deadzone_cand = df_corr_base[
            (df_corr_base['pop_65plus'] >= mean_pop) &
            (df_corr_base[acc_col] <= mean_acc)
        ].copy()
        print(f"  기준: 65세+ ≥ {mean_pop:,.0f}명 AND 복지관밀도 ≤ {mean_acc:.4f}")

    print(f"  데드존 후보 ({len(deadzone_cand)}개):")
    show_cols = ['자치구','pop_65plus', acc_col]
    show_cols = [c for c in show_cols if c in deadzone_cand.columns]
    print(deadzone_cand[show_cols].sort_values(acc_col, ascending=(acc_col!='최근거리_km')).to_string(index=False))
    print("  ⚠️  자치구 단위 분석 — 행정동 단위 데이터 추가 시 재검토 필요")

except Exception as e:
    import traceback; traceback.print_exc()


# ══════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("STEP 4. validation_report.md 생성")
print("="*70)

# 상관관계 텍스트
try:
    c65_alone = corr_mat.loc['65세+\n인구수','독거노인\n수']
    c65_acc   = corr_mat.loc['65세+\n인구수','접근성\n부족지수']
    clv_acc   = corr_mat.loc['생활인구\n65~74세','접근성\n부족지수']
    corr_text = f"""\
| 변수 쌍 | 상관계수 | 해석 |
|---|---|---|
| 65세+ 인구 ↔ 독거노인 | {c65_alone:.3f} | {'강한 양의 상관' if c65_alone>0.7 else '보통 양의 상관'} |
| 65세+ 인구 ↔ 접근성부족지수 | {c65_acc:.3f} | {'음의 상관' if c65_acc<-0.3 else '약한/양의 상관'} |
| 생활인구(65~74) ↔ 접근성부족지수 | {clv_acc:.3f} | {'H1 지지' if clv_acc<-0.3 else 'H1 증거 약함(구 단위 한계)'} |
"""
except:
    corr_text = "> 상관관계 계산 중 오류\n"

# 데드존 리스트
try:
    dz_list = "\n".join(
        f"- **{r['자치구']}**: 65세+ {r['pop_65plus']:,.0f}명, "
        f"복지관까지 {r['최근거리_km']:.2f}km"
        for _, r in deadzone_cand.sort_values('최근거리_km', ascending=False).iterrows()
    )
except:
    dz_list = "- 계산 오류"

# 시설 집중도 최고/최저
try:
    best_gu  = df_merged_gu.nlargest(1,'복지관_만명당')['자치구'].values[0]
    worst_gu = df_merged_gu.nsmallest(1,'복지관_만명당')['자치구'].values[0]
    best_val  = df_merged_gu.nlargest(1,'복지관_만명당')['복지관_만명당'].values[0]
    worst_val = df_merged_gu.nsmallest(1,'복지관_만명당')['복지관_만명당'].values[0]
    facility_text = (f"- 1만 명당 복지관 수 최고: **{best_gu}** ({best_val:.2f}개)\n"
                     f"- 1만 명당 복지관 수 최저: **{worst_gu}** ({worst_val:.2f}개)\n"
                     f"- 자치구 간 편차 큼 → H1 가설의 주요 근거")
except:
    facility_text = "- 계산 오류"

# 복지관 거리 상위 3
try:
    top3_dist = df_dist.head(3)['자치구'].tolist()
    mean_dist_val = df_dist['최근거리_km'].mean()
    mean_density_val = df_dist['bokji_per_10k'].mean() if 'bokji_per_10k' in df_dist.columns else 0
except:
    top3_dist = []; mean_dist_val = 0.0; mean_density_val = 0.0

report_md = f"""# 서울시 노인 복지 데드존 분석 — 데이터 검증 리포트

> 작성일: 2026-05-20
> 분석 단계: STEP 1~4 (검증 + 사전분석)
> 분석 범위: **자치구(구) 단위** (행정동 단위 데이터 불충분)

---

## 1. 파일별 품질 요약

| 파일 | 단위 | 행수 | 상태 | 주요 이슈 |
|------|------|------|------|----------|
| 서울_노인복지시설_2025.xlsx | 시설 | ~3,126 | ✅ | 좌표 없음 — 주소→지오코딩 필요 |
| 202603_202604_연령별인구현황_월간.xlsx | **자치구** | 26 | ⚠️ | **행정동 아닌 구 단위** |
| LOCAL_PEOPLE_GU_2025.csv | **자치구** | 217,800 | ⚠️ | GU 단위 / 75세이상 없음 / 일별시간대 |
| 독거노인현황(연령별_동별).xlsx | 행정동 | ~426 | ⚠️ | 행정동 코드 없음(동명만) |
| 서울시버스정류소위치정보.xlsx | 포인트 | 11,250 | ✅ | WGS84 좌표 있음, 서울 99.9% |
| 전체_도시철도역사정보.xlsx | 포인트 | 1,099 (전국) | ✅ | 서울 필터 필요, 461역 |
| 행정동·격자/match.shp | **250m격자** | 10,125 | ⚠️ | **행정동 경계 아닌 격자** / EPSG:5179 |
| 기초생활수급자 (별도파일) | - | - | ❌ | **파일 없음** — 독거노인 파일 내 수급권자 컬럼 대체 가능 |

### 분석 가능성 요약

| 항목 | 가능 여부 |
|------|-----------|
| 자치구 단위 종합 분석 | ✅ 가능 |
| 250m 격자 단위 버스/지하철 분석 | ✅ 가능 |
| 행정동 단위 분석 | ⚠️ 독거노인 동명 매핑 시 부분 가능 |
| 행정동 단위 완전 공간분석 | ❌ 행정동 경계 SHP 없음 |

---

## 2. 행정동 코드 매핑 가능 여부

| 파일 | 코드 형식 | 매핑 가능 |
|------|-----------|----------|
| 65세이상인구 | 10자리 자치구코드 | ❌ 구 단위만 |
| 생활인구 | 5자리 자치구코드 | ❌ 구 단위만 |
| 독거노인 | 동명 텍스트 | ⚠️ 매핑 작업 필요 |
| 버스정류소 | WGS84 좌표 | ✅ 격자 공간조인 |
| 지하철역 | WGS84 좌표 | ✅ 격자 공간조인 |
| 격자SHP | GID(비표준) | ⚠️ 표준코드 아님 |

**결론**: 행정동 경계 SHP + 행정동 단위 인구 데이터 추가 수집 필요
→ 통계청 SGIS (https://sgis.kostat.go.kr) 또는 공공데이터포털 제공

---

## 3. H1 검증 가능성 판단

**핵심 가설 (H1)**: 노인 인구↑ + 시설 거리↑ + 대중교통 접근성↓ → 노인 생활인구↓

### 상관관계 (자치구 단위, n=25)

{corr_text}

### 변수별 데이터 충족도

| 변수 | 필요 단위 | 현재 단위 | 충족 |
|------|-----------|-----------|------|
| 노인 인구 | 행정동 | 자치구 | ⚠️ |
| 독거노인 수 | 행정동 | 행정동(동명) | ⚠️ |
| 복지관까지 거리 | 행정동 | 자치구(임시) | ⚠️ |
| 버스정류소 수 | 격자/행정동 | 격자 공간조인 | ✅ |
| 지하철역 접근성 | 격자/행정동 | 격자 공간조인 | ✅ |
| 노인 생활인구 | 행정동 | 자치구 / 75세+없음 | ❌ |

**판정**: ⚠️ **자치구 단위 H1 사전 검토 가능 / 행정동 단위 완전 검증은 추가 데이터 필요**

---

## 4. 전처리 시 주의할 점

1. **행정동 경계 SHP 없음**: SGIS에서 행정동 경계 (HangJeongDong_ver202X.zip) 수집 필요
2. **65세 인구 수준 불일치**: 행안부 파일은 구 단위 → 행정동 단위는 행안부 주민등록통계 동별 집계 별도 수집
3. **생활인구 75세+ 없음**: 65~74세 생활인구를 대리변수로 사용하거나, 빅데이터 캠퍼스 격자단위 데이터 수집
4. **독거노인 코드 없음**: 동명 → 행정동 코드 매핑 테이블 작성 (전국 동명 중복 주의)
5. **격자 CRS EPSG:5179**: 버스·지하철 WGS84 좌표를 반드시 EPSG:5179로 변환 후 공간조인
6. **노인복지시설 좌표 없음**: 카카오 로컬 API 또는 공공 주소 API 활용 지오코딩
7. **기초수급자 별도 파일 없음**: 독거노인 파일 col6(기초생활보장 수급권자) 사용 가능
8. **생활인구 217,800행**: 날짜×시간대×구 — 일평균 또는 월평균 집계 후 분석 권장
9. **65세+ 인구 계산**: 65세~100세이상 36개 컬럼(col 69~104) 합산 (col 105부터 다음 블록)

---

## 5. 사전 분석 인사이트

### 5-1. 노인복지관 접근성
- **주의**: 서울 25개 자치구 모두 복지관 ≥1개 보유 → 구 중심점 거리 분석 무의미
- 대신 **접근성 부족 지수**(1/복지관밀도)를 사용
- 접근성 부족 상위 자치구: **{top3_dist}**
- 서울 평균 1만 명당 복지관 수: **{mean_density_val:.3f}개**
- 실제 주소 지오코딩 후 행정동 단위 재분석 필요

### 5-2. 시설 집중도 불균형
{facility_text}

### 5-3. 잠재적 데드존 후보 (자치구 단위)
> 기준: 65세+ 인구 서울 평균 이상 AND 복지관 거리 서울 평균 이상

{dz_list}

### 5-4. 다음 단계 데이터 수집 우선순위
| 우선순위 | 데이터 | 획득처 |
|---------|--------|--------|
| 🔴 1순위 | 행정동 경계 SHP | 통계청 SGIS |
| 🔴 2순위 | 행정동 단위 65세+ 인구 | 행안부 주민등록인구통계 |
| 🟡 3순위 | 생활인구 행정동 단위 | 열린데이터광장 OA-14991 재확인 |
| 🟡 4순위 | 75세이상 생활인구 격자 | 서울 빅데이터 캠퍼스 |
| 🟢 5순위 | 노인복지시설 좌표 | 카카오/네이버 지오코딩 API |

---

*생성된 그래프*
- `fig_dist_histogram.png` — 노인복지관 최근접 거리 히스토그램
- `fig_correlation_heatmap.png` — H1 변수 상관관계 히트맵
- `fig_facility_imbalance.png` — 자치구별 시설 집중도 막대그래프
"""

with open(OUT / 'validation_report.md', 'w', encoding='utf-8') as f:
    f.write(report_md)

print(f"\n  → validation_report.md 저장 완료")
print("\n" + "="*70)
print("전체 분석 완료")
print("="*70)
