from unittest.mock import patch

import pandas as pd
import os
import sys
import importlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKFLOW_MANAGER_MODULE = importlib.import_module('src.lawdigest_data_pipeline.WorkFlowManager')

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager


def _mk_minimal_bill_df(proposer_kind: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "proposeDate": ["2026-01-01"],
            "bill_id": ["BILL-001"],
            "bill_name": ["테스트 법안"],
            "summary": ["테스트 요약"],
            "proposer_kind": [proposer_kind],
        }
    )


@patch.object(WORKFLOW_MANAGER_MODULE, "DatabaseManager")
@patch.object(WORKFLOW_MANAGER_MODULE, "DataFetcher")
def test_ai_test_update_bills_data_no_db_required(mock_fetcher_cls, mock_db_cls):
    mock_fetcher = mock_fetcher_cls.return_value
    mock_fetcher.fetch_bills_data.return_value = _mk_minimal_bill_df("위원장")

    workflow = WorkFlowManager(mode="ai_test")
    result = workflow.update_bills_data(start_date=None, end_date="2026-01-02", age="22")

    assert result is None
    assert mock_db_cls.call_count == 0


@patch.object(WORKFLOW_MANAGER_MODULE, "DatabaseManager")
@patch.object(WORKFLOW_MANAGER_MODULE, "DataFetcher")
def test_ai_test_fetch_bills_step_no_db_required(mock_fetcher_cls, mock_db_cls):
    mock_fetcher = mock_fetcher_cls.return_value
    mock_fetcher.fetch_bills_data.return_value = _mk_minimal_bill_df("위원장")

    workflow = WorkFlowManager(mode="ai_test")
    result = workflow.fetch_bills_step(start_date=None, end_date="2026-01-02", age="22")

    assert isinstance(result, pd.DataFrame)
    assert mock_db_cls.call_count == 0
