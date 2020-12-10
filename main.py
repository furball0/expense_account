import os
import numpy as np
import pytesseract
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from text_recognition import *

currentdirectory = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
# Secret key for sessions encryption
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Таблица для краткой информации о чеке
class receipts_main(db.Model):
    # global uname_main
    id = db.Column(db.Integer, primary_key=True)
    market_names = db.Column(db.Text)
    dates = db.Column(db.Text)
    results = db.Column(db.Float)
    uname_main = db.Column(db.Text)

    def __repr__(self):
        return '<receipts_main %r>' % self.id

# Таблица для информации о чеке
class receipts_info(db.Model):
    id = db.Column(db.Integer)
    products = db.Column(db.Text)
    price = db.Column(db.Float)
    quantity = db.Column(db.Float)
    costs = db.Column(db.Float)
    id2 = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return '<receipts_info %r>' % self.id

# Таблица для регистарции
class user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    password = db.Column(db.String(80))


@app.route('/')
def home():
    if 'userLogged' not in session:
        flash('You need to log in to use the website',
              category='alert alert-info')
        return render_template("first.html", title="ExpenseAccounting")
    return render_template("index.html", title="Expense Accounting")


@ app.route('/scanner', methods=['GET', 'POST'])
def scan_file():
    if 'userLogged' in session:
        try:
            if request.method == 'POST':
                image_data = request.files['file'].read()
                file_bytes = np.asarray(bytearray(image_data), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                img_preprocces = preprocessing(img)
                scanned_text = pytesseract.image_to_string(
                    img_preprocces, config='--psm 6', lang='rus+eng')
                print(scanned_text)
                receipt_ocr = data_find(scanned_text)

                session['data'] = {
                    "text": scanned_text
                }
                data_upload(receipt_ocr, currentdirectory,
                            session['userLogged'])

                return redirect(url_for('result'))
        except:
            return render_template(
                "result_error.html"
            )
    else:
        return redirect(url_for('home'))


@app.route('/stats', methods=['GET', 'POST'])
def stats():
    receipt_info = receipts_info.query.all()
    receipt_main = receipts_main.query.order_by(
        receipts_main.dates.desc()).filter_by(uname_main=session['userLogged']).all()
    return render_template("stats.html", title='Статистика', receipt_info=receipt_info, receipt_main=receipt_main)


@app.route('/stats/<int:id>', methods=['GET', 'POST'])
def stats_sort(id):
    receipt_info = receipts_info.query.all()
    if id == 1:
        receipt_main = receipts_main.query.order_by(
            receipts_main.dates.desc()).filter_by(uname_main=session['userLogged']).all()
    elif id == 2:
        receipt_main = receipts_main.query.order_by(
            receipts_main.dates).filter_by(uname_main=session['userLogged']).all()
    elif id == 3:
        receipt_main = receipts_main.query.order_by(
            receipts_main.market_names).filter_by(uname_main=session['userLogged']).all()
    elif id == 4:
        receipt_main = receipts_main.query.order_by(
            receipts_main.market_names.desc()).filter_by(uname_main=session['userLogged']).all()
    return render_template("stats.html", title='Статистика', receipt_info=receipt_info, receipt_main=receipt_main)


@app.route('/stat/<int:id>', methods=['GET', 'POST'])
def stat_detail(id):
    receipt_info = receipts_info.query.filter_by(id=id).all()
    receipt_main = receipts_main.query.filter_by(id=id).all()
    return render_template("stat_detail.html", receipt_main=receipt_main, receipt_info=receipt_info, title='Статистика')


@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if 'userLogged' in session:
            flash('You are already authorized.', category='flash alert alert-success')
            return redirect(url_for('home'))
        elif request.method == "POST":
            uname = request.form["uname"]
            passw = request.form["passw"]
            login = user.query.filter_by(
                username=uname, password=passw).first()
            if login is not None:
                session['userLogged'] = request.form['uname']
                flash('Successful authorization.',
                      category='flash alert alert-success')
                return redirect(url_for('home'))
            flash('Incorrect login or password.',
                  category='flash alert alert-danger')
        return render_template("login.html", title='Авторизация')
    except:
        return render_template("error.html", title='Ошибка')


@app.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "POST":
            uname = request.form['uname']
            mail = request.form['mail']
            passw = request.form['passw']
            # Проверяем, есть ли такой логин в БД
            login_1 = user.query.filter_by(username=uname).first()
            if login_1 is not None:
                flash('This login is used', category='flash alert alert-danger')
                return render_template("register.html")
            register = user(username=uname, email=mail, password=passw)
            db.session.add(register)
            db.session.commit()

            if 'userLogged' in session:
                flash('Account successfully created',
                      category='flash alert alert-success')
                return redirect(url_for('home'))
            else:
                flash('Account successfully created',
                      category='flash alert alert-success')
                return redirect(url_for('login'))
        return render_template("register.html")
    except:
        return render_template("error.html")


@app.route('/logout', methods=["GET", "POST"])
def logout():
    if 'userLogged' in session:
        del session['userLogged']
        flash('Signing out of an account', category='flash alert alert-success')
        return redirect(url_for('home'))
    else:
        flash('You are not logged in', category='flash alert alert-success')
        return render_template("first.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/result')
def result():
    if "data" in session:
        data = session['data']
        return render_template(
            "result.html",
            title="Result",
            text=data["text"])
    else:
        return "Wrong request method."


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page404.html', title="Страница не найдена")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4567)
