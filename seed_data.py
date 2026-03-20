#!/usr/bin/env python3
"""
Sample data seeder for Smart E-Learn Platform
This script populates the database with initial courses, lessons, and quizzes.
"""

from app import app, db, User, Course, Lesson, Quiz, Question, QuestionOption
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_sample_data():
    with app.app_context():
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
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

        # Create instructor
        instructor = User.query.filter_by(username='instructor1').first()
        if not instructor:
            instructor = User(
                username='instructor1',
                email='instructor@smartelearn.com',
                password_hash=generate_password_hash('instructor123'),
                first_name='John',
                last_name='Doe',
                role='instructor'
            )
            db.session.add(instructor)
            db.session.commit()

        # Create sample student
        student = User.query.filter_by(username='student1').first()
        if not student:
            student = User(
                username='student1',
                email='student@smartelearn.com',
                password_hash=generate_password_hash('student123'),
                first_name='Jane',
                last_name='Smith',
                role='student'
            )
            db.session.add(student)
            db.session.commit()

        # Create superadmin user
        superadmin = User.query.filter_by(username='superadmin').first()
        if not superadmin:
            superadmin = User(
                username='superadmin',
                email='superadmin@smartelearn.com',
                password_hash=generate_password_hash('superadmin123'),
                first_name='Super',
                last_name='Admin',
                role='superadmin'
            )
            db.session.add(superadmin)
            db.session.commit()

        # Create sample courses
        courses_data = [
            {
                'title': 'Complete Python Programming Course',
                'description': 'Learn Python from scratch with hands-on projects and real-world applications. Perfect for beginners and intermediate learners.',
                'category': 'Programming',
                'difficulty_level': 'beginner',
                'duration_hours': 20,
                'price': 99.99,
                'thumbnail_url': '/static/images/courses/python-course.png'
            },
            {
                'title': 'Web Development with HTML, CSS & JavaScript',
                'description': 'Master the fundamentals of web development and build responsive, interactive websites.',
                'category': 'Web Development',
                'difficulty_level': 'beginner',
                'duration_hours': 15,
                'price': 79.99,
                'thumbnail_url': '/static/images/courses/web-course.jpg'
            },
            {
                'title': 'Data Structures and Algorithms',
                'description': 'Learn essential data structures and algorithms to ace technical interviews and build efficient software.',
                'category': 'Computer Science',
                'difficulty_level': 'intermediate',
                'duration_hours': 25,
                'price': 149.99,
                'thumbnail_url': '/static/images/courses/data-course.jpg'
            },
            {
                'title': 'Machine Learning Fundamentals',
                'description': 'Introduction to machine learning concepts, algorithms, and practical applications using Python.',
                'category': 'Data Science',
                'difficulty_level': 'intermediate',
                'duration_hours': 30,
                'price': 199.99,
                'thumbnail_url': '/static/images/courses/algo-course.jpg'
            },
            {
                'title': 'Java Programming Masterclass',
                'description': 'Complete Java programming course covering OOP, collections, multithreading, and advanced concepts.',
                'category': 'Programming',
                'difficulty_level': 'intermediate',
                'duration_hours': 35,
                'price': 129.99,
                'thumbnail_url': '/static/images/courses/java-course.jpg'
            },
            {
                'title': 'React.js Development Bootcamp',
                'description': 'Build modern web applications with React.js, including hooks, state management, and deployment.',
                'category': 'Web Development',
                'difficulty_level': 'intermediate',
                'duration_hours': 18,
                'price': 89.99,
                'thumbnail_url': '/static/images/courses/javascript-course.jpg'
            }
        ]

        for course_data in courses_data:
            course = Course.query.filter_by(title=course_data['title']).first()
            if not course:
                course = Course(
                    title=course_data['title'],
                    description=course_data['description'],
                    instructor_id=instructor.id,
                    category=course_data['category'],
                    difficulty_level=course_data['difficulty_level'],
                    duration_hours=course_data['duration_hours'],
                    price=course_data['price'],
                    thumbnail_url=course_data['thumbnail_url'],
                    is_published=True
                )
                db.session.add(course)
                db.session.commit()

                # Create lessons for each course
                create_lessons_for_course(course)
                create_quiz_for_course(course)

