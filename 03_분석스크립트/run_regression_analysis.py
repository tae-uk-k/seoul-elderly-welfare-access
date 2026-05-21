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
from shapely.geometry import Point

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rc('axes', unicode_minus=False)

# 폴더 설정
today = "20260521"
folder_name = f"regression_{today}"
os.makedirs(folder_name, exist_ok=True)

def normalize_name(name):
    if not isinstance(name, str): return name
    # 특수문자 제거 및 공백 제거
    return re.sub(r'[^가-힣0-9a-zA-Z]', '', name)

print(f"## STEP 1. 데이터 로드 및 병합")

# 1.1 행정동별 65세 이상 인구
df_elderly = pd.read_csv('행정동별_65세이상인구.csv')
df_elderly['행정동코드_8'] = df_elderly['행정동코드'].astype(str).str[:8]
df_elderly['norm_name'] = df_elderly['행정동명'].apply(normalize_name)

# 1.2 행정동 경계 SHP
gdf_hdong = gpd.read_file('통계자료/행정동·격자/BND_ADM_DONG_PG/BND_ADM_DONG_PG.shp', encoding='euc-kr')
gdf_hdong['norm_name'] = gdf_hdong['ADM_NM'].apply(normalize_name)
if gdf_hdong.crs is None:
    gdf_hdong.set_crs(epsg=5179, inplace=True)
else:
    gdf_hdong = gdf_hdong.to_crs(epsg=5179)
gdf_hdong['centroid'] = gdf_hdong.geometry.centroid

# SHP와 Elderly를 이름으로 먼저 병합하여 코드 매핑 생성
# (SHP의 ADM_CD는 비표준일 수 있으므로 Elderly의 행정동코드_8을 기준으로 사용)
gdf_merged_base = gdf_hdong.merge(df_elderly, on='norm_name', how='inner')
print(f"SHP-Elderly 이름 기준 병합 성공: {len(gdf_merged_base)}개 동")

# 1.3 생활인구 (종속변수)
df_pop = pd.read_csv('통계자료/생활인구_행정동별_시간대별_2026년4월.csv', index_col=False)
df_pop['행정동코드'] = df_pop['행정동코드'].astype(int).astype(str)
elderly_cols = ['남자65세부터69세생활인구수', '남자70세이상생활인구수', '여자65세부터69세생활인구수', '여자70세이상생활인구수']
df_pop['elderly_pop_sum'] = df_pop[elderly_cols].sum(axis=1)
df_pop_avg = df_pop.groupby('행정동코드')['elderly_pop_sum'].mean().reset_index()
df_pop_avg.rename(columns={'elderly_pop_sum': 'avg_elderly_living_pop'}, inplace=True)

# 1.4 독거노인
df_alone = pd.read_csv('독거노인_행정동코드포함.csv')
df_alone['행정동코드_8'] = df_alone['행정동코드'].astype(str).str[:8]

# 최종 병합 (gdf_merged_base의 행정동코드_8 기준)
df_merged = gdf_merged_base.merge(df_pop_avg, left_on='행정동코드_8', right_on='행정동코드', how='inner')
df_merged = df_merged.merge(df_alone, on='행정동코드_8', how='inner', suffixes=('', '_alone'))

print(f"최종 병합 완료 (생활인구 포함): {len(df_merged)}개 동")

if len(df_merged) == 0:
    print("Error: 병합된 데이터가 없습니다. 코드를 다시 확인해 주세요.")
    exit()

print(f"\n## STEP 2. 독립변수 생성")

# 2.1 노인복지관 거리
df_welfare = pd.read_excel('통계자료/서울_복지시설_접근성분석용.xlsx')
gdf_welfare = gpd.GeoDataFrame(df_welfare, geometry=gpd.points_from_xy(df_welfare['경도'], df_welfare['위도']), crs="EPSG:4324")
gdf_welfare = gdf_welfare.to_crs(epsg=5179)

# 2.2 버스정류소 수
df_bus = pd.read_excel('통계자료/버스정류소_위치정보_2026년5월.xlsx')
gdf_bus = gpd.GeoDataFrame(df_bus, geometry=gpd.points_from_xy(df_bus['X좌표'], df_bus['Y좌표']), crs="EPSG:4324")
gdf_bus = gdf_bus.to_crs(epsg=5179)

# 2.3 지하철역 거리
df_subway = pd.read_csv('서울_지하철역_좌표.csv')
gdf_subway = gpd.GeoDataFrame(df_subway, geometry=gpd.points_from_xy(df_subway['역경도'], df_subway['역위도']), crs="EPSG:4324")
gdf_subway = gdf_subway.to_crs(epsg=5179)

def get_min_dist(point, other_gdf):
    return other_gdf.distance(point).min()

def count_within_dist(point, other_gdf, dist=500):
    return (other_gdf.distance(point) <= dist).sum()

