import sys
import os
import pytest

# 프로젝트 루트 디렉토리의 src 폴더를 sys.path에 추가
# 이를 통해 테스트 파일에서 src 패키지 내부의 모듈을 바로 임포트할 수 있습니다.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
