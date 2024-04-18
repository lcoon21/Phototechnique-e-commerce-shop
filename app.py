from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, logout_user, login_required
from models import db, Product, User, Cart, CartItem, Order, OrderItem, Category
from flask_migrate import Migrate
from forms import RegistrationForm, LoginForm, OrderForm
from flask_bcrypt import Bcrypt
from datetime import datetime
from flask_login import current_user, login_user
from flask_bootstrap import Bootstrap
from flask_admin import Admin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db.init_app(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config['SECRET_KEY'] = 'secret_key_here'
bootstrap = Bootstrap(app)
from flask_admin.contrib.sqla import ModelView


with app.app_context():
    db.create_all()


admin = Admin(app, name='Админ-панель', template_mode='bootstrap3')

class ProductView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    form_columns = ['name', 'price', 'description', 'category_id', 'image_url']
    column_list = ('id', 'name', 'price', 'description', 'category_id', 'image_url')

admin.add_view(ProductView(Product, db.session))

admin.add_view(ModelView(User, db.session))
class CartView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    form_columns = ['user_id']
    column_list = ('id', 'user_id')

admin.add_view(CartView(Cart, db.session))

class CartItemView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    form_columns = ['quantity', 'cart_id', 'product_id']
    column_list = ('id', 'quantity', 'cart_id', 'product_id')

admin.add_view(CartItemView(CartItem, db.session))

class OrderView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    form_columns = ['user_id', 'total_price', 'created_at']
    column_list = ('id', 'user_id', 'total_price', 'created_at')

admin.add_view(OrderView(Order, db.session))

class OrderItemView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    form_columns = ['order_id', 'product_id', 'quantity']
    column_list = ('id', 'order_id', 'product_id', 'quantity')

admin.add_view(OrderItemView(OrderItem, db.session))

admin.add_view(ModelView(Category, db.session))


@app.route('/')
def index():
    products = Product.query.limit(20).all()
    categories = Category.query.all()
    return render_template('index.html', products=products, current_user=current_user, categories=categories)


@app.route('/category/<int:category_id>')
def category(category_id):
    # Fetch the category and its products from the database
    category = Category.query.get(category_id)
    categories = Category.query.all()

    products = Product.query.filter_by(category_id=category.id).all()

    # Render the template with the category and its products
    return render_template('index.html', category=category, products=products, categories=categories)


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
        cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first() #################

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

    if cart:
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
    else:
        return render_template('index.html')

    product_data = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        product_data.append({
            'name': product.name,
            'image_url': product.image_url,
            'quantity': cart_item.quantity,
            'product_price': product.price,
            'total_price': cart_item.quantity * product.price,
            'cart_item_id': cart_item.id
        })
    return render_template('my_cart.html', product_data=product_data)


@app.route('/update_quantity/<int:cart_item_id>/<int:new_quantity>', methods=['POST'])
@login_required
def update_quantity(cart_item_id, new_quantity):
    try:
        cart_item = CartItem.query.get_or_404(cart_item_id)

        cart_item.quantity = new_quantity
        db.session.commit()

        return jsonify({'success': True, 'message': 'Quantity updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/remove_item/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_item(cart_item_id):
    try:
        # Найдем запись о товаре в корзине
        cart_item = CartItem.query.get_or_404(cart_item_id)

        # Удалим запись о товаре из корзины
        db.session.delete(cart_item)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Товар успешно удален из корзины'})

    except Exception as e:
        print(e)
        return jsonify({'success': False, 'message': 'Произошла ошибка сервера'}), 500


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout_form():
    form = OrderForm()

    if request.method == 'POST':
        name = form.name.data
        address = form.address.data
        phone = form.phone.data

        # Создание нового заказа
        new_order = Order(user_id=current_user.id, total_price=0)  # Подставьте свой способ расчета общей стоимости
        db.session.add(new_order)
        db.session.commit()

        user_cart = Cart.query.filter_by(user_id=current_user.id).first()
        cart_items = CartItem.query.filter_by(cart_id=user_cart.id)

        total_price = 0

        for i in cart_items:
            product_=Product.query.filter_by(id=i.product_id).first()
            print(product_)
            total_price=total_price + (i.quantity*product_.price)

        # Перебор товаров в корзине и создание соответствующих записей OrderItem
        for product_item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product_item.product_id,
                quantity=product_item.quantity
            )
            db.session.add(order_item)

        # order=Order.query.filter_by(user_id=current_user.id).last()
        new_order.total_price=total_price

        db.session.commit()

        for cart_item in cart_items:
            db.session.delete(cart_item)
        db.session.delete(user_cart)

        db.session.commit()

        return render_template('order_confirmation.html',
                               order=new_order)  # Перенаправление на страницу подтверждения заказа с информацией о заказе

    return render_template('checkout_form.html', form=form)


@app.route('/delivery', methods=['GET'])
def delivery():
    return render_template('delivery.html')

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)