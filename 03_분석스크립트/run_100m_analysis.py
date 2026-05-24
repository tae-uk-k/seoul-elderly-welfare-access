"""
서울시 복지 데드존 분석 — 100m 격자 단위 재분석
행정동 생활인구를 SGIS 100m 격자 인구 비율로 분해하여 100m 단위 회귀분석 수행
"""

import os, time, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

BASE = Path("/mnt/c/Users/xodnr/Desktop/서울시 복지 데드존 분석")
DATA  = BASE / "01_원본데이터"
PROC  = BASE / "02_가공데이터"
GEO   = BASE / "05_지도_공간자료"
today = datetime.now().strftime("%Y%m%d")
OUT   = BASE / "04_분석결과" / f"analysis_100m_{today}"
OUT.mkdir(parents=True, exist_ok=True)
print(f"결과 폴더: {OUT}/")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 1 시작 : 파일 확인 및 로드 ===")
print("="*60)
t0 = time.time()

# 1-1. 행정동 경계 SHP (서울만 필터)
print("\n[1-1] 행정동 경계 SHP 로드...")
gdf_hdong = gpd.read_file(
    GEO / "BND_ADM_DONG_PG/BND_ADM_DONG_PG.shp", encoding='euc-kr'
)
gdf_hdong = gdf_hdong[gdf_hdong['ADM_CD'].astype(str).str.startswith('11')].copy()
gdf_hdong = gdf_hdong.to_crs(epsg=5179)
gdf_hdong['행정동코드_8'] = gdf_hdong['ADM_CD'].astype(str).str[:8]
print(f"  서울 행정동 수: {len(gdf_hdong)}, CRS: {gdf_hdong.crs}")

# 서울 경계 bbox (100m 격자 필터용)
seoul_bbox = gdf_hdong.total_bounds  # [minx, miny, maxx, maxy]
print(f"  서울 bbox (EPSG:5179): {seoul_bbox.astype(int).tolist()}")

# 1-2. SGIS 100m 격자 SHP (서울 영역만 로드)
print("\n[1-2] SGIS 100m 격자 SHP 로드 (서울 bbox 필터)...")
t1 = time.time()
gdf_100m = gpd.read_file(
    DATA / "_grid_border_grid_2025_grid_다사_grid_다사/grid_다사_100M.shp",
    bbox=tuple(seoul_bbox)   # bbox로 pre-filter → 속도 향상
)
gdf_100m = gdf_100m.to_crs(epsg=5179)
print(f"  bbox 필터 후 격자 수: {len(gdf_100m)}, CRS: {gdf_100m.crs}")

# 서울 행정동 경계 내 격자만 정밀 필터
seoul_union = gdf_hdong.union_all()
gdf_100m['centroid'] = gdf_100m.geometry.centroid
mask = gdf_100m['centroid'].within(seoul_union)
gdf_100m = gdf_100m[mask].copy()
print(f"  서울 경계 내 100m 격자 수: {len(gdf_100m)}")
print(f"  소요: {time.time()-t1:.1f}초")

# 1-3. SGIS 100m 격자 인구 CSV
print("\n[1-3] SGIS 100m 인구 CSV 로드...")
df_sgis = pd.read_csv(
    DATA / "_census_reqdoc_1779542403896/2024년_인구_다사_100M.csv",
    encoding='cp949', header=None,
    names=['year', 'grid_cd', 'age_group', 'pop']
)
df_sgis['pop'] = pd.to_numeric(df_sgis['pop'], errors='coerce').fillna(0).astype(int)
# to_in_001 = 총인구 (남/여 합계)
df_pop_sgis = df_sgis[df_sgis['age_group'] == 'to_in_001'][['grid_cd', 'pop']].copy()
df_pop_sgis.columns = ['GRID_CD', 'total_pop']
# 서울 격자만 유지
seoul_grids = set(gdf_100m['GRID_CD'].tolist())
df_pop_sgis = df_pop_sgis[df_pop_sgis['GRID_CD'].isin(seoul_grids)].copy()
print(f"  총인구(to_in_001) 격자 수: {len(df_pop_sgis)}")
print(f"  서울 해당 격자 수: {len(df_pop_sgis)}")
print(f"  서울 총인구 합계: {df_pop_sgis['total_pop'].sum():,}명")

