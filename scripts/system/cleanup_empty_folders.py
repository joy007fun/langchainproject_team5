#!/usr/bin/env python3
# scripts/cleanup_empty_folders.py
"""
빈 폴더 정리 스크립트

experiments 폴더의 빈 폴더들을 정리합니다.
"""

# ==================== Import ==================== #
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.experiment_manager import ExperimentManager


# ==================== 메인 함수 ==================== #
def main():
    """빈 폴더 정리"""
    print("=" * 80)
    print("🧹 실험 폴더 정리 시작")
    print("=" * 80)
    print()

    # 오늘 날짜
    today = datetime.now().strftime("%Y%m%d")
    date_dir = Path(f"experiments/{today}")

    if not date_dir.exists():
        print(f"❌ 오늘 날짜 폴더가 존재하지 않습니다: {date_dir}")
        return

    print(f"📂 정리 대상 폴더: {date_dir}")
    print()

    # 정리 전 빈 폴더 개수 확인
    empty_folders_before = [
        folder for folder in date_dir.rglob("*")
        if folder.is_dir() and not any(folder.iterdir())
    ]

    print(f"🔍 정리 전 빈 폴더 개수: {len(empty_folders_before)}")
    if empty_folders_before:
        print("\n빈 폴더 목록:")
        for folder in sorted(empty_folders_before):
            print(f"  - {folder}")
    print()

    # ExperimentManager를 임시로 생성하여 cleanup 실행
    # (새 세션 폴더가 생성되지만 cleanup에서 제거됨)
    with ExperimentManager() as exp_manager:
        print("🧹 빈 폴더 정리 중...")
        # cleanup_empty_folders는 close()에서 자동 호출됨

    print()

    # 정리 후 빈 폴더 개수 확인
    empty_folders_after = [
        folder for folder in date_dir.rglob("*")
        if folder.is_dir() and not any(folder.iterdir())
    ]

    deleted_count = len(empty_folders_before) - len(empty_folders_after)

    print("=" * 80)
    print(f"✅ 빈 폴더 정리 완료: {deleted_count}개 삭제")
    print(f"🔍 정리 후 빈 폴더 개수: {len(empty_folders_after)}")
    if empty_folders_after:
        print("\n남아있는 빈 폴더:")
        for folder in sorted(empty_folders_after):
            print(f"  - {folder}")
    print("=" * 80)


# ==================== 실행 ==================== #
if __name__ == "__main__":
    main()
