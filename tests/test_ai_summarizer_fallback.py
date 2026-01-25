"""
AI Summarizer Fallback 로직 테스트

이 테스트는 AISummarizer의 Fallback 로직이 정상적으로 동작하는지 검증합니다.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from lawdigest_data_pipeline.AISummarizer import AISummarizer


class TestAISummarizerFallback:
    """AISummarizer Fallback 로직 테스트"""
    
    @pytest.fixture
    def summarizer(self):
        """테스트용 AISummarizer 인스턴스"""
        with patch('dotenv.load_dotenv'):
            summarizer = AISummarizer()
            summarizer.gemini_api_key = "test_gemini_key"
            summarizer.api_key = "test_openai_key"
            return summarizer
    
    @pytest.fixture
    def sample_messages(self):
        """테스트용 메시지"""
        from langchain_core.messages import SystemMessage, HumanMessage
        return [
            SystemMessage(content="Test system message"),
            HumanMessage(content="Test human message")
        ]
    
    @pytest.fixture
    def sample_bill_info(self):
        """테스트용 법안 정보"""
        return {
            'billNumber': '2101234',
            'billName': '테스트 법률 개정안'
        }
    
    def test_fallback_gemini_success(self, summarizer, sample_messages, sample_bill_info):
        """1차 시도 Gemini API 성공 시나리오"""
        # Gemini API Mock
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_gemini:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = "Gemini API 응답 내용"
            mock_llm.invoke.return_value = mock_response
            mock_gemini.return_value = mock_llm
            
            # 실행
            result = summarizer._invoke_llm_with_fallback(
                sample_messages, 
                "gemini-3-flash-preview",
                sample_bill_info
            )
            
            # 검증
            assert result == "Gemini API 응답 내용"
            assert len(summarizer.failed_bills) == 0
            mock_gemini.assert_called_once()
    
    def test_fallback_gemini_to_gpt(self, summarizer, sample_messages, sample_bill_info):
        """Gemini 실패 → GPT-5-mini 성공 시나리오"""
        # Gemini API 실패, GPT API 성공 Mock
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_gemini, \
             patch('langchain_community.chat_models.ChatOpenAI') as mock_gpt:
            
            # Gemini 실패 설정
            mock_gemini_llm = Mock()
            mock_gemini_llm.invoke.side_effect = Exception("Gemini quota exceeded")
            mock_gemini.return_value = mock_gemini_llm
            
            # GPT 성공 설정
            mock_gpt_llm = Mock()
            mock_gpt_response = Mock()
            mock_gpt_response.content = "GPT-5-mini API 응답 내용"
            mock_gpt_llm.invoke.return_value = mock_gpt_response
            mock_gpt.return_value = mock_gpt_llm
            
            # 실행
            result = summarizer._invoke_llm_with_fallback(
                sample_messages,
                "gemini-3-flash-preview",
                sample_bill_info
            )
            
            # 검증
            assert result == "GPT-5-mini API 응답 내용"
            assert len(summarizer.failed_bills) == 0
            mock_gemini.assert_called_once()
            mock_gpt.assert_called_once()
    
    def test_fallback_all_fail(self, summarizer, sample_messages, sample_bill_info):
        """모든 API 호출 실패 시나리오"""
        # 모든 API 실패 Mock
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_gemini, \
             patch('langchain_community.chat_models.ChatOpenAI') as mock_gpt:
            
            # Gemini 실패 설정
            mock_gemini_llm = Mock()
            mock_gemini_llm.invoke.side_effect = Exception("Gemini quota exceeded")
            mock_gemini.return_value = mock_gemini_llm
            
            # GPT 실패 설정
            mock_gpt_llm = Mock()
            mock_gpt_llm.invoke.side_effect = Exception("GPT API error")
            mock_gpt.return_value = mock_gpt_llm
            
            # 실행
            result = summarizer._invoke_llm_with_fallback(
                sample_messages,
                "gemini-3-flash-preview",
                sample_bill_info
            )
            
            # 검증
            assert result is None
            assert len(summarizer.failed_bills) == 1
            assert summarizer.failed_bills[0]['billNumber'] == '2101234'
            assert summarizer.failed_bills[0]['billName'] == '테스트 법률 개정안'
            mock_gemini.assert_called_once()
            mock_gpt.assert_called_once()
    
    def test_fallback_gpt_primary_success(self, summarizer, sample_messages, sample_bill_info):
        """1차 시도 GPT API 성공 시나리오"""
        # GPT API Mock
        with patch('langchain_community.chat_models.ChatOpenAI') as mock_gpt:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = "GPT API 응답 내용"
            mock_llm.invoke.return_value = mock_response
            mock_gpt.return_value = mock_llm
            
            # 실행
            result = summarizer._invoke_llm_with_fallback(
                sample_messages,
                "gpt-5",
                sample_bill_info
            )
            
            # 검증
            assert result == "GPT API 응답 내용"
            assert len(summarizer.failed_bills) == 0
            mock_gpt.assert_called_once()
    
    def test_ai_title_summarize_with_fallback(self, summarizer):
        """AI_title_summarize 메서드 Fallback 적용 테스트"""
        # 샘플 데이터 생성
        df_bills = pd.DataFrame([
            {
                'billNumber': '2101234',
                'billName': '테스트 법률 개정안',
                'summary': '이 법안은 테스트를 위한 법안입니다.',
                'proposers': '홍길동 의원',
                'briefSummary': None
            }
        ])
        
        # Fallback 메서드 Mock
        with patch.object(summarizer, '_invoke_llm_with_fallback') as mock_fallback:
            mock_fallback.return_value = "테스트 목적을 위한 테스트 법률 개정안"
            
            # 실행
            result_df = summarizer.AI_title_summarize(df_bills, model="gemini-3-flash-preview")
            
            # 검증
            assert result_df.loc[0, 'briefSummary'] == "테스트 목적을 위한 테스트 법률 개정안"
            mock_fallback.assert_called_once()
    
    def test_ai_content_summarize_with_fallback(self, summarizer):
        """AI_content_summarize 메서드 Fallback 적용 테스트"""
        # 샘플 데이터 생성
        df_bills = pd.DataFrame([
            {
                'billNumber': '2101234',
                'billName': '테스트 법률 개정안',
                'summary': '이 법안은 테스트를 위한 법안입니다.',
                'proposers': '홍길동 의원',
                'proposerKind': '의원',
                'gptSummary': None
            }
        ])
        
        # Fallback 메서드 Mock
        with patch.object(summarizer, '_invoke_llm_with_fallback') as mock_fallback:
            mock_fallback.return_value = "홍길동 의원이 발의한 테스트 법률 개정안의 내용 및 목적은 다음과 같습니다: 테스트"
            
            # 실행
            result_df = summarizer.AI_content_summarize(df_bills, model="gemini-3-flash-preview")
            
            # 검증
            assert result_df.loc[0, 'gptSummary'] == "홍길동 의원이 발의한 테스트 법률 개정안의 내용 및 목적은 다음과 같습니다: 테스트"
            mock_fallback.assert_called_once()
    
    def test_failed_bills_tracking(self, summarizer, sample_messages):
        """실패한 법안 추적 기능 테스트"""
        # 여러 법안에 대해 실패 시나리오
        bills_info = [
            {'billNumber': '2101234', 'billName': '법안1'},
            {'billNumber': '2101235', 'billName': '법안2'},
            {'billNumber': '2101236', 'billName': '법안3'}
        ]
        
        # 모든 API 실패 Mock
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_gemini, \
             patch('langchain_community.chat_models.ChatOpenAI') as mock_gpt:
            
            mock_gemini_llm = Mock()
            mock_gemini_llm.invoke.side_effect = Exception("Gemini error")
            mock_gemini.return_value = mock_gemini_llm
            
            mock_gpt_llm = Mock()
            mock_gpt_llm.invoke.side_effect = Exception("GPT error")
            mock_gpt.return_value = mock_gpt_llm
            
            # 여러 법안 처리
            for bill_info in bills_info:
                summarizer._invoke_llm_with_fallback(
                    sample_messages,
                    "gemini-3-flash-preview",
                    bill_info
                )
            
            # 검증
            assert len(summarizer.failed_bills) == 3
            assert all(bill['billNumber'] in ['2101234', '2101235', '2101236'] 
                      for bill in summarizer.failed_bills)
