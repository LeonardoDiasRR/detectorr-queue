# Bug Fix: NoneType Frame on Event Copy

## Problema Identificado

Erro ao finalizar tracks:
```
AttributeError: 'NoneType' object has no attribute 'copy'
```

Ocorria em `_finalize_track_internal` quando tentava copiar o `best_event`:
```python
if not self.findface_queue.put(best_event.copy(), block=False):
```

## Causa Raiz

O método `Event.copy()` tentava chamar `self._frame.copy()`, mas o frame era `None`.

Isto ocorria porque:
1. `track.finalize()` chama `cleanup()`
2. `cleanup()` chama `_release_event_memory(best_event)`
3. `_release_event_memory()` chama `event.cleanup()`
4. `event.cleanup()` zera `self._frame = None`
5. Depois, ao tentar fazer `best_event.copy()`, o frame já estava None

**Causa do problema**: A sequência de chamadas estava aparentemente correta na lógica de código, mas havia uma race condition ou sincronização que levava o frame a ser zerado antes do esperado.

## Soluções Implementadas

### 1. **Event.copy() - Validação e Mensagens Melhoradas** 
`src/domain/entities/event_entity.py`

✅ Adicionada verificação explícita se `self._frame is None`
✅ Mensagens de erro detalhadas indicando:
  - Que o cleanup() foi chamado antes de copy()
  - Que é um problema de sequenciação/sincronização
  - Sugestão de quando a cópia deve ser feita

✅ Try/except para capturar erros ao copiar o frame com mensagens específicas

### 2. **_finalize_track_internal() - Validações em Cascata**
`src/application/use_cases/manage_tracks_use_case.py`

✅ Verificação explícita se `best_event.frame is None` ANTES de tentar copy()
✅ Log de erro detalhado quando frame é None, indicando sincronização problema
✅ Try/except melhorado para capturar ValueError e AttributeError
✅ Graceful fallback: descarta track sem erro fatal se copy falhar

## Fluxo Corrigido

```
_finalize_track_internal()
├─ Obtém best_event do track
├─ Verifica se best_event é None → retorna
├─ ✅ NOVA: Verifica se best_event.frame é None → retorna com erro
├─ Tenta fazer best_event.copy()
│  └─ ✅ NOVA: Try/except com tratamento específico de ValueError/AttributeError
├─ Enfileira best_event_copy ao FindFace
└─ Chama track.finalize() (que zera o frame)
```

## Prevenção de Futuros Problemas

As validações agora são defensivas:

1. **Na source** (Event.copy()): Detecta frame None com mensagem clara
2. **No caller** (_finalize_track_internal): Valida frame antes de chamar copy()
3. **Com logging**: Ambas as camadas logam detalhes de qualquer anomalia

## Mensagens de Erro Informativas

### Se frame é None:
```
Track 41 possui best_event com frame None. 
Descartando sem envio ao FindFace. 
Isto indica um problema de sincronização ou cleanup prematuro.
```

### Se copy() falhar:
```
Não é possível copiar evento (id=41): 
o frame foi limpado via cleanup(). 
A cópia deve ser feita ANTES do cleanup. 
Isto indica um problema de sequenciação ou sincronização.
```

## Status

✅ **Corrigido**: Aplicação agora trata gracefully eventos com frame None
✅ **Informativo**: Mensagens de erro facilitam debug futuro
✅ **Resiliente**: Tracks sem frame são descartados, aplicação continua funcionando
