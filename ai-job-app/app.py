import io
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# BUG FIX: secret key now comes from an environment variable in production,
# falling back to a dev-only value so local runs still work.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///users.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ----------------------------
# DATABASE MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class ReportHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(150))
    job = db.Column(db.String(150))
    risk = db.Column(db.Float)
    level = db.Column(db.String(200))
    selected_skills = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

# ----------------------------
# DATASET
# ----------------------------
data = pd.read_csv("jobs_dataset.csv")
data.columns = data.columns.str.strip().str.lower().str.replace(" ", "_")

# ----------------------------
# JOB SKILLS
# ----------------------------
job_skills = {
    "Data Scientist": ["Python", "SQL", "Machine Learning", "Statistics", "Pandas", "NumPy", "Power BI", "Tableau", "Deep Learning", "Model Deployment"],
    "AI Engineer": ["Python", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "MLOps", "Cloud AI", "Docker", "Deep Learning", "Neural Networks"],
    "Software Developer": ["Python", "Java", "JavaScript", "React", "Node.js", "DSA", "System Design", "SQL", "Git", "APIs"],
    "Cybersecurity Analyst": ["Networking", "Linux", "SIEM", "Penetration Testing", "Ethical Hacking"],
    "Cloud Engineer": ["AWS", "Azure", "Docker", "Kubernetes", "Linux", "CI/CD"],
    "DevOps Engineer": ["Linux", "Docker", "Kubernetes", "Jenkins", "CI/CD", "AWS", "Monitoring"],
    "UX Designer": ["Figma", "Wireframing", "User Research", "Prototyping", "UI Design"],
    "Product Manager": ["Roadmapping", "Agile", "Stakeholder Management", "Analytics", "Communication"],
    "Research Scientist": ["Research Methods", "Python", "Statistics", "Experimentation", "Documentation"],
    "Doctor": ["Diagnosis", "Patient Care", "Medical Knowledge", "Communication"],
    "Surgeon": ["Surgery", "Patient Care", "Precision", "Medical Procedures"],
    "Psychologist": ["Counseling", "Patient Interaction", "Assessment", "Therapy"],
    "Teacher": ["Communication", "Lesson Planning", "LMS", "Public Speaking", "Content Creation"],
    "Nurse": ["Patient Care", "Medical Support", "Communication", "Emergency Response"],
    "Pharmacist": ["Pharmacology", "Prescription Review", "Patient Guidance", "Inventory"],
    "Business Analyst": ["Excel", "SQL", "Power BI", "Tableau", "Reporting", "Stakeholder Communication"],
    "Financial Analyst": ["Excel", "Financial Modeling", "Forecasting", "Power BI", "Reporting"],
    "Accountant": ["Excel", "Tally", "GST", "Taxation", "Finance", "Bookkeeping"],
    "HR Manager": ["Recruitment", "People Management", "Payroll", "Communication"],
    "Marketing Manager": ["SEO", "Social Media", "Campaign Management", "Analytics", "Branding"],
    "Graphic Designer": ["Photoshop", "Illustrator", "Figma", "Branding", "Typography"],
    "Video Editor": ["Premiere Pro", "After Effects", "Storytelling", "Editing"],
    "Content Writer": ["Writing", "SEO", "Research", "Editing", "Content Strategy"],
    "Customer Support Executive": ["Communication", "CRM", "Problem Solving", "Email Support"],
    "Data Entry Clerk": ["Typing", "Excel", "Accuracy", "Documentation"]
}

# ----------------------------
# RISK CALCULATION
# ----------------------------
def calculate_research_risk(row):
    score = (
        row["routine_score"] * 0.30 +
        row["repetitive_score"] * 0.25 +
        row["ai_exposure"] * 0.25 -
        row["creativity_score"] * 0.10 -
        row["human_interaction"] * 0.10
    )
    return round(max(0, min(100, score * 20)), 2)


def get_risk_level(risk):
    if risk < 30:
        return "🟢 Low Risk - This job has a low chance of being automated by AI."
    elif risk < 70:
        return "🟡 Moderate Risk - This job has a moderate chance of partial automation."
    return "🔴 High Risk - This job has a high chance of automation."


def get_skill_gap(job, user_list):
    required = job_skills.get(job, [])
    user_list = [u.lower().strip() for u in user_list]
    return [skill for skill in required if skill.lower() not in user_list]


