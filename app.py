from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import os
from werkzeug.utils import secure_filename
import uuid
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Additional decorators for role-based access
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check role after login_required ensures user is authenticated
        if current_user.role not in ['admin', 'superadmin']:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check role after login_required ensures user is authenticated
        if current_user.role != 'superadmin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Superadmin access required'}), 403
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_change(entity_type, entity_id, action, old_values=None, new_values=None):
    """Log a change to the database"""
    try:
        change_log = ChangeLog(
            changed_by_id=current_user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(change_log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging change: {e}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
# Ensure instance directory exists
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)
# Use proper path formatting for SQLite (Windows paths need special handling)
db_path = os.path.join(instance_path, 'smart_elearn.db').replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Get the base directory of the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'static', 'uploads'))
# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['VIDEO_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
# Ensure video upload folder exists
os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 500 * 1024 * 1024))  # 500MB max file size for videos
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}

# OAuth2 Configuration
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')
app.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID', '')
app.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET', '')

# AWS S3 Configuration
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', '')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '')
app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')
app.config['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME', '')

# OpenAI Configuration
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize storage manager
from utils.storage import StorageManager
storage_manager = StorageManager(app)

def allowed_video_file(filename):
    """Check if the uploaded file has an allowed video extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

def save_video_file(file, course_id, lesson_id=None):
    """Save uploaded video file to local storage"""
    if file and allowed_video_file(file.filename):
        # Ensure base video directory exists
        os.makedirs(app.config['VIDEO_UPLOAD_FOLDER'], exist_ok=True)
        
        # Create course-specific directory
        course_video_dir = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], str(course_id))
        os.makedirs(course_video_dir, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        # Add unique identifier to avoid conflicts
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Save file
        filepath = os.path.join(course_video_dir, unique_filename)
        file.save(filepath)
        
        # Verify file was saved
        if not os.path.exists(filepath):
            raise Exception(f"Failed to save video file to {filepath}")
        
        # Return path relative to static folder (without 'static/' prefix for url_for)
        # Store as 'uploads/videos/course_id/filename' for url_for('static', filename='...')
        relative_path = os.path.join('uploads', 'videos', str(course_id), unique_filename).replace('\\', '/')
        return relative_path
    return None

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, instructor, admin, superadmin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='user', lazy=True)
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)
    progress = db.relationship('UserProgress', backref='user', lazy=True)
    messages = db.relationship('Message', backref='user', lazy=True)
    changes_made = db.relationship('ChangeLog', backref='user', lazy=True, foreign_keys='ChangeLog.changed_by_id')

class ChangeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # course, user, quiz, etc.
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False)  # create, update, delete
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    difficulty_level = db.Column(db.String(20), default='beginner')
    duration_hours = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    thumbnail_url = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instructor = db.relationship('User', backref='courses_taught', foreign_keys=[instructor_id])
    lessons = db.relationship('Lesson', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)
    quizzes = db.relationship('Quiz', backref='course', lazy=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    video_url = db.Column(db.String(500))
    duration_minutes = db.Column(db.Integer, default=0)
    order_index = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    progress = db.relationship('UserProgress', backref='lesson', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    time_limit_minutes = db.Column(db.Integer, default=30)
    max_attempts = db.Column(db.Integer, default=3)
    passing_score = db.Column(db.Integer, default=70)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True)
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='multiple_choice')  # multiple_choice, true_false, text
    points = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, default=0)
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy=True, cascade='all, delete-orphan')

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    progress_percentage = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    score = db.Column(db.Float)
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)
    time_taken_minutes = db.Column(db.Integer)
    
    # Relationships
    answers = db.relationship('QuizAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')

class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_option.id'))
    text_answer = db.Column(db.Text)
    is_correct = db.Column(db.Boolean)
    points_earned = db.Column(db.Float, default=0.0)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_spent_minutes = db.Column(db.Integer, default=0)
    progress_percentage = db.Column(db.Float, default=0.0)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='general')  # general, support, feedback
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.Text)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(20), default='info')  # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    courses = Course.query.filter_by(is_published=True).limit(6).all()
    stats = {
        'total_courses': Course.query.filter_by(is_published=True).count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_instructors': User.query.filter_by(role='instructor').count(),
        'total_enrollments': Enrollment.query.count()
    }
    
    # Get recommendations for logged-in users
    recommended_courses = []
    if current_user.is_authenticated:
        try:
            from utils.recommendations import recommendation_engine
            rec_ids = recommendation_engine.get_recommendations(current_user.id, n_recommendations=3)
            recommended_courses = Course.query.filter(Course.id.in_(rec_ids)).all()
        except Exception as e:
            print(f"Error getting recommendations: {e}")
    
    return render_template('index.html', 
                         courses=courses, 
                         stats=stats,
                         recommended_courses=recommended_courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            else:
                return jsonify({'success': False, 'message': 'Account is deactivated'})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    return render_template('login.html')

# OAuth2 Routes
@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    if not app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google OAuth is not configured', 'error')
        return redirect(url_for('login'))
    
    google = app.config.get('OAUTH_GOOGLE')
    if not google:
        from utils.oauth import init_oauth
        init_oauth(app)
        google = app.config.get('OAUTH_GOOGLE')
    
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        google = app.config.get('OAUTH_GOOGLE')
        token = google.authorize_access_token()
        user_info = google.get('userinfo', token=token).json()
        
        # Check if user exists
        user = User.query.filter_by(email=user_info.get('email')).first()
        
        if not user:
            # Create new user
            username = user_info.get('email', '').split('@')[0]
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=user_info.get('email'),
                password_hash=generate_password_hash(uuid.uuid4().hex),  # Random password
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
                role='student'
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error during Google login: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/github')
def github_login():
    """Initiate GitHub OAuth login"""
    if not app.config.get('GITHUB_CLIENT_ID'):
        flash('GitHub OAuth is not configured', 'error')
        return redirect(url_for('login'))
    
    github = app.config.get('OAUTH_GITHUB')
    if not github:
        from utils.oauth import init_oauth
        init_oauth(app)
        github = app.config.get('OAUTH_GITHUB')
    
    redirect_uri = url_for('github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/auth/github/callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        github = app.config.get('OAUTH_GITHUB')
        token = github.authorize_access_token()
        resp = github.get('user', token=token)
        user_info = resp.json()
        
        # Get email from GitHub (may require additional API call)
        email = user_info.get('email', '')
        if not email:
            # Try to get email from GitHub API
            email_resp = github.get('user/emails', token=token)
            emails = email_resp.json()
            if emails:
                email = emails[0].get('email', '')
        
        if not email:
            flash('Could not retrieve email from GitHub', 'error')
            return redirect(url_for('login'))
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            username = user_info.get('login', email.split('@')[0])
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            name = user_info.get('name', '').split()
            first_name = name[0] if name else ''
            last_name = ' '.join(name[1:]) if len(name) > 1 else ''
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(uuid.uuid4().hex),  # Random password
                first_name=first_name,
                last_name=last_name,
                role='student'
            )
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error during GitHub login: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username already exists'})
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'message': 'Email already exists'})
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data.get('role', 'student')
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'student':
        enrollments = Enrollment.query.filter_by(user_id=current_user.id, is_active=True).all()
        recent_progress = UserProgress.query.filter_by(user_id=current_user.id).order_by(UserProgress.completed_at.desc()).limit(5).all()
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
        
        return render_template('student_dashboard.html', 
                             enrollments=enrollments, 
                             recent_progress=recent_progress,
                             notifications=notifications)
    
    elif current_user.role == 'instructor':
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        return render_template('instructor_dashboard.html', courses=courses)
    
    elif current_user.role in ['admin', 'superadmin']:
        # Calculate user distribution by role
        total_students = User.query.filter_by(role='student').count()
        total_instructors = User.query.filter_by(role='instructor').count()
        total_admins = User.query.filter_by(role='admin').count()
        total_superadmins = User.query.filter_by(role='superadmin').count()
        
        # Calculate course categories distribution
        categories_data = db.session.query(Course.category, db.func.count(Course.id)).group_by(Course.category).all()
        categories = [cat[0] for cat in categories_data]
        category_counts = [cat[1] for cat in categories_data]
        
        stats = {
            'total_users': User.query.count(),
            'total_courses': Course.query.count(),
            'total_enrollments': Enrollment.query.count(),
            'recent_users': User.query.order_by(User.created_at.desc()).limit(5).all(),
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_admins': total_admins + total_superadmins,
            'categories': categories,
            'category_counts': category_counts
        }
        return render_template('admin_dashboard.html', stats=stats)

@app.route('/courses')
def courses():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = Course.query.filter_by(is_published=True)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Course.title.contains(search) | Course.description.contains(search))
    
    courses = query.paginate(page=page, per_page=9, error_out=False)
    
    categories = db.session.query(Course.category).distinct().all()
    categories = [cat[0] for cat in categories]
    
    return render_template('courses.html', courses=courses, categories=categories)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    lessons = Lesson.query.filter_by(course_id=course_id, is_published=True).order_by(Lesson.order_index).all()
    quizzes = Quiz.query.filter_by(course_id=course_id, is_published=True).all()
    
    # Check if user is enrolled
    is_enrolled = False
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id, is_active=True).first()
        is_enrolled = enrollment is not None
    
    return render_template('course_detail.html', 
                         course=course, 
                         lessons=lessons, 
                         quizzes=quizzes,
                         is_enrolled=is_enrolled)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id, is_active=True).first()
    if existing_enrollment:
        return jsonify({'success': False, 'message': 'Already enrolled in this course'})
    
    # Create enrollment
    enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()
    
    # Create notification
    notification = Notification(
        user_id=current_user.id,
        title='Course Enrollment',
        message=f'You have successfully enrolled in {course.title}',
        notification_type='success'
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Successfully enrolled in course'})

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    
    # Check if user is enrolled
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id, is_active=True).first()
    if not enrollment:
        flash('You must be enrolled in this course to access lessons', 'error')
        return redirect(url_for('course_detail', course_id=course.id))
    
    # Get all lessons in the course
    all_lessons = Lesson.query.filter_by(course_id=course.id, is_published=True).order_by(Lesson.order_index).all()
    
    # Get user progress for this lesson
    progress = UserProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    
    return render_template('lesson_detail.html', 
                         lesson=lesson, 
                         course=course, 
                         all_lessons=all_lessons,
                         progress=progress)

@app.route('/quiz/<int:quiz_id>')
@login_required
def quiz_detail(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    course = quiz.course
    
    # Check if user is enrolled
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id, is_active=True).first()
    if not enrollment:
        flash('You must be enrolled in this course to access quizzes', 'error')
        return redirect(url_for('course_detail', course_id=course.id))
    
    # Get questions with options
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_index).all()
    for question in questions:
        question.options = QuestionOption.query.filter_by(question_id=question.id).order_by(QuestionOption.order_index).all()
    
    # Check existing attempts
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).order_by(QuizAttempt.started_at.desc()).all()
    
    return render_template('quiz_detail.html', 
                         quiz=quiz, 
                         course=course, 
                         questions=questions,
                         attempts=attempts)

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    
    # Create quiz attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        completed_at=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.flush()  # Get the attempt ID
    
    total_questions = len(data.get('answers', []))
    correct_answers = 0
    total_points = 0
    earned_points = 0
    
    # Process answers
    for answer_data in data.get('answers', []):
        question = Question.query.get(answer_data['question_id'])
        if not question:
            continue
        
        total_points += question.points
        
        # Create quiz answer record
        quiz_answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            text_answer=answer_data.get('text_answer', '')
        )
        
        if question.question_type == 'multiple_choice':
            selected_option = QuestionOption.query.get(answer_data.get('selected_option_id'))
            if selected_option:
                quiz_answer.selected_option_id = selected_option.id
                quiz_answer.is_correct = selected_option.is_correct
                if selected_option.is_correct:
                    correct_answers += 1
                    earned_points += question.points
                    quiz_answer.points_earned = question.points
        
        elif question.question_type == 'true_false':
            # Handle true/false questions
            pass
        
        elif question.question_type == 'text':
            # Handle text questions (would need manual grading)
            pass
        
        db.session.add(quiz_answer)
    
    # Calculate score
    score = (earned_points / total_points * 100) if total_points > 0 else 0
    
    # Update attempt
    attempt.score = score
    attempt.total_questions = total_questions
    attempt.correct_answers = correct_answers
    attempt.time_taken_minutes = data.get('time_taken', 0)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'score': score,
        'passed': score >= quiz.passing_score,
        'correct_answers': correct_answers,
        'total_questions': total_questions
    })

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    
    current_user.first_name = data.get('first_name', current_user.first_name)
    current_user.last_name = data.get('last_name', current_user.last_name)
    current_user.email = data.get('email', current_user.email)
    
    if data.get('password'):
        current_user.password_hash = generate_password_hash(data['password'])
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Profile updated successfully'})

@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not check_password_hash(current_user.password_hash, current_password):
        return jsonify({'success': False, 'message': 'Current password is incorrect'})
    
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password updated successfully'})

@app.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    data = request.get_json()
    # Store preferences in user model or separate preferences table
    # For now, just return success
    return jsonify({'success': True, 'message': 'Preferences updated successfully'})

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # In a real application, you would implement proper account deletion
    # For now, just return success
    return jsonify({'success': True, 'message': 'Account deletion requested'})

# Admin Routes for Course Management
@app.route('/admin/courses')
@admin_required
def admin_courses():
    courses = Course.query.all()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/courses/create', methods=['GET', 'POST'])
@login_required
def admin_create_course():
    # Check if user has admin or instructor role
    if current_user.role not in ['admin', 'superadmin', 'instructor']:
        flash('You do not have permission to create courses', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            # Validate required fields
            required_fields = ['title', 'description', 'category', 'difficulty_level', 'duration_hours', 'price']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({'success': False, 'message': f'{field} is required'}), 400
            
            # Log the creation
            try:
                log_change('course', 0, 'create', None, data)
            except Exception as e:
                print(f"Error logging change: {e}")
            
            course = Course(
                title=data['title'],
                description=data['description'],
                instructor_id=current_user.id,
                category=data['category'],
                difficulty_level=data['difficulty_level'],
                duration_hours=int(data['duration_hours']),
                price=float(data['price']),
                thumbnail_url=data.get('thumbnail_url', ''),
                is_published=data.get('is_published', False)
            )
            
            db.session.add(course)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Course created successfully', 'course_id': course.id})
        except Exception as e:
            db.session.rollback()
            print(f"Error creating course: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Error creating course: {str(e)}'}), 500
    
    return render_template('admin/create_course.html')

@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        data = request.get_json()
        old_values = {
            'title': course.title,
            'description': course.description,
            'category': course.category,
            'difficulty_level': course.difficulty_level,
            'duration_hours': course.duration_hours,
            'price': course.price,
            'is_published': course.is_published
        }
        
        # Update course
        course.title = data['title']
        course.description = data['description']
        course.category = data['category']
        course.difficulty_level = data['difficulty_level']
        course.duration_hours = data['duration_hours']
        course.price = data['price']
        course.is_published = data.get('is_published', course.is_published)
        course.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log the change
        log_change('course', course_id, 'update', old_values, data)
        
        return jsonify({'success': True, 'message': 'Course updated successfully'})
    
    return render_template('admin/edit_course.html', course=course)

@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def admin_delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Log the deletion
    old_values = {
        'title': course.title,
        'description': course.description,
        'category': course.category,
        'price': course.price
    }
    log_change('course', course_id, 'delete', old_values, None)
    
    db.session.delete(course)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Course deleted successfully'})

# Lesson Management Routes
@app.route('/admin/courses/<int:course_id>/lessons')
@login_required
def admin_course_lessons(course_id):
    """View all lessons for a course"""
    course = Course.query.get_or_404(course_id)
    
    # Check if user has permission (admin, superadmin, or course instructor)
    if current_user.role not in ['admin', 'superadmin'] and course.instructor_id != current_user.id:
        flash('You do not have permission to manage lessons for this course', 'error')
        return redirect(url_for('dashboard'))
    
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order_index).all()
    return render_template('admin/lessons.html', course=course, lessons=lessons)

@app.route('/admin/courses/<int:course_id>/lessons/create', methods=['GET', 'POST'])
@login_required
def admin_create_lesson(course_id):
    """Create a new lesson with video upload"""
    course = Course.query.get_or_404(course_id)
    
    # Check if user has permission (admin, superadmin, or course instructor)
    if current_user.role not in ['admin', 'superadmin', 'instructor']:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You do not have permission to create lessons'}), 403
        flash('You do not have permission to create lessons', 'error')
        return redirect(url_for('dashboard'))
    
    if current_user.role not in ['admin', 'superadmin'] and course.instructor_id != current_user.id:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You do not have permission to create lessons for this course'}), 403
        flash('You do not have permission to create lessons for this course', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Handle form data with file upload
            title = request.form.get('title')
            if not title:
                return jsonify({'success': False, 'message': 'Lesson title is required'}), 400
            
            content = request.form.get('content', '')
            duration_minutes = int(request.form.get('duration_minutes', 0) or 0)
            order_index = int(request.form.get('order_index', 0) or 0)
            is_published = request.form.get('is_published') == 'on'
            
            # Handle video file upload
            video_file = request.files.get('video_file')
            video_url = None
            
            # Check if video file is required (if no video_url provided)
            video_url_input = request.form.get('video_url', '').strip()
            
            if video_file and video_file.filename:
                try:
                    video_path = save_video_file(video_file, course_id)
                    if video_path:
                        # Store path that can be used with url_for('static', filename=video_path)
                        video_url = video_path  # Store as 'uploads/videos/course_id/filename'
                    else:
                        return jsonify({'success': False, 'message': 'Invalid video file format. Supported formats: MP4, AVI, MOV, WMV, FLV, WebM, MKV'}), 400
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Error uploading video: {str(e)}'}), 500
            
            # If no video file but video_url is provided in form
            if not video_url and video_url_input:
                video_url = video_url_input
            
            # Validate that either video file or video URL is provided
            if not video_url:
                return jsonify({'success': False, 'message': 'Either a video file or video URL is required'}), 400
            
            # Create lesson
            lesson = Lesson(
                course_id=course_id,
                title=title,
                content=content,
                video_url=video_url,
                duration_minutes=duration_minutes,
                order_index=order_index,
                is_published=is_published
            )
            
            db.session.add(lesson)
            db.session.commit()
            
            # Log the creation
            try:
                log_change('lesson', lesson.id, 'create', None, {
                    'title': title,
                    'course_id': course_id
                })
            except Exception as log_error:
                print(f"Error logging change: {log_error}")
            
            # Always return JSON for POST requests (since we're using fetch)
            return jsonify({
                'success': True, 
                'message': 'Lesson created successfully', 
                'lesson_id': lesson.id
            })
                
        except ValueError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Invalid input: {str(e)}'}), 400
        except Exception as e:
            db.session.rollback()
            print(f"Error creating lesson: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Error creating lesson: {str(e)}'}), 500
    
    # Get next order index
    last_lesson = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order_index.desc()).first()
    next_order = (last_lesson.order_index + 1) if last_lesson else 1
    
    return render_template('admin/create_lesson.html', course=course, next_order=next_order)

@app.route('/admin/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_lesson(lesson_id):
    """Edit a lesson with video upload"""
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    
    # Check if user has permission (admin, superadmin, or course instructor)
    if current_user.role not in ['admin', 'superadmin', 'instructor']:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You do not have permission to edit lessons'}), 403
        flash('You do not have permission to edit lessons', 'error')
        return redirect(url_for('dashboard'))
    
    if current_user.role not in ['admin', 'superadmin'] and course.instructor_id != current_user.id:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You do not have permission to edit this lesson'}), 403
        flash('You do not have permission to edit this lesson', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            old_values = {
                'title': lesson.title,
                'content': lesson.content,
                'video_url': lesson.video_url,
                'duration_minutes': lesson.duration_minutes,
                'order_index': lesson.order_index,
                'is_published': lesson.is_published
            }
            
            # Handle form data
            title = request.form.get('title')
            if not title:
                return jsonify({'success': False, 'message': 'Lesson title is required'}), 400
            
            lesson.title = title
            lesson.content = request.form.get('content', '')
            lesson.duration_minutes = int(request.form.get('duration_minutes', 0) or 0)
            lesson.order_index = int(request.form.get('order_index', 0) or 0)
            lesson.is_published = request.form.get('is_published') == 'on'
            
            # Handle video file upload
            video_file = request.files.get('video_file')
            video_url_input = request.form.get('video_url', '').strip()
            
            if video_file and video_file.filename:
                try:
                    video_path = save_video_file(video_file, course.id, lesson.id)
                    if video_path:
                        # Delete old video file if exists
                        if lesson.video_url and ('uploads/videos' in lesson.video_url or 'static/uploads/videos' in lesson.video_url):
                            # Handle both old and new path formats
                            if lesson.video_url.startswith('/static/'):
                                old_video_path = lesson.video_url.replace('/static/', '')
                            elif lesson.video_url.startswith('static/'):
                                old_video_path = lesson.video_url.replace('static/', '')
                            else:
                                old_video_path = lesson.video_url
                            
                            old_file_path = os.path.join('static', old_video_path)
                            if os.path.exists(old_file_path):
                                try:
                                    os.remove(old_file_path)
                                except Exception as e:
                                    print(f"Error deleting old video: {e}")
                        lesson.video_url = video_path  # Store as 'uploads/videos/course_id/filename'
                    else:
                        return jsonify({'success': False, 'message': 'Invalid video file format. Supported formats: MP4, AVI, MOV, WMV, FLV, WebM, MKV'}), 400
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': f'Error uploading video: {str(e)}'}), 500
            # If video_url is provided in form and no new file is uploaded
            elif video_url_input:
                lesson.video_url = video_url_input
            
            db.session.commit()
            
            # Log the change
            try:
                new_values = {
                    'title': lesson.title,
                    'content': lesson.content,
                    'video_url': lesson.video_url,
                    'duration_minutes': lesson.duration_minutes,
                    'order_index': lesson.order_index,
                    'is_published': lesson.is_published
                }
                log_change('lesson', lesson_id, 'update', old_values, new_values)
            except Exception as log_error:
                print(f"Error logging change: {log_error}")
            
            # Always return JSON for POST requests (since we're using fetch)
            return jsonify({'success': True, 'message': 'Lesson updated successfully'})
                
        except ValueError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Invalid input: {str(e)}'}), 400
        except Exception as e:
            db.session.rollback()
            print(f"Error updating lesson: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'Error updating lesson: {str(e)}'}), 500
    
    return render_template('admin/edit_lesson.html', lesson=lesson, course=course)

@app.route('/admin/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
def admin_delete_lesson(lesson_id):
    """Delete a lesson"""
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.course
    course_id = course.id
    
    # Check if user has permission (admin, superadmin, or course instructor)
    if current_user.role not in ['admin', 'superadmin', 'instructor']:
        return jsonify({'success': False, 'message': 'You do not have permission to delete lessons'}), 403
    
    if current_user.role not in ['admin', 'superadmin'] and course.instructor_id != current_user.id:
        return jsonify({'success': False, 'message': 'You do not have permission to delete this lesson'}), 403
    
    # Log the deletion
    old_values = {
        'title': lesson.title,
        'course_id': course_id
    }
    log_change('lesson', lesson_id, 'delete', old_values, None)
    
    # Delete video file if exists
    if lesson.video_url and ('uploads/videos' in lesson.video_url or 'static/uploads/videos' in lesson.video_url):
        # Handle both old and new path formats
        if lesson.video_url.startswith('/static/'):
            video_path = lesson.video_url.replace('/static/', '')
        elif lesson.video_url.startswith('static/'):
            video_path = lesson.video_url.replace('static/', '')
        else:
            video_path = lesson.video_url
        
        file_path = os.path.join('static', video_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting video file: {e}")
    
    db.session.delete(lesson)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Lesson deleted successfully'})

# Superadmin Routes for User Management
@app.route('/superadmin/users')
@superadmin_required
def superadmin_users():
    users = User.query.all()
    return render_template('superadmin/users.html', users=users)

@app.route('/superadmin/users/create', methods=['GET', 'POST'])
@superadmin_required
def superadmin_create_user():
    if request.method == 'POST':
        data = request.get_json()
        
        # Log the creation
        log_change('user', 0, 'create', None, data)
        
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            is_active=data.get('is_active', True)
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User created successfully', 'user_id': user.id})
    
    return render_template('superadmin/create_user.html')

@app.route('/superadmin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@superadmin_required
def superadmin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        data = request.get_json()
        old_values = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active
        }
        
        # Update user
        user.username = data['username']
        user.email = data['email']
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.role = data['role']
        user.is_active = data.get('is_active', user.is_active)
        
        if data.get('password'):
            user.password_hash = generate_password_hash(data['password'])
        
        db.session.commit()
        
        # Log the change
        log_change('user', user_id, 'update', old_values, data)
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
    
    return render_template('superadmin/edit_user.html', user=user)

@app.route('/superadmin/users/<int:user_id>/delete', methods=['POST'])
@superadmin_required
def superadmin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting superadmin accounts
    if user.role == 'superadmin':
        return jsonify({'success': False, 'message': 'Cannot delete superadmin accounts'})
    
    # Log the deletion
    old_values = {
        'username': user.username,
        'email': user.email,
        'role': user.role
    }
    log_change('user', user_id, 'delete', old_values, None)
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

# Superadmin route for price management
@app.route('/superadmin/courses/<int:course_id>/update-price', methods=['POST'])
@superadmin_required
def superadmin_update_course_price(course_id):
    course = Course.query.get_or_404(course_id)
    data = request.get_json()
    new_price = data.get('price')
    
    if new_price is None:
        return jsonify({'success': False, 'message': 'Price is required'})
    
    old_price = course.price
    course.price = new_price
    course.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log the price change
    log_change('course', course_id, 'update', {'price': old_price}, {'price': new_price})
    
    return jsonify({'success': True, 'message': f'Course price updated from ${old_price} to ${new_price}'})

# Change tracking routes
@app.route('/admin/change-log')
@admin_required
def admin_change_log():
    changes = ChangeLog.query.order_by(ChangeLog.timestamp.desc()).limit(100).all()
    return render_template('admin/change_log.html', changes=changes)

@app.route('/superadmin/change-log')
@superadmin_required
def superadmin_change_log():
    changes = ChangeLog.query.order_by(ChangeLog.timestamp.desc()).limit(500).all()
    return render_template('superadmin/change_log.html', changes=changes)

# User Routes for Simple Interface
@app.route('/user-dashboard')
@login_required
def user_dashboard():
    """Simple user dashboard for students"""
    # Get user's enrolled courses
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_courses = [enrollment.course for enrollment in enrollments]
    
    # Calculate progress statistics
    completed_lessons = UserProgress.query.filter_by(
        user_id=current_user.id
    ).count()
    
    quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id).count()
    
    # Calculate average score
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    average_score = sum(attempt.score for attempt in attempts) / len(attempts) if attempts else 0
    
    # Get recent activities (simplified)
    recent_activities = [
        {
            'icon': 'book',
            'color': 'primary',
            'description': 'Enrolled in new course',
            'timestamp': '2 hours ago'
        },
        {
            'icon': 'check-circle',
            'color': 'success',
            'description': 'Completed lesson',
            'timestamp': '1 day ago'
        },
        {
            'icon': 'question-circle',
            'color': 'info',
            'description': 'Took quiz',
            'timestamp': '2 days ago'
        }
    ]
    
    return render_template('user_dashboard.html', 
                         enrolled_courses=enrolled_courses,
                         completed_lessons=completed_lessons,
                         quiz_attempts=quiz_attempts,
                         average_score=round(average_score, 1),
                         recent_activities=recent_activities)

@app.route('/user-courses')
@login_required
def user_courses():
    """Browse courses for users"""
    courses = Course.query.filter_by(is_published=True).all()
    
    # Get enrolled course IDs for current user
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]
    
    return render_template('user_courses.html', 
                         courses=courses,
                         enrolled_course_ids=enrolled_course_ids)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def user_enroll_course(course_id):
    """Enroll user in a course"""
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, 
        course_id=course_id
    ).first()
    
    if existing_enrollment:
        return jsonify({'success': False, 'message': 'Already enrolled in this course'})
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        enrolled_at=datetime.utcnow()
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    # Log the enrollment
    log_change('enrollment', enrollment.id, 'create', None, {
        'user_id': current_user.id,
        'course_id': course_id
    })
    
    return jsonify({'success': True, 'message': 'Successfully enrolled in course'})

@app.route('/my-quizzes')
@login_required
def my_quizzes():
    """Show available quizzes for user"""
    # Get quizzes from enrolled courses
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    
    quizzes = Quiz.query.filter(
        Quiz.course_id.in_(course_ids),
        Quiz.is_published == True
    ).all()
    
    return render_template('user_quizzes.html', quizzes=quizzes)

@app.route('/quiz/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    """Take a quiz"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Check if user is enrolled in the course
    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_id=quiz.course_id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in the course to take this quiz', 'error')
        return redirect(url_for('user_courses'))
    
    # Get quiz questions
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(Question.order_index).all()
    
    # Get current attempt number
    attempts = QuizAttempt.query.filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id
    ).count()
    current_attempt = attempts + 1
    
    # Check if max attempts reached
    if current_attempt > quiz.max_attempts:
        flash('You have reached the maximum number of attempts for this quiz', 'error')
        return redirect(url_for('my_quizzes'))
    
    return render_template('user_quiz.html', 
                         quiz=quiz, 
                         questions=questions,
                         current_attempt=current_attempt)

