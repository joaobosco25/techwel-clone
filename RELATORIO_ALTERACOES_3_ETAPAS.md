# Alteração 3 — Exibição progressiva do formulário

## O que foi ajustado

- As etapas do formulário de Solicitação de Serviços agora aparecem uma por vez.
- A próxima etapa só é exibida após validação dos dados da etapa atual.
- Etapas futuras ficam bloqueadas até o usuário avançar corretamente.
- O botão Voltar continua permitindo retornar à etapa anterior.
- Ao enviar com sucesso, o formulário volta para a primeira etapa.
- Foi adicionado CSS explícito para impedir que etapas ocultas apareçam por conflito de `display`.

## Arquivos alterados

- `templates/solicitacao-servicos.html` — mantida estrutura em etapas.
- `static/js/main.js` — controle progressivo das etapas.
- `static/css/style.css` — ocultação segura de etapas inativas.

## Segurança

- `.env` não foi lido nem alterado.
- Fluxo SMTP não foi alterado.
- Backend de e-mail/XLSX não foi alterado nesta etapa.
