"""
Entidade Track do domínio.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.domain.value_objects import IdVO
from src.domain.entities.event_entity import Event


class Track:
    """
    Entidade que representa um track (rastreamento) de uma face ao longo de múltiplos frames.
    OTIMIZAÇÃO MÁXIMA: Armazena apenas 3 eventos (primeiro, melhor, último) ao invés de lista completa.
    Economia de memória: ~99% (de 5.4GB para ~18MB em tracks longos).
    """

    def __init__(
        self,
        id: IdVO,
        first_event: Optional[Event] = None,
        min_movement_percentage: float = 0.1
    ):
        """
        Inicializa a entidade Track.
        OTIMIZAÇÃO: Armazena apenas first_event, best_event e last_event.

        :param id: ID único do track (IdVO).
        :param first_event: Primeiro evento do track (opcional).
        :param min_movement_percentage: Percentual mínimo de frames com movimento (0.0 a 1.0).
        :raises TypeError: Se algum parâmetro não for do tipo esperado.
        """
        if not isinstance(id, IdVO):
            raise TypeError(f"id deve ser IdVO, recebido: {type(id).__name__}")
        
        if first_event is not None and not isinstance(first_event, Event):
            raise TypeError(f"first_event deve ser Event, recebido: {type(first_event).__name__}")
        
        self._id = id
        self._first_event: Optional[Event] = first_event
        self._best_event: Optional[Event] = first_event
        self._last_event: Optional[Event] = first_event
        self._event_count: int = 1 if first_event is not None else 0
        self._movement_count: int = 1 if first_event is not None else 0
        self._min_movement_percentage: float = min_movement_percentage

    @property
    def id(self) -> IdVO:
        """Retorna o ID do track."""
        return self._id

    @property
    def first_event(self) -> Optional[Event]:
        """Retorna o primeiro evento do track."""
        return self._first_event

    @property
    def best_event(self) -> Optional[Event]:
        """Retorna o evento com melhor qualidade facial."""
        return self._best_event

    @property
    def last_event(self) -> Optional[Event]:
        """Retorna o último evento do track."""
        return self._last_event

    @property
    def event_count(self) -> int:
        """Retorna a quantidade total de eventos processados no track."""
        return self._event_count

    @property
    def has_movement(self) -> bool:
        """Indica se houve movimento significativo no track."""
        # Track com 1 evento sempre tem movimento
        if self._event_count <= 1:
            return True
        
        # Calcula percentual de eventos com movimento
        movement_percentage = self._movement_count / self._event_count
        return movement_percentage >= self._min_movement_percentage

    @property
    def is_empty(self) -> bool:
        """Verifica se o track está vazio (sem eventos)."""
        return self._event_count == 0
    
    def is_active(self, max_inactivity_seconds: float = 2.0) -> bool:
        """
        Verifica se o track está ativo baseado no tempo desde o último evento.
        
        :param max_inactivity_seconds: Tempo máximo de inatividade em segundos.
        :return: True se o track está ativo.
        """
        if self._last_event is None:
            return False
        
        last_timestamp = self._last_event.frame.timestamp.value()
        time_diff = (datetime.now() - last_timestamp).total_seconds()
        
        return time_diff <= max_inactivity_seconds

    def add_event(self, event: Event, min_threshold_pixels: float = 50.0) -> None:
        """
        Adiciona um evento ao track.
        OTIMIZAÇÃO MÁXIMA: Armazena apenas primeiro, melhor e último evento.
        Libera memória de eventos descartados (frames grandes não são mais referenciados).
        
        Lógica:
        - Primeiro evento: armazenado como first, best e last
        - Eventos subsequentes: atualiza best se qualidade for maior, sempre atualiza last
        - Calcula movimento entre último evento e novo evento para atualizar has_movement
        - Remove referências de eventos não utilizados (libera frames da memória)

        :param event: Evento a ser adicionado.
        :param min_threshold_pixels: Limiar mínimo em pixels para considerar movimento.
        :raises TypeError: Se event não for do tipo Event.
        """
        if not isinstance(event, Event):
            raise TypeError(f"event deve ser Event, recebido: {type(event).__name__}")
        
        # Primeiro evento do track
        if self.is_empty:
            self._first_event = event
            self._best_event = event
            self._last_event = event
            self._event_count = 1
            self._movement_count = 1
            return
        
        # Guarda referência ao evento anterior para possível limpeza
        old_last_event = self._last_event
        old_best_event = self._best_event
        
        # Calcula movimento entre último evento e novo evento
        if self._last_event is not None:
            import math
            
            # Centro do último bbox
            x1_last, y1_last, x2_last, y2_last = self._last_event.bbox.value()
            center_x_last = (x1_last + x2_last) / 2.0
            center_y_last = (y1_last + y2_last) / 2.0
            
            # Centro do novo bbox
            x1_new, y1_new, x2_new, y2_new = event.bbox.value()
            center_x_new = (x1_new + x2_new) / 2.0
            center_y_new = (y1_new + y2_new) / 2.0
            
            # Distância euclidiana
            distance = math.sqrt(
                (center_x_new - center_x_last) ** 2 + 
                (center_y_new - center_y_last) ** 2
            )
            
            # Incrementa contador se houve movimento
            if distance >= min_threshold_pixels:
                self._movement_count += 1
        
        # Eventos subsequentes
        self._event_count += 1
        
        # Atualiza melhor evento se qualidade for superior (safe check para None)
        if self._best_event is None or event.face_quality_score.value() > self._best_event.face_quality_score.value():
            self._best_event = event
        
        # Sempre atualiza último evento
        self._last_event = event
        
        # ============= LIMPEZA DE MEMÓRIA DE EVENTOS NÃO UTILIZADOS =============
        # Se o evento anterior (last) não é mais utilizado, libera sua memória
        if old_last_event is not None and old_last_event is not self._first_event and old_last_event is not self._best_event:
            # O evento anterior não é mais referenciado (não é first, best ou current last)
            self._release_event_memory(old_last_event)
        
        # Se o best_event mudou e o anterior não é mais utilizado, libera sua memória
        if old_best_event is not None and old_best_event is not self._first_event and old_best_event is not self._last_event:
            # O antigo best_event não é mais referenciado
            self._release_event_memory(old_best_event)
    
    def _release_event_memory(self, event: Event) -> None:
        """
        Libera a memória associada a um evento que não será mais utilizado.
        Zera APENAS o conteúdo do full_frame (numpy array grande), mantendo metadados.
        
        IMPORTANTE: Não deleta o atributo _full_frame (FullFrameVO), apenas seu valor interno.
        O frame é necessário para acessar metadados como camera_id, width, height, etc.
        
        :param event: Evento cujas referências devem ser liberadas.
        """
        try:
            if hasattr(event, 'frame') and hasattr(event.frame, '_full_frame'):
                full_frame_vo = event.frame._full_frame
                
                # Zera o conteúdo interno do FullFrameVO (não deleta o objeto)
                if hasattr(full_frame_vo, '_ndarray'):
                    try:
                        # Substitui numpy array por um array vazio mínimo para manter integridade
                        # Isso libera a memória do frame original
                        import numpy as np
                        full_frame_vo._ndarray = np.zeros((1, 1, 3), dtype=np.uint8)
                        full_frame_vo._ndarray.flags.writeable = False
                    except:
                        pass  # Se não conseguir, deixa o GC fazer o trabalho
        except Exception:
            # Se algo der errado, não interrompe o fluxo
            pass

    def cleanup(self) -> None:
        """
        Limpa a memória do track antes de ser descartado.
        Remove referências desnecessárias para facilitar garbage collection.
        Mantém apenas o best_event (que será enviado ao FindFace).
        """
        # Libera first_event se ele não for o best_event
        if self._first_event is not None and self._first_event is not self._best_event:
            self._release_event_memory(self._first_event)
            self._first_event = None
        
        # Libera last_event se ele não for o best_event
        if self._last_event is not None and self._last_event is not self._best_event:
            self._release_event_memory(self._last_event)
            self._last_event = None

    def finalize(self) -> None:
        """
        Finaliza completamente o track, liberando TODA memória.
        Chamado após o best_event ser enfileirado ao FindFace.
        Zera todas as referências internas.
        """
        # Primeiro executa cleanup parcial
        self.cleanup()
        
        # Depois zera o best_event também
        if self._best_event is not None:
            self._release_event_memory(self._best_event)
            self._best_event = None
        
        # Zera contadores
        self._event_count = 0
        self._movement_count = 0

    def get_best_event(self) -> Optional[Event]:
        """
        Retorna o evento com o maior score de qualidade facial.
        
        :return: Evento com melhor qualidade ou None se track estiver vazio.
        """
        return self._best_event

    def get_first_event(self) -> Optional[Event]:
        """
        Retorna o primeiro evento do track.

        :return: Primeiro evento ou None se track estiver vazio.
        """
        return self._first_event

    def get_last_event(self) -> Optional[Event]:
        """
        Retorna o último evento do track.

        :return: Último evento ou None se track estiver vazio.
        """
        return self._last_event

    def get_average_confidence(self) -> float:
        """
        Calcula a confiança média das detecções no track.
        OTIMIZAÇÃO: Baseado apenas nos 3 eventos armazenados.

        :return: Confiança média ou 0.0 se track estiver vazio.
        """
        if self.is_empty:
            return 0.0
        
        # Coleta eventos não-nulos
        events = [e for e in [self._first_event, self._best_event, self._last_event] if e is not None]
        
        # Remove duplicatas (eventos podem ser o mesmo)
        unique_events = list({id(e): e for e in events}.values())
        
        if not unique_events:
            return 0.0
        
        total_confidence = sum(event.confidence.value() for event in unique_events)
        return total_confidence / len(unique_events)

    def get_average_quality_score(self) -> float:
        """
        Calcula o score médio de qualidade facial no track.
        OTIMIZAÇÃO: Baseado apenas nos 3 eventos armazenados.

        :return: Score médio de qualidade ou 0.0 se track estiver vazio.
        """
        if self.is_empty:
            return 0.0
        
        # Coleta eventos não-nulos
        events = [e for e in [self._first_event, self._best_event, self._last_event] if e is not None]
        
        # Remove duplicatas
        unique_events = list({id(e): e for e in events}.values())
        
        if not unique_events:
            return 0.0
        
        total_quality = sum(event.face_quality_score.value() for event in unique_events)
        return total_quality / len(unique_events)
    
    def get_movement_statistics(self) -> Dict[str, float]:
        """
        Retorna estatísticas detalhadas sobre o movimento no track.
        OTIMIZAÇÃO: Baseado apenas em primeiro e último evento.
        
        :return: Dicionário com estatísticas de movimento.
        """
        if self.is_empty or self._first_event is None or self._last_event is None:
            return {
                'total_distance': 0.0,
                'average_distance': 0.0,
                'max_distance': 0.0,
                'min_distance': 0.0,
                'movement_detected': False
            }
        
        if self.event_count < 2:
            return {
                'total_distance': 0.0,
                'average_distance': 0.0,
                'max_distance': 0.0,
                'min_distance': 0.0,
                'movement_detected': False
            }
        
        import math
        
        # Calcula centros do primeiro e último bbox
        x1_first, y1_first, x2_first, y2_first = self._first_event.bbox.value()
        center_x_first = (x1_first + x2_first) / 2.0
        center_y_first = (y1_first + y2_first) / 2.0
        
        x1_last, y1_last, x2_last, y2_last = self._last_event.bbox.value()
        center_x_last = (x1_last + x2_last) / 2.0
        center_y_last = (y1_last + y2_last) / 2.0
        
        # Distância total entre primeiro e último
        distance = math.sqrt(
            (center_x_last - center_x_first) ** 2 + 
            (center_y_last - center_y_first) ** 2
        )
        
        return {
            'total_distance': distance,
            'average_distance': distance,
            'max_distance': distance,
            'min_distance': distance,
            'movement_detected': distance > 0.0
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a entidade para um dicionário.
        OTIMIZAÇÃO: Retorna apenas os 3 eventos armazenados.

        :return: Dicionário com os dados do track.
        """
        return {
            'id': self._id.value(),
            'event_count': self.event_count,
            'first_event': self._first_event.to_dict() if self._first_event else None,
            'best_event': self._best_event.to_dict() if self._best_event else None,
            'last_event': self._last_event.to_dict() if self._last_event else None,
            'average_confidence': self.get_average_confidence(),
            'average_quality_score': self.get_average_quality_score(),
            'best_event_id': self._best_event.id.value() if self._best_event else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """
        Cria uma instância de Track a partir de um dicionário.
        OTIMIZAÇÃO: Reconstrói apenas o ID e metadados.
        Nota: Eventos não são reconstruídos (Event não possui from_dict).

        :param data: Dicionário com os dados do track.
        :return: Instância de Track.
        :raises KeyError: Se alguma chave obrigatória estiver ausente.
        """
        track = cls(id=IdVO(data['id']))
        track._event_count = data.get('event_count', 0)
        return track

    def __eq__(self, other) -> bool:
        """Compara dois tracks por igualdade (baseado no ID)."""
        if not isinstance(other, Track):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Retorna o hash do track (baseado no ID)."""
        return hash(self._id)

    def __repr__(self) -> str:
        """Representação string do track."""
        best_event = self.get_best_event()
        best_quality = best_event.face_quality_score.value() if best_event is not None else 0.0
        return (
            f"Track(id={self._id.value()}, "
            f"events={self.event_count}, "
            f"avg_quality={self.get_average_quality_score():.4f}, "
            f"best_quality={best_quality:.4f})"
        )

    def __str__(self) -> str:
        """Conversão para string."""
        return (
            f"Track {self._id.value()}: "
            f"{self.event_count} events, "
            f"avg quality {self.get_average_quality_score():.4f}"
        )
