import os
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS plano_exercicios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_semana TEXT NOT NULL,
            grupo TEXT NOT NULL,
            exercicio TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercicios_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT NOT NULL,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

iniciar_db()

def normalizar_exercicio(nome):
    if not nome or not nome.strip():
        return ""
    
    nome_limpo = nome.strip().lower()
    
    correcoes = {
        "sipino": "Supino",
        "supino": "Supino",
        "supino inclinado": "Supino Inclinado",
        "sipino inclinado": "Supino Inclinado",
        "supino reto": "Supino Reto",
        "curl bicep": "Curl de Bíceps",
        "curl biceps": "Curl de Bíceps"
    }
    
    if nome_limpo in correcoes:
        return correcoes[nome_limpo]
    
    return " ".join([ palavra.capitalize() for palavra in nome_limpo.split() ])

def registar_catalogo(grupo, nome):
    nome_normalizado = normalizar_exercicio(nome)
    if not nome_normalizado:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO exercicios_catalogo (grupo, nome) VALUES (?, ?)", (grupo, nome_normalizado))
    conn.commit()
    conn.close()

def calcular_streak_treino():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = "SELECT DISTINCT date(data_hora) as dia FROM musculacao UNION SELECT DISTINCT date(data_hora) as dia FROM cardio ORDER BY dia DESC"
    dias_raw = c.execute(query).fetchall()
    conn.close()
    
    if not dias_raw:
        return 0
        
    dias_treino = [datetime.strptime(row['dia'], '%Y-%m-%d').date() for row in dias_raw]
    
    hoje = datetime.now().date()
    ontem = hoje - timedelta(days=1)
    
    # Se não treinou hoje nem ontem, a streak quebra imediatamente a 0
    if dias_treino[0] != hoje and dias_treino[0] != ontem:
        return 0
        
    streak = 0
    dia_esperado = dias_treino[0]
    
    for d in dias_treino:
        if d == dia_esperado:
            streak += 1
            dia_esperado -= timedelta(days=1)
        elif d < dia_esperado:
            break
            
    return streak

