import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify , session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem, User
import os
import  io
import redis
from PIL import  Image, ImageDraw, ImageFont
from flask import Response


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


# Database setup
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
db_session = DBSession()  # Renamed from session to db_session to avoid conflicts

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)



@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to access this page.', 'error')
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return db_session.query(User).get(user_id)  # Updated to use db_session

#For Approving new Admins
@app.route('/admin/approve_users')
@login_required
def approve_users():
    if current_user.role != 'admin':
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('home'))

    # Query for users who are not approved yet
    pending_users = db_session.query(User).filter_by(is_approved=False).all()
    return render_template('approve_users.html', users=pending_users)


@app.route('/admin/admin_dashboard/<int:user_id>/approve', methods=['POST','GET'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        flash('You must be an admin to approve users.', 'error')
        return redirect(url_for('home'))

    user_to_approve = db_session.query(User).filter_by(id=user_id).one_or_none()
    if user_to_approve:
        user_to_approve.is_approved = True
        db_session.commit()
        flash(f'User {user_to_approve.username} has been approved!', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/admin_dashboard/<int:user_id>/reject', methods=['POST','GET'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        flash('You must be an admin to reject users.', 'error')
        return redirect(url_for('home'))

    user_to_reject = db_session.query(User).filter_by(id=user_id).one_or_none()
    if user_to_reject:
        db_session.delete(user_to_reject)
        db_session.commit()
        flash(f'User {user_to_reject.username} has been rejected and deleted!', 'info')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('restaurants'))

    pending_users = db_session.query(User).filter_by(is_approved=False).all()
    pending_users_count = len(pending_users)
    
    return render_template('admin_dashboard.html', users=pending_users, pending_users_count=pending_users_count)


# For Admins
@app.route('/admin/')
@login_required
def admin():
    restaurants = db_session.query(Restaurant).all()  # Updated to use db_session
    return render_template('admin_restaurants.html', restaurants=restaurants)

@app.route('/restaurants/new/', methods=['GET', 'POST'])
@login_required
def newRestaurant():
    if request.method == 'POST':
        name = request.form.get('name')
        restaurant1 = Restaurant(name=name)
        db_session.add(restaurant1)  # Updated to use db_session
        db_session.commit()
        return redirect(url_for('admin'))

    return render_template('newrestaurant.html')

@app.route('/admin/<int:restaurant_id>/delete/', methods=['POST'])
@login_required
def delete(restaurant_id):

    try:
        itemToDelete = db_session.query(Restaurant).filter_by(id=restaurant_id).one_or_none()  # Updated to use db_session
        if not itemToDelete:
            flash("Restaurant not found.", 'error')
            return redirect(url_for('admin'))

        db_session.delete(itemToDelete)  # Updated to use db_session
        db_session.commit()
        flash("Restaurant Deleted!", 'success')
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('admin'))

from PIL import Image, ImageDraw, ImageFont

def generate_captcha_image(captcha_code):
    # Create a blank image with white background
    width, height = 120, 50
    image = Image.new('RGB', (width, height), color='white')

    # Initialize drawing context
    draw = ImageDraw.Draw(image)


    # Neon color for the text
    neon_color = (0, 0, 255)  # Neon blue
    glow_color = (255, 105, 180,80)  # Semi-transparent green for glow effect
    glow_color2 = (0, 255, 0 , 80)
    # Set font (you can customize the font)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()

    # Calculate the text size using textbbox (recommended method in Pillow 8.0+)
    text_bbox = draw.textbbox((0, 0), captcha_code, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calculate position to center the text
    position = ((width - text_width) // 2, (height - text_height) // 2)

    # Add the CAPTCHA text to the image
     # Create a glowing effect by drawing shadows
    for offset in range(3, 0, -1):  # Draw shadow around the text
        draw.text((position[0] + offset, position[1] + offset), captcha_code, fill=glow_color, font=font)
    # for offset in range(4, 0, -1):  # Draw shadow around the text
    #     draw.text((position[0] + offset, position[1] + offset), captcha_code, fill=glow_color2, font=font)

    # Now draw the actual text on top
    draw.text(position, captcha_code, fill=neon_color, font=font)
    # Optionally, you can add random noise or lines for additional security

    # Return the image
    return image


    
def generate_captcha(length=4, use_digits=True, use_letters=True, use_both=True):
    # Define possible characters for CAPTCHA
    if use_both:
        characters = string.ascii_letters + string.digits  # Both letters and digits
    elif use_digits:
        characters = string.digits  # Only digits
    elif use_letters:
        characters = string.ascii_letters  # Only letters
    else:
        characters = string.digits  # Default to digits if no valid choice
    
    # Generate the CAPTCHA by randomly selecting characters
    captcha_code = ''.join(random.choice(characters) for _ in range(length))
    
    return captcha_code.upper()

@app.route('/captcha_image/')
def captcha_image():
    captcha_code = generate_captcha()
    
    # Save the CAPTCHA text to session
    session['captcha_solution'] = captcha_code
    
    # Generate CAPTCHA image
    image = generate_captcha_image(captcha_code)
    
    # Convert the image to a byte stream
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    
    # Return the image as a response with the correct content type
    return Response(img_io, mimetype='image/png')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    
    if 'captcha_solution' not in session or request.args.get('refresh_captcha'):
        captcha_code = generate_captcha()
        session['captcha_solution'] = captcha_code

    if request.method == 'POST':
    
        username = request.form['username']
        password = request.form['password']
        
        captcha_answer = request.form['captcha']

        # Check CAPTCHA solution
        if captcha_answer != session.get('captcha_solution'):
            flash('Invalid CAPTCHA ! Please try again.', 'error')
            captcha_code = generate_captcha()  # Generate new CAPTCHA if answer is wrong
            session['captcha_solution'] = captcha_code
            return render_template('login.html', captcha=captcha_code)


        # Clear CAPTCHA solution after successful validation
        session.pop('captcha_solution', None)

        # Validate username and password
        user = db_session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if not user.is_approved:
                flash('Your account is pending approval. Please wait for an admin to approve you.', 'warning')
                return redirect(url_for('login'))
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'error')

    captcha_code = session.get('captcha_solution', None)
    return render_template('login.html', captcha=captcha_code)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register/', methods=['GET', 'POST'])
def register():

    if 'captcha_solution' not in session or request.args.get('refresh_captcha'):
        captcha_code = generate_captcha()
        session['captcha_solution'] = captcha_code

    if request.method == 'POST':
        
        username = request.form['username']
        password = request.form['password']

        captcha_answer = request.form['captcha']
        # refresh_captcha = request.method=='GET'? True:False

        # Check CAPTCHA solution
        if captcha_answer != session.get('captcha_solution'):
            flash('Incorrect CAPTCHA. Please try again.', 'error')
            captcha_code = generate_captcha()  # Generate new CAPTCHA if answer is wrong
            session['captcha_solution'] = captcha_code
            return render_template('login.html', captcha=captcha_code)


        # Clear CAPTCHA solution after successful validation
        session.pop('captcha_solution', None)

        # Check if username already exists
        if db_session.query(User).filter_by(username=username).first():  # Updated to use db_session
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password, role='user',is_approved = False)
        db_session.add(new_user)  # Updated to use db_session
        db_session.commit()

        flash('You are Registered! Approval Pending', 'success')
        return redirect(url_for('login'))
    captcha_code = session.get('captcha_solution', None)
    return render_template('register.html', captcha=captcha_code)

@app.route('/admin/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])
@login_required
def newMenuItem(restaurant_id):
    restaurant = db_session.query(Restaurant).filter_by(id=restaurant_id).one()  # Updated to use db_session

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')

        if not name or not price:
            flash('Name and Price are required fields!', 'error')
            return redirect(url_for('newMenuItem', restaurant_id=restaurant_id))

        try:
            price = float(price)
        except ValueError:
            flash('Invalid price value. Please enter a valid number.', 'error')
            return redirect(url_for('newMenuItem', restaurant_id=restaurant_id))

        new_item = MenuItem(
            name=name,
            description=description,
            price=price,
            restaurant_id=restaurant.id
        )

        # Add to db_session and commit to the database
        db_session.add(new_item)  # Updated to use db_session
        db_session.commit()
        flash('New menu item added successfully!', 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant.id))

    return render_template('newmenuitem.html', restaurant=restaurant)

@app.route('/admin/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET', 'POST'])
@login_required
def editMenuItem(restaurant_id, menu_id):    
    editedItem = db_session.query(MenuItem).filter_by(id=menu_id).one()  # Updated to use db_session
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        db_session.add(editedItem)  # Updated to use db_session
        db_session.commit()
        flash('Menu item edited successfully!', 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)

