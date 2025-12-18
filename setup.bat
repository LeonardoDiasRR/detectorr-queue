@echo off
SETLOCAL

:: Caminho do ambiente virtual
SET VENV_DIR=venv

echo [1/4] Criando ambiente virtual em %VENV_DIR%...
python -m venv %VENV_DIR%
IF ERRORLEVEL 1 (
    echo Erro ao criar o ambiente virtual.
    EXIT /B 1
)

echo [2/5] Atualizando pip...
%VENV_DIR%\Scripts\python.exe -m pip install --upgrade pip
IF ERRORLEVEL 1 (
    echo Erro ao atualizar pip.
    EXIT /B 1
)

echo [3/5] Detectando GPU CUDA...
%VENV_DIR%\Scripts\python.exe -c "import torch; print('CUDA disponível' if torch.cuda.is_available() else 'CUDA não disponível')" 2>nul
IF ERRORLEVEL 1 (
    echo PyTorch não instalado ainda. Verificando GPU via nvidia-smi...
    nvidia-smi >nul 2>&1
    IF ERRORLEVEL 1 (
        echo CPU detectada. Usando requirements_cpu.txt
        SET REQUIREMENTS_FILE=requirements_cpu.txt
    ) ELSE (
        echo GPU CUDA detectada. Usando requirements_gpu.txt
        SET REQUIREMENTS_FILE=requirements_gpu.txt
    )
) ELSE (
    %VENV_DIR%\Scripts\python.exe -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>nul
    IF ERRORLEVEL 1 (
        echo CPU detectada. Usando requirements_cpu.txt
        SET REQUIREMENTS_FILE=requirements_cpu.txt
    ) ELSE (
        echo GPU CUDA detectada. Usando requirements_gpu.txt
        SET REQUIREMENTS_FILE=requirements_gpu.txt
    )
)

echo [4/4] Instalando dependências de %REQUIREMENTS_FILE%...
IF EXIST %REQUIREMENTS_FILE% (
    %VENV_DIR%\Scripts\pip.exe install -r %REQUIREMENTS_FILE%
    IF ERRORLEVEL 1 (
        echo Erro ao instalar dependências.
        EXIT /B 1
    )
    echo Dependências instaladas com sucesso.
) ELSE (
    echo Arquivo %REQUIREMENTS_FILE% não encontrado.
    echo Tentando instalar requirements.txt como fallback...
    IF EXIST requirements.txt (
        %VENV_DIR%\Scripts\pip.exe install -r requirements.txt
        IF ERRORLEVEL 1 (
            echo Erro ao instalar dependências.
            EXIT /B 1
        )
    ) ELSE (
        echo Nenhum arquivo de requisitos encontrado.
        EXIT /B 1
    )
)

echo.
echo [5/7] Copiando arquivos de configuração...
IF NOT EXIST config.yaml (
    IF EXIST config-sample.yaml (
        copy config-sample.yaml config.yaml >nul
        echo ✅ config.yaml criado a partir de config-sample.yaml
    ) ELSE (
        echo ⚠️ Arquivo config-sample.yaml não encontrado
    )
) ELSE (
    echo ℹ️ config.yaml já existe - mantendo arquivo atual
)

IF NOT EXIST .env (
    IF EXIST .env-exemplo (
        copy .env-exemplo .env >nul
        echo ✅ .env criado a partir de .env-exemplo
    ) ELSE (
        echo ⚠️ Arquivo .env-exemplo não encontrado
    )
) ELSE (
    echo ℹ️ .env já existe - mantendo arquivo atual
)

echo.
echo [6/7] Extraindo caminho do modelo de detecção...
FOR /F "tokens=2 delims=:" %%A IN ('findstr /C:"model_path:" config.yaml ^| findstr "modelo_deteccao" -A 1') DO (
    SET MODEL_PATH=%%A
)
SET MODEL_PATH=%MODEL_PATH: =%
SET MODEL_PATH=%MODEL_PATH:"=%
echo Modelo de detecção: %MODEL_PATH%

echo.
echo [7/7] Configurando TensorRT (se GPU disponível)...
IF EXIST %MODEL_PATH% (
    %VENV_DIR%\Scripts\python.exe setup_tensorrt.py %MODEL_PATH%
) ELSE (
    echo ⚠️ Modelo não encontrado: %MODEL_PATH%
    echo TensorRT não será configurado - você pode executar manualmente:
    echo   %VENV_DIR%\Scripts\python.exe setup_tensorrt.py ^<caminho_modelo^>
)

echo.
echo ✅ Setup concluído com sucesso.
ENDLOCAL
