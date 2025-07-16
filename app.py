from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_teste_desenvolvimento')
DB_NAME = 'database.db'

# Inicializar banco de dados
def init_db():
    if not os.path.exists(DB_NAME):
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS lojas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_loja TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    endereco TEXT,
                    telefone TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

# Rota de Registro de Usuário (existente)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            flash('Registro de usuário bem-sucedido! Faça login agora.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe. Por favor, escolha outro.', 'danger')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
    return render_template('register.html')

# Rota de Login de Usuário (existente)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
            user = c.fetchone()

        if user and check_password_hash(user[2], password):
            session['logged_in'] = True
            session['username'] = user[1]
            session['user_type'] = 'usuario' # Adiciona o tipo de usuário à sessão
            flash('Login de usuário bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

# Rota de Registro de Loja (NOVA)
@app.route('/register_loja', methods=['GET', 'POST'])
def register_loja():
    if request.method == 'POST':
        nome_loja = request.form['nome_loja']
        email = request.form['email']
        password = request.form['password']
        endereco = request.form.get('endereco') # Opcional
        telefone = request.form.get('telefone') # Opcional
        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO lojas (nome_loja, email, password, endereco, telefone) VALUES (?, ?, ?, ?, ?)",
                          (nome_loja, email, hashed_password, endereco, telefone))
                conn.commit()
            flash('Registro de loja bem-sucedido! Faça login agora.', 'success')
            return redirect(url_for('login_loja'))
        except sqlite3.IntegrityError:
            flash('Nome da loja ou e-mail já existem. Por favor, escolha outros.', 'danger')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'danger')
    return render_template('register_loja.html') # Você precisará criar este template

# Rota de Login de Loja (NOVA)
@app.route('/login_loja', methods=['GET', 'POST'])
def login_loja():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM lojas WHERE email = ?", (email,))
            loja = c.fetchone()

        if loja and check_password_hash(loja[3], password): # loja[3] é a coluna da senha
            session['logged_in'] = True
            session['username'] = loja[1] # Armazena o nome da loja como username
            session['user_type'] = 'loja' # Adiciona o tipo de usuário à sessão
            session['loja_id'] = loja[0] # Armazena o ID da loja
            flash(f'Login da loja "{loja[1]}" bem-sucedido!', 'success')
            return redirect(url_for('index')) # Redireciona para a página inicial ou um dashboard da loja
        else:
            flash('E-mail ou senha da loja inválidos.', 'danger')
    return render_template('login_loja.html') # Você precisará criar este template

# Rota de Logout (Atualizada para lidar com ambos os tipos de usuário)
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('user_type', None) # Remove o tipo de usuário
    session.pop('loja_id', None) # Remove o ID da loja
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
