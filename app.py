import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

os.makedirs('data', exist_ok=True)
os.makedirs('static', exist_ok=True)

DB_PATH = 'data/ginasio.db'

def iniciar_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS musculacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            grupo TEXT NOT NULL,
            exercicio TEXT NOT NULL,
            peso REAL NOT NULL,
            repeticoes INTEGER NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS cardio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            tipo TEXT NOT NULL,
            subtipo TEXT,
            duracao_min REAL NOT NULL,
            distancia_km REAL,
            kcal REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS peso_corporal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            peso REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

iniciar_db()

def gerar_grafico_peso():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT data_hora, peso FROM peso_corporal ORDER BY data_hora ASC", conn)
    conn.close()

    if df.empty:
        return None

    df['data_formatada'] = pd.to_datetime(df['data_hora']).dt.strftime('%d/%m %H:%M')

    plt.figure(figsize=(10, 4.5))
    plt.plot(df['data_formatada'], df['peso'], marker='o', linestyle='-', color='#357abd', linewidth=2.5, markersize=6)
    
    plt.title('Evolução do Peso Corporal', fontsize=14, color='white', pad=15)
    plt.xlabel('Data e Hora', fontsize=11, color='#a8a8b3')
    plt.ylabel('Peso (kg)', fontsize=11, color='#a8a8b3')
    
    plt.gca().set_facecolor('#202024')
    plt.gcf().patch.set_facecolor('#202024')
    plt.tick_params(colors='#a8a8b3', which='both', labelsize=8)
    plt.xticks(rotation=30)
    plt.grid(True, linestyle='--', alpha=0.2, color='white')
    
    for spine in plt.gca().spines.values():
        spine.set_color('#29292e')

    plt.tight_layout()
    caminho = 'static/peso_evolucao.png'
    plt.savefig(caminho, dpi=150)
    plt.close()
    return caminho

def gerar_grafico_cardio(tipo, subtipo=None):
    conn = sqlite3.connect(DB_PATH)
    if subtipo:
        query = "SELECT data_hora, duracao_min, distancia_km, kcal FROM cardio WHERE tipo = ? AND subtipo = ? ORDER BY data_hora ASC"
        df = pd.read_sql_query(query, conn, params=(tipo, subtipo))
        nome_ficheiro = f"static/cardio_{tipo.lower()}_{subtipo.lower()}_evolucao.png"
        titulo_base = f"Passadeira - {subtipo}"
    else:
        query = "SELECT data_hora, duracao_min, distancia_km FROM cardio WHERE tipo = ? ORDER BY data_hora ASC"
        df = pd.read_sql_query(query, conn, params=(tipo,))
        nome_ficheiro = f"static/cardio_{tipo.lower()}_evolucao.png"
        titulo_base = f"Cardio - {tipo}"
    conn.close()

    if df.empty:
        return None

    df['data_formatada'] = pd.to_datetime(df['data_hora']).dt.strftime('%d/%m %H:%M')

    plt.figure(figsize=(10, 4.5))
    
    plt.plot(df['data_formatada'], df['duracao_min'], marker='o', linestyle='-', color='#fba94c', linewidth=2, label='Duração (min)')
    if 'distancia_km' in df.columns:
        plt.plot(df['data_formatada'], df['distancia_km'], marker='s', linestyle='-', color='#00b37e', linewidth=2, label='Distância (km)')
    if 'kcal' in df.columns and subtipo:
        plt.plot(df['data_formatada'], df['kcal'], marker='^', linestyle='-', color='#f75a68', linewidth=2, label='Calorias (kcal)')

    plt.title(f'Evolução: {titulo_base}', fontsize=14, color='white', pad=15)
    plt.xlabel('Data e Hora', fontsize=11, color='#a8a8b3')
    plt.ylabel('Valores', fontsize=11, color='#a8a8b3')
    
    plt.gca().set_facecolor('#202024')
    plt.gcf().patch.set_facecolor('#202024')
    plt.tick_params(colors='#a8a8b3', which='both', labelsize=8)
    plt.xticks(rotation=30)
    plt.grid(True, linestyle='--', alpha=0.2, color='white')
    plt.legend(facecolor='#202024', edgecolor='#29292e', labelcolor='white')
    
    for spine in plt.gca().spines.values():
        spine.set_color('#29292e')

    plt.tight_layout()
    plt.savefig(nome_ficheiro, dpi=150)
    plt.close()
    return nome_ficheiro

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/musculacao')
def musculacao_menu():
    return render_template('musculacao.html', step='menu')

@app.route('/musculacao/superiores')
def musculacao_superiores():
    return render_template('musculacao.html', step='superiores')

