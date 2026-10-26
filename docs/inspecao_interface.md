# Inspeção da interface — 26/10/2026

## Verificação dimensional executada

A janela real foi aberta com dados fictícios (Maria Oliveira, conta 0001,
saldo de R$ 1.250,50) e persistência em diretório temporário. O arquivo
`bank.json` do projeto não foi utilizado.

Foram verificadas as dimensões dos componentes em dois tamanhos:

| Janela | Largura dos painéis | Texto de rótulos cortado | Componentes em grid fora do pai |
| --- | --- | --- | --- |
| 1180 × 800 | 565 e 569 pixels | Nenhum detectado | Nenhum detectado |
| 980 × 700 | 475 e 459 pixels | Nenhum detectado | Nenhum detectado |

A verificação comparou a largura medida pela fonte com a largura disponível
dos rótulos sem quebra de linha e conferiu os limites dos componentes
posicionados por `grid`. Ela não avalia esteticamente cores, espaços ou
sobreposições, nem garante o comportamento em todas as resoluções e escalas.

## Limitação da inspeção visual

A janela foi localizada pelo controle do computador. As duas tentativas de
capturar sua imagem, incluindo uma após reconexão e ativação da janela,
falharam com `window capture timed out: timed out waiting on channel`.

Portanto, a inspeção visual por imagem continua pendente. A janela de teste
foi encerrada e o diretório temporário foi descartado. Nenhuma biblioteca
foi instalada e nenhum código de negócio foi alterado durante esta inspeção.

Para concluir a revisão visual, é necessária uma captura da janela fornecida
pelo usuário ou o restabelecimento da captura pelo controle do computador.
