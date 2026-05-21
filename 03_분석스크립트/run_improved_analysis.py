import pandas as pd
import geopandas as gpd
import numpy as np
import os
import re
from datetime import datetime
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from shapely.geometry import Point

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

# === STEP 1. 폴더 생성 ===
today = datetime.now().strftime("%Y%m%d")
folder = f"regression_improved_{today}"
os.makedirs(folder, exist_ok=True)
print(f"결과 폴더: {folder}/")

# === STEP 2. 생활인구 주간 시간대 필터링 ===
print("\n=== STEP 2 시작 ===")

# 행정동 단위 생활인구 로드
# 파일: 통계자료/생활인구_행정동별_시간대별_2026년4월.csv
df_hdong_pop = pd.read_csv('통계자료/생활인구_행정동별_시간대별_2026년4월.csv', index_col=False)
df_hdong_pop['행정동코드'] = df_hdong_pop['행정동코드'].astype(int).astype(str)

# 격자별(?) 생활인구 로드 (사용자가 언급한 파일)
df_grid_pop_file = pd.read_csv('격자별_생활인구_65세이상.csv')
df_grid_pop_file['행정동코드'] = df_grid_pop_file['행정동코드'].astype(int).astype(str)

def filter_daytime(df):
    # 시간대구분 컬럼 (0~23)
    # 9시~17시 필터링
    return df[(df['시간대구분'] >= 9) & (df['시간대구분'] <= 17)]

# 필터링 전 평균 (65세 이상 합계)
elderly_cols = ['남자65세부터69세생활인구수', '남자70세이상생활인구수', '여자65세부터69세생활인구수', '여자70세이상생활인구수']
df_hdong_pop['elderly_pop_sum'] = df_hdong_pop[elderly_cols].sum(axis=1)
total_avg_pre = df_hdong_pop['elderly_pop_sum'].mean()

# 필터링 후 평균
df_hdong_pop_day = filter_daytime(df_hdong_pop)
total_avg_post = df_hdong_pop_day['elderly_pop_sum'].mean()

print(f"행정동 전체 평균 {total_avg_pre:.1f} → 주간 평균 {total_avg_post:.1f}")

# 행정동별 주간 평균 집계
df_hdong_pop_final = df_hdong_pop_day.groupby('행정동코드')['elderly_pop_sum'].mean().reset_index()
df_hdong_pop_final.rename(columns={'elderly_pop_sum': 'y_living_pop'}, inplace=True)

# 격자별 데이터 (현재 Hdong 레벨인 것으로 확인됨)
df_grid_pop_day = filter_daytime(df_grid_pop_file)
grid_avg_pre = df_grid_pop_file['65세이상'].mean()
grid_avg_post = df_grid_pop_day['65세이상'].mean()
print(f"격자(파일) 전체 평균 {grid_avg_pre:.1f} → 주간 평균 {grid_avg_post:.1f}")

# === STEP 3. PCA로 접근성 지수 합성 ===
print("\n=== STEP 3 시작 ===")

# 기존 분석에서 계산했던 거리 데이터 로드 (필요시 재계산)
# 여기서는 편의상 다시 계산 로직 포함
gdf_hdong_shp = gpd.read_file('통계자료/행정동·격자/BND_ADM_DONG_PG/BND_ADM_DONG_PG.shp', encoding='euc-kr')
gdf_hdong_shp = gdf_hdong_shp.to_crs(epsg=5179)
gdf_hdong_shp['centroid'] = gdf_hdong_shp.geometry.centroid

# 시설 데이터 로드
df_welfare_raw = pd.read_excel('통계자료/서울_복지시설_접근성분석용.xlsx')
gdf_welfare = gpd.GeoDataFrame(df_welfare_raw, geometry=gpd.points_from_xy(df_welfare_raw['경도'], df_welfare_raw['위도']), crs="EPSG:4324")
gdf_welfare = gdf_welfare.to_crs(epsg=5179)

