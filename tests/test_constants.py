import pytest
from lawdigest_data_pipeline.constants import BillStageType, ProposerKindType

class TestBillStageType:
    def test_predefined_stages_order(self):
        """Test the order of predefined stages matches Java logic"""
        assert BillStageType.WITHDRAWAL.order == 0
        assert BillStageType.RECEIPT.order == 1
        assert BillStageType.PROMULGATION.order == 7

    def test_from_value_predefined(self):
        """Test retrieving predefined stages from value"""
        stage = BillStageType.from_value("접수")
        assert stage.key == "접수"
        assert stage.value == "접수"
        assert stage.order == 1
        assert stage.predefined is True
        assert stage == BillStageType.RECEIPT

    def test_from_value_new(self):
        """Test creating new stage from unknown value"""
        stage = BillStageType.from_value("새로운단계")
        assert stage.key == "새로운단계"
        assert stage.value == "새로운단계"
        assert stage.order == -1
        assert stage.predefined is False

    def test_can_update_stage(self):
        """Test stage update logic"""
        # Dictionary of test cases (current, next, expected)
        test_cases = [
            # 1. Next is not predefined -> Always True
            (BillStageType.RECEIPT, BillStageType.from_value("NewStage"), True),
            
            # 2. Current is not predefined -> Always True
            (BillStageType.from_value("OldStage"), BillStageType.RECEIPT, True),
            
            # 3. Both predefined
            # 3.1 Order increases -> True
            (BillStageType.RECEIPT, BillStageType.STANDING_COMMITTEE_RECEIPT, True),
            (BillStageType.RECEIPT, BillStageType.PROMULGATION, True),
            
            # 3.2 Order decreases or equal -> False
            (BillStageType.STANDING_COMMITTEE_RECEIPT, BillStageType.RECEIPT, False),
            (BillStageType.RECEIPT, BillStageType.RECEIPT, False),
        ]

        for current, next_stage, expected in test_cases:
            assert BillStageType.can_update_stage(current, next_stage) == expected, \
                f"Failed for {current.value} -> {next_stage.value}"

class TestProposerKindType:
    def test_from_string_valid(self):
        assert ProposerKindType.from_string("의원") == ProposerKindType.CONGRESSMAN
        assert ProposerKindType.from_string("위원장") == ProposerKindType.CHAIRMAN

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            ProposerKindType.from_string("Unknown")
        
        with pytest.raises(ValueError):
            ProposerKindType.from_string(None)
