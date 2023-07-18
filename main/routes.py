from flask import render_template, Flask, url_for, flash, redirect, request, session, abort
import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, session
from main import app, db, bcrypt, mail, admin
from main.forms import (RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm, VerifyEmailForm,
                         UpdateAccountForm, PostForm, AdminForm)
from main.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from flask_admin.contrib.sqla import ModelView

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if user.confirmed:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('home'))
            else:
                flash('Please confirm your email address to log in.', 'warning')
        else:
            flash('Login Unsuccessful. Please check email or password.', 'danger')
    return render_template('login.html', title='Login', form=form)



from itsdangerous import BadSignature, Serializer, TimedSerializer, URLSafeTimedSerializer
from yaml import serialize_all 
from flask_mail import Message, Mail
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


@app.route("/registration", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)

        # Generate a confirmation token
        token = serializer.dumps(user.email, salt='email-confirm')

        # Send confirmation email
        confirmation_link = url_for('confirm_email', token=token, _external=True)
        message = Message('Confirm Your Email', recipients=[user.email], sender=app.config['MAIL_USERNAME'])
        message.body = f'Please click the link to confirm your email: {confirmation_link}'
        mail.send(message)

        db.session.add(user)
        db.session.commit()
        flash('Your account has been created. Please check your email to confirm your account.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registration', form=form)

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=1800)  # 30 minutes expiration

        user = User.query.filter_by(email=email).first()
        if user:
            user.confirmed = True
            db.session.commit()
            flash('Email confirmed. You can now log in.', 'success')
        else:
            flash('User not found.', 'danger')

    except BadSignature:
        flash('The confirmation link is invalid or has expired.', 'danger')

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image = url_for('static', filename='profile_pics/' + current_user.image)
    return render_template('account.html', title='Account', image=image, form=form)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request')
    msg.recipients=[user.email]
    msg.sender='noreply@app.com'
    msg.body = f''' To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request then simply ingnore this email and no changes will be made
'''
    
    mail.send(msg)

@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    form = VerifyEmailForm()
    return redirect(url_for('home'), form=form)
    

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user =User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash(f'An email has been sent to {user.email} with instructions to reset your password','info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to Log In', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', title='Reset Password', form=form)

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created', 'Success')
        return redirect(url_for('view_post'))
    return render_template('create_post.html', title='New Post', 
                           form=form, legend='New Post')

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your Post Has Been Updated!', 'Success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', 
                           form=form, legend='Update Post')

@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('view_post'))

@app.route('/view_post')
def view_post():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('view_post.html', title='View Posts', posts=posts)

class Controller(ModelView):
    def is_accessible(self):
        if current_user.is_admin == True:
            return current_user.is_authenticated
        else:
            return abort(404)
    def not_auth(self):
        return "You are not allowed to view this page"
    
admin.add_view(Controller(User, db.session))

@app.route('/24112000', methods=['GET', 'POST'])
def admin_signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = AdminForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password, is_admin=True)
        db.session.add(user)
        db.session.commit()
        flash('Account Created Succesfully. Login with your details!', 'success')
        return redirect(url_for('login'))
    return render_template('admin-signup.html', title='Sign Up', form=form)











#RECOMMENDER SYSTEMS IMPLEMENTATION
import pickle
from main.search import search
from main.contentB import contentB_recommend
with open('search.pkl', 'rb') as file:
    search = pickle.load(file)
with open('contentB.pkl', 'rb') as file:
    contentB_rec = pickle.load(file)


@app.route('/content')
@login_required
def content_based_rec():
    return render_template('content-based.html')

@app.route('/hybrid')
@login_required
def hybrid_rec():
    return render_template('hybrid.html')


#SEARCH ENGINE
@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_route():
    if request.method == 'POST':
        search_query = request.form['name']
        results = search(search_query)  # Call your search function here
        return render_template('search_results.html', results=results)
    return render_template('search.html')


#CONTENT BASED RECOMMENDATION
@app.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend():
    if request.method == 'POST':
        description = request.form['description']
        results = contentB_rec(description)  # Call your content-based recommendation function here
        return render_template('recommendation_results.html', results=results)
    return render_template('recommendation.html')



