from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from urllib.parse import quote_plus
from sqlalchemy import text
from werkzeug.utils import secure_filename
from flask import send_from_directory, abort
import datetime
import os

from models import db, User, Job, Application

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret123'

# MYSQL DATABASE CONNECTION (use env vars or fallback)
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', 'keerthana2004')
db_host = os.environ.get('DB_HOST', 'localhost')
db_name = os.environ.get('DB_NAME', 'jobboard_db')

# Quote the password to safely include special characters like '@'
db_pass_enc = quote_plus(db_pass)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+mysqlconnector://{db_user}:{db_pass_enc}@{db_host}/{db_name}'
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif'}

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore[attr-defined]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    jobs = Job.query.all()
    return render_template('index.html', jobs=jobs)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Allow users to register as 'student', 'recruiter', or 'admin'
        role = request.form.get('role', 'student')
        if role not in ('student', 'recruiter', 'admin'):
            role = 'student'

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role
        )

        db.session.add(user)
        db.session.commit()

        # If admin created, auto-login and send to admin dashboard
        if role == 'admin':
            login_user(user)
            flash('Administrator account created')
            return redirect(url_for('admin_dashboard'))

        flash('Registration successful')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # Redirect admins to admin dashboard
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    # Render role-specific dashboard
    if current_user.role == 'recruiter':
        # recruiter sees their posted jobs and quick links
        recruiter_jobs = Job.query.filter_by(owner_id=current_user.id).all()
        return render_template('recruiter_dashboard.html', jobs=recruiter_jobs)

    # student dashboard shows user info and applications
    user_applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', applications=user_applications)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Only students can edit profile here
    if current_user.role != 'student':
        flash('Only students can edit a profile here')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        phone = request.form.get('phone')
        bio = request.form.get('bio')
        current_user.phone = phone
        current_user.bio = bio

        # handle resume upload
        file = request.files.get('resume')
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext in {'pdf', 'doc', 'docx'}:
                unique = f"{current_user.id}_{int(datetime.datetime.utcnow().timestamp())}_{filename}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                file.save(dest)
                current_user.resume_filename = unique
            else:
                flash('Resume must be PDF or DOC/DOCX')

        # handle profile photo upload
        photo = request.files.get('photo')
        if photo and photo.filename:
            pfilename = secure_filename(photo.filename)
            pext = pfilename.rsplit('.', 1)[-1].lower()
            if pext in {'png', 'jpg', 'jpeg', 'gif'}:
                uniquep = f"photo_{current_user.id}_{int(datetime.datetime.utcnow().timestamp())}_{pfilename}"
                pdest = os.path.join(app.config['UPLOAD_FOLDER'], uniquep)
                photo.save(pdest)
                current_user.photo_filename = uniquep
            else:
                flash('Photo must be an image file (png/jpg/jpeg/gif)')

        db.session.commit()
        flash('Profile updated')
        return redirect(url_for('profile'))

    return render_template('profile.html')


@app.route('/jobs')
@login_required
def jobs():
    category = request.args.get('category')
    if category:
        all_jobs = Job.query.filter_by(category=category).all()
    else:
        all_jobs = Job.query.all()
    return render_template('jobs.html', jobs=all_jobs, selected_category=category)


@app.route('/jobs/categories')
@login_required
def job_categories():
    # list distinct categories
    cats = [r[0] for r in db.session.query(Job.category).distinct().filter(Job.category != None).all()]
    return render_template('categories.html', categories=cats)


@app.route('/apply/<int:job_id>')
@login_required
def apply(job_id):
    existing = Application.query.filter_by(
        user_id=current_user.id,
        job_id=job_id
    ).first()

    if existing:
        flash('Already applied')
        return redirect(url_for('jobs'))

    application = Application(
        user_id=current_user.id,
        job_id=job_id
    )

    db.session.add(application)
    db.session.commit()

    flash('Application submitted successfully')

    return redirect(url_for('applications'))


@app.route('/applications')
@login_required
def applications():
    user_applications = Application.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        'applications.html',
        applications=user_applications
    )


@app.route('/recruiter/job/<int:job_id>/applications')
@login_required
def view_job_applications(job_id):
    # recruiter-only: view applications for a job they own
    job = Job.query.get_or_404(job_id)
    if current_user.role != 'recruiter' or job.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))

    applications = Application.query.filter_by(job_id=job_id).all()
    return render_template('recruiter_applications.html', applications=applications, job=job)


@app.route('/application/<int:app_id>/update', methods=['POST'])
@login_required
def update_application(app_id):
    application = Application.query.get_or_404(app_id)
    job = Job.query.get(application.job_id)
    if current_user.role != 'recruiter' or job.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))

    status = request.form.get('status')
    interview_dt = request.form.get('interview_datetime')

    if status:
        application.status = status

    if interview_dt:
        try:
            # parse datetime-local string into python datetime via fromisoformat
            application.interview_datetime = __import__('datetime').datetime.fromisoformat(interview_dt)
            application.status = 'interview_scheduled'
        except Exception:
            flash('Invalid interview datetime format')

    db.session.commit()
    flash('Application updated')
    return redirect(url_for('view_job_applications', job_id=job.id))


