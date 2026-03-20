# Smart E-Learn Platform - Deployment Guide

## 🐳 Docker Deployment

### Quick Start with Docker

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Run in background:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

### Manual Docker Build

```bash
# Build the image
docker build -t smart-elearn .

# Run the container
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance smart-elearn
```

## ☁️ Cloud Deployment

### Environment Configuration

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Configure your environment variables in `.env`:**

   **Required:**
   - `SECRET_KEY`: Flask secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `DATABASE_URL`: Database connection string

   **Optional (for enhanced features):**
   - OAuth2 credentials (Google, GitHub)
   - AWS S3 credentials (for cloud storage)
   - OpenAI API key (for AI features)
   - Redis URL (for caching)

### AWS S3 Setup

1. Create an S3 bucket in AWS Console
2. Configure IAM user with S3 access
3. Add credentials to `.env`:
   ```
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your-bucket-name
   ```

### OAuth2 Setup

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:5000/auth/google/callback`
6. Add to `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

#### GitHub OAuth

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App
3. Set Authorization callback URL: `http://localhost:5000/auth/github/callback`
4. Add to `.env`:
   ```
   GITHUB_CLIENT_ID=your-client-id
   GITHUB_CLIENT_SECRET=your-client-secret
   ```

## 🚀 Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker in Production

1. **Update `docker-compose.yml` for production:**
   - Set `FLASK_ENV=production`
   - Set `FLASK_DEBUG=0`
   - Use PostgreSQL instead of SQLite
   - Configure proper volumes

2. **Use production-ready database:**
   ```yaml
   db:
     image: postgres:15-alpine
     environment:
       POSTGRES_DB: smart_elearn
       POSTGRES_USER: elearn_user
       POSTGRES_PASSWORD: secure_password
   ```

### AWS EC2 Deployment

1. Launch EC2 instance
2. Install Docker:
   ```bash
   sudo yum install docker -y
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

3. Clone repository and deploy:
   ```bash
   git clone <your-repo>
   cd Smart_Elearn
   docker-compose up -d
   ```

### Heroku Deployment

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   web: gunicorn app:app
   ```

3. Deploy:
   ```bash
   heroku create smart-elearn
   heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   git push heroku main
   ```

## 📊 Monitoring & Maintenance

### Database Backups

```bash
# SQLite backup
cp instance/smart_elearn.db instance/smart_elearn.db.backup

# PostgreSQL backup
pg_dump -U username smart_elearn > backup.sql
```

### Logs

```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f logs/app.log
```

## 🔒 Security Checklist

- [ ] Change default `SECRET_KEY`
- [ ] Use strong database passwords
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Regular security updates
- [ ] Database backups
- [ ] Environment variables secured

## 📝 Notes

- The application uses SQLite by default for development
- For production, use PostgreSQL or MySQL
- Cloud storage (S3) is optional but recommended for scalability
- OAuth2 is optional but improves user experience

