# Relatório de Alterações 2 - Formulário Solicitação de Serviços

## Alterações realizadas

1. Adicionada na aba **Dados da solicitação** a seleção obrigatória:
   - Cliente com contrato
   - Cliente sem contrato

2. Incluído o novo campo `tipo_cliente` no backend Flask:
   - validação obrigatória;
   - bloqueio de valores diferentes das duas opções permitidas;
   - inclusão no corpo do e-mail administrativo;
   - inclusão no XLSX enviado por e-mail;
   - inclusão na revisão antes do envio.

3. Corrigida e reforçada a validação automática de CEP no frontend:
   - máscara automática `00000-000`;
   - consulta ao ViaCEP assim que o campo tiver 8 números;
   - preenchimento automático da rua quando o CEP retorna logradouro;
   - bloqueio da próxima etapa quando o CEP é inválido;
   - validação também no evento `blur`.

4. Mantida validação de segurança no backend:
   - CEP com 8 dígitos;
   - bloqueio de CEP repetido como `00000-000`;
   - consulta ViaCEP no backend quando disponível.

## Testes executados

- `python3 -m py_compile app.py`
- `node -c static/js/main.js`
- Teste via Flask test client para validar:
  - campo tipo de cliente obrigatório;
  - bloqueio de tipo de cliente inválido;
  - bloqueio de CEP estruturalmente inválido;
  - envio válido com campo “Situação do cliente” presente no corpo do e-mail.

## Observação

O arquivo `.env` não foi aberto nem incluído no pacote final.