@app.route('/recruiter/job/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    # recruiter-only: delete a job they own and its applications
    job = Job.query.get_or_404(job_id)
    if current_user.role != 'recruiter' or job.owner_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('dashboard'))

    # remove related applications first
    Application.query.filter_by(job_id=job.id).delete()
    db.session.delete(job)
    db.session.commit()

    flash('Job deleted')
    return redirect(url_for('dashboard'))


@app.route('/create-job', methods=['GET', 'POST'])
@login_required
def create_job():
    # Only allow recruiters to create jobs
    if current_user.role != 'recruiter':
        flash('Only recruiters can post jobs')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        description = request.form['description']
        location = request.form['location']
        salary = request.form['salary']
        category = request.form.get('category')

        job = Job(
            title=title,
            company=company,
            description=description,
            location=location,
            salary=salary
            , owner_id=current_user.id
            , category=category
        )

        db.session.add(job)
        db.session.commit()

        flash('Job created successfully')
        return redirect(url_for('jobs'))

    return render_template('create_job.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_recruiters = User.query.filter_by(role='recruiter').count()

    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_students=total_students,
                           total_recruiters=total_recruiters)


@app.route('/admin/users')
@login_required
def admin_view_users():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    role = request.args.get('role')
    if role:
        users = User.query.filter_by(role=role).all()
    else:
        users = User.query.all()

    return render_template('admin_users.html', users=users, filter_role=role)


@app.route('/admin/recruiters')
@login_required
def admin_recruiters():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    recruiters = User.query.filter_by(role='recruiter').all()
    return render_template('admin_recruiters.html', recruiters=recruiters)


@app.route('/admin/recruiter/add', methods=['GET', 'POST'])
@login_required
def admin_add_recruiter():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields required')
            return redirect(url_for('admin_add_recruiter'))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already in use')
            return redirect(url_for('admin_add_recruiter'))

        hashed = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed, role='recruiter')
        db.session.add(user)
        db.session.commit()
        flash('Recruiter added')
        return redirect(url_for('admin_recruiters'))

    return render_template('admin_add_recruiter.html')


@app.route('/admin/recruiter/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_recruiter(user_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username') or user.username
        user.email = request.form.get('email') or user.email
        db.session.commit()
        flash('Recruiter updated')
        return redirect(url_for('admin_recruiters'))

    return render_template('admin_edit_recruiter.html', user=user)


@app.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    from models import Company
    companies = Company.query.all()
    return render_template('admin_companies.html', companies=companies)


@app.route('/admin/company/add', methods=['GET', 'POST'])
@login_required
def admin_add_company():
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    from models import Company
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Name required')
            return redirect(url_for('admin_add_company'))

        c = Company(name=name)
        db.session.add(c)
        db.session.commit()
        flash('Company added')
        return redirect(url_for('admin_companies'))

    return render_template('admin_add_company.html')


@app.route('/admin/company/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    from models import Company
    c = Company.query.get_or_404(company_id)
    if request.method == 'POST':
        c.name = request.form.get('name') or c.name
        db.session.commit()
        flash('Company updated')
        return redirect(url_for('admin_companies'))

    return render_template('admin_edit_company.html', company=c)


@app.route('/admin/company/<int:company_id>/delete', methods=['POST'])
@login_required
def admin_delete_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))

    from models import Company
    c = Company.query.get_or_404(company_id)
    db.session.delete(c)
    db.session.commit()
    flash('Company deleted')
    return redirect(url_for('admin_companies'))


with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        msg = str(e).lower()
        # Ignore 'table already exists' errors which can happen if the DB
        # already contains the table (e.g., Company created earlier).
        if 'already exists' in msg or '1050' in msg:
            pass
        else:
            raise
    # Ensure new columns exist in older databases (non-migration environments)
    conn = db.engine.connect()
    try:
        # Add owner_id to job if missing
        try:
            conn.execute(text('ALTER TABLE job ADD COLUMN owner_id INT NULL'))
        except Exception:
            pass

        # Add category to job if missing
        try:
            conn.execute(text("ALTER TABLE job ADD COLUMN category VARCHAR(100) NULL"))
        except Exception:
            pass

        # Add status and interview_datetime to application if missing
        try:
            conn.execute(text("ALTER TABLE application ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))
        except Exception:
            pass

        try:
            conn.execute(text('ALTER TABLE application ADD COLUMN interview_datetime DATETIME NULL'))
        except Exception:
            pass
        # Add profile columns to user if missing
        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN phone VARCHAR(50) NULL"))
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN bio TEXT NULL"))
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN resume_filename VARCHAR(255) NULL"))
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE user ADD COLUMN photo_filename VARCHAR(255) NULL"))
        except Exception:
            pass
    finally:
        conn.close()


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve uploaded files from UPLOAD_FOLDER. Keep simple public access.
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception:
        abort(404)


if __name__ == '__main__':
    app.run(debug=True)
