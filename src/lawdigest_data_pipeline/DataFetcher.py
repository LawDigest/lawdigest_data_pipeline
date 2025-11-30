import requests
import pandas as pd
from xml.etree import ElementTree
import time
from datetime import datetime, timedelta
from IPython.display import clear_output
import os
from dotenv import load_dotenv
from tqdm import tqdm
import json
import re # fetch_bills_info (주석 해제 시) 대비

class DataFetcher:
    def __init__(self, url=None, filter_data=True):
        """
        DataFetcher 클래스 초기화.
        이제 생성 시점이 아닌, 각 fetch 메서드 호출 시 데이터를 수집합니다.
        
        Args:
            url (str, optional): 일부 메서드에서 사용할 기본 URL. Defaults to None.
            filter_data (bool, optional): 수집한 데이터의 컬럼을 필터링할지 여부. Defaults to True.
        """
        self.url = url  # 일부 메서드에서 공유 가능 (현재는 fetch_bills_info만 사용)
        self.filter_data = filter_data
        self.content = None  # 가장 최근에 수집된 데이터를 저장
        
        # 데이터 캐싱을 위한 인스턴스 변수
        self.df_bills = None
        self.df_lawmakers = None
        self.df_vote = None

        # 열린국회정보(json) 매퍼
        self.mapper_open_json = {
            "page_param": "pIndex",
            "size_param": "pSize",
            "data_path": ["ALLBILL", 1, "row"],
            "total_count_path": ["ALLBILL", 0, "head", 0, "list_total_count"],
            "result_code_path": ["ALLBILL", 0, "head", 1, "RESULT", "CODE"],
            "result_msg_path": ["ALLBILL", 0, "head", 1, "RESULT", "MESSAGE"],
            "success_code": "INFO-000",
        }

        # 열린국회정보(xml) 매퍼
        self.mapper_open_xml = {
            "page_param": "pIndex",
            "size_param": "pSize",
            "data_path": ".//row",
            "total_count_path": ".//list_total_count",
            "result_code_path": ".//RESULT/CODE",
            "result_msg_path": ".//RESULT/MESSAGE",
            "success_code": "INFO-000",
        }

        # 공공데이터포털(xml) 매퍼
        self.mapper_datagokr_xml = {
            "page_param": "pageNo",
            "size_param": "numOfRows",
            "data_path": ".//item",
            "total_count_path": ".//totalCount",
            "result_code_path": ".//resultCode",
            "result_msg_path": ".//resultMsg",
            "success_code": "00",
        }

        load_dotenv()
        # __init__에서 자동 데이터 수집 로직 제거

    # ------------------------------------------------------------------
    # Generic API helpers (변경 없음)
    # ------------------------------------------------------------------

    def _get_nested_value(self, data, path):
        current_level = data
        for key in path:
            if isinstance(current_level, dict):
                current_level = current_level.get(key)
            elif isinstance(current_level, list) and isinstance(key, int):
                try:
                    current_level = current_level[key]
                except IndexError:
                    return None
            else:
                return None
            if current_level is None:
                return None
        return current_level

    def _parse_response(self, response_content, format, mapper):
        data, total_count, result_code, result_msg = [], 0, None, "No message"
        try:
            if format == 'xml':
                root = ElementTree.fromstring(response_content)
                data = [{child.tag: child.text for child in item} for item in root.findall(mapper['data_path'])]
                total_count_elem = root.find(mapper['total_count_path'])
                total_count = int(total_count_elem.text) if total_count_elem is not None else 0
                result_code_elem = root.find(mapper['result_code_path'])
                result_code = result_code_elem.text if result_code_elem is not None else mapper['success_code'] # 코드가 없으면 성공으로 간주 (일부 API)
                result_msg_elem = root.find(mapper['result_msg_path'])
                result_msg = result_msg_elem.text if result_msg_elem is not None else "No message"
            elif format == 'json':
                response_json = json.loads(response_content)
                data = self._get_nested_value(response_json, mapper['data_path']) or []
                total_count = int(self._get_nested_value(response_json, mapper['total_count_path']) or 0)
                result_code = self._get_nested_value(response_json, mapper['result_code_path'])
                result_msg = self._get_nested_value(response_json, mapper['result_msg_path'])

            if result_code != mapper['success_code']:
                tqdm.write(f"   [API 응답 실패] 코드: {result_code}, 메시지: {result_msg}")
                return [], 0
            return data, total_count
        except Exception as e:
            tqdm.write(f"   ❌ 응답 파싱 중 오류 발생: {e}")
            print(f"응답 결과: {response_content}")
            return [], 0

    def fetch_data_generic(self, url, params, mapper, format='json', all_pages=True, verbose=False, max_retry=3):
        page_param = mapper.get('page_param')
        if all_pages and not page_param:
            raise ValueError("'all_pages=True'일 경우, 매퍼에 'page_param'이 정의되어야 합니다.")

        all_data = []
        current_params = params.copy()

        print("➡️  첫 페이지 요청하여 전체 데이터 개수 확인 중...")
        try:
            response = requests.get(url, params=current_params)
            response.raise_for_status()
            if verbose:
                print(response.content.decode('utf-8'))

            initial_data, total_count = self._parse_response(response.content, format, mapper)

            if total_count == 0 and not initial_data:
                print("⚠️  수집할 데이터가 없거나 API 응답에 문제가 있습니다.")
                return pd.DataFrame()

            all_data.extend(initial_data)

        except Exception as e:
            print(f"❌ 첫 페이지 요청 오류: {e}")
            return pd.DataFrame()

        if not all_pages:
            df = pd.DataFrame(all_data)
            print(f"\n🎉 다운로드 완료! 총 {len(df)}개의 데이터를 수집했습니다. 📊")
            return df

        with tqdm(total=total_count, initial=len(all_data), desc="📥 데이터 수집 중", unit="개") as pbar:
            retries_left = max_retry

            while len(all_data) < total_count:
                current_params[page_param] += 1

                try:
                    response = requests.get(url, params=current_params)
                    response.raise_for_status()
                    data, _ = self._parse_response(response.content, format, mapper)

                    if not data:
                        pbar.set_description("⚠️ API 응답에 더 이상 데이터가 없습니다")
                        break

                    all_data.extend(data)
                    pbar.update(len(data))
                    retries_left = max_retry

                except Exception as e:
                    pbar.write(f"❌ 오류 발생 (페이지 {current_params[page_param]}): {e}")
                    retries_left -= 1
                    if retries_left <= 0:
                        pbar.write("\n🚨 최대 재시도 횟수를 초과했습니다.")
                        break

        df = pd.DataFrame(all_data)
        print(f"\n🎉 다운로드 완료! 총 {len(df)}개의 데이터를 수집했습니다. 📊")
        return df
        
    def fetch_bills_data(self, start_date=None, end_date=None, age=None, start_ord=None, end_ord=None, **kwargs):
        """
        법안 주요 내용 데이터를 API에서 수집하는 함수.
        
        Args:
            start_date (str, optional): 검색 시작일 (YYYY-MM-DD). Defaults to 어제.
            end_date (str, optional): 검색 종료일 (YYYY-MM-DD). Defaults to 오늘.
            age (str, optional): 대수. Defaults to AGE 환경변수.
            start_ord (str, optional): 검색 시작 대수. Defaults to age.
            end_ord (str, optional): 검색 종료 대수. Defaults to age.
            **kwargs: API 요청에 전달할 추가 매개변수.
        """
        # self.params.get() 대신 메서드 인자를 직접 사용
        _start_date = start_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        _end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        _age = age or os.environ.get("AGE")
        _start_ord = start_ord or _age
        _end_ord = end_ord or _age

        api_key = os.environ.get("APIKEY_DATAGOKR")
        url = 'http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList'
        mapper = self.mapper_datagokr_xml

        # requests에 전달할 params 딕셔너리를 *이곳에서* 생성
        params = {
            'serviceKey': api_key,
            mapper['page_param']: 1,
            mapper['size_param']: 100,
            'start_ord': _start_ord,
            'end_ord': _end_ord,
            'start_propose_date': _start_date,
            'end_propose_date': _end_date,
        }
        
        # **kwargs를 통해 받은 추가 인자를 params에 병합
        params.update(kwargs)

        print(f"📌 [{_start_date} ~ {_end_date}] 의안 주요 내용 데이터 수집 시작...")

        df_bills = self.fetch_data_generic(
            url=url,
            params=params, # <-- 지역 변수 params 전달
            mapper=mapper,
            format='xml',
            all_pages=True,
        )

        if df_bills.empty:
            print(
                "⚠️ [WARNING] 수집된 데이터가 없습니다. API 응답을 확인하세요."
            )
            # 빈 DF라도 캐시하고 반환
            self.df_bills = df_bills
            self.content = df_bills
            return df_bills

        print(f"✅ [INFO] 총 {len(df_bills)} 개의 법안 수집됨.")

        if self.filter_data:
            print("✅ [INFO] 데이터 컬럼 필터링을 수행합니다.")
            # 유지할 컬럼 목록
            columns_to_keep = [
                'proposeDt',  # 발의일자
                'billId', # 법안 ID
                'billName', # 법안 이름
                'billNo',  # 법안번호
                'summary',  # 주요내용
                'procStageCd',  # 현재 처리 단계
                'proposerKind' # 발의자 종류
            ]
            
            # 실제 존재하는 컬럼만 필터링
            existing_columns_to_keep = [col for col in columns_to_keep if col in df_bills.columns]
            df_bills = df_bills[existing_columns_to_keep]

            # 'summary' 컬럼에 결측치가 있는 행 제거
            if 'summary' in df_bills.columns:
                df_bills = df_bills.dropna(subset=['summary'])

            # 인덱스 재설정
            df_bills.reset_index(drop=True, inplace=True)

            print(f"✅ [INFO] 결측치 처리 완료. {len(df_bills)} 개의 법안 유지됨.")

        else:
            print("✅ [INFO] 데이터 컬럼 필터링을 수행하지 않습니다.")

        # 컬럼 이름 변경
        df_bills.rename(columns={
            "proposeDt": "proposeDate",
            "billNo": "billNumber",
            "summary": "summary",
            "procStageCd": "stage"
        }, inplace=True)

        # AssemblyNumber는 데이터 호출에 사용된 _age에서 가져오기
        df_bills['assemblyNumber'] = _age 


        print("\n📌 발의일자별 수집한 데이터 수:")
        if 'proposeDate' in df_bills.columns:
            print(df_bills['proposeDate'].value_counts())
        else:
            print("ProposeDate 컬럼이 없습니다.")

        self.content = df_bills
        self.df_bills = df_bills # 인스턴스에 캐시
        
        return df_bills

    # def fetch_bills_info(self, df_bills=None, start_date=None, end_date=None, age=None, **kwargs):
    #     """
    #     법안 기본 정보를 API에서 가져오는 함수. (주석 처리됨 - 원본 유지)
    #     """
    # 
    #     # 1. df_bills 처리 (사용자 > 캐시 > 자동 수집)
    #     local_df_bills = df_bills
    #     if local_df_bills is None:
    #         print("✅ [INFO] 'df_bills'가 전달되지 않았습니다. 캐시 확인 중...")
    #         if self.df_bills is not None and not self.df_bills.empty:
    #             print("✅ [INFO] 캐시된 'self.df_bills'를 사용합니다.")
    #             local_df_bills = self.df_bills
    #         else:
    #             print("✅ [INFO] 캐시가 없습니다. 'df_bills' 자동 수집을 시작합니다.")
    #             # fetch_bills_info가 받은 매개변수를 fetch_bills_data에 전달
    #             local_df_bills = self.fetch_bills_data(start_date=start_date, 
    #                                                    end_date=end_date, 
    #                                                    age=age) # 여기서는 kwargs 제외
    # 
    #     if local_df_bills is None or local_df_bills.empty:
    #         print("❌ [ERROR] `df_bills` 데이터가 없습니다. 올바른 값을 전달하세요.")
    #         return None
    # 
    #     api_key = os.environ.get("APIKEY_billsInfo")
    #     url = self.url or "https://open.assembly.go.kr/portal/openapi/ALLBILL"
    # 
    #     # ... (이하 로직은 원본과 거의 동일) ...
    # 
    #     all_data = []
    #     print(f"\n📌 [법안 정보 데이터 수집 중...]")
    #     start_time = time.time()
    # 
    #     for row in tqdm(local_df_bills.itertuples(), total=len(local_df_bills)):
    #         params = {
    #             "Key": api_key,
    #             mapper.get("page_param", "pIndex"): 1,
    #             mapper.get("size_param", "pSize"): 5,
    #             "Type": format,
    #             "BILL_NO": row.billNumber,
    #         }
    #         
    #         # **kwargs를 통해 받은 추가 인자를 params에 병합
    #         params.update(kwargs)
    # 
    #         df_tmp = self.fetch_data_generic(
    #             url=url,
    #             params=params,
    #             mapper=mapper,
    #             format=format,
    #             all_pages=True,
    #         )
    #
    #     # ... (이하 생략) ...

    def fetch_lawmakers_data(self, **kwargs):
        """
        국회의원 데이터를 API로부터 가져와서 DataFrame으로 반환하는 함수.
        API 키와 URL은 함수 내부에서 정의되며, 모든 페이지를 처리합니다.

        Args:
            **kwargs: API 요청에 전달할 추가 매개변수.

        Returns:
            df_lawmakers: pandas.DataFrame, 수집된 국회의원 데이터
        """
        # 캐시 확인
        if self.df_lawmakers is not None and not self.df_lawmakers.empty:
            print("✅ [INFO] 캐시된 'self.df_lawmakers'를 반환합니다.")
            self.content = self.df_lawmakers
            return self.df_lawmakers

        api_key = os.environ.get("APIKEY_lawmakers")
        url = 'https://open.assembly.go.kr/portal/openapi/nwvrqwxyaytdsfvhu'  # 열린국회정보 '국회의원 인적사항' API
        mapper = self.mapper_open_xml

        params = {
            'KEY': api_key,
            'Type': 'xml',
            mapper['page_param']: 1,
            mapper['size_param']: 100,
        }
        
        # **kwargs를 통해 받은 추가 인자를 params에 병합
        params.update(kwargs)

        print("\n📌 [국회의원 데이터 수집 시작]")
        start_time = time.time()

        df_lawmakers = self.fetch_data_generic(
            url=url,
            params=params,
            mapper=mapper,
            format='xml',
            all_pages=True,
        )

        end_time = time.time()
        total_time = end_time - start_time
        print(f"✅ [INFO] 다운로드 완료! 총 소요 시간: {total_time:.2f}초")

        if df_lawmakers.empty:
            print("❌ [ERROR] 수집한 데이터가 없습니다.")
            return None

        print(f"✅ [INFO] 총 {len(df_lawmakers)} 개의 의원 데이터 수집됨")

        self.df_lawmakers = df_lawmakers # 캐시
        self.content = df_lawmakers
        return df_lawmakers


    def fetch_bills_coactors(self, df_bills=None, start_date=None, end_date=None, age=None, **kwargs):
        """
        열린국회정보 API를 활용하여 대표발의자 및 공동발의자 정보를 수집합니다.
        
        Args:
            df_bills (pd.DataFrame, optional): 'billId'가 포함된 법안 데이터프레임. 
                                              None이면 자동 수집을 시도합니다.
            start_date (str, optional): df_bills 자동 수집 시 사용할 시작일.
            end_date (str, optional): df_bills 자동 수집 시 사용할 종료일.
            age (str, optional): df_bills 자동 수집 시 사용할 대수.
            **kwargs: *공동발의자* API 요청에 전달할 추가 매개변수.
        """

        # 1. df_bills 처리 (사용자 > 캐시 > 자동 수집)
        local_df_bills = df_bills
        if local_df_bills is None:
            print("✅ [INFO] 'df_bills'가 전달되지 않았습니다. 캐시 확인 중...")
            if self.df_bills is not None and not self.df_bills.empty:
                print("✅ [INFO] 캐시된 'self.df_bills'를 사용합니다.")
                local_df_bills = self.df_bills
            else:
                print("✅ [INFO] 캐시가 없습니다. 'df_bills' 자동 수집을 시작합니다.")
                # 자동 수집 시에는 kwargs를 넘기지 않음 (kwargs는 이 메서드의 API용)
                local_df_bills = self.fetch_bills_data(start_date=start_date, 
                                                       end_date=end_date, 
                                                       age=age)

        if local_df_bills is None or local_df_bills.empty:
            print("❌ [ERROR] 법안 데이터가 없습니다.")
            return pd.DataFrame(columns=['billId', 'publicProposerIdList'])

        # 2. 국회의원 데이터 처리 (캐시 > 자동 수집)
        if self.df_lawmakers is None or self.df_lawmakers.empty:
            print("✅ [INFO] 국회의원 데이터가 없습니다. 자동 수집을 시작합니다.")
            self.fetch_lawmakers_data() # 매개변수 없이 호출
        
        df_lawmakers = self.df_lawmakers # 캐시된 데이터 사용

        if df_lawmakers is None or df_lawmakers.empty:
            print("❌ [ERROR] 국회의원 데이터가 존재하지 않아 발의자 코드를 매칭할 수 없습니다.")
            return pd.DataFrame(columns=['billId', 'publicProposerIdList'])

        required_columns = {'HG_NM', 'MONA_CD'}
        missing_columns = required_columns - set(df_lawmakers.columns)
        if missing_columns:
            print(f"❌ [ERROR] 국회의원 데이터에 필요한 컬럼이 없습니다: {', '.join(sorted(missing_columns))}")
            return pd.DataFrame(columns=['billId', 'publicProposerIdList'])

        api_key = (
            os.environ.get("APIKEY_billProposers")
            or os.environ.get("APIKEY_lawmakers")
            or os.environ.get("APIKEY_billsInfo")
        )

        if not api_key:
            print("❌ [ERROR] 발의자 정보를 조회할 API Key가 설정되어 있지 않습니다.")
            return pd.DataFrame(columns=['billId', 'publicProposerIdList'])

        url = 'https://open.assembly.go.kr/portal/openapi/BILLNPPPSR'
        mapper = self.mapper_open_xml

        bill_ids = (
            local_df_bills
            .dropna(subset=['billId'])
            ['billId']
            .astype(str)
            .unique()
            .tolist()
        )

        print(f"📌 [INFO] 대표/공동 발의자 정보 수집 시작... 총 {len(bill_ids)}개의 법안 대상")

        # --- (내부 헬퍼 함수: 원본과 동일) ---
        def append_unique(seq, value, *, front=False):
            if not value:
                return
            if value in seq:
                return
            if front:
                seq.insert(0, value)
            else:
                seq.append(value)

        def normalize_str(value):
            if value is None:
                return None
            if isinstance(value, float) and pd.isna(value):
                return None
            if pd.isna(value):
                return None
            value = str(value).strip()
            return value or None

        def ensure_entry(bill_id):
            normalized = normalize_str(bill_id)
            if not normalized:
                return None
            return aggregated.setdefault(
                normalized,
                {
                    'billId': normalized,
                    'representativeProposerIdList': [],
                    'publicProposerIdList': [],
                    'ProposerName': [],
                },
            )

        def find_lawmaker_code(name=None, hj_name=None, party=None):
            if name is None:
                return None

            candidates = df_lawmakers[df_lawmakers['HG_NM'] == name]
            if 'HJ_NM' in df_lawmakers.columns and hj_name:
                candidates = candidates[candidates['HJ_NM'] == hj_name]
            if 'POLY_NM' in df_lawmakers.columns and party:
                candidates = candidates[candidates['POLY_NM'] == party]

            if not candidates.empty:
                return normalize_str(candidates.iloc[0]['MONA_CD'])

            # 한자/정당 정보가 일치하지 않는 경우 이름만으로 재검색
            candidates = df_lawmakers[df_lawmakers['HG_NM'] == name]
            if not candidates.empty:
                return normalize_str(candidates.iloc[0]['MONA_CD'])

            return None
        # --- (내부 헬퍼 함수 끝) ---

        aggregated = {}

        for bill_id in tqdm(bill_ids, desc="발의자 수집", unit="건"):
            if ensure_entry(bill_id) is None:
                tqdm.write(f"⚠️ [WARN] billId {bill_id} 값이 올바르지 않아 건너뜁니다.")
                continue

            params = {
                'KEY': api_key,
                'Type': 'xml',
                mapper['page_param']: 1,
                mapper['size_param']: 100,
                'BILL_ID': bill_id,
            }
            
            # **kwargs를 통해 받은 추가 인자를 params에 병합
            params.update(kwargs)

            df_tmp = self.fetch_data_generic(
                url=url,
                params=params,
                mapper=mapper,
                format='xml',
                all_pages=True,
            )

            if df_tmp.empty:
                tqdm.write(f"⚠️ [WARN] billId {bill_id}에 대한 발의자 데이터를 찾을 수 없습니다.")
                continue

            df_tmp.columns = [col.upper() for col in df_tmp.columns]
            if 'BILL_ID' not in df_tmp.columns:
                df_tmp['BILL_ID'] = bill_id

            for row in df_tmp.to_dict('records'):
                row_bill_id = normalize_str(row.get('BILL_ID', bill_id))
                target = ensure_entry(row_bill_id)
                if target is None:
                    continue
                proposer_role = normalize_str(row.get('PUBL_PROPOSER'))
                proposer_code = normalize_str(
                    row.get('PPSR_CD')
                    or row.get('PUBL_PRPSR_CD')
                    or row.get('RPRSNT_PRPSR_CD')
                )
                proposer_name = normalize_str(
                    row.get('PPSR_NM')
                    or row.get('PUBL_PRPSR_NM')
                )
                proposer_hj_name = normalize_str(
                    row.get('PPSR_HJ_NM')
                    or row.get('PUBL_PRPSR_HJ_NM')
                )
                proposer_party = normalize_str(
                    row.get('RPP_NM')
                    or row.get('PPR_NM')
                    or row.get('POLY_NM')
                )

                if proposer_code is None:
                    proposer_code = find_lawmaker_code(
                        name=proposer_name,
                        hj_name=proposer_hj_name,
                        party=proposer_party,
                    )

                is_representative = proposer_role and ('대표' in proposer_role)

                if is_representative:
                    append_unique(target['representativeProposerIdList'], proposer_code)
                    append_unique(target['publicProposerIdList'], proposer_code, front=True)
                    append_unique(target['ProposerName'], proposer_name, front=True)
                else:
                    append_unique(target['publicProposerIdList'], proposer_code)
                    append_unique(target['ProposerName'], proposer_name)

        if not aggregated:
            print("⚠️ [WARN] 어떤 법안에서도 발의자 정보를 수집하지 못했습니다.")
            return pd.DataFrame(columns=['billId', 'publicProposerIdList'])

        df_coactors = pd.DataFrame(aggregated.values())

        def drop_empty_list(values):
            return [
                value
                for value in values
                if value and not (isinstance(value, float) and pd.isna(value)) and not pd.isna(value)
            ]

        df_coactors['representativeProposerIdList'] = df_coactors['representativeProposerIdList'].apply(drop_empty_list)
        df_coactors['publicProposerIdList'] = df_coactors['publicProposerIdList'].apply(drop_empty_list)
        df_coactors['ProposerName'] = df_coactors['ProposerName'].apply(drop_empty_list)
        df_coactors = df_coactors[
            ['billId', 'representativeProposerIdList', 'publicProposerIdList', 'ProposerName']
        ]

        filtered_count = len(df_coactors)
        df_coactors = df_coactors[df_coactors['publicProposerIdList'].apply(bool)]
        removed_count = filtered_count - len(df_coactors)
        if removed_count > 0:
            print(f"⚠️ [INFO] 공동발의자 정보를 확보하지 못한 {removed_count}개 법안을 제외했습니다.")

        print(f"✅ [INFO] 발의자 정보 수집 완료. 총 {len(df_coactors)}개의 법안에 대한 데이터를 확보했습니다.")

        self.content = df_coactors
        return df_coactors

    def fetch_bills_timeline(self, start_date=None, end_date=None, age=None, **kwargs):
        """
        특정 기간 동안의 의정활동 데이터를 수집합니다.
        이 메서드는 날짜별로 페이지네이션을 수행합니다.
        
        Args:
            start_date (str, optional): 검색 시작일 (YYYY-MM-DD). Defaults to 어제.
            end_date (str, optional): 검색 종료일 (YYYY-MM-DD). Defaults to 오늘.
            age (str, optional): 대수. Defaults to AGE 환경변수.
            **kwargs: API 요청에 전달할 추가 매개변수.
        """
        all_data = []
        pageNo = 1
        processing_count = 0
        start_time = time.time()

        _start_date_str = start_date or (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
        _end_date_str = end_date or datetime.now().strftime('%Y-%m-%d')
        _age = age or os.environ.get("AGE")

        # 문자열을 datetime 객체로 변환
        _start_date = datetime.strptime(_start_date_str, '%Y-%m-%d')
        _end_date = datetime.strptime(_end_date_str, '%Y-%m-%d')
        date_range = (_end_date - _start_date).days + 1

        print(f"\n📌 [INFO] [{_start_date.strftime('%Y-%m-%d')} ~ {_end_date.strftime('%Y-%m-%d')}] 의정활동 데이터 수집 시작...")

        max_retry = 3
        url = "https://open.assembly.go.kr/portal/openapi/nqfvrbsdafrmuzixe"

        for single_date in (_start_date + timedelta(n) for n in range(date_range)):
            date_str = single_date.strftime('%Y-%m-%d')
            pageNo = 1 # 날짜가 변경되면 페이지 번호 초기화
            retries_for_date = max_retry # 날짜별 재시도 횟수

            while True:
                params = {
                    "Key": os.environ.get("APIKEY_status"),
                    "Type": "xml",
                    "pIndex": pageNo,
                    "pSize": 100,
                    "AGE": _age,
                    "DT": date_str
                }
                # **kwargs를 통해 받은 추가 인자를 params에 병합
                params.update(kwargs)

                try:
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 200:
                        root = ElementTree.fromstring(response.content)
                        items = root.findall(".//row")

                        if not items:
                            if pageNo == 1:
                                print(f"ℹ️  [INFO] {date_str} | 데이터 없음.")
                            break  # 더 이상 데이터 없음

                        data = [{child.tag: child.text for child in item} for item in items]
                        all_data.extend(data)
                        print(f"✅ [INFO] {date_str} | 📄 Page {pageNo} | 📊 {len(data)} 개 추가됨. 총 {len(all_data)} 개 수집됨.")
                        processing_count += 1
                        retries_for_date = max_retry # 성공 시 재시도 횟수 초기화
                    else:
                        print(f"❌ [ERROR] 응답 코드: {response.status_code} (📅 Date: {date_str}, 📄 Page {pageNo})")
                        retries_for_date -= 1

                except Exception as e:
                    print(f"❌ [ERROR] 응답 처리 중 오류 발생: {str(e)}")
                    retries_for_date -= 1

                if retries_for_date <= 0:
                    print(f"🚨 [WARNING] {date_str} 최대 재시도 횟수 초과! 다음 날짜로 넘어갑니다.")
                    break # 다음 날짜로

                if not items and pageNo > 1:
                    break # 데이터가 있었는데 끝난 경우

                pageNo += 1

        df_timeline = pd.DataFrame(all_data)

        end_time = time.time()
        total_time = end_time - start_time
        print(f"\n✅ [INFO] 모든 파일 다운로드 완료! ⏳ 전체 소요 시간: {total_time:.2f}초")
        print(f"📌 [INFO] 총 {len(df_timeline)} 개의 의정활동 데이터 수집됨.")

        self.content = df_timeline
        return df_timeline


    def fetch_bills_result(self, start_date=None, end_date=None, age=None, **kwargs):
        """
        특정 기간 동안의 법안 결과 데이터를 수집합니다.
        
        Args:
            start_date (str, optional): 검색 시작일 (YYYY-MM-DD). Defaults to 오늘.
            end_date (str, optional): 검색 종료일 (YYYY-MM-DD). Defaults to 오늘.
            age (str, optional): 대수. Defaults to AGE 환경변수.
            **kwargs: API 요청에 전달할 추가 매개변수.
        """
        _start_date_str = start_date or datetime.now().strftime('%Y-%m-%d')
        _end_date_str = end_date or datetime.now().strftime('%Y-%m-%d')
        _age = age or os.getenv("AGE")
        
        _start_date = datetime.strptime(_start_date_str, '%Y-%m-%d')
        _end_date = datetime.strptime(_end_date_str, '%Y-%m-%d')
        
        api_key = os.getenv("APIKEY_result")
        url = 'https://open.assembly.go.kr/portal/openapi/TVBPMBILL11'
        
        all_data = []
        processing_count = 0
        
        print(f"\n📌 [INFO] [{_start_date.strftime('%Y-%m-%d')} ~ {_end_date.strftime('%Y-%m-%d')}] 법안 결과 데이터 수집 시작...")
        start_time = time.time()
        
        current_date = _start_date
        while current_date <= _end_date:
            pageNo = 1
            max_retry_per_date = 3
            
            while True:
                params = {
                    'KEY': api_key,
                    'Type': 'xml',
                    'pIndex': pageNo,
                    'pSize': 100,
                    'AGE': _age,
                    'PROC_DT': current_date.strftime('%Y-%m-%d')
                }
                # **kwargs를 통해 받은 추가 인자를 params에 병합
                params.update(kwargs)
                
                try:
                    response = requests.get(url, params=params, timeout=10)
                    
                    if response.status_code == 200:
                        root = ElementTree.fromstring(response.content)
                        head = root.find('head')
                        
                        # API가 데이터가 없을 때 head를 반환하지 않는 경우가 있음
                        if head is None:
                            if pageNo == 1:
                                print(f"ℹ️  [INFO] {current_date.strftime('%Y-%m-%d')} | 데이터 없음.")
                            break # 데이터 없음, 다음 날짜로

                        total_count_elem = head.find('list_total_count')
                        total_count = int(total_count_elem.text) if total_count_elem is not None else 0
                        
                        rows = root.findall('row')
                        if not rows:
                            if pageNo == 1:
                                print(f"ℹ️  [INFO] {current_date.strftime('%Y-%m-%d')} | 데이터 없음 (total: 0).")
                            break # 데이터 없음, 다음 날짜로
                        
                        data = [{child.tag: child.text for child in row_elem} for row_elem in rows]
                        all_data.extend(data)
                        print(f"✅ [INFO] {current_date.strftime('%Y-%m-%d')} | 📄 Page {pageNo} | 📊 Total: {len(all_data)} 개 수집됨.")
                        processing_count += 1
                        max_retry_per_date = 3 # 성공 시 초기화
                        
                        if pageNo * 100 >= total_count:
                            break # 현재 날짜의 모든 페이지 수집 완료
                    else:
                        print(f"❌ [ERROR] 응답 코드: {response.status_code} (📄 Page {pageNo})")
                        max_retry_per_date -= 1
                
                except Exception as e:
                    print(f"❌ [ERROR] 데이터 처리 중 오류 발생: {e}")
                    max_retry_per_date -= 1
                
                if max_retry_per_date <= 0:
                    print(f"🚨 [WARNING] {current_date.strftime('%Y-%m-%d')} 최대 재시도 횟수 초과! 다음 날짜로 넘어갑니다.")
                    break # 다음 날짜로
                
                pageNo += 1
            
            current_date += timedelta(days=1)
        
        df_result = pd.DataFrame(all_data)
        
        if df_result.empty:
            print("⚠️ [WARNING] 수집된 데이터가 없습니다.")
            self.content = df_result
            return df_result
        
        end_time = time.time()
        total_time = end_time - start_time
        print(f"\n✅ [INFO] 모든 파일 다운로드 완료! ⏳ 전체 소요 시간: {total_time:.2f}초")
        print(f"📌 [INFO] 총 {len(df_result)} 개의 법안 수집됨.")
        
        pd.set_option('display.max_columns', None)
        
        self.content = df_result
        return df_result

    def fetch_bills_vote(self, start_date=None, end_date=None, age=None, **kwargs):
        """
        특정 기간 동안의 본회의 의결 데이터를 수집합니다.
        
        Args:
            start_date (str, optional): 검색 시작일 (YYYY-MM-DD). Defaults to 어제.
            end_date (str, optional): 검색 종료일 (YYYY-MM-DD). Defaults to 오늘.
            age (str, optional): 대수. Defaults to AGE 환경변수.
            **kwargs: API 요청에 전달할 추가 매개변수.
        """
        _start_date_str = start_date or (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
        _end_date_str = end_date or datetime.now().strftime('%Y-%m-%d')
        _age = age or os.getenv("AGE")

        # 문자열을 datetime 객체로 변환
        _start_date = datetime.strptime(_start_date_str, '%Y-%m-%d')
        _end_date = datetime.strptime(_end_date_str, '%Y-%m-%d')
        date_range = (_end_date - _start_date).days + 1

        api_key = os.getenv("APIKEY_status")
        url = 'https://open.assembly.go.kr/portal/openapi/nwbpacrgavhjryiph'
        all_data = []
        processing_count = 0
        start_time = time.time()

        print(f"\n📌 [INFO] [{_start_date.strftime('%Y-%m-%d')} ~ {_end_date.strftime('%Y-%m-%d')}] 본회의 의결 데이터 수집 시작...")

        for single_date in (_start_date + timedelta(n) for n in range(date_range)):
            date_str = single_date.strftime('%Y-%m-%d')
            pageNo = 1 # 날짜 변경 시 페이지 번호 초기화
            max_retry_per_date = 3

            while True:
                params = {
                    'KEY': api_key,
                    'Type': 'xml',
                    'pIndex': pageNo,
                    'pSize': 100,
                    'AGE': _age,
                    'RGS_PROC_DT': date_str  # 본회의심의_의결일 필터링
                }
                # **kwargs를 통해 받은 추가 인자를 params에 병합
                params.update(kwargs)

                try:
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 200:
                        root = ElementTree.fromstring(response.content)
                        head = root.find('head')
                        if head is None:
                            if pageNo == 1:
                                print(f"ℹ️  [INFO] {date_str} | 데이터 없음.")
                            break # 데이터 없음

                        total_count_elem = head.find('list_total_count')
                        total_count = int(total_count_elem.text) if total_count_elem is not None else 0
                        
                        rows = root.findall('row')

                        if not rows:
                            if pageNo == 1:
                                print(f"ℹ️  [INFO] {date_str} | 데이터 없음 (total: 0).")
                            break

                        data = [{child.tag: child.text for child in row_elem} for row_elem in rows]
                        all_data.extend(data)
                        print(f"✅ [INFO] {date_str} | 📄 Page {pageNo} | 📊 Total: {len(all_data)} 개 수집됨.")
                        processing_count += 1
                        max_retry_per_date = 3 # 성공 시 초기화

                        if pageNo * 100 >= total_count:
                            break # 현재 날짜의 모든 페이지 수집 완료

                    else:
                        print(f"❌ [ERROR] 응답 코드: {response.status_code} (📄 Page {pageNo})")
                        max_retry_per_date -= 1

                except Exception as e:
                    print(f"❌ [ERROR] 데이터 처리 중 오류 발생: {e}")
                    max_retry_per_date -= 1
                
                if max_retry_per_date <= 0:
                    print(f"🚨 [WARNING] {date_str} 최대 재시도 횟수 초과! 다음 날짜로 넘어갑니다.")
                    break

                pageNo += 1

        # 데이터프레임 생성
        df_vote = pd.DataFrame(all_data)

        end_time = time.time()
        total_time = end_time - start_time
        print(f"\n✅ [INFO] 모든 파일 다운로드 완료! ⏳ 전체 소요 시간: {total_time:.2f}초")
        print(f"📌 [INFO] 총 {len(df_vote)} 개의 본회의 의결 데이터 수집됨.")

        self.df_vote = df_vote # 캐시
        self.content = df_vote
        return df_vote

    def fetch_vote_party(self, df_vote=None, start_date=None, end_date=None, age=None, **kwargs):
        """
        법안별 정당별 투표 결과를 수집합니다.
        
        Args:
            df_vote (pd.DataFrame, optional): 'BILL_ID'가 포함된 본회의 의결 데이터.
                                            None이면 자동 수집을 시도합니다.
            start_date (str, optional): df_vote 자동 수집 시 사용할 시작일.
            end_date (str, optional): df_vote 자동 수집 시 사용할 종료일.
            age (str, optional): df_vote 자동 수집 시 사용할 대수.
            **kwargs: *정당별 투표 결과* API 요청에 전달할 추가 매개변수.
        """
        _age = age or os.getenv("AGE")
        
        api_key = os.getenv("APIKEY_status")
        url = 'https://open.assembly.go.kr/portal/openapi/nojepdqqaweusdfbi'

        all_data = []
        count = 0
        processing_count = 0
        start_time = time.time()

        # 1. df_vote 처리 (사용자 > 캐시 > 자동 수집)
        local_df_vote = df_vote
        if local_df_vote is None:
            print("✅ [INFO] 'df_vote'가 전달되지 않았습니다. 캐시 확인 중...")
            if self.df_vote is not None and not self.df_vote.empty:
                print("✅ [INFO] 캐시된 'self.df_vote'를 사용합니다.")
                local_df_vote = self.df_vote
            else:
                print("⚠️ [WARNING] 수집에 필요한 'df_vote' 데이터가 없습니다. 새로 수집합니다.")
                # 자동 수집 시 kwargs 제외
                local_df_vote = self.fetch_bills_vote(start_date=start_date, 
                                                      end_date=end_date, 
                                                      age=age)
                self.df_vote = local_df_vote # 캐시

        if local_df_vote is None or local_df_vote.empty:
            print("🚨 [WARNING] 투표 결과(df_vote) 데이터가 없어 정당별 투표를 수집할 수 없습니다.")
            return None

        print(f"\n📌 [INFO] 법안별 정당별 투표 결과 데이터 수집 시작...")
        
        # 'PROC_RESULT_CD'가 '철회'가 아닌 'BILL_ID' 목록 추출
        bill_ids_to_fetch = []
        if 'PROC_RESULT_CD' in local_df_vote.columns and 'BILL_ID' in local_df_vote.columns:
             bill_ids_to_fetch = local_df_vote[
                 local_df_vote['PROC_RESULT_CD'] != '철회'
             ]['BILL_ID'].unique()
        elif 'BILL_ID' in local_df_vote.columns:
             print("⚠️ [WARNING] 'PROC_RESULT_CD' 컬럼이 없어 모든 BILL_ID에 대해 수집을 시도합니다.")
             bill_ids_to_fetch = local_df_vote['BILL_ID'].unique()
        else:
            print("❌ [ERROR] 'BILL_ID' 컬럼이 df_vote에 없습니다.")
            return None

        for bill_id in tqdm(bill_ids_to_fetch, desc="정당별 투표 수집", unit="법안"):
            pageNo = 1
            max_retry_per_bill = 3
            bill_data_count = 0
            
            while True:
                params = {
                    'KEY': api_key,
                    'Type': 'xml',
                    'pIndex': pageNo,
                    'pSize': 100,
                    'AGE': _age,
                    'BILL_ID': bill_id
                }
                # **kwargs를 통해 받은 추가 인자를 params에 병합
                params.update(kwargs)

                count += 1
                # print(f"📄 [INFO] 페이지 {pageNo} 요청 중...") # 너무 로그가 많아 주석 처리

                try:
                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code == 200:
                        root = ElementTree.fromstring(response.content)
                        head = root.find('head')
                        if head is None:
                            if pageNo == 1:
                                tqdm.write(f"ℹ️  [INFO] {bill_id} | 데이터 없음.")
                            break

                        total_count_elem = head.find('list_total_count')
                        total_count = int(total_count_elem.text) if total_count_elem is not None else 0
                        
                        rows = root.findall('row')

                        if not rows:
                            if pageNo == 1:
                                tqdm.write(f"ℹ️  [INFO] {bill_id} | 데이터 없음 (total: 0).")
                            break

                        data = [{child.tag: child.text for child in row_elem} for row_elem in rows]
                        all_data.extend(data)
                        bill_data_count += len(data)
                        # tqdm.write(f"✅ [INFO] {bill_id} | 📄 Page {pageNo} | 📊 총 {len(all_data)} 개 데이터 수집됨.")

                        processing_count += 1
                        max_retry_per_bill = 3 # 성공 시 초기화

                        if pageNo * 100 >= total_count:
                            # tqdm.write(f"✅ [INFO] 법안 ID: {bill_id}의 모든 페이지 처리 완료.")
                            break

                    else:
                        tqdm.write(f"❌ [ERROR] 응답 코드: {response.status_code} (📄 Page {pageNo})")
                        max_retry_per_bill -= 1

                except Exception as e:
                    tqdm.write(f"❌ [ERROR] 데이터 처리 중 오류 발생: {e}")
                    max_retry_per_bill -= 1

                if max_retry_per_bill <= 0:
                    tqdm.write(f"🚨 [WARNING] {bill_id} 최대 재시도 횟수 초과! 다음 법안으로 넘어갑니다.")
                    break

                pageNo += 1
            
            tqdm.write(f"✅ [INFO] {bill_id} | 📊 {bill_data_count} 개 데이터 수집됨.")

        # 데이터프레임 생성
        df_vote_individual = pd.DataFrame(all_data)

        if df_vote_individual.empty:
            print("⚠️ [WARNING] 수집된 데이터가 없습니다.")
            self.content = df_vote_individual
            return df_vote_individual

        end_time = time.time()
        total_time = end_time - start_time
        print(f"\n✅ [INFO] 모든 파일 다운로드 완료! ⏳ 전체 소요 시간: {total_time:.2f}초")
        print(f"📌 [INFO] 총 {len(df_vote_individual)} 개의 개별 투표 데이터 수집됨.")

        # 필요한 컬럼만 유지 (존재하는 컬럼만 선택)
        columns_to_keep = [
            'AGE',  # 대수
            'BILL_ID',  # 의안번호
            'HG_NM',  # 의원명
            'POLY_NM',  # 소속정당
            'RESULT_VOTE_MOD',  # 표결결과
        ]
        existing_columns = [col for col in columns_to_keep if col in df_vote_individual.columns]
        df_vote_individual_filtered = df_vote_individual[existing_columns]

        if 'RESULT_VOTE_MOD' not in df_vote_individual_filtered.columns or \
           'BILL_ID' not in df_vote_individual_filtered.columns or \
           'POLY_NM' not in df_vote_individual_filtered.columns:
            print("❌ [ERROR] 정당별 투표 집계에 필요한 컬럼(BILL_ID, POLY_NM, RESULT_VOTE_MOD)이 없습니다.")
            self.content = df_vote_individual
            return df_vote_individual # 집계 전 원본 반환

        # 정당별 찬성 투표 개수 집계
        df_vote_party = df_vote_individual_filtered[df_vote_individual_filtered['RESULT_VOTE_MOD'] == '찬성'] \
            .groupby(['BILL_ID', 'POLY_NM']) \
            .size() \
            .reset_index(name='voteForCount')

        # 컬럼 이름 변경
        df_vote_party.rename(columns={
            'BILL_ID': 'billId',
            'POLY_NM': 'partyName',
            'voteForCount': 'voteForCount'
        }, inplace=True)

        self.content = df_vote_party
        return df_vote_party

    def fetch_bills_alternatives(self, df_bills=None, start_date=None, end_date=None, age=None, **kwargs):
        """
        df_bills를 기반으로 각 법안의 대안을 수집하고 반환하는 메서드.

        Args:
            df_bills (pd.DataFrame, optional): 'billId'가 포함된 법안 데이터프레임. 
                                              None이면 자동 수집을 시도합니다.
            start_date (str, optional): df_bills 자동 수집 시 사용할 시작일.
            end_date (str, optional): df_bills 자동 수집 시 사용할 종료일.
            age (str, optional): df_bills 자동 수집 시 사용할 대수.
            **kwargs: *대안 법안* API 요청에 전달할 추가 매개변수.
            
        Returns:
            pd.DataFrame: 각 법안의 대안을 포함하는 데이터프레임
        """

        # 1. df_bills 처리 (사용자 > 캐시 > 자동 수집)
        local_df_bills = df_bills
        if local_df_bills is None:
            print("✅ [INFO] 'df_bills'가 전달되지 않았습니다. 캐시 확인 중...")
            if self.df_bills is not None and not self.df_bills.empty:
                print("✅ [INFO] 캐시된 'self.df_bills'를 사용합니다.")
                local_df_bills = self.df_bills
            else:
                print("⚠️ [WARNING] 수집된 법안 데이터(self.df_bills)가 없습니다. 법안 내용을 먼저 수집합니다...")
                # 자동 수집 시 kwargs 제외
                local_df_bills = self.fetch_bills_data(start_date=start_date, 
                                                       end_date=end_date, 
                                                       age=age)

        if local_df_bills is None or local_df_bills.empty:
            print("🚨 [WARNING] 법안 내용 데이터를 수집할 수 없습니다. 작업을 중단합니다.")
            return None
            
        if 'billId' not in local_df_bills.columns:
            print("❌ [ERROR] 'billId' 컬럼이 df_bills에 없습니다.")
            return None

        def fetch_alternativeBills_relation_data(bill_id, api_key, **inner_kwargs):
            """ 주어진 bill_id에 대한 대안 법안 데이터를 API에서 수집하는 내부 함수 """
            url = 'http://apis.data.go.kr/9710000/BillInfoService2/getBillAdditionalInfo'
            params = {
                'serviceKey': api_key,
                'bill_id': bill_id
            }
            # 이 메서드에 전달된 kwargs를 내부 API 호출에 사용
            params.update(inner_kwargs) 

            try:
                response = requests.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    root = ElementTree.fromstring(response.content)
                    items = root.find('.//exhaust')

                    if items is None or len(items.findall('item')) == 0:
                        return []

                    law_data = []
                    for item in items.findall('item'):
                        bill_link_elem = item.find('billLink')
                        bill_name_elem = item.find('billName')
                        
                        if bill_link_elem is None or bill_name_elem is None:
                            continue
                            
                        bill_link = bill_link_elem.text
                        law_bill_id = bill_link.split('bill_id=')[-1]
                        bill_name = bill_name_elem.text
                        law_data.append({'billId': law_bill_id, 'billName': bill_name})

                    return law_data
                else:
                    tqdm.write(f"❌ [ERROR] API 요청 실패 (bill_id={bill_id}), 응답 코드: {response.status_code}")
                    return []
            except Exception as e:
                tqdm.write(f"❌ [ERROR] bill_id={bill_id} 처리 중 오류 발생: {e}")
                return []

        # 대안 데이터프레임 초기화
        alternatives_data = []
        api_key = os.environ.get("APIKEY_DATAGOKR")
        
        if not api_key:
            print("❌ [ERROR] 대안 법안 조회에 필요한 APIKEY_DATAGOKR 키가 없습니다.")
            return None

        print("📌 [INFO] 법안별 대안 데이터 수집 시작...")

        # tqdm을 사용하여 진행 상황 표시
        for _, row in tqdm(local_df_bills.iterrows(), total=len(local_df_bills), desc="대안 법안 수집"):
            alt_id = row['billId']  # 대안(위원장안) ID

            # 대안 데이터 수집 (kwargs 전달)
            law_data = fetch_alternativeBills_relation_data(alt_id, api_key, **kwargs)

            # 수집된 데이터를 리스트에 추가
            for law in law_data:
                alternatives_data.append({
                    'altBillId': alt_id,  # 대안(위원장안) ID
                    'billId': law['billId'],  # 대안에 포함된 법안 ID
                })

        # 대안 데이터를 데이터프레임으로 변환
        df_alternatives = pd.DataFrame(alternatives_data)

        if df_alternatives.empty:
            print("⚠️ [WARNING] 대안 법안 데이터를 수집하지 못했습니다.")
        else:
            print(f"✅ [INFO] 총 {len(df_alternatives)} 개의 대안 법안 관계 데이터 수집 완료.")

        self.content = df_alternatives  # 클래스 속성에 저장
        return df_alternatives