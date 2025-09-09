#!/usr/bin/env python3
"""
Verifica o conteúdo do SQLite
"""

import sqlite3

def check_sqlite():
    try:
        conn = sqlite3.connect('/shared-data/dataset_1/data.db')
        cursor = conn.cursor()
        
        # Listar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tabelas encontradas: {[t[0] for t in tables]}")
        
        if tables:
            table_name = tables[0][0]
            print(f"Verificando tabela: {table_name}")
            
            # Contar registros
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f"Registros na tabela {table_name}: {count}")
            
            # Mostrar estrutura
            cursor.execute(f'PRAGMA table_info({table_name})')
            columns = cursor.fetchall()
            print(f"Colunas: {[(col[1], col[2]) for col in columns]}")
            
            # Mostrar primeiros registros
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
            rows = cursor.fetchall()
            print(f"Primeiros registros: {rows}")
        
        conn.close()
        print("✅ SQLite verificado com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao verificar SQLite: {e}")

if __name__ == "__main__":
    check_sqlite()
