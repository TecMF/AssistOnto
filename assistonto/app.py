from flask import Flask, url_for, render_template, redirect, request, flash, g, session
# to create new function decorator:
from functools import wraps
import itertools as it
import json
# to increase password security
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import openai
import sqlite3
import rdflib
import owlrl
import markdown as md
from sanitize_md import SanitizeExtension
import os

app = Flask("AssistOnto")

def load_model_credentials():
  models = app.config.get('MODELS')
  for model_name, data in models.items():
    if data.get('default'):
      app.config['default_model_name'] = model_name
    if isinstance(credentials := data.get('credentials'), dict):
      if credentials_path := credentials['file']:
        with open(os.path.expanduser(credentials_path)) as f:
          models[model_name]['credentials'] = f.read()
      else:
        models[model_name]['credentials'] = None


app.config.from_prefixed_env("ASSISTONTO")
load_model_credentials()
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
)

if app.config.get("PROXY") is not None:
  # see https://flask.palletsprojects.com/en/3.0.x/deploying/proxy_fix/
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)



#### Database

def db_query_db(db, query, args=(), one=False):
  cur = db.execute(query, args)
  rv = cur.fetchall()
  cur.close()
  return (rv[0] if rv else None) if one else rv

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = sqlite3.connect(app.config.get('DB_PATH', 'assistonto.db'))
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
  'ol': [], 'ul': [], 'li': [],
  # 'a':['href'], # unsafe:
  'td': [], 'tr': [], 'th': [], 'table': [],
  'blockquote': [], 'em': [], 'strong': [], 'h1':[], 'h2':[], 'h3':[]
}
app.add_template_global(lambda text: md.markdown(text, extensions=['fenced_code', 'tables', SanitizeExtension(HTML_WHITELIST)]), name='sane_markdown')

#### User configuration

USER_DEFAULT_CONTEXT_SIZE = 3

def user_config(new=None):
  models = [model_name for model_name in app.config.get("MODELS")]
  config = {
    "chosen_model": app.config.get("default_model_name") \
      or next(iter(models)) if models else None,
    "models": models,
    "context_size": USER_DEFAULT_CONTEXT_SIZE,
  }
  if new is None:
    return config
  config.update(new)
  return config


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
  return render_template('register.html')

@app.route('/register', methods=['POST'])
def post_register():
  username = request.form.get('input-username', '')
  email = request.form.get('input-email')
  password = request.form.get('input-password', '')
  invite_token = request.form.get('input-invite-token', '')
  input_valid = True
  if len(username) < 6:
    input_valid = False
    flash("Username should have at least 6 characters", category='warning')
  if len(password) < 6:
    input_valid = False
    flash("Password should have at least 6 characters", category='warning')
  was_invited = query_db("""SELECT TRUE
  FROM invites
  WHERE redeemed IS NULL AND secret = ?""",
                         (invite_token,), one=True)
  if was_invited is None:
    input_valid = False
    flash("Invite token is invalid", category='warning')
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
    cur = db.execute("""UPDATE invites
SET redeemed = unixepoch()
WHERE secret = ?""", (invite_token,))
    if res is not None:
      user_id = res['user_id']
      g._user_id = user_id
      db.commit()
    else:
      db.rollback()
      redirect(url_for('view_register'))
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


@app.route('/settings', methods=["POST"])
@login_required
def post_settings():
  new_model_name = request.form['model']
  models = app.config.get("MODELS")
  config = {}
  ok = True
  if new_model_name not in models:
    ok = False
  else:
    config['chosen_model'] = new_model_name
  if (context_size_str := request.form.get('context_size')) is None \
    or not context_size_str.isdigit():
    ok = False
  else:
    config['context_size'] = int(context_size_str)
  user_id = g._user_id
  # all config values are ok
  if not ok:
    app.logger.info(f'Invalid configuration submitted by {user_id}')
    return '', 204
  db = get_db()
  r = db_query_db(
      db,
      """INSERT INTO settings(user_id, config_json)
      VALUES (:user_id, :config_json)
      ON CONFLICT(user_id) DO UPDATE SET config_json=excluded.config_json
      RETURNING user_id""",
      dict(user_id=user_id, config_json=json.dumps(config)),
      one = True
    )
  if r:
    db.commit()
  else:
    db.rollback()
  return '', 204 # no content -> no swap


