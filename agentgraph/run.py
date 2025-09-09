#!/usr/bin/env python3
"""
Script de inicialização inteligente do AgentGraph
Detecta o ambiente e executa o comando apropriado
"""
import os
import sys
import subprocess
import argparse
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_docker_available() -> bool:
    """Verifica se Docker está disponível"""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def is_docker_running() -> bool:
    """Verifica se Docker está rodando"""
    try:
        subprocess.run(["docker", "info"], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_env_file() -> bool:
    """Verifica se arquivo .env existe"""
    return os.path.exists(".env")

def run_local():
    """Executa aplicação localmente (Windows)"""
    logging.info("🖥️ Iniciando AgentGraph localmente...")
    
    # Verifica se Python está disponível
    try:
        subprocess.run([sys.executable, "--version"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        logging.error("❌ Python não encontrado")
        return False
    
    # Verifica dependências
    try:
        import gradio
        import celery
        import redis
        logging.info("✅ Dependências Python verificadas")
    except ImportError as e:
        logging.error(f"❌ Dependência não encontrada: {e}")
        logging.info("💡 Execute: pip install -r requirements.txt")
        return False
    
    # Executa aplicação
    try:
        logging.info("🚀 Iniciando aplicação...")
        subprocess.run([sys.executable, "app.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erro ao executar aplicação: {e}")
        return False
    except KeyboardInterrupt:
        logging.info("🛑 Aplicação interrompida pelo usuário")
        return True

def run_docker():
    """Executa aplicação no Docker"""
    logging.info("🐳 Iniciando AgentGraph no Docker...")
    
    # Verifica se .env existe
    if not check_env_file():
        logging.warning("⚠️ Arquivo .env não encontrado")
        logging.info("💡 Crie um arquivo .env com suas API keys")
        logging.info("💡 Exemplo:")
        logging.info("   OPENAI_API_KEY=sua_chave_aqui")
        logging.info("   ANTHROPIC_API_KEY=sua_chave_aqui")
        logging.info("   HUGGINGFACE_API_KEY=sua_chave_aqui")
    
    # Para containers existentes
    try:
        logging.info("🧹 Parando containers existentes...")
        subprocess.run(["docker-compose", "down"], capture_output=True)
    except subprocess.CalledProcessError:
        pass
    
    # Constrói e inicia containers
    try:
        logging.info("🔨 Construindo imagem Docker...")
        subprocess.run(["docker-compose", "build"], check=True)
        
        logging.info("🚀 Iniciando containers...")
        subprocess.run(["docker-compose", "up"], check=True)
        return True
        
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Erro ao executar Docker: {e}")
        return False
    except KeyboardInterrupt:
        logging.info("🛑 Containers interrompidos pelo usuário")
        
        # Para containers
        try:
            logging.info("🧹 Parando containers...")
            subprocess.run(["docker-compose", "down"], capture_output=True)
        except subprocess.CalledProcessError:
            pass
        
        return True

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="AgentGraph - Inicialização Inteligente")
    parser.add_argument(
        "--mode", 
        choices=["auto", "local", "docker"], 
        default="auto",
        help="Modo de execução (padrão: auto)"
    )
    parser.add_argument(
        "--force-docker", 
        action="store_true",
        help="Força execução no Docker mesmo se não estiver rodando"
    )
    
    args = parser.parse_args()
    
    print("🤖 AgentGraph - Plataforma Multi-Agente LangGraph")
    print("=" * 50)
    
    if args.mode == "local":
        # Força execução local
        logging.info("🎯 Modo local forçado")
        success = run_local()
        
    elif args.mode == "docker":
        # Força execução Docker
        logging.info("🎯 Modo Docker forçado")
        if not is_docker_available():
            logging.error("❌ Docker não está disponível")
            logging.info("💡 Instale Docker Desktop: https://www.docker.com/products/docker-desktop/")
            return 1
        
        if not is_docker_running() and not args.force_docker:
            logging.error("❌ Docker não está rodando")
            logging.info("💡 Inicie o Docker Desktop ou use --force-docker")
            return 1
        
        success = run_docker()
        
    else:
        # Modo automático - detecta melhor opção
        logging.info("🔍 Detectando melhor modo de execução...")
        
        if is_docker_available() and is_docker_running():
            logging.info("✅ Docker disponível e rodando - usando Docker")
            success = run_docker()
        else:
            if not is_docker_available():
                logging.info("ℹ️ Docker não disponível - usando modo local")
            else:
                logging.info("ℹ️ Docker não está rodando - usando modo local")
            success = run_local()
    
    if success:
        logging.info("✅ AgentGraph finalizado com sucesso")
        return 0
    else:
        logging.error("❌ AgentGraph finalizado com erro")
        return 1

if __name__ == "__main__":
    sys.exit(main())
