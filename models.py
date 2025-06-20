from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy()

class JobStatus(Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class JobFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    script_filename = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Enum(JobFrequency), nullable=False)
    execution_time = db.Column(db.Time, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum(JobStatus), default=JobStatus.SCHEDULED)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_execution = db.Column(db.DateTime)
    next_execution = db.Column(db.DateTime)
    execution_count = db.Column(db.Integer, default=0)
    
    # Relationship to execution logs
    executions = db.relationship('Execution', backref='job', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'script_filename': self.script_filename,
            'frequency': self.frequency.value,
            'execution_time': self.execution_time.strftime('%H:%M'),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'next_execution': self.next_execution.isoformat() if self.next_execution else None,
            'execution_count': self.execution_count
        }

class Execution(db.Model):
    __tablename__ = 'executions'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), nullable=False)  # success, error, timeout
    output = db.Column(db.Text)
    error_output = db.Column(db.Text)
    duration = db.Column(db.Float)  # in seconds
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'output': self.output,
            'error_output': self.error_output,
            'duration': self.duration
        }