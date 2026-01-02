from enum import Enum, auto
from typing import Optional, Any

class ProposerKindType(Enum):
    """
    Java ProposerKindType Enum 포팅.
    src/main/java/com/everyones/lawmaking/domain/entity/ProposerKindType.java
    """
    CONGRESSMAN = "의원"
    CHAIRMAN = "위원장"

    @classmethod
    def from_string(cls, value: Optional[str]) -> "ProposerKindType":
        """
        문자열 값으로 Enum 인스턴스를 반환합니다.

        Args:
            value (str): 찾을 문자열 값 (예: "의원")

        Returns:
            ProposerKindType: 일치하는 Enum 인스턴스

        Raises:
            ValueError: 값이 None이거나 일치하는 타입이 없을 경우
        """
        if value is None:
            raise ValueError("Proposer kind type cannot be null.")
        
        for k in cls:
            if k.value == value:
                return k
        raise ValueError(f"Unknown proposer kind type: {value}")


class BillStageType:
    """
    Java BillStageType Class/Enum 포팅.
    src/main/java/com/everyones/lawmaking/global/constant/BillStageType.java
    """
    # 사전 정의된 단계 (순서, 키, 값)    
    WITHDRAWAL = (0, "철회", "철회")
    RECEIPT = (1, "접수", "접수")
    STANDING_COMMITTEE_RECEIPT = (2, "위원회 심사", "소관위접수")
    STANDING_COMMITTEE_AUDIT_BEFORE = (3, "위원회 심사", "위원회 심사")
    SYSTEMATIC_REVIEW = (4, "체계자구 심사", "체계자구 심사")
    PLENARY_SESSION = (5, "본회의 심의", "본회의 심의")
    GOVERNMENT_TRANSFER = (6, "정부이송", "정부이송")
    PROMULGATION = (7, "공포", "공포")

    _VALUE_MAP = {}
    _PREDEFINED_STAGES = []

    def __init__(self, order: int, key: str, value: str, predefined: bool = True):
        """
        BillStageType 초기화.

        Args:
            order (int): 단계 순서 (사전 정의된 단계 비교용)
            key (str): 단계 키 (대표 명칭)
            value (str): 단계 값 (실제 데이터 상의 명칭)
            predefined (bool): 사전 정의 여부
        """
        self.order = order
        self.key = key
        self.value = value
        self.predefined = predefined

    @classmethod
    def _initialize(cls):
        """
        사전 정의된 인스턴스를 초기화하고 클래스 속성을 덮어씌웁니다.
        """
        cls.WITHDRAWAL = cls(*cls.WITHDRAWAL)
        cls.RECEIPT = cls(*cls.RECEIPT)
        cls.STANDING_COMMITTEE_RECEIPT = cls(*cls.STANDING_COMMITTEE_RECEIPT)
        cls.STANDING_COMMITTEE_AUDIT_BEFORE = cls(*cls.STANDING_COMMITTEE_AUDIT_BEFORE)
        cls.SYSTEMATIC_REVIEW = cls(*cls.SYSTEMATIC_REVIEW)
        cls.PLENARY_SESSION = cls(*cls.PLENARY_SESSION)
        cls.GOVERNMENT_TRANSFER = cls(*cls.GOVERNMENT_TRANSFER)
        cls.PROMULGATION = cls(*cls.PROMULGATION)

        cls._PREDEFINED_STAGES = [
            cls.WITHDRAWAL,
            cls.RECEIPT,
            cls.STANDING_COMMITTEE_RECEIPT,
            cls.STANDING_COMMITTEE_AUDIT_BEFORE,
            cls.SYSTEMATIC_REVIEW,
            cls.PLENARY_SESSION,
            cls.GOVERNMENT_TRANSFER,
            cls.PROMULGATION
        ]

        for stage in cls._PREDEFINED_STAGES:
            cls._VALUE_MAP[stage.value] = stage

    @classmethod
    def from_value(cls, value: str) -> "BillStageType":
        """
        값(value)으로 BillStageType을 찾습니다.
        사전 정의된 단계에 없으면 새로운 비정규(Non-predefined) BillStageType을 생성하여 반환합니다.

        Args:
            value (str): 찾을 단계의 값

        Returns:
            BillStageType: 해당 값에 매핑되는 BillStageType 인스턴스
        """
        if not cls._VALUE_MAP:
            cls._initialize()
            
        stage = cls._VALUE_MAP.get(value)
        if stage:
            return stage
        
        # 사전 정의된 단계에 없는 경우 새로운 단계 생성
        # key와 value를 동일하게 설정, order는 -1
        return cls(-1, value, value, predefined=False)

    @classmethod
    def can_update_stage(cls, current: "BillStageType", next_stage: "BillStageType") -> bool:
        """
        현재 단계에서 다음 단계로 업데이트가 가능한지 확인합니다.

        Args:
            current (BillStageType): 현재 단계
            next_stage (BillStageType): 변경하려는 다음 단계

        Returns:
            bool: 업데이트 가능 여부 (True/False)
        """
        # 대상 단계가 사전 정의되지 않은 경우 항상 업데이트 가능
        if not next_stage.predefined:
            return True

        # 현재 단계가 사전 정의되지 않은 경우, 사전 정의된 단계로 항상 업데이트 가능
        if not current.predefined:
            return True

        # 둘 다 사전 정의된 단계인 경우, 순서가 증가해야만 업데이트 가능
        return current.order < next_stage.order

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BillStageType):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"BillStageType(order={self.order}, key='{self.key}', value='{self.value}', predefined={self.predefined})"

# 정적 멤버 초기화
BillStageType._initialize()
