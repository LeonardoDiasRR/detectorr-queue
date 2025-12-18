# Sistema de Detecção Facial com RTSP e FindFace

Sistema de detecção e rastreamento facial em tempo real que captura streams RTSP, processa com YOLO-face + ByteTrack e envia os melhores eventos ao FindFace.

## 🏗️ Arquitetura

O sistema foi implementado seguindo princípios de **Domain-Driven Design (DDD)** com as seguintes camadas:

```
src/
├── domain/              # Entidades, Value Objects, Repositories (interfaces)
│   ├── entities/        # Camera, Frame, Event, Track
│   ├── repositories/    # Interfaces de repositórios
│   ├── services/        # Serviços de domínio (FaceQualityService)
│   └── value_objects/   # VOs imutáveis (IdVO, BboxVO, etc)
│
├── application/         # Use Cases e lógica de orquestração
│   ├── queues/          # Filas thread-safe (Frame, Event, Findface)
│   ├── use_cases/       # Use Cases especializados
│   └── orchestrator.py  # Orquestrador principal
│
└── infrastructure/      # Implementações concretas
    ├── clients/         # FindfaceMulti (SDK)
    ├── config/          # ConfigLoader, Settings
    └── repositories/    # CameraRepositoryFindface
```

## 🔄 Fluxo de Processamento

```
1. RTSP Stream → FrameQueue
   ↓ (StreamCameraUseCase - 1 thread por câmera)
   
2. FrameQueue → Detecção YOLO + ByteTrack → EventQueue
   ↓ (DetectFacesUseCase - 1 thread por GPU)
   
3. EventQueue → Gerenciamento de Tracks → FindfaceQueue
   ↓ (ManageTracksUseCase - 1 thread global)
   
4. FindfaceQueue → Envio ao FindFace
   ↓ (SendToFindfaceUseCase - N threads configuráveis)
```

## ⚙️ Configuração

### 1. Variáveis de Ambiente (.env)

Copie o arquivo `.env.example` para `.env` e preencha:

```bash
FINDFACE_URL=https://seu-servidor-findface
FINDFACE_USER=seu-usuario
FINDFACE_PASSWORD=sua-senha
FINDFACE_UUID=seu-uuid-dispositivo
```

### 2. Arquivo de Configuração (config.yaml)

```yaml
processing:
  cpu_batch_size: 1          # Batch size para CPU
  gpu_batch_size: 32         # Batch size para GPU
  gpu_devices: [0]           # Lista de GPUs (Round-Robin)

performance:
  detection_skip_frames: 2   # Processa a cada N frames (1 = todos)
  inference_size: 640        # Tamanho de inferência (640 ou 1280)

yolo:
  model_path: "yolo-models/yolov12n-face.pt"
  confidence_threshold: 0.5
  iou_threshold: 0.45

tracking:
  iou_threshold: 0.3
  max_age: 30                # Frames sem detecção antes de perder track
  min_hits: 3                # Detecções mínimas para confirmar track
  max_frames: 500            # Força encerramento após N frames

filter:
  min_bbox_width: 30         # Largura mínima da bbox (pixels)
  min_confidence: 0.5        # Confiança mínima

track:
  min_movement_percentage: 0.1
  min_movement_pixels: 50.0

queues:
  frame_queue_max_size: 100
  event_queue_max_size: 1000
  findface_queue_max_size: 100

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

camera:
  prefix: "TESTE"            # Prefixo para filtrar câmeras do FindFace
  rtsp_reconnect_delay: 5    # Delay entre reconexões (segundos)
  rtsp_max_retries: 3        # Máximo de tentativas de reconexão
```

## 🚀 Instalação e Execução

### 1. Instalar Dependências

```bash
# Windows
setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### 2. Executar Aplicação

```bash
python run.py
```

## 📊 Funcionamento Detalhado

### Threads e Distribuição de Carga

- **1 thread por câmera**: Captura frames do RTSP
- **1 thread por GPU**: Executa detecção YOLO + ByteTrack em lote
- **1 thread global**: Gerencia tracks e seleciona melhor evento
- **N threads**: Enviam eventos ao FindFace (padrão: 2)

### Gerenciamento de Tracks

Cada track armazena **3 eventos**:
- **Primeiro evento**: Face detectada inicialmente
- **Melhor evento**: Face com maior score de qualidade
- **Último evento**: Face detectada mais recentemente

O track é finalizado quando:
- ByteTrack perde o ID (após `max_age` frames sem detecção)
- Atinge `max_frames` frames consecutivos

### Seleção e Envio ao FindFace

1. Track finalizado → verifica se tem movimento suficiente
2. Se válido → seleciona melhor evento (maior qualidade)
3. Enfileira na `FindfaceQueue`
4. Workers enviam ao FindFace via SDK
5. Sucesso/falha registrado em log

## 🛑 Parada Graceful

A aplicação responde a `SIGTERM` e `SIGINT` (Ctrl+C):

1. Sinaliza parada para todas as threads
2. Aguarda processamento de filas pendentes (timeout: 10s)
3. Aguarda finalização de todas as threads
4. Faz logout do FindFace
5. Encerra aplicação

## 📝 Logs

Logs são salvos em:
- **Console**: Saída padrão
- **Arquivo**: `application.log`

Níveis de log configuráveis em `config.yaml`.

## 🔧 Troubleshooting

### Fila de frames cheia
- Aumente `frame_queue_max_size`
- Aumente `detection_skip_frames`
- Adicione mais GPUs

### Tracks sem movimento
- Ajuste `min_movement_pixels` e `min_movement_percentage`

### Baixa taxa de detecção
- Reduza `confidence_threshold`
- Reduza `min_bbox_width`

### Falhas de conexão RTSP
- Verifique URL da câmera
- Aumente `rtsp_max_retries`
- Aumente `rtsp_reconnect_delay`

## 📄 Licença

Proprietário - Uso interno apenas.
