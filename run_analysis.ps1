param([switch]$DownloadNetwork)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
# 프로젝트 가상환경이 있으면 먼저 사용하고, 현재 수업 폴더 환경도 사용할 수 있습니다.
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (!(Test-Path $taskPython)) { $taskPython = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe' }
if (!(Test-Path $taskPython)) { throw 'README를 따라 Python 가상환경을 먼저 준비하세요.' }
& $taskPython scripts/download_data.py
if ($LASTEXITCODE -ne 0) { throw '원자료 확보 실패' }
& $taskPython scripts/prepare.py
if ($LASTEXITCODE -ne 0) { throw '전처리 실패' }
if ($DownloadNetwork -or !(Test-Path data/raw/seoul_buffer_walk.graphml)) {
    & $taskPython scripts/fetch_network.py
    if ($LASTEXITCODE -ne 0) { throw 'OSM 보행망 확보 실패' }
}
& $taskPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '계산 함수 검증 실패' }
& $taskPython scripts/analyze.py
if ($LASTEXITCODE -ne 0) { throw '접근성 분석 실패' }
& $taskPython scripts/build_report.py
if ($LASTEXITCODE -ne 0) { throw '보고서 생성 실패' }
Write-Output '분석·검증·보고서 생성 완료. public/index.html은 HTTP 서버로 열어 주세요.'
