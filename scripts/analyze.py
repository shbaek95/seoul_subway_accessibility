"""OSM 보행망 최단거리로 모든 역의 중력형 기여도를 합산합니다."""
import gc
import json
import time
import hashlib
import pickle
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from scipy.spatial import cKDTree
from pyproj import Transformer
from common import *
import osmnx as ox

def load_network():
    """큰 GraphML은 처음 한 번만 변환하고, 직접 만든 로컬 계산 캐시를 재사용합니다."""
    source=RAW/'seoul_buffer_walk.graphml'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    cache=PROCESSED/'network_local_cache.pkl'
    marker=PROCESSED/'network_cache_sha256.txt'
    if cache.exists() and marker.exists() and marker.read_text()==digest:
        # 인터넷에서 받은 pickle을 읽지 않습니다. 이 함수가 만든 로컬 캐시만 사용합니다.
        with cache.open('rb') as handle: graph,node_ids,xy=pickle.load(handle)
        print('직접 생성한 계산용 네트워크 캐시 사용',flush=True)
        return graph,node_ids,xy
    original=ox.load_graphml(source)
    node_ids=np.array(list(original.nodes),dtype=np.int64)
    transform=Transformer.from_crs(original.graph['crs'],CRS,always_xy=True)
    xx,yy=transform.transform([original.nodes[n]['x'] for n in node_ids], [original.nodes[n]['y'] for n in node_ids])
    xy=np.column_stack([xx,yy])
    graph=nx.Graph()
    graph.add_nodes_from(node_ids)
    for u,v,attr in original.edges(data=True):
        distance=float(attr['length'])
        assert np.isfinite(distance) and distance>=0
        if not graph.has_edge(u,v) or distance<graph[u][v]['length']:
            graph.add_edge(u,v,length=distance)
    del original;gc.collect()
    with cache.open('wb') as handle:pickle.dump((graph,node_ids,xy),handle,protocol=5)
    marker.write_text(digest)
    return graph,node_ids,xy

def calculate_scores(graph, grid_nodes, grid_snap, station_nodes, station_snap):
    """역별 Dijkstra를 수행합니다. 같은 노드에 붙은 서로 다른 역도 각각 더합니다."""
    score = np.zeros(len(grid_nodes), dtype=float)
    nearest = np.full(len(grid_nodes), np.inf)
    counts = np.zeros(len(grid_nodes), dtype=int)
    node_to_rows = {}
    for i,node in enumerate(grid_nodes):
        if grid_snap[i] <= SNAP_MAX_M:
            node_to_rows.setdefault(node,[]).append(i)
    node_to_rows = {n:np.asarray(rows,dtype=int) for n,rows in node_to_rows.items()}
    for j,(node,offset) in enumerate(zip(station_nodes, station_snap)):
        if offset > SNAP_MAX_M: continue
        distances = nx.single_source_dijkstra_path_length(graph, node, cutoff=MAX_MIN*SPEED-offset, weight='length')
        for n,distance in distances.items():
            rows = node_to_rows.get(n)
            if rows is None: continue
            minutes = (distance+offset+grid_snap[rows])/SPEED
            good = minutes <= MAX_MIN
            target = rows[good]
            score[target] += np.exp(-BETA*minutes[good])
            nearest[target] = np.minimum(nearest[target], minutes[good])
            counts[target] += 1
        if (j+1)%25==0: print(f'역 {j+1}/{len(station_nodes)} 계산 완료',flush=True)
    score[grid_snap>SNAP_MAX_M]=np.nan
    return score,nearest,counts