# 1-4. 행정동 생활인구 (65세이상, 주간)
# 원본 raw 파일(생활인구_행정동별_시간대별_2026년4월.csv)은 첫 번째 데이터 행에
# 쉼표가 하나 더 있어 C 파서가 에러를 발생시킴 → 이미 65세이상 컬럼이 계산된
# 전처리 파일(격자별_생활인구_65세이상.csv)을 직접 사용
print("\n[1-4] 행정동 생활인구 로드 (전처리 파일 사용)...")
df_lpop = pd.read_csv(PROC / "격자별_생활인구_65세이상.csv")
# 주간(9~17시)만 사용
df_lpop_day = df_lpop[(df_lpop['시간대구분'] >= 9) & (df_lpop['시간대구분'] <= 17)]
df_lpop_avg = (df_lpop_day
               .groupby('행정동코드')['65세이상']
               .mean()
               .reset_index()
               .rename(columns={'65세이상': 'y_living_pop', '행정동코드': '행정동코드_full'}))
df_lpop_avg['행정동코드_8'] = df_lpop_avg['행정동코드_full'].astype(str).str[:8]
print(f"  행정동 수: {len(df_lpop_avg)}, 주간 65세+ 평균 생활인구: {df_lpop_avg['y_living_pop'].mean():.1f}명")

# 1-5. 행정동별 65세이상인구
print("\n[1-5] 행정동별 65세이상인구 로드...")
df_elderly = pd.read_csv(PROC / "행정동별_65세이상인구.csv")
df_elderly['행정동코드_8'] = df_elderly['행정동코드'].astype(str).str[:8]
print(f"  행 수: {len(df_elderly)}, 컬럼: {df_elderly.columns.tolist()}")

# 1-6. 독거노인
print("\n[1-6] 독거노인 로드...")
df_alone = pd.read_csv(PROC / "독거노인_행정동코드포함.csv")
df_alone['행정동코드_8'] = df_alone['행정동코드'].astype(str).str[:8]
print(f"  행 수: {len(df_alone)}, 컬럼: {df_alone.columns.tolist()}")

# 1-7. 복지시설
print("\n[1-7] 복지시설 로드...")
df_welfare = pd.read_excel(PROC / "서울_복지시설_접근성분석용.xlsx")
df_welfare = df_welfare.dropna(subset=['위도', '경도'])
gdf_welfare = gpd.GeoDataFrame(
    df_welfare,
    geometry=gpd.points_from_xy(df_welfare['경도'], df_welfare['위도']),
    crs='EPSG:4326'
).to_crs(epsg=5179)
print(f"  복지시설 수: {len(gdf_welfare)}, CRS: {gdf_welfare.crs}")

# 1-8. 버스정류소
print("\n[1-8] 버스정류소 로드...")
df_bus = pd.read_excel(DATA / "버스정류소_위치정보_2026년5월.xlsx")
df_bus['X좌표'] = pd.to_numeric(df_bus['X좌표'], errors='coerce')
df_bus['Y좌표'] = pd.to_numeric(df_bus['Y좌표'], errors='coerce')
df_bus = df_bus.dropna(subset=['X좌표', 'Y좌표'])
gdf_bus = gpd.GeoDataFrame(
    df_bus,
    geometry=gpd.points_from_xy(df_bus['X좌표'], df_bus['Y좌표']),
    crs='EPSG:4326'
).to_crs(epsg=5179)
in_s = gdf_bus.geometry.within(seoul_union)
gdf_bus = gdf_bus[in_s].copy()
print(f"  서울 버스정류소 수: {len(gdf_bus)}, CRS: {gdf_bus.crs}")

