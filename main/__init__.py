from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_admin import Admin


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hello'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:faraja@localhost/rrs'
admin = Admin(app, name='Control Panel')
app.config.from_pyfile('../config.cfg')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'ombenifaraja@gmail.com'
app.config['MAIL_PASSWORD'] = 'qokdawokmxsyvxgx'
mail = Mail(app)






from main import routes