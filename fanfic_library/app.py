import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from models import db, User, Fic
from scraper import scrape_ao3
from collections import Counter
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, URLField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional, Length

# --- Configuração da App ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'shiplog-secret-key-v7-final-fix'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Formulários (Completos) ---
class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')
    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Este nome de usuário já existe.')

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Login')

class AddFicUrlForm(FlaskForm):
    url = URLField('URL da Fanfic no AO3', validators=[DataRequired()])
    submit = SubmitField('Importar Fanfic')

class AddFicManualForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired()])
    author = StringField('Autor(a)', validators=[DataRequired()])
    fandom = StringField('Fandom(s)', validators=[DataRequired()])
    relationship = StringField('Relacionamento Principal')
    summary = TextAreaField('Sumário')
    tags = StringField('Tags (separadas por vírgula)')
    status = StringField('Status')
    source_url = URLField('URL da Fanfic', validators=[DataRequired()])
    submit = SubmitField('Salvar Manualmente')

class EditFicDetailsForm(FlaskForm):
    date_read = DateField('Data da Leitura', format='%Y-%m-%d', validators=[Optional()])
    comment = TextAreaField('Comentário Pessoal', validators=[Length(max=500)])
    submit = SubmitField('Salvar Comentário')

# --- Context Processor para o Menu ---
@app.context_processor
def inject_sidebar_data():
    if not current_user.is_authenticated:
        return dict(sidebar_data={})
    fics = Fic.query.filter_by(user_id=current_user.id).order_by(Fic.title).all()
    sidebar_data = {}
    for fic in fics:
        main_fandom = fic.fandom.split(',')[0].strip()
        if main_fandom not in sidebar_data:
            sidebar_data[main_fandom] = {}
        relationship = fic.relationship or "Geral"
        if relationship not in sidebar_data[main_fandom]:
            sidebar_data[main_fandom][relationship] = []
        sidebar_data[main_fandom][relationship].append(fic)
    return dict(sidebar_data=sidebar_data)

# --- Rotas da Aplicação ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('library'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('library'))
        flash('Login sem sucesso. Verifique usuário e senha.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('library'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash('Sua conta foi criada! Agora você pode fazer login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registro', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/library')
@login_required
def library():
    fandom = request.args.get('fandom')
    relationship = request.args.get('relationship')
    query = Fic.query.filter_by(user_id=current_user.id)
    if fandom: query = query.filter(Fic.fandom.like(f'{fandom}%'))
    if relationship:
        if relationship != "Geral": query = query.filter_by(relationship=relationship)
        else: query = query.filter((Fic.relationship == "Geral") | (Fic.relationship.is_(None)))
    fics = query.order_by(Fic.title).all()
    return render_template('library.html', fics=fics, selected_fandom=fandom, selected_relationship=relationship)

@app.route('/fic/<int:fic_id>/details')
@login_required
def fic_details(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user: return redirect(url_for('library'))
    form = EditFicDetailsForm(obj=fic)
    return render_template('fic_details.html', fic=fic, form=form, title="Detalhes")

@app.route('/fic/<int:fic_id>/edit', methods=['POST'])
@login_required
def edit_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user: return redirect(url_for('library'))
    form = EditFicDetailsForm()
    if form.validate_on_submit():
        fic.date_read = form.date_read.data
        fic.comment = form.comment.data
        db.session.commit()
        flash('Detalhes atualizados!', 'success')
    return redirect(url_for('fic_details', fic_id=fic_id))

@app.route('/fic/<int:fic_id>/rate', methods=['POST'])
@login_required
def rate_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user: return jsonify({'success': False, 'error': 'Permission denied'}), 403
    rating = request.form.get('rating')
    if rating and 1 <= int(rating) <= 5:
        fic.rating = int(rating)
        db.session.commit()
        return jsonify({'success': True, 'newRating': fic.rating})
    return jsonify({'success': False, 'error': 'Invalid rating'}), 400

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_fic():
    url_form = AddFicUrlForm()
    manual_form = AddFicManualForm()
    if url_form.validate_on_submit() and 'submit_url' in request.form:
        fic_data = scrape_ao3(url_form.url.data)
        if fic_data:
            new_fic = Fic(
                title=fic_data['title'], author=fic_data['author'], fandom=fic_data['fandom'],
                relationship=fic_data['relationship'], summary=fic_data['summary'], tags=fic_data['tags'],
                status=fic_data['status'], date_published=fic_data['date_published'],
                source_url=fic_data['source_url'], user_id=current_user.id )
            db.session.add(new_fic); db.session.commit()
            flash(f"Fanfic '{new_fic.title}' importada!", 'success')
            return redirect(url_for('fic_details', fic_id=new_fic.id))
        else:
            flash('Não foi possível importar a fanfic da URL.', 'danger')
    if manual_form.validate_on_submit() and 'submit_manual' in request.form:
        new_fic = Fic(
            title=manual_form.title.data, author=manual_form.author.data, fandom=manual_form.fandom.data,
            relationship=manual_form.relationship.data, summary=manual_form.summary.data,
            tags=manual_form.tags.data, status=manual_form.status.data,
            source_url=manual_form.source_url.data, user_id=current_user.id )
        db.session.add(new_fic); db.session.commit()
        flash(f"Fanfic '{new_fic.title}' adicionada!", 'success')
        return redirect(url_for('fic_details', fic_id=new_fic.id))
    return render_template('add_fic.html', url_form=url_form, manual_form=manual_form, title="Adicionar Fanfic")

@app.route('/fic/<int:fic_id>/delete', methods=['POST'])
@login_required
def delete_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user: return redirect(url_for('library'))
    db.session.delete(fic); db.session.commit()
    flash(f"Fanfic '{fic.title}' deletada.", "success")
    return redirect(url_for('library'))

@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html', title='Estatísticas')

@app.route('/stats/data')
@login_required
def stats_data():
    period = request.args.get('period', 'all')
    query = Fic.query.filter_by(user_id=current_user.id).filter(Fic.date_read.isnot(None))
    if period != 'all':
        today = datetime.utcnow().date()
        if period == 'week': start_date = today - timedelta(days=7)
        elif period == 'month': start_date = today - timedelta(days=30)
        elif period == 'year': start_date = today - timedelta(days=365)
        else: start_date = None
        if start_date: query = query.filter(Fic.date_read >= start_date)
    fics = query.all()
    fandoms_list = []; [fandoms_list.extend([f.strip() for f in fic.fandom.split(',')]) for fic in fics]
    fandom_counts = Counter(fandoms_list).most_common(5)
    ships_list = [fic.relationship for fic in fics if fic.relationship and fic.relationship != "Geral"]
    ship_counts = Counter(ships_list).most_common(5)
    return jsonify({
        'top_fandoms': [{'name': item[0], 'count': item[1]} for item in fandom_counts],
        'top_ships': [{'name': item[0], 'count': item[1]} for item in ship_counts],
        'total_read': len(fics)
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)

