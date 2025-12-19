# Design Principles - Detectorr Queue

## 1. Immutable Attributes During Lifecycle

### Princípio
Atributos críticos de entidades nunca devem ser modificados após criação, exceto quando a entidade é descartada.

### Aplicação em Event
```python
# ❌ ERRADO: Frame pode ser None em qualquer momento
event._frame = None  # Estado inválido intermediário

# ✅ CORRETO: Frame é imutável durante ciclo de vida
# Apenas removemos a referência ao descartar o Event
best_event = None  # Remove referência, GC limpa memória
```

### Benefícios
- Elimina race conditions
- Previne estados intermediários inválidos
- Simplifica lógica de threading
- Facilita debug (estado sempre válido)

---

## 2. Trust the Garbage Collector

### Princípio
Confie na garbage collection do Python para liberar memória. Não faça cleanup manual de recursos que não requerem ação (como memoria).

### Aplicação
```python
# ❌ ERRADO: Cleanup manual frágil
class Event:
    def cleanup(self):
        self._frame = None  # Esperança de que ninguém acesse depois

# ✅ CORRETO: Deixar GC cuidar
class Event:
    # Frame é atributo imutável
    # Quando Event deixa de ser referenciado, GC libera tudo
```

### Quando NÃO Usar
- Recursos que requerem ação (arquivos, conexões, locks)
- Estes sim devem ter `__del__` ou context managers

### Quando Usar
- Objetos que contêm só memória (frames, arrays, etc)
- GC é otimizado para isto

---

## 3. Immutability for Thread Safety

### Princípio
Objetos imutáveis são naturalmente thread-safe. Não precisam de locks para leitura.

### Aplicação em Event
```python
# ✅ Thread-safe: Múltiplas threads podem ler frame
thread1 = Event(frame=frame_data, ...)  # Imutável
thread2 = event.copy()  # Lê frame sem locks
thread3 = event.frame   # Lê frame sem locks
```

### Race Condition Eliminada
```
# ANTES (com cleanup manual):
thread1: event.copy()     # Lê frame
thread2: event.cleanup()  # Zera frame
         # RACE CONDITION! ❌

# DEPOIS (sem cleanup):
thread1: event.copy()     # Lê frame
thread2: best_event = None # Remove referência, não toca frame
         # SEGURO! ✅
```

---

## 4. Single Responsibility + Composition

### Princípio
Cada objeto é responsável por seu próprio ciclo de vida, não pelo de seus componentes.

### Aplicação
```python
# ❌ ERRADO: Event responsável por liberar frame
class Event:
    def cleanup(self):
        self._frame = None  # Responsabilidade do frame

# ✅ CORRETO: Cada um cuida de si
class Event:
    pass  # Event é simples, imutável

class Track:
    def finalize(self):
        self._best_event = None  # Track remove sua referência
        # Best_event é liberado automaticamente se ninguém mais o referenciar
```

---

## 5. Defensive Programming in Boundaries

### Princípio
Validações devem estar nos limites (interfaces) entre componentes, não em cada operação.

### Aplicação
```python
# ✅ Validação em copy() (limite de transformação)
def copy(self) -> 'Event':
    if not isinstance(self._frame, Frame):
        raise TypeError("Frame corrompido")  # Detecta problema
    # ... resto da lógica
```

### NOT em cada acesso
```python
# ❌ ERRADO: Validar em cada lugar que acessa frame
@property
def frame(self) -> Frame:
    if self._frame is None:
        raise ValueError("Frame foi zerado")
    return self._frame
```

---

## 6. Explicit Error Messages

### Princípio
Mensagens de erro devem indicar: O QUÊ, ONDE, POR QUÊ, COMO ARRUMAR.

### Aplicação
```python
# ✅ BOM
raise TypeError(
    f"Frame corrompido no evento {self._id.value()}: "
    f"esperado Frame, recebido {type(self._frame).__name__}. "
    f"Isto indica um erro interno de integridade de dados."
)

# ❌ RUIM
raise TypeError("Frame error")
```

