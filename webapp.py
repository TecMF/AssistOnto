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
import markdown as md
from sanitize_md import SanitizeExtension

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

#### Database

DATABASE = None
MAX_MESSAGES_SHOWN = 100

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

#### Templating
HTML_WHITELIST = {
  'div': [], 'p': [], 'pre':[], 'code': ['class'],
  # 'a':['href'], # unsafe:
  'blockquote': [], 'em': [], 'strong': [], 'h1':[], 'h2':[], 'h3':[]
}
app.add_template_global(lambda text: md.markdown(text, extensions=['fenced_code', SanitizeExtension(HTML_WHITELIST)]), name='sane_markdown')

#### Authentication

USER_SESSION_KEY = 'USERNAME'
USER_CHAT_KEY = 'USERCHAT'

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

@app.route('/chat', methods=["GET"])
@app.route('/chat/<int:chat_id>', methods=["GET"])
@login_required
def view_app(chat_id=None):
  db = get_db()
  user_chats = db_query_db(
      db,
      """SELECT id, subject
FROM chats
WHERE user_id = :user_id""",
      dict(user_id=g._user_id)
    )
  if chat_id is None or chat_id not in [chat['id'] for chat in user_chats]:
    # No chat specified or unauthorized chat (not owned by user), so
    # get latest chat id, if any
    chat_id = db_query_db(
      db,
      """SELECT chat_id
FROM messages INNER JOIN chats ON messages.chat_id = chats.id
WHERE user_id = :user_id
ORDER BY tstamp DESC
LIMIT 1""",
      dict(user_id=g._user_id),
      one = True
    )['chat_id']
    if chat_id is None:
      # if no chat, create one
      chat_id = chat_new_chat(user_id, db=db)
  session[USER_CHAT_KEY] = chat_id
  chat_messages = chat_get_context(chat_id, ncontext=MAX_MESSAGES_SHOWN)
  return render_template(
    "app.html",
    username=g._username,
    chat_messages=chat_messages,
    user_chats=user_chats
  )

def chat_new_chat(user_id, subject=None, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    """INSERT INTO chats(user_id, subject)
  VALUES (:user_id, :subject)
  RETURNING id AS chat_id""",
    dict(user_id=user_id, subject=subject),
    one=True)
  if res is None:
    db.rollback()
  else:
    db.commit()
    chat_id = res.chat_id
    return chat_id

def chat_insert_message(chat_id, role, content, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    """INSERT INTO messages(chat_id, user_msg, content, tstamp)
  VALUES (:chat_id, :user_msg, :content, unixepoch())
  RETURNING id AS message_id""",
    dict(chat_id=chat_id, user_msg=(role == "user"), content=content),
    one=True)
  if res is None:
    db.rollback()
  else:
    db.commit()
    message_id = res['message_id']
    return message_id

def chat_get_context(chat_id, ncontext=3, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    """SELECT content, user_msg
FROM messages
WHERE chat_id = :chat_id
ORDER BY tstamp DESC
LIMIT :ncontext""",
    dict(chat_id=chat_id, ncontext=ncontext))
  return reversed(res)

@app.route('/messaged', methods=["POST"])
@login_required
def message_new():
  user_message = request.form.get('user_message', None)
  if user_message is None:
    return "" # no HTML response
  chat_id = session.get(USER_CHAT_KEY)
  if chat_id is None:
    return redirect(url_for('view_app'))
  db = get_db()
  _ = chat_insert_message(chat_id, "user", user_message, db=db)
  # get answer from AI
  # # TODO: break it into paragraphs <p>
  api_key = os.environ.get("OPENAI_API_KEY", None)
  if api_key is None:
    flash("No API key means we can't contact the assistant.", category='error')
    return "", 500
  client = OpenAI(api_key=api_key)
  del api_key
  context_messages = chat_get_context(chat_id, ncontext=3, db=db)
  messages = [
    dict(role="user" if usr_msg == 1 else "assistant", content=content)
    for (content, usr_msg) in context_messages
  ]
  ontology = request.form.get('ontology', None)
  ontology_message = f"The current ontology is:\n{ontology}" if ontology is not None else ""
  system_msg = dict(
    role="system",
    content=f"""You are helpful assistant in the domain of CyberSecurity ontologies. You should help the user build and query their ontology. {ontology_message}""")
  messages.append(system_msg)
  response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    max_tokens=2000
  )
  # TODO: check if response was ok
  assistant_message = response.choices[0].message.content
  _ = chat_insert_message(chat_id, "assistant", assistant_message)
  return render_template(
    "assistant_message.html",
    ainame="AI", # TODO: include AI name when we have more options
    assistant_message=assistant_message
  )

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
