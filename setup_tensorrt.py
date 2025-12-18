"""
Script para exportar modelo YOLO para TensorRT e atualizar configuração.

Uso:
    python setup_tensorrt.py <caminho_modelo.pt>

Exemplo:
    python setup_tensorrt.py yolo-models/yolov12n-face.pt
"""

import sys
import os
from pathlib import Path


def check_virtual_env():
    """Verifica se o script está sendo executado em um ambiente virtual."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("⚠️  AVISO: Este script não está sendo executado em um ambiente virtual")
        print("   Certifique-se de ativar o ambiente virtual antes de executar:")
        print()
        if os.name == 'nt':  # Windows
            print("   venv\\Scripts\\activate")
            print("   python setup_tensorrt.py <modelo.pt>")
        else:  # Linux/macOS
            print("   source venv/bin/activate")
            print("   python setup_tensorrt.py <modelo.pt>")
        print()
        print("   Ou execute através dos scripts de setup:")
        print("   - Windows: setup.bat")
        print("   - Linux/macOS: bash setup.sh")
        print()
    
    return in_venv


def check_gpu_available():
    """Verifica se há GPU CUDA disponível."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU CUDA detectada: {gpu_name} ({gpu_count} device(s))")
            return True
        else:
            print("ℹ️  CUDA disponível mas nenhuma GPU detectada")
            return False
    except ImportError:
        print("⚠️  PyTorch não instalado - impossível verificar GPU")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar GPU: {e}")
        return False


def export_to_tensorrt(model_path):
    """
    Exporta modelo YOLO para TensorRT.
    
    :param model_path: Caminho do arquivo .pt do modelo YOLO
    :return: Caminho do arquivo .engine gerado ou None se falhar
    """
    try:
        from ultralytics import YOLO  # type: ignore
        
        model_path = Path(model_path)
        if not model_path.exists():
            print(f"❌ Arquivo de modelo não encontrado: {model_path}")
            return None
        
        print(f"➡️  Carregando modelo: {model_path}")
        model = YOLO(str(model_path))
        
        # Exporta para TensorRT na mesma pasta do modelo original
        print(f"➡️  Exportando para TensorRT (FP16)...")
        print("   Isso pode levar alguns minutos na primeira vez...")
        
        export_path = model.export(
            format='engine',
            half=True,  # FP16 precision
            workspace=4,  # 4GB workspace
            device=0,  # GPU 0
            simplify=True,
            verbose=False
        )
        
        print(f"✅ Modelo exportado com sucesso: {export_path}")
        return export_path
        
    except ImportError as e:
        print(f"❌ Erro ao importar ultralytics: {e}")
        print("   Certifique-se de que o ultralytics está instalado")
        return None
    except Exception as e:
        print(f"❌ Erro ao exportar modelo para TensorRT: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_config_tensorrt(config_path='config.yaml'):
    """
    Atualiza arquivo de configuração para habilitar TensorRT.
    
    :param config_path: Caminho do arquivo config.yaml
    """
    try:
        import yaml
        
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"⚠️  Arquivo de configuração não encontrado: {config_path}")
            return False
        
        print(f"➡️  Atualizando configuração: {config_path}")
        
        # Lê configuração atual
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Atualiza configuração do TensorRT
        if 'tensorrt' not in config:
            config['tensorrt'] = {}
        
        config['tensorrt']['enabled'] = True
        
        # Salva configuração atualizada
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✅ Configuração atualizada: tensorrt.enabled = true")
        return True
        
    except ImportError:
        print("❌ PyYAML não instalado - impossível atualizar configuração")
        return False
    except Exception as e:
        print(f"❌ Erro ao atualizar configuração: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal do script."""
    print("=" * 80)
    print("SETUP TENSORRT - Exportação de Modelo YOLO para TensorRT")
    print("=" * 80)
    print()
    
    # Verifica se está em ambiente virtual
    check_virtual_env()
    
    # Verifica argumentos
    if len(sys.argv) < 2:
        print("❌ Uso: python setup_tensorrt.py <caminho_modelo.pt>")
        print()
        print("Exemplo:")
        print("  python setup_tensorrt.py yolo-models/yolov12n-face.pt")
        sys.exit(1)
    
    model_path = sys.argv[1]
    
    # Verifica GPU
    print("🔍 Verificando disponibilidade de GPU...")
    if not check_gpu_available():
        print()
        print("⚠️  Nenhuma GPU CUDA detectada - TensorRT não será habilitado")
        print("   O sistema continuará usando o modelo YOLO padrão")
        sys.exit(0)
    
    print()
    
    # Exporta modelo para TensorRT
    print("🚀 Iniciando exportação para TensorRT...")
    engine_path = export_to_tensorrt(model_path)
    
    if engine_path is None:
        print()
        print("⚠️  Falha na exportação - TensorRT não será habilitado")
        print("   O sistema continuará usando o modelo YOLO padrão")
        sys.exit(0)
    
    print()
    
    # Atualiza configuração
    print("⚙️  Atualizando arquivo de configuração...")
    if update_config_tensorrt():
        print()
        print("=" * 80)
        print("✅ SETUP TENSORRT CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
        print()
        print("O modelo TensorRT será usado automaticamente na próxima execução.")
        print(f"Arquivo engine: {engine_path}")
        print()
    else:
        print()
        print("⚠️  Modelo exportado mas configuração não atualizada")
        print("   Você pode habilitar TensorRT manualmente em config.yaml")
        print()


if __name__ == "__main__":
    main()
