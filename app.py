# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SelectMultipleField, DateField, URLField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
import json
import os
import datetime
from markdown2 import markdown

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production

# Data handling functions
def load_data():
    if not os.path.exists('data.json'):
        return {"next_id": 1, "genres": [], "recommendations": []}
    with open('data.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

# Forms
class AddForm(FlaskForm):
    title = StringField('Movie/TV Show Title', validators=[DataRequired()])
    year = IntegerField('Year', validators=[Optional(), NumberRange(min=1900)])
    rating = SelectField('Personal Rating (1-10)', choices=[(i, str(i)) for i in range(1, 11)], coerce=int, validators=[DataRequired()])
    genres = SelectMultipleField('Genres')
    new_genres = StringField('New Genres (comma separated)')
    watched_date = DateField('Watched Date', default=datetime.date.today, validators=[DataRequired()])
    poster_url = URLField('Poster URL', validators=[Optional()])
    platform = StringField('Where I Watched It', validators=[Optional()])
    review = TextAreaField('Recommendation Text / Review', validators=[DataRequired()])
    watched = BooleanField('Watched', default='checked')
    rewatch = BooleanField('Rewatch?')
    submit = SubmitField('Submit')

class GenreForm(FlaskForm):
    genre = StringField('New Genre', validators=[DataRequired()])
    submit = SubmitField('Add Genre')

class SearchForm(FlaskForm):
    q = StringField('Search')

# Routes
@app.route('/')
def index():
    data = load_data()
    recommendations = sorted(data['recommendations'], key=lambda x: x['added_at'], reverse=True)
    page = request.args.get('page', 1, type=int)
    per_page = 6
    start = (page - 1) * per_page
    end = start + per_page
    paginated_recs = recommendations[start:end]
    has_more = end < len(recommendations)
    return render_template('index.html', recommendations=paginated_recs, page=page, has_more=has_more)

@app.route('/add', methods=['GET', 'POST'])
def add():
    data = load_data()
    form = AddForm()
    form.genres.choices = [(g, g) for g in data['genres']]
    if form.validate_on_submit():
        new_genres = [g.strip() for g in form.new_genres.data.split(',') if g.strip()]
        for ng in new_genres:
            if ng not in data['genres']:
                data['genres'].append(ng)
                data['genres'].sort()
        selected_genres = form.genres.data + new_genres
        rec = {
            "id": data['next_id'],
            "title": form.title.data,
            "year": form.year.data,
            "rating": form.rating.data,
            "genres": selected_genres,
            "watched_date": form.watched_date.data.isoformat(),
            "poster_url": form.poster_url.data,
            "platform": form.platform.data,
            "review": form.review.data,
            "watched": form.watched.data,
            "rewatch": form.rewatch.data,
            "added_at": datetime.datetime.utcnow().isoformat()
        }
        data['recommendations'].append(rec)
        data['next_id'] += 1
        save_data(data)
        flash('Recommendation added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add.html', form=form)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    data = load_data()
    rec = next((r for r in data['recommendations'] if r['id'] == id), None)
    if not rec:
        return redirect(url_for('index'))
    form = AddForm(
        title=rec['title'],
        year=rec['year'],
        rating=rec['rating'],
        new_genres='',
        watched_date=datetime.date.fromisoformat(rec['watched_date']),
        poster_url=rec['poster_url'],
        platform=rec['platform'],
        review=rec['review'],
        watched=rec['watched'],
        rewatch=rec['rewatch']
    )
    form.genres.choices = [(g, g) for g in data['genres']]
    form.genres.data = rec['genres']
    if form.validate_on_submit():
        new_genres = [g.strip() for g in form.new_genres.data.split(',') if g.strip()]
        for ng in new_genres:
            if ng not in data['genres']:
                data['genres'].append(ng)
                data['genres'].sort()
        selected_genres = form.genres.data + new_genres
        rec['title'] = form.title.data
        rec['year'] = form.year.data
        rec['rating'] = form.rating.data
        rec['genres'] = selected_genres
        rec['watched_date'] = form.watched_date.data.isoformat()
        rec['poster_url'] = form.poster_url.data
        rec['platform'] = form.platform.data
        rec['review'] = form.review.data
        rec['watched'] = form.watched.data
        rec['rewatch'] = form.rewatch.data
        # Update added_at if desired, but keeping original
        save_data(data)
        flash('Recommendation updated successfully!', 'success')
        return redirect(url_for('view', id=id))
    return render_template('edit.html', form=form, id=id)

@app.route('/movie/<int:id>')
def view(id):
    data = load_data()
    rec = next((r for r in data['recommendations'] if r['id'] == id), None)
    if not rec:
        return redirect(url_for('index'))
    rec['review_html'] = markdown(rec['review'], extras=['fenced-code-blocks'])
    return render_template('movie.html', rec=rec)

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    data = load_data()
    data['recommendations'] = [r for r in data['recommendations'] if r['id'] != id]
    save_data(data)
    flash('Recommendation deleted successfully!', 'danger')
    return redirect(url_for('index'))

@app.route('/genres', methods=['GET', 'POST'])
def genres():
    data = load_data()
    form = GenreForm()
    if form.validate_on_submit():
        new_genre = form.genre.data.strip()
        if new_genre and new_genre not in data['genres']:
            data['genres'].append(new_genre)
            data['genres'].sort()
            save_data(data)
            flash('Genre added successfully!', 'success')
            return redirect(url_for('genres'))
    return render_template('genres.html', genres=data['genres'], form=form)

@app.route('/search')
def search():
    q = request.args.get('q', '').lower()
    if not q:
        return redirect(url_for('index'))
    data = load_data()
    recommendations = [r for r in data['recommendations'] if q in r['title'].lower()]
    recommendations = sorted(recommendations, key=lambda x: x['added_at'], reverse=True)
    return render_template('index.html', recommendations=recommendations, page=1, has_more=False, search_query=q)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)