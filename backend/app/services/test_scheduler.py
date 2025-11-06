"""测试运行定时任务调度器"""
import logging
from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.test_execution_service import TestExecutionService

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = AsyncIOScheduler()


class TestScheduler:
    """测试运行定时调度器"""
    
    def __init__(self):
        self.scheduler = scheduler
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("测试调度器已启动")
    
    def add_scheduled_test_run(
        self,
        test_run_id: int,
        schedule_config: Dict[str, Any]
    ) -> str:
        """添加定时测试运行任务"""
        job_id = f"test_run_{test_run_id}"
        
        # 如果已存在，先删除
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # 根据调度类型创建触发器
        schedule_type = schedule_config.get("type", "cron")
        
        if schedule_type == "cron":
            # Cron表达式调度
            trigger = CronTrigger.from_crontab(schedule_config.get("cron_expression", "0 0 * * *"))
        elif schedule_type == "interval":
            # 间隔调度
            interval_config = schedule_config.get("interval", {})
            trigger = IntervalTrigger(
                seconds=interval_config.get("seconds", 0),
                minutes=interval_config.get("minutes", 0),
                hours=interval_config.get("hours", 0),
                days=interval_config.get("days", 0)
            )
        elif schedule_type == "once":
            # 一次性执行
            run_time = schedule_config.get("run_time")
            if run_time:
                trigger = DateTrigger(run_date=datetime.fromisoformat(run_time))
            else:
                raise ValueError("一次性执行必须提供 run_time")
        else:
            raise ValueError(f"不支持的调度类型: {schedule_type}")
        
        # 添加任务
        self.scheduler.add_job(
            func=self._execute_test_run_job,
            trigger=trigger,
            id=job_id,
            args=[test_run_id],
            replace_existing=True,
            misfire_grace_time=300  # 5分钟容错时间
        )
        
        logger.info(f"已添加定时测试运行任务: {job_id}, 调度配置: {schedule_config}")
        return job_id
    
    async def _execute_test_run_job(self, test_run_id: int):
        """执行定时测试运行任务"""
        db = SessionLocal()
        try:
            logger.info(f"开始执行定时测试运行: {test_run_id}")
            execution_service = TestExecutionService(db)
            
            # 获取测试运行信息和配置
            from app.models.project import TestRun
            test_run = db.query(TestRun).filter(TestRun.id == test_run_id).first()
            
            if not test_run:
                logger.error(f"测试运行 {test_run_id} 不存在")
                return
            
            if test_run.status == "running":
                logger.warning(f"测试运行 {test_run_id} 正在运行中，跳过本次调度")
                return
            
            # 获取测试用例ID和执行配置
            test_case_ids = []
            execution_config = {}
            
            if test_run.results and isinstance(test_run.results, dict):
                test_case_ids = test_run.results.get("test_case_ids", [])
                execution_config = test_run.results.get("execution_config", {})
            
            if not test_case_ids:
                logger.error(f"测试运行 {test_run_id} 没有关联的测试用例")
                return
            
            # 执行测试运行
            await execution_service.execute_test_run_async(
                test_run_id,
                test_case_ids,
                execution_config
            )
            
            logger.info(f"定时测试运行 {test_run_id} 执行完成")
        except Exception as e:
            logger.error(f"执行定时测试运行 {test_run_id} 失败: {e}", exc_info=True)
        finally:
            db.close()
    
    def remove_scheduled_test_run(self, test_run_id: int) -> bool:
        """移除定时测试运行任务"""
        job_id = f"test_run_{test_run_id}"
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除定时测试运行任务: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"移除定时测试运行任务失败: {e}")
            return False
    
    def get_scheduled_test_run(self, test_run_id: int) -> Optional[Dict[str, Any]]:
        """获取定时测试运行任务信息"""
        job_id = f"test_run_{test_run_id}"
        job = self.scheduler.get_job(job_id)
        
        if not job:
            return None
        
        return {
            "job_id": job_id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
    
    def list_all_scheduled_runs(self) -> Dict[str, Dict[str, Any]]:
        """列出所有定时测试运行任务"""
        jobs = {}
        for job in self.scheduler.get_jobs():
            if job.id.startswith("test_run_"):
                test_run_id = int(job.id.replace("test_run_", ""))
                jobs[str(test_run_id)] = {
                    "job_id": job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
        return jobs


# 全局调度器实例
test_scheduler = TestScheduler()

