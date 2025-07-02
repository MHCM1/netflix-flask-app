
# app.py - Simple Flask Application for CSC 335
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'simple-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_netflix.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Account(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(50), nullable=False)  # Plain text for simplicity
    email = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')

class User(db.Model):
    userid = db.Column(db.Integer, primary_key=True)
    displayname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), db.ForeignKey('account.username'), nullable=False)

class Movies(db.Model):
    movieid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    director = db.Column(db.String(50), nullable=False)
    cast = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    releasedate = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)

class UserRating(db.Model):
    ratingid = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    reviewtext = db.Column(db.Text, nullable=True)
    movieid = db.Column(db.Integer, db.ForeignKey('movies.movieid'), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)

class WatchLater(db.Model):
    listnum = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('user.userid'), nullable=False)
    movieid = db.Column(db.Integer, db.ForeignKey('movies.movieid'), nullable=False)

# Create routes
@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Show all movies on home page
    movies = Movies.query.all()
    return render_template('home.html', movies=movies)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Password check 
        account = Account.query.filter_by(username=username, password=password).first()
        
        if account:
            session['username'] = username
            session['role'] = account.role
            flash(f'Welcome {account.firstname}!')
            return redirect(url_for('home'))
        else:
            flash('Wrong username or password!')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        password = request.form['password']
        displayname = request.form['displayname']
        
        # Check if username already exists
        existing = Account.query.filter_by(username=username).first()
        if existing:
            flash('Username already taken!')
            return render_template('register.html')
        
        # Create new account
        new_account = Account(
            username=username,
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=password,  # Store plain text 
            role='user'
        )
        db.session.add(new_account)
        
        # Create user profile
        new_user = User(
            displayname=displayname,
            username=username
        )
        db.session.add(new_user)
        
        db.session.commit()
        flash('Account created! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/movies')
def movies():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Search
    search = request.args.get('search', '')
    if search:
        movies = Movies.query.filter(Movies.title.contains(search)).all()
    else:
        movies = Movies.query.all()
    
    return render_template('movies.html', movies=movies, search=search)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    movie = Movies.query.get(movie_id)
    if not movie:
        flash('Movie not found!')
        return redirect(url_for('movies'))
    
    # Get current user
    current_user = User.query.filter_by(username=session['username']).first()
    
    # Check if in watchlist
    in_watchlist = WatchLater.query.filter_by(
        userid=current_user.userid, 
        movieid=movie_id
    ).first() is not None
    
    return render_template('movie_detail.html', movie=movie, in_watchlist=in_watchlist)

@app.route('/add_to_watchlist/<int:movie_id>')
def add_to_watchlist(movie_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.filter_by(username=session['username']).first()
    
    # Check if already in watchlist
    existing = WatchLater.query.filter_by(
        userid=current_user.userid,
        movieid=movie_id
    ).first()
    
    if not existing:
        new_item = WatchLater(
            userid=current_user.userid,
            movieid=movie_id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Added to watchlist!')
    else:
        flash('Already in watchlist!')
    
    return redirect(url_for('movie_detail', movie_id=movie_id))

@app.route('/watchlist')
def watchlist():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.filter_by(username=session['username']).first()
    
    # Get watchlist movies
    watchlist_items = db.session.query(Movies).join(WatchLater).filter(
        WatchLater.userid == current_user.userid
    ).all()
    
    return render_template('watchlist.html', movies=watchlist_items)

@app.route('/rate_movie/<int:movie_id>', methods=['POST'])
def rate_movie(movie_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.filter_by(username=session['username']).first()
    score = int(request.form['rating'])
    review = request.form.get('review', '')
    
    # Check if already rated
    existing_rating = UserRating.query.filter_by(
        userid=current_user.userid,
        movieid=movie_id
    ).first()
    
    if existing_rating:
        existing_rating.score = score
        existing_rating.reviewtext = review
        flash('Rating updated!')
    else:
        new_rating = UserRating(
            userid=current_user.userid,
            movieid=movie_id,
            score=score,
            reviewtext=review
        )
        db.session.add(new_rating)
        flash('Rating added!')
    
    db.session.commit()
    return redirect(url_for('movie_detail', movie_id=movie_id))

@app.route('/admin')
def admin():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin only!')
        return redirect(url_for('home'))
    
    total_movies = Movies.query.count()
    total_users = User.query.count()
    
    return render_template('admin.html', total_movies=total_movies, total_users=total_users)

@app.route('/admin/add_movie', methods=['GET', 'POST'])
def add_movie():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin only!')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        new_movie = Movies(
            title=request.form['title'],
            genre=request.form['genre'],
            director=request.form['director'],
            cast=request.form['cast'],
            rating=float(request.form['rating']) if request.form['rating'] else None,
            releasedate=datetime.strptime(request.form['releasedate'], '%Y-%m-%d').date(),
            description=request.form['description']
        )
        
        db.session.add(new_movie)
        db.session.commit()
        flash('Movie added!')
        return redirect(url_for('admin'))
    
    return render_template('add_movie.html')

# Initialize database with sample data
def init_db():
    db.create_all()
    
    # Check if admin exists
    admin = Account.query.filter_by(username='admin').first()
    if not admin:
        # Create admin account
        admin_account = Account(
            username='admin',
            firstname='Admin',
            lastname='User',
            email='admin@netflix.com',
            password='admin',  # Simple password
            role='admin'
        )
        db.session.add(admin_account)
        
        # Add sample movies
        movies = [
            Movies(title='The Matrix', genre='Sci-Fi', director='Wachowski Sisters',
                  cast='Keanu Reeves, Laurence Fishburne', rating=8.7,
                  releasedate=date(1999, 3, 31),
                  description='A computer programmer discovers reality is a simulation.'),
            Movies(title='Inception', genre='Sci-Fi', director='Christopher Nolan',
                  cast='Leonardo DiCaprio, Marion Cotillard', rating=8.8,
                  releasedate=date(2010, 7, 16),
                  description='A thief enters dreams to steal secrets.'),
            Movies(title='The Godfather', genre='Crime', director='Francis Ford Coppola',
                  cast='Marlon Brando, Al Pacino', rating=9.2,
                  releasedate=date(1972, 3, 24),
                  description='The story of a crime family.'),
            Movies(title='Titanic', genre='Romance', director='James Cameron',
                  cast='Leonardo DiCaprio, Kate Winslet', rating=7.8,
                  releasedate=date(1997, 12, 19),
                  description='A love story on the doomed ship.'),
            Movies(title='Avatar', genre='Action', director='James Cameron',
                  cast='Sam Worthington, Zoe Saldana', rating=7.8,
                  releasedate=date(2009, 12, 18),
                  description='Humans explore an alien world.')
        ]
        
        for movie in movies:
            db.session.add(movie)
        
        db.session.commit()
        print("Database initialized with sample data!")

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
