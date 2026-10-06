import os
import psycopg2
from psycopg2.extras import RealDictCursor
from helpers import login_required, apology
from flask import Flask, redirect, render_template, request, session, g, url_for, Response, make_response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import base64
import os



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = os.environ["SECRET_KEY"]
Session(app)
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = psycopg2.connect(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            dbname=os.environ["DB_NAME"],
            cursor_factory=RealDictCursor,
        )
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def SQL(query, *args, read=True, one=False):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(query.replace("?", "%s"), args)
        rv = cur.fetchall() if cur.description else []
    if not read:
        db.commit()
    return (rv[0] if rv else None) if one else rv


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        name = request.form.get("accountName")
        email = request.form.get("email").lower()
        role = request.form.get("accountType")
        password = request.form.get("password")
        confirmation = request.form.get("confirmationPassword")
        if password != confirmation:
            return apology("Passwords do not match", 400)
        else:
            rows = SQL("SELECT * FROM users WHERE email = ?", email)
            if len(rows) != 0:
                return apology("Email already exists", 400)
            else:
                SQL("INSERT INTO users (name, email, role, password_hash) VALUES(?, ?, ?, ?)", name, email, role, generate_password_hash(password), read=False)
                return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Forget any user_id
    session.clear()
    if request.method == "POST":
        # Query database for username
        rows = SQL("SELECT * FROM users WHERE email = ?", request.form.get("email").lower())
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password_hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 403)
        # Remember which user has logged in
        session.update({f'user_{key}': rows[0][key] for key in ["id", "name" ,"email", "role"]}) 
        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("login.html")



@app.route('/')
def index():
    if session.get("user_id"):
        if session['user_role'] == 'instructor':
            rows=SQL("SELECT * FROM courses WHERE instructor_id = ? ORDER BY id DESC",session.get("user_id"))
            return render_template('home_instructor.html', courses=rows)
        else:
            rows=SQL("""SELECT courses.* FROM courses,course_enrollments 
                         WHERE  courses.id = course_enrollments.course_id 
		                   AND course_enrollments.learner_id=? ORDER BY enrollment_date DESC;""",session["user_id"])
            return render_template('home.html', courses=rows)
    else:
        return render_template('index.html')


@app.route("/logout")
@login_required
def logout():
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")




@app.route('/forums', methods=['GET', 'POST'])
@login_required
def forums():
    if request.method == 'POST':
        title = request.form.get("post_title")
        content = request.form.get('post_content')
        posts = SQL("SELECT Posts.*, users.name AS user_name FROM Posts JOIN users ON Posts.user_id = users.id ORDER BY Posts.id DESC;")
        return redirect('/forums')
    else:
        posts = SQL("SELECT Posts.*, users.name AS user_name FROM Posts JOIN users ON Posts.user_id = users.id ORDER BY id DESC;")
        return render_template('forums.html', posts=posts)

@app.route('/post/<id>', methods=['GET', 'POST'])
@login_required
def post(id):
    if request.method == 'POST':
        message = request.form.get('message')
        SQL("INSERT INTO Comments (user_id, post_id, message) VALUES (?, ?, ?)", session["user_id"], id, message, read=False)
        return redirect(url_for('post', id=id))  
    else:
        post = SQL("SELECT * FROM Posts WHERE id=?;", id, one=True)
        #comments = SQL("SELECT * FROM Comments WHERE post_id=?;", id)
        comments = SQL("SELECT Comments.*, users.name AS user_name FROM Comments JOIN users ON Comments.user_id = users.id WHERE comments.post_id=?;", id)
        return render_template('post.html', post=post, comments=comments)
        

@app.route('/courses')
@login_required
def courses():
    if session['user_role']=='instructor':
        rows=SQL("SELECT courses.*, users.name As instructor_name FROM courses JOIN users ON courses.instructor_id = users.id;")
        return render_template('courses.html', courses=rows)
    else:
        rows=SQL("SELECT courses.*, users.name As instructor_name FROM courses JOIN users ON courses.instructor_id = users.id;")
        enrollments = SQL("SELECT * FROM course_enrollments WHERE learner_id = ?;",session['user_id'])
        courses_enrolled = []
        for enrollment in enrollments:
            courses_enrolled.append(enrollment['course_id']) 
        return render_template('courses.html', courses=rows, enrollments=courses_enrolled)


@app.route('/list/<id>')
@login_required
def list(id):
    SQL("INSERT INTO course_enrollments (learner_id, course_id) VALUES (?, ?)", session['user_id'], id, read=False)
    return redirect('/')


@app.route('/unlist/<id>')
@login_required
def unlist(id):
    SQL("DELETE FROM course_enrollments WHERE learner_id=? AND course_id=?;", session['user_id'], id, read=False)
    return redirect('/')

@app.route('/course/<id>')
@login_required
def course(id):
    return render_template('course.html', id= id)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        title = request.form.get("course_title")
        description = request.form.get("course_description")
        pdf_file = request.files['pdf_file']
        image_file = request.files['image_file']
        if pdf_file and image_file:
            filename = secure_filename(pdf_file.filename)
            # Ensure the uploads directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(file_path)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)

            with open(image_path, 'rb') as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')           

            with open(file_path, 'rb') as f:
                data = f.read()

            
            SQL('INSERT INTO courses (title, description, instructor_id, lecture_file, preview) VALUES (?, ?, ?, ?, ?)', title, description, session['user_id'], data, image_base64, read=False)
            return redirect('/')
    return redirect('/')


@app.route('/delete/<title>')
@login_required
def delete(title):
    SQL("DELETE FROM courses WHERE title = ?", title, read = False)
    return redirect('/')

@app.route('/edit/<id>', methods=['POST'])
@login_required
def edit(id):
    course = SQL("SELECT * FROM courses WHERE id = ?", id, one=True)
    title = request.form.get("course_title_new")
    description = request.form.get("course_description_new")
    pdf_file = request.files['pdf_file_new']
    image_file = request.files['image_file_new']
    # Ensure the uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if title:
        SQL("UPDATE courses SET title = ? WHERE id = ?;", title, id, read=False)
    if description:
        SQL("UPDATE courses SET description = ? WHERE id = ?;", description, id, read=False) 
    if pdf_file:   
        filename = secure_filename(pdf_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pdf_file.save(file_path)          
        with open(file_path, 'rb') as f:
            data = f.read()
        SQL("UPDATE courses SET lecture_file = ? WHERE id = ?;", data, id, read=False) 
    if image_file:       
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_path)
        with open(image_path, 'rb') as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')    
        SQL("UPDATE courses SET preview = ? WHERE id = ?;", image_base64, id, read=False) 
   
    return redirect('/')


@app.route('/view_pdf/<id>')
@login_required
def view_pdf(id):
    row = SQL('SELECT title,lecture_file FROM courses WHERE id = ?', id, one=True)
    title = row["title"]
    data = bytes(row["lecture_file"])
    response = make_response(data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=file.pdf'
    return response
