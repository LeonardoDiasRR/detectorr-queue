import requests
from typing import Optional, List, Dict, Any, Union
try:
    import urllib3
except ModuleNotFoundError:  # pragma: no cover - library may be absent in tests
    urllib3 = None
import mimetypes
import io
from pathlib import Path
import json


if urllib3 is not None:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FindfaceMulti:
    """
    Classe responsável por autenticar e interagir com a API do FindFace Multi.
    """

    def __init__(self, url_base: str, user: str, password: str, uuid: str) -> None:
        """
        Inicializa a instância da classe e realiza o login automaticamente.

        :param url_base: URL base da API (ex: https://10.95.7.19)
        :param user: Nome de usuário da API
        :param password: Senha do usuário
        :param uuid: Identificador único do dispositivo
        """
        # Verificações de tipo
        if not isinstance(url_base, str):
            raise TypeError("url_base deve ser uma string.")
        if not isinstance(user, str):
            raise TypeError("user deve ser uma string.")
        if not isinstance(password, str):
            raise TypeError("password deve ser uma string.")
        if not isinstance(uuid, str):
            raise TypeError("uuid deve ser uma string.")

        # Atributos da instância
        self.url_base: str = url_base.rstrip("/")
        self.user: str = user
        self.password: str = password
        self.uuid: str = uuid
        self.token: Optional[str] = None

        # Realiza login automaticamente
        self.login()

    def login(self) -> None:
        """
        Realiza o login na API do FindFace e armazena o token de autenticação.

        A verificação SSL está desativada por padrão (``verify=False``).
        Altere o código para ``verify=True`` se possuir um certificado válido.
        """
        url: str = f"{self.url_base}/auth/login/"

        headers: dict = {
            "Content-Type": "application/json"
        }

        # Corpo da requisição com o UUID do dispositivo
        payload: dict = {
            "uuid": self.uuid
        }

        # Requisição com autenticação básica (usuário + senha)
        try:
            response = requests.post(
                url,
                auth=(self.user, self.password),
                json=payload,
                headers=headers,
                # A verificação SSL está desativada por padrão. Mude para True se houver certificado válido.
                verify=False
            )
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro de conexão: {exc}") from exc

        # Verifica se a resposta foi bem-sucedida
        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                self.token = data["token"]
                print("login realizado")
            else:
                raise ValueError("Resposta não contém o token de autenticação.")
        else:
            raise ConnectionError(f"Falha no login. Código HTTP: {response.status_code} - {response.text}")

    def logout(self) -> None:
        """
        Realiza o logout da API, invalidando o token atual.
        """
        # Verifica se há um token válido
        if not isinstance(self.token, str) or not self.token:
            print("Aviso: Nenhum token armazenado. Logout não será executado.")
            return

        url: str = f"{self.url_base}/auth/logout/"
        headers: dict = {
            "Authorization": f"Token {self.token}"
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                verify=False
            )
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro de conexão: {exc}") from exc

        if response.status_code == 204:
            self.token = None  # Limpa o token da instância
            print("Logout realizado.")
        else:
            raise ConnectionError(f"Falha ao realizar logout. Código HTTP: {response.status_code} - {response.text}")


    def _request(self, method: str, path: str, expected: int = 200, **kwargs) -> Any:
        """Helper for authenticated HTTP requests."""

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url = f"{self.url_base}/{path.lstrip('/')}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Token {self.token}"

        try:
            resp = requests.request(method, url, headers=headers, verify=False, **kwargs)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro de conexão: {exc}") from exc

        if resp.status_code == expected:
            if expected == 204:
                return None
            return resp.json()
        elif resp.status_code == 404:
            raise ValueError("Recurso não encontrado")
        else:
            raise ConnectionError(f"Erro {resp.status_code} - {resp.text}")


    def get_human_cards(
        self,
        active: Optional[bool] = None,
        filled: Optional[bool] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        modified_date_gt: Optional[str] = None,
        modified_date_gte: Optional[str] = None,
        modified_date_last_n_days: Optional[int] = None,
        modified_date_lt: Optional[str] = None,
        modified_date_lte: Optional[str] = None,
        modified_date_nth_full_week: Optional[int] = None,
        modified_date_nth_work_week: Optional[int] = None,
        has_face_objects: Optional[bool] = None,
        has_body_objects: Optional[bool] = None,
        id_in: Optional[List[int]] = None,
        looks_like: Optional[str] = None,
        name_contains: Optional[str] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
        limit: Optional[int] = None,
        relation: Optional[List[int]] = None,
        watch_lists: Optional[List[int]] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Recupera a lista de human cards com base nos filtros definidos na API FindFace Multi.

        Todos os parâmetros são opcionais e correspondem aos filtros disponíveis na API.

        :return: Dicionário com os resultados da API
        """

        # Verificação de tipo para cada parâmetro
        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue

            if nome in {"active", "filled", "has_face_objects", "has_body_objects"}:
                if not isinstance(valor, bool):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo bool.")
            elif nome in {"created_date_gt", "created_date_gte", "created_date_lt", "created_date_lte",
                        "modified_date_gt", "modified_date_gte", "modified_date_lt", "modified_date_lte",
                        "looks_like", "name_contains", "ordering", "page"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo str.")
            elif nome in {"created_date_last_n_days", "created_date_nth_full_week", "created_date_nth_work_week",
                        "modified_date_last_n_days", "modified_date_nth_full_week", "modified_date_nth_work_week",
                        "limit"}:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo int.")
            elif nome in {"id_in", "relation", "watch_lists"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser uma lista de inteiros.")
            elif nome == "threshold":
                if not isinstance(valor, float):
                    raise TypeError("O parâmetro 'threshold' deve ser do tipo float.")

        # Verifica se o token está disponível
        if not isinstance(self.token, str):
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/humans/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        # Montagem dos parâmetros de query
        params: Dict[str, Any] = {}
        for key, value in locals().items():
            if key not in {"self", "url", "headers"} and value is not None:
                if isinstance(value, list):
                    params[key] = ",".join(map(str, value))
                else:
                    params[key] = value

        response = requests.get(url, headers=headers, params=params, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(f"Erro ao buscar human cards: {response.status_code} - {response.text}")


    def create_human_card(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um novo card humano na API FindFace Multi a partir de um dicionário JSON.

        :param data: Dicionário com os dados do novo card humano, conforme a especificação da API.
        :return: Dicionário com os dados do card criado.
        """

        # --- Verificação de estrutura e tipos ---

        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        # Verificação dos campos obrigatórios
        if "name" not in data:
            raise ValueError("O campo obrigatório 'name' está ausente.")
        if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
            raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "watch_lists" not in data:
            raise ValueError("O campo obrigatório 'watch_lists' está ausente.")
        if not isinstance(data["watch_lists"], list) or not all(isinstance(i, int) for i in data["watch_lists"]):
            raise TypeError("O campo 'watch_lists' deve ser uma lista de inteiros.")

        # Campos opcionais e seus tipos
        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if "meta" in data and not isinstance(data["meta"], dict):
            raise TypeError("O campo 'meta' deve ser um dicionário.")

        if "active_after" in data and not isinstance(data["active_after"], str):
            raise TypeError("O campo 'active_after' deve ser uma string no formato ISO 8601.")

        if "active_before" in data and not isinstance(data["active_before"], str):
            raise TypeError("O campo 'active_before' deve ser uma string no formato ISO 8601.")

        if "disable_schedule" in data:
            if not isinstance(data["disable_schedule"], dict):
                raise TypeError("O campo 'disable_schedule' deve ser um dicionário.")
            dias_validos = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            for dia, blocos in data["disable_schedule"].items():
                if dia not in dias_validos:
                    raise ValueError(f"Dia inválido no 'disable_schedule': {dia}")
                if not isinstance(blocos, list) or not all(
                    isinstance(block, list) and all(isinstance(h, str) for h in block) for block in blocos
                ):
                    raise TypeError(f"O conteúdo de 'disable_schedule[{dia}]' deve ser uma lista de listas de strings.")

        # --- Verificação do token ---
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        # --- Requisição POST ---
        url: str = f"{self.url_base}/cards/humans/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=data, verify=False)

        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ConnectionError(f"Erro ao criar human card: {response.status_code} - {response.text}")


    def update_human_card(self, card_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza parcialmente os dados de um human card existente via PATCH.

        :param card_id: ID do card humano a ser atualizado.
        :param data: Dicionário com os campos a serem atualizados.
        :return: Dicionário com os dados atualizados do card.
        """

        # --- Validação do ID ---
        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        # --- Validação do JSON ---
        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        if "name" in data:
            if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
                raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "watch_lists" in data:
            if not isinstance(data["watch_lists"], list) or not all(isinstance(i, int) for i in data["watch_lists"]):
                raise TypeError("O campo 'watch_lists' deve ser uma lista de inteiros.")

        if "meta" in data and not isinstance(data["meta"], dict):
            raise TypeError("O campo 'meta' deve ser um dicionário.")

        if "active_after" in data and not isinstance(data["active_after"], str):
            raise TypeError("O campo 'active_after' deve ser uma string ISO 8601.")

        if "active_before" in data and not isinstance(data["active_before"], str):
            raise TypeError("O campo 'active_before' deve ser uma string ISO 8601.")

        if "disable_schedule" in data:
            dias_validos = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            disable_schedule = data["disable_schedule"]

            if not isinstance(disable_schedule, dict):
                raise TypeError("O campo 'disable_schedule' deve ser um dicionário.")
            for dia, blocos in disable_schedule.items():
                if dia not in dias_validos:
                    raise ValueError(f"Dia inválido em 'disable_schedule': {dia}")
                if not isinstance(blocos, list) or not all(
                    isinstance(b, list) and all(isinstance(h, str) for h in b) for b in blocos
                ):
                    raise TypeError(f"'disable_schedule[{dia}]' deve ser uma lista de listas de strings.")

        # --- Verifica autenticação ---
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        # --- Executa a requisição PATCH ---
        url: str = f"{self.url_base}/cards/humans/{card_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        response = requests.patch(url, headers=headers, json=data, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(f"Erro ao atualizar o human card {card_id}: {response.status_code} - {response.text}")


    def delete_human_card(self, card_id: int) -> None:
        """
        Remove um human card do sistema FindFace Multi com base no ID informado.

        :param card_id: ID do card humano a ser removido.
        :raises TypeError: Se o ID não for um inteiro.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Se a operação de deleção falhar.
        """

        # Verificação de tipo
        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        # Verificação de autenticação
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/humans/{card_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}"
        }

        response = requests.delete(url, headers=headers, verify=False)

        if response.status_code == 204:
            return  # Sucesso silencioso
        elif response.status_code == 404:
            raise ValueError(f"O card com ID {card_id} não foi encontrado.")
        else:
            raise ConnectionError(f"Erro ao deletar human card {card_id}: {response.status_code} - {response.text}")
        

    def get_human_card_by_id(self, card_id: int) -> Dict[str, Any]:
        """
        Recupera os dados detalhados de um human card específico com base no ID informado.

        :param card_id: ID do human card a ser consultado.
        :return: Dicionário com os dados do card retornado pela API.
        :raises TypeError: Se o ID não for um inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em caso de falha na comunicação com a API.
        """

        # Verificação de tipo
        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        # Verificação de autenticação
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/humans/{card_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise ValueError(f"Card com ID {card_id} não encontrado.")
        else:
            raise ConnectionError(f"Erro ao buscar human card {card_id}: {response.status_code} - {response.text}")


    def detect(
        self,
        photo: Union[str, bytes, io.BytesIO],
        attributes: Dict[str, Dict[str, bool]]
    ) -> Dict[str, Any]:
        """
        Envia uma imagem para detecção de faces, corpos ou veículos no FindFace Multi.

        :param photo: Caminho para o arquivo (str), bytes ou BytesIO contendo a imagem.
        :param attributes: Dicionário de atributos solicitado para análise. 
                        Deve seguir a estrutura esperada de face, car e body.
        :return: Resultado JSON da API com as detecções realizadas.
        """

        # --- Validação do token ---
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        # --- Validação de atributos ---
        if not isinstance(attributes, dict):
            raise TypeError("O parâmetro 'attributes' deve ser um dicionário.")

        estrutura_valida = {
            "face": {"age", "beard", "emotions", "glasses", "gender", "medmask", "headpose"},
            "car": {"description", "license_plate", "special_vehicle_type", "category", "weight_type", "orientation"},
            "body": {"color", "clothes", "bags", "protective_equipment", "age_gender"}
        }

        for categoria, campos in attributes.items():
            if categoria not in estrutura_valida:
                raise ValueError(f"Categoria inválida em 'attributes': {categoria}")
            if not isinstance(campos, dict):
                raise TypeError(f"O valor de 'attributes[{categoria}]' deve ser um dicionário.")
            for chave, valor in campos.items():
                if chave not in estrutura_valida[categoria]:
                    raise ValueError(f"Atributo inválido em '{categoria}': {chave}")
                if not isinstance(valor, bool):
                    raise TypeError(f"O valor de 'attributes[{categoria}][{chave}]' deve ser booleano.")

        # --- Preparação da imagem ---
        if isinstance(photo, str):
            caminho = Path(photo)
            if not caminho.exists() or not caminho.is_file():
                raise FileNotFoundError(f"Arquivo '{photo}' não encontrado.")
            file_data = caminho.read_bytes()
            file_name = caminho.name
        elif isinstance(photo, bytes):
            file_data = photo
            file_name = "upload.jpg"
        elif isinstance(photo, io.BytesIO):
            file_data = photo.getvalue()
            file_name = "upload.jpg"
        else:
            raise TypeError("O parâmetro 'photo' deve ser uma string de caminho, bytes ou io.BytesIO.")

        # --- Montagem da requisição ---
        url: str = f"{self.url_base}/detect"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}"
        }

        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        files = {
            "photo": (file_name, file_data, mime_type),
            "attributes": (None, json.dumps(attributes), "application/json")
        }

        response = requests.post(url, headers=headers, files=files, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(f"Erro na detecção: {response.status_code} - {response.text}")


    def create_face_object(
        self,
        source_photo: Union[str, bytes, io.BytesIO],
        card_id: int,
        create_from: Optional[str] = None,
        mf_selector: str = "all",
        upload_list: Optional[int] = None,
        frame_coords_left: Optional[int] = None,
        frame_coords_top: Optional[int] = None,
        frame_coords_right: Optional[int] = None,
        frame_coords_bottom: Optional[int] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """
        Cria um novo objeto de face vinculado a um card humano a partir de uma imagem.

        :param source_photo: Caminho da imagem, conteúdo em bytes ou io.BytesIO (obrigatório).
        :param card_id: ID do card humano vinculado (obrigatório).
        :param create_from: Origem da criação ('detection:<id>' ou 'faceevent:<id>').
        :param mf_selector: Estratégia de seleção de face ('reject', 'all' ou 'biggest'). Default: 'all'.
        :param upload_list: ID opcional da lista de upload.
        :param frame_coords_left: Coordenada esquerda da face.
        :param frame_coords_top: Coordenada superior da face.
        :param frame_coords_right: Coordenada direita da face.
        :param frame_coords_bottom: Coordenada inferior da face.
        :param active: Define se o objeto estará ativo (padrão True).
        :return: Dicionário com os dados retornados pela API.
        """

        # --- Verificação de autenticação ---
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        # --- Validação dos obrigatórios ---
        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")
        if not isinstance(active, bool):
            raise TypeError("O parâmetro 'active' deve ser booleano.")
        if mf_selector not in {"reject", "all", "biggest"}:
            raise ValueError("O parâmetro 'mf_selector' deve ser 'reject', 'all' ou 'biggest'.")
        if create_from is not None and not isinstance(create_from, str):
            raise TypeError("O parâmetro 'create_from' deve ser uma string.")

        # --- Validação dos opcionais inteiros ---
        for name, value in {
            "upload_list": upload_list,
            "frame_coords_left": frame_coords_left,
            "frame_coords_top": frame_coords_top,
            "frame_coords_right": frame_coords_right,
            "frame_coords_bottom": frame_coords_bottom
        }.items():
            if value is not None and not isinstance(value, int):
                raise TypeError(f"O parâmetro '{name}' deve ser um inteiro.")

        # --- Preparação da imagem ---
        if isinstance(source_photo, str):
            caminho = Path(source_photo)
            if not caminho.exists() or not caminho.is_file():
                raise FileNotFoundError(f"Arquivo '{source_photo}' não encontrado.")
            file_data = caminho.read_bytes()
            file_name = caminho.name
        elif isinstance(source_photo, bytes):
            file_data = source_photo
            file_name = "upload.jpg"
        elif isinstance(source_photo, io.BytesIO):
            file_data = source_photo.getvalue()
            file_name = "upload.jpg"
        else:
            raise TypeError("O parâmetro 'source_photo' deve ser str, bytes ou io.BytesIO.")

        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # --- Montagem da requisição ---
        url: str = f"{self.url_base}/objects/faces/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}"
        }

        files: Dict[str, Any] = {
            "source_photo": (file_name, file_data, mime_type)
        }

        data: Dict[str, Any] = {
            "card": str(card_id),
            "mf_selector": mf_selector,
            "active": json.dumps(active)
        }

        if create_from is not None:
            data["create_from"] = create_from
        if upload_list is not None:
            data["upload_list"] = str(upload_list)
        if frame_coords_left is not None:
            data["frame_coords_left"] = str(frame_coords_left)
        if frame_coords_top is not None:
            data["frame_coords_top"] = str(frame_coords_top)
        if frame_coords_right is not None:
            data["frame_coords_right"] = str(frame_coords_right)
        if frame_coords_bottom is not None:
            data["frame_coords_bottom"] = str(frame_coords_bottom)

        response = requests.post(url, headers=headers, files=files, data=data, verify=False)

        if response.status_code == 201:
            return response.json()
        else:
            raise ConnectionError(f"Erro ao criar objeto de face: {response.status_code} - {response.text}")

    def get_car_cards(
        self,
        active: Optional[bool] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        filled: Optional[bool] = None,
        has_car_objects: Optional[bool] = None,
        id_in: Optional[List[int]] = None,
        license_plate_number_contains: Optional[str] = None,
        limit: Optional[int] = None,
        looks_like: Optional[str] = None,
        modified_date_gt: Optional[str] = None,
        modified_date_gte: Optional[str] = None,
        modified_date_lt: Optional[str] = None,
        modified_date_lte: Optional[str] = None,
        modified_date_last_n_days: Optional[int] = None,
        modified_date_nth_full_week: Optional[int] = None,
        modified_date_nth_work_week: Optional[int] = None,
        name_contains: Optional[str] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
        relation: Optional[List[int]] = None,
        threshold: Optional[float] = None,
        watch_lists: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Retorna a lista de car cards (cartões de veículo) filtrando pelos
        parâmetros fornecidos.

        Todos os argumentos são opcionais e mapeiam diretamente os filtros da
        API ``/cards/cars/``.

        :param active: Filtra por cards ativos (``True``) ou inativos
            (``False``).
        :param created_date_gt: Data de criação maior que este valor
            (ISO 8601).
        :param created_date_gte: Data de criação maior ou igual ao valor
            informado.
        :param created_date_last_n_days: Cards criados nos últimos ``N`` dias.
        :param created_date_lt: Data de criação menor que este valor.
        :param created_date_lte: Data de criação menor ou igual ao valor
            informado.
        :param created_date_nth_full_week: N-ésima semana cheia para o filtro
            ``created_date``.
        :param created_date_nth_work_week: N-ésima semana útil para o filtro
            ``created_date``.
        :param filled: Filtra por cards preenchidos (``True``) ou vazios
            (``False``).
        :param has_car_objects: Filtra por cards que possuem objetos de carro.
        :param id_in: Lista de IDs a serem retornados.
        :param license_plate_number_contains: Busca por placa contendo o texto
            informado.
        :param limit: Quantidade de resultados por página.
        :param looks_like: Identificador de objeto semelhante.
        :param modified_date_gt: Data de modificação maior que.
        :param modified_date_gte: Data de modificação maior ou igual a.
        :param modified_date_lt: Data de modificação menor que.
        :param modified_date_lte: Data de modificação menor ou igual a.
        :param modified_date_last_n_days: Cards modificados nos últimos ``N``
            dias.
        :param modified_date_nth_full_week: N-ésima semana cheia para o filtro
            ``modified_date``.
        :param modified_date_nth_work_week: N-ésima semana útil para o filtro
            ``modified_date``.
        :param name_contains: Filtra por nome contendo o texto informado.
        :param ordering: Campo de ordenação.
        :param page: Cursor de paginação.
        :param relation: Lista de IDs de relações relacionadas.
        :param threshold: Similaridade mínima para ``looks_like``.
        :param watch_lists: IDs das listas de observação a filtrar.
        :return: Dicionário retornado pela API.
        :raises TypeError: Caso algum parâmetro tenha tipo inválido.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Em caso de falha de comunicação com a API.
        """

        # Verifica tipos dos parametros
        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {"active", "filled", "has_car_objects"}:
                if not isinstance(valor, bool):
                    raise TypeError(f"O parâmetro '{nome}' deve ser bool.")
            elif nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
                "modified_date_gt",
                "modified_date_gte",
                "modified_date_lt",
                "modified_date_lte",
                "looks_like",
                "license_plate_number_contains",
                "name_contains",
                "ordering",
                "page",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "modified_date_last_n_days",
                "modified_date_nth_full_week",
                "modified_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")
            elif nome in {"id_in", "relation", "watch_lists"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser lista de inteiros.")
            elif nome == "threshold":
                if not isinstance(valor, float):
                    raise TypeError("O parâmetro 'threshold' deve ser float.")

        if not isinstance(self.token, str):
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/cars/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "url", "headers"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        response = requests.get(url, headers=headers, params=params, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao buscar car cards: {response.status_code} - {response.text}"
            )

    def create_car_card(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo car card.

        O ``data`` deve seguir a estrutura definida na documentação da API,
        contendo obrigatoriamente ``name`` e ``watch_lists``.

        :param data: Dicionário com os campos do card.
        :return: Dicionário com o card criado.
        :raises TypeError: Se ``data`` ou algum campo possuir tipo inválido.
        :raises ValueError: Para campos obrigatórios ausentes ou fora do padrão.
        :raises RuntimeError: Caso o token de autenticação seja inválido.
        :raises ConnectionError: Se a API retornar erro durante a criação.
        """

        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        if "name" not in data:
            raise ValueError("O campo obrigatório 'name' está ausente.")
        if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
            raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "watch_lists" not in data:
            raise ValueError("O campo obrigatório 'watch_lists' está ausente.")
        if not isinstance(data["watch_lists"], list) or not all(isinstance(i, int) for i in data["watch_lists"]):
            raise TypeError("O campo 'watch_lists' deve ser uma lista de inteiros.")

        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if "meta" in data and not isinstance(data["meta"], dict):
            raise TypeError("O campo 'meta' deve ser um dicionário.")

        if "active_after" in data and not isinstance(data["active_after"], str):
            raise TypeError("O campo 'active_after' deve ser uma string ISO 8601.")

        if "active_before" in data and not isinstance(data["active_before"], str):
            raise TypeError("O campo 'active_before' deve ser uma string ISO 8601.")

        if "disable_schedule" in data:
            if not isinstance(data["disable_schedule"], dict):
                raise TypeError("O campo 'disable_schedule' deve ser um dicionário.")
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            for day, blocks in data["disable_schedule"].items():
                if day not in valid_days:
                    raise ValueError(f"Dia inválido em 'disable_schedule': {day}")
                if not isinstance(blocks, list) or not all(
                    isinstance(block, list) and all(isinstance(h, str) for h in block) for block in blocks
                ):
                    raise TypeError(
                        f"'disable_schedule[{day}]' deve ser uma lista de listas de strings."
                    )

        if "license_plate_number" in data and not (
            isinstance(data["license_plate_number"], str) or data["license_plate_number"] is None
        ):
            raise TypeError("O campo 'license_plate_number' deve ser uma string ou None.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/cars/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=data, verify=False)

        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao criar car card: {response.status_code} - {response.text}"
            )

    def get_car_card_by_id(self, card_id: int) -> Dict[str, Any]:
        """Recupera os dados de um car card específico.

        :param card_id: Identificador do card desejado.
        :return: Dicionário com os dados retornados pela API.
        :raises TypeError: Se ``card_id`` não for inteiro.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ValueError: Se nenhum card for encontrado com esse ID.
        :raises ConnectionError: Para outros erros de comunicação.
        """

        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/cars/{card_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise ValueError(f"Card com ID {card_id} não encontrado.")
        else:
            raise ConnectionError(
                f"Erro ao buscar car card {card_id}: {response.status_code} - {response.text}"
            )

    def delete_car_card(self, card_id: int) -> None:
        """Remove permanentemente um car card.

        :param card_id: ID do card a ser removido.
        :raises TypeError: Se ``card_id`` não for inteiro.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ValueError: Se o card não existir.
        :raises ConnectionError: Para outros erros de comunicação.
        """

        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/cars/{card_id}/"
        headers: Dict[str, str] = {"Authorization": f"Token {self.token}"}

        response = requests.delete(url, headers=headers, verify=False)

        if response.status_code == 204:
            return
        elif response.status_code == 404:
            raise ValueError(f"O card com ID {card_id} não foi encontrado.")
        else:
            raise ConnectionError(
                f"Erro ao deletar car card {card_id}: {response.status_code} - {response.text}"
            )

    def update_car_card(self, card_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza parcialmente um car card existente.

        ``data`` segue a mesma estrutura aceita em :py:meth:`create_car_card`.

        :param card_id: ID do card a ser atualizado.
        :param data: Campos a modificar.
        :return: Dicionário com os dados atualizados.
        :raises TypeError: Caso ``card_id`` ou ``data`` tenham tipo incorreto.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Quando a API retorna erro na atualização.
        """

        if not isinstance(card_id, int):
            raise TypeError("O parâmetro 'card_id' deve ser um inteiro.")

        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        if "name" in data:
            if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
                raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "watch_lists" in data:
            if not isinstance(data["watch_lists"], list) or not all(isinstance(i, int) for i in data["watch_lists"]):
                raise TypeError("O campo 'watch_lists' deve ser uma lista de inteiros.")

        if "meta" in data and not isinstance(data["meta"], dict):
            raise TypeError("O campo 'meta' deve ser um dicionário.")

        if "active_after" in data and not isinstance(data["active_after"], str):
            raise TypeError("O campo 'active_after' deve ser uma string ISO 8601.")

        if "active_before" in data and not isinstance(data["active_before"], str):
            raise TypeError("O campo 'active_before' deve ser uma string ISO 8601.")

        if "disable_schedule" in data:
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            disable_schedule = data["disable_schedule"]
            if not isinstance(disable_schedule, dict):
                raise TypeError("O campo 'disable_schedule' deve ser um dicionário.")
            for day, blocks in disable_schedule.items():
                if day not in valid_days:
                    raise ValueError(f"Dia inválido em 'disable_schedule': {day}")
                if not isinstance(blocks, list) or not all(
                    isinstance(b, list) and all(isinstance(h, str) for h in b) for b in blocks
                ):
                    raise TypeError(
                        f"'disable_schedule[{day}]' deve ser uma lista de listas de strings."
                    )

        if "license_plate_number" in data and not (
            isinstance(data["license_plate_number"], str) or data["license_plate_number"] is None
        ):
            raise TypeError("O campo 'license_plate_number' deve ser uma string ou None.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/cards/cars/{card_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        response = requests.patch(url, headers=headers, json=data, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao atualizar o car card {card_id}: {response.status_code} - {response.text}"
            )

    def get_watch_lists(
        self,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recupera as watch lists cadastradas.

        Os argumentos correspondem aos filtros da API ``/watch-lists/``.
        Todos são opcionais e devem respeitar os tipos abaixo.

        :return: Dicionário com o resultado retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Caso o token de autenticação seja inválido.
        :raises ConnectionError: Em caso de falha de comunicação com a API.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
                "ordering",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo int.")
            elif nome == "id_in":
                if not (
                    isinstance(valor, list)
                    and all(isinstance(x, int) for x in valor)
                ):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de inteiros.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "url", "headers"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        try:
            response = requests.get(url, headers=headers, params=params, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao buscar watch lists: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao buscar watch lists: {response.status_code} - {response.text}"
            )

    def create_watch_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria uma nova watch list.

        :param data: Dados conforme a API ``/watch-lists/``.
        :return: Dicionário com a watch list criada.
        :raises TypeError: Quando ``data`` possui tipo inválido.
        :raises ValueError: Para campos obrigatórios ausentes ou fora do padrão.
        :raises RuntimeError: Se o token não estiver definido.
        :raises ConnectionError: Em caso de falha na comunicação com a API.
        """

        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        if "name" not in data:
            raise ValueError("O campo obrigatório 'name' está ausente.")
        if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
            raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if "camera_groups" in data:
            if not isinstance(data["camera_groups"], list) or not all(isinstance(i, int) for i in data["camera_groups"]):
                raise TypeError("O campo 'camera_groups' deve ser uma lista de inteiros.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, headers=headers, json=data, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao criar watch list: {exc}") from exc

        if response.status_code in (200, 201):
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao criar watch list: {response.status_code} - {response.text}"
            )

    def get_watch_list_by_id(self, list_id: int) -> Dict[str, Any]:
        """Recupera uma watch list específica.

        :param list_id: ID da watch list.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``list_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ValueError: Caso a lista não exista.
        :raises ConnectionError: Em erros de comunicação.
        """

        if not isinstance(list_id, int):
            raise TypeError("O parâmetro 'list_id' deve ser um inteiro.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/{list_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao buscar watch list {list_id}: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            raise ValueError(f"Watch list com ID {list_id} não encontrada.")
        else:
            raise ConnectionError(
                f"Erro ao buscar watch list {list_id}: {response.status_code} - {response.text}"
            )

    def delete_watch_list(self, list_id: int) -> None:
        """Remove uma watch list existente.

        :param list_id: ID da lista.
        :raises TypeError: Se ``list_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ValueError: Caso a lista não exista.
        :raises ConnectionError: Em erros de comunicação.
        """

        if not isinstance(list_id, int):
            raise TypeError("O parâmetro 'list_id' deve ser um inteiro.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/{list_id}/"
        headers: Dict[str, str] = {"Authorization": f"Token {self.token}"}

        try:
            response = requests.delete(url, headers=headers, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao deletar watch list {list_id}: {exc}") from exc

        if response.status_code == 204:
            return
        elif response.status_code == 404:
            raise ValueError(f"Watch list com ID {list_id} não encontrada.")
        else:
            raise ConnectionError(
                f"Erro ao deletar watch list {list_id}: {response.status_code} - {response.text}"
            )

    def update_watch_list(self, list_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza parcialmente uma watch list.

        :param list_id: ID da watch list.
        :param data: Campos a atualizar.
        :return: Dicionário retornado pela API.
        :raises TypeError: Para tipos incorretos.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em erros de comunicação.
        """

        if not isinstance(list_id, int):
            raise TypeError("O parâmetro 'list_id' deve ser um inteiro.")

        if not isinstance(data, dict):
            raise TypeError("O parâmetro 'data' deve ser um dicionário.")

        if "name" in data:
            if not isinstance(data["name"], str) or not (1 <= len(data["name"]) <= 256):
                raise ValueError("O campo 'name' deve ser uma string entre 1 e 256 caracteres.")

        if "camera_groups" in data:
            if not isinstance(data["camera_groups"], list) or not all(isinstance(i, int) for i in data["camera_groups"]):
                raise TypeError("O campo 'camera_groups' deve ser uma lista de inteiros.")

        if "active" in data and not isinstance(data["active"], bool):
            raise TypeError("O campo 'active' deve ser booleano.")

        if "comment" in data:
            if not isinstance(data["comment"], str):
                raise TypeError("O campo 'comment' deve ser uma string.")
            if len(data["comment"]) > 2048:
                raise ValueError("O campo 'comment' não pode exceder 2048 caracteres.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/{list_id}/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.patch(url, headers=headers, json=data, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao atualizar watch list {list_id}: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao atualizar watch list {list_id}: {response.status_code} - {response.text}"
            )

    def purge_watch_list(self, list_id: int) -> None:
        """Remove todos os cards de uma watch list.

        :param list_id: ID da watch list.
        :raises TypeError: Se ``list_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ValueError: Se a lista não existir.
        :raises ConnectionError: Em erros de comunicação.
        """

        if not isinstance(list_id, int):
            raise TypeError("O parâmetro 'list_id' deve ser um inteiro.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/{list_id}/purge/"
        headers: Dict[str, str] = {"Authorization": f"Token {self.token}"}

        try:
            response = requests.post(url, headers=headers, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao limpar watch list {list_id}: {exc}") from exc

        if response.status_code == 204:
            return
        elif response.status_code == 404:
            raise ValueError(f"Watch list com ID {list_id} não encontrada.")
        else:
            raise ConnectionError(
                f"Erro ao limpar watch list {list_id}: {response.status_code} - {response.text}"
            )

    def get_watch_lists_count(
        self,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        id_in: Optional[List[int]] = None,
    ) -> int:
        """Retorna a quantidade de watch lists registradas.

        Os parâmetros são equivalentes aos de :py:meth:`get_watch_lists`.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser do tipo int.")
            elif nome == "id_in":
                if not (
                    isinstance(valor, list)
                    and all(isinstance(x, int) for x in valor)
                ):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de inteiros.")

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/count/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "url", "headers"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        try:
            response = requests.get(url, headers=headers, params=params, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao contar watch lists: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            return int(data.get("count", 0))
        else:
            raise ConnectionError(
                f"Erro ao contar watch lists: {response.status_code} - {response.text}"
            )

    def purge_all_watch_lists(self) -> Dict[str, Any]:
        """Remove todos os cards de todas as watch lists."""

        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        url: str = f"{self.url_base}/watch-lists/purge_all/"
        headers: Dict[str, str] = {"Authorization": f"Token {self.token}"}

        try:
            response = requests.post(url, headers=headers, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao purgar todas as watch lists: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao purgar todas as watch lists: {response.status_code} - {response.text}"
            )

    # ------------------------------------------------------------------
    # Area triggers
    # ------------------------------------------------------------------

    def get_area_trigger_activations(
        self,
        active: Optional[bool] = None,
        area: Optional[List[int]] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        duration_gte: Optional[int] = None,
        duration_lte: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        max_body_count_gte: Optional[int] = None,
        max_body_count_lte: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recupera ativações de area trigger com filtros opcionais.

        Os argumentos mapeiam os filtros disponíveis na API
        ``/area-trigger-activations/``. Todos são opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {"active"}:
                if not isinstance(valor, bool):
                    raise TypeError(f"O parâmetro '{nome}' deve ser bool.")
            elif nome in {"area", "id_in"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser uma lista de inteiros.")
            elif nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
                "ordering",
                "page",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "duration_gte",
                "duration_lte",
                "limit",
                "max_body_count_gte",
                "max_body_count_lte",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/area-trigger-activations/", params=params)

    def get_area_trigger_activation_by_id(self, act_id: int) -> Dict[str, Any]:
        """Recupera os dados de uma ativação específica.

        :param act_id: Identificador da ativação.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``act_id`` não for inteiro.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Em caso de erro de comunicação.
        """

        if not isinstance(act_id, int):
            raise TypeError("act_id deve ser int")
        return self._request("GET", f"/area-trigger-activations/{act_id}/")

    def count_area_trigger_activations(self) -> int:
        """Quantidade de ativações."""
        data = self._request("GET", "/area-trigger-activations/count/")
        return int(data.get("count", 0))

    def get_area_trigger_records(
        self,
        area: Optional[List[int]] = None,
        area_trigger: Optional[List[int]] = None,
        body_count_gte: Optional[int] = None,
        body_count_lte: Optional[int] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Obtém registros de ativações de área com filtros opcionais.

        Os parâmetros refletem os filtros do endpoint
        ``/area-trigger-records/`` e todos são opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Caso algum parâmetro tenha tipo incorreto.
        :raises RuntimeError: Se o token não for válido.
        :raises ConnectionError: Em falhas de comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {"area", "area_trigger", "id_in"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser uma lista de inteiros.")
            elif nome in {"ordering", "page", "created_date_gt", "created_date_gte", "created_date_lt", "created_date_lte"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "body_count_gte",
                "body_count_lte",
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/area-trigger-records/", params=params)

    def get_area_trigger_record_by_id(self, rec_id: int) -> Dict[str, Any]:
        """Recupera um registro de área específico pelo ID.

        :param rec_id: Identificador do registro.
        :return: Dicionário com os dados retornados pela API.
        :raises TypeError: Se ``rec_id`` não for inteiro.
        :raises RuntimeError: Se o token estiver inválido.
        :raises ConnectionError: Em caso de falha de comunicação.
        """

        if not isinstance(rec_id, int):
            raise TypeError("rec_id deve ser int")
        return self._request("GET", f"/area-trigger-records/{rec_id}/")

    def count_area_trigger_records(self) -> int:
        data = self._request("GET", "/area-trigger-records/count/")
        return int(data.get("count", 0))

    def get_areas(
        self,
        camera_groups: Optional[List[int]] = None,
        cameras: Optional[List[int]] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        enabled: Optional[bool] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        multi_camera: Optional[bool] = None,
        name_contains: Optional[str] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retorna a lista de áreas cadastradas conforme filtros.

        Parâmetros correspondem aos filtros do endpoint ``/areas/``.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Caso o token seja inválido.
        :raises ConnectionError: Em erro de comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {"enabled", "multi_camera"}:
                if not isinstance(valor, bool):
                    raise TypeError(f"O parâmetro '{nome}' deve ser bool.")
            elif nome in {"camera_groups", "cameras", "id_in"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser uma lista de inteiros.")
            elif nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
                "name_contains",
                "ordering",
                "page",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/areas/", params=params)

    def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("POST", "/areas/", expected=201, json=data)

    def get_area_by_id(self, area_id: int) -> Dict[str, Any]:
        """Recupera uma área específica pelo ID.

        :param area_id: Identificador da área.
        :return: Dicionário com os dados retornados pela API.
        :raises TypeError: Se ``area_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        if not isinstance(area_id, int):
            raise TypeError("area_id deve ser int")
        return self._request("GET", f"/areas/{area_id}/")

    def delete_area(self, area_id: int) -> None:
        if not isinstance(area_id, int):
            raise TypeError("area_id deve ser int")
        self._request("DELETE", f"/areas/{area_id}/", expected=204)

    def update_area(self, area_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(area_id, int):
            raise TypeError("area_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/areas/{area_id}/", json=data)

    def count_areas(self) -> int:
        data = self._request("GET", "/areas/count/")
        return int(data.get("count", 0))

    # ------------------------------------------------------------------
    # Camera groups
    # ------------------------------------------------------------------

    def get_camera_groups(
        self,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        id_gte: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista grupos de câmeras com filtros opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Caso o token seja inválido.
        :raises ConnectionError: Em falhas na comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome == "id_gte":
                if not isinstance(valor, int):
                    raise TypeError("O parâmetro 'id_gte' deve ser int.")
            elif nome in {"id_in"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de inteiros.")
            elif nome in {"ordering", "created_date_gt", "created_date_gte", "created_date_lt", "created_date_lte"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/camera-groups/", params=params)

    def create_camera_group(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("POST", "/camera-groups/", expected=201, json=data)

    def get_camera_group_by_id(self, group_id: int) -> Dict[str, Any]:
        """Obtém um grupo de câmeras específico.

        :param group_id: ID do grupo de câmeras.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``group_id`` não for inteiro.
        :raises RuntimeError: Se o token estiver inválido.
        :raises ConnectionError: Em falhas de comunicação.
        """

        if not isinstance(group_id, int):
            raise TypeError("group_id deve ser int")
        return self._request("GET", f"/camera-groups/{group_id}/")

    def delete_camera_group(self, group_id: int) -> None:
        if not isinstance(group_id, int):
            raise TypeError("group_id deve ser int")
        self._request("DELETE", f"/camera-groups/{group_id}/", expected=204)

    def update_camera_group(self, group_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(group_id, int):
            raise TypeError("group_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/camera-groups/{group_id}/", json=data)

    def count_camera_groups(self) -> int:
        data = self._request("GET", "/camera-groups/count/")
        return int(data.get("count", 0))

    # ------------------------------------------------------------------
    # Cameras
    # ------------------------------------------------------------------

    def get_cameras(
        self,
        active: Optional[bool] = None,
        camera_groups: Optional[List[int]] = None,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        external_detector: Optional[bool] = None,
        external_vms: Optional[List[int]] = None,
        external_vms_camera_id_contains: Optional[str] = None,
        from_external_vms: Optional[bool] = None,
        has_coordinates: Optional[bool] = None,
        id_gte: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        latitude_gte: Optional[float] = None,
        latitude_lte: Optional[float] = None,
        limit: Optional[int] = None,
        longitude_gte: Optional[float] = None,
        longitude_lte: Optional[float] = None,
        name_contains: Optional[str] = None,
        object_type: Optional[str] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
        state_color: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista câmeras configuradas aplicando filtros.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em erros de comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome in {"active", "external_detector", "from_external_vms", "has_coordinates"}:
                if not isinstance(valor, bool):
                    raise TypeError(f"O parâmetro '{nome}' deve ser bool.")
            elif nome in {"camera_groups", "external_vms", "id_in"}:
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser uma lista de inteiros.")
            elif nome in {
                "created_date_gt",
                "created_date_gte",
                "created_date_lt",
                "created_date_lte",
                "external_vms_camera_id_contains",
                "name_contains",
                "object_type",
                "ordering",
                "page",
                "state_color",
            }:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "id_gte",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")
            elif nome in {
                "latitude_gte",
                "latitude_lte",
                "longitude_gte",
                "longitude_lte",
            }:
                if not isinstance(valor, (int, float)):
                    raise TypeError(f"O parâmetro '{nome}' deve ser numérico.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/cameras/", params=params)

    def create_camera(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("POST", "/cameras/", expected=201, json=data)

    def get_camera_by_id(self, cam_id: int) -> Dict[str, Any]:
        """Recupera uma câmera específica pelo ID.

        :param cam_id: Identificador da câmera.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``cam_id`` não for inteiro.
        :raises RuntimeError: Se o token estiver inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        return self._request("GET", f"/cameras/{cam_id}/")

    def update_camera(self, cam_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PUT", f"/cameras/{cam_id}/", json=data)

    def patch_camera(self, cam_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/cameras/{cam_id}/", json=data)

    def delete_camera(self, cam_id: int) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        self._request("DELETE", f"/cameras/{cam_id}/", expected=204)

    def camera_restart(self, cam_id: int) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        self._request("POST", f"/cameras/{cam_id}/restart/", expected=204)

    def camera_get_screenshot(self, cam_id: int) -> bytes:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        resp = self._request("GET", f"/cameras/{cam_id}/screenshot/")
        return resp

    def camera_take_screenshot(self, cam_id: int) -> bytes:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        resp = self._request("POST", f"/cameras/{cam_id}/screenshot/", expected=200)
        return resp

    def camera_ptz(self, cam_id: int, data: Dict[str, Any]) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        self._request("POST", f"/cameras/{cam_id}/ptz/", expected=204, json=data)

    def count_cameras(self) -> int:
        data = self._request("GET", "/cameras/count/")
        return int(data.get("count", 0))

    def get_cameras_default_parameters(self) -> Dict[str, Any]:
        return self._request("GET", "/cameras/default_parameters/")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def get_car_events(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is not None and not isinstance(params, dict):
            raise TypeError("params deve ser um dicionário.")
        return self._request("GET", "/events/cars/", params=params)

    def get_car_event_by_id(self, event_id: int) -> Dict[str, Any]:
        if not isinstance(event_id, int):
            raise TypeError("event_id deve ser int")
        return self._request("GET", f"/events/cars/{event_id}/")

    def update_car_event(self, event_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(event_id, int):
            raise TypeError("event_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/events/cars/{event_id}/", json=data)

    def acknowledge_car_events(self) -> None:
        self._request("POST", "/events/cars/acknowledge/", expected=200)

    def add_car_event(self, files: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not isinstance(files, dict):
            raise TypeError("files deve ser dict")
        if data is not None and not isinstance(data, dict):
            raise TypeError("data deve ser dict ou None")
        return self._request(
            "POST",
            "/events/cars/add/",
            files=files,
            data=data,
            expected=200,
        )

    def get_face_events(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params is not None and not isinstance(params, dict):
            raise TypeError("params deve ser um dicionário.")
        return self._request("GET", "/events/faces/", params=params)

    def get_face_event_by_id(self, event_id: int) -> Dict[str, Any]:
        if not isinstance(event_id, int):
            raise TypeError("event_id deve ser int")
        return self._request("GET", f"/events/faces/{event_id}/")

    def update_face_event(self, event_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(event_id, int):
            raise TypeError("event_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/events/faces/{event_id}/", json=data)

    def acknowledge_face_events(self) -> None:
        self._request("POST", "/events/faces/acknowledge/", expected=200)

    def add_face_event(
        self,
        token: str,
        fullframe: Union[str, bytes, io.BytesIO],
        camera: Optional[int] = None,
        rotate: Optional[bool] = None,
        timestamp: Optional[str] = None,
        mf_selector: str = "all",
        roi: Optional[List[int]] = None,
        temperature: Optional[float] = None,
        liveness: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cria novos eventos de face a partir de uma imagem fornecida.

        :param token: Token da API para criação de eventos (obrigatório, min 1 char).
        :param fullframe: Frame completo do evento - caminho do arquivo, bytes ou BytesIO (obrigatório).
        :param camera: ID da câmera relacionada (opcional).
        :param rotate: Tenta rotacionar a imagem fonte (opcional).
        :param timestamp: Timestamp do evento no formato ISO 8601 (opcional).
        :param mf_selector: Define o comportamento quando múltiplos objetos estão presentes.
                           Valores permitidos: 'biggest' (padrão) ou 'all'.
                           - 'all': Seleciona todos os objetos no fullframe
                           - 'biggest': Seleciona o maior objeto no fullframe
        :param roi: Coordenadas dos pontos ROI para detecção: [left, top, right, bottom] (opcional).
        :param temperature: Temperatura (apenas para detectores externos) (opcional).
        :param liveness: Vivacidade (apenas para detectores externos) (opcional).
        :return: Dicionário com os dados retornados pela API.
        :raises TypeError: Se algum parâmetro possuir tipo incorreto.
        :raises ValueError: Se algum parâmetro estiver fora do padrão esperado.
        :raises RuntimeError: Se o token de autenticação for inválido.
        :raises ConnectionError: Em caso de falha na comunicação com a API.
        """

        # --- Validação do token ---
        if not isinstance(self.token, str) or not self.token:
            raise RuntimeError("Token de autenticação inválido ou ausente.")

        # --- Validação do token de criação de eventos ---
        if not isinstance(token, str) or len(token) < 1:
            raise ValueError("O parâmetro 'token' deve ser uma string com no mínimo 1 caractere.")

        # --- Validação do mf_selector ---
        if mf_selector not in {"biggest", "all"}:
            raise ValueError("O parâmetro 'mf_selector' deve ser 'biggest' ou 'all'.")

        # --- Validação dos opcionais ---
        if camera is not None and not isinstance(camera, int):
            raise TypeError("O parâmetro 'camera' deve ser um inteiro.")

        if rotate is not None and not isinstance(rotate, bool):
            raise TypeError("O parâmetro 'rotate' deve ser booleano.")

        if timestamp is not None and not isinstance(timestamp, str):
            raise TypeError("O parâmetro 'timestamp' deve ser uma string no formato ISO 8601.")

        if roi is not None:
            if not isinstance(roi, list) or len(roi) != 4:
                raise ValueError("O parâmetro 'roi' deve ser uma lista com 4 elementos [left, top, right, bottom].")
            if not all(isinstance(x, int) for x in roi):
                raise TypeError("Todos os elementos de 'roi' devem ser inteiros.")

        if temperature is not None and not isinstance(temperature, (int, float)):
            raise TypeError("O parâmetro 'temperature' deve ser numérico.")

        if liveness is not None and not isinstance(liveness, (int, float)):
            raise TypeError("O parâmetro 'liveness' deve ser numérico.")

        # --- Preparação da imagem fullframe ---
        if isinstance(fullframe, str):
            caminho = Path(fullframe)
            if not caminho.exists() or not caminho.is_file():
                raise FileNotFoundError(f"Arquivo '{fullframe}' não encontrado.")
            file_data = caminho.read_bytes()
            file_name = caminho.name
        elif isinstance(fullframe, bytes):
            file_data = fullframe
            file_name = "fullframe.jpg"
        elif isinstance(fullframe, io.BytesIO):
            file_data = fullframe.getvalue()
            file_name = "fullframe.jpg"
        else:
            raise TypeError("O parâmetro 'fullframe' deve ser str, bytes ou io.BytesIO.")

        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # --- Montagem da requisição ---
        url: str = f"{self.url_base}/events/faces/add/"
        headers: Dict[str, str] = {
            "Authorization": f"Token {self.token}"
        }

        # Preparação dos arquivos
        files: Dict[str, Any] = {
            "fullframe": (file_name, file_data, mime_type)
        }

        # Preparação dos dados do formulário
        data: Dict[str, Any] = {
            "token": token,
            "mf_selector": mf_selector
        }

        if camera is not None:
            data["camera"] = str(camera)
        if rotate is not None:
            data["rotate"] = "true" if rotate else "false"
        if timestamp is not None:
            data["timestamp"] = timestamp
        if temperature is not None:
            data["temperature"] = str(temperature)
        if liveness is not None:
            data["liveness"] = str(liveness)

        # ROI deve ser enviado como múltiplos campos com o mesmo nome
        # Similar ao curl: -F "roi=348" -F "roi=243" -F "roi=460" -F "roi=382"
        if roi is not None:
            # Cria uma lista de tuplas para enviar múltiplos valores com a mesma chave
            data_list = [(k, v) for k, v in data.items()]
            for valor in roi:
                data_list.append(("roi", str(valor)))
            data = data_list

        try:
            response = requests.post(url, headers=headers, files=files, data=data, verify=False)
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Erro ao criar evento de face: {exc}") from exc

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError(
                f"Erro ao criar evento de face: {response.status_code} - {response.text}"
            )

    # ------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------

    def get_body_objects(
        self,
        active: Optional[bool] = None,
        card: Optional[List[int]] = None,
        id_in: Optional[List[str]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista objetos de corpo com filtros opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em falhas na comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome == "active":
                if not isinstance(valor, bool):
                    raise TypeError("O parâmetro 'active' deve ser bool.")
            elif nome == "card":
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError("O parâmetro 'card' deve ser uma lista de inteiros.")
            elif nome == "id_in":
                if not (isinstance(valor, list) and all(isinstance(x, str) for x in valor)):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de strings.")
            elif nome in {"ordering", "page"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {"limit"}:
                if not isinstance(valor, int):
                    raise TypeError("O parâmetro 'limit' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/objects/bodies/", params=params)

    def create_body_object(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("POST", "/objects/bodies/", expected=201, json=data)

    def get_body_object_by_id(self, obj_id: int) -> Dict[str, Any]:
        """Recupera um objeto de corpo pelo ID.

        :param obj_id: Identificador do objeto.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``obj_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        return self._request("GET", f"/objects/bodies/{obj_id}/")

    def update_body_object(self, obj_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/objects/bodies/{obj_id}/", json=data)

    def delete_body_object(self, obj_id: int) -> None:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        self._request("DELETE", f"/objects/bodies/{obj_id}/", expected=204)

    def get_car_objects(
        self,
        active: Optional[bool] = None,
        card: Optional[List[int]] = None,
        id_in: Optional[List[str]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista objetos de carro aplicando filtros.

        :return: Dicionário retornado pela API.
        :raises TypeError: Para parâmetros com tipo incorreto.
        :raises RuntimeError: Se o token não for válido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome == "active":
                if not isinstance(valor, bool):
                    raise TypeError("O parâmetro 'active' deve ser bool.")
            elif nome == "card":
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError("O parâmetro 'card' deve ser uma lista de inteiros.")
            elif nome == "id_in":
                if not (isinstance(valor, list) and all(isinstance(x, str) for x in valor)):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de strings.")
            elif nome in {"ordering", "page"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome == "limit":
                if not isinstance(valor, int):
                    raise TypeError("O parâmetro 'limit' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/objects/cars/", params=params)

    def create_car_object(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("POST", "/objects/cars/", expected=201, json=data)

    def get_car_object_by_id(self, obj_id: int) -> Dict[str, Any]:
        """Retorna um objeto de carro pelo ID.

        :param obj_id: Identificador do objeto.
        :return: Dicionário com os dados retornados.
        :raises TypeError: Se ``obj_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em falha de comunicação.
        """

        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        return self._request("GET", f"/objects/cars/{obj_id}/")

    def update_car_object(self, obj_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/objects/cars/{obj_id}/", json=data)

    def delete_car_object(self, obj_id: int) -> None:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        self._request("DELETE", f"/objects/cars/{obj_id}/", expected=204)

    def get_face_objects(
        self,
        active: Optional[bool] = None,
        card: Optional[List[int]] = None,
        id_in: Optional[List[str]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista objetos de face com filtros opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Quando algum parâmetro possui tipo incorreto.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em falhas de comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome == "active":
                if not isinstance(valor, bool):
                    raise TypeError("O parâmetro 'active' deve ser bool.")
            elif nome == "card":
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError("O parâmetro 'card' deve ser uma lista de inteiros.")
            elif nome == "id_in":
                if not (isinstance(valor, list) and all(isinstance(x, str) for x in valor)):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de strings.")
            elif nome in {"ordering", "page"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome == "limit":
                if not isinstance(valor, int):
                    raise TypeError("O parâmetro 'limit' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/objects/faces/", params=params)

    def get_face_object_by_id(self, obj_id: int) -> Dict[str, Any]:
        """Recupera um objeto de face pelo ID.

        :param obj_id: Identificador do objeto.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``obj_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        return self._request("GET", f"/objects/faces/{obj_id}/")

    def update_face_object(self, obj_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/objects/faces/{obj_id}/", json=data)

    def delete_face_object(self, obj_id: int) -> None:
        if not isinstance(obj_id, int):
            raise TypeError("obj_id deve ser int")
        self._request("DELETE", f"/objects/faces/{obj_id}/", expected=204)

    # ------------------------------------------------------------------
    # ONVIF cameras
    # ------------------------------------------------------------------

    def get_onvif_cameras(
        self,
        created_date_gt: Optional[str] = None,
        created_date_gte: Optional[str] = None,
        created_date_last_n_days: Optional[int] = None,
        created_date_lt: Optional[str] = None,
        created_date_lte: Optional[str] = None,
        created_date_nth_full_week: Optional[int] = None,
        created_date_nth_work_week: Optional[int] = None,
        id_in: Optional[List[int]] = None,
        limit: Optional[int] = None,
        ordering: Optional[str] = None,
        page: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista câmeras ONVIF registradas com filtros opcionais.

        :return: Dicionário retornado pela API.
        :raises TypeError: Para parâmetros com tipo incorreto.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em falhas na comunicação.
        """

        for nome, valor in locals().items():
            if nome in {"self"} or valor is None:
                continue
            if nome == "id_in":
                if not (isinstance(valor, list) and all(isinstance(x, int) for x in valor)):
                    raise TypeError("O parâmetro 'id_in' deve ser uma lista de inteiros.")
            elif nome in {"ordering", "page", "created_date_gt", "created_date_gte", "created_date_lt", "created_date_lte"}:
                if not isinstance(valor, str):
                    raise TypeError(f"O parâmetro '{nome}' deve ser str.")
            elif nome in {
                "created_date_last_n_days",
                "created_date_nth_full_week",
                "created_date_nth_work_week",
                "limit",
            }:
                if not isinstance(valor, int):
                    raise TypeError(f"O parâmetro '{nome}' deve ser int.")

        params: Dict[str, Any] = {}
        for chave, valor in locals().items():
            if chave not in {"self", "params"} and valor is not None:
                if isinstance(valor, list):
                    params[chave] = ",".join(map(str, valor))
                else:
                    params[chave] = valor

        return self._request("GET", "/onvif-cameras/", params=params)

    def get_onvif_camera_by_id(self, cam_id: int) -> Dict[str, Any]:
        """Busca uma câmera ONVIF específica.

        :param cam_id: Identificador da câmera.
        :return: Dicionário retornado pela API.
        :raises TypeError: Se ``cam_id`` não for inteiro.
        :raises RuntimeError: Se o token for inválido.
        :raises ConnectionError: Em caso de falha na comunicação.
        """

        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        return self._request("GET", f"/onvif-cameras/{cam_id}/")

    def update_onvif_camera(self, cam_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        return self._request("PATCH", f"/onvif-cameras/{cam_id}/", json=data)

    def onvif_camera_auth(self, cam_id: int, data: Dict[str, Any]) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        if not isinstance(data, dict):
            raise TypeError("data deve ser dict")
        self._request("POST", f"/onvif-cameras/{cam_id}/auth/", expected=204, json=data)

    def onvif_camera_start_streaming(self, cam_id: int) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        self._request("POST", f"/onvif-cameras/{cam_id}/start-streaming/", expected=204)

    def onvif_camera_stop_streaming(self, cam_id: int) -> None:
        if not isinstance(cam_id, int):
            raise TypeError("cam_id deve ser int")
        self._request("POST", f"/onvif-cameras/{cam_id}/stop-streaming/", expected=204)