# ----------------------------
# ROADMAP
# ----------------------------
job_roadmaps = {
    "Business Analyst": {
        "30_days": ["Stakeholder interviews", "Website analysis", "Requirement gathering", "Competitor analysis"],
        "60_days": ["Prepare Business Requirement Document (BRD)", "Create user stories", "Process flow mapping", "Sprint collaboration"],
        "90_days": ["KPI monitoring", "A/B testing", "Product roadmap alignment"]
    },
    "Financial Analyst": {
        "30_days": ["Understand revenue model", "Cost analysis", "Financial review"],
        "60_days": ["Financial forecasting", "ROI analysis", "Cost optimization"],
        "90_days": ["Financial strategy development", "Pricing optimization", "Dashboard creation"]
    },
    "Accountant": {
        "30_days": ["Bookkeeping review", "Account reconciliation", "Compliance understanding"],
        "60_days": ["Invoice and payroll management", "Tax compliance", "Process improvement"],
        "90_days": ["Accounting automation", "Financial statement preparation", "Audit support"]
    },
    "HR Manager": {
        "30_days": ["Workforce analysis", "Policy review", "Hiring needs identification"],
        "60_days": ["Recruitment", "Onboarding process", "Performance management"],
        "90_days": ["Retention strategy", "Training programs", "Culture building"]
    },
    "Marketing Manager": {
        "30_days": ["Market research", "Traffic analysis", "SEO audit"],
        "60_days": ["Campaign execution", "Funnel optimization", "Content collaboration"],
        "90_days": ["Campaign scaling", "ROI optimization", "Brand strategy"]
    },
    "Graphic Designer": {
        "30_days": ["Brand understanding", "Design audit", "Tool familiarization"],
        "60_days": ["Asset creation", "UI improvement", "Collaboration with developers"],
        "90_days": ["Design system creation", "Brand enhancement", "UX optimization"]
    },
    "Video Editor": {
        "30_days": ["Content analysis", "Audience understanding", "Tool learning"],
        "60_days": ["Video production", "Engagement optimization", "Platform optimization"],
        "90_days": ["Campaign creation", "Storytelling improvement", "Workflow management"]
    },
    "Content Writer": {
        "30_days": ["Audience research", "Content audit", "SEO learning"],
        "60_days": ["Content creation", "SEO optimization", "Editing and proofreading"],
        "90_days": ["Content strategy", "Engagement improvement", "Editorial planning"]
    },
    "Customer Support Executive": {
        "30_days": ["Product knowledge", "Tool training", "Basic query handling"],
        "60_days": ["Advanced support", "Response optimization", "Issue documentation"],
        "90_days": ["Process improvement", "Training others", "Customer experience optimization"]
    },
    "Data Entry Clerk": {
        "30_days": ["System learning", "Data entry basics", "Process understanding"],
        "60_days": ["Accuracy improvement", "Data cleaning", "Reporting support"],
        "90_days": ["Automation", "Data integrity maintenance", "System support"]
    },
    "Data Scientist": {
        "30_days": ["Learn Python, Pandas, NumPy", "Statistics basics", "Data cleaning", "EDA", "Mini project"],
        "60_days": ["Supervised learning", "Model training", "Data visualization", "Feature engineering", "Prediction project"],
        "90_days": ["Model optimization", "Deep learning basics", "Deployment with Flask/Streamlit", "Final ML pipeline project"]
    },
    "AI Engineer": {
        "30_days": ["Learn Python and ML basics", "Neural network fundamentals", "TensorFlow and PyTorch"],
        "60_days": ["Deep learning models", "NLP or Computer Vision", "Chatbot or image classifier"],
        "90_days": ["Model optimization", "API integration", "AI-powered app"]
    },
    "Software Developer": {
        "30_days": ["Programming fundamentals", "DSA basics", "Simple coding programs"],
        "60_days": ["Frontend development", "Backend basics", "CRUD application"],
        "90_days": ["Full-stack development", "Authentication", "API integration", "Deploy full web app"]
    },
    "Cybersecurity Analyst": {
        "30_days": ["Networking basics", "Linux fundamentals", "Cybersecurity principles"],
        "60_days": ["Wireshark and Nmap", "Vulnerability scanning", "Security audit"],
        "90_days": ["Penetration testing", "Ethical hacking labs", "Security assessment report"]
    },
    "Cloud Engineer": {
        "30_days": ["Cloud basics", "Virtual machines", "Deploy simple app"],
        "60_days": ["Core cloud services", "IAM", "Scalable system"],
        "90_days": ["Kubernetes", "CI/CD", "Cloud architecture"]
    },
    "DevOps Engineer": {
        "30_days": ["Linux basics", "Git", "CI/CD concepts"],
        "60_days": ["Docker", "Jenkins", "Pipeline project"],
        "90_days": ["Kubernetes", "Terraform", "End-to-end workflow"]
    },
    "UX Designer": {
        "30_days": ["Design principles", "User research", "Figma"],
        "60_days": ["Wireframes", "Prototypes", "Usability testing"],
        "90_days": ["Case studies", "UX portfolio", "Advanced strategies"]
    },
    "Product Manager": {
        "30_days": ["Product lifecycle", "Market research", "Agile basics"],
        "60_days": ["Roadmaps", "Stakeholder communication", "PRD"],
        "90_days": ["KPIs", "Launch strategy", "Product roadmap"]
    },
    "Research Scientist": {
        "30_days": ["Research methodology", "Literature review", "Academic writing"],
        "60_days": ["Experiment design", "Data analysis", "Mini research"],
        "90_days": ["Publishing", "Research paper"]
    },
    "Doctor": {
        "30_days": ["Medical fundamentals", "Patient communication"],
        "60_days": ["Clinical observation", "Diagnosis methods"],
        "90_days": ["Case handling", "Case documentation"]
    },
    "Surgeon": {
        "30_days": ["Anatomy study", "Observation"],
        "60_days": ["Assist surgeries", "Learn techniques"],
        "90_days": ["Supervised operations", "Surgical case log"]
    },
    "Psychologist": {
        "30_days": ["Psychology basics", "Counseling skills"],
        "60_days": ["Therapy methods", "Case studies"],
        "90_days": ["Practice sessions", "Psychological report"]
    },
    "Teacher": {
        "30_days": ["Lesson planning", "Teaching methods"],
        "60_days": ["Classroom management", "Student engagement"],
        "90_days": ["Assessments", "Teaching portfolio"]
    },
    "Nurse": {
        "30_days": ["Basic care", "Patient interaction"],
        "60_days": ["Clinical practice", "Emergency care"],
        "90_days": ["Specialized care", "Case records"]
    },
    "Pharmacist": {
        "30_days": ["Drug basics", "Pharmacology"],
        "60_days": ["Prescription handling", "Patient counseling"],
        "90_days": ["Clinical pharmacy", "Medication system"]
    }
}