def create_lessons_for_course(course):
    """Create sample lessons for a course"""
    lesson_templates = {
        'Complete Python Programming Course': [
            {'title': 'Introduction to Python', 'content': 'Learn the basics of Python programming language.', 'duration': 45},
            {'title': 'Variables and Data Types', 'content': 'Understanding Python variables and different data types.', 'duration': 60},
            {'title': 'Control Structures', 'content': 'Learn about if-else statements, loops, and control flow.', 'duration': 75},
            {'title': 'Functions and Modules', 'content': 'Creating and using functions, importing modules.', 'duration': 90},
            {'title': 'Object-Oriented Programming', 'content': 'Classes, objects, inheritance, and polymorphism in Python.', 'duration': 120},
            {'title': 'File Handling', 'content': 'Reading from and writing to files in Python.', 'duration': 60},
            {'title': 'Error Handling', 'content': 'Try-except blocks and exception handling.', 'duration': 45},
            {'title': 'Final Project', 'content': 'Build a complete Python application.', 'duration': 180}
        ],
        'Web Development with HTML, CSS & JavaScript': [
            {'title': 'HTML Fundamentals', 'content': 'Learn HTML structure, tags, and semantic markup.', 'duration': 60},
            {'title': 'CSS Styling', 'content': 'CSS selectors, properties, and responsive design.', 'duration': 90},
            {'title': 'JavaScript Basics', 'content': 'Variables, functions, and DOM manipulation.', 'duration': 75},
            {'title': 'Advanced JavaScript', 'content': 'ES6 features, async programming, and APIs.', 'duration': 120},
            {'title': 'Responsive Design', 'content': 'Mobile-first design and CSS frameworks.', 'duration': 90},
            {'title': 'Project: Personal Website', 'content': 'Build a complete personal website.', 'duration': 180}
        ],
        'Data Structures and Algorithms': [
            {'title': 'Introduction to Algorithms', 'content': 'Algorithm analysis and complexity theory.', 'duration': 60},
            {'title': 'Arrays and Linked Lists', 'content': 'Linear data structures and their operations.', 'duration': 90},
            {'title': 'Stacks and Queues', 'content': 'LIFO and FIFO data structures.', 'duration': 75},
            {'title': 'Trees and Binary Trees', 'content': 'Tree traversal and binary search trees.', 'duration': 120},
            {'title': 'Graphs', 'content': 'Graph representation and traversal algorithms.', 'duration': 90},
            {'title': 'Sorting Algorithms', 'content': 'Bubble sort, merge sort, quick sort, and heap sort.', 'duration': 105},
            {'title': 'Searching Algorithms', 'content': 'Linear search, binary search, and hash tables.', 'duration': 75},
            {'title': 'Dynamic Programming', 'content': 'Memoization and optimal substructure.', 'duration': 120}
        ]
    }

    lessons = lesson_templates.get(course.title, [
        {'title': f'Lesson {i+1}', 'content': f'Content for lesson {i+1}', 'duration': 60}
        for i in range(5)
    ])

    for i, lesson_data in enumerate(lessons):
        lesson = Lesson(
            course_id=course.id,
            title=lesson_data['title'],
            content=lesson_data['content'],
            duration_minutes=lesson_data['duration'],
            order_index=i + 1,
            is_published=True
        )
        db.session.add(lesson)

def create_quiz_for_course(course):
    """Create a sample quiz for a course"""
    quiz = Quiz(
        course_id=course.id,
        title=f'{course.title} - Final Quiz',
        description=f'Test your knowledge of {course.title}',
        time_limit_minutes=30,
        max_attempts=3,
        passing_score=70,
        is_published=True
    )
    db.session.add(quiz)
    db.session.flush()  

    questions_data = [
        {
            'question_text': f'What is the main topic covered in {course.title}?',
            'question_type': 'multiple_choice',
            'points': 10,
            'options': [
                {'text': 'Option A', 'is_correct': True},
                {'text': 'Option B', 'is_correct': False},
                {'text': 'Option C', 'is_correct': False},
                {'text': 'Option D', 'is_correct': False}
            ]
        },
        {
            'question_text': f'Is {course.title} suitable for beginners?',
            'question_type': 'true_false',
            'points': 5,
            'options': [
                {'text': 'True', 'is_correct': course.difficulty_level == 'beginner'},
                {'text': 'False', 'is_correct': course.difficulty_level != 'beginner'}
            ]
        },
        {
            'question_text': f'Explain the key concepts learned in {course.title}.',
            'question_type': 'text',
            'points': 15,
            'options': []
        }
    ]

    for i, question_data in enumerate(questions_data):
        question = Question(
            quiz_id=quiz.id,
            question_text=question_data['question_text'],
            question_type=question_data['question_type'],
            points=question_data['points'],
            order_index=i + 1
        )
        db.session.add(question)
        db.session.flush()  # Get the question ID

        # Create options for the question
        for j, option_data in enumerate(question_data['options']):
            option = QuestionOption(
                question_id=question.id,
                option_text=option_data['text'],
                is_correct=option_data['is_correct'],
                order_index=j + 1
            )
            db.session.add(option)

if __name__ == '__main__':
    print("Creating sample data...")
    create_sample_data()
    print("Sample data created successfully!")
    print("\nSample accounts created:")
    print("Superadmin: username=superadmin, password=superadmin123")
    print("Admin: username=admin, password=admin123")
    print("Instructor: username=instructor1, password=instructor123")
    print("Student: username=student1, password=student123")
