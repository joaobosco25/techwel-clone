# Relatório de Alterações - Solicitação de Serviços

## Alteração solicitada
A página "Solicitação de Serviços" foi convertida para um formulário em 3 etapas/abas:

1. Endereço do atendimento
   - CEP com máscara e validação
   - Rua
   - Número

2. Dados da solicitação
   - Nome completo
   - E-mail
   - Descrição do problema

3. Revisão e envio
   - Resumo dos dados preenchidos
   - Consentimento LGPD
   - Botão de envio

## Backend
O endpoint `/api/formulario` foi ajustado para aceitar os novos campos do formulário:

- `cep`
- `rua`
- `numero`
- `nome_completo`
- `email`
- `descricao`

Os campos antigos da solicitação foram removidos da validação obrigatória:

- CPF/CNPJ
- Empresa
- Celular
- Endereço antigo
- Marca
- Modelo
- Número de série
- Tipo de problema

## Excel enviado por e-mail
O XLSX automático agora segue a mesma estrutura do formulário, na ordem:

1. CEP
2. Rua
3. Número
4. Nome completo
5. E-mail
6. Descrição do problema
7. Tipo do formulário
8. Origem
9. Data de recebimento

## Validação de CEP
Foi adicionada validação de CEP:

- validação estrutural: 8 dígitos no formato `00000-000` ou `00000000`;
- bloqueio de CEPs claramente inválidos, como `11111-111`;
- validação online opcional via ViaCEP no backend;
- preenchimento automático da rua no frontend quando o ViaCEP retorna logradouro.

A validação online pode ser desligada com:

```env
VALIDATE_CEP_ONLINE=false
```

## Testes realizados
Sem abrir o `.env`, foram realizados testes em cópia limpa do projeto:

- compilação Python com `python -m py_compile app.py`;
- renderização da página `/solicitacao-servicos`;
- confirmação de remoção do campo antigo `cpf_cnpj`;
- envio simulado válido para `/api/formulario` com SMTP mockado;
- validação de e-mail de resposta `reply_to`;
- bloqueio de CEP inválido;
- geração do XLSX com campos na mesma ordem do formulário.