# 1-9. 지하철역
print("\n[1-9] 지하철역 로드...")
df_subway = pd.read_csv(PROC / "서울_지하철역_좌표.csv")
df_subway = df_subway.dropna(subset=['역위도', '역경도'])
gdf_subway = gpd.GeoDataFrame(
    df_subway,
    geometry=gpd.points_from_xy(df_subway['역경도'], df_subway['역위도']),
    crs='EPSG:4326'
).to_crs(epsg=5179)
print(f"  지하철역 수: {len(gdf_subway)}, CRS: {gdf_subway.crs}")

print(f"\n  STEP 1 완료 ({time.time()-t0:.1f}초)")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 2 시작 : 행정동 생활인구 → 100m 격자 분해 ===")
print("="*60)
t0 = time.time()

# 2-1. 100m 격자 → 행정동 매핑 (공간 조인)
print("\n[2-1] 100m 격자 → 행정동 공간 조인...")
t1 = time.time()
gdf_100m_pts = gdf_100m[['GRID_CD', 'centroid']].copy()
gdf_100m_pts = gpd.GeoDataFrame(gdf_100m_pts, geometry='centroid', crs='EPSG:5179')

joined = gpd.sjoin(
    gdf_100m_pts,
    gdf_hdong[['행정동코드_8', 'geometry']],
    how='left',
    predicate='within'
)
# 하나의 격자가 여러 행정동에 걸칠 경우 첫 번째만 사용
joined = joined[~joined.index.duplicated(keep='first')]
gdf_100m['행정동코드_8'] = joined['행정동코드_8'].values
n_matched = gdf_100m['행정동코드_8'].notna().sum()
print(f"  행정동 매칭 완료: {n_matched}/{len(gdf_100m)} ({n_matched/len(gdf_100m)*100:.1f}%)")
print(f"  소요: {time.time()-t1:.1f}초")

# 2-2. SGIS 인구 가중치 계산
print("\n[2-2] SGIS 인구 가중치 계산...")
# 격자에 SGIS 인구 병합
gdf_100m = gdf_100m.merge(df_pop_sgis, on='GRID_CD', how='left')
gdf_100m['total_pop'] = gdf_100m['total_pop'].fillna(0)

# 행정동별 총인구 합계
hdong_pop_sum = (gdf_100m
                 .groupby('행정동코드_8')['total_pop']
                 .sum()
                 .reset_index()
                 .rename(columns={'total_pop': 'hdong_total_pop'}))
gdf_100m = gdf_100m.merge(hdong_pop_sum, on='행정동코드_8', how='left')

# 가중치 계산
# 행정동 내 모든 격자 인구가 0이면 균등배분
gdf_100m['hdong_grid_count'] = gdf_100m.groupby('행정동코드_8')['GRID_CD'].transform('count')
gdf_100m['weight'] = np.where(
    gdf_100m['hdong_total_pop'] > 0,
    gdf_100m['total_pop'] / gdf_100m['hdong_total_pop'],
    1.0 / gdf_100m['hdong_grid_count']          # 균등배분 대체
)
print(f"  가중치 범위: {gdf_100m['weight'].min():.6f} ~ {gdf_100m['weight'].max():.6f}")
n_uniform = (gdf_100m['hdong_total_pop'] == 0).sum()
print(f"  균등배분 적용 격자 (행정동 인구=0): {n_uniform}개")

# 2-3. 생활인구 분배
print("\n[2-3] 생활인구 → 100m 격자 분배...")
gdf_100m = gdf_100m.merge(
    df_lpop_avg[['행정동코드_8', 'y_living_pop']],
    on='행정동코드_8', how='left'
)
gdf_100m['y_living_100m'] = gdf_100m['y_living_pop'] * gdf_100m['weight']
gdf_100m['y_living_100m'] = gdf_100m['y_living_100m'].fillna(0)

