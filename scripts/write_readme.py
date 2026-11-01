"""실제 보고서와 검증 기록을 README에 정리합니다. 배포 URL은 검증 후에만 입력합니다."""
import json
import argparse
from common import ROOT, PUBLIC

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deployed-url');args=parser.parse_args()
    qa=json.loads((ROOT/'reports/validation.json').read_text(encoding='utf-8'))
    report=(ROOT/'reports/analysis_report.md').read_text(encoding='utf-8')
    deployment=args.deployed_url or '배포 전: 실제 주소 검증 후 기록'
    intro='서울 행정동별 지하철역 밀도와 주민의 지하철 보행 접근성이 같은 평가를 내리는지 살펴본 과제입니다. 역 밀도는 동 안의 역군 수를 면적으로 나누고, 접근성은 100m 인구 격자에서 30분 안의 여러 역까지 OSM 보행망 거리를 계산해 합산했습니다. 2024년 공개 인구와 2025년 경계를 사용하므로 현재 실제 주민 전체를 측정한 공식 통계는 아닙니다. 지도·산점도·백분위 차이로 두 지표가 닮거나 달라지는 지역을 탐색하고, 관찰 결과와 추가 검증이 필요한 설명을 구분했습니다.'
    text=f'''# 서울 지하철: 역 밀도와 주민 접근성

백승현 · 스마트도시데이터분석 **과제 3**

- GitHub: https://github.com/shbaek95/seoul_subway_accessibility
- Cloudflare Pages: {deployment}
- 수업 원문: [03_accessibility.ipynb 마지막 과제3 안내](https://github.com/jslee-gses/code/blob/main/lecture05_urban_planning_index/03_accessibility.ipynb)
- 마감일·필수 파일명·필수 파일 형식: **과제 안내에서 확인되지 않음**

## 교수님께 설명할 소개

{intro}

## 프로젝트 구조

```text
seoul_subway_accessibility/
├── public/                   # Pages에 공개하는 유일한 폴더
│   ├── index.html, style.css, app.js
│   ├── results.geojson       # 행정동 집계 지도, 공개용 15m 단순화
│   ├── results.csv           # 행정동 집계 수치
│   ├── summary.json, sources.json, validation.json, report.md
│   └── _headers, 404.html
├── scripts/
│   ├── download_data.py      # 수업 원자료 확보·지정 커밋 해시 대조
│   ├── prepare.py            # 총인구 1:1 결합·역군·행정동 배정·밀도
│   ├── fetch_network.py      # 서울+2.5km OSM 보행망 다운로드·캐시
│   ├── analyze.py            # 역별 Dijkstra·모든 역 기여도 합산
│   ├── build_report.py       # 실제 결과로 보고서·그림 생성
│   ├── write_readme.py, common.py
│   └── check_site.mjs        # 실제 Edge 브라우저 검증·화면 캡처
├── tests/test_metrics.py     # 손계산 기반 5개 검증
├── reports/                  # 분석 보고서·검증·그림·대표 이미지
├── data/raw/                 # Git 제외: 원자료·OSM 캐시
├── data/processed/           # Git 제외: 중간 결과·연결·중복 정리 목록
├── .local/                   # Git 제외: 추가 패키지·작업 로그·인증 보조 도구
├── requirements.txt
├── run_analysis.ps1
└── submission.txt
```

## 실행 환경과 재현

실제 실행 환경: Windows, Python 3.11.13. 라이브러리 버전은 `requirements.txt`에 고정했습니다.
OSM은 수집 시점에 따라 바뀌므로 **동일 결과 재현에는 보존한 GraphML·Overpass 캐시가 필요**합니다. 원시망은 공개 GitHub에 올리지 않습니다. 새로 내려받으면 같은 방법의 새 스냅샷 분석이 됩니다.

새 환경의 PowerShell에서:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\run_analysis.ps1 -DownloadNetwork
```

이 작업 폴더에서는 수업 폴더의 기존 `..\\.venv\\Scripts\\python.exe`와 프로젝트 전용 `.local/packages/osmnx`를 사용했습니다. 기존 수업 가상환경의 패키지를 변경하지 않았습니다. `run_analysis.ps1`은 프로젝트 환경이 없으면 해당 수업 환경을 사용합니다.

단계별 실행:

```powershell
python scripts/download_data.py
python scripts/prepare.py
python scripts/fetch_network.py
python -m unittest discover -s tests -v
python scripts/analyze.py
python scripts/build_report.py
python scripts/write_readme.py
python -m http.server 8093 --directory public
```

브라우저에서 `http://localhost:8093`을 엽니다. HTML을 파일로 직접 열면 JSON fetch가 제한될 수 있습니다.
보행망은 공개 Overpass 서버의 혼잡도에 따라 오래 걸릴 수 있습니다. 순차 요청·디스크 캐시·점진적 재시도를 사용하며, 확보 실패 시 실제 보행망을 직선거리 결과로 바꾸어 표시하지 않습니다.

선택적 웹 검증: Node.js와 Playwright가 있는 환경에서 `node scripts/check_site.mjs http://localhost:8093`을 실행합니다. 이 PC의 기존 Edge를 사용하며, 새 환경에서는 `npm install --no-save playwright`가 필요합니다. 분석을 매번 Pages에서 다시 실행하지 않습니다.

## 전처리의 구체적 기준

- 수업 배포본은 교수님 `jslee-gses/code` 커밋 `d04422c9a8341df75795956db6bdec4aaa9a61e0`의 8개 파일과 Git blob 해시가 일치합니다. `reports/download_manifest.json`과 `input_sha256.json`에 기록했습니다.
- 인구는 `to_in_001`만 선택해 코드별 1:1 결합합니다. 성별 값을 더해 총인구를 이중 집계하지 않습니다.
- 행정동 코드와 경계는 같은 파일의 `ADM_CD`를 사용합니다. SGIS 8자리 코드이며 다른 행정기관 코드와 이름만으로 결합하지 않습니다.
- 인구는 투영좌표계 격자 중심점으로 행정동 한 곳에 배정합니다. 경계 위 점은 코드 오름차순 1곳만 배정합니다. 서울 밖 중심점 {qa['grid_center_outside_seoul']:,}개(확인 가능한 인구 {qa['outside_grid_known_population']:,.0f}명)는 제외합니다.
- 인구 기록이 없는 격자는 {qa['missing_population_grids']:,}개이며 0으로 대체하지 않습니다. 공개값 0인 {qa['zero_population_grids']}개와 구별합니다. 결측 인구 총량은 미상으로, 공개 인구만의 가중 평균을 실제 전체 주민 평균이라고 주장하지 않습니다.
- SGIS 공식 안내는 N/A 및 BSCA 비밀보호를 설명합니다. 특히 격자 공개 0도 실제 무인구를 보장하지 않습니다. 원시 인구의 참값을 역추정하지 않았습니다.
- 역 이름은 괄호 부가명을 제거하고 서울/서울역, 이수/총신대입구 별칭을 정규화합니다. 같은 정규명+500m 이내 또는 동일 좌표인 기록을 연결 군집으로 묶습니다. 연결 군집의 최대 지름은 500m를 넘을 수 있습니다(서울 역군 508.68m). 동일 이름만으로 먼 역을 합치지 않습니다.
- 역군의 대표점은 군내 다른 점까지 거리합이 최소인 **실제 원자료 좌표**입니다. 환승역 수가 서비스 가중치를 늘리지 않으며 S=1입니다. `data/processed/station_dedup_audit.csv`에서 구성 기록과 거리를 확인할 수 있습니다.
- GTX 삼성 기록 1행은 미정차역으로 제외하고 2호선 삼성은 유지합니다. [공공기관 운영계획 근거](https://mas.smc.seoul.kr/attach/record/SEOUL/appendix/a11/A0069210.pdf). 다른 역의 모든 운영 상태를 별도 전수 확인한 것은 아닙니다.
- 역은 서울 안에서 한 행정동에만 배정해 밀도를 계산합니다. 접근성에는 서울 밖 2.5km 안의 역 {qa['stations_outside_seoul_in_buffer']}개도 포함합니다.
- OSM `walk` 필터, 모든 연결 성분 보존, 도로 중간 정점 보존. 도로망 최단거리와 양 끝 연결거리를 모두 합산합니다. 연결거리가 300m를 넘으면 실패로 표시합니다. 연결 실패 양수 인구가 있는 동은 접근성 결측으로 공개합니다.
- 공개 지도만 15m 단순화하며 면적·거리·집계는 단순화 이전 원자료로 계산합니다.

## 자료별 출처·연도·조건

`public/sources.json`에 제공기관, 자료명, URL, 기준일, 다운로드 날짜, 좌표계, 주요 필드, 공간 단위, 이용 조건, 처리 방법을 모두 기록했습니다. 서울 역 자료는 공공누리 제1유형, OSM은 ODbL과 출처 표시 조건입니다. SGIS는 출처 표시·활용 결과 제출 조건을 확인했고, 교수님 가공본의 별도 재배포 허락은 확인되지 않아 원자료 전체는 GitHub에 올리지 않았습니다.

## 배포 구성

Cloudflare Pages의 GitHub `main` 연결을 우선 사용합니다. Framework preset **None**, 프로젝트 루트는 저장소 루트, build command **exit 0**, output directory **public**입니다. 빌드 시 분석을 다시 돌리지 않고 검증된 공개 집계만 배포합니다. 이 사이트에는 API 키가 필요하지 않습니다.

- [Cloudflare 공식 정적 HTML 안내](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/)
- [공식 GitHub 연결 안내](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/)
- 실제 배포·브라우저 검증 결과는 `reports/browser-deployed.json`과 최종 제출 자료에 기록합니다.

## 검증

- 총인구·격자 코드 1:1, 경계 코드 426개 고유, EPSG:5179 면적·연결거리 미터 단위 확인.
- 역 원자료 {qa['stations_raw']}행, 비정차 제외 {qa['excluded_nonstopping_records']}행, 수도권 역군 {qa['stations_unique_all_region']}개, 서울 {qa['stations_in_seoul']}개.
- 도로망 노드 {qa['network_nodes']:,}개, 무향 간선 {qa['network_edges']:,}개, 연결 성분 {qa['network_components']:,}개.
- 격자 연결거리 95백분위 {qa['grid_snap_quantiles_m']['p95']:.1f}m, 역 최대 연결거리 {qa['station_snap_max_m']:.1f}m.
- 양수 인구 연결 실패 {qa['failed_positive_grid_count']}격자 / {qa['failed_known_population']:,.0f}명. 유효 지역 {qa['valid_dongs']}개 / 계산 불가 {qa['unavailable_dongs']}개.
- 30분 안에 역이 없는 공개 인구 {qa['zero_access_known_population']:,.0f}명을 가중 평균 분모에 포함.
- 손계산 5개 검증 통과: 여러 역 합산, 30분 상한, 인구 분모, 같은 노드의 서로 다른 역, 연결거리·실패·재실행.
- 실제 격자 12개를 격자→역의 반대 방향 경로 계산으로 검증: 최대 점수 오차 {qa['sample_path_max_error']:.3g}.
- NaN·0·무한대 검사 완료. 재실행 결과 해시 기록은 `reports/reexecution.json` 참조.

---

{report}
'''
    (ROOT/'README.md').write_text(text.rstrip()+'\n',encoding='utf-8')

if __name__=='__main__': main()
