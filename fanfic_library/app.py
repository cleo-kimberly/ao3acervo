import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField, URLField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, Length

# Importações locais
from models import db, User, Fic
from scraper import scrape_ao3
from collections import Counter

# --- Configuração da App ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Formulários com WTForms ---
class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nome de usuário já existe. Por favor, escolha outro.')

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
    content = TextAreaField('Conteúdo da História', validators=[DataRequired()])
    submit = SubmitField('Salvar Manualmente')

class EditFicDetailsForm(FlaskForm):
    date_read = DateField('Data da Leitura', format='%Y-%m-%d', validators=[Optional()])
    comment = TextAreaField('Comentário Pessoal', validators=[Length(max=500)])
    submit = SubmitField('Salvar')


# --- Context Processor para o Menu Lateral ---
@app.context_processor
def inject_sidebar_data():
    if not current_user.is_authenticated:
        return dict(sidebar_data={})
    
    fics = Fic.query.filter_by(user_id=current_user.id).order_by(Fic.title).all()
    sidebar_data = {}
    for fic in fics:
        # Pega o primeiro fandom da lista
        main_fandom = fic.fandom.split(',')[0].strip()
        
        if main_fandom not in sidebar_data:
            sidebar_data[main_fandom] = {}
        
        relationship = fic.relationship if fic.relationship else "Geral"
        if relationship not in sidebar_data[main_fandom]:
            sidebar_data[main_fandom][relationship] = []
        
        sidebar_data[main_fandom][relationship].append(fic)
        
    return dict(sidebar_data=sidebar_data)


# --- Rotas da Aplicação ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login sem sucesso. Verifique usuário e senha.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Sua conta foi criada! Agora você pode fazer login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registro', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    fandom = request.args.get('fandom')
    relationship = request.args.get('relationship')
    fics = []
    
    if fandom and relationship:
        query = Fic.query.filter_by(user_id=current_user.id)
        # Filtro de Fandom precisa ser mais robusto para "Fandom A, Fandom B"
        query = query.filter(Fic.fandom.like(f'{fandom}%'))
        if relationship != "Geral":
            query = query.filter_by(relationship=relationship)
        else:
            query = query.filter((Fic.relationship == "Geral") | (Fic.relationship == None))
        fics = query.order_by(Fic.title).all()
        
    return render_template('index.html', fics=fics, selected_fandom=fandom, selected_relationship=relationship)


@app.route('/fic/<int:fic_id>')
@login_required
def view_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user:
        flash("Você não tem permissão para ver esta fanfic.", "danger")
        return redirect(url_for('index'))
    
    form = EditFicDetailsForm(obj=fic)
    return render_template('fic_view.html', fic=fic, form=form)


@app.route('/fic/<int:fic_id>/edit', methods=['POST'])
@login_required
def edit_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user:
        flash("Você não tem permissão para editar esta fanfic.", "danger")
        return redirect(url_for('index'))
    
    form = EditFicDetailsForm()
    if form.validate_on_submit():
        fic.date_read = form.date_read.data
        fic.comment = form.comment.data
        db.session.commit()
        flash('Detalhes da fanfic atualizados com sucesso!', 'success')
    else:
        flash('Erro ao atualizar os detalhes.', 'danger')

    return redirect(url_for('view_fic', fic_id=fic_id))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_fic():
    url_form = AddFicUrlForm()
    manual_form = AddFicManualForm()
    
    if url_form.validate_on_submit() and 'submit_url' in request.form:
        fic_data = scrape_ao3(url_form.url.data)
        if fic_data:
            new_fic = Fic(
                title=fic_data['title'],
                author=fic_data['author'],
                fandom=fic_data['fandom'],
                relationship=fic_data['relationship'],
                summary=fic_data['summary'],
                tags=fic_data['tags'],
                status=fic_data['status'],
                date_published=fic_data['date_published'],
                content=fic_data['content'],
                source_url=fic_data['source_url'],
                user_id=current_user.id
            )
            db.session.add(new_fic)
            db.session.commit()
            flash(f"Fanfic '{new_fic.title}' importada com sucesso!", 'success')
            return redirect(url_for('view_fic', fic_id=new_fic.id))
        else:
            flash('Não foi possível importar a fanfic da URL fornecida.', 'danger')

    if manual_form.validate_on_submit() and 'submit_manual' in request.form:
        new_fic = Fic(
            title=manual_form.title.data,
            author=manual_form.author.data,
            fandom=manual_form.fandom.data,
            relationship=manual_form.relationship.data,
            summary=manual_form.summary.data,
            tags=manual_form.tags.data,
            status=manual_form.status.data,
            content=manual_form.content.data,
            user_id=current_user.id
        )
        db.session.add(new_fic)
        db.session.commit()
        flash(f"Fanfic '{new_fic.title}' adicionada manualmente com sucesso!", 'success')
        return redirect(url_for('view_fic', fic_id=new_fic.id))

    return render_template('add_fic.html', url_form=url_form, manual_form=manual_form)


@app.route('/fic/<int:fic_id>/delete', methods=['POST'])
@login_required
def delete_fic(fic_id):
    fic = Fic.query.get_or_404(fic_id)
    if fic.owner != current_user:
        flash("Você não tem permissão para deletar esta fanfic.", "danger")
        return redirect(url_for('index'))

    db.session.delete(fic)
    db.session.commit()
    flash(f"Fanfic '{fic.title}' deletada com sucesso.", "success")
    return redirect(url_for('index'))

@app.route('/stats')
@login_required
def stats():
    return render_template('stats.html', title='Estatísticas')


@app.route('/stats/data')
@login_required
def stats_data():
    fics = Fic.query.filter_by(user_id=current_user.id).all()
    
    # Fandoms mais lidos
    fandoms_list = []
    for fic in fics:
        fandoms_list.extend([f.strip() for f in fic.fandom.split(',')])
    fandom_counts = Counter(fandoms_list).most_common(10)
    
    # Ships mais lidos
    ships_list = [fic.relationship for fic in fics if fic.relationship and fic.relationship != "Geral"]
    ship_counts = Counter(ships_list).most_common(10)
    
    # Leituras por mês/ano
    readings_by_month = {}
    for fic in fics:
        if fic.date_read:
            month_year = fic.date_read.strftime('%Y-%m')
            readings_by_month[month_year] = readings_by_month.get(month_year, 0) + 1
    
    # Ordena por data para o gráfico
    sorted_readings = sorted(readings_by_month.items())

    return jsonify({
        'top_fandoms': {
            'labels': [item[0] for item in fandom_counts],
            'data': [item[1] for item in fandom_counts]
        },
        'top_ships': {
            'labels': [item[0] for item in ship_counts],
            'data': [item[1] for item in ship_counts]
        },
        'readings_over_time': {
            'labels': [item[0] for item in sorted_readings],
            'data': [item[1] for item in sorted_readings]
        }
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)