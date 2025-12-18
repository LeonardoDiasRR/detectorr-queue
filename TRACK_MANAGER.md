Classe TrackManager
A classe TrackManager é responsável por gerenciar o rastreamento de faces detectadas ao longo de múltiplos frames. Aqui estão suas principais funcionalidades:

Propósito Principal
Associação de eventos a tracks: Liga eventos de detecção facial (objetos Evento) a sequências de rastreamento (objetos Track), identificando se uma face detectada em um novo frame pertence a um track existente ou representa uma nova pessoa.
Atributos
tracks_por_camera: Dicionário que armazena listas de tracks organizadas por ID de câmera, permitindo rastreamento independente para cada fonte de vídeo.
lock: Trava de sincronização (Lock) para garantir acesso thread-safe às estruturas de dados compartilhadas.
event_bus: Barramento de eventos opcional para publicação de eventos de finalização de tracks.
Métodos Públicos
associar_evento(evento: Evento) -> Track
Função: Associa um novo evento de detecção a um track existente ou cria um novo track.
Estratégia de associação:
Busca por sobreposição de bounding boxes (IoU) - prioriza tracks com maior IoU acima do limiar.
Caso não encontre por IoU, busca por distância entre centros - seleciona o track mais próximo dentro do limiar.
Se nenhum track corresponder, cria um novo track.
Validações temporais: Ignora tracks cujo último evento ocorreu há mais de 2 segundos.
atualizar_tracks_inativos(camera_id: int, ativos: set)
Função: Incrementa o contador de frames sem detecção para todos os tracks que não estão no conjunto de tracks ativos.
Finalidade: Controla quando um track deve ser finalizado por inatividade.
coletar_lixo(camera_id: int, ttl_segundos: int = 30)
Função: Remove tracks finalizados da memória após um período configurável (TTL).
Comportamento: Mantém apenas tracks não finalizados ou finalizados recentemente (dentro do TTL), liberando referências de tracks antigos.
Métodos Privados (Cálculos)
_calcular_sobreposicao_bbox(b1, b2) -> float
Calcula a sobreposição entre duas bounding boxes usando a média das áreas ao invés do IoU tradicional.
Retorna valor entre 0.0 (sem sobreposição) e 1.0 (sobreposição total).
_calcular_distancia_entre_centros(b1, b2) -> float
Calcula a distância euclidiana entre os centros de duas bounding boxes.
_calcular_limiar_sobreposicao_bbox(w, h) -> float
Define limiares adaptativos de IoU baseados na resolução do frame:
≤640px: 0.2
≤1280px: 0.15
≤1920px: 0.12
>1920px: 0.1
_calcular_limiar_distancia_centros(w, h) -> float
Calcula o limiar máximo de distância entre centros como 7% da diagonal do frame (configurável).
Thread Safety
Todas as operações críticas utilizam with self.lock para garantir consistência em ambientes multi-threading.


class TrackManager:
    """
    Responsável por associar eventos a tracks existentes ou criar novos.
    """
    def __init__(self, event_bus: Optional["EventBus"] = None):
        self.tracks_por_camera = {}
        self.lock = Lock()
        self.event_bus = event_bus

    def coletar_lixo(self, camera_id: int, ttl_segundos: int = 30) -> None:
        agora = datetime.now()
        with self.lock:
            tracks = self.tracks_por_camera.get(camera_id, [])
            filtrados = []
            for t in tracks:
                if not t.finalizado:
                    filtrados.append(t)
                else:
                    if t.timestamp_finalizacao and (agora - t.timestamp_finalizacao).total_seconds() <= ttl_segundos:
                        filtrados.append(t)
                    # senão, soltamos o track e suas referências
            self.tracks_por_camera[camera_id] = filtrados
            
    def associar_evento(self, evento: Evento) -> Track:
        if not isinstance(evento, Evento):
            raise TypeError("evento deve ser uma instância da classe Evento.")

        camera_id = evento.frame.camera_id
        frame_largura = evento.frame.largura
        frame_altura = evento.frame.altura
        tempo_max = timedelta(seconds=2)
        limiar_iou = self._calcular_limiar_sobreposicao_bbox(frame_largura, frame_altura)
        limiar_dist = self._calcular_limiar_distancia_centros(frame_largura, frame_altura)

        track_por_iou = None
        maior_iou = 0.0
        track_por_distancia = None
        menor_distancia = float('inf')

        with self.lock:
            tracks = [t for t in self.tracks_por_camera.get(camera_id, []) if not t.finalizado]
            self.tracks_por_camera[camera_id] = tracks

            for track in tracks:
                tempo_desde_ultimo_evento = evento.timestamp - track.evento_atual.timestamp
                if tempo_desde_ultimo_evento > tempo_max:
                    continue

                iou = self._calcular_sobreposicao_bbox(track.evento_atual.bbox, evento.bbox)
                if iou >= limiar_iou and iou > maior_iou:
                    track_por_iou = track
                    maior_iou = iou
                else:
                    dist = self._calcular_distancia_entre_centros(track.evento_atual.bbox, evento.bbox)
                    if dist <= limiar_dist and dist < menor_distancia:
                        track_por_distancia = track
                        menor_distancia = dist

            if track_por_iou:
                track_por_iou.atualizar_evento(evento)
                return track_por_iou

            if track_por_distancia:
                track_por_distancia.atualizar_evento(evento)
                return track_por_distancia

            novo_track = Track(evento, event_bus=self.event_bus)
            self.tracks_por_camera.setdefault(camera_id, []).append(novo_track)

            if CONFIG.get("log_ativo", False):
                log_track.info(f"Track #{novo_track.id} criado com o Evento #{evento.id}")

            return novo_track

    def atualizar_tracks_inativos(self, camera_id: int, ativos: set):
        with self.lock:
            for track in self.tracks_por_camera.get(camera_id, []):
                if track not in ativos:
                    track.incrementar_frames_sem_detectar()

    def _calcular_limiar_sobreposicao_bbox(self, w: int, h: int) -> float:
        if w <= 640:
            return 0.2
        elif w <= 1280:
            return 0.15
        elif w <= 1920:
            return 0.12
        else:
            return 0.1

    def _calcular_distancia_entre_centros(self, b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        cx1 = (b1[0] + b1[2]) / 2
        cy1 = (b1[1] + b1[3]) / 2
        cx2 = (b2[0] + b2[2]) / 2
        cy2 = (b2[1] + b2[3]) / 2
        return distance.euclidean((cx1, cy1), (cx2, cy2))

    def _calcular_limiar_distancia_centros(self, w: int, h: int) -> float:
        diagonal = (w**2 + h**2) ** 0.5
        return diagonal * CONFIG.get("limite_distancia_bbox_no_track", 0.07)

    def _calcular_sobreposicao_bbox(self, b1: Tuple[int, int, int, int], b2: Tuple[int, int, int, int]) -> float:
        x1_1, y1_1, x2_1, y2_1 = b1
        x1_2, y1_2, x2_2, y2_2 = b2

        inter_x1 = max(x1_1, x1_2)
        inter_y1 = max(y1_1, y1_2)
        inter_x2 = min(x2_1, x2_2)
        inter_y2 = min(y2_1, y2_2)

        inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        media_area = (area1 + area2) / 2

        return inter_area / media_area if media_area > 0 else 0.0