# ----------------------------
# CAREER PATH
# ----------------------------
def generate_career(job):
    career_paths = {
        "Data Scientist": [
            {"title": "Machine Learning Engineer", "reason": "Move into model building and deployment"},
            {"title": "AI Engineer", "reason": "Advance into deep learning systems"},
            {"title": "Analytics Lead", "reason": "Lead data-driven business decisions"}
        ],
        "AI Engineer": [
            {"title": "Senior ML Engineer", "reason": "Build advanced ML systems"},
            {"title": "AI Research Scientist", "reason": "Focus on innovation and models"},
            {"title": "MLOps Architect", "reason": "Scale AI systems in production"}
        ],
        "Software Developer": [
            {"title": "Full Stack Developer", "reason": "Expand frontend and backend skills"},
            {"title": "System Architect", "reason": "Design large-scale systems"},
            {"title": "DevOps Engineer", "reason": "Move into deployment and automation"}
        ],
        "Cybersecurity Analyst": [
            {"title": "Security Engineer", "reason": "Build secure systems"},
            {"title": "Penetration Tester", "reason": "Specialize in ethical hacking"},
            {"title": "Security Architect", "reason": "Design enterprise security systems"}
        ],
        "Cloud Engineer": [
            {"title": "Cloud Architect", "reason": "Design scalable cloud systems"},
            {"title": "DevOps Engineer", "reason": "Automation and CI/CD pipelines"},
            {"title": "Site Reliability Engineer", "reason": "Improve system reliability"}
        ],
        "DevOps Engineer": [
            {"title": "Site Reliability Engineer", "reason": "Focus on system uptime"},
            {"title": "Cloud Architect", "reason": "Design cloud infrastructure"},
            {"title": "Platform Engineer", "reason": "Build internal developer platforms"}
        ],
        "UX Designer": [
            {"title": "UI/UX Product Designer", "reason": "Work on end-to-end product design"},
            {"title": "Product Designer", "reason": "Own full design lifecycle"},
            {"title": "Design Lead", "reason": "Lead design teams and strategy"}
        ],
        "Product Manager": [
            {"title": "Senior Product Manager", "reason": "Handle larger product lines"},
            {"title": "Product Lead", "reason": "Lead product strategy"},
            {"title": "Chief Product Officer", "reason": "Executive product leadership"}
        ],
        "Research Scientist": [
            {"title": "Senior Research Scientist", "reason": "Lead research projects"},
            {"title": "Data Scientist", "reason": "Apply research to industry data"},
            {"title": "AI Research Lead", "reason": "Head research teams"}
        ],
        "Doctor": [
            {"title": "Specialist Doctor", "reason": "Focus on medical specialization"},
            {"title": "Hospital Consultant", "reason": "Advise complex medical cases"},
            {"title": "Medical Researcher", "reason": "Contribute to medical studies"}
        ],
        "Surgeon": [
            {"title": "Senior Surgeon", "reason": "Advanced surgical practice"},
            {"title": "Surgical Specialist", "reason": "Highly specialized procedures"},
            {"title": "Medical Director", "reason": "Hospital leadership role"}
        ],
        "Psychologist": [
            {"title": "Clinical Psychologist", "reason": "Advanced patient therapy"},
            {"title": "Counseling Psychologist", "reason": "Focus on behavioral therapy"},
            {"title": "Mental Health Consultant", "reason": "Corporate or institutional consulting"}
        ],
        "Teacher": [
            {"title": "Senior Educator", "reason": "Advanced teaching experience"},
            {"title": "Principal", "reason": "School leadership role"},
            {"title": "Curriculum Developer", "reason": "Design learning materials"}
        ],
        "Nurse": [
            {"title": "Senior Nurse", "reason": "Advanced patient care"},
            {"title": "Nurse Supervisor", "reason": "Manage nursing teams"},
            {"title": "Clinical Nurse Specialist", "reason": "Specialized medical care"}
        ],
        "Pharmacist": [
            {"title": "Clinical Pharmacist", "reason": "Hospital-based pharmacy role"},
            {"title": "Pharma Manager", "reason": "Manage pharmacy operations"},
            {"title": "Drug Research Scientist", "reason": "Research new medicines"}
        ],
        "Business Analyst": [
            {"title": "Product Manager", "reason": "Move into product ownership"},
            {"title": "Data Analyst Lead", "reason": "Lead analytics teams"},
            {"title": "Management Consultant", "reason": "Strategic business consulting"}
        ],
        "Financial Analyst": [
            {"title": "Investment Analyst", "reason": "Focus on market investments"},
            {"title": "Finance Manager", "reason": "Manage financial planning"},
            {"title": "Portfolio Manager", "reason": "Handle investment portfolios"}
        ],
        "Accountant": [
            {"title": "Senior Accountant", "reason": "Advanced accounting responsibilities"},
            {"title": "Auditor", "reason": "Ensure financial compliance"},
            {"title": "Finance Controller", "reason": "Oversee financial operations"}
        ],
        "HR Manager": [
            {"title": "HR Director", "reason": "Lead HR department"},
            {"title": "Talent Acquisition Head", "reason": "Manage recruitment strategy"},
            {"title": "Chief HR Officer", "reason": "Executive HR leadership"}
        ],
        "Marketing Manager": [
            {"title": "Digital Marketing Head", "reason": "Lead online marketing"},
            {"title": "Brand Manager", "reason": "Manage brand strategy"},
            {"title": "Chief Marketing Officer", "reason": "Executive marketing role"}
        ],
        "Graphic Designer": [
            {"title": "Senior Designer", "reason": "Advanced design work"},
            {"title": "Art Director", "reason": "Lead creative direction"},
            {"title": "UI/UX Designer", "reason": "Transition into digital product design"}
        ],
        "Video Editor": [
            {"title": "Motion Graphics Designer", "reason": "Advanced video effects"},
            {"title": "Film Editor", "reason": "Cinema-level editing"},
            {"title": "Creative Director", "reason": "Lead visual storytelling"}
        ],
        "Content Writer": [
            {"title": "Content Strategist", "reason": "Plan content direction"},
            {"title": "SEO Specialist", "reason": "Optimize content performance"},
            {"title": "Editor-in-Chief", "reason": "Lead content teams"}
        ],
        "Customer Support Executive": [
            {"title": "Support Team Lead", "reason": "Manage support agents"},
            {"title": "Customer Success Manager", "reason": "Improve client experience"},
            {"title": "Operations Manager", "reason": "Handle service operations"}
        ],
        "Data Entry Clerk": [
            {"title": "Data Analyst", "reason": "Move into analytics role"},
            {"title": "Operations Executive", "reason": "Broader office operations"},
            {"title": "Office Administrator", "reason": "Manage administrative tasks"}
        ]
    }

    return career_paths.get(job, [
        {"title": "Domain Specialist", "reason": "Grow in your current field"},
        {"title": "Senior Professional", "reason": "Gain experience-based promotion"},
        {"title": "Team Lead", "reason": "Move into leadership role"}
    ])


