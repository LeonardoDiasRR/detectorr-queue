# Design Fix: Immutable Frame Attribute

## Problema Identificado

Tentativas de fazer cleanup manual do atributo `frame` em Event levou a um design inseguro onde:
- O frame poderia ser setado para None em qualquer momento
- Violava o princípio de encapsulamento
- Causava race conditions (frame None ao copiar evento)
- Criava lógica complexa e frágil de gerenciamento de memória

## Causa Raiz

O design original tentava fazer cleanup manual de recursos (frame) ao invés de confiar na garbage collection. Isto é um anti-padrão que causou:
1. Estados intermediários inválidos (frame = None)
2. Race conditions entre threads
3. Sequências de limpeza frágeis e propensas a erros

## Solução Implementada

### ✅ Princípio Fundamental
**O atributo `frame` de um Event é imutável e nunca pode ser None.**

O frame é liberado da memória **apenas quando o próprio objeto Event é garbage collected**, não antes.

### Mudanças Realizadas

#### 1️⃣ **Event.cleanup() Removido**
`src/domain/entities/event_entity.py`

- ❌ Removido método `cleanup()` que zeravaframe
- ❌ Removidas tentativas de controlar limpeza manual de frame
- ✅ Frame agora é imutável durante todo ciclo de vida do Event

#### 2️⃣ **Event.copy() Simplificado**
`src/domain/entities/event_entity.py`

- ✅ Valida se frame é instância válida de Frame (não None)
- ✅ Mensagens de erro claras indicam corrupção de dados
- ✅ Sem mais verificação de "frame foi zerado" 

#### 3️⃣ **Track._release_event_memory() Simplificado**
`src/domain/entities/track_entity.py`

- ❌ Removidas chamadas a `event.cleanup()`
- ✅ Apenas remove referência (= None)
- ✅ Garbage collection cuida do resto

#### 4️⃣ **Track.cleanup() Simplificado**
`src/domain/entities/track_entity.py`

- ✅ Apenas remove referências a first_event e last_event
- ✅ Não tenta fazer cleanup dos eventos
- ✅ Mantém best_event intacto

#### 5️⃣ **Track.finalize() Simplificado**
`src/domain/entities/track_entity.py`

- ✅ Chama cleanup() para remover referências
- ✅ Remove referência a best_event
- ✅ Zera contadores
- ✅ Deixa garbage collection fazer seu trabalho

#### 6️⃣ **Removidas Chamadas a event.cleanup()**
- ❌ `detect_faces_use_case.py`: Removido `event.cleanup()`
- ❌ `send_to_findface_use_case.py`: Removido `event.cleanup()`

### Novo Fluxo de Lifecycle

```
Event criado
  ↓
Enfileirado em fila
  ↓
Consumido por worker
  ↓
Processado (frame é lido mas nunca modificado)
  ↓
Referência removida (= None)
  ↓
Garbage Collection libera memória automaticamente
```

## Benefícios

✅ **Seguro por Design**: Sem estados intermediários inválidos
✅ **Sem Race Conditions**: Frame nunca é zerado manualmente
✅ **Simples**: Deixa Python gerenciar memória automaticamente
✅ **Resiliente**: Não depende de sequências complexas de cleanup
✅ **Eficiente**: GC é otimizado para este padrão

## Design Principle: Trust the Garbage Collector

Em vez de tentar fazer cleanup manual:
- ❌ `frame = None` → deixa esperança de cleanup posterior
- ❌ `event.cleanup()` → sequência frágil e propensa a erros
- ❌ Múltiplos estados do objeto

Agora:
- ✅ Atributos imutáveis durante lifecycle
- ✅ Remover referência (= None) quando não mais precisa
- ✅ Confiar na GC para liberar memória

Este é o padrão Pythônico correto! 🐍

