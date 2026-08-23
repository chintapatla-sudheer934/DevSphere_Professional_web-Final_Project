
# DevSphere – Developer Collaboration & Project Workspace

DevSphere is a professional full-stack Web Technology project designed for students and developers to manage projects, collaborate with teams and showcase software work.

## Main Concept

DevSphere does not use a separate admin panel. A developer can create their own projects and participate in other project workspaces.

## Features

- Professional registration and login
- Developer profile
- Skills, GitHub and LinkedIn links
- Personal dashboard
- Project creation
- Public/private projects
- Project workspace
- Team members
- Task management
- Task status tracking
- Issue and bug tracking
- Milestones
- Project discussions
- Project resource uploads
- Project progress
- Project stars
- Public project discovery
- Notifications
- REST-style JSON API

## Technology Stack

- Python
- Flask
- SQLite
- HTML5
- CSS3
- JavaScript
- Werkzeug password hashing
- Flask sessions

## Folder Structure

```text
DevSphere/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── edit_profile.html
│   ├── projects.html
│   ├── create_project.html
│   ├── discover.html
│   ├── project.html
│   └── notifications.html
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── app.js
    └── uploads/
```

## Installation – Windows

Open Command Prompt in the project folder:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the browser:

```text
http://127.0.0.1:5000
```

## How to Use

```text
Register
   ↓
Login
   ↓
Developer Dashboard
   ↓
Complete Profile
   ↓
Create Project
   ↓
Project Workspace
   ├── Tasks
   ├── Issues
   ├── Team
   ├── Milestones
   ├── Discussion
   └── Resources
   ↓
Project Showcase
```

## API

Logged-in users can request public projects:

```text
GET /api/projects
```

## Database

SQLite is used. The database file `devsphere.db` is created automatically when the application starts.

Tables include:

- users
- projects
- members
- tasks
- issues
- comments
- milestones
- resources
- notifications
- stars

## Security

The project includes:

- Password hashing
- Session authentication
- Login protection
- Project access checks
- File extension validation

For production deployment, add CSRF protection, secure environment variables, rate limiting and production file storage.

## Future Enhancements

- Real-time team chat
- GitHub API integration
- GitHub commit activity
- Email notifications
- Team invitation system
- Kanban board
- Calendar
- Advanced analytics
- Dark mode
- MySQL/PostgreSQL
- Cloud deployment

## Academic Project

**Project Title:** DevSphere – Developer Collaboration & Project Workspace

**Project Type:** Web Technology Final Project

**Backend:** Python Flask

**Frontend:** HTML, CSS, JavaScript

**Database:** SQLite
