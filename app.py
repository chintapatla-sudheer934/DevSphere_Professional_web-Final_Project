
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"
DB = "devsphere.db"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","pdf","txt","zip","doc","docx"}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        bio TEXT DEFAULT '',
        skills TEXT DEFAULT '',
        github TEXT DEFAULT '',
        linkedin TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        technologies TEXT DEFAULT '',
        github TEXT DEFAULT '',
        demo TEXT DEFAULT '',
        visibility TEXT DEFAULT 'Public',
        progress INTEGER DEFAULT 0,
        stars INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'Developer',
        UNIQUE(project_id,user_id)
    );

    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'Todo',
        priority TEXT DEFAULT 'Medium',
        due_date TEXT
    );

    CREATE TABLE IF NOT EXISTS issues(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        issue_type TEXT DEFAULT 'Bug',
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS milestones(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        due_date TEXT,
        status TEXT DEFAULT 'Pending'
    );

    CREATE TABLE IF NOT EXISTS resources(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS stars(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        UNIQUE(project_id,user_id)
    );
    """)
    conn.commit()
    conn.close()
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper

def project_access(project_id):
    conn = get_db()
    project = conn.execute("""
        SELECT p.*, u.name AS owner_name
        FROM projects p JOIN users u ON p.owner_id=u.id
        WHERE p.id=?
    """,(project_id,)).fetchone()
    member = conn.execute(
        "SELECT * FROM members WHERE project_id=? AND user_id=?",
        (project_id,session["user_id"])
    ).fetchone()
    conn.close()
    return project, member

@app.context_processor
def common_data():
    if "user_id" not in session:
        return {}
    conn=get_db()
    count=conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
        (session["user_id"],)
    ).fetchone()[0]
    conn.close()
    return {"unread_notifications":count}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip()
        email=request.form["email"].strip().lower()
        password=request.form["password"]

        if len(password)<6:
            flash("Password must contain at least 6 characters.","danger")
            return redirect(url_for("register"))

        conn=get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password) VALUES(?,?,?)",
                (name,email,generate_password_hash(password))
            )
            conn.commit()
            flash("Account created successfully.","success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.","danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower()
        password=request.form["password"]

        conn=get_db()
        user=conn.execute(
            "SELECT * FROM users WHERE email=?",(email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"],password):
            session["user_id"]=user["id"]
            session["name"]=user["name"]
            return redirect(request.args.get("next") or url_for("dashboard"))

        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn=get_db()
    user=conn.execute(
        "SELECT * FROM users WHERE id=?",(session["user_id"],)
    ).fetchone()

    projects=conn.execute("""
        SELECT p.* FROM projects p
        JOIN members m ON p.id=m.project_id
        WHERE m.user_id=?
        ORDER BY p.created_at DESC
    """,(session["user_id"],)).fetchall()

    stats={
        "projects":len(projects),
        "tasks":conn.execute("""
            SELECT COUNT(*) FROM tasks t
            JOIN members m ON t.project_id=m.project_id
            WHERE m.user_id=? AND t.status!='Done'
        """,(session["user_id"],)).fetchone()[0],
        "issues":conn.execute("""
            SELECT COUNT(*) FROM issues i
            JOIN members m ON i.project_id=m.project_id
            WHERE m.user_id=? AND i.status!='Resolved'
        """,(session["user_id"],)).fetchone()[0],
        "stars":conn.execute("""
            SELECT COALESCE(SUM(stars),0) FROM projects WHERE owner_id=?
        """,(session["user_id"],)).fetchone()[0]
    }
    conn.close()
    return render_template("dashboard.html",user=user,projects=projects,stats=stats)

@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    conn=get_db()
    user=conn.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
    projects=conn.execute(
        "SELECT * FROM projects WHERE owner_id=? AND visibility='Public'",
        (user_id,)
    ).fetchall()
    conn.close()
    if not user:
        return "User not found",404
    return render_template("profile.html",user=user,projects=projects)

@app.route("/profile/edit",methods=["GET","POST"])
@login_required
def edit_profile():
    conn=get_db()
    if request.method=="POST":
        d=request.form
        conn.execute("""
            UPDATE users SET name=?,bio=?,skills=?,github=?,linkedin=?
            WHERE id=?
        """,(d["name"],d["bio"],d["skills"],d["github"],d["linkedin"],session["user_id"]))
        conn.commit()
        conn.close()
        session["name"]=d["name"]
        flash("Profile updated.","success")
        return redirect(url_for("profile",user_id=session["user_id"]))

    user=conn.execute(
        "SELECT * FROM users WHERE id=?",(session["user_id"],)
    ).fetchone()
    conn.close()
    return render_template("edit_profile.html",user=user)

@app.route("/projects")
@login_required
def projects():
    conn=get_db()
    rows=conn.execute("""
        SELECT p.*,u.name owner_name
        FROM projects p JOIN users u ON p.owner_id=u.id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("projects.html",projects=rows)

@app.route("/projects/new",methods=["GET","POST"])
@login_required
def create_project():
    if request.method=="POST":
        d=request.form
        conn=get_db()
        conn.execute("""
            INSERT INTO projects
            (owner_id,title,description,category,technologies,github,demo,visibility)
            VALUES(?,?,?,?,?,?,?,?)
        """,(
            session["user_id"],d["title"],d["description"],d["category"],
            d["technologies"],d["github"],d["demo"],d["visibility"]
        ))
        project_id=conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO members(project_id,user_id,role) VALUES(?,?,?)",
            (project_id,session["user_id"],"Owner")
        )
        conn.commit()
        conn.close()
        flash("Project created.","success")
        return redirect(url_for("project",project_id=project_id))
    return render_template("create_project.html")

@app.route("/project/<int:project_id>")
@login_required
def project(project_id):
    project,member=project_access(project_id)
    if not project:
        return "Project not found",404
    if project["visibility"]=="Private" and not member:
        return "Private project",403

    conn=get_db()
    members=conn.execute("""
        SELECT m.*,u.name,u.email FROM members m
        JOIN users u ON m.user_id=u.id
        WHERE m.project_id=?
    """,(project_id,)).fetchall()

    tasks=conn.execute(
        "SELECT * FROM tasks WHERE project_id=? ORDER BY id DESC",
        (project_id,)
    ).fetchall()

    issues=conn.execute(
        "SELECT * FROM issues WHERE project_id=? ORDER BY id DESC",
        (project_id,)
    ).fetchall()

    comments=conn.execute("""
        SELECT c.*,u.name FROM comments c
        JOIN users u ON c.user_id=u.id
        WHERE c.project_id=? ORDER BY c.created_at DESC
    """,(project_id,)).fetchall()

    milestones=conn.execute(
        "SELECT * FROM milestones WHERE project_id=? ORDER BY id",
        (project_id,)
    ).fetchall()

    resources=conn.execute("""
        SELECT r.*,u.name FROM resources r
        JOIN users u ON r.user_id=u.id
        WHERE r.project_id=? ORDER BY r.uploaded_at DESC
    """,(project_id,)).fetchall()

    conn.close()
    return render_template(
        "project.html",p=project,member=member,members=members,
        tasks=tasks,issues=issues,comments=comments,
        milestones=milestones,resources=resources
    )

@app.route("/project/<int:project_id>/task",methods=["POST"])
@login_required
def add_task(project_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    d=request.form
    conn=get_db()
    conn.execute("""
        INSERT INTO tasks(project_id,title,description,priority,due_date)
        VALUES(?,?,?,?,?)
    """,(project_id,d["title"],d["description"],d["priority"],d["due_date"]))
    conn.commit()
    conn.close()
    flash("Task created.","success")
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/task/<int:task_id>",methods=["POST"])
@login_required
def update_task(project_id,task_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    conn=get_db()
    conn.execute(
        "UPDATE tasks SET status=? WHERE id=? AND project_id=?",
        (request.form["status"],task_id,project_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/issue",methods=["POST"])
@login_required
def add_issue(project_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    d=request.form
    conn=get_db()
    conn.execute("""
        INSERT INTO issues(project_id,title,description,issue_type,priority)
        VALUES(?,?,?,?,?)
    """,(project_id,d["title"],d["description"],d["issue_type"],d["priority"]))
    conn.commit()
    conn.close()
    flash("Issue reported.","success")
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/issue/<int:issue_id>",methods=["POST"])
@login_required
def update_issue(project_id,issue_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    conn=get_db()
    conn.execute(
        "UPDATE issues SET status=? WHERE id=? AND project_id=?",
        (request.form["status"],issue_id,project_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/comment",methods=["POST"])
@login_required
def add_comment(project_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    body=request.form["body"].strip()
    if body:
        conn=get_db()
        conn.execute(
            "INSERT INTO comments(project_id,user_id,body) VALUES(?,?,?)",
            (project_id,session["user_id"],body)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/milestone",methods=["POST"])
@login_required
def add_milestone(project_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    d=request.form
    conn=get_db()
    conn.execute(
        "INSERT INTO milestones(project_id,title,due_date) VALUES(?,?,?)",
        (project_id,d["title"],d["due_date"])
    )
    conn.commit()
    conn.close()
    return redirect(url_for("project",project_id=project_id))

@app.route("/project/<int:project_id>/upload",methods=["POST"])
@login_required
def upload(project_id):
    _,member=project_access(project_id)
    if not member:return "Access denied",403

    file=request.files.get("file")
    if not file or not file.filename:
        flash("Choose a file.","danger")
        return redirect(url_for("project",project_id=project_id))

    extension=file.filename.rsplit(".",1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        flash("This file type is not allowed.","danger")
        return redirect(url_for("project",project_id=project_id))

    stored=secrets.token_hex(8)+"_"+secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER,stored))

    conn=get_db()
    conn.execute("""
        INSERT INTO resources(project_id,user_id,filename,original_name)
        VALUES(?,?,?,?)
    """,(project_id,session["user_id"],stored,file.filename))
    conn.commit()
    conn.close()
    flash("Resource uploaded.","success")
    return redirect(url_for("project",project_id=project_id))

@app.route("/discover")
@login_required
def discover():
    q=request.args.get("q","").strip()
    conn=get_db()

    if q:
        rows=conn.execute("""
            SELECT p.*,u.name owner_name
            FROM projects p JOIN users u ON p.owner_id=u.id
            WHERE p.visibility='Public'
            AND (p.title LIKE ? OR p.category LIKE ? OR p.technologies LIKE ?)
            ORDER BY p.stars DESC
        """,(f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else:
        rows=conn.execute("""
            SELECT p.*,u.name owner_name
            FROM projects p JOIN users u ON p.owner_id=u.id
            WHERE p.visibility='Public'
            ORDER BY p.stars DESC,p.created_at DESC
        """).fetchall()

    conn.close()
    return render_template("discover.html",projects=rows,q=q)

@app.route("/project/<int:project_id>/star",methods=["POST"])
@login_required
def star(project_id):
    conn=get_db()
    existing=conn.execute(
        "SELECT id FROM stars WHERE project_id=? AND user_id=?",
        (project_id,session["user_id"])
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM stars WHERE id=?",(existing["id"],))
        conn.execute(
            "UPDATE projects SET stars=MAX(stars-1,0) WHERE id=?",
            (project_id,)
        )
    else:
        conn.execute(
            "INSERT INTO stars(project_id,user_id) VALUES(?,?)",
            (project_id,session["user_id"])
        )
        conn.execute(
            "UPDATE projects SET stars=stars+1 WHERE id=?",
            (project_id,)
        )

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("discover"))

@app.route("/notifications")
@login_required
def notifications():
    conn=get_db()
    rows=conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    conn.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=?",
        (session["user_id"],)
    )
    conn.commit()
    conn.close()
    return render_template("notifications.html",notifications=rows)

@app.route("/api/projects")
@login_required
def api_projects():
    conn=get_db()
    rows=conn.execute("""
        SELECT id,title,category,technologies,visibility,progress,stars
        FROM projects WHERE visibility='Public'
        ORDER BY stars DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

if __name__=="__main__":
    init_db()
    app.run(debug=True)
