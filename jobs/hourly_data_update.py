# # -*- coding: utf-8 -*-
# import time
# import sys
# import os
# import datetime
# from typing import Dict, Any, Callable, Optional
# import pandas as pd

# # 프로젝트 루트 경로를 sys.path에 추가
# sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# from src.data_operations.WorkFlowManager import WorkFlowManager
# from src.data_operations.ReportManager import ReportManager
# from src.data_operations.Notifier import Notifier

# def run_update_job(job_key: str, job_function: Callable, report_manager: ReportManager) -> Optional[str]:
#     """
#     개별 데이터 업데이트 작업을 실행하고, 중복을 확인하며, 결과를 기록합니다.
#     오류 발생 시 오류 메시지를 반환합니다.
#     """
#     job_name_map = {
#         "bills": "법안", "lawmakers": "의원", "timeline": "타임라인",
#         "results": "처리결과", "votes": "표결정보",
#     }
#     job_name = job_name_map.get(job_key, job_key)
#     last_run_dir = "reports/last_run"
#     last_run_file = os.path.join(last_run_dir, f"{job_key}.csv")

#     print(f"--- [시작] {job_name} 업데이트 ---")
#     start_time = time.time()
#     try:
#         result_obj = job_function()
#         execution_time = time.time() - start_time

#         result_df = result_obj[0] if isinstance(result_obj, tuple) else result_obj

#         if result_df is None or result_df.empty:
#             report_manager.save_job_result(job_key, "no_data", execution_time=execution_time)
#             print(f"➖ [{job_name}] 수집된 데이터 없음 (소요 시간: {execution_time:.2f}초)")
#             return None

#         # 'bills'를 제외하고 중복 검사 수행
#         if job_key != "bills":
#             if os.path.exists(last_run_file):
#                 try:
#                     old_df = pd.read_csv(last_run_file)
#                     # 데이터프레임의 내용을 비교하기 위해 정렬
#                     result_df_sorted = result_df.sort_values(by=list(result_df.columns)).reset_index(drop=True)
#                     old_df_sorted = old_df.sort_values(by=list(old_df.columns)).reset_index(drop=True)
                    
#                     if result_df_sorted.equals(old_df_sorted):
#                         report_manager.save_job_result(job_key, "no_change", data_count=len(result_df), execution_time=execution_time)
#                         print(f"⚪ [{job_name}] 변경사항 없음-전송 생략 (소요 시간: {execution_time:.2f}초)")
#                         return None
#                 except Exception as e:
#                     print(f"⚠️ [경고] 이전 결과 파일({last_run_file}) 비교 중 오류: {e}")

#         # 성공 또는 변경된 데이터 처리
#         report_manager.save_job_result(job_key, "success", data_count=len(result_df), execution_time=execution_time)
#         print(f"✅ [{job_name}] 전송 성공: {len(result_df)}건 (소요 시간: {execution_time:.2f}초)")
        
#         # 성공 시, 마지막 실행 결과 저장 ('bills' 제외)
#         if job_key != "bills":
#             result_df.to_csv(last_run_file, index=False)
            
#         return None

#     except Exception as e:
#         execution_time = time.time() - start_time
#         error_message = f"🚨 **[{job_name.upper()}]** 작업 중 오류 발생!\n\n- **오류 내용**: `{type(e).__name__}: {str(e)}`"
#         print(error_message)
        
#         report_manager.save_job_result(job_key, "error", error_message=str(e), execution_time=execution_time)
#         return error_message

# def main():
#     """
#     전체 데이터 업데이트 및 리포팅 파이프라인을 실행합니다.
#     성공 또는 오류가 발생한 항목에 대해서만 알림을 전송합니다.
#     """
#     mode = 'remote'
#     print(f"🚀 전체 데이터 업데이트를 '{mode}' 모드로 시작합니다.")
    
#     wfm = WorkFlowManager(mode=mode)
#     report_manager = ReportManager()
    
#     # 이전 리포트 및 마지막 실행 결과 저장 디렉토리 생성
#     os.makedirs("reports/last_run", exist_ok=True)
#     report_manager.clear_results()
    
#     update_jobs = {
#         "bills": wfm.update_bills_data,
#         "lawmakers": wfm.update_lawmakers_data,
#         "timeline": wfm.update_bills_timeline,
#         "results": wfm.update_bills_result,
#         "votes": wfm.update_bills_vote,
#     }

#     for job_key, job_func in update_jobs.items():
#         run_update_job(job_key, job_func, report_manager)
#         time.sleep(1)

#     # --- 알림 로직 수정 ---
#     # 1. 모든 작업 결과 수집
#     print("\n--- [시작] 리포트 생성 및 전송 ---")
#     all_results = report_manager.collect_all_results()

#     # 2. 알림 보낼 결과 필터링 (성공 또는 오류)
#     results_to_notify = {
#         key: result for key, result in all_results.items()
#         if result['status'] in ['success', 'error']
#     }

#     # 3. 필터링된 결과가 있을 때만 알림 생성 및 전송
#     if results_to_notify:
#         current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
#         report_lines = [f"📊 **데이터 업데이트 결과** ({current_time})"]
        
#         status_emojis = {"success": "✅", "error": "🚨"}
#         job_name_map = {
#             "bills": "법안", "lawmakers": "의원", "timeline": "타임라인",
#             "results": "처리결과", "votes": "표결정보",
#         }

#         for job_key, result in sorted(results_to_notify.items()):
#             status = result['status']
#             job_name = job_name_map.get(job_key, job_key)
#             emoji = status_emojis.get(status, "❓")

#             if status == "success":
#                 data_count = result.get('data_count', 0)
#                 line = f"{emoji} **{job_name}**: 전송 성공 ({data_count}건)"
#             elif status == "error":
#                 error_msg = result.get('error_message', '알 수 없는 오류')
#                 line = f"{emoji} **{job_name}**: 실행 오류 - `{error_msg}`"
            
#             report_lines.append(line)
        
#         report_message = "\n".join(report_lines)
        
#         print("\n--- [시작] 알림 전송 ---")
#         notifier = Notifier()
#         notifier.send_discord_message(report_message)
#         print("✅ [성공] 알림 전송 완료")
#     else:
#         print("\n✅ 전송할 신규 데이터 또는 오류가 없어 알림을 생략합니다.")

#     print("\n🎉 모든 데이터 업데이트 및 리포팅 작업이 완료되었습니다.")


# if __name__ == "__main__":
#     main()
