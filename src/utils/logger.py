# ---------------------- 로그 기록 모듈 ---------------------- #

import sys                                       # 시스템 관련 기능 모듈
from datetime import datetime                    # 현재 시간 가져오기 모듈
from pathlib import Path                         # 경로 처리 모듈
from typing import Optional                      # 타입 힌팅 모듈

# tqdm은 선택적 의존성
try:
    from tqdm import tqdm                        # 진행률 표시 모듈
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# ---------------------- Logger 클래스 정의 ---------------------- #
class Logger:                                    # Logger 클래스 정의
    """
    로그를 파일에 저장하고, 표준 출력(stdout)과 표준 에러(stderr)를
    로그 파일로 리디렉션하는 기능이 추가된 Logger 클래스
    """
    # 초기화 함수 정의
    def __init__(self, log_path: str, print_also: bool = True):
        self.log_path = Path(log_path)           # 로그 파일 경로 저장 (pathlib.Path 사용)
        self.print_also = print_also             # 콘솔 출력 여부 저장

        # 로그 폴더 자동 생성
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # 원본 표준 출력을 저장해 둡니다.
        self.original_stdout = sys.stdout        # 원본 표준 출력 저장
        self.original_stderr = sys.stderr        # 원본 표준 에러 저장

        # 로그 파일을 열고, UTF-8 인코딩을 사용합니다.
        self.log_file = open(self.log_path, 'a', encoding='utf-8')  # 로그 파일 열기

        # tqdm 진행률 추적 변수
        self._tqdm_last_percent = {}             # {desc: last_percent} - 작업별 마지막 기록 진행률

    
    # 로그 기록 함수 정의
    def write(self, message: str, print_also: Optional[bool] = None, print_error: bool = False):
        """
        로그 메시지를 파일에 기록하고,
        print_also=True일 경우 콘솔에도 출력합니다.
        """
        # 메시지 앞뒤 공백을 제거하고, 개행 문자가 없으면 추가합니다.
        message = message.strip()                # 메시지 공백 제거
        if not message:                          # 메시지가 비어있으면
            return                               # 함수 종료

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 현재 시간 타임스탬프 생성
        line = f"{timestamp} | {message}\n"      # 타임스탬프와 메시지 결합

        self.log_file.write(line)                # 로그 파일에 기록
        self.log_file.flush()                    # 버퍼 즉시 플러시 (데이터 손실 방지)

        # 콘솔 출력 옵션 처리 (None이면 기본값 사용)
        should_print = print_also if print_also is not None else self.print_also
        if should_print:
            # 에러 메시지인 경우
            if print_error:
                # 재귀 호출을 피하기 위해 원본 표준 출력을 사용합니다.
                self.original_stdout.write(f"\033[91m{line}\033[0m")  # 빨간색으로 에러 출력
            # 일반 메시지인 경우
            else:
                self.original_stdout.write(line) # 일반 출력


    # 분기점 기록 함수 정의
    def write_separator(self, separator: str = "=========="):
        """
        로그 파일에 분기점을 기록합니다.
        질의-응답 종료 시 또는 주요 이벤트 후에 사용합니다.

        Args:
            separator: 분기점 문자열 (기본값: "==========")
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 현재 시간 타임스탬프 생성
        line = f"{timestamp} | {separator}\n"    # 타임스탬프와 분기점 결합

        self.log_file.write(line)                # 로그 파일에 기록
        self.log_file.flush()                    # 버퍼 즉시 플러시 (데이터 손실 방지)

        # 콘솔에도 출력 (기본 설정에 따름)
        if self.print_also:
            self.original_stdout.write(line)     # 분기점 출력
    
    
    # 플러시 함수 정의
    def flush(self):
        """
        스트림 인터페이스에 필요한 flush 메서드입니다.
        """
        self.log_file.flush()   # 로그 파일 버퍼 플러시


    # 리다이렉션 시작 함수 정의
    def start_redirect(self):
        """
        표준 출력(stdout)과 표준 에러(stderr)를 이 로거 인스턴스로 리다이렉션합니다.
        """
        self.write(">> 표준 출력 및 오류를 로그 파일로 리디렉션 시작", print_also=True)  # 리다이렉션 시작 로그
        sys.stdout = self   # 표준 출력을 로거로 리디렉션
        sys.stderr = self   # 표준 에러를 로거로 리디렉션


    # 리다이렉션 중지 함수 정의
    def stop_redirect(self):
        """
        표준 출력(stdout)과 표준 에러(stderr)를 원상 복구합니다.
        """
        self.write(">> 로그 리디렉션 종료", print_also=True)  # 리다이렉션 중지 로그
        sys.stdout = self.original_stdout        # 표준 출력 원상 복구
        sys.stderr = self.original_stderr        # 표준 에러 원상 복구
    
    
    # tqdm 진행률 표시 함수 정의
    def tqdm(self, iterable=None, total=None, desc=None, **kwargs):
        """
        진행률 표시 - 10%마다만 로그 기록

        Args:
            iterable: 반복 가능한 객체
            total: 전체 항목 수 (iterable이 None일 때 필수)
            desc: 진행률 설명
            **kwargs: tqdm의 기타 파라미터

        사용법:
            for item in logger.tqdm(items, desc="데이터 처리"):
                # work
        """
        if not TQDM_AVAILABLE:
            self.write("tqdm이 설치되지 않았습니다. 기본 반복을 사용합니다.", print_error=True)
            # tqdm 없이 기본 반복 - 10%마다 진행률 로그
            if iterable:
                total = total or (len(iterable) if hasattr(iterable, '__len__') else None)
                for i, item in enumerate(iterable, 1):
                    if total and i % max(1, total // 10) == 0:
                        percent = (i / total * 100)
                        self.write(f"{desc or 'Progress'}: {percent:.0f}% ({i}/{total})")
                    yield item
                if total:
                    self.write(f"{desc or 'Progress'}: 100% ({total}/{total}) - 완료")
            return

        # tqdm 사용 - 콘솔에는 진행률 바 표시, 로그에는 10%마다만 기록
        desc = desc or "Progress"
        last_percent = self._tqdm_last_percent.get(desc, -10)
        total = total or (len(iterable) if iterable and hasattr(iterable, '__len__') else None)

        try:
            # tqdm 진행률 바 생성 (콘솔에 표시)
            from tqdm import tqdm as tqdm_orig
            pbar = tqdm_orig(iterable=iterable, total=total, desc=desc, **kwargs)

            for item in pbar:
                # 10% 단위로만 로그 기록
                if total:
                    percent = (pbar.n / total * 100)
                    if percent - last_percent >= 10:
                        self.write(f"{desc}: {percent:.0f}% ({pbar.n}/{total})")
                        last_percent = percent
                        self._tqdm_last_percent[desc] = last_percent
                yield item

            # 완료 로그
            if total:
                self.write(f"{desc}: 100% ({total}/{total}) - 완료")

            # 완료 후 추적 변수 초기화
            self._tqdm_last_percent.pop(desc, None)

        except Exception as e:
            # 에러 발생 시 마지막 진행률 기록
            if total and 'pbar' in locals():
                current_percent = (pbar.n / total * 100)
                self.write(f"{desc}: 에러 발생 (마지막 진행률: {current_percent:.0f}% - {pbar.n}/{total})", print_error=True)
            self._tqdm_last_percent.pop(desc, None)
            raise

    
    # 로거 종료 함수 정의
    def close(self):
        """
        로그 파일을 닫습니다.
        """
        # 중복 close 방지
        if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
            self.log_file.close()                # 로그 파일 닫기

    # 소멸자 정의
    def __del__(self):
        """
        소멸자 - 파일 자동 닫기
        """
        self.close()

    # with 문 지원
    def __enter__(self):
        """
        with 문 지원
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with 문 종료 시 자동 close
        """
        self.close()
        return False