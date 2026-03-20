#!/usr/bin/env python3
"""
Smart E-Learn Platform Startup Script
This script initializes the database and starts the application.
"""

import os
import sys
from app import app, db

def initialize_database():
    """Initialize the database with tables"""
    print("Initializing database...")
    with app.app_context():
        db.create_all()
        print("Database tables created")

def seed_sample_data():
    """Seed the database with sample data"""
    print("Seeding sample data...")
    try:
        from seed_data import create_sample_data
        create_sample_data()
        print("Sample data created")
    except Exception as e:
        print(f"Warning: Could not seed sample data: {e}")

def check_requirements():
    """Check if all required packages are installed"""
    print("Checking requirements...")
    try:
        import flask
        import flask_sqlalchemy
        import flask_login
        import flask_cors
        print("All required packages are installed")
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main startup function"""
    print("Starting Smart E-Learn Platform...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Initialize database
    initialize_database()
    
    # Seed sample data
    seed_sample_data()
    
    print("\n" + "=" * 50)
    print("Smart E-Learn Platform is ready!")
    print("\nDefault Accounts:")
    print("   Superadmin: username=superadmin, password=superadmin123")
    print("   Admin:     username=admin,     password=admin123")
    print("   Instructor: username=instructor1, password=instructor123")
    print("   Student:   username=student1,   password=student123")
    print("\nAccess the platform at: http://localhost:5000")
    print("=" * 50)
    
    # Start the application
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nShutting down Smart E-Learn Platform...")
        sys.exit(0)

if __name__ == '__main__':
    main()
