from flask import Flask, request, render_template, redirect
from flask.ext.bootstrap import Bootstrap # Because bootstrap == <3
from flask.ext.sqlalchemy import SQLAlchemy
from flask_wtf import Form 
from wtforms import StringField, TextField, validators
from wtforms.validators import DataRequired
from flask.ext.security import current_user, Security, SQLAlchemyUserDatastore, \
    LoginForm, RegisterForm, UserMixin, RoleMixin, login_required
from flask_security.forms import RegisterForm
from flask_mail import Mail
from datetime import datetime
import wikipedia

def create_app():
    app = Flask(__name__)
    Bootstrap(app)
    return app

app = create_app()

# Config
SECRET_KEY = 'SECRET_KEY_HERE'
URI = 'oracle://USER:PASSWORD@oracle.cise.ufl.edu:1521/orcl'
app.config['SECRET_KEY'] = 'SECRET_KEY_HERE'
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
app.config['SECURITY_PASSWORD_SALT'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = URI

# Mail Config
app.config['MAIL_SERVER'] = 'smtp.servername.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'USERNAME'
app.config['MAIL_PASSWORD'] = 'PASSWORD'
mail = Mail(app)

# Create database connection object
db = SQLAlchemy(app)

roles_users = db.Table('roles_users',
        db.Column('user_id', db.String(80), db.ForeignKey('users.id')),
        db.Column('role_id', db.String(80), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.String(80), primary_key=True)
    description = db.Column(db.String(255))

class Users(db.Model, UserMixin):
    id = db.Column(db.String(80), primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    # confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

# Create the user and role tables.
db.create_all()

def _get_date():
    return datetime.now()

class Music(db.Model):
    id = db.Column('SONGID',
                   db.String(18),
                   primary_key = True)
    song = db.Column('SONG', db.String(200))
    artist = db.Column('ARTIST', db.String(200))
    year = db.Column('YEAR', db.Integer)

class Tags(db.Model):
    name = db.Column('TAGNAME',
                     db.String(200),
                     primary_key = True)
    color = db.Column('TAGCOLOR', db.String(7))

    def __init__(self, name, color):
        self.name = name
        self.color = color
    
class Tagmap(db.Model):
    tag_name = db.Column('TAGNAME',
                         db.String(200),
                         primary_key=True)
    username = db.Column('USERNAME',
                         db.String(80),
                         primary_key=True)
    song_id = db.Column('SONGID',
                        db.String(18),
                        primary_key=True)
    artist = db.Column('ARTIST',
                       db.String(200),
                       primary_key=True)
    date_created = db.Column('DATECREATED', db.Date, default=_get_date())

    def __init__(self, tag_name, username, artist, song_id):
        self.tag_name = tag_name
        self.username = username
        self.artist = artist
        self.song_id = song_id

class ExtendedRegisterForm(RegisterForm):
    id = TextField('Username', validators=[DataRequired()])
    
# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, Users, Role)
security = Security(app, user_datastore, register_form = ExtendedRegisterForm)
    
class SearchForm(Form):
    query = StringField('query', validators=[DataRequired()])

class TagForm(Form):
    tag = StringField('tag', validators=[DataRequired()])

@app.errorhandler(500)
def internal_error(error):
    return render_template('tag_failed.html'), 500
    
# Home page
@app.route('/', methods=('GET', 'POST'))
def index():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"] )
    return render_template('index.html', form=form)

@app.route('/user/<name>', methods=('GET', 'POST'))
def user(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"] )
    username = Users.query.filter_by(id = name).first()
    if username is not None:
        tag_result = db.session.query( Tagmap.tag_name, Tagmap.username,
                                       Tagmap.song_id, Tagmap.artist,
                                       Tagmap.date_created, Music.song ) \
                          .filter( Tagmap.username == name ) \
                          .outerjoin(Music, (Music.id == Tagmap.song_id)) \
                          .all()
        count = len(tag_result)
        return render_template('user.html', name=name, tag_result=tag_result,
                               form=form, count=count)
    # 404 if the user doesn't exist.
    else:
        error_type = 'User'
        return render_template('404.html', error_type=error_type, form=form), 404

@app.route('/users', methods=('GET', 'POST'))
def users():
    form = SearchForm()
    user_result = db.session.query( Users.id ).all()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"] )
    return render_template('users.html', user_result = user_result, form=form)

@app.route('/popular', methods=('GET', 'POST'))
def popular():
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"] )
    tag_result = db.session.query( Tagmap.tag_name,
                                   db.func.count(Tagmap.tag_name) \
                                   .label('tag_count')) \
                           .group_by( Tagmap.tag_name ) \
                           .order_by(db.func.count(Tagmap.tag_name).desc()) \
                           .limit(20).all()
    print tag_result[0]._fields
    return render_template('popular.html', form=form, tag_result=tag_result)

@app.route('/artist/<name>', methods=('GET', 'POST'))
def artist(name):
    form = SearchForm()
    tagform = TagForm()
    artist_result = db.session.query( Music.artist, Music.song, Music.year ) \
                              .distinct().order_by(Music.year) \
                              .filter(db.func.lower(Music.artist) ==
                                      db.func.lower(name)).all()
    tag_result = db.session.query( Tagmap.tag_name, Tagmap.artist ) \
                           .filter(db.func.lower(Tagmap.artist) ==
                                   db.func.lower(name)) \
                           .filter(Tagmap.song_id == 'artist_tag').all()
    if len(artist_result) is 0:
        error_type = 'Artist'
        return render_template('404.html', error_type=error_type), 404
    if tagform.validate_on_submit():
        tag = db.session.query( Tags.name ) \
                        .filter(db.func.lower(Tags.name) ==
                                db.func.lower(request.form["tag"])).first()
        if tag is not None:
            tagmap = Tagmap(tag.name, current_user.id,
                            artist_result[0].artist, 'artist_tag')
            db.session.add(tagmap)
            db.session.commit()
            return render_template('tag_created.html', form=form)
        else:
            tagentry = Tags(request.form["tag"], '#000000')
            tagmap = Tagmap(request.form["tag"], current_user.id,
                            artist_result[0].artist, 'artist_tag')
            db.session.add(tagentry)
            db.session.add(tagmap)
            db.session.commit()
            return render_template('tag_created.html', form=form)
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"] )
    return render_template('artist.html', artist_result=artist_result,
                           tag_result=tag_result, form=form, tagform=tagform)

@app.route('/search/year/<name>', methods=('GET', 'POST'))
def year(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    name = int(name)
    year_result = db.session.query( Music.artist, Music.song ) \
                            .distinct().order_by(Music.artist) \
                                       .filter_by(year = name).all()
    if len(year_result) is 0:
        error_type = 'Year'
        return render_template('404.html', error_type=error_type), 404
    return render_template('year.html', year_result=year_result,
                           name=name, form=form)

@app.route('/tag/<name>', methods=('GET', 'POST'))
def tag(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    tag = db.session.query(Tags.name).filter(db.func.lower(Tags.name) == db.func.lower(name)).first()
    tag_info = wikipedia.summary(tag.name)
    tag_url = wikipedia.page(tag.name).url
    tag_result = db.session.query( Tagmap.tag_name, Tagmap.username,
                                   Tagmap.song_id, Tagmap.artist,
                                   Tagmap.date_created, Music.song ) \
                           .filter( Tagmap.tag_name == name ) \
                           .outerjoin(Music, (Music.id == Tagmap.song_id)) \
                           .all()
    if tag is not None:
        return render_template('tag.html', tag=tag, tag_info = tag_info,
                               tag_url = tag_url, tag_result=tag_result,
                               form=form)
    # 404 if the user doesn't exist.
    else:
        error_type = 'Tag'
        return render_template('404.html', error_type=error_type, form=form), 404    

@app.route('/song/<artist>/<name>', methods=('GET', 'POST'))
def song(artist, name):
    form = SearchForm()
    tagform = TagForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    song_result = db.session.query( Music.id, Music.artist, Music.song,
                                    Music.year ).order_by(Music.id) \
                            .filter(db.func.lower(Music.song) ==
                                    db.func.lower(name)) \
                            .filter(db.func.lower(Music.artist) ==
                                    db.func.lower(artist)).first()

    tag_result = db.session.query( Tagmap.tag_name ) \
                           .filter(Tagmap.song_id == song_result.id).all()
    
    if song_result is None:
        error_type = 'Song'
        return render_template('404.html', error_type=error_type), 404

    if tagform.validate_on_submit():
        tag = db.session.query( Tags.name ) \
                        .filter(db.func.lower(Tags.name) ==
                                db.func.lower(request.form["tag"])).first()
        if tag is not None:
            tagmap = Tagmap(tag.name, current_user.id,
                            song_result.artist, song_result.id)
            db.session.add(tagmap)
            db.session.commit()
            return render_template('tag_created.html', form=form)
        else:
            tagentry = Tags(request.form["tag"], '#000000')
            tagmap = Tagmap(request.form["tag"], current_user.id,
                            song_result.artist, song_result.id)
            db.session.add(tagentry)
            db.session.add(tagmap)
            db.session.commit()
            return render_template('tag_created.html', form=form)
    return render_template('song.html', song_result=song_result, name=name,
                           tag_result=tag_result, form=form, tagform=tagform)

@app.route('/search/<name>', methods=('GET', 'POST'))
def query(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    artist_result = db.session.query( Music.artist ).distinct() \
                              .filter(Music.artist.ilike('%' + name + '%'))\
                              .limit(5).all()
    song_result = db.session.query( Music.artist, Music.song, Music.year ) \
                            .distinct().order_by(Music.artist) \
                            .filter(Music.song.ilike('%' + name + '%')) \
                            .limit(5).all()
    tag_result = db.session.query( Tags.name ).distinct() \
                           .filter( Tags.name.ilike('%' + name + '%')) \
                           .limit(5).all()
    return render_template('results.html', artist_result=artist_result,
                           song_result=song_result, tag_result=tag_result,
                           name=name, form=form)

@app.route('/search/artist/<name>', methods=('GET', 'POST'))
def query_artist(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    artist_result = db.session.query( Music.artist ).distinct() \
                              .filter(Music.artist.ilike('%' + name + '%')).limit(120).all()
    return render_template('artist_results.html', artist_result=artist_result, form=form)

@app.route('/search/tag/<name>', methods=('GET', 'POST'))
def query_tag(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    tag_result = db.session.query( Tags.name ).distinct() \
                           .filter( Tags.name.ilike('%' + name + '%')) \
                           .limit(120).all()
    return render_template('tag_results.html', tag_result=tag_result, form=form)

@app.route('/search/song/<name>', methods=('GET', 'POST'))
def query_song(name):
    form = SearchForm()
    if form.validate_on_submit():
        return redirect('/search/' + request.form["query"])
    song_result = db.session.query( Music.artist, Music.song, Music.year ) \
                            .distinct().order_by(Music.artist) \
                            .filter(Music.song.ilike('%' + name + '%')).limit(120).all()
    return render_template('song_results.html', song_result=song_result, form=form)

# Leave the app in debug mode.
if __name__ == '__main__':
    app.run()
