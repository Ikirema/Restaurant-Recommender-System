from flask import render_template, Flask, url_for, flash, redirect, request, session, abort
import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, session
from main import app, db, bcrypt, mail, admin
from main.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm, VerifyEmailForm, UpdateAccountForm, PostForm, AdminForm
from main.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
import numpy as np
import pandas as pd
import csv
from flask_admin.contrib.sqla import ModelView



@app.route('/')
def index():
    return render_template('home.html')

@app.route('/home')
def home():
    return render_template('home.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccesful. Please check emaiil and password!', 'danger')
    return render_template('login.html', title='Log In', form=form)

@app.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account Created Succesfully.Login with your details', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Sign Up', form=form)

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

# Load the data
df = pd.read_csv('ratings.csv')

# Popularity-based recommendation
def popularity_based_rec(df, group_col, rating_col):
    grouped = df.groupby(group_col).agg({rating_col: [np.size, np.sum, np.mean]})
    popular = grouped.sort_values((rating_col, 'mean'), ascending=False)
    total_sum = grouped[rating_col]['sum'].sum()
    popular['percentage'] = popular[rating_col]['sum'].div(total_sum) * 100
    return popular.sort_values(('percentage'), ascending=False)


# Nearest neighbor recommendation
def compute_distance(a, b):
    common_ratings = [rating for rating in a['ratings'] if rating in b['ratings']]
    if len(common_ratings) == 0 or len(a['ratings']) != len(b['ratings']):
        return float('inf')
    sum_squared_differences = sum([(a['ratings'][i] - b['ratings'][i]) ** 2 for i in range(len(common_ratings))])
    return sum_squared_differences ** 0.5

def get_neighbors(itemID, K):
    target_item = itemDict[itemID]
    distances = [(compute_distance(target_item, itemDict[itemID]), itemID) for itemID in itemDict if itemDict[itemID]['name'] != target_item['name']]
    distances.sort()
    return distances[:K]

# User-based recommendation
item_ratings = df.pivot_table(index='userID', columns='name', values='rating')


@app.route('/popularity')
@login_required
def popularity():
    popularity_stats = popularity_based_rec(df, 'name', 'rating').head()
    popular_items = popularity_stats
    return render_template('popularity.html', items=popular_items)

@app.route('/nearest/<int:itemID>')
@login_required
def nearest(itemID):
    neighbors = get_neighbors(itemID, 5)
    nearest_items = [itemDict[itemID]['name'] for _, itemID in neighbors]
    return render_template('nearest.html', items=nearest_items)

@app.route('/user/<string:username>')
@login_required
def user(username):
    user_ratings = item_ratings.loc[username].dropna()
    similar_users = item_ratings.corrwith(user_ratings).sort_values(ascending=False).dropna().head(5)
    similar_users = similar_users.index.tolist()
    return render_template('user.html', username=username, similar_users=similar_users)

if __name__ == '__main__':
    # Store all restaurants in a dictionary
    itemDict = {}
    with open('ratings.csv', mode='r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader)
        for row in csv_reader:
            if row[1] == '' or row[2] == '' or row[3] == '' or row[4] == '':
                continue
            itemID = int(row[1])
            name = row[2]
            userID = int(row[3])
            rating = int(row[4])
            if itemID not in itemDict:
                itemDict[itemID] = {'name': name, 'ratings': [], 'numRatings': 0, 'totalRating': 0}
            itemDict[itemID]['ratings'].append(rating)
            itemDict[itemID]['numRatings'] += 1
            itemDict[itemID]['totalRating'] += rating
    for itemID in itemDict:
        item = itemDict[itemID]
        name = item['name']
        ratings = item['ratings']
        numRatings = item['numRatings']
        totalRating = item['totalRating']
        avgRating = totalRating / numRatings
        itemDict[itemID] = {'name': name, 'ratings': ratings, 'numRatings': numRatings, 'avgRating': avgRating}



class Controller(ModelView):
    def is_accessible(self):
        if current_user.is_admin == True:
            return current_user.is_authenticated
        else:
            return abort(404)
    def not_auth(self):
        return "You are not allowed to view this page"
    
admin.add_view(Controller(User, db.session))

@app.route('/admin-signup', methods=['GET', 'POST'])
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
