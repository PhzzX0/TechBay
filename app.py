from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_secreta_muito_segura_e_aleatoria') # Use uma chave mais forte em produção
DB_NAME = 'database.db'

# Função para obter a conexão com o banco de dados
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row # Permite acessar colunas por nome
    return g.db

# Função para fechar a conexão com o banco de dados
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Inicializar banco de dados
def init_db():
    with app.app_context():
        db = get_db()
        c = db.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS lojas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_loja TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                endereco TEXT,
                telefone TEXT,
                descricao TEXT,
                foto_perfil TEXT,
                whatsapp TEXT, -- Nova coluna
                instagram TEXT -- Nova coluna
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS tecnicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                especialidade TEXT,
                localizacao TEXT,
                preco_hora REAL,
                foto_perfil TEXT,
                status TEXT DEFAULT 'Offline',
                descricao TEXT,
                whatsapp TEXT, -- Nova coluna
                instagram TEXT -- Nova coluna
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS avaliacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                avaliador_id INTEGER NOT NULL,
                avaliador_tipo TEXT NOT NULL,
                avaliado_id INTEGER NOT NULL,
                avaliado_tipo TEXT NOT NULL,
                nota INTEGER NOT NULL CHECK(nota >= 1 AND nota <= 5),
                comentario TEXT,
                data_avaliacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (avaliador_id) REFERENCES usuarios(id)
            )
        ''')
        db.commit()

# Rota principal
@app.route('/')
def index():
    db = get_db()
    tecnicos_destaque = []
    lojas_parceiras = []
    avaliacoes_clientes = [] # Nova lista para avaliações de clientes

    try:
        c = db.cursor()
        # Seleciona 3 técnicos com maior média de avaliações
        c.execute("""
            SELECT t.*, AVG(a.nota) as media_nota
            FROM tecnicos t
            LEFT JOIN avaliacoes a ON t.id = a.avaliado_id AND a.avaliado_tipo = 'tecnico'
            GROUP BY t.id
            ORDER BY media_nota DESC, t.id DESC
            LIMIT 3
        """)
        tecnicos_destaque = c.fetchall()

        # Seleciona 3 lojas com maior média de avaliações
        c.execute("""
            SELECT l.*, AVG(a.nota) as media_nota
            FROM lojas l
            LEFT JOIN avaliacoes a ON l.id = a.avaliado_id AND a.avaliado_tipo = 'loja'
            GROUP BY l.id
            ORDER BY media_nota DESC, l.id DESC
            LIMIT 3
        """)
        lojas_parceiras = c.fetchall()

        # Seleciona as 3 avaliações mais recentes (pode ser de técnico ou loja)
        c.execute("""
            SELECT a.*, u.username as avaliador_username,
                    CASE
                        WHEN a.avaliado_tipo = 'tecnico' THEN t.nome
                        WHEN a.avaliado_tipo = 'loja' THEN l.nome_loja
                    END as avaliado_nome
            FROM avaliacoes a
            JOIN usuarios u ON a.avaliador_id = u.id
            LEFT JOIN tecnicos t ON a.avaliado_id = t.id AND a.avaliado_tipo = 'tecnico'
            LEFT JOIN lojas l ON a.avaliado_id = l.id AND a.avaliado_tipo = 'loja'
            ORDER BY a.data_avaliacao DESC
            LIMIT 3
        """)
        avaliacoes_clientes = c.fetchall()

    except Exception as e:
        print(f"Erro ao buscar dados para index: {e}")

    return render_template('index.html', tecnicos=tecnicos_destaque, lojas=lojas_parceiras, avaliacoes_clientes=avaliacoes_clientes)

# Rota de Registro de Usuário
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        db = get_db()
        try:
            c = db.cursor()
            c.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (username, hashed_password))
            db.commit()
            flash('Registro de usuário bem-sucedido! Faça login agora.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe. Por favor, escolha outro.', 'danger')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
    return render_template('register.html')

# Rota de Login de Usuário
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
        user = c.fetchone()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            session['user_id'] = user['id'] # Armazena o ID do usuário
            session['user_type'] = 'usuario'
            flash('Login de usuário bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

# Rota para escolher tipo de cadastro de parceiro
@app.route('/parceiro_cadastro')
def parceiro_cadastro():
    return render_template('/parceiro_cadastro.html')

# Rota de Registro de Loja
@app.route('/register_loja', methods=['GET', 'POST'])
def register_loja():
    if request.method == 'POST':
        nome_loja = request.form['nome_loja']
        email = request.form['email']
        password = request.form['password']
        endereco = request.form.get('endereco')
        telefone = request.form.get('telefone')
        descricao = request.form.get('descricao')
        foto_perfil = request.form.get('foto_perfil')
        whatsapp = request.form.get('whatsapp') # Novo
        instagram = request.form.get('instagram') # Novo
        hashed_password = generate_password_hash(password)

        db = get_db()
        try:
            c = db.cursor()
            c.execute("INSERT INTO lojas (nome_loja, email, password, endereco, telefone, descricao, foto_perfil, whatsapp, instagram) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (nome_loja, email, hashed_password, endereco, telefone, descricao, foto_perfil, whatsapp, instagram))
            db.commit()
            flash('Registro de loja bem-sucedido! Faça login agora.', 'success')
            return redirect(url_for('login_loja'))
        except sqlite3.IntegrityError:
            flash('Nome da loja ou e-mail já existem. Por favor, escolha outros.', 'danger')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
    return render_template('register_loja.html')

# Rota de Login de Loja
@app.route('/login_loja', methods=['GET', 'POST'])
def login_loja():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM lojas WHERE email = ?", (email,))
        loja = c.fetchone()

        if loja and check_password_hash(loja['password'], password):
            session['logged_in'] = True
            session['username'] = loja['nome_loja']
            session['user_id'] = loja['id'] # Armazena o ID da loja
            session['user_type'] = 'loja'
            flash(f'Login da loja "{loja["nome_loja"]}" bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail ou senha da loja inválidos.', 'danger')
    return render_template('login_loja.html')

# Rota de Registro de Técnico
@app.route('/register_tecnico', methods=['GET', 'POST'])
def register_tecnico():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        password = request.form['password']
        especialidade = request.form.get('especialidade')
        localizacao = request.form.get('localizacao')
        preco_hora = request.form.get('preco_hora')
        descricao = request.form.get('descricao')
        foto_perfil = request.form.get('foto_perfil')
        whatsapp = request.form.get('whatsapp') # Novo
        instagram = request.form.get('instagram') # Novo
        hashed_password = generate_password_hash(password)

        db = get_db()
        try:
            c = db.cursor()
            c.execute("INSERT INTO tecnicos (nome, email, password, especialidade, localizacao, preco_hora, descricao, foto_perfil, whatsapp, instagram) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (nome, email, hashed_password, especialidade, localizacao, preco_hora, descricao, foto_perfil, whatsapp, instagram))
            db.commit()
            flash('Registro de técnico bem-sucedido! Faça login agora.', 'success')
            return redirect(url_for('login_tecnico'))
        except sqlite3.IntegrityError:
            flash('E-mail de técnico já existe. Por favor, escolha outro.', 'danger')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
    return render_template('register_tecnico.html')

# Rota de Login de Técnico
@app.route('/login_tecnico', methods=['GET', 'POST'])
def login_tecnico():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM tecnicos WHERE email = ?", (email,))
        tecnico = c.fetchone()

        if tecnico and check_password_hash(tecnico['password'], password):
            session['logged_in'] = True
            session['username'] = tecnico['nome']
            session['user_id'] = tecnico['id'] # Armazena o ID do técnico
            session['user_type'] = 'tecnico'
            flash(f'Login do técnico "{tecnico["nome"]}" bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail ou senha de técnico inválidos.', 'danger')
    return render_template('login_tecnico.html')

# Rota de Logout
@app.route('/logout')
def logout():
    session.clear() # Limpa todas as variáveis de sessão
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('index'))

# Rota para perfil de Técnico
@app.route('/tecnico/<int:tecnico_id>')
def profile_tecnico(tecnico_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM tecnicos WHERE id = ?", (tecnico_id,))
    tecnico = c.fetchone()

    if not tecnico:
        flash('Técnico não encontrado.', 'danger')
        return redirect(url_for('index'))

    # Buscar avaliações para este técnico
    c.execute("""
        SELECT a.*, u.username as avaliador_username
        FROM avaliacoes a
        JOIN usuarios u ON a.avaliador_id = u.id
        WHERE a.avaliado_id = ? AND a.avaliado_tipo = 'tecnico'
        ORDER BY a.data_avaliacao DESC
    """, (tecnico_id,))
    avaliacoes = c.fetchall()

    # Calcular média de avaliações
    media_avaliacoes = 0
    if avaliacoes:
        total_notas = sum(a['nota'] for a in avaliacoes)
        media_avaliacoes = total_notas / len(avaliacoes)

    return render_template('profile_tecnico.html', tecnico=tecnico, avaliacoes=avaliacoes, media_avaliacoes=media_avaliacoes)

# Rota para perfil de Loja
@app.route('/loja/<int:loja_id>')
def profile_loja(loja_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM lojas WHERE id = ?", (loja_id,))
    loja = c.fetchone()

    if not loja:
        flash('Loja não encontrada.', 'danger')
        return redirect(url_for('index'))

    # Buscar avaliações para esta loja
    c.execute("""
        SELECT a.*, u.username as avaliador_username
        FROM avaliacoes a
        JOIN usuarios u ON a.avaliador_id = u.id
        WHERE a.avaliado_id = ? AND a.avaliado_tipo = 'loja'
        ORDER BY a.data_avaliacao DESC
    """, (loja_id,))
    avaliacoes = c.fetchall()

    # Calcular média de avaliações
    media_avaliacoes = 0
    if avaliacoes:
        total_notas = sum(a['nota'] for a in avaliacoes)
        media_avaliacoes = total_notas / len(avaliacoes)

    return render_template('profile_loja.html', loja=loja, avaliacoes=avaliacoes, media_avaliacoes=media_avaliacoes)

# Rota para adicionar avaliação
@app.route('/avaliar', methods=['POST'])
def avaliar():
    if not session.get('logged_in') or session.get('user_type') != 'usuario':
        flash('Você precisa estar logado como usuário para avaliar.', 'danger')
        # Redireciona para a página de login, mas mantém o 'next' para voltar após o login
        return redirect(url_for('login', next=request.referrer))

    avaliado_id = request.form['avaliado_id']
    avaliado_tipo = request.form['avaliado_tipo']
    nota = request.form['nota']
    comentario = request.form.get('comentario')
    avaliador_id = session['user_id']

    if not (1 <= int(nota) <= 5):
        flash('A nota deve ser entre 1 e 5.', 'danger')
        return redirect(request.referrer or url_for('index'))

    db = get_db()
    try:
        c = db.cursor()
        # Verifica se o usuário já avaliou este item
        c.execute("SELECT 1 FROM avaliacoes WHERE avaliador_id = ? AND avaliado_id = ? AND avaliado_tipo = ?",
                  (avaliador_id, avaliado_id, avaliado_tipo))
        if c.fetchone():
            flash('Você já avaliou este item.', 'warning')
        else:
            c.execute("INSERT INTO avaliacoes (avaliador_id, avaliador_tipo, avaliado_id, avaliado_tipo, nota, comentario) VALUES (?, ?, ?, ?, ?, ?)",
                      (avaliador_id, 'usuario', avaliado_id, avaliado_tipo, nota, comentario))
            db.commit()
            flash('Avaliação registrada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao registrar avaliação: {e}', 'danger')

    if avaliado_tipo == 'tecnico':
        return redirect(url_for('profile_tecnico', tecnico_id=avaliado_id))
    elif avaliado_tipo == 'loja':
        return redirect(url_for('profile_loja', loja_id=avaliado_id))
    return redirect(url_for('index'))

# Rota para listar todos os técnicos
@app.route('/tecnicos')
def tecnicos_list():
    db = get_db()
    c = db.cursor()
    service_filter = request.args.get('service', 'all')

    query = """
        SELECT t.*, AVG(a.nota) as media_nota
        FROM tecnicos t
        LEFT JOIN avaliacoes a ON t.id = a.avaliado_id AND a.avaliado_tipo = 'tecnico'
    """
    params = []

    if service_filter != 'all':
        query += " WHERE especialidade LIKE ?"
        params.append(f'%{service_filter}%')

    query += " GROUP BY t.id ORDER BY t.nome" # Ordenar por nome para consistência

    c.execute(query, params)
    tecnicos = c.fetchall()
    return render_template('tecnicos_list.html', tecnicos=tecnicos)

# Rota para listar todas as lojas
@app.route('/lojas')
def lojas_list():
    db = get_db()
    c = db.cursor()
    c.execute("""
        SELECT l.*, AVG(a.nota) as media_nota
        FROM lojas l
        LEFT JOIN avaliacoes a ON l.id = a.avaliado_id AND a.avaliado_tipo = 'loja'
        GROUP BY l.id
        ORDER BY l.nome_loja
    """)
    lojas = c.fetchall()
    return render_template('lojas_list.html', lojas=lojas)

# Rota para função ainda não implementada
@app.route('/notimp')
def notimp():
    return render_template('/notimp.html')

if __name__ == '__main__':
    # Garante que o banco de dados seja inicializado apenas uma vez ao iniciar o app
    # Se o arquivo database.db já existir, ele não será recriado.
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(debug=True)