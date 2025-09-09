#!/usr/bin/env python3
"""
Script de migração simplificado para AgentAPI

Executa migração das tabelas baseado nos modelos SQLAlchemy.
Pode ser executado diretamente ou via Docker Compose.

Uso:
    python migrate.py
    python migrate.py --verify-only
    python migrate.py --seed
"""

import os
import sys
import subprocess

def run_migration():
    """Executa o sistema de migração"""
    try:
        # Executar o módulo de migração
        cmd = [sys.executable, "-m", "api.db.migrate"] + sys.argv[1:]
        
        print("🚀 Executando migração da AgentAPI...")
        print("=" * 60)
        
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print("=" * 60)
            print("✅ Migração concluída com sucesso!")
        else:
            print("=" * 60)
            print("❌ Migração falhou!")
            
        return result.returncode
        
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        return 1

if __name__ == "__main__":
    exit(run_migration())