@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def user_submit_quiz(quiz_id):
    """Submit quiz answers"""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get user answers
    answers = {}
    for key, value in request.form.items():
        if key.startswith('question_'):
            question_id = int(key.split('_')[1])
            answers[question_id] = value
    
    # Calculate score (simplified)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    total_points = 0
    earned_points = 0
    correct_count = 0
    
    for question in questions:
        total_points += question.points
        
        if question.question_type in ['multiple_choice', 'true_false']:
            user_answer = answers.get(question.id)
            if user_answer:
                option = QuestionOption.query.filter_by(
                    question_id=question.id,
                    id=user_answer
                ).first()
                if option and option.is_correct:
                    earned_points += question.points
                    correct_count += 1
    
    score = (earned_points / total_points * 100) if total_points > 0 else 0
    
    # Create quiz attempt
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        completed_at=datetime.utcnow(),
        total_questions=len(questions),
        correct_answers=correct_count,
        time_taken_minutes=0
    )
    
    db.session.add(attempt)
    db.session.flush()  # Get the attempt ID
    
    # Create quiz answer records
    for question in questions:
        user_answer = answers.get(question.id)
        if user_answer:
            option = QuestionOption.query.filter_by(
                question_id=question.id,
                id=user_answer
            ).first()
            if option:
                quiz_answer = QuizAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_option_id=option.id,
                    is_correct=option.is_correct,
                    points_earned=question.points if option.is_correct else 0
                )
                db.session.add(quiz_answer)
    
    db.session.commit()
    
    # Log the quiz attempt
    log_change('quiz_attempt', attempt.id, 'create', None, {
        'user_id': current_user.id,
        'quiz_id': quiz_id,
        'score': score
    })
    
    # Show results
    passed = score >= quiz.passing_score
    flash(f'Quiz completed! Score: {score:.1f}% - {"Passed" if passed else "Failed"}', 
          'success' if passed else 'warning')
    
    return redirect(url_for('my_quizzes'))