df_bus_raw = pd.read_excel('통계자료/버스정류소_위치정보_2026년5월.xlsx')
gdf_bus = gpd.GeoDataFrame(df_bus_raw, geometry=gpd.points_from_xy(df_bus_raw['X좌표'], df_bus_raw['Y좌표']), crs="EPSG:4324")
gdf_bus = gdf_bus.to_crs(epsg=5179)

df_subway_raw = pd.read_csv('서울_지하철역_좌표.csv')
gdf_subway = gpd.GeoDataFrame(df_subway_raw, geometry=gpd.points_from_xy(df_subway_raw['역경도'], df_subway_raw['역위도']), crs="EPSG:4324")
gdf_subway = gdf_subway.to_crs(epsg=5179)

def get_dists(target_gdf, name_prefix=""):
    print(f"{name_prefix} 거리 계산 중...")
    target_gdf['dist_welfare'] = target_gdf['centroid'].apply(lambda x: gdf_welfare.distance(x).min())
    target_gdf['bus_count_500m'] = target_gdf['centroid'].apply(lambda x: (gdf_bus.distance(x) <= 500).sum())
    target_gdf['dist_subway'] = target_gdf['centroid'].apply(lambda x: gdf_subway.distance(x).min())
    return target_gdf

gdf_hdong_shp = get_dists(gdf_hdong_shp, "행정동")

# PCA 수행
pca_cols = ['dist_welfare', 'bus_count_500m', 'dist_subway']
scaler = StandardScaler()
X_pca = scaler.fit_transform(gdf_hdong_shp[pca_cols])

pca = PCA(n_components=3)
pca_features = pca.fit_transform(X_pca)

print(f"각 주성분 설명 분산 비율: {pca.explained_variance_ratio_}")
print(f"PC1 Loadings: {dict(zip(pca_cols, pca.components_[0]))}")

# PC1을 종합_접근성지수로 사용
# dist_welfare, dist_subway가 크고 bus_count가 작을 때 PC1이 커지도록 부호 조정
# 보통 Loading 부호를 보고 결정.
# dist_welfare loading이 양수이면, 값이 클수록 접근성 나쁨.
loading_welfare = pca.components_[0][0]
if loading_welfare < 0:
    gdf_hdong_shp['access_index'] = -pca_features[:, 0]
else:
    gdf_hdong_shp['access_index'] = pca_features[:, 0]

# 시각화 저장
plt.figure(figsize=(8, 5))
plt.bar(['PC1', 'PC2', 'PC3'], pca.explained_variance_ratio_)
plt.title('PCA Explained Variance Ratio')
plt.savefig(f"{folder}/pca_explained_variance.png")
plt.close()

# === STEP 4-A. 행정동 단위 회귀 (개선) ===
print("\n=== STEP 4-A 시작 ===")

# 병합을 위해 이름 정규화
def normalize_name(name):
    if not isinstance(name, str): return name
    return re.sub(r'[^가-힣0-9a-zA-Z]', '', name)

df_elderly = pd.read_csv('행정동별_65세이상인구.csv')
df_elderly['norm_name'] = df_elderly['행정동명'].apply(normalize_name)
df_elderly['행정동코드_8'] = df_elderly['행정동코드'].astype(str).str[:8]

df_alone = pd.read_csv('독거노인_행정동코드포함.csv')
df_alone['행정동코드_8'] = df_alone['행정동코드'].astype(str).str[:8]

gdf_hdong_shp['norm_name'] = gdf_hdong_shp['ADM_NM'].apply(normalize_name)

# 병합
df_hdong_final = gdf_hdong_shp.merge(df_elderly, on='norm_name', how='inner')
df_hdong_final = df_hdong_final.merge(df_hdong_pop_final, left_on='행정동코드_8', right_on='행정동코드', how='inner')
df_hdong_final = df_hdong_final.merge(df_alone, on='행정동코드_8', how='inner', suffixes=('', '_alone'))