print(f"  100m 격자 생활인구 기술통계:")
print(gdf_100m['y_living_100m'].describe().round(2).to_string())

# 검증: 100m 합산 vs 원본 행정동 합계 비교 (샘플)
print("\n  [검증] 행정동별 100m 합산 vs 원본 생활인구 비교 (상위 5개 행정동):")
check = (gdf_100m.groupby('행정동코드_8')['y_living_100m']
         .sum()
         .reset_index()
         .rename(columns={'y_living_100m': '100m_합산'}))
check = check.merge(df_lpop_avg[['행정동코드_8', 'y_living_pop']], on='행정동코드_8')
check['오차율(%)'] = ((check['100m_합산'] - check['y_living_pop']).abs()
                      / check['y_living_pop'].replace(0, np.nan) * 100).round(2)
print(check.head(5).to_string(index=False))
max_err = check['오차율(%)'].max()
ok = "✅ 정상" if max_err < 5 else f"⚠️ 최대 오차 {max_err:.2f}%"
print(f"  최대 오차율: {max_err:.2f}% → {ok}")

print(f"\n  STEP 2 완료 ({time.time()-t0:.1f}초)")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 3 시작 : 100m 격자별 독립변수 생성 (거리·PCA) ===")
print("="*60)
t0 = time.time()

# 유효 격자만 사용 (행정동 매칭 + 생활인구 있음)
gdf_valid = gdf_100m[gdf_100m['행정동코드_8'].notna()].copy()
print(f"  유효 격자 수: {len(gdf_valid)}")

centroids = gdf_valid['centroid'].values  # shapely Point 배열

# 3-1. 복지관까지 최단 거리
print("\n[3-1] 복지관까지 최단 거리 계산...")
t1 = time.time()
welfare_pts = np.array([[g.x, g.y] for g in gdf_welfare.geometry])
centroid_pts = np.array([[c.x, c.y] for c in centroids])

# 벡터화: 각 격자 vs 모든 복지관 거리 행렬 → 최솟값
# 메모리 절약을 위해 청크 처리
CHUNK = 5000
dist_welfare = np.empty(len(centroid_pts))
for i in range(0, len(centroid_pts), CHUNK):
    chunk = centroid_pts[i:i+CHUNK]
    diffs = chunk[:, np.newaxis, :] - welfare_pts[np.newaxis, :, :]  # (C, W, 2)
    dist_welfare[i:i+CHUNK] = np.sqrt((diffs**2).sum(axis=2)).min(axis=1)

gdf_valid['dist_welfare'] = dist_welfare
print(f"  완료: 평균 {dist_welfare.mean():.0f}m, 최대 {dist_welfare.max():.0f}m ({time.time()-t1:.1f}초)")

# 3-2. 500m 내 버스정류소 수
print("\n[3-2] 500m 내 버스정류소 수 계산 (공간 인덱스 활용)...")
t1 = time.time()
bus_pts = np.array([[g.x, g.y] for g in gdf_bus.geometry])
bus_count = np.empty(len(centroid_pts), dtype=int)
for i in range(0, len(centroid_pts), CHUNK):
    chunk = centroid_pts[i:i+CHUNK]
    diffs = chunk[:, np.newaxis, :] - bus_pts[np.newaxis, :, :]
    dists = np.sqrt((diffs**2).sum(axis=2))
    bus_count[i:i+CHUNK] = (dists <= 500).sum(axis=1)

gdf_valid['bus_count_500m'] = bus_count
print(f"  완료: 평균 {bus_count.mean():.1f}개, 최대 {bus_count.max()}개 ({time.time()-t1:.1f}초)")