# ----------------------------
# INCOME OPTIONS
# ----------------------------
def generate_income(job):
    income_options = {
        "Data Scientist": [
            {"title": "Freelance Consulting", "desc": "Offer your data science expertise to businesses on a project basis."},
            {"title": "Online Course Creation", "desc": "Develop and sell courses on Udemy or Coursera."},
            {"title": "Data Science Blogging", "desc": "Monetize blogs via ads, sponsorships, or affiliate marketing."},
            {"title": "Data Product Development", "desc": "Create dashboards or predictive models and sell them."},
            {"title": "Data Science Competitions", "desc": "Earn prizes via Kaggle competitions and hackathons."}
        ],
        "AI Engineer": [
            {"title": "AI Startup", "desc": "Launch your own AI-focused startup."},
            {"title": "Freelance AI Development", "desc": "Offer AI solutions to clients."},
            {"title": "AI Consulting", "desc": "Help businesses implement AI strategies."},
            {"title": "AI Software Products", "desc": "Build and sell AI-powered applications."},
            {"title": "AI Research", "desc": "Publish papers and contribute to AI innovation."}
        ],
        "Software Developer": [
            {"title": "Freelance Development", "desc": "Build software solutions for clients."},
            {"title": "Software Products", "desc": "Develop and sell your own apps."},
            {"title": "WordPress Themes/Plugins", "desc": "Create and sell web tools."},
            {"title": "Online Teaching", "desc": "Create coding courses."},
            {"title": "Tech Blogging", "desc": "Monetize programming content."}
        ],
        "Cybersecurity Analyst": [
            {"title": "Cybersecurity Consulting", "desc": "Provide security solutions to companies."},
            {"title": "Bug Bounty Programs", "desc": "Earn rewards for finding vulnerabilities."},
            {"title": "Security Training", "desc": "Teach cybersecurity skills."},
            {"title": "Penetration Testing", "desc": "Test systems for security flaws."},
            {"title": "Cybersecurity Blogging", "desc": "Share knowledge and earn online."}
        ],
        "Cloud Engineer": [
            {"title": "Cloud Consulting", "desc": "Help businesses migrate to cloud."},
            {"title": "Cloud Software Development", "desc": "Build cloud-based applications."},
            {"title": "Infrastructure Management", "desc": "Maintain cloud systems for clients."},
            {"title": "Online Courses", "desc": "Teach AWS/Azure/GCP skills."},
            {"title": "Cloud Blogging", "desc": "Create content on cloud technologies."}
        ],
        "DevOps Engineer": [
            {"title": "DevOps Consulting", "desc": "Optimize deployment pipelines."},
            {"title": "Automation Tools", "desc": "Build CI/CD automation tools."},
            {"title": "Cloud Infrastructure Work", "desc": "Manage scalable systems."},
            {"title": "DevOps Training", "desc": "Teach DevOps practices."},
            {"title": "Tech Content Creation", "desc": "Write DevOps tutorials."}
        ],
        "UX Designer": [
            {"title": "Freelance UX Design", "desc": "Design apps and websites."},
            {"title": "UX Consulting", "desc": "Improve product usability."},
            {"title": "UI/UX Courses", "desc": "Teach design principles."},
            {"title": "UX Research Services", "desc": "Conduct user research."},
            {"title": "Template Selling", "desc": "Sell UI kits and templates."}
        ],
        "Product Manager": [
            {"title": "Product Consulting", "desc": "Guide startups on product strategy."},
            {"title": "Freelance Roadmapping", "desc": "Build product plans for companies."},
            {"title": "Digital Products", "desc": "Create and sell SaaS or tools."},
            {"title": "PM Training", "desc": "Teach product management skills."},
            {"title": "Content Creation", "desc": "Share PM knowledge online."}
        ],
        "Research Scientist": [
            {"title": "Research Grants", "desc": "Get funding for scientific research."},
            {"title": "Industry Consulting", "desc": "Work with companies on innovation."},
            {"title": "Startup Development", "desc": "Build research-based startups."},
            {"title": "Patent Licensing", "desc": "License innovations."},
            {"title": "Science Writing", "desc": "Publish research content."}
        ],
        "Doctor": [
            {"title": "Private Practice", "desc": "Treat patients independently."},
            {"title": "Telemedicine", "desc": "Online medical consultations."},
            {"title": "Medical Consulting", "desc": "Advise healthcare organizations."},
            {"title": "Medical Writing", "desc": "Write healthcare articles."},
            {"title": "Medical Research", "desc": "Contribute to medical studies."}
        ],
        "Surgeon": [
            {"title": "Private Surgery Practice", "desc": "Perform specialized surgeries."},
            {"title": "Hospital Consulting", "desc": "Work as expert surgeon advisor."},
            {"title": "Medical Device Work", "desc": "Help design surgical tools."},
            {"title": "Telemedicine Consultations", "desc": "Remote patient advice."},
            {"title": "Teaching & Training", "desc": "Train new surgeons."}
        ],
        "Psychologist": [
            {"title": "Private Practice", "desc": "Offer therapy sessions."},
            {"title": "Online Counseling", "desc": "Provide virtual therapy."},
            {"title": "Corporate Consulting", "desc": "Improve workplace mental health."},
            {"title": "Writing & Books", "desc": "Publish psychology content."},
            {"title": "Training Programs", "desc": "Run mental health workshops."}
        ],
        "Teacher": [
            {"title": "Tutoring", "desc": "Teach students individually."},
            {"title": "Online Teaching", "desc": "Create online courses."},
            {"title": "Curriculum Design", "desc": "Develop learning materials."},
            {"title": "Educational Consulting", "desc": "Help schools improve teaching."},
            {"title": "Educational Content Creation", "desc": "Write books and resources."}
        ],
        "Nurse": [
            {"title": "Hospital Nursing", "desc": "Work in healthcare institutions."},
            {"title": "Travel Nursing", "desc": "Work in different locations."},
            {"title": "Home Care Services", "desc": "Provide patient care at home."},
            {"title": "Medical Support Work", "desc": "Assist healthcare professionals."},
            {"title": "Healthcare Business", "desc": "Start health services."}
        ],
        "Pharmacist": [
            {"title": "Pharmacy Ownership", "desc": "Run your own pharmacy."},
            {"title": "Consulting", "desc": "Advise healthcare companies."},
            {"title": "Telepharmacy", "desc": "Remote medicine services."},
            {"title": "Drug Sales", "desc": "Work in pharma sales."},
            {"title": "Compounding Pharmacy", "desc": "Specialized medicine preparation."}
        ],
        "Business Analyst": [
            {"title": "Freelance Consulting", "desc": "Work with companies on analysis."},
            {"title": "Project Management", "desc": "Move into management roles."},
            {"title": "Data Analysis", "desc": "Work in BI and analytics."},
            {"title": "Entrepreneurship", "desc": "Start your own business."},
            {"title": "Training Services", "desc": "Teach business analysis."}
        ],
        "Financial Analyst": [
            {"title": "Investment Banking", "desc": "Work in finance sector."},
            {"title": "Portfolio Management", "desc": "Manage investments."},
            {"title": "Financial Consulting", "desc": "Advise businesses."},
            {"title": "Trading", "desc": "Stock market trading."},
            {"title": "Real Estate Investment", "desc": "Property investment income."}
        ],
        "Accountant": [
            {"title": "Freelance Accounting", "desc": "Offer accounting services."},
            {"title": "Tax Consulting", "desc": "GST and tax filing services."},
            {"title": "Financial Planning", "desc": "Help clients manage money."},
            {"title": "Forensic Accounting", "desc": "Detect financial fraud."},
            {"title": "Business Consulting", "desc": "Advise companies financially."}
        ],
        "HR Manager": [
            {"title": "HR Consulting", "desc": "Help companies manage HR."},
            {"title": "Recruitment Services", "desc": "Hire employees for firms."},
            {"title": "Training Programs", "desc": "Employee development."},
            {"title": "HR Technology", "desc": "Work with HR software."},
            {"title": "Compensation Advisory", "desc": "Salary structure planning."}
        ],
        "Marketing Manager": [
            {"title": "Marketing Agency", "desc": "Run your own agency."},
            {"title": "Digital Marketing", "desc": "SEO and ads services."},
            {"title": "Content Creation", "desc": "Brand marketing content."},
            {"title": "Social Media Management", "desc": "Handle online presence."},
            {"title": "Brand Consulting", "desc": "Help companies grow brands."}
        ],
        "Graphic Designer": [
            {"title": "Freelance Design", "desc": "Client-based design work."},
            {"title": "Web Design", "desc": "Build websites UI."},
            {"title": "Brand Identity Design", "desc": "Create brand systems."},
            {"title": "Illustration Work", "desc": "Art and digital illustrations."},
            {"title": "Template Selling", "desc": "Sell design assets online."}
        ],
        "Video Editor": [
            {"title": "Freelance Editing", "desc": "Edit videos for clients."},
            {"title": "YouTube Editing", "desc": "Work with creators."},
            {"title": "Motion Graphics", "desc": "Advanced video effects."},
            {"title": "Film Editing", "desc": "Cinema production work."},
            {"title": "Content Agency", "desc": "Video production business."}
        ],
        "Content Writer": [
            {"title": "Freelance Writing", "desc": "Write for clients."},
            {"title": "Blogging", "desc": "Start your own blog."},
            {"title": "Copywriting", "desc": "Marketing writing."},
            {"title": "Technical Writing", "desc": "Documentation creation."},
            {"title": "Content Marketing", "desc": "SEO content strategy."}
        ],
        "Customer Support Executive": [
            {"title": "Remote Support Jobs", "desc": "Work from home support."},
            {"title": "Virtual Assistant", "desc": "Admin support tasks."},
            {"title": "CRM Management", "desc": "Manage customer systems."},
            {"title": "Sales Transition", "desc": "Move into sales roles."},
            {"title": "Support Training", "desc": "Train customer teams."}
        ],
        "Data Entry Clerk": [
            {"title": "Freelance Data Entry", "desc": "Simple online tasks."},
            {"title": "Virtual Assistant", "desc": "Admin and office support."},
            {"title": "Transcription Work", "desc": "Audio to text services."},
            {"title": "Data Analyst Path", "desc": "Upgrade to analytics roles."},
            {"title": "Office Administration", "desc": "Manage office tasks."}
        ]
    }

    return income_options.get(job, [
        {"title": "Freelancing", "desc": "Skill-based income opportunities"},
        {"title": "Remote Work", "desc": "Work-from-home jobs"},
        {"title": "Consulting", "desc": "Domain expertise services"}
    ])


