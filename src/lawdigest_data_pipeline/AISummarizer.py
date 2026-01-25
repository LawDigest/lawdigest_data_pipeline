import pandas as pd
from IPython.display import clear_output
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv
import logging

class AISummarizer:

    def __init__(self):
        self.input_data = None
        self.output_data = None
        self.failed_bills = []  # API 호출 실패한 법안 추적
        self.style_prompt = """
            위 법률개정안 텍스트에서 달라지는 핵심 내용을 항목별로 정리해줘. 형식은 다음과 같아:

            1. **[항목명]**: 핵심 내용 간단히 서술 (2~3줄)
            2. **[항목명]**: 핵심 내용 간단히 서술 (2~3줄)

            법안이나 정책 설명에 쓰일 수 있게 친절하게 공식적으로 작성하고, 이해하기 쉽게 서술식으로 작성해줘. 
            항목명은 반드시 볼드체 처리해. 핵심 내용을 간단히 서술한 문장에서는 무엇이 어떻게 바뀌었는지 나타내는 내용 혹은 숫자 값을 볼드체 처리해.
            원문 법률개정안 텍스트의 길이와 내용에 따라 최소 3개 최대 7개 사이의 항목으로 이해하기 쉽게 요약해.
            각 항목 사이에는 한 줄씩 줄바꿈을 넣어 가독성을 높여줘. 
            모든 항목 이후에는 법안의 취지를 설명하는 한 문장으로 마무리해. "
            """
        self.prompt_dict = {
            # 한글 키 (하위 호환성)
            '의원':  "너는 법률개정안을 이해하기 쉽게 요약해서 알려줘야 해. 반드시 \"{proposer}이 발의한 {title}의 내용 및 목적은 다음과 같습니다:\"로 문장을 시작해. {style}",
            '위원장': "너는 법률개정안을 이해하기 쉽게 요약해서 알려줘야 해. 반드시 \"{proposer}이 발의한 {title}의 내용 및 목적은 다음과 같습니다:\"로 문장을 시작해. {style}",
            '정부':  "너는 법률개정안을 이해하기 쉽게 요약해서 알려줘야 해. 반드시 \"대한민국 {proposer}가 발의한 {title}의 내용 및 목적은 다음과 같습니다:\"로 문장을 시작해. {style}",
            # 영문 키 (DB 스키마에 맞춰 추가)
            'CONGRESSMAN':  "너는 법률개정안을 이해하기 쉽게 요약해서 알려줘야 해. 반드시 \"{proposer}이 발의한 {title}의 내용 및 목적은 다음과 같습니다:\"로 문장을 시작해. {style}",
            'CHAIRMAN': "너는 법률개정안을 이해하기 쉽게 요약해서 알려줘야 해. 반드시 \"{proposer}이 발의한 {title}의 내용 및 목적은 다음과 같습니다:\"로 문장을 시작해. {style}",
        }

        # 환경변수 로드 (환경변수 읽기 전에 반드시 먼저 호출)
        load_dotenv()
        
        # ChatGPT model via Langchain
        self.api_key = os.environ.get("APIKEY_OPENAI")
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)

    def _extract_text_from_response(self, response):
        """
        AI 응답에서 순수 텍스트만 추출
        
        Args:
            response: AI 모델의 응답 (str, list, dict 등 다양한 형태 가능)
            
        Returns:
            str: 추출된 순수 텍스트
        """
        # 이미 문자열인 경우
        if isinstance(response, str):
            return response
        
        # 리스트인 경우 (예: [{'type': 'text', 'text': '...'}])
        if isinstance(response, list):
            texts = []
            for item in response:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item['text'])
                elif isinstance(item, str):
                    texts.append(item)
            return '\n'.join(texts) if texts else str(response)
        
        # 딕셔너리인 경우
        if isinstance(response, dict):
            if 'text' in response:
                return response['text']
            elif 'content' in response:
                return self._extract_text_from_response(response['content'])
        
        # 기타 경우 문자열로 변환
        return str(response)

    def _invoke_llm_with_fallback(self, messages, primary_model, bill_info=None):
        """
        Fallback 로직이 적용된 LLM 호출 메서드
        
        Args:
            messages: LLM에 전달할 메시지 리스트
            primary_model: 1차로 시도할 모델명 (예: 'gemini-3-flash-preview')
            bill_info: 실패 추적을 위한 법안 정보 딕셔너리 (optional)
            
        Returns:
            str: AI 응답 내용, 모든 API 실패 시 None 반환
        """
        fallback_model = "gpt-5-mini"  # 비용 절감형 대체 모델
        
        # 1차 시도: Gemini API
        if primary_model.lower().startswith("gemini"):
            try:
                self.logger.info(f"[1차 시도] Gemini API 호출 - 모델: {primary_model}")
                llm = ChatGoogleGenerativeAI(model=primary_model, google_api_key=self.gemini_api_key, temperature=1)
                response = llm.invoke(messages).content
                # 응답이 리스트/딕셔너리 형태인 경우 텍스트만 추출
                return self._extract_text_from_response(response)
                
            except Exception as e:
                self.logger.warning(f"[1차 실패] Gemini API 호출 실패: {str(e)}")
                if bill_info:
                    self.logger.warning(f"  법안: {bill_info.get('bill_name', 'Unknown')} (ID: {bill_info.get('bill_id', 'Unknown')})")
                
                # 2차 시도: OpenAI GPT-5-mini API
                try:
                    self.logger.info(f"[2차 시도] OpenAI GPT-5-mini API 호출")
                    llm_fallback = ChatOpenAI(model=fallback_model, openai_api_key=self.api_key, temperature=1)
                    response = llm_fallback.invoke(messages).content
                    self.logger.info(f"[2차 성공] OpenAI GPT-5-mini로 성공")
                    return self._extract_text_from_response(response)
                    
                except Exception as e2:
                    self.logger.error(f"[2차 실패] OpenAI GPT-5-mini API 호출 실패: {str(e2)}")
                    if bill_info:
                        self.logger.error(f"  법안: {bill_info.get('bill_name', 'Unknown')} (ID: {bill_info.get('bill_id', 'Unknown')})")
                        self.failed_bills.append({
                            'bill_id': bill_info.get('bill_id'),
                            'bill_name': bill_info.get('bill_name'),
                            'error': f"Gemini: {str(e)}, GPT: {str(e2)}"
                        })
                    self.logger.error("[최종 실패] 모든 API 호출 실패 - 해당 데이터는 처리하지 않음")
                    return None
        
        # primary_model이 GPT 계열인 경우
        else:
            try:
                self.logger.info(f"[1차 시도] OpenAI API 호출 - 모델: {primary_model}")
                llm = ChatOpenAI(model=primary_model, openai_api_key=self.api_key, temperature=1)
                response = llm.invoke(messages).content
                return self._extract_text_from_response(response)
                
            except Exception as e:
                self.logger.warning(f"[1차 실패] OpenAI API 호출 실패: {str(e)}")
                if bill_info:
                    self.logger.warning(f"  법안: {bill_info.get('bill_name', 'Unknown')} (ID: {bill_info.get('bill_id', 'Unknown')})")
                
                # 2차 시도: Gemini API
                try:
                    self.logger.info(f"[2차 시도] Gemini API 호출")
                    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
                    llm_fallback = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", google_api_key=self.gemini_api_key, temperature=1)
                    response = llm_fallback.invoke(messages).content
                    self.logger.info(f"[2차 성공] Gemini API로 성공")
                    return self._extract_text_from_response(response)
                    
                except Exception as e2:
                    self.logger.error(f"[2차 실패] Gemini API 호출 실패: {str(e2)}")
                    if bill_info:
                        self.logger.error(f"  법안: {bill_info.get('bill_name', 'Unknown')} (ID: {bill_info.get('bill_id', 'Unknown')})")
                        self.failed_bills.append({
                            'bill_id': bill_info.get('bill_id'),
                            'bill_name': bill_info.get('bill_name'),
                            'error': f"GPT: {str(e)}, Gemini: {str(e2)}"
                        })
                    self.logger.error("[최종 실패] 모든 API 호출 실패 - 해당 데이터는 처리하지 않음")
                    return None

    def AI_title_summarize(self, df_bills, model=None):
        """
        법안 제목 요약 생성 (Fallback 로직 적용)
        
        Args:
            df_bills: 법안 데이터 DataFrame
            model: 사용할 AI 모델명 (None이면 환경변수에서 가져옴)
            
        Returns:
            DataFrame: briefSummary가 추가된 DataFrame
        """
        if model is None:
            model = os.environ.get("TITLE_SUMMARIZATION_MODEL")
        
        print(f"\n[AI 제목 요약 진행 중... (Model: {model})]")
        
        # 'brief_summary' 컬럼이 공백인 경우에만 요약문을 생성
        rows_to_process = df_bills[df_bills['brief_summary'].isnull()]
        total = len(rows_to_process)
        
        if total == 0:
            print("[모든 법안에 대한 제목 요약이 이미 존재합니다.]")
            self.output_data = df_bills
            return df_bills
        
        count = 0
        success_count = 0
        show_count = 0

        for index, row in rows_to_process.iterrows():
            count += 1
            print(f"현재 진행률: {count}/{total} | {round(count/total*100, 2)}%")

            content, title, id, proposer = row['summary'], row['bill_name'], row['bill_id'], row['proposers']
            print('-'*10)

            task = f"\n위 내용의 핵심을 한 문장으로 요약한 제목을 작성할 것. 제목은 반드시 {title}으로 끝나야 함."
            print(f"task: {task}")
            print('-'*10)

            messages = [
                SystemMessage(content="입력하는 법률개정안 내용의 핵심을 한 문장으로 짧게 요약한 제목을 한 문장으로 작성할 것. 제목은 반드시 법률개정안 이름으로 끝나야 함.\n\n법률개정안의 내용을 한눈에 알아볼 수 있게 핵심을 요약한 제목을 작성. 반드시 '~하기 위한 ~법안'와 같은 형식으로 작성. 반드시 한 문장으로 작성. 법안의 취지를 중심으로 최대한 짧고 간결하게 요약\n"),
                HumanMessage(content=str(content) + str(task))
            ]

            # Fallback 로직 적용
            bill_info = {'bill_id': id, 'bill_name': title}
            chat_response = self._invoke_llm_with_fallback(messages, model, bill_info)
            
            if chat_response is None:
                print(f"[SKIP] {title} - 모든 API 호출 실패로 제목 요약 생성 건너뜀")
                continue

            # AI 응답 미리보기 (첫 200자만)
            preview = str(chat_response)[:200] + "..." if len(str(chat_response)) > 200 else str(chat_response)
            print(f"✅ 요약 생성 완료 (길이: {len(str(chat_response))}자)")
            print(f"   미리보기: {preview}")

            # 추출된 요약문을 'brief_summary' 컬럼에 저장
            df_bills.loc[df_bills['bill_id'] == id, 'brief_summary'] = chat_response
            success_count += 1
            show_count += 1

            if show_count % 5 == 0:
                clear_output()
        
        print(f"\n[법안 {count}건 처리 완료 - 성공: {success_count}건, 실패: {count - success_count}건]")
        
        if len(self.failed_bills) > 0:
            print(f"\n[경고] {len(self.failed_bills)}건의 법안이 API 호출 실패로 처리되지 않았습니다.")
            print("실패한 법안 목록:")
            for failed in self.failed_bills[:5]:  # 최대 5개만 출력
                print(f"  - {failed['bill_name']} (ID: {failed['bill_id']})")
            if len(self.failed_bills) > 5:
                print(f"  ... 외 {len(self.failed_bills) - 5}건")

        clear_output()
        print("[AI 제목 요약 완료]")

        self.output_data = df_bills
        return df_bills

    def AI_content_summarize(self, df_bills, model=None):
        """
        법안 내용 요약 생성 (Fallback 로직 적용)
        df_bills를 입력받아 'proposerKind' 컬럼을 기준으로 발의주체별 프롬프트를 자동으로 적용하여 AI 요약을 생성합니다.
        
        Args:
            df_bills: 법안 데이터 DataFrame
            model: 사용할 AI 모델명 (None이면 환경변수에서 가져옴)
            
        Returns:
            DataFrame: gptSummary가 추가된 DataFrame
        """
        if model is None:
            model = os.environ.get("CONTENT_SUMMARIZATION_MODEL")

        print(f"\n[AI 내용 요약 진행 중... (Model: {model})]")

        rows_to_process = df_bills[df_bills['gpt_summary'].isnull()]
        total = len(rows_to_process)
        
        if total == 0:
            print("[모든 법안에 대한 AI 요약이 이미 존재합니다.]")
            self.output_data = df_bills
            return df_bills

        count = 0
        success_count = 0
        
        for index, row in rows_to_process.iterrows():
            count += 1
            print(f"현재 진행률: {count}/{total} | {round(count/total*100, 2)}%")

            content, title, bill_id, proposer = row['summary'], row['bill_name'], row['bill_id'], row['proposers']
            proposer_kind = row['proposer_kind'] # 'CONGRESSMAN', 'CHAIRMAN', '정부'
            
            print('-'*10)
            
            # 1. 'proposerKind' 값을 키로 사용해 prompt_dict에서 직접 템플릿 가져오기
            #    .get()을 사용하여 해당 키가 없는 경우에도 오류 없이 안전하게 처리합니다.
            prompt_template = self.prompt_dict.get(proposer_kind)
            
            if not prompt_template:
                print(f"경고: '{proposer_kind}'에 해당하는 프롬프트 템플릿이 없습니다. (법안: {title})")
                continue

            # 2. 선택된 프롬프트 템플릿 포맷팅
            system_prompt = prompt_template.format(proposer=proposer, title=title, style=self.style_prompt)
            
            task = f"\n위 내용은 {title}이야. 이 법률개정안에서 무엇이 달라졌는지 제안이유 및 주요내용을 쉽게 요약해줘."
            print(f"task: {task}")
            print('-'*10)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=str(content) + str(task))
            ]

            # Fallback 로직 적용
            bill_info = {'bill_id': bill_id, 'bill_name': title}
            chat_response = self._invoke_llm_with_fallback(messages, model, bill_info)
            
            if chat_response is None:
                print(f"[SKIP] {title} - 모든 API 호출 실패로 내용 요약 생성 건너뜀")
                continue
                
            # AI 응답 미리보기 (첫 200자만)
            preview = str(chat_response)[:200] + "..." if len(str(chat_response)) > 200 else str(chat_response)
            print(f"✅ 요약 생성 완료 (길이: {len(str(chat_response))}자)")
            print(f"   미리보기: {preview}")
            df_bills.loc[index, 'gpt_summary'] = chat_response
            success_count += 1

            if count % 5 == 0 and count < total:
                # clear_output(wait=True)
                pass
        
        # clear_output()
        print(f"\n[법안 {count}건 처리 완료 - 성공: {success_count}건, 실패: {count - success_count}건]")
        
        if len(self.failed_bills) > 0:
            print(f"\n[경고] {len(self.failed_bills)}건의 법안이 API 호출 실패로 처리되지 않았습니다.")
            print("실패한 법안 목록:")
            for failed in self.failed_bills[:5]:  # 최대 5개만 출력
                print(f"  - {failed['bill_name']} (ID: {failed['bill_id']})")
            if len(self.failed_bills) > 5:
                print(f"  ... 외 {len(self.failed_bills) - 5}건")
        
        print("[AI 내용 요약 완료]")

        self.output_data = df_bills
        return df_bills

    def AI_model_test(date=None, title_model=None, content_model=None):
        pass
