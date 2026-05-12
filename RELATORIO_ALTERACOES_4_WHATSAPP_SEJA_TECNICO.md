# Relatório de Alterações 4 - WhatsApp flutuante e página Seja um técnico

## Alterações realizadas

1. Botão flutuante de WhatsApp
- Adicionado botão fixo no canto inferior da tela em todas as páginas do site.
- Botão usa o número configurado em `WHATSAPP_NUMBER`, sem expor credenciais.
- Incluído ícone SVG do WhatsApp.
- Layout responsivo: no celular o botão fica compacto, mostrando apenas o ícone.
- Link abre em nova aba com mensagem pronta para atendimento.

2. Nova página “Seja um técnico”
- Criada rota `/seja-um-tecnico`.
- Página adicionada à navbar de todas as páginas.
- Formulário criado com os campos:
  - Nome completo
  - CEP
  - Cidade
  - Estado
  - Endereço
- CEP com máscara e consulta automática via ViaCEP no frontend.
- Cidade, Estado e Endereço são preenchidos automaticamente quando possível.
- Validação do CEP mantida também no backend.
- Consentimento LGPD obrigatório.

3. Envio para administrador
- O formulário usa o fluxo SMTP já existente.
- Os dados são enviados para o e-mail administrativo configurado em `MAIL_TO_EMAIL`.
- Para o formulário “Seja um técnico”, o envio não usa BCC, respeitando a regra de acesso apenas pelo administrador.
- XLSX automático atualizado com os campos do formulário.

## Arquivos alterados
- `app.py`
- `static/js/main.js`
- `static/css/style.css`
- `templates/*.html`
- `templates/seja-um-tecnico.html`

## Testes realizados
- Importação/compilação do `app.py` sem erro.
- GET `/seja-um-tecnico` retornando 200.
- POST `/api/formulario` com `form_type=seja_tecnico` retornando sucesso.
- Verificado que `include_bcc=False` no formulário de técnico.
- POST de solicitação de serviços mantido funcionando.