def generate_trends(job):
    trends = {
        "Data Scientist": [
            "Shift from basic analytics → AI-driven predictive modeling",
            "High demand for data storytelling + business insights",
            "Strong growth in healthcare, fintech, and e-commerce analytics"
        ],
        "AI Engineer": [
            "Explosion in generative AI, LLM apps, and AI automation tools",
            "Companies hiring for AI integration + deployment (not just research)",
            "MLOps + cloud AI systems becoming mandatory skills"
        ],
        "Software Developer": [
            "AI-assisted coding becoming standard in development workflows",
            "Demand shifting toward full-stack + system design roles",
            "Strong need for developers who can integrate APIs and AI tools"
        ],
        "Cybersecurity Analyst": [
            "Rapid increase in cyber attacks due to AI-powered hacking",
            "High demand for ethical hackers and security automation experts",
            "Cloud security and zero-trust architecture becoming critical"
        ],
        "Cloud Engineer": [
            "Massive cloud migration still ongoing globally",
            "Rise of multi-cloud and hybrid cloud systems",
            "Demand for cost optimization and cloud security experts"
        ],
        "DevOps Engineer": [
            "DevOps evolving into platform engineering and automation roles",
            "Strong demand for CI/CD + Kubernetes + infrastructure automation",
            "AI is now used to monitor and auto-fix system failures"
        ],
        "UX Designer": [
            "AI tools speeding up UI/UX prototyping",
            "Focus shifting to user psychology + product experience design",
            "Demand for designers who understand product + tech integration"
        ],
        "Product Manager": [
            "AI product management becoming a top role in tech companies",
            "Need for strong technical + business hybrid skills",
            "Focus on data-driven product decision-making"
        ],
        "Research Scientist": [
            "AI research and applied science roles expanding rapidly",
            "Industry research collaborations increasing (big tech + universities)",
            "Focus on LLMs, robotics, and advanced ML systems"
        ],
        "Doctor": [
            "Telemedicine and AI-assisted diagnosis growing fast",
            "Digital health records becoming standard worldwide",
            "Demand increasing in rural and remote healthcare services"
        ],
        "Surgeon": [
            "Robotic surgery and AI-assisted procedures increasing",
            "High specialization demand in complex surgeries",
            "Advanced imaging tech improving surgical precision"
        ],
        "Psychologist": [
            "Mental health awareness driving global demand",
            "Rise of online therapy and tele-counseling platforms",
            "Workplace mental health consulting growing"
        ],
        "Teacher": [
            "Shift toward online and hybrid learning systems",
            "AI tools used for personalized student learning",
            "High demand for digital content creators in education"
        ],
        "Nurse": [
            "Strong global shortage increasing job demand",
            "Use of digital health monitoring tools in hospitals",
            "Growth in home-care and elderly care services"
        ],
        "Pharmacist": [
            "Digital pharmacies and e-prescription systems rising",
            "Demand for clinical pharmacy in hospitals increasing",
            "Pharma logistics and supply chain automation growing"
        ],
        "Business Analyst": [
            "Shift toward data-driven business decision systems",
            "High demand for Power BI + SQL analytics skills",
            "Companies adopting real-time dashboard reporting"
        ],
        "Financial Analyst": [
            "AI-driven financial forecasting becoming standard",
            "Growth in fintech, crypto, and digital banking analysis",
            "Demand for investment risk modeling experts"
        ],
        "Accountant": [
            "Automation of bookkeeping using AI tools",
            "Focus shifting to tax strategy and advisory roles",
            "Cloud accounting systems replacing manual processes"
        ],
        "HR Manager": [
            "AI-based recruitment and talent screening tools increasing",
            "Focus on employee experience and retention strategies",
            "Remote workforce management becoming standard"
        ],
        "Marketing Manager": [
            "AI-driven digital marketing and ad optimization booming",
            "Strong demand for SEO + performance marketing skills",
            "Influencer + social media marketing expanding rapidly"
        ],
        "Graphic Designer": [
            "AI design tools increasing productivity (Figma AI, Canva AI)",
            "High demand for brand identity + UI design skills",
            "Motion graphics and 3D design trending upward"
        ],
        "Video Editor": [
            "Short-form content (Reels, Shorts, TikTok) dominating demand",
            "AI video editing tools speeding up production",
            "Freelance video editing market growing globally"
        ],
        "Content Writer": [
            "SEO writing evolving with AI-assisted content tools",
            "High demand for storytelling + brand content",
            "Content strategy more important than basic writing"
        ],
        "Customer Support Executive": [
            "AI chatbots handling basic queries",
            "Human support shifting to complex problem solving",
            "Remote customer support jobs increasing"
        ],
        "Data Entry Clerk": [
            "Automation reducing manual data entry jobs",
            "Shift toward virtual assistant and admin support roles",
            "Need for accuracy + digital tool proficiency"
        ]
    }

    return trends.get(job, [
        "AI is transforming most industries",
        "Automation is increasing across job roles",
        "Upskilling in digital tools is essential"
    ])


