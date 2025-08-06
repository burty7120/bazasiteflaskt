from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import telegram
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '8f834a6b2c4d3e9f1a2b5c7d9e0f3a2b')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL',
                                                  'postgresql://bazasite_user:cdyCb4lq05384JDrTu18r9NqY1o7XBHJ@dpg-d2995rbe5dus73c3kfeg-a.frankfurt-postgres.render.com/bazasite')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7912466673:AAFTlyieZGWoPXCR03ND_VszDjsF65jsuvY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1402588151')

db = SQLAlchemy(app)
CORS(app)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)


# Models
class Sneaker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    sizes = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sneaker_id = db.Column(db.Integer, db.ForeignKey('sneaker.id'), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    telegram = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    post_office = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db():
    logger.info("Initializing database...")
    try:
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        if 'sneaker' not in existing_tables or 'order' not in existing_tables:
            db.create_all()
            logger.info("Tables created successfully.")
        if Sneaker.query.count() == 0:
            sample_sneakers = [
                Sneaker(name="Nike Air Max 270", image="nike_air_max_270.jpg", sizes="40,41,42,43,44",
                        created_at=datetime.utcnow()),
                Sneaker(name="Adidas Yeezy Boost", image="adidas_yeezy_boost.jpg", sizes="41,42,43,44,45,46",
                        created_at=datetime.utcnow()),
                Sneaker(name="Puma RS-X", image="puma_rs_x.jpg", sizes="40,42,44,46,48", created_at=datetime.utcnow())
            ]
            db.session.bulk_save_objects(sample_sneakers)
            db.session.commit()
            logger.info("Sample sneakers added to database.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


# Initialize database when app starts
with app.app_context():
    init_db()


# API endpoint to get sneakers
@app.route('/api/sneakers', methods=['GET'])
def get_sneakers():
    try:
        sneakers = Sneaker.query.all()
        return jsonify([{
            'id': sneaker.id,
            'name': sneaker.name,
            'image': f"/static/uploads/{sneaker.image}",
            'sizes': sneaker.sizes
        } for sneaker in sneakers])
    except Exception as e:
        logger.error(f"Error in get_sneakers: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Routes
@app.route('/')
def index():
    try:
        sneakers = Sneaker.query.all()
        return render_template('index.html', sneakers=sneakers)
    except Exception as e:
        logger.error(f"Error in index: {e}")
        return render_template('error.html', error='Failed to load sneakers'), 500


@app.route('/profile')
def profile():
    try:
        orders = Order.query.all()
        return render_template('profile.html', orders=orders)
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        return render_template('error.html', error='Failed to load orders'), 500


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        flash('Неправильний логін або пароль')
    return render_template('admin_login.html')


@app.route('/admin/panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            sizes = ','.join([str(i) for i in range(40, 49) if request.form.get(f'size_{i}')])
            file = request.files['image']
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                sneaker = Sneaker(name=name, image=filename, sizes=sizes)
                db.session.add(sneaker)
                db.session.commit()
                flash('Кросівки додано!')
        except Exception as e:
            logger.error(f"Error in admin_panel: {e}")
            flash('Помилка при додаванні кросівок')
    return render_template('admin_panel.html')


@app.route('/order/<int:sneaker_id>', methods=['GET', 'POST'])
def order(sneaker_id):
    try:
        sneaker = Sneaker.query.get_or_404(sneaker_id)
        if request.method == 'POST':
            size = request.form.get('size')
            nickname = request.form.get('nickname')
            telegram = request.form.get('telegram')
            phone = request.form.get('phone')
            post_office = request.form.get('post_office')
            order = Order(sneaker_id=sneaker_id, size=size, nickname=nickname,
                          telegram=telegram, phone=phone, post_office=post_office)
            db.session.add(order)
            db.session.commit()
            message = f"Нове замовлення!\nКросівки: {sneaker.name}\nРозмір: {size}\nНік: {nickname}\nТелеграм: {telegram}\nТелефон: {phone}\nПошта: {post_office}"
            asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
            flash('Замовлення успішно оформлено!')
            return redirect(url_for('profile'))
        return render_template('order.html', sneaker=sneaker)
    except Exception as e:
        logger.error(f"Error in order: {e}")
        return render_template('error.html', error='Failed to process order'), 500


if __name__ == '__main__':
    with app.app_context():
        init_db()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
