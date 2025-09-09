"""
Script para baixar e configurar Redis localmente no projeto
"""
import os
import zipfile
import urllib.request
import logging

def download_redis():
    """Baixa Redis para Windows se não estiver presente"""
    
    # Verifica se Redis já existe
    redis_paths = [
        "redis-server.exe",
        "redis/redis-server.exe", 
        "Redis/redis-server.exe",
        "redis-windows/redis-server.exe"
    ]
    
    for path in redis_paths:
        if os.path.exists(path):
            print(f"✅ Redis já encontrado em: {path}")
            return True
    
    print("📥 Redis não encontrado, baixando...")
    
    try:
        # URL do Redis para Windows (versão estável)
        redis_url = "https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip"
        zip_filename = "redis-windows.zip"
        extract_folder = "redis-windows"
        
        print(f"🔽 Baixando Redis de: {redis_url}")
        
        # Baixa o arquivo
        urllib.request.urlretrieve(redis_url, zip_filename)
        print(f"✅ Download concluído: {zip_filename}")
        
        # Extrai o arquivo
        print(f"📂 Extraindo para: {extract_folder}")
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        
        # Remove o arquivo zip
        os.remove(zip_filename)
        print(f"🗑️ Arquivo zip removido")
        
        # Verifica se foi extraído corretamente
        redis_exe = os.path.join(extract_folder, "redis-server.exe")
        redis_conf = os.path.join(extract_folder, "redis.windows.conf")

        if os.path.exists(redis_exe):
            print(f"✅ Redis executável encontrado: {redis_exe}")

            if os.path.exists(redis_conf):
                print(f"✅ Arquivo de configuração encontrado: {redis_conf}")
            else:
                print(f"⚠️ Arquivo de configuração não encontrado: {redis_conf}")
                print("Redis funcionará com configurações padrão")

            return True
        else:
            print(f"❌ Erro: redis-server.exe não encontrado após extração")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao baixar Redis: {e}")
        return False

def test_redis():
    """Testa se Redis pode ser iniciado"""
    import subprocess
    import time

    # Finaliza processos Redis existentes
    try:
        if os.name == 'nt':
            subprocess.run(
                ["taskkill", "/F", "/IM", "redis-server.exe"],
                capture_output=True,
                check=False
            )
            print("🔄 Processos Redis existentes finalizados")
    except:
        pass

    redis_paths = [
        ("redis-windows/redis-server.exe", "redis-windows/redis.windows.conf"),
        ("redis-windows\\redis-server.exe", "redis-windows\\redis.windows.conf"),  # Windows paths
        ("redis-server.exe", "redis.windows.conf"),
        ("Redis/redis-server.exe", "Redis/redis.windows.conf")
    ]

    redis_exe = None
    redis_conf = None

    for exe_path, conf_path in redis_paths:
        if os.path.exists(exe_path):
            redis_exe = exe_path
            if os.path.exists(conf_path):
                redis_conf = conf_path
            break

    if not redis_exe:
        print("❌ Redis não encontrado para teste")
        return False

    try:
        # Converte para caminhos absolutos
        abs_exe_path = os.path.abspath(redis_exe)
        abs_conf_path = os.path.abspath(redis_conf) if redis_conf else None

        # Monta comando com caminhos absolutos
        if abs_conf_path and os.path.exists(abs_conf_path):
            cmd = [abs_exe_path, abs_conf_path]
            print(f"🧪 Testando Redis: {abs_exe_path} {abs_conf_path}")
        else:
            cmd = [abs_exe_path]
            print(f"🧪 Testando Redis: {abs_exe_path} (sem configuração)")

        # Inicia Redis em background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
            cwd=os.getcwd()  # Usa diretório atual
        )
        
        # Aguarda um pouco
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ Redis iniciado com sucesso!")
            
            # Testa conexão
            try:
                import redis
                # Usa localhost para teste local (setup_redis.py é só para Windows)
                client = redis.Redis(host='localhost', port=6379, db=0)
                client.ping()
                print("✅ Conexão com Redis testada com sucesso!")
                
                # Encerra processo de teste
                process.terminate()
                process.wait(timeout=5)
                print("✅ Teste concluído")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao conectar com Redis: {e}")
                process.terminate()
                return False
        else:
            print("❌ Redis não conseguiu iniciar")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar Redis: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Configurando Redis para AgentGraph...")
    print("=" * 50)
    
    # 1. Baixar Redis se necessário
    if download_redis():
        print("\n🧪 Testando Redis...")
        
        # 2. Testar Redis
        if test_redis():
            print("\n✅ Redis configurado e testado com sucesso!")
            print("\n📋 Próximos passos:")
            print("1. Execute: python app.py")
            print("2. O Redis será iniciado automaticamente")
            print("3. Acesse Flower em: http://localhost:5555")
        else:
            print("\n❌ Redis baixado mas falhou no teste")
            print("Tente executar manualmente: redis-windows/redis-server.exe")
    else:
        print("\n❌ Falha ao configurar Redis")
        print("Baixe manualmente de: https://github.com/microsoftarchive/redis/releases")

if __name__ == "__main__":
    main()
