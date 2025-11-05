# from celery import shared_task
# from .utils import check_fact_with_rag
#
# @shared_task(bind=True, max_retries=2, default_retry_delay=10)
# def run_fact_check_task(self, query: str):
#     try:
#         return check_fact_with_rag(query, k_sources_return=3)
#     except Exception as e:
#         # إعادة المحاولة في حالة فشل مؤقت
#         raise self.retry(exc=e)
