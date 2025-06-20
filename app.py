import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from datetime import datetime, date, time
from config import Config
from models import db, Job, Execution, JobStatus, JobFrequency
from scheduler import PythonScriptScheduler
import tempfile

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize scheduler
    scheduler = PythonScriptScheduler(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        return render_template('dashboard.html', jobs=jobs)
    
    @app.route('/upload', methods=['GET', 'POST'])
    def upload_script():
        if request.method == 'POST':
            # Check if file was uploaded
            if 'script_file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['script_file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'Only Python (.py) files are allowed'}), 400
            
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Validate script
            is_valid, message = scheduler.validate_python_script(filepath)
            if not is_valid:
                os.remove(filepath)  # Remove invalid file
                return jsonify({'error': f'Script validation failed: {message}'}), 400
            
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            frequency = request.form.get('frequency')
            execution_time = request.form.get('execution_time')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date') or None
            
            # Create job record
            job = Job(
                name=name,
                description=description,
                script_filename=filename,
                frequency=JobFrequency(frequency),
                execution_time=datetime.strptime(execution_time, '%H:%M').time(),
                start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            )
            
            db.session.add(job)
            db.session.commit()
            
            # Schedule the job
            scheduler.schedule_job(job)
            job.next_execution = scheduler.calculate_next_execution(job)
            db.session.commit()
            
            return jsonify({'success': True, 'job_id': job.id, 'message': 'Script uploaded and scheduled successfully'})
        
        return render_template('upload.html')
    
    @app.route('/api/jobs')
    def get_jobs():
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        return jsonify([job.to_dict() for job in jobs])
    
    @app.route('/api/jobs/<int:job_id>')
    def get_job(job_id):
        job = Job.query.get_or_404(job_id)
        return jsonify(job.to_dict())
    
    @app.route('/api/jobs/<int:job_id>/executions')
    def get_job_executions(job_id):
        executions = Execution.query.filter_by(job_id=job_id).order_by(Execution.started_at.desc()).all()
        return jsonify([execution.to_dict() for execution in executions])
    
    @app.route('/api/jobs/<int:job_id>/pause', methods=['POST'])
    def pause_job(job_id):
        try:
            scheduler.pause_job(job_id)
            return jsonify({'success': True, 'message': 'Job paused successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs/<int:job_id>/resume', methods=['POST'])
    def resume_job(job_id):
        try:
            scheduler.resume_job(job_id)
            return jsonify({'success': True, 'message': 'Job resumed successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs/<int:job_id>/delete', methods=['DELETE'])
    def delete_job(job_id):
        try:
            job = Job.query.get_or_404(job_id)
            
            # Remove from scheduler
            scheduler.delete_job(job_id)
            
            # Remove script file
            script_path = os.path.join(app.config['UPLOAD_FOLDER'], job.script_filename)
            if os.path.exists(script_path):
                os.remove(script_path)
            
            # Delete from database (cascades to executions)
            db.session.delete(job)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Job deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs/<int:job_id>/run', methods=['POST'])
    def run_job_now(job_id):
        try:
            # Run job immediately in background
            scheduler.execute_script(job_id)
            return jsonify({'success': True, 'message': 'Job execution started'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/executions/<int:execution_id>/log')
    def download_execution_log(execution_id):
        execution = Execution.query.get_or_404(execution_id)
        
        # Create temporary log file
        log_content = f"""Execution Log
================
Job ID: {execution.job_id}
Started: {execution.started_at}
Completed: {execution.completed_at or 'Not completed'}
Status: {execution.status}
Duration: {execution.duration}s

Output:
{execution.output or 'No output'}

Error Output:
{execution.error_output or 'No errors'}
"""
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write(log_content)
        temp_file.close()
        
        return send_file(temp_file.name, as_attachment=True, download_name=f'execution_{execution_id}_log.txt')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)