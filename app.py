from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, logout_user, login_required
from models import db, Product, User, Cart, CartItem
from flask_migrate import Migrate
from forms import RegistrationForm, LoginForm
from flask_bcrypt import Bcrypt
from datetime import datetime
from flask_login import current_user, login_user
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config['SECRET_KEY'] = 'secret_key_here'
bootstrap = Bootstrap(app)


with app.app_context():
    db.create_all()

@app.route('/')
def index():
    products = Product.query.limit(20).all()
    return render_template('index.html', products=products, current_user=current_user)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, hashed_password=hashed_password, registration_date=datetime.utcnow(), name=form.name.data)

        db.session.add(user)
        db.session.commit()

        flash('Ваш аккаунт был создан! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # if current_user.is_authenticated:
    #     return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.hashed_password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Ошибка входа. Пожалуйста, проверьте email и пароль', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# Маршрут для добавления товара в корзину
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    try:
        # Получаем данные из запроса
        data = request.get_json()
        quantity = data.get('quantity', 1)

        # Проверяем, существует ли корзина пользователя
        user_id = current_user.id  # Ваш код для получения user_id (в данном случае устанавливаем в 1 для примера)
        cart = Cart.query.filter_by(user_id=user_id).first()

        if not cart:
            # Если корзины нет, создаем новую
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()

        # Проверяем, существует ли запись для данного товара в корзине пользователя
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()

        if cart_item:
            # Если запись уже существует, обновляем количество товара
            cart_item.quantity += quantity
        else:
            # Если записи нет, создаем новую запись в корзине пользователя
            cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)

        # Сохраняем изменения в базе данных
        db.session.commit()

        return jsonify({'success': True, 'message': f'Товар {product_id} добавлен в корзину', 'quantity': cart_item.quantity})
    except Exception as e:
        # Обработка ошибок, если не удалось добавить товар в корзину
        return jsonify({'success': False, 'error': str(e)})


# Маршрут для отображения корзины пользователя
@app.route('/my_cart')
@login_required
def my_cart():
    user_id = current_user.id
    cart = Cart.query.filter_by(user_id=user_id).first()

    # if not cart:
    #     flash('Ваша корзина пуста', 'info')
    #     return redirect(url_for('index'))

    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()

    product_data = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        product_data.append({
            'name': product.name,
            'image_url': product.image_url,
            'quantity': cart_item.quantity,
            'total_price': cart_item.quantity * product.price
        })
    return render_template('my_cart.html', product_data=product_data)


if __name__ == '__main__':
    app.run(debug=True)