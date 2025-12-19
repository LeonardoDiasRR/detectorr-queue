"""
Use Case para gerenciar tracks e selecionar melhor evento.
"""

import logging
import gc
import time
from typing import Dict, List, Optional
from threading import Event as ThreadEvent, Lock

from src.domain.entities import Track, Event
from src.domain.value_objects import IdVO
from src.domain.services.track_matching_service import TrackMatchingService
from src.application.queues import EventQueue, FindfaceQueue
from src.infrastructure.config.settings import TrackingConfig, TrackConfig


class ManageTracksUseCase:
    """Use Case responsável por gerenciar tracks e selecionar melhores eventos."""
    
    def __init__(
        self,
        event_queue: EventQueue,
        findface_queue: FindfaceQueue,
        tracking_config: TrackingConfig,
        track_config: TrackConfig,
        stop_event: ThreadEvent,
        queue_timeout: float = 0.5
    ):
        """
        Inicializa o use case.
        
        :param event_queue: Fila de eventos de entrada.
        :param findface_queue: Fila de eventos para envio ao FindFace.
        :param tracking_config: Configurações de tracking.
        :param track_config: Configurações de track.
        :param stop_event: Evento para parar a execução.
        """
        self.event_queue = event_queue
        self.findface_queue = findface_queue
        self.tracking_config = tracking_config
        self.track_config = track_config
        self.stop_event = stop_event
        self.queue_timeout = queue_timeout
        
        self.logger = logging.getLogger(__name__)
        # Tracks organizados por câmera: {camera_id: [Track, Track, ...]}
        self._tracks_por_camera: Dict[int, List[Track]] = {}
        self._lock = Lock()
        self._track_id_counter = 0
    
    def execute(self):
        """Executa o gerenciamento de tracks."""
        self.logger.info("Iniciando gerenciador de tracks")
        
        try:
            self._management_loop()
        except Exception as e:
            self.logger.error(f"Erro no gerenciador de tracks: {e}", exc_info=True)
        finally:
            self._finalize_all_tracks()
            self.logger.info("Gerenciador de tracks finalizado")
    
    def _management_loop(self):
        """Loop principal de gerenciamento."""
        last_cleanup_time = time.time()
        cleanup_interval = 5.0  # Limpeza a cada 5 segundos
        
        while not self.stop_event.is_set():
            try:
                event = self.event_queue.get(block=True, timeout=self.queue_timeout)
                
                if event is None:
                    # Limpeza periódica mesmo sem eventos
                    try:
                        current_time = time.time()
                        if current_time - last_cleanup_time >= cleanup_interval:
                            try:
                                self._cleanup_inactive_tracks()
                            except Exception as e:
                                self.logger.error(f"Erro na limpeza de tracks inativos: {e}", exc_info=True)
                            last_cleanup_time = current_time
                    except Exception as e:
                        self.logger.error(f"Erro ao verificar limpeza periódica: {e}")
                    continue
                
                self.logger.debug(
                    f"Consumido evento {event.id.value()} da fila "
                    f"(câmera: {event.camera_id.value()}, tamanho fila: {self.event_queue.qsize()})"
                )
                
                try:
                    self._process_event(event)
                except Exception as e:
                    self.logger.error(f"Erro ao processar evento {event.id.value()}: {e}", exc_info=True)
                finally:
                    try:
                        self.event_queue.task_done()
                    except Exception as e:
                        self.logger.warning(f"Erro ao marcar task_done: {e}")
            except Exception as e:
                self.logger.error(f"Erro no loop de gerenciamento de tracks: {e}", exc_info=True)
    
    def _process_event(self, event: Event):
        """
        Processa um evento e associa a um track existente ou cria novo.
        Lógica baseada no sistema legado:
        1. Busca por IoU (maior IoU acima do limiar)
        2. Se não encontrar, busca por distância de centros (menor distância)
        3. Se não encontrar, cria novo track
        
        :param event: Evento a processar.
        """
        try:
            camera_id = event.camera_id.value()
            frame_width = event.frame.width
            frame_height = event.frame.height
            
            # Calcula limiares adaptativos
            try:
                limiar_iou = TrackMatchingService.calcular_limiar_iou(frame_width, frame_height)
                limiar_distancia = TrackMatchingService.calcular_limiar_distancia(frame_width, frame_height)
            except Exception as e:
                self.logger.error(f"Erro ao calcular limiares: {e}", exc_info=True)
                return
            
            with self._lock:
                try:
                    # Obtém tracks da câmera (filtra apenas ativos)
                    # Aumento o timeout para 15 segundos para melhor acúmulo de eventos
                    tracks = self._tracks_por_camera.get(camera_id, [])
                    tracks_ativos = [t for t in tracks if t.is_active(max_inactivity_seconds=15.0)]
                    
                    # Atualiza lista de tracks ativos
                    self._tracks_por_camera[camera_id] = tracks_ativos
                    
                    track_matched = None
                    melhor_iou = 0.0
                    melhor_distancia = float('inf')
                    track_por_distancia = None
                    
                    # 1ª estratégia: busca por IoU
                    for track in tracks_ativos:
                        try:
                            if track.last_event is None:
                                continue
                            
                            iou, distancia = TrackMatchingService.match_evento_com_track(
                                event.bbox,
                                track.last_event.bbox,
                                frame_width,
                                frame_height
                            )
                            
                            # Prioriza IoU
                            if iou >= limiar_iou and iou > melhor_iou:
                                track_matched = track
                                melhor_iou = iou
                            # Guarda melhor distância como fallback
                            elif distancia <= limiar_distancia and distancia < melhor_distancia:
                                track_por_distancia = track
                                melhor_distancia = distancia
                        except Exception as e:
                            self.logger.warning(f"Erro ao comparar evento com track: {e}")
                            continue
                    
                    # 2ª estratégia: se não encontrou por IoU, usa distância
                    if track_matched is None and track_por_distancia is not None:
                        track_matched = track_por_distancia
                        self.logger.debug(
                            f"Evento {event.id.value()} associado ao track {track_matched.id.value()} "
                            f"por distância ({melhor_distancia:.2f}px)"
                        )
                    elif track_matched is not None:
                        self.logger.debug(
                            f"Evento {event.id.value()} associado ao track {track_matched.id.value()} "
                            f"por IoU ({melhor_iou:.3f})"
                        )
                    
                    # Se encontrou match, adiciona evento ao track
                    if track_matched is not None:
                        try:
                            track_matched.add_event(event, min_threshold_pixels=self.track_config.min_movement_pixels)
                            
                            # Verifica se deve finalizar
                            if self._should_finalize_track(track_matched):
                                self._finalize_track_internal(track_matched, camera_id)
                        except Exception as e:
                            self.logger.error(f"Erro ao adicionar evento ao track: {e}", exc_info=True)
                    else:
                        # Cria novo track
                        try:
                            self._track_id_counter += 1
                            novo_track = Track(
                                id=IdVO(self._track_id_counter),
                                first_event=event,
                                min_movement_percentage=self.track_config.min_movement_percentage
                            )
                            
                            self._tracks_por_camera.setdefault(camera_id, []).append(novo_track)
                            self.logger.debug(f"Novo track {self._track_id_counter} criado para câmera {camera_id}")
                        except Exception as e:
                            self.logger.error(f"Erro ao criar novo track: {e}", exc_info=True)
                except Exception as e:
                    self.logger.error(f"Erro dentro de lock ao processar evento: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Erro ao processar evento: {e}", exc_info=True)
    
    def _should_finalize_track(self, track: Track) -> bool:
        """
        Verifica se um track deve ser finalizado.
        
        :param track: Track a verificar.
        :return: True se deve finalizar.
        """
        # Finaliza se atingiu número máximo de eventos (não frames)
        if track.event_count >= self.tracking_config.max_frames:
            self.logger.debug(
                f"Track {track.id.value()} atingiu max_frames "
                f"({track.event_count} >= {self.tracking_config.max_frames})"
            )
            return True
        
        return False
    
    def _finalize_track_internal(self, track: Track, camera_id: int):
        """
        Finaliza um track internamente (já dentro do lock).
        Remove completamente da memória após finalização.
        
        Ciclo de vida:
        1. Verifica se track tem movimento
        2. Obtém melhor evento
        3. Enfileira melhor evento ao FindFace (SendFindface consumer irá processar)
        4. Chama track.finalize() para liberar TODA memória (best_event já foi copiado para fila)
        
        :param track: Track a finalizar.
        :param camera_id: ID da câmera.
        """
        # Remove da lista de tracks (não será mais acessado)
        tracks = self._tracks_por_camera.get(camera_id, [])
        if track in tracks:
            tracks.remove(track)
        
        # Verifica se track tem movimento suficiente
        if not track.has_movement:
            self.logger.debug(
                f"Track {track.id.value()} descartado: movimento insuficiente "
                f"({track._movement_count}/{track.event_count} eventos com movimento)"
            )
            # Libera TODA memória antes de descartar
            track.finalize()
            del track  # GC irá descartar
            return
        
        # Obtém melhor evento (ainda não foi zerado)
        best_event = track.best_event
        
        if best_event is None:
            self.logger.warning(f"Track {track.id.value()} finalizado sem melhor evento")
            track.finalize()  # Libera memória
            del track  # GC
            return
        
        # Valida se best_event tem frame intacto ANTES de copiar
        if best_event.frame is None:
            self.logger.error(
                f"Track {track.id.value()} possui best_event com frame None. "
                f"Descartando sem envio ao FindFace. "
                f"Isto indica um problema de sincronização ou cleanup prematuro."
            )
            track.finalize()
            del track
            return
        
        # Enfileira melhor evento ao FindFace
        # ISOLAMENTO: O evento no track é uma cópia isolada
        # Fazemos outra cópia para enviar (isolando completamente do track)
        try:
            best_event_copy = best_event.copy()
        except (ValueError, AttributeError) as e:
            self.logger.error(
                f"Erro ao copiar best_event do track {track.id.value()}: {e}. "
                f"Track será descartado sem envio ao FindFace."
            )
            track.finalize()
            del track
            return
        
        if not self.findface_queue.put(best_event_copy, block=False):
            self.logger.warning(
                f"Fila do FindFace cheia, evento do track {track.id.value()} descartado "
                f"(tamanho fila: {self.findface_queue.qsize()})"
            )
        else:
            try:
                self.logger.info(
                    f"✓ Track {track.id.value()} finalizado e enviado à fila do FindFace | "
                    f"eventos: {track.event_count} | "
                    f"movimento: {track._movement_count} | "
                    f"qualidade: {best_event.face_quality_score.value():.4f}"
                )
            except Exception as e:
                self.logger.warning(f"Erro ao logar informações do track: {e}")
        
        # Libera TODA memória do track (inclusive best_event)
        # O evento já foi enfileirado ao FindFace, SendFindface consumer irá processar
        # Quando SendFindface terminar, o evento não será mais referenciado
        track.finalize()
        del track  # GC irá descartar imediatamente
    
    def _cleanup_inactive_tracks(self):
        """Finaliza e remove tracks inativos de todas as câmeras."""
        try:
            with self._lock:
                total_finalized = 0
                max_inactivity = 15.0  # 15 segundos antes de finalizar
                
                for camera_id in list(self._tracks_por_camera.keys()):
                    try:
                        tracks = self._tracks_por_camera[camera_id]
                        tracks_ativos = [t for t in tracks if t.is_active(max_inactivity_seconds=max_inactivity)]
                        
                        # Tracks inativos devem ser finalizados ANTES de serem removidos
                        tracks_inativos = [t for t in tracks if t not in tracks_ativos]
                        
                        for inactive_track in tracks_inativos:
                            try:
                                self.logger.debug(
                                    f"Track {inactive_track.id.value()} inativado (sem evento há >{max_inactivity}s), finalizando..."
                                )
                                self._finalize_track_internal(inactive_track, camera_id)
                                total_finalized += 1
                            except Exception as e:
                                self.logger.error(f"Erro ao finalizar track inativo: {e}", exc_info=True)
                        
                        if tracks_ativos:
                            self._tracks_por_camera[camera_id] = tracks_ativos
                        else:
                            # Remove camera_id se não há tracks ativos
                            del self._tracks_por_camera[camera_id]
                            self.logger.debug(f"Câmera {camera_id} removida (sem tracks ativos)")
                    except Exception as e:
                        self.logger.error(f"Erro ao limpar tracks da câmera {camera_id}: {e}", exc_info=True)
                
                # Força garbage collection se houve remoções significativas
                if total_finalized > 0:
                    try:
                        self.logger.debug(f"Limpeza: {total_finalized} tracks finalizados")
                        gc.collect()
                    except Exception as e:
                        self.logger.warning(f"Erro ao executar garbage collection: {e}")
        except Exception as e:
            self.logger.error(f"Erro ao limpar tracks inativos: {e}", exc_info=True)
    
    def _finalize_all_tracks(self):
        """Finaliza todos os tracks pendentes."""
        self.logger.info("Finalizando todos os tracks pendentes...")
        
        try:
            with self._lock:
                total_finalizados = 0
                for camera_id, tracks in list(self._tracks_por_camera.items()):
                    for track in list(tracks):  # Copia lista para iterar
                        try:
                            self._finalize_track_internal(track, camera_id)
                            total_finalizados += 1
                        except Exception as e:
                            self.logger.error(f"Erro ao finalizar track {track.id.value()}: {e}", exc_info=True)
                
                # Limpa todos os tracks
                self._tracks_por_camera.clear()
            
            self.logger.info(f"{total_finalizados} tracks finalizados")
        except Exception as e:
            self.logger.error(f"Erro ao finalizar todos os tracks: {e}", exc_info=True)
