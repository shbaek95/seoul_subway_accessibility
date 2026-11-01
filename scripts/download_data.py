"""교수님 공개 수업 저장소에서 필수 파일만 받습니다. 기존 파일은 보존합니다."""
import hashlib
from common import RAW, ROOT, save_json, DATE
import requests

COMMIT = 'd04422c9a8341df75795956db6bdec4aaa9a61e0'
BASE = f'https://raw.githubusercontent.com/jslee-gses/code/{COMMIT}/lecture05_urban_planning_index/'
FILES = ['grid/2024년_인구_다사_100M.csv','grid/seoul_100m_grid_2025.geojson',
         *['shp/bnd_dong_seoul.'+ext for ext in ['shp','dbf','prj','shx','cpg']],
         'data/서울시 역사마스터 정보.csv']
EXPECTED = {'2024년_인구_다사_100M.csv':'0d2532947a49a40627cfd2071160b3f4de3a8a1a',
 'seoul_100m_grid_2025.geojson':'3221782c1feaa0e181ec749bbdd8c1f3c15a9b97',
 'bnd_dong_seoul.cpg':'3ad133c048f2189041151425a73485649e6c32c0',
 'bnd_dong_seoul.dbf':'c8660636fd185de1610856b102b2736ecb921170',
 'bnd_dong_seoul.prj':'3a44051f7b0db6e2565488a6ef7cbca8dfebfbf8',
 'bnd_dong_seoul.shp':'26c5a0f7da3328a3f6921ad9dad1db62fce2b8a0',
 'bnd_dong_seoul.shx':'6b6b3d7bea28f811c17b9c67a19a336006196acf',
 '서울시 역사마스터 정보.csv':'e7a33e7d42b73bf0552695b73aff3b9fea8b02f9'}

def main():
    RAW.mkdir(parents=True,exist_ok=True)
    hashes={}
    for filename in FILES:
        path=RAW/filename.split('/')[-1]
        if not path.exists():
            r=requests.get(BASE+filename,timeout=180);r.raise_for_status()
            path.write_bytes(r.content)
        content=path.read_bytes()
        # Git blob 해시로 수업 저장소의 지정 커밋과 바이트가 같은지 확인합니다.
        actual=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if actual != EXPECTED[path.name]:
            raise ValueError(f'{path.name}: 지정 원본과 다릅니다. 기존 파일을 보존하고 중단합니다.')
        hashes[path.name]=hashlib.sha256(content).hexdigest()
        print(path.name,path.stat().st_size)
    save_json(ROOT/'reports/download_manifest.json',{'download_date':DATE,'source_commit':COMMIT,'base_url':BASE,'sha256':hashes})

if __name__=='__main__':main()