@app.route('/musculacao/registar', methods=['GET', 'POST'])
def musculacao_registar():
    grupo = request.args.get('grupo', 'Geral')
    
    if request.method == 'POST':
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        form_grupo = request.form.get('grupo', grupo)
        exercicio = request.form['exercicio']
        peso = request.form['peso']
        repeticoes = request.form['repeticoes']
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO musculacao (data_hora, grupo, exercicio, peso, repeticoes) VALUES (?, ?, ?, ?, ?)", 
                  (data_hora, form_grupo, exercicio, float(peso), int(repeticoes)))
        conn.commit()
        conn.close()
        return redirect(url_for('musculacao_registar', grupo=form_grupo))

    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    return render_template('musculacao.html', step='registar', grupo=grupo, agora_str=agora_str)

@app.route('/cardio')
def cardio_menu():
    return render_template('cardio.html', step='menu')

@app.route('/cardio/passadeira')
def cardio_passadeira():
    return render_template('cardio.html', step='passadeira_menu')

@app.route('/cardio/registar', methods=['GET', 'POST'])
def cardio_registar():
    tipo = request.args.get('tipo', 'Estrada')
    subtipo = request.args.get('subtipo', '')
    
    titulo = f"Passadeira ({subtipo})" if tipo == 'Passadeira' else "Estrada"

    if request.method == 'POST':
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f_tipo = request.form.get('tipo', tipo)
        f_subtipo = request.form.get('subtipo', subtipo)
        
        if 'apagar_id' in request.form:
            registo_id = request.form['apagar_id']
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM cardio WHERE id = ?", (registo_id,))
            conn.commit()
            conn.close()
        else:
            duracao_min = request.form['duracao_min']
            distancia_km = request.form['distancia_km']
            kcal = request.form.get('kcal', 0.0)
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO cardio (data_hora, tipo, subtipo, duracao_min, distancia_km, kcal) VALUES (?, ?, ?, ?, ?, ?)", 
                      (data_hora, f_tipo, f_subtipo if f_subtipo else None, float(duracao_min), float(distancia_km) if distancia_km else 0.0, float(kcal) if kcal else 0.0))
            conn.commit()
            conn.close()
        
        if f_tipo == 'Passadeira':
            gerar_grafico_cardio(f_tipo, f_subtipo)
        else:
            gerar_grafico_cardio(f_tipo)
            
        return redirect(url_for('cardio_registar', tipo=f_tipo, subtipo=f_subtipo))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if tipo == 'Passadeira':
        registos_raw = c.execute("SELECT id, data_hora, duracao_min, distancia_km, kcal FROM cardio WHERE tipo = ? AND subtipo = ? ORDER BY data_hora DESC", (tipo, subtipo)).fetchall()
        grafico_path = gerar_grafico_cardio(tipo, subtipo)
        img_filename = f"cardio_{tipo.lower()}_{subtipo.lower()}_evolucao.png"
    else:
        registos_raw = c.execute("SELECT id, data_hora, duracao_min, distancia_km FROM cardio WHERE tipo = ? ORDER BY data_hora DESC", (tipo,)).fetchall()
        grafico_path = gerar_grafico_cardio(tipo)
        img_filename = f"cardio_{tipo.lower()}_evolucao.png"
    conn.close()

    registos = []
    for r in registos_raw:
        r_dict = dict(r)
        r_dict['data_formatada'] = datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        registos.append(r_dict)

    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    timestamp = datetime.now().timestamp()

    return render_template('cardio.html', step='registar', tipo=tipo, subtipo=subtipo, titulo=titulo, 
                           agora_str=agora_str, grafico_path=grafico_path, img_filename=img_filename, 
                           registos=registos, timestamp=timestamp)

@app.route('/peso', methods=['GET', 'POST'])
def peso_atual():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        if 'peso' in request.form:
            data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            peso = request.form['peso']
            c.execute("INSERT INTO peso_corporal (data_hora, peso) VALUES (?, ?)", (data_hora, float(peso)))
            conn.commit()
        elif 'apagar_id' in request.form:
            registo_id = request.form['apagar_id']
            c.execute("DELETE FROM peso_corporal WHERE id = ?", (registo_id,))
            conn.commit()
        
        conn.close()
        gerar_grafico_peso()
        return redirect(url_for('peso_atual'))

    registos_raw = c.execute("SELECT id, data_hora, peso FROM peso_corporal ORDER BY data_hora DESC").fetchall()
    conn.close()

    registos = []
    for r in registos_raw:
        r_dict = dict(r)
        r_dict['data_formatada'] = datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        registos.append(r_dict)

    grafico_path = gerar_grafico_peso()
    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    timestamp = datetime.now().timestamp()

    return render_template('peso.html', agora_str=agora_str, grafico_path=grafico_path, 
                           registos=registos, timestamp=timestamp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)