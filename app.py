# app.py
import sqlite3
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)


def init_db():
  conn = sqlite3.connect('gym.db')
  cursor = conn.cursor()
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS body_weight (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight REAL NOT NULL
        )
    ''')
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    ''')
  conn.commit()
  conn.close()


def query_db(query, args=(), one=False):
  conn = sqlite3.connect('gym.db')
  conn.row_factory = sqlite3.Row
  cur = conn.cursor()
  cur.execute(query, args)
  rv = cur.fetchall()
  conn.close()
  return (rv[0] if rv else None) if one else rv


@app.route('/')
def index():
  init_db()
  registos = query_db(
      'SELECT date, weight FROM body_weight ORDER BY date ASC LIMIT 30'
  )
  dates = [r['date'] for r in registos]
  weights = [r['weight'] for r in registos]

  workouts = query_db('SELECT * FROM workouts ORDER BY date DESC LIMIT 10')

  return render_template(
      'index.html', dates=dates, weights=weights, workouts=workouts
  )


@app.route('/add_weight', methods=['POST'])
def add_weight():
  date = request.form['date']
  weight = request.form['weight']
  conn = sqlite3.connect('gym.db')
  conn.execute(
      'INSERT INTO body_weight (date, weight) VALUES (?, ?)', (date, weight)
  )
  conn.commit()
  conn.close()
  return redirect(url_for('index'))


@app.route('/add_workout', methods=['POST'])
def add_workout():
  date = request.form['date']
  exercise = request.form['exercise']
  sets = request.form['sets']
  reps = request.form['reps']
  weight = request.form['weight']
  conn = sqlite3.connect('gym.db')
  conn.execute(
      'INSERT INTO workouts (date, exercise, sets, reps, weight) VALUES (?, ?,'
      ' ?, ?, ?)',
      (date, exercise, sets, reps, weight),
  )
  conn.commit()
  conn.close()
  return redirect(url_for('index'))


if __name__ == '__main__':
  init_db()
  app.run(host='0.0.0.0', port=5000)