def generate_upskill(job):
    upskill_map = {
        "Data Scientist": ["Master advanced Python (Pandas, NumPy, Scikit-learn)", "Learn real-world ML projects (prediction, classification)", "Practice Kaggle competitions daily", "Learn deployment (Flask, FastAPI, Docker)", "Build 3–5 portfolio projects with dashboards"],
        "AI Engineer": ["Deep dive into Deep Learning (CNN, RNN, Transformers)", "Master TensorFlow and PyTorch", "Learn LLMs and Generative AI tools", "Practice building AI apps (chatbots, vision apps)", "Learn MLOps + cloud deployment (AWS/GCP)"],
        "Software Developer": ["Master Data Structures & Algorithms", "Build full-stack projects (React + Node.js)", "Learn system design basics", "Practice API development and integration", "Contribute to open-source projects"],
        "Cybersecurity Analyst": ["Learn networking fundamentals deeply", "Practice ethical hacking labs (TryHackMe, HackTheBox)", "Master Linux security tools", "Learn SIEM tools (Splunk, QRadar)", "Get certifications (CEH, CompTIA Security+)"],
        "Cloud Engineer": ["Master AWS / Azure / GCP fundamentals", "Learn Docker and Kubernetes deeply", "Practice cloud architecture design", "Build scalable cloud projects", "Learn Infrastructure as Code (Terraform)"],
        "DevOps Engineer": ["Master Linux and shell scripting", "Learn CI/CD tools (Jenkins, GitHub Actions)", "Deep dive into Docker + Kubernetes", "Learn monitoring tools (Prometheus, Grafana)", "Build end-to-end deployment pipelines"],
        "UX Designer": ["Master Figma and advanced prototyping", "Study UI principles and color theory", "Learn user research and psychology", "Build real app redesign case studies", "Create strong portfolio (Behance/Dribbble)"],
        "Product Manager": ["Learn Agile and Scrum deeply", "Practice writing product requirement documents (PRD)", "Study real product case studies", "Learn analytics tools (Mixpanel, GA)", "Work on mock startup product ideas"],
        "Research Scientist": ["Strengthen mathematics and statistics", "Learn advanced research methodologies", "Publish small research papers", "Learn Python for scientific computing", "Collaborate on academic projects"],
        "Doctor": ["Master clinical knowledge and diagnosis", "Practice patient case studies", "Learn modern medical technologies", "Stay updated with medical research papers", "Gain hands-on hospital experience"],
        "Surgeon": ["Master surgical anatomy deeply", "Practice surgical simulations", "Learn advanced surgical techniques", "Observe senior surgeons in operation", "Attend surgical workshops and training"],
        "Psychologist": ["Study human behavior and psychology theories", "Practice counseling sessions", "Learn CBT and therapy techniques", "Gain real case experience", "Specialize in clinical psychology areas"],
        "Teacher": ["Master subject knowledge deeply", "Learn digital teaching tools (LMS, Zoom)", "Create engaging lesson plans", "Develop communication and presentation skills", "Build online teaching portfolio"],
        "Nurse": ["Master patient care techniques", "Learn emergency response procedures", "Practice hospital training cases", "Study medical terminology deeply", "Gain specialization (ICU, pediatrics)"],
        "Pharmacist": ["Study advanced pharmacology", "Learn prescription analysis", "Understand drug interactions deeply", "Practice hospital pharmacy work", "Learn pharmaceutical business operations"],
        "Business Analyst": ["Master Excel, SQL, and Power BI", "Learn business intelligence tools", "Study real business case studies", "Practice dashboard creation", "Improve stakeholder communication skills"],
        "Financial Analyst": ["Master financial modeling in Excel", "Learn stock market analysis", "Study corporate finance deeply", "Practice investment simulations", "Use Bloomberg/financial tools"],
        "Accountant": ["Master advanced accounting principles", "Learn GST and tax regulations", "Practice Tally and accounting software", "Study auditing procedures", "Work on real company books"],
        "HR Manager": ["Learn recruitment strategies deeply", "Master HR tools (SAP, Workday)", "Practice employee management scenarios", "Learn labor laws and compliance", "Develop leadership and communication skills"],
        "Marketing Manager": ["Master SEO and digital marketing tools", "Learn paid ads (Google, Meta)", "Study brand building strategies", "Practice campaign analysis", "Build real marketing campaigns"],
        "Graphic Designer": ["Master Photoshop, Illustrator, Figma", "Study typography and composition", "Practice daily design challenges", "Build strong portfolio projects", "Learn motion graphics basics"],
        "Video Editor": ["Master Premiere Pro and After Effects", "Practice storytelling through video", "Learn color grading techniques", "Edit real client projects", "Specialize in short-form content (Reels, Shorts)"],
        "Content Writer": ["Improve grammar and writing style", "Learn SEO writing techniques", "Practice daily content creation", "Build blog/portfolio website", "Study copywriting frameworks"],
        "Customer Support Executive": ["Improve communication skills", "Learn CRM tools (Zendesk, Freshdesk)", "Practice real customer scenarios", "Develop problem-solving skills", "Learn escalation handling"],
        "Data Entry Clerk": ["Increase typing speed and accuracy", "Master Excel shortcuts", "Practice data organization tasks", "Learn virtual assistant tools", "Upgrade toward data analysis skills"]
    }

    return upskill_map.get(job, [
        "Learn core skills of your domain",
        "Build real-world projects",
        "Practice daily improvement",
        "Gain certifications",
        "Work on internships or freelance tasks"
    ])