# API Routes for AJAX calls
@app.route('/api/courses')
def api_courses():
    courses = Course.query.filter_by(is_published=True).all()
    return jsonify([{
        'id': course.id,
        'title': course.title,
        'description': course.description,
        'category': course.category,
        'difficulty_level': course.difficulty_level,
        'duration_hours': course.duration_hours,
        'price': course.price,
        'thumbnail_url': course.thumbnail_url,
        'instructor': course.instructor.first_name + ' ' + course.instructor.last_name if course.instructor else 'Instructor'
    } for course in courses])

@app.route('/api/ai-chat', methods=['POST'])
@login_required
def ai_chat():
    data = request.get_json()
    message = data.get('message', '')
    lesson_id = data.get('lesson_id')
    course_id = data.get('course_id')
    
    if not message:
        return jsonify({'answer': 'Please provide a message to chat with the AI assistant.'}), 400
    
    # Get lesson context if provided
    context = ""
    if lesson_id:
        lesson = Lesson.query.get(lesson_id)
        if lesson:
            context = lesson.content or ""
    
    # Get course context if provided
    if course_id:
        course = Course.query.get(course_id)
        if course:
            context += f"\nCourse: {course.title}\nDescription: {course.description}"
    
    # Try OpenAI API first if configured
    if app.config.get('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=app.config['OPENAI_API_KEY'])
            system_prompt = "You are a helpful AI tutor for an e-learning platform. Answer questions clearly and concisely."
            if context:
                system_prompt += f"\n\nContext: {context[:1000]}"
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            return jsonify({'answer': answer})
        except Exception as e:
            print(f"OpenAI API error: {e}")
            # Continue to fallback
    
    # Fallback to local AI model
    try:
        from model.flapp import get_answer, context as ai_context
        # Use provided context or default AI context
        final_context = context if context else ai_context
        
        # Check if context is empty or too short
        if not final_context or len(final_context.strip()) < 10:
            final_context = ai_context  # Use default context if lesson context is missing
        
        answer = get_answer(message, [], final_context)
        
        # Validate answer
        if not answer or len(answer.strip()) == 0:
            answer = "I'm not sure how to answer that. Could you rephrase your question or provide more context?"
        
        return jsonify({'answer': answer})
    except ImportError as e:
        error_msg = str(e)
        print(f"ImportError in AI chat: {error_msg}")
        import traceback
        traceback.print_exc()
        if 'sentencepiece' in error_msg.lower():
            return jsonify({
                'answer': (
                    'I apologize, but the AI model requires the SentencePiece library which is not installed. '
                    'Please contact the administrator to install it using: pip install sentencepiece. '
                    'Alternatively, you can configure OpenAI API key in the environment variables for a cloud-based AI assistant.'
                )
            }), 500
        return jsonify({
            'answer': f'I apologize, but there is a missing dependency for the AI model. Please contact the administrator. Error: {str(e)}'
        }), 500
    except Exception as e:
        error_str = str(e)
        print(f"Local AI model error: {error_str}")
        import traceback
        traceback.print_exc()
        # Provide a helpful error message based on error type
        if 'sentencepiece' in error_str.lower():
            return jsonify({
                'answer': (
                    'I apologize, but the AI model is not properly configured. '
                    'The SentencePiece library is required but not installed. '
                    'Please contact the administrator to install the required dependencies using: pip install sentencepiece'
                )
            }), 500
        elif 'Model directory not found' in error_str or 'Missing model files' in error_str:
            return jsonify({
                'answer': (
                    'I apologize, but the AI model files are missing or not properly configured. '
                    'Please contact the administrator to ensure the model files are in place. '
                    'Alternatively, you can configure an OpenAI API key in the environment variables for a cloud-based AI assistant.'
                )
            }), 500
        else:
            # Return the error message from get_answer if it's user-friendly
            # Otherwise provide a generic message
            return jsonify({
                'answer': (
                    'I apologize, but I encountered an error processing your question. '
                    'This might be due to model loading issues or configuration problems. '
                    'Please try again later or contact support. '
                    'If this issue persists, the administrator may need to check the server logs or configure an OpenAI API key.'
                )
            }), 500

@app.route('/api/complete-lesson', methods=['POST'])
@login_required
def complete_lesson():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    
    lesson = Lesson.query.get_or_404(lesson_id)
    
    # Check if user is enrolled in the course
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=lesson.course_id, is_active=True).first()
    if not enrollment:
        return jsonify({'success': False, 'message': 'Not enrolled in course'})
    
    # Check if already completed
    existing_progress = UserProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if existing_progress:
        return jsonify({'success': True, 'message': 'Already completed'})
    
    # Create progress record
    progress = UserProgress(
        user_id=current_user.id,
        lesson_id=lesson_id,
        progress_percentage=100.0,
        time_spent_minutes=lesson.duration_minutes
    )
    db.session.add(progress)
    
    # Update enrollment progress
    total_lessons = Lesson.query.filter_by(course_id=lesson.course_id, is_published=True).count()
    completed_lessons = UserProgress.query.filter_by(user_id=current_user.id).join(Lesson).filter(Lesson.course_id == lesson.course_id).count()
    enrollment.progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    # Check if course is completed
    if enrollment.progress_percentage >= 100:
        enrollment.completed_at = datetime.utcnow()
        
        # Create completion notification
        notification = Notification(
            user_id=current_user.id,
            title='Course Completed!',
            message=f'Congratulations! You have completed {lesson.course.title}',
            notification_type='success'
        )
        db.session.add(notification)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Lesson marked as complete'})

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify([])
    
    # Search courses
    courses = Course.query.filter(
        Course.is_published == True,
        (Course.title.contains(query) | Course.description.contains(query))
    ).limit(5).all()
    
    results = []
    for course in courses:
        results.append({
            'id': course.id,
            'title': course.title,
            'description': course.description[:100] + '...',
            'type': 'Course',
            'url': url_for('course_detail', course_id=course.id)
        })
    
    return jsonify(results)

@app.route('/api/user_progress')
@login_required
def api_user_progress():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id, is_active=True).all()
    progress_data = []
    
    for enrollment in enrollments:
        course = enrollment.course
        total_lessons = Lesson.query.filter_by(course_id=course.id, is_published=True).count()
        completed_lessons = UserProgress.query.filter_by(user_id=current_user.id).join(Lesson).filter(Lesson.course_id == course.id).count()
        
        progress_data.append({
            'course_id': course.id,
            'course_title': course.title,
            'progress_percentage': (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons
        })
    
    return jsonify(progress_data)

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    return jsonify([{
        'id': notif.id,
        'title': notif.title,
        'message': notif.message,
        'type': notif.notification_type,
        'created_at': notif.created_at.isoformat()
    } for notif in notifications])

@app.route('/api/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Unauthorized'})

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@smartelearn.com',
                password_hash=generate_password_hash('admin123'),
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
