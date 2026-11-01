"""서울 경계에 2.5km 버퍼를 둔 OSM 보행망을 한 번 받아 캐시합니다."""
import sys
import time
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/packages'))
import geopandas as gpd
import osmnx as ox

ox.settings.use_cache = True
ox.settings.cache_folder = ROOT / 'data/raw/osm_cache'
ox.settings.log_console = True
ox.settings.requests_timeout = 300
ox.settings.overpass_rate_limit = True
# 공개 서버에 과도한 동시 요청을 보내지 않고, 순서대로 분할 다운로드합니다.
ox.settings.max_query_area_size = 250_000_000
path = ROOT / 'data/raw/seoul_buffer_walk.graphml'
if path.exists():
    print('기존 GraphML 캐시 사용:', path, flush=True)
else:
    dong = gpd.read_file(ROOT / 'data/raw/bnd_dong_seoul.shp').to_crs(5179)
    polygon = gpd.GeoSeries([dong.geometry.union_all().buffer(2500)], crs=5179).to_crs(4326).iloc[0]
    # simplify=False: 긴 도로의 중간 정점을 유지하여 최근접 노드 연결 오차를 줄입니다.
    # retain_all=True: 작은 분리 성분을 삭제해 접근성을 과장하지 않습니다.
    for attempt in range(4):
        try:
            graph = ox.graph_from_polygon(polygon, network_type='walk', simplify=False,
                                          retain_all=True, truncate_by_edge=True)
            break
        except Exception as error:
            if attempt == 3: raise
            # 이미 받은 타일은 디스크 캐시로 재사용하고 실패한 요청만 재시도합니다.
            delay = 30 * (2 ** attempt)
            print(f'공개 Overpass 서버 응답 실패: {type(error).__name__}. {delay}초 후 캐시를 재사용하여 재시도합니다.', flush=True)
            time.sleep(delay)
    ox.save_graphml(graph, path)
    print('OSM 다운로드 완료:', len(graph), graph.number_of_edges(), flush=True)
snapshots=[]
for cached in (ROOT/'data/raw/osm_cache').glob('*.json'):
    data=json.loads(cached.read_text(encoding='utf-8'))
    if data.get('remark'):
        raise ValueError('OSM 응답에 부분 결과 경고가 있습니다: '+str(data['remark']))
    snapshots.append({'cache_file':cached.name,'osm_base':data.get('osm3s',{}).get('timestamp_osm_base')})
metadata={'download_date':'2026-11-01','buffer_m':2500,'network_type':'walk','retain_all':True,'simplify':False,'snapshots':snapshots,'copyright':'© OpenStreetMap contributors','license':'https://www.openstreetmap.org/copyright'}
(ROOT/'reports/network_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
