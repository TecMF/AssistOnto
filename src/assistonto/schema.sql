PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT,
  password TEXT NOT NULL
) STRICT;

CREATE INDEX username_index
ON users(username);

DROP TABLE IF EXISTS chats;
CREATE TABLE chats (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  subject TEXT,
  FOREIGN KEY(user_id)
    REFERENCES users(id)
) STRICT;

CREATE INDEX chats_user_index
ON chats(user_id);

DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  chat_id INTEGER NOT NULL,
  -- is user message: can't use BOOLEAN with strict
  user_msg INTEGER,
  content TEXT NOT NULL,
  when_created INTEGER NOT NULL,
  when_deleted INTEGER,
  FOREIGN KEY(chat_id)
    REFERENCES chats(id)
) STRICT;

CREATE INDEX messages_chat_index
ON messages(chat_id);

DROP TABLE IF EXISTS invites;
CREATE TABLE invites (
  secret TEXT NOT NULL UNIQUE,
  created INTEGER NOT NULL,
  redeemed INTEGER
) STRICT;

--- create invite with
-- INSERT INTO invites(secret, created) VALUES (lower(hex(randomblob(32))), unixepoch()) RETURNING secret;

DROP TABLE IF EXISTS settings;
CREATE TABLE settings (
  user_id INTEGER PRIMARY KEY,
  config_json TEXT NOT NULL,
  FOREIGN KEY(user_id)
    REFERENCES users(id)
) STRICT;
