from flask import Flask, render_template, request, redirect, request, url_for, session
from flask_mysqldb import MySQL, MySQLdb
import bcrypt
from jinja2 import Undefined
import requests
import json
from pprint import pprint
from datetime import datetime
import pytz


app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'rw-cek-resi'
app.config['SECRET_KEY'] = 'gbfg[bpfgbfgbkfgbjgbfgbghj'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# datetime Indonesia
now = datetime.now()
idTime = now.astimezone(pytz.timezone('Asia/Jakarta')).strftime("%d/%m/%Y %H:%M:%S")

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

        if user:
            if bcrypt.hashpw(password, user["password"].encode('utf-8')) == user["password"].encode('utf-8'):
                session['id'] = user['id']
                session['name'] = user['name']
                session['email'] = user['email']
                return redirect(url_for('index'))
            else:
                error = "Email & password doesn't match"
                return render_template('login.html', error=error)
        else:
            error = "User not found"
            return render_template('login.html', error=error)
    if request.method == 'GET' and 'name' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for('main'))

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",(name,email,hash_password,))
        mysql.connection.commit()
        
        return redirect(url_for('login'))
        
    if request.method == 'GET' and 'name' in session:
        return redirect(url_for('index'))

    return render_template("register.html")
    
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

        # check has checked resi
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM history_user WHERE no_resi=%s AND visibility='YES'", [awb])
        resi = cur.fetchone()
        cur.close()

        if resi:
            if 'errorTrack' in session:
                session.pop('errorTrack', Undefined)

            data = resi['data']
            data = data.replace("\'", "\"")
            data = json.loads(data)

            track = data['data']['summary']
            detail = data['data']['detail']
            history = data['data']['history']

            session['track'] = track
            session['detail'] = detail
            session['history'] = history

            return redirect(url_for('index'))

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

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO history_user (no_resi, user_id, data, time) VALUES (%s, %s, %s, %s)", (session['track']['awb'], session['id'], json_data, idTime))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('index'))

    return redirect(url_for('login'))

@app.route('/profile', methods=['POST','GET'])
def profile():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        # mencari data user yang sedang login
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", [session['email']])
        user = cur.fetchone()
        cur.close()

        # jika password ingin diubah / form password ada isi
        if old_password != '':
            
            # dilakukan encode ke utf-8 agar bisa dilakukan pengecekan
            old_password = request.form['old_password'].encode('utf-8')

            # pengecekan apakah old password sama dengan password yang ada di database
            if bcrypt.hashpw(old_password, user["password"].encode('utf-8')) == user["password"].encode('utf-8') and new_password != '':
                # jika sama maka form new_password akan dienkripsi
                new_password = request.form['new_password'].encode('utf-8')
                hash_password = bcrypt.hashpw(new_password, bcrypt.gensalt())

                # semua form (name, email, password) akan dimasukkan ke database
                cur = mysql.connection.cursor()
                cur.execute("UPDATE users SET name=%s, email=%s, password=%s WHERE email=%s", (name, email, hash_password, session['email']))
                mysql.connection.commit()
                cur.close()

                # session baru diberikan
                session['name'] = name
                session['email'] = email

                success = "Data has been updated"

                return render_template('profile.html', success=success)
            # jika password old_password salah atau form password baru kosong
            error = 'The old password is wrong or the new password is blank!'
            return render_template('profile.html', error=error)

        # jika yang akan diubah hanya nama dan email atau salah satunya
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET name=%s, email=%s WHERE email=%s", (name, email, user['email']))
        mysql.connection.commit()
        cur.close()


        session['name'] = name
        session['email'] = email

        success = "Data has been updated"

        return render_template('profile.html', success=success)
    else:
        return render_template('profile.html')

@app.route("/history", methods=['GET'])
def history():
    if 'name' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM history_user INNER JOIN users ON history_user.user_id = users.id")
        history = cur.fetchall()
        cur.close()

        return render_template("history.html", histories=history)

    return redirect(url_for('main'))


@app.route("/history/<noresi>", methods=['GET'])
def historyDetails(noresi):
    if 'name' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM history_user WHERE no_resi=%s AND visibility='YES'", [noresi])
        resi = cur.fetchone()
        cur.close()

        if resi:
            data = resi['data']
            data = data.replace("\'", "\"")
            data = json.loads(data)

            track = data['data']['summary']
            detail = data['data']['detail']
            history = data['data']['history']

            return render_template('history-details.html', track=track,detail=detail,histories=history)


    return redirect(url_for('main'))

@app.route('/trash/<noresi>')
def trash(noresi):
    if 'name' in session:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE history_user SET visibility='NO' WHERE no_resi=%s", [noresi])
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('history'))

    return redirect(url_for('index'))



@app.route("/delete", methods=['POST'])
def delete():

    if 'delete' in request.form:
        # mencari data user yang sedang login
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", [session['email']])
        user = cur.fetchone()
        cur.close()

        # lakukan delete
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM users WHERE email=%s", [user['email']])
        mysql.connection.commit()
        cur.close()

        session.clear()
        return redirect(url_for('main'))
    else:
        session['error'] = "Please tick on 'Delete my data' !"
        return redirect(url_for('profile'))

@app.route('/clear-track')
def clearTrack():
    session.pop('track', Undefined)
    session.pop('errorTrack', Undefined)
    return redirect(url_for('index'))

if __name__=="__main__":
    app.run(debug=True)

