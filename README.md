# ⚙️ Automated Python Script Scheduler

A sleek Flask web app to **upload**, **schedule**, and **auto-execute** Python scripts at predefined intervals. Built for automation enthusiasts, system admins, and dev teams who want a visual and flexible way to manage scheduled jobs.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-black?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-lightblue?logo=mysql)
![APScheduler](https://img.shields.io/badge/APScheduler-3.x-purple)

---

## 🧩 Features

✅ Upload Python scripts via the browser  
📅 Schedule execution:
- **Daily**
- **Weekly**
- **Monthly**

🟢 Start, ⏸ Pause, or 🚀 Run jobs manually  
📊 Track job run logs and statuses  
🔄 Automatically re-load active jobs on restart  
📁 Secure file storage (uploads stored separately)  

---

## 🔧 Tech Stack

| Layer        | Tools Used                                  |
|-------------|----------------------------------------------|
| 💻 Backend   | Flask, SQLAlchemy, APScheduler              |
| 🗃️ Database  | MySQL (via `mysql-connector-python`)         |
| 🎨 Frontend  | Bootstrap 5, HTML, Jinja2                   |
| 📂 Storage   | Local file system (`/uploads`)              |

---

## 📂 Directory Structure

```bash
automated-scheduler/
├── app.py                 # Main Flask app
├── config.py              # DB and app config
├── extensions.py          # SQLAlchemy init
├── models.py              # Job & JobRun models
├── scheduler.py           # APScheduler setup
├── job_runner.py          # Logic to run scripts
├── uploads/               # Saved .py files
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── jobs.html
│   ├── upload.html
│   └── job_detail.html
├── static/                # Custom JS/CSS
└── README.md              # You're reading it!


🚀 Quick Start
1️⃣ Clone the Repo
git clone https://github.com/your-username/automated-scheduler.git
cd automated-scheduler

2️⃣ Install Requirements
pip install -r requirements.txt

3️⃣ Configure Database
Create a MySQL database named script_scheduler.

Update your config.py:
DB_CONFIG = {
    'host': 'localhost',
    'database': 'script_scheduler',
    'user': 'root',
    'password': 'your_mysql_password'
}
4️⃣ Set Up the Tables
Run this once to create the tables:


# In app.py
with app.app_context():
    db.create_all()

Or use Flask-Migrate:
flask db init
flask db migrate -m "initial"
flask db upgrade

5️⃣ Launch the App
python app.py
Navigate to: http://localhost:5000

📸 Screenshots
<details> <summary>📊 Dashboard (Click to expand)</summary>

</details> <details> <summary>📝 Upload Page</summary>

</details> <details> <summary>📁 Job Details & Logs</summary>

</details>
🧠 How It Works
Each uploaded script is saved to /uploads.
Using APScheduler, we schedule jobs via CronTrigger based on:


# Example: Run daily at 10:30 AM
CronTrigger(hour=10, minute=30)
Execution is handled in job_runner.py using Python’s subprocess module. Logs are saved to the database (stdout, stderr, etc.).

📬 API & Dev Ideas
Want to extend this?

🔐 Add user login/auth (Flask-Login)

📡 Build a REST API for mobile triggering

📈 Add real-time updates using Socket.IO

📨 Email notifications on job failures

🧪 Unit testing with pytest

💡 Example Use Cases
Use Case	Description
✅ Auto Reporting	Generate & email daily reports at 8 AM
✅ Health Checks	Run API checks weekly and log failures
✅ Data ETL	Monthly data clean-up or migration scripts
✅ Automation Demos	Showcase timed automations during hackathons

🧑‍💻 Author
Made with 💻 by Anuj Soni
🔗 LinkedIn | [✉️ anujsoni.com](https://www.linkedin.com/in/anuj-soni-2387b5291/)

📄 License
This project is under the MIT License.

🧱 Sample Job Script
# hello.py
from datetime import datetime
print("✅ Script ran at:", datetime.now())
Upload this and schedule it daily to test!