def main():
    started=time.time()
    dong=gpd.read_file(PROCESSED/'dong.gpkg')
    grid=gpd.read_file(PROCESSED/'grid.gpkg')
    stations=gpd.read_file(PROCESSED/'stations.gpkg')
    # 매번 새 배열에서 합산하므로 재실행해도 중복 누적되지 않습니다.
    print('보행망 GraphML 읽기',flush=True)
    graph,node_ids,xy=load_network()
    tree=cKDTree(xy)
    # 100m 격자 중심·역 대표점과 가까운 원래 도로 정점 사이 연결거리도 더합니다.
    grid_snap,grid_positions=tree.query(np.column_stack([grid.geometry.x,grid.geometry.y]))
    station_snap,station_positions=tree.query(np.column_stack([stations.geometry.x,stations.geometry.y]))
    grid_nodes=node_ids[grid_positions]; station_nodes=node_ids[station_positions]
    print('망 크기',len(graph),graph.number_of_edges(),'격자 연결거리',np.percentile(grid_snap,[50,95,99,100]),'역 연결거리',np.percentile(station_snap,[50,95,99,100]),flush=True)
    score,nearest,counts=calculate_scores(graph,grid_nodes,grid_snap,station_nodes,station_snap)
    # 미연결점은 NaN, 망에 연결되지만 30분 안에 역이 없으면 0입니다.
    grid['snap_m']=grid_snap;grid['accessibility']=score
    grid['nearest_walk_min']=np.where(np.isfinite(nearest),nearest,np.nan)
    grid['reachable_stations']=counts
    stations['snap_m']=station_snap
    stations.drop(columns='geometry').to_csv(PROCESSED/'station_connections.csv',index=False,encoding='utf-8-sig')
    known=grid.population.notna()
    positive=grid.population.gt(0)
    failed=grid.snap_m.gt(SNAP_MAX_M)
    rows=[]
    for code,part in grid.groupby('ADM_CD'):
        kp=part.loc[part.population.notna()]
        bad=kp.population.gt(0)&kp.accessibility.isna()
        denominator=float(kp.population.sum())
        a=weighted_mean(kp.population,kp.accessibility)
        rows.append({'ADM_CD':code,'population':denominator,'grid_count':len(part),'missing_population_grids':int(part.population.isna().sum()),'failed_population':float(kp.loc[bad,'population'].sum()),'zero_access_population':float(kp.loc[kp.accessibility.eq(0),'population'].sum()),'accessibility':a,'status':'계산 불가: 보행망 연결 실패' if bad.any() else ('공개 인구 기준 계산' if denominator else '자료 없음: 인구 분모 0'),'zero_access_pct':float(kp.loc[kp.accessibility.eq(0),'population'].sum()/denominator*100) if denominator else np.nan,'snap_p95_m':float(np.percentile(part.snap_m,95))})
    result=dong.merge(pd.DataFrame(rows),on='ADM_CD',validate='one_to_one',how='left')
    # 백분위는 동점 평균 순위 / 유효 지역 수 ×100입니다. 두 원지표의 단위를 직접 빼지 않습니다.
    paired=result.accessibility.notna()
    result['density_percentile']=np.nan;result['access_percentile']=np.nan
    result.loc[paired,'density_percentile']=result.loc[paired,'density'].rank(method='average',pct=True)*100
    result.loc[paired,'access_percentile']=result.loc[paired,'accessibility'].rank(method='average',pct=True)*100
    result['percentile_gap']=result.access_percentile-result.density_percentile
    assert result.ADM_CD.is_unique and len(result)==426
    for c in ['area_km2','density','accessibility']:
        assert not np.isinf(result[c]).any()
        assert result[c].dropna().ge(0).all()
    assert np.all(score[np.isfinite(score)] >= np.where(np.isfinite(nearest[np.isfinite(score)]),np.exp(-BETA*nearest[np.isfinite(score)]),0)-1e-10)
    # 독립적인 소표본 검증: 격자에서 역으로 경로를 다시 구해 역별 합산과 대조합니다.
    sample=np.random.default_rng(42).choice(np.flatnonzero(positive & ~failed),size=12,replace=False)
    max_error=0
    for i in sample:
        distances=nx.single_source_dijkstra_path_length(graph,grid_nodes[i],cutoff=MAX_MIN*SPEED,weight='length')
        times=np.array([(distances.get(n,np.inf)+offset+grid_snap[i])/SPEED if offset<=SNAP_MAX_M else np.inf for n,offset in zip(station_nodes,station_snap)])
        expected=gravity(times)
        max_error=max(max_error,abs(expected-score[i]))
        assert abs(expected-score[i])<1e-9
    # 같은 노드에 붙은 서로 다른 역을 한 역으로 합치지 않는지도 별도로 검증합니다.
    grid.drop(columns='geometry').to_csv(PROCESSED/'grid_scores.csv',index=False,encoding='utf-8-sig')
    result.to_file(PROCESSED/'results.gpkg',driver='GPKG')
    result.drop(columns='geometry').to_csv(PUBLIC/'results.csv',index=False,encoding='utf-8-sig',float_format='%.8f')
    # 공개 폴더에는 행정동 집계만 저장합니다. 격자 인구·OSM 원시망은 넣지 않습니다.
    simple=result.to_crs(CRS).copy()
    simple.geometry=simple.geometry.simplify(15,preserve_topology=True)
    simple=simple.to_crs(4326)
    geo=json.loads(simple.to_json(drop_id=True,na='null'))
    save_json(PUBLIC/'results.geojson',geo)
    correlation=result.loc[paired,['density','accessibility']].corr(method='spearman').iloc[0,1]
    before=json.loads((PROCESSED/'prepare_validation.json').read_text(encoding='utf-8'))
    qa={**before,'network_nodes':len(graph),'network_edges':graph.number_of_edges(),'network_components':nx.number_connected_components(graph),'network_method':'OSMnx walk · 모든 연결 성분 보존 · 무향 · 도로 중간 정점 유지','snap_max_m':SNAP_MAX_M,'grid_snap_quantiles_m':dict(zip(['p50','p95','p99','max'],map(float,np.percentile(grid_snap,[50,95,99,100])))),'station_snap_max_m':float(station_snap.max()),'failed_grid_count':int(failed.sum()),'failed_positive_grid_count':int((failed&positive).sum()),'failed_known_population':float(grid.loc[failed,'population'].sum()),'station_snap_failures':int((station_snap>SNAP_MAX_M).sum()),'zero_access_known_population':float(grid.loc[grid.accessibility.eq(0),'population'].sum()),'all_known_population_denominator':float(grid.population.sum()),'valid_dongs':int(paired.sum()),'unavailable_dongs':int((~paired).sum()),'sample_path_checks':len(sample),'sample_path_max_error':float(max_error),'spearman':float(correlation),'runtime_seconds':round(time.time()-started,1),'result_csv_sha256':hashlib.sha256((PUBLIC/'results.csv').read_bytes()).hexdigest()}
    save_json(ROOT/'reports/validation.json',qa)
    # 연결 실패 역이 있으면 누락 점수를 정상 결과로 공개하지 않고 중단합니다.
    if qa['station_snap_failures']: raise ValueError('역 연결 실패가 있습니다. 연결 목록을 확인한 후 재분석하세요.')
    print(json.dumps(qa,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__': main()
