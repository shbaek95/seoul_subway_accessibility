"""총인구 1:1 결합, 행정동 배정, 환승역 중복 제거를 수행합니다."""
import re
import hashlib
import json
import pandas as pd
import numpy as np
import geopandas as gpd
from scipy.spatial import cKDTree
from common import *

GU = dict(zip(['11010','11020','11030','11040','11050','11060','11070','11080','11090','11100','11110','11120','11130','11140','11150','11160','11170','11180','11190','11200','11210','11220','11230','11240','11250'],
              ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']))

def assign_once(points, dong):
    # intersects는 경계 위 점도 포함합니다. 두 동에 걸리면 코드 오름차순 1곳에만 배정합니다.
    joined = gpd.sjoin(points, dong[['ADM_CD','geometry']], how='left', predicate='intersects')
    multi = int(joined.index.duplicated().sum())
    joined = joined.sort_values('ADM_CD', na_position='last').loc[lambda x: ~x.index.duplicated()]
    joined = joined.sort_index().drop(columns='index_right')
    assert len(joined) == len(points)
    return joined, multi

def normalize_name(value):
    # 이름만으로 합치지 않고, 아래에서 500m 이내 좌표 조건도 함께 검사합니다.
    value = str(value).strip()
    if value in ['서울역','서울']: return '서울'
    if value.startswith('총신대입구') or value == '이수': return '이수(총신대입구)'
    return re.sub(r'\([^)]*\)', '', value).strip()

def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    dong = gpd.read_file(RAW/'bnd_dong_seoul.shp').to_crs(CRS)
    assert dong.ADM_CD.is_unique and dong.geometry.is_valid.all()
    dong['gu'] = dong.ADM_CD.str[:5].map(GU)
    assert dong.gu.notna().all()
    dong['name'] = dong.gu + ' ' + dong.ADM_NM
    dong['area_km2'] = dong.area / 1e6
    assert (dong.area_km2 > 0).all()
    grid = gpd.read_file(RAW/'seoul_100m_grid_2025.geojson').to_crs(CRS)
    assert grid.GRID_CD.is_unique and grid.geometry.is_valid.all()
    p = pd.read_csv(RAW/'2024년_인구_다사_100M.csv', encoding='cp949', header=None,
                    names=['year','GRID_CD','stat_code','population'], dtype={'GRID_CD':str})
    total = p.loc[p.stat_code.eq('to_in_001'), ['GRID_CD','population']]
    assert total.GRID_CD.is_unique
    grid = grid.merge(total, how='left', on='GRID_CD', validate='one_to_one')
    grid['population'] = pd.to_numeric(grid.population, errors='coerce')
    assert (grid.population.dropna() >= 0).all()
    # 누락 인구를 0으로 만들지 않습니다. 수업 예제의 fillna(0)는 사용하지 않습니다.
    grid['population_status'] = np.select([grid.population.isna(),grid.population.eq(0)],['자료 없음','공개값 0'],default='공개값 양수')
    grid.geometry = grid.geometry.centroid
    all_grid_count = len(grid)
    grid, grid_ties = assign_once(grid, dong)
    outside_grid = grid.loc[grid.ADM_CD.isna()]
    grid = grid.loc[grid.ADM_CD.notna()].reset_index(drop=True)
    source = pd.read_csv(RAW/'서울시 역사마스터 정보.csv', encoding='cp949')
    assert source['역사_ID'].is_unique
    source['norm'] = source['역사명'].map(normalize_name)
    valid = source['위도'].between(33,39) & source['경도'].between(124,132)
    stations = gpd.GeoDataFrame(source.loc[valid].copy(),geometry=gpd.points_from_xy(source.loc[valid,'경도'],source.loc[valid,'위도']),crs=4326).to_crs(CRS)
    # GTX 삼성은 공식 안내상 미정차역입니다. 호선별 동일명 정차역(2호선 삼성)은 유지합니다.
    not_operating = stations['역사명'].eq('삼성') & stations['호선'].str.contains('광역급행')
    excluded = stations.loc[not_operating].drop(columns='geometry')
    excluded.to_csv(PROCESSED/'excluded_stations.csv', index=False, encoding='utf-8-sig')
    stations = stations.loc[~not_operating].copy()
    # 동일 좌표 또는 동일 정규명+500m 이내인 레코드를 한 역군으로 묶습니다.
    # 연결된 군은 실제 원자료 중 다른 점까지 거리합이 최소인 점(medoid)을 대표점으로 씁니다.
    parents = {i:i for i in stations.index}
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    xy = np.column_stack([stations.geometry.x, stations.geometry.y])
    ids = stations.index.to_numpy()
    for a,b in cKDTree(xy).query_pairs(500):
        i,j = ids[a],ids[b]
        if stations.loc[i,'norm']==stations.loc[j,'norm'] or np.linalg.norm(xy[a]-xy[b]) < .01:
            parents[root(j)] = root(i)
    stations['group'] = [root(i) for i in stations.index]
    rows=[]; audit=[]
    for group, part in stations.groupby('group', sort=True):
        coords = np.column_stack([part.geometry.x, part.geometry.y])
        distances = np.linalg.norm(coords[:,None]-coords[None,:],axis=2)
        row = part.iloc[int(np.argmin(distances.sum(axis=1)))].copy()
        row['station_id'] = str(part['역사_ID'].min())
        row['lines'] = ', '.join(sorted(part['호선'].unique()))
        row['members'] = len(part)
        rows.append(row)
        audit.append({'station_id':row.station_id,'name':row['norm'],'record_ids':','.join(part['역사_ID'].astype(str)), 'members':len(part),'max_separation_m':round(float(distances.max()),2),'lines':row.lines})
    unique = gpd.GeoDataFrame(rows,crs=CRS).reset_index(drop=True)
    buffer = dong.geometry.union_all().buffer(BUFFER_M)
    unique = unique.loc[unique.intersects(buffer)].copy().reset_index(drop=True)
    unique,ties = assign_once(unique,dong)
    counts = unique.groupby('ADM_CD').size()
    dong['station_count'] = dong.ADM_CD.map(counts).fillna(0).astype(int)
    dong['density'] = dong.station_count / dong.area_km2
    assert dong.station_count.sum() == unique.ADM_CD.notna().sum()
    pd.DataFrame(audit).to_csv(PROCESSED/'station_dedup_audit.csv',index=False,encoding='utf-8-sig')
    dong.to_file(PROCESSED/'dong.gpkg', driver='GPKG')
    grid.to_file(PROCESSED/'grid.gpkg', driver='GPKG')
    unique.to_file(PROCESSED/'stations.gpkg', driver='GPKG')
    qa={'population_rows_raw':len(p),'total_population_records':len(total),'total_population_codes_unique':bool(total.GRID_CD.is_unique),'grid_codes_unique':True,'population_join':'one_to_one','population_years': sorted(p.year.astype(str).unique().tolist()),'grid_rows_raw':all_grid_count,'grid_rows_in_seoul':len(grid),'grid_center_outside_seoul':len(outside_grid),'outside_grid_known_population':float(outside_grid.population.sum()),'grid_boundary_ties':grid_ties,'missing_population_grids':int(grid.population.isna().sum()),'zero_population_grids':int(grid.population.eq(0).sum()),'positive_population_grids':int(grid.population.gt(0).sum()),'known_population':float(grid.population.sum()),'stations_raw':len(source),'station_invalid_coordinates':int((~valid).sum()),'excluded_nonstopping_records':len(excluded),'stations_unique_all_region':len(rows),'stations_in_buffer':len(unique),'stations_in_seoul':int(unique.ADM_CD.notna().sum()),'stations_outside_seoul_in_buffer':int(unique.ADM_CD.isna().sum()),'station_boundary_ties':ties,'dong_count':len(dong),'dong_base_date':sorted(dong.BASE_DATE.unique().tolist()),'crs':CRS,'buffer_m':BUFFER_M,'grid_crs_raw':'EPSG:4326','station_crs_raw':'EPSG:4326','station_snapshot_date':'수업 CSV 자체에는 기준일 없음','grid_year':'2025 (파일명 기준)','downloads_date':DATE}
    save_json(PROCESSED/'prepare_validation.json',qa)
    hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in RAW.iterdir() if f.is_file() and f.suffix!='.graphml'}
    save_json(ROOT/'reports/input_sha256.json',hashes)
    print(json.dumps(qa,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
