import os
import subprocess
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from models import db, Job, Execution, JobStatus, JobFrequency
import tempfile
import ast

class PythonScriptScheduler:
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler()
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.upload_folder = app.config['UPLOAD_FOLDER']
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Start scheduler
        if not self.scheduler.running:
            self.scheduler.start()
        
        # Load existing jobs on startup
        with app.app_context():
            self.load_scheduled_jobs()
    
    def validate_python_script(self, script_path):
        """Validate Python script syntax"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Check for syntax errors
            ast.parse(source)
            return True, "Script is valid"
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def execute_script(self, job_id):
        """Execute a Python script for a given job"""
        with self.app.app_context():
            job = Job.query.get(job_id)
            if not job:
                return
            
            # Update job status
            job.status = JobStatus.RUNNING
            job.last_execution = datetime.utcnow()
            db.session.commit()
            
            # Create execution record
            execution = Execution(
                job_id=job_id,
                started_at=datetime.utcnow(),
                status='running'
            )
            db.session.add(execution)
            db.session.commit()
            
            script_path = os.path.join(self.upload_folder, job.script_filename)
            
            try:
                # Execute script in isolated environment
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    
                )
                
                execution.completed_at = datetime.utcnow()
                execution.duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.output = result.stdout
                execution.error_output = result.stderr
                
                if result.returncode == 0:
                    execution.status = 'success'
                    job.status = JobStatus.COMPLETED
                else:
                    execution.status = 'error'
                    job.status = JobStatus.FAILED
                
            except subprocess.TimeoutExpired:
                execution.completed_at = datetime.utcnow()
                execution.duration = 300  # timeout duration
                execution.status = 'timeout'
                execution.error_output = 'Script execution timed out after 5 minutes'
                job.status = JobStatus.FAILED
                
            except Exception as e:
                execution.completed_at = datetime.utcnow()
                execution.duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.status = 'error'
                execution.error_output = str(e)
                job.status = JobStatus.FAILED
            
            # Update job execution count and next execution time
            job.execution_count += 1
            job.next_execution = self.calculate_next_execution(job)
            
            # If job has ended or failed, update status
            if job.end_date and datetime.now().date() > job.end_date:
                job.status = JobStatus.COMPLETED
            elif job.status == JobStatus.FAILED:
                pass  # Keep failed status
            else:
                job.status = JobStatus.SCHEDULED
            
            db.session.commit()
    
    def calculate_next_execution(self, job):
        """Calculate next execution time for a job"""
        if job.end_date and datetime.now().date() >= job.end_date:
            return None
        
        now = datetime.now()
        execution_time = datetime.combine(now.date(), job.execution_time)
        
        if job.frequency == JobFrequency.DAILY:
            if execution_time <= now:
                execution_time += timedelta(days=1)
        elif job.frequency == JobFrequency.WEEKLY:
            days_ahead = 7 - now.weekday()
            if days_ahead <= 0 or (days_ahead == 7 and execution_time <= now):
                days_ahead += 7
            execution_time = execution_time + timedelta(days=days_ahead)
        elif job.frequency == JobFrequency.MONTHLY:
            if execution_time <= now:
                if now.month == 12:
                    execution_time = execution_time.replace(year=now.year + 1, month=1)
                else:
                    execution_time = execution_time.replace(month=now.month + 1)
        
        return execution_time
    
    def schedule_job(self, job):
        """Schedule a job in the APScheduler"""
        if job.frequency == JobFrequency.DAILY:
            trigger = CronTrigger(
                hour=job.execution_time.hour,
                minute=job.execution_time.minute,
                start_date=job.start_date,
                end_date=job.end_date
            )
        elif job.frequency == JobFrequency.WEEKLY:
            trigger = CronTrigger(
                day_of_week=0,  # Monday
                hour=job.execution_time.hour,
                minute=job.execution_time.minute,
                start_date=job.start_date,
                end_date=job.end_date
            )
        elif job.frequency == JobFrequency.MONTHLY:
            trigger = CronTrigger(
                day=1,  # First day of month
                hour=job.execution_time.hour,
                minute=job.execution_time.minute,
                start_date=job.start_date,
                end_date=job.end_date
            )
        
        self.scheduler.add_job(
            func=self.execute_script,
            trigger=trigger,
            args=[job.id],
            id=f'job_{job.id}',
            replace_existing=True
        )
    
    def load_scheduled_jobs(self):
        """Load all scheduled jobs from database"""
        jobs = Job.query.filter(Job.status.in_([JobStatus.SCHEDULED, JobStatus.RUNNING])).all()
        for job in jobs:
            try:
                self.schedule_job(job)
                # Update next execution time
                job.next_execution = self.calculate_next_execution(job)
                db.session.commit()
            except Exception as e:
                print(f"Error scheduling job {job.id}: {e}")
    
    def pause_job(self, job_id):
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(f'job_{job_id}')
            with self.app.app_context():
                job = Job.query.get(job_id)
                if job:
                    job.status = JobStatus.PAUSED
                    db.session.commit()
        except Exception as e:
            print(f"Error pausing job {job_id}: {e}")
    
    def resume_job(self, job_id):
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(f'job_{job_id}')
            with self.app.app_context():
                job = Job.query.get(job_id)
                if job:
                    job.status = JobStatus.SCHEDULED
                    db.session.commit()
        except Exception as e:
            print(f"Error resuming job {job_id}: {e}")
    
    def delete_job(self, job_id):
        """Delete a scheduled job"""
        try:
            self.scheduler.remove_job(f'job_{job_id}')
        except Exception:
            pass  # Job might not exist in scheduler