USER_CHATS_QUERY = """SELECT id, subject
FROM chats
WHERE user_id = :user_id"""


@app.route('/chat', methods=["GET"])
@app.route('/chat/<int:chat_id>', methods=["GET"])
@login_required
def view_app(chat_id=None):
  db = get_db()
  user_id = g._user_id
  user_chats = db_query_db(
      db, USER_CHATS_QUERY,
      dict(user_id=user_id)
    )
  # app.logger.info(user_chats)
  if chat_id is None or chat_id not in [chat['id'] for chat in user_chats]:
    # No chat specified or unauthorized chat (not owned by user), so
    # get latest chat id, if any
    r = db_query_db(
      db,
      """SELECT chat_id
FROM messages INNER JOIN chats ON messages.chat_id = chats.id
WHERE user_id = :user_id
ORDER BY when_created DESC
LIMIT 1""",
      dict(user_id=user_id),
      one = True
    )
    if r is None:
      # if no chat, create one
      chat_id = chat_new_chat(user_id, db=db)
    else:
      chat_id = r['chat_id']
  session[USER_CHAT_KEY] = chat_id
  r = db_query_db(
      db,
      """SELECT config_json
FROM settings
WHERE user_id = :user_id
LIMIT 1""",
      dict(user_id=user_id),
      one = True
    )
  initial_config = None
  if r:
    initial_config = json.loads(r['config_json'])
  chat_messages = chat_get_context(chat_id, ncontext=app.config.get('MAX_MESSAGES_SHOWN', 100))
  return render_template(
    "app.html",
    username=g._username,
    chat_messages=chat_messages,
    user_chats=user_chats,
    initial_config=user_config(initial_config),
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
    chat_id = res['chat_id']
    return chat_id

def chat_insert_message(chat_id, role, content, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    """INSERT INTO messages(chat_id, user_msg, content, when_created)
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

def chat_delete_message(user_id, message_id, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    f"""UPDATE messages
    SET when_deleted = unixepoch()
    WHERE id = :message_id AND chat_id IN (SELECT id FROM ({USER_CHATS_QUERY}))
    RETURNING id AS message_id""",
    dict(message_id=message_id, user_id=user_id),
    one=True)
  if res is None:
    db.rollback()
  else:
    db.commit()


def chat_get_context(chat_id, ncontext=3, db=None):
  if db is None:
    db = get_db()
  res = db_query_db(
    db,
    """SELECT id, content, user_msg
FROM (SELECT id, content, user_msg, when_created
FROM messages
WHERE chat_id = :chat_id AND when_deleted IS NULL
ORDER BY when_created DESC
LIMIT :ncontext)
ORDER BY when_created ASC""",
    dict(chat_id=chat_id, ncontext=ncontext))
  return res

@app.route('/render-user-message', methods=["POST"])
@login_required
def render_user_message():
  # Called when user sends a message in the interface and we want to
  # render it instantly, without having it saved on the DB (this
  # might not be ideal, however)
  user_message = request.form.get('user_message', None)
  if user_message is None or len(user_message.strip()) == 0:
    return "", 204
  return render_template(
    "user_message.html",
    user_message=user_message
  )

@app.route('/messaged', methods=["POST"])
@login_required
def message_new():
  user_message = request.form.get('user_message', None)
  chosen_model = request.form.get('model', None)
  if user_message is None or len(user_message.strip()) == 0:
    return "", 204 # no swap
  chat_id = session.get(USER_CHAT_KEY)
  if chat_id is None:
    return redirect(url_for('view_app'))
  db = get_db()
  # save user message
  _ = chat_insert_message(chat_id, "user", user_message, db=db)
  # get answer from AI
  models = app.config.get("MODELS", {})
  model = models.get(chosen_model) or models.get(app.config.get("default_model_name")) if models else None
  if model is None:
    flash("No model means we can't have an assistant.", category='error')
    return "Model not found", 500
  api_key = model.get('credentials')
  if api_key is None:
    flash("No API key means we can't contact the assistant.", category='error')
    return "No API key configured", 500
  base_url = model.get('base_url')
  client = openai.OpenAI(
    api_key=api_key,
    base_url=base_url
  )
  ontology = request.form.get('user-ontology', None)
  ontology_message = f"The current ontology is:\n{ontology}" if ontology else ""
  messages = [
    dict(
      role="system",
      content=f"""You are helpful assistant in the domain of CyberSecurity ontologies. You should help the user build and query their ontology. {ontology_message}"""
      )
  ]
  context_size = int(context_size_str) if (context_size_str := request.form.get('context_size')) is not None \
    and context_size_str.isdigit() else USER_DEFAULT_CONTEXT_SIZE
  context_messages = it.dropwhile(
    # remove initial assistant messages since we have to start with
    # user interactions
    lambda m: m['user_msg'] == 0,
    chat_get_context(chat_id, ncontext=context_size, db=db)
  )
  # add context messages without repeated messages (we must have
  # messages following the user/assistant/user order)
  first_msg = next(context_messages)
  messages.append({"role": 'user', "content": first_msg['content']})
  messages.extend([
    dict(role="user" if curr_msg['user_msg'] == 1 else "assistant", content=curr_msg['content'])
    for prev_msg, curr_msg in it.pairwise(it.chain([first_msg], context_messages)) # include first message again or we skip a message
    # don't send two messages from the same person in a row
    if curr_msg['user_msg'] != prev_msg['user_msg']
  ])
  try:
    response = client.chat.completions.create(
      model=model.get('name', chosen_model),
      messages=messages,
      max_tokens=2000
    )
    # TODO: check if response was ok
    assistant_message = response.choices[0].message.content
    assistant_message_id = chat_insert_message(chat_id, "assistant", assistant_message)
    return render_template(
      "assistant_message.html",
      ainame=chosen_model,
      assistant_message=assistant_message,
      assistant_message_id=assistant_message_id,
    )
  except openai.AuthenticationError:
    app.logger.error(f'Could not authenticate with key {api_key[:5]}… to {base_url} (model={model})')
    return render_template('error.html', what="Could not authenticate to LLM server"), 500
  except openai.APITimeoutError:
    app.logger.error('Request to server timed out')
    return render_template('error.html', what="Server timed out"), 500


class NotAuthorized(Exception):
  "Raised when the user does not have the authority to perform some action"
  pass

@app.route('/check-ontology', methods=['POST'])
@login_required
def check_ontology():
  g = rdflib.Graph()
  ontology_str = request.form.get('user-ontology', None)
  if ontology_str is None:
    return '', 204
  g.parse(data=ontology_str)
  owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
  query = """
  prefix ns1: <http://www.daml.org/2002/03/agents/agent-ont#>

  SELECT ?error ?errorMessage
  WHERE {
    ?error a ns1:ErrorMessage .
    ?error ns1:error ?errorMessage .
  }
  """
  inconsistencies = g.query(query)
  return render_template('owl-reasoner-results.html', inconsistencies=inconsistencies)


@app.route('/deleted_message', methods=["GET"])
@login_required
def message_delete():
  message_id = request.args.get('message_id')
  if message_id is None:
    return "", 204 # no swap
  _ = chat_delete_message(g._user_id, message_id)
  return "" # return empty



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
  if db_path is not None:
    app.config['DB_PATH'] = db_path
  return app.run(host=host, port=port, debug=debug_mode)