# ----------------------------
# RESOURCE HUB
# ----------------------------
def generate_resources(job):
    resources = {
        "Data Scientist": [
            {"name": "Kaggle", "link": "https://www.kaggle.com", "type": "Practice Platform"},
            {"name": "IBM SkillsBuild", "link": "https://skillsbuild.org", "type": "Course"},
            {"name": "Scikit-learn Docs", "link": "https://scikit-learn.org", "type": "Documentation"},
            {"name": "Pandas Documentation", "link": "https://pandas.pydata.org/docs", "type": "Documentation"},
            {"name": "Google Colab", "link": "https://colab.research.google.com", "type": "Tool"}
        ],
        "AI Engineer": [
            {"name": "DeepLearning.AI", "link": "https://www.deeplearning.ai", "type": "Course"},
            {"name": "TensorFlow Docs", "link": "https://www.tensorflow.org", "type": "Documentation"},
            {"name": "PyTorch Tutorials", "link": "https://pytorch.org/tutorials", "type": "Documentation"},
            {"name": "Hugging Face", "link": "https://huggingface.co", "type": "Tool"},
            {"name": "Google AI", "link": "https://ai.google", "type": "Learning"}
        ],
        "Software Developer": [
            {"name": "freeCodeCamp", "link": "https://www.freecodecamp.org", "type": "Course"},
            {"name": "MDN Web Docs", "link": "https://developer.mozilla.org", "type": "Documentation"},
            {"name": "LeetCode", "link": "https://leetcode.com", "type": "Practice"},
            {"name": "GitHub", "link": "https://github.com", "type": "Tool"},
            {"name": "Stack Overflow", "link": "https://stackoverflow.com", "type": "Community"}
        ],
        "Cybersecurity Analyst": [
            {"name": "TryHackMe", "link": "https://tryhackme.com", "type": "Practice"},
            {"name": "Hack The Box", "link": "https://hackthebox.com", "type": "Practice"},
            {"name": "OWASP", "link": "https://owasp.org", "type": "Documentation"},
            {"name": "Kali Linux Docs", "link": "https://www.kali.org/docs", "type": "Documentation"},
            {"name": "Practical DevSecOps", "link": "https://www.practical-devsecops.com", "type": "Course"}
        ],
        "Cloud Engineer": [
            {"name": "AWS Skill Builder", "link": "https://explore.skillbuilder.aws", "type": "Course"},
            {"name": "Microsoft Learn (Azure)", "link": "https://learn.microsoft.com", "type": "Documentation"},
            {"name": "Google Cloud Training", "link": "https://cloud.google.com/training", "type": "Course"},
            {"name": "Docker Docs", "link": "https://docs.docker.com", "type": "Documentation"},
            {"name": "Kubernetes Docs", "link": "https://kubernetes.io/docs", "type": "Documentation"}
        ],
        "DevOps Engineer": [
            {"name": "Git Documentation", "link": "https://git-scm.com/docs", "type": "Documentation"},
            {"name": "Docker Docs", "link": "https://docs.docker.com", "type": "Documentation"},
            {"name": "Kubernetes Docs", "link": "https://kubernetes.io/docs", "type": "Documentation"},
            {"name": "Jenkins Docs", "link": "https://www.jenkins.io/doc", "type": "Documentation"},
            {"name": "DevOps Roadmap", "link": "https://roadmap.sh/devops", "type": "Guide"}
        ],
        "UX Designer": [
            {"name": "Google UX Design Course", "link": "https://www.coursera.org/professional-certificates/google-ux-design", "type": "Course"},
            {"name": "Figma", "link": "https://www.figma.com", "type": "Tool"},
            {"name": "Nielsen Norman Group", "link": "https://www.nngroup.com", "type": "Research"},
            {"name": "Adobe XD", "link": "https://www.adobe.com/products/xd.html", "type": "Tool"},
            {"name": "UX Collective", "link": "https://uxdesign.cc", "type": "Blog"}
        ],
        "Product Manager": [
            {"name": "Product School", "link": "https://productschool.com", "type": "Course"},
            {"name": "Scrum Guide", "link": "https://scrumguides.org", "type": "Documentation"},
            {"name": "Atlassian Agile", "link": "https://www.atlassian.com/agile", "type": "Learning"},
            {"name": "Notion", "link": "https://www.notion.so", "type": "Tool"},
            {"name": "Aha!", "link": "https://www.aha.io", "type": "Tool"}
        ],
        "Research Scientist": [
            {"name": "Google Scholar", "link": "https://scholar.google.com", "type": "Research"},
            {"name": "arXiv", "link": "https://arxiv.org", "type": "Research"},
            {"name": "ResearchGate", "link": "https://www.researchgate.net", "type": "Community"},
            {"name": "Overleaf", "link": "https://www.overleaf.com", "type": "Tool"},
            {"name": "Mendeley", "link": "https://www.mendeley.com", "type": "Tool"}
        ],
        "Doctor": [
            {"name": "PubMed", "link": "https://pubmed.ncbi.nlm.nih.gov", "type": "Research"},
            {"name": "WHO", "link": "https://www.who.int", "type": "Guidelines"},
            {"name": "Medscape", "link": "https://www.medscape.com", "type": "Learning"},
            {"name": "AMBOSS", "link": "https://www.amboss.com", "type": "Course"},
            {"name": "Osmosis", "link": "https://www.osmosis.org", "type": "Course"}
        ],
        "Surgeon": [
            {"name": "Touch Surgery", "link": "https://www.touchsurgery.com", "type": "Simulation"},
            {"name": "WebSurg", "link": "https://www.websurg.com", "type": "Learning"},
            {"name": "TeachMeAnatomy", "link": "https://teachmeanatomy.info", "type": "Reference"},
            {"name": "BMJ Learning", "link": "https://new-learning.bmj.com", "type": "Course"},
            {"name": "Geeky Medics", "link": "https://geekymedics.com", "type": "Practice"}
        ],
        "Psychologist": [
            {"name": "APA", "link": "https://www.apa.org", "type": "Guidelines"},
            {"name": "Coursera Psychology", "link": "https://www.coursera.org", "type": "Course"},
            {"name": "Simply Psychology", "link": "https://www.simplypsychology.org", "type": "Learning"},
            {"name": "Psychology Today", "link": "https://www.psychologytoday.com", "type": "Articles"},
            {"name": "MindTools", "link": "https://www.mindtools.com", "type": "Tool"}
        ],
        "Teacher": [
            {"name": "Khan Academy", "link": "https://www.khanacademy.org", "type": "Teaching"},
            {"name": "Google for Education", "link": "https://edu.google.com", "type": "Tool"},
            {"name": "Edutopia", "link": "https://www.edutopia.org", "type": "Resources"},
            {"name": "Coursera Teaching", "link": "https://www.coursera.org", "type": "Course"},
            {"name": "TES", "link": "https://www.tes.com", "type": "Resources"}
        ],
        "Nurse": [
            {"name": "Nurse.com", "link": "https://www.nurse.com", "type": "Course"},
            {"name": "MedlinePlus", "link": "https://medlineplus.gov", "type": "Reference"},
            {"name": "RegisteredNursing", "link": "https://www.registerednursing.org", "type": "Learning"},
            {"name": "Nursing Times", "link": "https://www.nursingtimes.net", "type": "Articles"},
            {"name": "Skillstat ECG", "link": "https://skillstat.com/tools/ecg-simulator", "type": "Practice"}
        ],
        "Pharmacist": [
            {"name": "Drugs.com", "link": "https://www.drugs.com", "type": "Reference"},
            {"name": "Pharmacy Times", "link": "https://www.pharmacytimes.com", "type": "Articles"},
            {"name": "RxPrep", "link": "https://rxprep.com", "type": "Course"},
            {"name": "FDA", "link": "https://www.fda.gov", "type": "Guidelines"},
            {"name": "Medscape Pharmacy", "link": "https://www.medscape.com/pharmacists", "type": "Learning"}
        ],
        "Business Analyst": [
            {"name": "IIBA", "link": "https://www.iiba.org", "type": "Documentation"},
            {"name": "Coursera Business Analysis", "link": "https://www.coursera.org", "type": "Course"},
            {"name": "Balsamiq Docs", "link": "https://balsamiq.com/docs", "type": "Documentation"},
            {"name": "Lucidchart", "link": "https://www.lucidchart.com/pages", "type": "Tool"}
        ],
        "Financial Analyst": [
            {"name": "CFA Institute", "link": "https://www.cfainstitute.org", "type": "Course"},
            {"name": "Investopedia", "link": "https://www.investopedia.com", "type": "Documentation"},
            {"name": "Excel Tutorials", "link": "https://support.microsoft.com/excel", "type": "Tool"}
        ],
        "Accountant": [
            {"name": "ACCA Global", "link": "https://www.accaglobal.com", "type": "Course"},
            {"name": "Tally Learning", "link": "https://tallysolutions.com", "type": "Tool"},
            {"name": "ICAI", "link": "https://www.icai.org", "type": "Documentation"}
        ],
        "HR Manager": [
            {"name": "SHRM", "link": "https://www.shrm.org", "type": "Course"},
            {"name": "LinkedIn Learning HR", "link": "https://www.linkedin.com/learning", "type": "Course"},
            {"name": "BambooHR Resources", "link": "https://www.bamboohr.com/resources", "type": "Documentation"}
        ],
        "Marketing Manager": [
            {"name": "HubSpot Academy", "link": "https://academy.hubspot.com", "type": "Course"},
            {"name": "Google Analytics", "link": "https://analytics.google.com", "type": "Tool"},
            {"name": "SEMrush Academy", "link": "https://www.semrush.com/academy", "type": "Course"}
        ],
        "Graphic Designer": [
            {"name": "Adobe Photoshop Tutorials", "link": "https://helpx.adobe.com/photoshop/tutorials.html", "type": "Course"},
            {"name": "Figma Learn", "link": "https://help.figma.com", "type": "Documentation"},
            {"name": "Canva Design School", "link": "https://www.canva.com/learn", "type": "Course"}
        ],
        "Video Editor": [
            {"name": "Premiere Pro Tutorials", "link": "https://helpx.adobe.com/premiere-pro/tutorials.html", "type": "Course"},
            {"name": "DaVinci Resolve Training", "link": "https://www.blackmagicdesign.com/products/davinciresolve/training", "type": "Course"},
            {"name": "YouTube Creator Academy", "link": "https://creatoracademy.youtube.com", "type": "Course"}
        ],
        "Content Writer": [
            {"name": "IIM Skills Writing Course", "link": "https://iimskills.com/content-writing-course/", "type": "Course"},
            {"name": "Grammarly", "link": "https://www.grammarly.com", "type": "Tool"},
            {"name": "WordPress Docs", "link": "https://wordpress.org/support", "type": "Documentation"}
        ],
        "Customer Support Executive": [
            {"name": "Zendesk Training", "link": "https://training.zendesk.com", "type": "Course"},
            {"name": "Freshdesk Academy", "link": "https://freshdesk.com/academy", "type": "Course"},
            {"name": "HubSpot Service Courses", "link": "https://academy.hubspot.com", "type": "Course"}
        ],
        "Data Entry Clerk": [
            {"name": "Excel Training", "link": "https://support.microsoft.com/excel", "type": "Course"},
            {"name": "Google Docs Learning", "link": "https://support.google.com/docs", "type": "Documentation"},
            {"name": "TypingClub", "link": "https://www.typingclub.com", "type": "Course"}
        ]
    }

    return resources.get(job, [])


