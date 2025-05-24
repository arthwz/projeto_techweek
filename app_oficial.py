from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from models import db, Plataforma, Categoria, Jogo, Usuario
from functools import wraps
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque_jogos.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta')  

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor, faça login para acessar esta pagina.', 'erro')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('tipo', '') != 'admin':
            flash('Acesso restrito a administradores', 'erro')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    busca = request.args.get('busca', '', type=str)
    pagina = request.args.get('page', 1, type=int)

    consulta = Jogo.query
    if busca:
        consulta = consulta.filter(Jogo.nome.ilike(f"%{busca}%"))

    pagination = consulta.order_by(Jogo.nome).paginate(page=pagina, per_page=5, error_out=False)
    jogos = pagination.items

    return render_template("index.html", jogos=jogos, pagination=pagination, tipo_usuario=session.get('tipo'))

@app.route('/cadastrar', methods=['GET', 'POST'])
@admin_required
def cadastrar():
    if request.method == 'POST':
        try:
            novo_jogo = Jogo(
                nome=request.form['nome'],
                preco=float(request.form['preco']),
                estoque=int(request.form['estoque']),
                plataforma_id=int(request.form['plataforma']),
                categoria_id=int(request.form['categoria'])
            )
            db.session.add(novo_jogo)
            db.session.commit()
            flash('Jogo cadastrado com sucesso!', 'sucesso')
            return redirect(url_for('index'))
        except ValueError:
            flash('Preco e estoque devem ser numeros validos', 'erro')
        except Exception as e:
            flash(f'Erro ao cadastrar jogo: {str(e)}', 'erro')

    plataformas = Plataforma.query.all()
    categorias = Categoria.query.all()
    return render_template("cadastrar.html", plataformas=plataformas, categorias=categorias)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(username=request.form['username']).first()
        if usuario and usuario.verificar_senha(request.form['senha']):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo
            session['username'] = usuario.username
            flash('Login realizado com sucesso!', 'sucesso')
            return redirect(url_for('index'))
        flash('Usuario ou senha invalidos', 'erro')
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    flash('Voce foi desconectado', 'info')
    return redirect(url_for('login'))

@app.route('/usuarios', methods=['GET', 'POST'])
@admin_required
def gerenciar_usuarios():
    if request.method == 'POST':
        username = request.form['username']
        senha = request.form['senha']
        tipo = request.form['tipo']

        if Usuario.query.filter_by(username=username).first():
            flash('Ja existe um usuario com esse nome.', 'erro')
        else:
            novo = Usuario(username=username, tipo=tipo)
            novo.set_senha(senha)
            db.session.add(novo)
            db.session.commit()
            flash(f'Usuario "{username}" criado com sucesso!', 'sucesso')

    usuarios = Usuario.query.order_by(Usuario.id).all()
    return render_template("usuarios.html", usuarios=usuarios)

@app.route('/usuarios/excluir/<int:id>')
@admin_required
def excluir_usuario(id):
    if session.get('usuario_id') == id:
        flash('Voce nao pode excluir seu proprio usuario.', 'erro')
        return redirect(url_for('gerenciar_usuarios'))

    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash(f'Usuario "{usuario.username}" excluido com sucesso.', 'sucesso')
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':
        usuario.username = request.form['username']
        usuario.tipo = request.form['tipo']
        if request.form.get('senha'):
            usuario.set_senha(request.form['senha'])
        db.session.commit()
        flash(f'Usuario "{usuario.username}" atualizado com sucesso.', 'sucesso')
        return redirect(url_for('gerenciar_usuarios'))

    return render_template("editar_usuario.html", usuario=usuario)

@app.route('/excluir/<int:id>')
@admin_required
def excluir_jogo(id):
    jogo = Jogo.query.get_or_404(id)
    db.session.delete(jogo)
    db.session.commit()
    flash(f'Jogo "{jogo.nome}" excluido com sucesso.', 'sucesso')
    return redirect(url_for('index'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_jogo(id):
    jogo = Jogo.query.get_or_404(id)
    plataformas = Plataforma.query.all()
    categorias = Categoria.query.all()

    if request.method == 'POST':
        try:
            jogo.nome = request.form['nome']
            jogo.preco = float(request.form['preco'])
            jogo.estoque = int(request.form['estoque'])
            jogo.plataforma_id = int(request.form['plataforma'])
            jogo.categoria_id = int(request.form['categoria'])

            db.session.commit()
            flash('Jogo atualizado com sucesso!', 'sucesso')
            return redirect(url_for('index'))
        except ValueError:
            flash('Preco e estoque devem ser numeros validos', 'erro')
        except Exception as e:
            flash(f'Erro ao atualizar jogo: {str(e)}', 'erro')

    return render_template('editar.html', jogo=jogo, plataformas=plataformas, categorias=categorias)

@app.route('/inicializar')
def inicializar_banco():
    with app.app_context():
        db.create_all()
        if not Usuario.query.first():
            plataformas = ['PC', 'PlayStation', 'Xbox', 'Switch']
            categorias = ['Acao', 'Aventura', 'Esporte', 'RPG', 'Simulacao']

            db.session.add_all([Plataforma(nome=p) for p in plataformas])
            db.session.add_all([Categoria(nome=c) for c in categorias])

            admin = Usuario(username='admin', tipo='admin')
            admin.set_senha('admin123')
            comum = Usuario(username='user', tipo='comum')
            comum.set_senha('user123')

            db.session.add_all([admin, comum])
            db.session.commit()
            print("Banco inicializado com dados padrao")

if __name__ == '__main__':
    inicializar_banco()
    app.run(debug=True)
