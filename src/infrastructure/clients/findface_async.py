"""
Wrapper assíncrono para FindfaceMulti usando httpx.

Implementa pool de conexões e requisições assíncronas
para melhorar performance de envios ao FindFace.

PROBLEMA RESOLVIDO:
requests.post() é bloqueante. Se houver latência de rede,
a thread SendFace fica travada esperando resposta.

SOLUÇÃO:
Usar httpx com conexões persistentes e possibilidade
de usar async/await em versões futuras.
Por enquanto, mantém pool de conexões para reusar conexões TCP.
"""

import logging
from typing import Optional, Any, Dict
try:
    import httpx
except ImportError:
    httpx = None


class FindfaceMultiAsync:
    """
    Wrapper assíncrono (ou com pool) para FindfaceMulti.
    
    Usa httpx em vez de requests para:
    - Reusar conexões (pool de conexões)
    - Melhor performance em múltiplas requisições
    - Suporte para async em versões futuras
    
    BENEFÍCIO:
    Reutiliza conexões TCP/TLS em vez de criar nova a cada request.
    Em 60 requests/segundo, isso é MUITO mais eficiente.
    
    Melhoria esperada: +10-20% throughput
    """
    
    def __init__(
        self,
        findface_multi_client,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        timeout: float = 30.0
    ):
        """
        Inicializa wrapper assíncrono.
        
        :param findface_multi_client: Cliente FindfaceMulti padrão (fallback).
        :param pool_connections: Número de pools de conexão.
        :param pool_maxsize: Máximo de conexões por pool.
        :param timeout: Timeout para requisições em segundos.
        """
        self.client = findface_multi_client
        self.logger = logging.getLogger(__name__)
        self.pool_maxsize = pool_maxsize
        self.timeout = timeout
        
        self._http_client: Optional[httpx.Client] = None
        
        # Tenta usar httpx, fallback para requests
        if httpx is not None:
            try:
                self._setup_httpx_client()
                self.logger.info(
                    f"✓ Pool de conexões httpx configurado "
                    f"(max_connections={pool_maxsize}, timeout={timeout}s)"
                )
            except Exception as e:
                self.logger.warning(f"Erro ao configurar httpx: {e}. Usando requests padrão.")
                self._http_client = None
        else:
            self.logger.warning("httpx não disponível. Usando requests padrão.")
    
    def _setup_httpx_client(self) -> None:
        """
        Configura client httpx com pool de conexões.
        
        Pooling permite reusar conexões TCP/TLS.
        """
        if httpx is None:
            return
        
        limits = httpx.Limits(
            max_connections=self.pool_maxsize,
            max_keepalive_connections=self.pool_maxsize
        )
        
        self._http_client = httpx.Client(
            limits=limits,
            timeout=self.timeout,
            verify=False  # Desabilita verificação SSL (igual ao original)
        )
    
    def add_face_event(
        self,
        token: str,
        fullframe: bytes,
        camera: str,
        timestamp: str,
        roi: Dict[str, float],
        mf_selector: str = "biggest",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Envia evento de face ao FindFace com pool de conexões.
        
        :param token: Token de autenticação da câmera.
        :param fullframe: Imagem JPEG completa (bytes).
        :param camera: ID da câmera.
        :param timestamp: Timestamp do evento (ISO 8601).
        :param roi: Bounding box {"left": x1, "top": y1, "right": x2, "bottom": y2}.
        :param mf_selector: Seletor ("biggest", "best", etc).
        :param kwargs: Argumentos adicionais.
        :return: Resposta da API.
        """
        # Se httpx disponível e configurado, usa pool
        if self._http_client is not None:
            return self._add_face_event_httpx(
                token, fullframe, camera, timestamp, roi, mf_selector, **kwargs
            )
        
        # Fallback para cliente padrão
        return self.client.add_face_event(
            token=token,
            fullframe=fullframe,
            camera=camera,
            timestamp=timestamp,
            roi=roi,
            mf_selector=mf_selector,
            **kwargs
        )
    
    def _add_face_event_httpx(
        self,
        token: str,
        fullframe: bytes,
        camera: str,
        timestamp: str,
        roi: Dict[str, float],
        mf_selector: str = "biggest",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Implementação usando httpx com pool de conexões.
        
        Reutiliza conexões TCP/TLS para melhor performance.
        """
        try:
            url = f"{self.client.url_base}/events/create_from_image/"
            
            headers = {
                "Authorization": f"Token {self.client.token}"
            }
            
            # Monta multipart form data
            files = {
                "fullframe": ("image.jpg", fullframe, "image/jpeg")
            }
            
            data = {
                "camera": camera,
                "timestamp": timestamp,
                "mf_selector": mf_selector,
                "roi": str(roi)  # Converte dict para string
            }
            
            # Usa client com pool de conexões
            response = self._http_client.post(
                url,
                headers=headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ConnectionError(
                    f"Erro ao enviar evento ao FindFace: "
                    f"HTTP {response.status_code} - {response.text}"
                )
        
        except Exception as e:
            self.logger.error(f"Erro em add_face_event_httpx: {e}")
            
            # Fallback para cliente padrão
            return self.client.add_face_event(
                token=token,
                fullframe=fullframe,
                camera=camera,
                timestamp=timestamp,
                roi=roi,
                mf_selector=mf_selector,
                **kwargs
            )
    
    def close(self) -> None:
        """Fecha o pool de conexões."""
        if self._http_client is not None:
            try:
                self._http_client.close()
                self.logger.info("Pool de conexões httpx fechado")
            except Exception as e:
                self.logger.warning(f"Erro ao fechar pool: {e}")
    
    def __getattr__(self, name: str) -> Any:
        """
        Delega métodos não implementados para cliente original.
        
        Permite usar FindfaceMultiAsync como drop-in replacement.
        """
        return getattr(self.client, name)
    
    def __del__(self) -> None:
        """Garante fechamento de pool ao destruir objeto."""
        self.close()