# ----------------------------
# ROUTES
# ----------------------------
@app.route("/", methods=["GET"])
def login_page():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        session["user"] = email
        session.permanent = True
        return redirect(url_for("dashboard"))

    # BUG FIX: was returning bare text ("Invalid email or password"), which
    # threw away the page styling. Now re-renders the login page with an
    # inline error message instead.
    return render_template("login.html", error="Invalid email or password"), 401


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return render_template("register.html", error="Email and password are required"), 400

        if User.query.filter_by(email=email).first():
            # BUG FIX: was returning bare text here too.
            return render_template("register.html", error="An account with that email already exists"), 400

        hashed = generate_password_hash(password)
        db.session.add(User(email=email, password=hashed))
        db.session.commit()

        return redirect(url_for("login_page"))

    return render_template("register.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login_page"))

    result = None
    skills_gap = []
    roadmap = {}
    career = []
    income = []
    selected_job = None
    user_skills = ""
    chart_labels = []
    chart_values = []
    trends = []
    upskill = []
    resources = []
    readiness = 0
    impact_score = 0

    if request.method == "POST":
        selected_job = request.form.get("job")

        # BUG FIX: the hidden "skills" field is a single comma-separated
        # string (populated by the page's JS), not a list of separately
        # named checkbox fields. request.form.getlist("skills") returned a
        # one-item list containing the whole comma string, which broke the
        # skill-gap and readiness calculations further down. Split it here
        # instead.
        skills_raw = request.form.get("skills", "")
        selected_skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

        # custom typed skills
        other_skills = request.form.get("other_skills", "")
        typed_skills = [skill.strip() for skill in other_skills.split(",") if skill.strip()]

        # merge both
        all_user_skills = selected_skills + typed_skills
        user_skills = ", ".join(all_user_skills)

        job_data = data[data["job_title"].str.strip() == selected_job.strip()]

        if not job_data.empty:
            row = job_data.iloc[0]

            risk_percent = calculate_research_risk(row)
            level = get_risk_level(risk_percent)

            # skill gap (now uses the correctly split skill list)
            skills_gap = get_skill_gap(selected_job, all_user_skills)

            required_skills = job_skills.get(selected_job, [])
            required_skills_lower = [skill.lower().strip() for skill in required_skills]
            all_user_skills_lower = [skill.lower().strip() for skill in all_user_skills]

            matched_skills = len(
                set(all_user_skills_lower) & set(required_skills_lower)
            )

            base_score = (matched_skills / len(required_skills)) * 100 if required_skills else 0

            extra_skills = list(set(all_user_skills_lower) - set(required_skills_lower))
            bonus_score = len(extra_skills) * 5

            readiness = min(100, round(base_score + bonus_score))
            impact_score = round((readiness * 0.6) + ((100 - risk_percent) * 0.4))

            roadmap = job_roadmaps.get(selected_job, {})
            career = generate_career(selected_job)
            income = generate_income(selected_job)
            trends = generate_trends(selected_job)
            upskill = generate_upskill(selected_job)
            resources = generate_resources(selected_job)

            result = {
                "job": selected_job,
                "risk": risk_percent,
                "level": level,
                "readiness": readiness,
                "impact_score": impact_score
            }

            # BUG FIX: this used to re-read selected_job/user_skills from
            # request.form again right here, which silently dropped any
            # "other skills" the user had typed in (since the raw "skills"
            # field only ever holds the checkbox values). Save the history
            # entry using the already-correct merged values instead.
            history_entry = ReportHistory(
                user_email=session["user"],
                job=selected_job,
                risk=risk_percent,
                level=level,
                selected_skills=user_skills
            )
            db.session.add(history_entry)
            db.session.commit()

            session["report_data"] = {
                "job": selected_job,
                "risk": risk_percent,
                "level": level,
                "skills_gap": skills_gap,
                "roadmap": roadmap,
                "career": career,
                "income": income,
                "trends": trends,
                "upskill": upskill,
                "resources": resources,
                "readiness": readiness,
                "impact_score": impact_score
            }

            category = row["category"]
            similar_jobs = data[data["category"] == category]

            for _, r in similar_jobs.iterrows():
                chart_labels.append(r["job_title"])
                chart_values.append(calculate_research_risk(r))

    jobs = sorted(data["job_title"].unique())

    return render_template(
        "index.html",
        jobs=jobs,
        result=result,
        skills_gap=skills_gap,
        roadmap=roadmap,
        career=career,
        income=income,
        trends=trends,
        upskill=upskill,
        selected_job=selected_job,
        user_skills=user_skills,
        chart_labels=chart_labels,
        chart_values=chart_values,
        job_skills=job_skills,
        resources=resources,
        readiness=readiness,
        impact_score=impact_score
    )


@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login_page"))

    reports = ReportHistory.query.filter_by(
        user_email=session["user"]
    ).order_by(ReportHistory.created_at.desc()).all()

    return render_template("history.html", reports=reports)


@app.route("/download_report")
def download_report():
    if "user" not in session:
        return redirect(url_for("login_page"))

    if "report_data" not in session:
        return redirect(url_for("dashboard"))

    data_ = session["report_data"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AI Job Empowerment Report", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Job: {data_['job']}", styles["Normal"]))
    content.append(Paragraph(f"Automation Risk: {data_['risk']}%", styles["Normal"]))
    content.append(Paragraph(f"Risk Level: {data_['level']}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Skill Gap:", styles["Heading2"]))
    for s in data_["skills_gap"]:
        content.append(Paragraph(f"- {s}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Learning Roadmap:", styles["Heading2"]))
    roadmap_data = data_["roadmap"]
    for phase, steps in roadmap_data.items():
        content.append(Paragraph(f"<b>{phase.upper()}</b>", styles["Normal"]))
        for step in steps:
            content.append(Paragraph(f"- {step}", styles["Normal"]))
        content.append(Spacer(1, 6))

    content.append(Paragraph("Career Transitions:", styles["Heading2"]))
    for c in data_["career"]:
        content.append(Paragraph(f"- {c['title']}: {c['reason']}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Income Opportunities:", styles["Heading2"]))
    for i in data_["income"]:
        content.append(Paragraph(f"- {i['title']} : {i['desc']}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Job Market Trends:", styles["Heading2"]))
    for t in data_["trends"]:
        content.append(Paragraph(f"- {t}", styles["Normal"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Upskill Plan:", styles["Heading2"]))
    for u in data_["upskill"]:
        content.append(Paragraph(f"- {u}", styles["Normal"]))
    content.append(Spacer(1, 12))

    doc.build(content)
    buffer.seek(0)

    response = make_response(buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=career_report.pdf"

    return response


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"
    port = int(os.environ.get("PORT", 5033))
    app.run(debug=debug_mode, port=port)