print("거리 변수 계산 중... (시간이 다소 소요될 수 있습니다)")
df_merged['dist_welfare'] = df_merged['centroid'].apply(lambda x: get_min_dist(x, gdf_welfare))
df_merged['bus_count_500m'] = df_merged['centroid'].apply(lambda x: count_within_dist(x, gdf_bus, 500))
df_merged['dist_subway'] = df_merged['centroid'].apply(lambda x: get_min_dist(x, gdf_subway))

dist_cols = ['dist_welfare', 'bus_count_500m', 'dist_subway']
print(df_merged[dist_cols].describe().loc[['mean', 'min', 'max']])

print(f"\n## STEP 3. 회귀분석 실행")

X_cols = ['dist_welfare', 'bus_count_500m', 'dist_subway', '65세이상인구', '독거노인_합계']
Y_col = 'avg_elderly_living_pop'

df_final = df_merged[[Y_col] + X_cols].dropna()
print(f"분석에 사용된 행 수: {len(df_final)}")

corr = df_final.corr()
plt.figure(figsize=(10, 8))
sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
plt.title('변수 간 상관관계 히트맵')
plt.savefig(f"{folder_name}/correlation_heatmap.png")
plt.close()

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_final[X_cols])
df_X_scaled = pd.DataFrame(X_scaled, columns=X_cols)

X = sm.add_constant(df_X_scaled)
model = sm.OLS(df_final[Y_col].values, X).fit()
print(model.summary())

print(f"\n## STEP 4. 결과 해석 및 저장")

vif_data = pd.DataFrame()
vif_data["feature"] = X_cols
vif_data["VIF"] = [variance_inflation_factor(df_X_scaled.values, i) for i in range(len(X_cols))]

plt.figure(figsize=(10, 6))
plt.scatter(model.fittedvalues, model.resid)
plt.axhline(y=0, color='r', linestyle='--')
plt.xlabel('Fitted Values')
plt.ylabel('Residuals')
plt.title('Residual Plot')
plt.savefig(f"{folder_name}/residual_plot.png")
plt.close()

with open(f"{folder_name}/regression_result.md", "w", encoding="utf-8") as f:
    f.write("# 회귀분석 결과 보고서\n\n")
    f.write(f"일자: {datetime.now().strftime('%Y-%m-%d')}\n\n")
    f.write("## 1. 모델 요약\n")
    f.write(f"- 분석 데이터 수: {len(df_final)}개 행정동\n")
    f.write(f"- 결정계수 (R-squared): {model.rsquared:.4f}\n")
    f.write(f"- 수정된 결정계수 (Adj. R-squared): {model.rsquared_adj:.4f}\n")
    f.write(f"  - 해석: 본 모델은 노인 생활인구 변화의 약 {model.rsquared_adj*100:.1f}%를 설명함.\n\n")
    f.write("## 2. 변수별 계수 및 유의성\n")
    f.write("| 변수 | 계수(Coef) | p-value | 유의성 | 가설일치 |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for col in X_cols:
        coef = model.params[col]
        p = model.pvalues[col]
        sig = "유의" if p < 0.05 else "불유의"
        h_match = "-"
        if col == 'dist_welfare':
            h_match = "일치" if coef < 0 else "불일치"
        elif col == 'bus_count_500m':
            h_match = "일치" if coef > 0 else "불일치"
        f.write(f"| {col} | {coef:.4f} | {p:.4f} | {sig} | {h_match} |\n")
    f.write("\n## 3. 다중공선성 체크 (VIF)\n")
    f.write("| 변수 | VIF |\n")
    f.write("| --- | --- |\n")
    for i, row in vif_data.iterrows():
        warn = " (경고: 다중공선성 높음)" if row['VIF'] > 10 else ""
        f.write(f"| {row['feature']} | {row['VIF']:.2f}{warn} |\n")
    f.write("\n## 4. 종합 해석\n")
    f.write("1. **생활인구 영향 요인**: ")
    sig_vars = [col for col in X_cols if model.pvalues[col] < 0.05]
    if sig_vars:
        f.write(f"{', '.join(sig_vars)} 변수가 통계적으로 유의한 영향을 미치는 것으로 나타남.\n")
    else:
        f.write("통계적으로 유의한 변수가 발견되지 않음.\n")
    if 'dist_welfare' in model.params:
        if model.params['dist_welfare'] < 0 and model.pvalues['dist_welfare'] < 0.05:
            f.write("2. **복지 접근성**: 복지관 거리가 가까울수록 생활인구가 증가하는 경향이 확인됨 (가설 지지).\n")
        elif model.params['dist_welfare'] > 0 and model.pvalues['dist_welfare'] < 0.05:
            f.write("2. **복지 접근성**: 복지관 거리가 멀수록 생활인구가 증가하는 예상 밖의 결과가 나타남.\n")
        else:
            f.write("2. **복지 접근성**: 복지관 거리와 생활인구 간의 유의미한 관계가 확인되지 않음.\n")

print(f"\n분석 완료! 결과가 {folder_name} 폴더에 저장되었습니다.")
