from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
   from flask_sqlalchemy import SQLAlchemy
   from flask_cors import CORS
   from werkzeug.utils import secure_filename
   import os
   from datetime import datetime
   import telegram
   import asyncio

   app = Flask(__name__)
   app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '8f834a6b2c4d3e9f1a2b5c7d9e0f3a2b')
   app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://bazasite_user:cdyCb4lq05384JDrTu18r9NqY1o7XBHJ@dpg-d2995rbe5dus73c3kfeg-a.frankfurt-postgres.render.com/bazasite')
   app.config['UPLOAD_FOLDER'] = 'static/uploads'
   app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
   TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7912466673:AAFTlyieZGWoPXCR03ND_VszDjsF65jsuvY')
   TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1402588151')
   app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable warnings

   db = SQLAlchemy(app)
   CORS(app)  # Enable CORS for frontend
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
       inspector = db.inspect(db.engine)
       existing_tables = inspector.get_table_names()
       if 'sneaker' not in existing_tables or 'order' not in existing_tables:
           db.create_all()
           print("Tables created successfully.")
       if Sneaker.query.count() == 0:
           sample_sneakers = [
               Sneaker(name="Nike Air Max 270", image="nike_air_max_270.jpg", sizes="40,41,42,43,44", created_at=datetime.utcnow()),
               Sneaker(name="Adidas Yeezy Boost", image="adidas_yeezy_boost.jpg", sizes="41,42,43,44,45,46", created_at=datetime.utcnow()),
               Sneaker(name="Puma RS-X", image="puma_rs_x.jpg", sizes="40,42,44,46,48", created_at=datetime.utcnow())
           ]
           db.session.bulk_save_objects(sample_sneakers)
           db.session.commit()
           print("Sample sneakers added to database.")

   # API endpoint to get sneakers
   @app.route('/api/sneakers', methods=['GET'])
   def get_sneakers():
       sneakers = Sneaker.query.all()
       return jsonify([{
           'id': sneaker.id,
           'name': sneaker.name,
           'image': f"/static/uploads/{sneaker.image}",
           'sizes': sneaker.sizes
       } for sneaker in sneakers])

   # Routes
   @app.route('/')
   def index():
       sneakers = Sneaker.query.all()
       return render_template('index.html', sneakers=sneakers)

   @app.route('/profile')
   def profile():
       orders = Order.query.all()
       return render_template('profile.html', orders=orders)

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
       return render_template('admin_panel.html')

   @app.route('/order/<int:sneaker_id>', methods=['GET', 'POST'])
   def order(sneaker_id):
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

   if __name__ == '__main__':
       with app.app_context():
           init_db()
       port = int(os.getenv('PORT', 5000))
       app.run(host='0.0.0.0', port=port, debug=True)