def gerar_grafico_peso():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT data_hora, peso FROM peso_corporal ORDER BY data_hora ASC", conn)
    conn.close()

    if df.empty:
        return None

    df['data_formatada'] = pd.to_datetime(df['data_hora']).dt.strftime('%d/%m %H:%M')

    plt.figure(figsize=(10, 4.5))
    plt.plot(df['data_formatada'], df['peso'], marker='o', linestyle='-', color='#3b82f6', linewidth=2.5, markersize=6)
    
    plt.title('Evolução do Peso Corporal', fontsize=14, color='white', pad=15)
    plt.xlabel('Data e Hora', fontsize=11, color='#8e8e93')
    plt.ylabel('Peso (kg)', fontsize=11, color='#8e8e93')
    
    plt.gca().set_facecolor('#1c1c1e')
    plt.gcf().patch.set_facecolor('#000000')
    plt.tick_params(colors='#8e8e93', which='both', labelsize=8)
    plt.xticks(rotation=30)
    plt.grid(True, linestyle='--', alpha=0.2, color='white')
    
    for spine in plt.gca().spines.values():
        spine.set_color('#38383a')

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
    
    plt.plot(df['data_formatada'], df['duracao_min'], marker='o', linestyle='-', color='#ff9f0a', linewidth=2, label='Duração (min)')
    if 'distancia_km' in df.columns:
        plt.plot(df['data_formatada'], df['distancia_km'], marker='s', linestyle='-', color='#30d158', linewidth=2, label='Distância (km)')
    if 'kcal' in df.columns and subtipo:
        plt.plot(df['data_formatada'], df['kcal'], marker='^', linestyle='-', color='#ff453a', linewidth=2, label='Calorias (kcal)')

    plt.title(f'Evolução: {titulo_base}', fontsize=14, color='white', pad=15)
    plt.xlabel('Data e Hora', fontsize=11, color='#8e8e93')
    plt.ylabel('Valores', fontsize=11, color='#8e8e93')
    
    plt.gca().set_facecolor('#1c1c1e')
    plt.gcf().patch.set_facecolor('#000000')
    plt.tick_params(colors='#8e8e93', which='both', labelsize=8)
    plt.xticks(rotation=30)
    plt.grid(True, linestyle='--', alpha=0.2, color='white')
    plt.legend(facecolor='#1c1c1e', edgecolor='#38383a', labelcolor='white')
    
    for spine in plt.gca().spines.values():
        spine.set_color('#38383a')

    plt.tight_layout()
    plt.savefig(nome_ficheiro, dpi=150)
    plt.close()
    return nome_ficheiro

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    pesos_raw = c.execute("SELECT peso, data_hora FROM peso_corporal ORDER BY data_hora DESC LIMIT 2").fetchall()
    
    peso_atual = None
    variacao_peso = None
    if len(pesos_raw) > 0:
        peso_atual = pesos_raw[0]['peso']
        if len(pesos_raw) > 1:
            peso_anterior = pesos_raw[1]['peso']
            variacao_peso = round(peso_atual - peso_anterior, 1)

    query_musc = "SELECT data_hora FROM musculacao WHERE datetime(data_hora) >= datetime('now', '-7 days')"
    query_cardio = "SELECT data_hora FROM cardio WHERE datetime(data_hora) >= datetime('now', '-7 days')"
    
    timestamps_raw = c.execute(query_musc).fetchall() + c.execute(query_cardio).fetchall()

    total_treinos_semana = 0
    if timestamps_raw:
        timestamps = [datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S') for r in timestamps_raw]
        timestamps.sort()
        
        total_treinos_semana = 1
        last_dt = timestamps[0]
        for dt in timestamps[1:]:
            if (dt - last_dt) > timedelta(hours=2):
                total_treinos_semana += 1
            last_dt = dt

    dias_pt = {
        'Monday': 'Segunda-feira',
        'Tuesday': 'Terça-feira',
        'Wednesday': 'Quarta-feira',
        'Thursday': 'Quinta-feira',
        'Friday': 'Sexta-feira',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    dia_ingles = datetime.now().strftime('%A')
    dia_hoje = dias_pt.get(dia_ingles, 'Segunda-feira')

    exercicios_hoje = c.execute("SELECT id, grupo, exercicio FROM plano_exercicios WHERE dia_semana = ?", (dia_hoje,)).fetchall()
    streak_dias = calcular_streak_treino()

    conn.close()

    return render_template('index.html', 
                           peso_atual=peso_atual, 
                           variacao_peso=variacao_peso, 
                           total_treinos_semana=total_treinos_semana,
                           dia_hoje=dia_hoje,
                           exercicios_hoje=exercicios_hoje,
                           streak_dias=streak_dias)

@app.route('/plano', methods=['GET', 'POST'])
def plano_semanal():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    dias_ordem = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    grupos_disponiveis = ['Peito', 'Costas', 'Ombros', 'Braços', 'Inferiores', 'Cardio']

    if request.method == 'POST':
        if 'apagar_id' in request.form:
            item_id = request.form['apagar_id']
            c.execute("DELETE FROM plano_exercicios WHERE id = ?", (item_id,))
            conn.commit()
        else:
            dia = request.form.get('dia_semana')
            grupo = request.form.get('grupo')
            exercicio_select = request.form.get('exercicio_select')
            exercicio_novo = request.form.get('exercicio_novo')
            
            exercicio_raw = exercicio_novo if (exercicio_novo and exercicio_novo.strip()) else exercicio_select
            exercicio = normalizar_exercicio(exercicio_raw)
            
            if dia and grupo and exercicio:
                c.execute("INSERT INTO plano_exercicios (dia_semana, grupo, exercicio) VALUES (?, ?, ?)", (dia, grupo, exercicio))
                conn.commit()
                registar_catalogo(grupo, exercicio)
        
        conn.close()
        return redirect(url_for('plano_semanal'))

    exercicios_db = c.execute("SELECT nome FROM exercicios_catalogo ORDER BY nome ASC").fetchall()
    exercicios_existentes = [row['nome'] for row in exercicios_db]

    plano_raw = c.execute("SELECT id, dia_semana, grupo, exercicio FROM plano_exercicios").fetchall()
    conn.close()

    return render_template('plano.html', dias_ordem=dias_ordem, grupos=grupos_disponiveis, 
                           exercicios_existentes=exercicios_existentes, plano_raw=plano_raw)

@app.route('/historico')
def historico_geral():
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    filtro_sql = ""
    params = []
    if data_inicio:
        filtro_sql += " AND data_hora >= ?"
        params.append(data_inicio + " 00:00:00")
    if data_fim:
        filtro_sql += " AND data_hora <= ?"
        params.append(data_fim + " 23:59:59")

    registos = []

    musc_rows = c.execute(f"SELECT id, grupo, exercicio, peso, repeticoes, data_hora FROM musculacao WHERE 1=1 {filtro_sql} ORDER BY data_hora DESC", params).fetchall()
    for r in musc_rows:
        registos.append({
            'id': r['id'],
            'categoria': 'Musculação',
            'titulo': f"{r['grupo']} - {r['exercicio']}",
            'detalhes': f"{r['peso']} kg × {r['repeticoes']} reps",
            'data_hora': r['data_hora'],
            'data_formatada': datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y às %H:%M')
        })

    cardio_rows = c.execute(f"SELECT id, tipo, subtipo, duracao_min, distancia_km, data_hora FROM cardio WHERE 1=1 {filtro_sql} ORDER BY data_hora DESC", params).fetchall()
    for r in cardio_rows:
        titulo_cardio = f"{r['tipo']}" + (f" ({r['subtipo']})" if r['subtipo'] else "")
        registos.append({
            'id': r['id'],
            'categoria': 'Cardio',
            'titulo': titulo_cardio,
            'detalhes': f"{r['duracao_min']} min • {r['distancia_km']} km",
            'data_hora': r['data_hora'],
            'data_formatada': datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y às %H:%M')
        })

    peso_rows = c.execute(f"SELECT id, peso, data_hora FROM peso_corporal WHERE 1=1 {filtro_sql} ORDER BY data_hora DESC", params).fetchall()
    for r in peso_rows:
        registos.append({
            'id': r['id'],
            'categoria': 'Peso',
            'titulo': 'Peso Corporal',
            'detalhes': f"{r['peso']} kg",
            'data_hora': r['data_hora'],
            'data_formatada': datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y às %H:%M')
        })

    conn.close()
    registos.sort(key=lambda x: x['data_hora'], reverse=True)

    return render_template('historico.html', registos=registos, data_inicio=data_inicio, data_fim=data_fim)

@app.route('/historico/apagar', methods=['POST'])
def historico_apagar():
    registo_id = request.form.get('id')
    categoria = request.form.get('categoria')

    tabela_map = {
        'Musculação': 'musculacao',
        'Cardio': 'cardio',
        'Peso': 'peso_corporal'
    }

    tabela = tabela_map.get(categoria)
    if tabela and registo_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(f"DELETE FROM {tabela} WHERE id = ?", (registo_id,))
        conn.commit()
        conn.close()
        
        if tabela == 'peso_corporal':
            gerar_grafico_peso()

    return redirect(url_for('historico_geral'))

@app.route('/musculacao')
def musculacao_menu():
    return render_template('musculacao.html', step='menu')

@app.route('/musculacao/superiores')
def musculacao_superiores():
    return render_template('musculacao.html', step='superiores')

@app.route('/musculacao/grupo/<grupo>')
def musculacao_grupo(grupo):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT exercicio, grupo, MAX(peso) as max_peso, MAX(data_hora) as ultima_data
        FROM musculacao
        WHERE grupo = ?
        GROUP BY exercicio
        ORDER BY ultima_data DESC
    '''
    exercicios_raw = c.execute(query, (grupo,)).fetchall()
    conn.close()

    exercicios = []
    for r in exercicios_raw:
        r_dict = dict(r)
        r_dict['data_formatada'] = datetime.strptime(r['ultima_data'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m %H:%M')
        exercicios.append(r_dict)

    return render_template('musculacao.html', step='grupo_detalhe', grupo=grupo, exercicios=exercicios)

@app.route('/musculacao/exercicio/<path:exercicio_nome>', methods=['GET', 'POST'])
def musculacao_exercicio_detalhe(exercicio_nome):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        if 'apagar_id' in request.form:
            registo_id = request.form['apagar_id']
            c.execute("DELETE FROM musculacao WHERE id = ?", (registo_id,))
            conn.commit()
        else:
            grupo = request.form['grupo']
            peso = request.form['peso']
            repeticoes = request.form['repeticoes']
            data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO musculacao (data_hora, grupo, exercicio, peso, repeticoes) VALUES (?, ?, ?, ?, ?)", 
                      (data_hora, grupo, exercicio_nome, float(peso), int(repeticoes)))
            conn.commit()
            registar_catalogo(grupo, exercicio_nome)

    registos_raw = c.execute("SELECT id, grupo, data_hora, peso, repeticoes FROM musculacao WHERE exercicio = ? ORDER BY data_hora DESC", (exercicio_nome,)).fetchall()
    max_peso = c.execute("SELECT MAX(peso) FROM musculacao WHERE exercicio = ?", (exercicio_nome,)).fetchone()[0]
    grupo_atual = registos_raw[0]['grupo'] if registos_raw else 'Geral'
    
    conn.close()

    registos = []
    for r in registos_raw:
        r_dict = dict(r)
        r_dict['data_formatada'] = datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
        registos.append(r_dict)

    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    timestamp = datetime.now().timestamp()

    return render_template('musculacao.html', step='exercicio_detalhe', exercicio=exercicio_nome, 
                           grupo=grupo_atual, max_peso=max_peso, registos=registos, 
                           agora_str=agora_str, timestamp=timestamp)

@app.route('/musculacao/repetir/<int:registo_id>', methods=['POST'])
def musculacao_repetir(registo_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    anterior = c.execute("SELECT grupo, exercicio, peso, repeticoes FROM musculacao WHERE id = ?", (registo_id,)).fetchone()
    
    if anterior:
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO musculacao (data_hora, grupo, exercicio, peso, repeticoes) VALUES (?, ?, ?, ?, ?)", 
                  (data_hora, anterior['grupo'], anterior['exercicio'], anterior['peso'], anterior['repeticoes']))
        conn.commit()
        exercicio_destino = anterior['exercicio']
    
    conn.close()
    return redirect(url_for('musculacao_exercicio_detalhe', exercicio_nome=exercicio_destino))

@app.route('/musculacao/registar', methods=['GET', 'POST'])
def musculacao_registar():
    grupo = request.args.get('grupo', 'Peito')
    exercicio_pre = request.args.get('exercicio', '')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == 'POST':
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        form_grupo = request.form.get('grupo', grupo)
        
        exercicio_escolhido = request.form.get('exercicio_select')
        exercicio_novo = request.form.get('exercicio_novo')
        
        exercicio_raw = exercicio_novo if (exercicio_novo and exercicio_novo.strip()) else exercicio_escolhido
        exercicio = normalizar_exercicio(exercicio_raw)
        
        peso = request.form['peso']
        repeticoes = request.form['repeticoes']
        
        if exercicio and peso and repeticoes:
            c.execute("INSERT INTO musculacao (data_hora, grupo, exercicio, peso, repeticoes) VALUES (?, ?, ?, ?, ?)", 
                      (data_hora, form_grupo, exercicio, float(peso), int(repeticoes)))
            conn.commit()
            registar_catalogo(form_grupo, exercicio)
        
        conn.close()
        return redirect(url_for('musculacao_grupo', grupo=form_grupo))

    exercicios_db = c.execute("SELECT nome FROM exercicios_catalogo ORDER BY nome ASC").fetchall()
    exercicios_anteriores = [row['nome'] for row in exercicios_db]
    
    conn.close()

    agora_str = datetime.now().strftime('%d/%m/%Y às %H:%M')
    return render_template('musculacao.html', step='registar', grupo=grupo, 
                           exercicio_pre=exercicio_pre,
                           exercicios_anteriores=exercicios_anteriores, agora_str=agora_str)

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
