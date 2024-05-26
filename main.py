from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from typing import List
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
# Configure Flask-Login's Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# TODO: Add Flask-Gravatar extension
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    # get session ID form active User or raise Status 404 for the application
    return db.get_or_404(User, user_id)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
# TODO: Create a BlogPost table for all blogs.
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    # Create Foreign Key, "users.id" the users refers to the table name of User.
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Create reference to the User object. The "posts" refers to the posts property in the User class.
    author: Mapped["User"] = relationship(back_populates="posts")

    # The "parent" refers to the parent property in the Comment class.
    comments: Mapped[List["Comment"]] = relationship(back_populates="parent_post")


# TODO: Create a User table for all your registered users.
# add UserMixin for User Authentication
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(250), nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts: Mapped[List["BlogPost"]] = relationship(back_populates="author")
    # This will act like a List of Comment objects attached to each User.
    # The "comment_author" refers to the comment_author property in the Comment class.
    comments: Mapped[List["Comment"]] = relationship(back_populates="comment_author")


# TODO: Create a Comment table for all comments.
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(250), nullable=False)

    # Create Foreign Key, "users.id" the users refers to the table name of Comment.
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Create reference to the User object. The "comments" refers to the comments property in the User class.
    comment_author: Mapped["User"] = relationship(back_populates="comments")

    # Create Foreign Key, "users.id" the users refers to the table name of BlogPost.
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    # Create reference to the BlogPost object. The "comments" refers to the comments property in the BlogPost class.
    parent_post: Mapped["BlogPost"] = relationship(back_populates="comments")


# Line below only required once, when creating DB
with app.app_context():
    db.create_all()


# add Admin to the Database (on the first run)
# with app.app_context():
#     admin = User(username="admin", email="admin@gmail.com",
#                  password=generate_password_hash("admin", method='pbkdf2', salt_length=8))
#
#     db.session.add(admin)
#     db.session.commit()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(code=403)
        return f(*args, **kwargs)

    return decorated_function


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    # get RegisterForm
    register_form = RegisterForm(meta={'csrf': False})
    # validate the form by controlling the User's inputs
    register_form.validate_on_submit()
    # if form was submitted (POST Method)
    if register_form.validate():
        # get data entered in the RegisterForm
        username_form = register_form.username.data
        email_form = register_form.email.data
        password_form = register_form.password.data
        # Hash and salt the password to make it more secure
        hashed_password = generate_password_hash(password_form, method='pbkdf2', salt_length=8)
        # search if the user already exist in the database
        existing_user = db.session.execute(db.select(User).where(User.email == email_form)).scalar()
        # if User does not exist:
        if not existing_user:
            # add new User to the Database
            new_user = User(
                username=username_form,
                email=email_form,
                password=hashed_password)

            db.session.add(new_user)
            db.session.commit()

            # Log in and authenticate user after adding details to database.
            login_user(new_user)
            # if User is logged in hide Log-In and Register Buttons
            return redirect(url_for("get_all_posts"))

        else:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
    return render_template("register.html", form=register_form, current_user=current_user)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET', 'POST'])
def login():
    # get LoginForm
    login_form = LoginForm(meta={'csrf': False})
    # validate the form by controlling the User's inputs
    login_form.validate_on_submit()
    # find the User that tries to Log in
    user_to_login = db.session.execute(db.select(User).where(User.email == login_form.email.data)).scalar()
    # if form was submitted (POST Method)
    if login_form.validate():
        # check if User exists
        if user_to_login:
            # check if the entered password is correct
            if check_password_hash(user_to_login.password, login_form.password.data):
                # Log in and authenticate user after adding details to database.
                login_user(user_to_login)
                flash('Logged in successfully')
                # go to secrets.html and pass in the username (current user is logged in)
                # if User is logged in hide Log-In and Register Buttons
                return redirect(url_for('get_all_posts'))
            else:
                # password is incorrect
                flash('Invalid password')
                redirect(url_for('login'))
        else:
            # User does not exist
            flash('User does not exist')
            return redirect(url_for('login'))

    return render_template("login.html", form=login_form, current_user=current_user)


@app.route('/logout')
def logout():
    # logout current User
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    # get all the created posts
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    # pass all created posts and in the template and check if the current User is authenticated
    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    # get a CommentForm to allow comments on posts
    comment_form = CommentForm()
    # get the requested post otherwise raise 404 exception ("URL Not Found")
    requested_post = db.get_or_404(BlogPost, post_id)
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please Login')
            return redirect(url_for('login'))
        else:
            # Add comment to the Comment Table
            new_comment = Comment(
                text=comment_form.comment.data,
                author_id=current_user.id,
                post_id=post_id
                )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('get_all_posts'))

    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form,
                           gravatar=gravatar)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    # get a form to create a new post
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        # go back to homepage
        return redirect(url_for("get_all_posts"))
    # render template to create a post and check if the current User is authenticated
    return render_template("make-post.html", form=form, current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    # get the selected post to edit
    post = db.get_or_404(BlogPost, post_id)
    # get the form to edit the selected post
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        # edit all the fields in the post
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user.username
        post.body = edit_form.body.data
        db.session.commit()
        # show edited post
        return redirect(url_for("show_post", post_id=post.id))
    # render the template in the "Edit mode"
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post
@admin_only
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    # get the selected post and delete it
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


# TODO: Create route to delete comment
@app.route("/delete_comment/<int:post_id>/<int:comment_id>", methods=["GET", "POST"])
def delete_comment(post_id, comment_id):
    # get the selected comment and delete it
    comment_to_delete = db.get_or_404(Comment, comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


# prevent page from Reloading Twice to avoid UNIQUE error for a certain field
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5002)

# if __name__ == "__main__":
#     app.run(debug=True, port=5002)