X_cols_hdong = ['access_index', '65세이상인구', '독거노인_합계']
Y_col = 'y_living_pop'

df_analysis_hdong = df_hdong_final[[Y_col] + X_cols_hdong].dropna()
print(f"행정동 분석 데이터 수: {len(df_analysis_hdong)}")

# 표준화
X_hdong_scaled = StandardScaler().fit_transform(df_analysis_hdong[X_cols_hdong])
df_X_hdong = pd.DataFrame(sm.add_constant(X_hdong_scaled), columns=['const'] + X_cols_hdong)

model_hdong = sm.OLS(df_analysis_hdong[Y_col].values, df_X_hdong).fit()
print(model_hdong.summary())

# VIF
vif_hdong = [variance_inflation_factor(df_X_hdong.values, i) for i in range(1, len(df_X_hdong.columns))]
print(f"행정동 VIF: {dict(zip(X_cols_hdong, vif_hdong))}")

# === STEP 4-B. 250m 격자 단위 회귀 ===
print("\n=== STEP 4-B 시작 ===")

gdf_grid = gpd.read_file('통계자료/행정동·격자/서울_250m격자.shp')
if gdf_grid.crs is None: gdf_grid.set_crs(epsg=5179, inplace=True)
else: gdf_grid = gdf_grid.to_crs(epsg=5179)
gdf_grid['centroid'] = gdf_grid.geometry.centroid

# 격자가 어느 행정동에 속하는지 공간 조인
# df_hdong_final은 GeoDataFrame 형태여야 함
gdf_hdong_final_for_join = gpd.GeoDataFrame(df_hdong_final[['norm_name', '행정동코드_8', 'geometry', 'access_index']], crs=gdf_hdong_shp.crs)
gdf_grid_joined = gpd.sjoin(gdf_grid, gdf_hdong_final_for_join, how='inner', predicate='intersects')

# 행정동별 격자 수 계산
grid_counts = gdf_grid_joined.groupby('행정동코드_8').size().reset_index(name='grid_count')

# 격자별 거리 및 PCA 지수 계산
# (시간 관계상 모든 격자 계산은 오래 걸릴 수 있으므로 샘플링하거나 최적화 필요하지만 일단 수행)
gdf_grid_sample = gdf_grid_joined # 전체 수행
gdf_grid_sample = get_dists(gdf_grid_sample, "격자")

# 격자 PCA (동일한 scaler와 pca 적용)
X_grid_pca = scaler.transform(gdf_grid_sample[pca_cols])
pca_features_grid = pca.transform(X_grid_pca)
if loading_welfare < 0:
    gdf_grid_sample['access_index_grid'] = -pca_features_grid[:, 0]
else:
    gdf_grid_sample['access_index_grid'] = pca_features_grid[:, 0]

# 인구 데이터 disaggregation
df_hdong_data = df_hdong_final[['행정동코드_8', 'y_living_pop', '65세이상인구', '독거노인_합계']]
gdf_grid_final = gdf_grid_sample.merge(df_hdong_data, on='행정동코드_8', how='inner')
gdf_grid_final = gdf_grid_final.merge(grid_counts, on='행정동코드_8', how='inner')

# 균등 배분
gdf_grid_final['y_grid'] = gdf_grid_final['y_living_pop'] / gdf_grid_final['grid_count']
gdf_grid_final['pop_grid'] = gdf_grid_final['65세이상인구'] / gdf_grid_final['grid_count']
gdf_grid_final['alone_grid'] = gdf_grid_final['독거노인_합계'] / gdf_grid_final['grid_count']

X_cols_grid = ['access_index_grid', 'pop_grid', 'alone_grid']
Y_col_grid = 'y_grid'

