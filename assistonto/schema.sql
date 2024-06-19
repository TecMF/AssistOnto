PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  email TEXT,
  password TEXT NOT NULL
) STRICT;

DROP TABLE IF EXISTS chats;
CREATE TABLE chats (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  subject TEXT,
  FOREIGN KEY(user_id)
    REFERENCES users(id)
) STRICT;

DROP TABLE IF EXISTS messages;
CREATE TABLE messages (
  id INTEGER PRIMARY KEY,
  chat_id INTEGER NOT NULL,
  -- can't use BOOLEAN with strict
  user_msg INTEGER,
  content TEXT NOT NULL,
  tstamp INTEGER NOT NULL,
  FOREIGN KEY(chat_id)
    REFERENCES chats(id)
) STRICT;

.save assistonto.db
