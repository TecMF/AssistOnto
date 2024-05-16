from flask import Flask, url_for, render_template, redirect, request, flash, g, session
from uuid import uuid4
# to create new function decorator:
from functools import wraps
# to increase password security
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import os
import sqlite3
import secrets

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

#### Database

DATABASE = None

def db_query_db(db, query, args=(), one=False):
  cur = db.execute(query, args)
  rv = cur.fetchall()
  cur.close()
  return (rv[0] if rv else None) if one else rv

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    g._database = db
    db_query_db(db, "PRAGMA foreign_keys=ON")
  return db

def query_db(query, args=(), one=False):
  db = get_db()
  return db_query_db(db, query, args, one)

@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()


#### Authentication

USER_SESSION_KEY = 'USERNAME'

def login_and_redirect(username, next_url=''):
  ## CAUTION: only call this function after verifying user
  ## authentication

  # NOTE: authentication is done simply by creating this key in
  # the session object, which translates to signed cookie in the
  # browser. Because the cookie is signed with our private secret
  # key, no user can fake being another one by editing the cookie
  # (which would render it invalid)
  session[USER_SESSION_KEY] = username
  if not next_url:
    next_url = url_for('view_app')
  return redirect(next_url)

def get_user_id(username):
  res = query_db("""SELECT id AS user_id
  FROM users
  WHERE username = ?""", (username,), one=True)
  if res is not None:
    user_id = res['user_id']
    g._user_id = user_id
    return user_id

def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if getattr(g, '_user_id', None) is None:
      username = session.get(USER_SESSION_KEY)
      if username is None:
        return redirect(url_for('view_login', next=request.url))
      else:
        user_id = get_user_id(username)
        if user_id is None:
          return redirect(url_for('logout'))
        g._username = username
    return f(*args, **kwargs)
  return decorated_function

##### Authentication Routes

@app.route('/login', methods=['GET'])
def view_login():
  if session.get(USER_SESSION_KEY) is not None:
    return redirect(url_for('view_app'))
  return render_template('login.html')

@app.route('/login', methods=['POST'])
def post_login():
  username = request.form.get('input-username', '')
  password = request.form.get('input-password', '')
  next_url = request.form.get('next-url', '')
  res = query_db("""SELECT id AS user_id, password AS password_hash
  FROM users
  WHERE username = ?""",
                (username,),
                one = True)
  if res is None:
    flash("No user with this name and password exists. Try again", category='warning')
    return redirect(url_for('view_login', next=next_url))
  user_id = res['user_id']
  password_hash = res['password_hash']
  if not check_password_hash(password_hash, password):
    flash("No user with this name and password exists. Try again", category='warning')
    return redirect(url_for('view_login', next=next_url))
  g._user_id = user_id
  return login_and_redirect(username, next_url=next_url)

@app.route('/register', methods=['GET'])
def view_register():
  # TODO: we don't want open registering
  return render_template('register.html')

@app.route('/register', methods=['POST'])
def post_register():
  username = request.form.get('input-username', '')
  email = request.form.get('input-email')
  password = request.form.get('input-password', '')
  input_valid = True
  if len(username) < 6:
    input_valid = False
    flash("Username should have at least 6 characters", category='warning')
  if len(password) < 6:
    input_valid = False
    flash("Password should have at least 6 characters", category='warning')
  # finished validation
  if not input_valid:
    return redirect(url_for('view_register'))
  password_hash = generate_password_hash(password)
  # create new user
  db = get_db()
  try:
    cur = db.execute("""INSERT INTO users(username, email, password)
  VALUES (:username, :email, :password)
  RETURNING id AS user_id""",
            {'username': username, 'email': email, 'password': password_hash})
    res = cur.fetchone()
    if res is not None:
      user_id = res['user_id']
      g._user_id = user_id
    db.commit()
  except sqlite3.IntegrityError:
    flash("Username already exists, please choose another", category='warning')
    return redirect(url_for('view_register'))
  return login_and_redirect(username)

@app.route('/logout')
@login_required
def logout():
  del session[USER_SESSION_KEY]
  g._user_id = None
  return redirect(url_for('index'))

#### Business Routes

@app.route("/", methods=["GET"])
def index():
  if session.get(USER_SESSION_KEY) is not None:
    return redirect(url_for('view_app'))
  return render_template("index.html")

@app.route('/app', methods=["GET"])
@login_required
def view_app():
  return render_template("app.html", username=g._username)

@app.route('/messaged', methods=["POST"])
@login_required
def message_new():
  # add message to session
  # db = get_db()
  #   cur = db.execute("""INSERT INTO groups(name, description)
  # VALUES (:name, :description)
  # RETURNING id AS group_id""",
  #           {'name': name, 'description': description})
  #   res = cur.fetchone()
  #   if res is not None:
  #     group_id = res['group_id']
  #db.commit()
  user_message = request.form.get('user_message', None)
  if user_message is None:
    return "" # no HTML response
  # get answer from AI
  # # TODO: get answer from AI https://platform.openai.com/docs/api-reference/chat/create
  # # TODO: break it into paragraphs <p>

  # TODO: store client in session data
  # client = OpenAI()
  # response = client.chat.completions.create(
  #     model="gpt-3.5-turbo",
  #     messages=[
  #         # TODO: include ontology in system message?
  #         {"role": "system", "content": "You are a helpful assistant."},
  #         {"role": "user", "content": user_message}
  #     ]
  # )
  # # TODO: check if response was ok
  # assistant_message = response.choices[0].message
  assistant_message = 'The answer to life, the universe, and everything is… 42.'
  # TODO: include user message client-side
  return render_template("message.html", username=g._username, user_message=user_message, ainame="AI", assistant_message=assistant_message)

class NotAuthorized(Exception):
  "Raised when the user does not have the authority to perform some action"
  pass

@app.errorhandler(NotAuthorized)
def handle_bad_request(e):
  return render_template("error.html", what="Unauthorized"), 401

@app.errorhandler(404)
def page_not_found(e):
  # note that we set the 404 status explicitly
  return render_template('error.html', what="Page not found"), 404

def start_webapp(host=None, port=None, debug_mode=None, db_path=None):
  global DATABASE
  if host is None:
    host = 'localhost'
  if port is None:
    port = 8888
  if debug_mode is None:
    # INFO: this is to debug the server; to debug openai library
    # we can set the environment variable OPENAI_LOG=debug
    debug_mode = True
  if db_path is None:
    db_path = 'assistonto.db'
  DATABASE = db_path
  app.run(host=host, port=port, debug=debug_mode)
