from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)

# 1. Database & Security Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SECRET_KEY'] = 'wendys-super-secret-key-123'

# Initialize the tools
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Sends uninvited guests to the login page

# 2. Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    likes = db.relationship('Like', backref='author', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)   



# This tells Flask-Login how to find a user in the database
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 3. Create the Database
with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html", name="Guest", year=2026)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for("login"))
        
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Hand them the VIP pass!
            login_user(user)
            # Send them to the feed
            return redirect(url_for("feed"))
        else:
            return "<h1>Oops!</h1><p>Invalid username or password. Try again.</p>"
            
    return render_template("login.html")

# The Blog Feed Route
@app.route("/feed")
@login_required
def feed():
   # Grab all the posts from the database
   all_posts = Post.query.all()
   #pass them to the feed template
   return render_template("feed.html", user=current_user, posts=all_posts)

@app.route("/create-post", methods=["GET", "POST"])
@login_required
def create_post():
    # THE BOUNCER: If you aren't Wendy, you get kicked out!
    if current_user.email != 'wendy@blog.com':
        return "<h1>Access Denied! Only Wendy can write posts.</h1>"

    if request.method == "POST":
        post_title = request.form.get("title")
        post_content = request.form.get("content")
        
        new_post = Post(title=post_title, content=post_content, author=current_user)
        
        db.session.add(new_post)
        db.session.commit()
        
        return redirect(url_for('feed'))
        
    return render_template("create_post.html")

@app.route("/like-post/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):
    post = Post.query.get(post_id)
    like = Like.query.filter_by(author_id=current_user.id, post_id=post_id).first()

    if not post:
        return redirect(url_for('feed'))
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        new_like = Like(author_id=current_user.id, post_id=post.id)
        db.session.add(new_like)
        db.session.commit()

    return redirect(url_for('feed'))

@app.route("/add-comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    text = request.form.get("text")

    if text:
        comment = Comment(text=text, author_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()

    return redirect(url_for('feed'))



# The Logout Route
@app.route("/logout")
@login_required
def logout():
    logout_user() # Tears up the VIP pass
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)