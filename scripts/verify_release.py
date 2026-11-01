"""공개 산출물의 수치·연결 관계와 파일 범위를 최종 확인합니다."""
import json
import hashlib
import csv
import numpy as np
import pandas as pd
from common import *

def main():
    geo=json.loads((PUBLIC/'results.geojson').read_text(encoding='utf-8'))
    qa=json.loads((ROOT/'reports/validation.json').read_text(encoding='utf-8'))
    frame=pd.DataFrame([f['properties'] for f in geo['features']])
    csv_frame=pd.read_csv(PUBLIC/'results.csv',dtype={'ADM_CD':str})
    assert len(frame)==426 and frame.ADM_CD.is_unique and csv_frame.ADM_CD.is_unique
    assert set(frame.ADM_CD)==set(csv_frame.ADM_CD)
    np.testing.assert_allclose(frame.density, frame.station_count/frame.area_km2,rtol=1e-10)
    assert int(frame.station_count.sum())==qa['stations_in_seoul']
    assert float(frame.population.sum())==qa['all_known_population_denominator']
    valid=frame.accessibility.notna()
    for key,rank in [('density','density_percentile'),('accessibility','access_percentile')]:
        expected=frame.loc[valid,key].rank(method='average',pct=True)*100
        np.testing.assert_allclose(frame.loc[valid,rank],expected,rtol=1e-9)
    np.testing.assert_allclose(frame.loc[valid,'percentile_gap'],frame.loc[valid,'access_percentile']-frame.loc[valid,'density_percentile'])
    assert frame.loc[~valid,'status'].str.contains('계산 불가|자료 없음').all()
    assert not (frame.accessibility.dropna()<0).any()
    for name in ['results.geojson','summary.json','sources.json','validation.json']:
        content=(PUBLIC/name).read_text(encoding='utf-8')
        assert 'NaN' not in content and 'Infinity' not in content
    for file in PUBLIC.rglob('*'):
        if file.is_file():
            assert not any(part.startswith('.') for part in file.relative_to(PUBLIC).parts)
            assert file.stat().st_size<5_000_000
            assert file.suffix not in ['.py','.graphml','.gpkg','.env','.shp','.dbf']
    release={'checks':'집계 426개, 코드·면적·밀도·인구 분모·백분위·실패 표시·JSON 유한값·공개 파일 범위 통과','result_csv_sha256':hashlib.sha256((PUBLIC/'results.csv').read_bytes()).hexdigest(),'public_files':sorted(str(p.relative_to(PUBLIC)) for p in PUBLIC.rglob('*') if p.is_file())}
    assert release['result_csv_sha256']==qa['result_csv_sha256']
    save_json(ROOT/'reports/release_validation.json',release)
    print(json.dumps(release,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
