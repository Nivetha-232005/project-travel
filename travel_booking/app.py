"""
Travel Ticket Booking Website - Flask Backend
Complete application with user authentication, ticket booking, and admin panel
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# ===================== DATABASE MODELS =====================

class User(db.Model):
    """User model for registration and login"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Route(db.Model):
    """Travel routes model (Bus, Train, Flight)"""
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    transport_type = db.Column(db.String(50), nullable=False)  # Bus, Train, Flight
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_seats = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    amenities = db.Column(db.String(255), default="")
    rating = db.Column(db.Float, default=4.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='route', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Route {self.source} to {self.destination}>'


class Booking(db.Model):
    """Booking model for user bookings"""
    id = db.Column(db.Integer, primary_key=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    passenger_name = db.Column(db.String(120), nullable=False)
    passenger_email = db.Column(db.String(120), nullable=False)
    passenger_phone = db.Column(db.String(15), nullable=False)
    passenger_age = db.Column(db.Integer, nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Confirmed')  # Confirmed, Cancelled
    payment_status = db.Column(db.String(50), default='Paid')  # Paid, Pending
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    travel_date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Booking {self.booking_ref}>'


class Payment(db.Model):
    """Payment model for transaction history"""
    id = db.Column(db.Integer, primary_key=True)
    booking_ref = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='Card')  # Card, UPI, etc
    transaction_id = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(50), default='Success')  # Success, Failed, Pending
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)


