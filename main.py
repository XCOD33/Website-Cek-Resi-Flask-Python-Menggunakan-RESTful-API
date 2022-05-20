from flask import Flask, render_template, request, redirect, request, url_for, session
from flask_mysqldb import MySQL, MySQLdb
import bcrypt
from jinja2 import Undefined
import mysql.connector
import requests
import json

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'rw-cek-resi'
app.config['SECRET_KEY'] = 'gbfg[bpfgbfgbkfgbjgbfgbghj'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


@app.route('/')
def main():
    return render_template('home.html')

@app.route('/login', methods = ["GET","POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        curl.execute("SELECT * FROM users WHERE email=%s",(email,))
        user = curl.fetchone()
        curl.close()

        if len(user) > 0:
            if bcrypt.hashpw(password, user["password"].encode('utf-8')) == user["password"].encode('utf-8'):
                session['name'] = user['name']
                session['email'] = user['email']
                return redirect(url_for('index'))
            else:
                return "Error user not found"
        else:
            return "Error user not found"
    else:
        return render_template('login.html')

@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for('main'))

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",(name,email,hash_password,))
        mysql.connection.commit()
        session['name'] = request.form['name']
        session['email'] = request.form['email']
        return redirect(url_for('login'))
    
###index
@app.route('/index', methods = ['POST', 'GET'])
def index():
    if request.method == 'GET' and 'name' in session:
        api = requests.get('https://api.binderbyte.com/v1/list_courier?api_key=3af0284cc24c7ac90e374cdb6abb62dcb2753e882bfa02db2f7b0289f27938c3')
        data = api.content
        json_data = json.loads(data)
        
        return render_template('index.html', courierLists = json_data)

    if request.method == 'POST':
        courier = request.form["courier"]
        awb = request.form["awb"]

        api = f'https://api.binderbyte.com/v1/track?api_key=3af0284cc24c7ac90e374cdb6abb62dcb2753e882bfa02db2f7b0289f27938c3&courier={courier}&awb={awb}'
        req = requests.get(api)

        data = req.content
        json_data = json.loads(data)

        if json_data['status'] == 400:
            session['errorTrack'] = 'Nomor resi tidak valid !'

            if 'track' in session:
                session.pop('track', Undefined)

            return redirect(url_for('index'))

        track = json_data['data']['summary']
        detail = json_data['data']['detail']
        history = json_data['data']['history']

        session['track'] = track
        session['detail'] = detail
        session['history'] = history

        if 'errorTrack' in session:
            session.pop('errorTrack', Undefined)

        return redirect(url_for('index'))

    return redirect(url_for('login'))

@app.route('/clear-track')
def clearTrack():
    session.pop('track', Undefined)
    session.pop('errorTrack', Undefined)
    return redirect(url_for('index'))

if __name__=="__main__":
    app.run(debug = True)