# 3-3. 지하철역까지 최단 거리
print("\n[3-3] 지하철역까지 최단 거리 계산...")
t1 = time.time()
subway_pts = np.array([[g.x, g.y] for g in gdf_subway.geometry])
dist_subway = np.empty(len(centroid_pts))
for i in range(0, len(centroid_pts), CHUNK):
    chunk = centroid_pts[i:i+CHUNK]
    diffs = chunk[:, np.newaxis, :] - subway_pts[np.newaxis, :, :]
    dist_subway[i:i+CHUNK] = np.sqrt((diffs**2).sum(axis=2)).min(axis=1)

gdf_valid['dist_subway'] = dist_subway
print(f"  완료: 평균 {dist_subway.mean():.0f}m, 최대 {dist_subway.max():.0f}m ({time.time()-t1:.1f}초)")

# 3-4. PCA → 종합_접근성지수
print("\n[3-4] PCA 수행 → 종합_접근성지수 생성...")
pca_cols = ['dist_welfare', 'bus_count_500m', 'dist_subway']
df_pca_in = gdf_valid[pca_cols].dropna()
valid_idx = df_pca_in.index

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_pca_in)

pca = PCA(n_components=3)
pca_features = pca.fit_transform(X_scaled)

print(f"  설명 분산 비율: {pca.explained_variance_ratio_.round(3).tolist()}")
print(f"  PC1 loadings: { {k: round(v,3) for k, v in zip(pca_cols, pca.components_[0])} }")

# 부호 확인: dist_welfare loading이 양수 → 값 클수록 접근성 나쁨 → 그대로 사용
loading_welfare = pca.components_[0][0]
sign = 1 if loading_welfare > 0 else -1
gdf_valid.loc[valid_idx, 'access_index'] = sign * pca_features[:, 0]
print(f"  부호 {'반전 없음' if sign == 1 else '반전 적용'} (dist_welfare loading={loading_welfare:.3f})")

# PCA 설명 분산 그래프 저장
plt.figure(figsize=(6, 4))
plt.bar(['PC1', 'PC2', 'PC3'], pca.explained_variance_ratio_, color='steelblue', alpha=0.85)
plt.title('PCA Explained Variance Ratio (100m 격자)')
plt.ylabel('설명 분산 비율')
plt.tight_layout()
plt.savefig(OUT / 'pca_variance_100m.png', dpi=150)
plt.close()

print(f"\n  STEP 3 완료 ({time.time()-t0:.1f}초)")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 4 시작 : 통제변수 매핑 (65세이상인구·독거노인) ===")
print("="*60)
t0 = time.time()

# 행정동 단위 65세이상인구·독거노인을 SGIS 가중치로 100m 격자에 배분
df_ctrl = df_elderly[['행정동코드_8', '65세이상인구']].merge(
    df_alone[['행정동코드_8', '독거노인_합계']],
    on='행정동코드_8', how='outer'
).fillna(0)

gdf_valid = gdf_valid.merge(df_ctrl, on='행정동코드_8', how='left')

gdf_valid['pop65_100m']   = gdf_valid['65세이상인구'] * gdf_valid['weight']
gdf_valid['alone_100m']   = gdf_valid['독거노인_합계'] * gdf_valid['weight']

print(f"  65세이상인구 배분 완료: 평균 {gdf_valid['pop65_100m'].mean():.2f}명/격자")
print(f"  독거노인 배분 완료:     평균 {gdf_valid['alone_100m'].mean():.2f}명/격자")
print(f"  STEP 4 완료 ({time.time()-t0:.1f}초)")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 5 시작 : 100m 단위 OLS 회귀분석 ===")
print("="*60)
t0 = time.time()

Y_col = 'y_living_100m'
X_cols = ['access_index', 'pop65_100m', 'alone_100m']

df_reg = gdf_valid[[Y_col] + X_cols].dropna()
df_reg = df_reg[df_reg[Y_col] > 0]   # Y=0인 비거주 격자 제외
print(f"\n  분석 표본 수: {len(df_reg)}개 격자")