df_analysis_grid = gdf_grid_final[[Y_col_grid] + X_cols_grid].dropna()
X_grid_scaled = StandardScaler().fit_transform(df_analysis_grid[X_cols_grid])
df_X_grid = pd.DataFrame(sm.add_constant(X_grid_scaled), columns=['const'] + X_cols_grid)

model_grid = sm.OLS(df_analysis_grid[Y_col_grid].values, df_X_grid).fit()
print(model_grid.summary())

# === STEP 5 & 6. 결과 비교 및 저장 ===
print("\n=== STEP 5 & 6 시작 ===")

# 상관관계 히트맵
plt.figure(figsize=(10, 8))
sns.heatmap(df_analysis_hdong.corr(), annot=True, cmap='coolwarm')
plt.title('Correlation Heatmap (Hdong)')
plt.savefig(f"{folder}/correlation_heatmap.png")
plt.close()

# 잔차 플롯
plt.figure(figsize=(10, 6))
plt.scatter(model_hdong.fittedvalues, model_hdong.resid)
plt.axhline(0, color='r', linestyle='--')
plt.title('Residual Plot (Hdong)')
plt.savefig(f"{folder}/residual_plot_hdong.png")
plt.close()

plt.figure(figsize=(10, 6))
plt.scatter(model_grid.fittedvalues, model_grid.resid)
plt.axhline(0, color='r', linestyle='--')
plt.title('Residual Plot (Grid)')
plt.savefig(f"{folder}/residual_plot_grid.png")
plt.close()

# 보고서 작성
report = f"""# 회귀분석 개선 결과 보고서

## 1. 개선 사항 요약
- **시간대 필터링**: 주간 시간대(09:00~17:00) 생활인구만 사용하여 신호 희석 방지
- **다중공선성 해소**: PCA를 통해 거리 관련 3개 변수를 '종합_접근성지수'로 통합
- **공간 해상도 확대**: 행정동 단위와 250m 격자 단위 분석 병행

## 2. 모델 비교

| 항목 | 행정동(이전) | 행정동(개선) | 격자(신규) |
|------|------------|------------|----------|
| 표본 수 | 306 | {len(df_analysis_hdong)} | {len(df_analysis_grid)} |
| Adj-R² | 0.569 | {model_hdong.rsquared_adj:.4f} | {model_grid.rsquared_adj:.4f} |
| 접근성 p-value | 0.225 | {model_hdong.pvalues['access_index']:.4f} | {model_grid.pvalues['access_index_grid']:.4f} |
| VIF 최댓값 | 12.66 | {max(vif_hdong):.2f} | {max([variance_inflation_factor(df_X_grid.values, i) for i in range(1, len(df_X_grid.columns))]):.2f} |
| H1 지지 여부 | ❌ | {"✅" if model_hdong.params['access_index'] < 0 and model_hdong.pvalues['access_index'] < 0.05 else "❌"} | {"✅" if model_grid.params['access_index_grid'] < 0 and model_grid.pvalues['access_index_grid'] < 0.05 else "❌"} |

*참고: 종합_접근성지수는 값이 클수록 접근성이 나쁜(거리가 먼) 방향으로 설정됨.*

## 3. H1 검증 결과 해석
- **행정동 모델**: 접근성지수의 영향력이 {"유의미함" if model_hdong.pvalues['access_index'] < 0.05 else "유의미하지 않음"}.
- **격자 모델**: 접근성지수의 영향력이 {"유의미함" if model_grid.pvalues['access_index_grid'] < 0.05 else "유의미하지 않음"}.
- **결론**: { "공간 단위를 세분화함에 따라 접근성의 효과가 더 뚜렷하게 나타남" if model_grid.rsquared_adj > model_hdong.rsquared_adj else "공간 단위 세분화에도 불구하고 인구 밀집도가 지배적인 요인임" }.
"""

with open(f"{folder}/regression_improved_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n모든 분석 완료! 결과가 {folder} 폴더에 저장되었습니다.")