---

## 7. Separation of Concerns

### Princípio
Cada classe é responsável por sua lógica, não pela lógica de dependências.

### Aplicação
```
Event:
  - Armazena frame imutável
  - Fornece copy() para isolamento
  - NÃO gerencia limpeza manual

Track:
  - Gerencia eventos (coleciona, seleciona best)
  - Remove referências quando não mais precisa
  - Chamada por manageTracksUseCase

ManageTracksUseCase:
  - Orquestra eventos entre tracks
  - Finaliza tracks quando necessário
  - Enfileira best_event ao FindFace
```

Cada camada tem uma responsabilidade clara!

---

## 8. Graceful Degradation

### Princípio
Se uma operação falhar, o sistema deve continuar funcionando, possível degradadamente.

### Aplicação
```python
try:
    best_event_copy = best_event.copy()
except TypeError as e:
    logger.error(f"Erro ao copiar best_event: {e}")
    track.finalize()  # Descarta track
    del track
    return  # Continua com próximo track, não falha
```

---

## 9. Value Objects are Immutable

### Princípio
Value Objects (IdVO, BboxVO, etc) nunca mudam após criação.

### Aplicação
```python
# ✅ CORRETO: Value object imutável
bbox = BboxVO((x1, y1, x2, y2))
# bbox.value() sempre retorna (x1, y1, x2, y2)
# Nunca muda

# ❌ ERRADO: Tentar modificar
bbox._value = (new_x1, new_y1, new_x2, new_y2)  # Não faça isto!
```

---

## 10. Memory Management Delegation

### Princípio
Para memória gerenciada (não recursos de SO), delegue a GC.

### Comparação
```python
# Recurso de SO → Use context manager e __del__
with cv2.VideoCapture(rtsp_url) as capture:
    frame = capture.read()

# Memória pura → Use referência e GC
event = Event(frame=frame)
best_event = event.copy()  # Novo Event, nova memória
best_event = None  # GC libera quando ninguém mais referenciar
```

---

## Resumo dos Princípios

| Princípio | Aplicação | Benefício |
|-----------|-----------|-----------|
| **Immutability** | Atributos não mudam durante lifecycle | Thread-safe, sem race conditions |
| **Trust GC** | Não fazer cleanup manual de memória | Simples, eficiente, Pythônico |
| **Thread Safety** | Objetos imutáveis naturalmente seguros | Sem locks, sem deadlocks |
| **Single Responsibility** | Cada classe cuida de si | Código limpo, testável |
| **Defensive Boundaries** | Validações nas interfaces | Erros detectados cedo |
| **Explicit Errors** | Mensagens claras e informativas | Debug mais fácil |
| **Separation of Concerns** | Responsabilidades bem definidas | Manutenção facilitada |
| **Graceful Degradation** | Falha local ≠ falha global | Resiliência |
| **Value Objects** | Imutáveis e pequenos | Seguros e eficientes |
| **Delegation** | GC para memória, SO para recursos | Código simples e correto |

---

## Exemplo Completo: Event Lifecycle

```python
# 1. CRIAÇÃO: Frame é imutável
frame = Frame(...)
event = Event(frame=frame)  # Frame é armazenado imutavelmente

# 2. PROPAGAÇÃO: Pode ser copiado, nunca modificado
event_copy = event.copy()   # Novo Event com frame copiado
another_copy = event.copy() # Outro Event

# 3. CONSUMO: Lido por múltiplas threads simultaneamente
thread1: event.frame        # Seguro, frame é imutável
thread2: event_copy.frame   # Seguro, frames são diferentes
thread3: best_event.copy()  # Seguro, cria outra cópia

# 4. DESCARTE: Referências removidas, GC limpa
best_event = None           # Remove referência
event = None                # Remove referência
# GC libera memória quando todas as referências se forem

# Resultado: NENHUM Estado inválido intermediário! ✅
```

---

Este design é **seguro por padrão**, não requer verificações extras, e segue as melhores práticas Python. 🐍