# 상관관계 히트맵
plt.figure(figsize=(7, 6))
corr_df = df_reg.rename(columns={
    'y_living_100m': '생활인구\n65세+',
    'access_index':  '접근성지수',
    'pop65_100m':    '65세이상인구',
    'alone_100m':    '독거노인'
})
sns.heatmap(corr_df.corr(), annot=True, fmt='.3f', cmap='coolwarm',
            vmin=-1, vmax=1, square=True, linewidths=0.5)
plt.title('변수 간 상관관계 히트맵 (100m 격자)')
plt.tight_layout()
plt.savefig(OUT / 'correlation_heatmap_100m.png', dpi=150)
plt.close()

# 표준화 후 OLS
scaler_reg = StandardScaler()
X_scaled_reg = scaler_reg.fit_transform(df_reg[X_cols])
df_X = pd.DataFrame(sm.add_constant(X_scaled_reg), columns=['const'] + X_cols)

model = sm.OLS(df_reg[Y_col].values, df_X).fit()
print("\n  [회귀분석 결과 요약]")
print(f"  표본 수:     {model.nobs:.0f}")
print(f"  Adj-R²:      {model.rsquared_adj:.4f}")
print(f"  F-statistic: {model.fvalue:.2f} (p={model.f_pvalue:.4e})")
print()
for col in X_cols:
    coef = model.params[col]
    pval = model.pvalues[col]
    sig  = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "n.s."
    print(f"  {col:<18}: coef={coef:+.4f}, p={pval:.4f} {sig}")

# VIF
vif_vals = [variance_inflation_factor(df_X.values, i+1) for i in range(len(X_cols))]
print(f"\n  VIF: { {k: round(v,2) for k, v in zip(X_cols, vif_vals)} }")

# 잔차 플롯
plt.figure(figsize=(8, 5))
plt.scatter(model.fittedvalues, model.resid, alpha=0.3, s=3, color='steelblue')
plt.axhline(0, color='red', linestyle='--')
plt.xlabel('Fitted Values')
plt.ylabel('Residuals')
plt.title('Residual Plot (100m 격자)')
plt.tight_layout()
plt.savefig(OUT / 'residual_plot_100m.png', dpi=150)
plt.close()

print(f"\n  STEP 5 완료 ({time.time()-t0:.1f}초)")

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 6 시작 : 기존 결과와 비교 ===")
print("="*60)

acc_p   = model.pvalues['access_index']
acc_coe = model.params['access_index']
h1_ok   = "✅" if (acc_p < 0.05 and acc_coe < 0) else "❌"

comparison = pd.DataFrame({
    '항목':       ['표본 수', 'Adj-R²', '접근성 p-value', 'H1 지지'],
    '행정동(개선)': ['306', '0.294', '0.027', '✅'],
    '250m 격자':  ['13,004', '0.484', '0.000', '✅'],
    '100m 격자':  [
        f"{model.nobs:,.0f}",
        f"{model.rsquared_adj:.3f}",
        f"{acc_p:.4f}",
        h1_ok
    ],
})
print()
print(comparison.to_string(index=False))

# ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("=== STEP 7 시작 : 결과 저장 ===")
print("="*60)
t0 = time.time()

# 7-1. 분석 데이터 CSV
save_cols = ['GRID_CD', '행정동코드_8', 'y_living_100m', 'access_index',
             'pop65_100m', 'alone_100m', 'dist_welfare', 'bus_count_500m',
             'dist_subway', 'total_pop', 'weight']
save_cols = [c for c in save_cols if c in gdf_valid.columns]
df_save = gdf_valid[save_cols].dropna(subset=['access_index'])
df_save.to_csv(OUT / '100m_격자_분석데이터.csv', index=False, encoding='utf-8-sig')
print(f"  100m_격자_분석데이터.csv 저장 ({len(df_save)}행)")

