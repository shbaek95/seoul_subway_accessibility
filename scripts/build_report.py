"""실제 집계 결과만으로 보고서·그림·웹 요약을 만듭니다."""
import json
import shutil
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *

PROF='https://github.com/jslee-gses/code/tree/main/lecture05_urban_planning_index'
SGIS='https://sgis.mods.go.kr/view/pss/dataProvdIntrcn'

def records(frame):
    return json.loads(frame.drop(columns='geometry',errors='ignore').to_json(orient='records',force_ascii=False))

def main():
    result=gpd.read_file(PROCESSED/'results.gpkg')
    valid=result.loc[result.accessibility.notna()].copy()
    qa=json.loads((ROOT/'reports/validation.json').read_text(encoding='utf-8'))
    high_d=valid.nlargest(3,'density');high_a=valid.nlargest(3,'accessibility');low_a=valid.nsmallest(3,'accessibility')
    plus=valid.nlargest(4,'percentile_gap');minus=valid.nsmallest(4,'percentile_gap')
    names=lambda df: ', '.join(df.name)
    p=plus.iloc[0];m=minus.iloc[0]
    findings=[{'label':'관찰 01 · 상위 지역','title':'밀도가 높은 곳과 접근성이 높은 곳','text':f'역 밀도 상위는 {names(high_d)}입니다. 인구가중 접근성 상위는 {names(high_a)}입니다. 각각 공급의 면적 대비 집중과 공개 인구가 누리는 여러 역의 기여도를 나타냅니다.'},
    {'label':'관찰 02 · 평가 차이','title':'동 내부 역 수만으로 설명되지 않는 차이','text':f'{p["name"]}의 역 밀도는 {p.density:.2f}역/㎢, 접근성은 {p.accessibility:.3f}점이며, 접근성 백분위가 밀도보다 {p.percentile_gap:.1f}%p 높습니다. 반대 방향의 큰 차이는 {m["name"]}({m.percentile_gap:.1f}%p)에서 나타납니다.'},
    {'label':'관찰 03 · 낮은 값과 해석','title':'0점과 자료 없음을 구분해서 읽기','text':f'접근성 하위는 {names(low_a)}입니다. 연결 가능한 보행망에서 30분 안에 역이 없는 공개 인구 {qa["zero_access_known_population"]:,.0f}명도 분모에 포함했습니다. 인구 기록이 없는 {qa["missing_population_grids"]:,}개 격자를 실제 0명이라고 해석하지 않습니다.'}]
    summary={'findings':findings,'gap_examples':records(pd.concat([plus,minus])),'density_high':records(high_d),'accessibility_high':records(high_a),'accessibility_low':records(low_a)}
    save_json(PUBLIC/'summary.json',summary)
    download='https://github.com/jslee-gses/code/tree/d04422c9a8341df75795956db6bdec4aaa9a61e0/lecture05_urban_planning_index'
    datasets=[
    {'name':'2024년 100m 격자 인구 (다사)','provider':'국가데이터처(구 통계청) SGIS / 교수님 수업 배포본','reference_date':'2024년 (CSV year 필드)','download_date':DATE,'crs':'비공간 CSV, GRID_CD로 100m 경계와 결합','spatial_unit':'100m 격자','fields':'year, GRID_CD, stat_code, population','source_url':SGIS,'download_url':download+'/grid','license':'SGIS 자료 활용 시 출처 명시·활용 결과 제출 조건. 수업 배포본의 별도 재배포 허락은 명시되지 않아 원자료는 공개 저장소에 올리지 않음.','processing':'to_in_001만 선택, 1:1 결합. 결측을 0으로 채우지 않음. 공개값 0과 자료 없음 구분. SGIS 비밀보호(BSCA/N/A)로 공개 인구는 참값과 다를 수 있음.'},
    {'name':'서울 100m 격자 경계','provider':'SGIS 경계체계 / 교수님 수업 가공본','reference_date':'2025년 (파일명 기준, 파일 내 별도 기준일 없음)','download_date':DATE,'crs':'원본 EPSG:4326 → 분석 EPSG:5179','spatial_unit':'100m 격자','fields':'GRID_CD, geometry','source_url':SGIS,'download_url':download+'/grid','license':'SGIS 출처 표시. 서울 추출·가공본의 제작 경위와 별도 이용허락은 확인되지 않음. 원본 전체를 재배포하지 않음.','processing':'코드 고유성·유효 도형 검사. 투영좌표계 중심점을 행정동에 배정. 서울 밖 중심점 격자 제외.'},
    {'name':'서울 행정동 경계 (bnd_dong_seoul)','provider':'국가데이터처 SGIS / 교수님 서울 추출본','reference_date':'2025-06-30 (BASE_DATE=20250630)','download_date':DATE,'crs':'EPSG:5179 (UTM-K, GRS80), 웹 공개본 EPSG:4326','spatial_unit':'행정동 426개','fields':'BASE_DATE, ADM_CD(8자리 SGIS), ADM_NM, geometry','source_url':SGIS,'download_url':download+'/shp','license':'SGIS 출처 표시·자료 활용 조건. 행정동 집계 지도만 공개하며 전체 경계 원본은 별도 재배포하지 않음.','processing':'ADM_CD 고유성·유효성 검사. 코드로 집계 결과 1:1 결합. 웹 지도만 15m 단순화(지표 계산 면적은 원도형 사용).'},
    {'name':'서울시 역사마스터 정보','provider':'서울특별시 TOPIS / 교수님 수업 CSV','reference_date':'수업 CSV 자체의 기준일은 확인되지 않음. 제공기관 페이지 갱신일 2026-10-22와 CSV의 기준일을 동일시하지 않음.','download_date':DATE,'crs':'EPSG:4326 위도·경도 → EPSG:5179','spatial_unit':'호선별 역사 기록 → 중복 정리한 역군','fields':'역사_ID, 역사명, 호선, 위도, 경도','source_url':'https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do','download_url':download+'/data','license':'공공누리 제1유형: 출처표시, 상업적 이용·변경 가능.','processing':'좌표 범위·ID 고유성 검사. 같은 정규명이며 500m 이내이거나 동일 좌표인 기록을 군집화. 서울/서울역, 이수/총신대입구 별칭 반영. 군내 실제 좌표 medoid를 대표점으로 선택. GTX 삼성 미정차 기록 1행 제외. 서울+2.5km 역을 접근성 계산에 포함.'},
    {'name':'OpenStreetMap 보행 도로망','provider':'OpenStreetMap contributors / Overpass API / OSMnx','reference_date':DATE+' 수집 당시 OSM 스냅샷 (2024 인구와 시점 다름)','download_date':DATE,'crs':'원본 EPSG:4326; 연결거리 EPSG:5179, OSMnx length 미터','spatial_unit':'도로 노드·간선, 서울 경계+2.5km','fields':'OSM node id, x, y, length, highway, access, foot','source_url':'https://www.openstreetmap.org/copyright','download_url':'https://overpass-api.de/api/interpreter','license':'ODbL 1.0, © OpenStreetMap contributors. 공개 지도·결과에 출처 표시. 원시 도로망은 로컬 캐시로만 보존.','processing':'walk 필터, 모든 연결 성분 유지, 도로 중간 노드 보존. 평행 간선은 최단 length. 최근접 노드 연결거리 포함. 300m 초과 연결은 실패, 정상 망의 역 미도달은 점수 0.'}]
    save_json(PUBLIC/'sources.json',{'datasets':datasets,'note':'본 분석은 2024 인구·2025 경계·기준일 미상 역 CSV·2026-11-01 수집 OSM을 결합한 수업 분석이며, 2026년 전체 현황이나 공식 교통 접근성 통계가 아닙니다.'})
    shutil.copy2(ROOT/'reports/validation.json',PUBLIC/'validation.json')
    lines=['# 역이 많은 동은 접근성도 좋을까?','', '서울 행정동별 지하철역 밀도와 공개 격자 인구가중 중력형 접근성 비교', '', '작성: 백승현 · 스마트도시데이터분석 과제 3','', '## 연구 질문','서울에서 지하철역이 조밀하게 분포한 행정동과, 주민이 지하철역에 접근하기 쉬운 행정동은 일치하는가?','', '## 실제 계산 결과',f'- 유효 행정동 {qa["valid_dongs"]}개 / 총 426개. Spearman 순위상관 {qa["spearman"]:.4f}.',f'- 인구 가중 분모는 확인 가능한 2024 공개 인구 {qa["known_population"]:,.0f}명이다. 인구 누락 격자의 규모는 알 수 없으므로 실제 전체 주민 평균으로 단정할 수 없다.',f'- 서울 역군 {qa["stations_in_seoul"]}개와 경계 밖 버퍼 역군 {qa["stations_outside_seoul_in_buffer"]}개를 사용했다.','']
    for f in findings:lines += ['### '+f['title'],f['text'],'']
    lines+=['## 지표 간 차이에 대한 해석','두 지표의 상관은 동일한 평가를 보장하지 않는다. 밀도는 동 내부 역 수와 면적에만 반응하지만 접근성은 격자별 보행경로와 여러 역의 거리, 공개 인구의 위치를 반영한다. 따라서 작은 동의 높은 밀도와, 인접 동의 역에 가까운 인구의 높은 접근성은 서로 다른 현상을 측정한다. 이는 지표 정의에서 확인되는 설명이며, 특정 지역의 격차가 이 중 어느 원인으로 얼마나 발생했는지는 추가 분해 분석이 필요하다.','', '## 계산식과 설정','D_d = N_d / Area_d (역/㎢). 면적은 EPSG:5179에서 계산.','A_i = Σ_j exp(−ln(2)/10 × t_ij), 단 t_ij ≤ 30분. 역 가중치 S_j=1.','A_d = Σ_i(P_i × A_i) / Σ_i P_i. 공개 인구가 있는 격자 기준. 0점 인구도 분모에 포함.','보행속도 4km/h. 격자 중심→최근접 도로 노드→역 최근접 노드→역 대표점의 거리 합계를 시간으로 환산. 연결거리는 최대300m. 서울 밖2.5km 버퍼 사용.','백분위 차이는 유효 행정동의 동점 평균 순위/N×100에서 접근성 백분위−밀도 백분위이며, 서로 다른 단위를 직접 빼지 않는다.','', '## 검증',f'총인구 코드 선택 후 1:1 결합, 행정동 426코드 고유, 원시역 784행에서 미정차1행 제외 후 역군655개. 손계산 단위검증5개 통과. 실제12개 격자를 역방향 Dijkstra로 검증한 최대오차 {qa["sample_path_max_error"]:.3g}. 연결실패 양수 인구 {qa["failed_known_population"]:,.0f}명, 역 연결 실패{qa["station_snap_failures"]}개. 결측·무한대·0값 검사와 재실행 기록은 validation.json·README 참조.','', '## 분석 한계','- 인구는2024, 행정동 경계는2025-06-30, 격자경계2025, 역 CSV 기준일 미상, OSM은2026-11-01 수집으로 시점이 다르다. 최신 역의 완전성이나 모든 역의 운영 상태를 보장하지 않는다.','- 인구 누락은0으로 대체하지 않았다. SGIS 비밀보호 처리와 미기록 격자로 실제 인구 총량과 차이가 있다. 공개0도 실제 무인구로 단정하지 않는다.','- 100m 중심점 기준 배정으로 동 경계 격자에 오차가 있다. 중심점이서울밖인 격자는제외하며 면적비율로 인구를 추정하지 않는다.','- 도로망 연결은 최단 직선 연결선으로 근사한다. 담장·하천 통과 가능성, 미등록길, 계단·보행제한의 태깅 오류, 실제 출입구·지하통로·경사·신호대기는 확인되지 않았다.','- 환승역 정규명과500m거리 기반 역군은 실제 모든 환승 복합체와 일치하지 않을 수 있다. 대표점은 관측된 좌표이며 새 좌표를 추정하지 않았다.','- 2.5km 버퍼는 경계 절단을 줄이지만 원자료 역 누락과 우회 경로, OSM 시점 차이를 완전히 해소하지 않는다.','- β, 속도, 30분상한에 대한 민감도 분석은 별도로 수행하지 않았다. 개별 보행자의 실측 통행시간이나 거주 만족도·주택가격·인과 효과를 나타내지 않는다.','', '## 자료 출처']
    for d in datasets:lines+=['- '+d['name']+': '+d['source_url']+' / '+d['reference_date']+' / '+d['license']]
    lines+=['','## 과제 원문',PROF+'/03_accessibility.ipynb','Cloudflare로 발행하여 Notion 과제3에 제출. 특정 파일명·파일형식·마감일은 확인되지 않음.']
    report='\n'.join(lines)+'\n'
    (PUBLIC/'report.md').write_text(report,encoding='utf-8')
    (ROOT/'reports/analysis_report.md').write_text(report,encoding='utf-8')
    # 보고서에 첨부할 독립적인 고해상도 그림을 실제 결과로 생성합니다.
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10,'savefig.facecolor':'white'})
    figures=ROOT/'reports/figures';figures.mkdir(exist_ok=True)
    for key,title,unit,cmap in [('density','서울 행정동별 지하철역 밀도','역/㎢','GnBu'),('accessibility','서울 행정동별 인구가중 중력형 접근성','무차원 점수','YlOrBr')]:
        fig,ax=plt.subplots(figsize=(10,9));result.plot(column=key,cmap=cmap,legend=True,ax=ax,edgecolor='white',linewidth=.25,missing_kwds={'color':'lightgrey','hatch':'///','label':'계산 불가'},legend_kwds={'label':unit,'shrink':.6});ax.set_title(title+'\n2024 공개 인구 · 2025 경계 · 기준일 미상 역 CSV · 2026 OSM',fontsize=14);ax.set_axis_off();fig.text(.05,.025,'출처: 국가데이터처 SGIS · 서울특별시 TOPIS · © OpenStreetMap contributors (ODbL) / 백승현 분석',fontsize=8);fig.savefig(figures/(key+'_map.png'),dpi=180,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,6));ax.scatter(valid.density,valid.accessibility,c='#087f81',s=20,alpha=.6);ax.set(xlabel='지하철역 밀도 (역/㎢)',ylabel='인구가중 중력형 접근성 (무차원)',title=f'역 밀도와 주민 접근성 · Spearman ρ={qa["spearman"]:.3f}');ax.grid(alpha=.15)
    for _,r in pd.concat([plus.head(2),minus.head(2)]).iterrows():ax.annotate(r['name'],(r.density,r.accessibility),fontsize=8,xytext=(4,5),textcoords='offset points')
    fig.text(.1,.01,'출처: SGIS(2024 인구·2025 경계), 서울특별시 역사마스터, OSM(2026-11-01) / 백승현 분석',fontsize=8);fig.tight_layout(rect=[0,.03,1,1]);fig.savefig(figures/'scatter.png',dpi=180);plt.close(fig)
    examples=pd.concat([plus,minus]).sort_values('percentile_gap');fig,ax=plt.subplots(figsize=(10,6));ax.barh(examples.name,examples.percentile_gap,color=['#087f81' if x>=0 else '#c05d25' for x in examples.percentile_gap]);ax.axvline(0,color='#555',lw=.7);ax.set(xlabel='접근성 백분위 - 역 밀도 백분위 (%p)',title='두 지표의 평가가 달라지는 지역');fig.text(.1,.01,'기준: 유효 지역 내 동점 평균 순위/N×100. 출처: 동일 원자료, 백승현 분석',fontsize=8);fig.tight_layout(rect=[0,.03,1,1]);fig.savefig(figures/'percentile_gap.png',dpi=180);plt.close(fig)
    print('보고서·웹 요약·그림4개 생성 완료',flush=True)

if __name__=='__main__':main()
