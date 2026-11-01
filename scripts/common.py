"""분석 전반에서 공유하는 설정과 JSON 저장 도구."""
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/packages'))
RAW = ROOT / 'data/raw'
PROCESSED = ROOT / 'data/processed'
PUBLIC = ROOT / 'public'
CRS = 'EPSG:5179'
SPEED = 4000 / 60
BETA = np.log(2) / 10
MAX_MIN = 30
BUFFER_M = 2500
SNAP_MAX_M = 300
DATE = '2026-11-01'

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def gravity(minutes, weights=None):
    """30분 이내 모든 역을 합산합니다. 접근 가능한 역이 없으면 0입니다."""
    t = np.asarray(minutes, dtype=float)
    w = np.ones_like(t) if weights is None else np.asarray(weights, dtype=float)
    return float(np.sum(np.where(t <= MAX_MIN, w * np.exp(-BETA * t), 0)))

def weighted_mean(population, scores):
    """0점인 인구도 분모에 포함합니다. 인구·점수 결측은 숨기지 않습니다."""
    p, a = np.asarray(population, dtype=float), np.asarray(scores, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p > 0) & ~np.isfinite(a)):
        return float('nan')
    return float(np.dot(p, np.nan_to_num(a)) / p.sum()) if p.sum() else float('nan')