# ===================== AUTHENTICATION ROUTES =====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/buses')
def buses():
    """Bus ticket booking page"""
    return render_template('bus_booking.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')

        # Validation
        if not all([username, email, password, full_name, phone]):
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'error')
            return redirect(url_for('register'))

        # Create new user
        user = User(username=username, email=email, full_name=full_name, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# ===================== SEARCH AND BOOKING ROUTES =====================

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for available routes"""
    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        travel_date = request.form.get('travel_date')
        transport_type = request.form.get('transport_type', 'All')

        # Parse date
        try:
            date_obj = datetime.strptime(travel_date, '%Y-%m-%d')
        except:
            flash('Invalid date format!', 'error')
            return redirect(url_for('index'))

        # Query routes
        query = Route.query.filter_by(source=source, destination=destination)
        
        if transport_type != 'All':
            query = query.filter_by(transport_type=transport_type)

        routes = query.filter(
            Route.departure_time >= date_obj,
            Route.departure_time < date_obj + timedelta(days=1),
            Route.available_seats > 0
        ).all()

        return render_template('search_results.html', 
                             routes=routes, 
                             source=source, 
                             destination=destination,
                             travel_date=travel_date)

    return redirect(url_for('index'))


@app.route('/book/<int:route_id>', methods=['GET', 'POST'])
def book(route_id):
    """Book a ticket"""
    if 'user_id' not in session:
        flash('Please log in to continue booking!', 'warning')
        return redirect(url_for('login'))

    route = Route.query.get(route_id)
    if not route or route.available_seats <= 0:
        flash('Route not available!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        passenger_name = request.form.get('passenger_name')
        passenger_email = request.form.get('passenger_email')
        passenger_phone = request.form.get('passenger_phone')
        passenger_age = request.form.get('passenger_age')
        seat_number = request.form.get('seat_number')

        if not all([passenger_name, passenger_email, passenger_phone, passenger_age, seat_number]):
            flash('All passenger details are required!', 'error')
            return redirect(url_for('book', route_id=route_id))

        # Create booking
        booking_ref = 'TBOOK' + secrets.token_hex(5).upper()
        booking = Booking(
            booking_ref=booking_ref,
            user_id=session['user_id'],
            route_id=route_id,
            passenger_name=passenger_name,
            passenger_email=passenger_email,
            passenger_phone=passenger_phone,
            passenger_age=int(passenger_age),
            seat_number=seat_number,
            price=route.price,
            travel_date=route.departure_time
        )

        # Update available seats
        route.available_seats -= 1

        db.session.add(booking)
        db.session.commit()

        # Store booking_ref in session for payment
        session['booking_ref'] = booking_ref
        session['booking_price'] = route.price

        return redirect(url_for('payment', booking_ref=booking_ref))

    return render_template('booking.html', route=route)


@app.route('/payment/<booking_ref>', methods=['GET', 'POST'])
def payment(booking_ref):
    """Payment page"""
    if 'user_id' not in session:
        flash('Please log in to continue!', 'error')
        return redirect(url_for('login'))

    booking = Booking.query.filter_by(booking_ref=booking_ref).first()
    if not booking or booking.user_id != session['user_id']:
        flash('Booking not found!', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        card_number = request.form.get('card_number')
        cvv = request.form.get('cvv')
        expiry = request.form.get('expiry')

        if not all([card_number, cvv, expiry]):
            flash('All payment details are required!', 'error')
            return redirect(url_for('payment', booking_ref=booking_ref))

        # Simulate payment processing
        transaction_id = 'TXN' + secrets.token_hex(8).upper()
        payment = Payment(
            booking_ref=booking_ref,
            user_id=session['user_id'],
            amount=booking.price,
            payment_method='Credit/Debit Card',
            transaction_id=transaction_id,
            status='Success'
        )

        booking.payment_status = 'Paid'
        db.session.add(payment)
        db.session.commit()

        flash('Payment successful!', 'success')
        return redirect(url_for('confirmation', booking_ref=booking_ref))

    return render_template('payment.html', booking=booking)


@app.route('/confirmation/<booking_ref>')
def confirmation(booking_ref):
    """Booking confirmation page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking = Booking.query.filter_by(booking_ref=booking_ref).first()
    if not booking or booking.user_id != session['user_id']:
        flash('Booking not found!', 'error')
        return redirect(url_for('dashboard'))

    session['booking_success'] = True
    return render_template('confirmation.html', booking=booking)


# ===================== USER DASHBOARD =====================

@app.route('/dashboard')
def dashboard():
    """User dashboard - view bookings and bookings history"""
    if 'user_id' not in session:
        flash('Please log in!', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    upcoming_bookings = Booking.query.filter_by(user_id=session['user_id']).filter(
        Booking.travel_date >= datetime.utcnow()
    ).order_by(Booking.travel_date).all()

    past_bookings = Booking.query.filter_by(user_id=session['user_id']).filter(
        Booking.travel_date < datetime.utcnow()
    ).order_by(Booking.travel_date.desc()).all()

    return render_template('dashboard.html', 
                         user=user, 
                         upcoming_bookings=upcoming_bookings,
                         past_bookings=past_bookings)


@app.route('/booking-details/<booking_ref>')
def booking_details(booking_ref):
    """View detailed booking information"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking = Booking.query.filter_by(booking_ref=booking_ref).first()
    if not booking or booking.user_id != session['user_id']:
        flash('Booking not found!', 'error')
        return redirect(url_for('dashboard'))

    return render_template('booking_details.html', booking=booking)


@app.route('/cancel-booking/<booking_ref>', methods=['POST'])
def cancel_booking(booking_ref):
    """Cancel a booking"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    booking = Booking.query.filter_by(booking_ref=booking_ref).first()
    if not booking or booking.user_id != session['user_id']:
        flash('Booking not found!', 'error')
        return redirect(url_for('dashboard'))

    if booking.travel_date <= datetime.utcnow():
        flash('Cannot cancel past bookings!', 'error')
        return redirect(url_for('booking_details', booking_ref=booking_ref))

    # Cancel booking and refund seat
    booking.status = 'Cancelled'
    booking.route.available_seats += 1

    db.session.commit()
    flash('Booking cancelled successfully. Refund will be processed within 5-7 business days.', 'success')
    return redirect(url_for('dashboard'))


# ===================== ADMIN PANEL =====================

@app.route('/admin')
def admin():
    """Admin dashboard"""
    # Check if admin (simple auth - in production use proper role-based access)
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('index'))

    routes = Route.query.all()
    total_bookings = Booking.query.count()
    total_revenue = db.session.query(db.func.sum(Booking.price)).scalar() or 0

    return render_template('admin.html', 
                         routes=routes, 
                         total_bookings=total_bookings,
                         total_revenue=total_revenue)


@app.route('/admin/add-route', methods=['GET', 'POST'])
def add_route():
    """Add new route"""
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        transport_type = request.form.get('transport_type')
        departure_time = request.form.get('departure_time')
        arrival_time = request.form.get('arrival_time')
        price = request.form.get('price')
        total_seats = request.form.get('total_seats')
        amenities = request.form.get('amenities')

        if not all([source, destination, transport_type, departure_time, arrival_time, price, total_seats]):
            flash('All fields are required!', 'error')
            return redirect(url_for('add_route'))

        try:
            dept_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M')
            arriv_time = datetime.strptime(arrival_time, '%Y-%m-%dT%H:%M')
        except:
            flash('Invalid datetime format!', 'error')
            return redirect(url_for('add_route'))

        # Calculate duration
        duration = arriv_time - dept_time
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        duration_str = f"{hours}h {minutes}m"

        route = Route(
            source=source,
            destination=destination,
            transport_type=transport_type,
            departure_time=dept_time,
            arrival_time=arriv_time,
            duration=duration_str,
            price=float(price),
            total_seats=int(total_seats),
            available_seats=int(total_seats),
            amenities=amenities
        )

        db.session.add(route)
        db.session.commit()

        flash('Route added successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('add_route.html')


@app.route('/admin/edit-route/<int:route_id>', methods=['GET', 'POST'])
def edit_route(route_id):
    """Edit existing route"""
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('index'))

    route = Route.query.get(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('admin'))

    if request.method == 'POST':
        route.source = request.form.get('source')
        route.destination = request.form.get('destination')
        route.transport_type = request.form.get('transport_type')
        route.price = float(request.form.get('price'))
        route.available_seats = int(request.form.get('available_seats'))
        route.amenities = request.form.get('amenities')

        db.session.commit()
        flash('Route updated successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('edit_route.html', route=route)


@app.route('/admin/delete-route/<int:route_id>', methods=['POST'])
def delete_route(route_id):
    """Delete route"""
    if 'user_id' not in session or session.get('username') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('index'))

    route = Route.query.get(route_id)
    if not route:
        flash('Route not found!', 'error')
        return redirect(url_for('admin'))

    db.session.delete(route)
    db.session.commit()

    flash('Route deleted successfully!', 'success')
    return redirect(url_for('admin'))


# ===================== ERROR HANDLERS =====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500


# ===================== DATABASE INITIALIZATION =====================

def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()

        # Check if data already exists
        if User.query.first():
            return

        # Create admin user
        admin = User(
            username='admin',
            email='admin@travelbook.com',
            full_name='Admin User',
            phone='+1234567890'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Create sample routes
        sample_routes = [
            Route(
                source='New York',
                destination='Los Angeles',
                transport_type='Flight',
                departure_time=datetime.now() + timedelta(days=7, hours=10),
                arrival_time=datetime.now() + timedelta(days=7, hours=18),
                duration='5h 30m',
                price=299.99,
                total_seats=180,
                available_seats=45,
                amenities='WiFi, Food Service, Entertainment System',
                rating=4.8
            ),
            Route(
                source='New York',
                destination='Boston',
                transport_type='Bus',
                departure_time=datetime.now() + timedelta(days=3, hours=8),
                arrival_time=datetime.now() + timedelta(days=3, hours=12),
                duration='4h',
                price=49.99,
                total_seats=50,
                available_seats=12,
                amenities='WiFi, AC, USB Charging',
                rating=4.2
            ),
            Route(
                source='New York',
                destination='Philadelphia',
                transport_type='Train',
                departure_time=datetime.now() + timedelta(days=2, hours=14),
                arrival_time=datetime.now() + timedelta(days=2, hours=16),
                duration='2h',
                price=89.99,
                total_seats=300,
                available_seats=78,
                amenities='WiFi, Dining Car, Comfortable Seating',
                rating=4.5
            ),
            Route(
                source='Los Angeles',
                destination='San Francisco',
                transport_type='Flight',
                departure_time=datetime.now() + timedelta(days=5, hours=9),
                arrival_time=datetime.now() + timedelta(days=5, hours=11),
                duration='1h 15m',
                price=149.99,
                total_seats=150,
                available_seats=32,
                amenities='WiFi, Complimentary Beverage',
                rating=4.6
            ),
            Route(
                source='Chicago',
                destination='Denver',
                transport_type='Bus',
                departure_time=datetime.now() + timedelta(days=4, hours=6),
                arrival_time=datetime.now() + timedelta(days=4, hours=18),
                duration='12h',
                price=69.99,
                total_seats=45,
                available_seats=8,
                amenities='WiFi, AC, Onboard Restroom, Recliners',
                rating=3.9
            ),
            Route(
                source='Miami',
                destination='New York',
                transport_type='Flight',
                departure_time=datetime.now() + timedelta(days=6, hours=15),
                arrival_time=datetime.now() + timedelta(days=6, hours=19),
                duration='3h',
                price=199.99,
                total_seats=200,
                available_seats=55,
                amenities='WiFi, Meal Service, Premium Seating',
                rating=4.7
            ),
        ]

        for route in sample_routes:
            db.session.add(route)

        db.session.commit()
        print("Database initialized with sample data!")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