@app.route('/admin/<int:restaurant_id>/<int:menu_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteMenuItem(restaurant_id, menu_id):
    itemToDelete = db_session.query(MenuItem).filter_by(id=menu_id).one()  # Updated to use db_session
    if request.method == 'POST':
        db_session.delete(itemToDelete)  # Updated to use db_session
        db_session.commit()
        flash("Item Deleted!", 'success')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deletemenuitem.html', item=itemToDelete)

# For Users
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/restaurants/')
def restaurants():
    restaurants = db_session.query(Restaurant).all()  # Updated to use db_session
    return render_template('restaurants.html', restaurants=restaurants)

@app.route('/restaurants/JSON/')
def restaurantsJSON():
    restaurants = db_session.query(Restaurant).all()  # Updated to use db_session
    return jsonify(RestaurantNames=[i.serialize() for i in restaurants])

@app.route('/restaurants/<int:restaurant_id>/')
def UserMenu(restaurant_id):
    restaurant = db_session.query(Restaurant).filter_by(id=restaurant_id).one()  # Updated to use db_session
    items = db_session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()  # Updated to use db_session
    return render_template('user_menu.html', restaurant=restaurant, items=items)

@app.route('/restaurants/<int:restaurant_id>/usermenu/')
def restaurantMenu(restaurant_id):
    restaurant = db_session.query(Restaurant).filter_by(id=restaurant_id).one()  # Updated to use db_session
    items = db_session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()  # Updated to use db_session
    return render_template('menu.html', restaurant=restaurant, items=items)

@app.route('/restaurants/<int:restaurant_id>/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = db_session.query(Restaurant).filter_by(id=restaurant_id).one()  # Updated to use db_session
    items = db_session.query(MenuItem).filter_by(restaurant_id=restaurant.id).all()  # Updated to use db_session
    return jsonify(MenuItems=[i.serialize() for i in items])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8085)