# 7-2. 회귀 결과 마크다운
vif_txt = "\n".join(
    f"| {k} | {v:.2f}{' (⚠️ 다중공선성)' if v > 10 else ''} |"
    for k, v in zip(X_cols, vif_vals)
)
coef_txt = "\n".join(
    f"| {col} | {model.params[col]:+.4f} | {model.pvalues[col]:.4f} | "
    f"{'유의' if model.pvalues[col] < 0.05 else '불유의'} | "
    f"{'✅ 일치' if (col=='access_index' and model.params[col]<0) or col!='access_index' else '❌ 불일치'} |"
    for col in X_cols
)

report = f"""# 100m 격자 단위 회귀분석 결과 보고서

생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 1. 분석 개요

| 항목 | 내용 |
|------|------|
| 분석 단위 | SGIS 100m × 100m 격자 |
| 종속변수(Y) | 100m 격자별 65세+ 생활인구 (주간 9~17시 평균, 행정동→SGIS 가중치 분해) |
| 독립변수(X) | 종합_접근성지수(PCA), 65세이상인구, 독거노인수 |
| 분석 표본 | {model.nobs:,.0f}개 격자 (Y>0인 거주 격자만) |

## 2. 생활인구 분해 방법

- 출처: 행정동 단위 생활인구(2026년 4월, 주간 평균)
- 가중치: SGIS 100m 격자 총인구(`to_in_001`) / 행정동 내 합계
- 행정동 인구 전체가 0인 경우: 균등배분으로 대체

## 3. PCA (종합_접근성지수)

| 주성분 | 설명 분산 비율 |
|--------|-------------|
| PC1 | {pca.explained_variance_ratio_[0]:.3f} |
| PC2 | {pca.explained_variance_ratio_[1]:.3f} |
| PC3 | {pca.explained_variance_ratio_[2]:.3f} |

PC1 Loadings: { {k: round(v,3) for k, v in zip(pca_cols, pca.components_[0])} }
→ 값이 클수록 접근성이 나쁜(거리가 멀고 버스가 적은) 지역

## 4. OLS 회귀분석 결과

- Adj-R²: **{model.rsquared_adj:.4f}**
- F-statistic: {model.fvalue:.2f} (p={model.f_pvalue:.4e})

| 변수 | 계수 | p-value | 유의성 | H1 일치 |
|------|------|---------|--------|---------|
{coef_txt}

## 5. 다중공선성 (VIF)

| 변수 | VIF |
|------|-----|
{vif_txt}

## 6. 기존 분석과 비교

| 항목 | 행정동(개선) | 250m 격자 | 100m 격자(신규) |
|------|------------|----------|----------------|
| 표본 수 | 306 | 13,004 | {model.nobs:,.0f} |
| Adj-R² | 0.294 | 0.484 | {model.rsquared_adj:.3f} |
| 접근성 p-value | 0.027 | 0.000 | {acc_p:.4f} |
| H1 지지 | ✅ | ✅ | {h1_ok} |

## 7. 결론

접근성지수 계수: **{model.params['access_index']:+.4f}** (p={acc_p:.4f})

{"→ 복지 접근성이 낮을수록 노인 생활인구가 감소한다는 H1 가설이 100m 격자 단위에서도 통계적으로 지지됨." if h1_ok == "✅" else "→ 100m 격자 단위에서 H1 가설이 통계적으로 지지되지 않음. 추가 분석 필요."}
"""

with open(OUT / '100m_회귀결과.md', 'w', encoding='utf-8') as f:
    f.write(report)
print(f"  100m_회귀결과.md 저장 완료")
print(f"  correlation_heatmap_100m.png 저장 완료")
print(f"  residual_plot_100m.png 저장 완료")
print(f"  pca_variance_100m.png 저장 완료")
print(f"\n  STEP 7 완료 ({time.time()-t0:.1f}초)")

print("\n" + "="*60)
print("전체 분석 완료")
print(f"결과 폴더: {OUT}/")
print("="*60)
