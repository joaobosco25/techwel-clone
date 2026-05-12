# TechWel — Entrega técnica

## O que foi preparado

- Backend Flask com rota `/api/formulario` para envio real dos formulários por e-mail.
- Remoção da dependência PostgreSQL/psycopg.
- Envio SMTP com dados sensíveis apenas via variáveis de ambiente.
- Resposta automática ao cliente quando o formulário tem e-mail válido.
- Cópia oculta configurável.
- Anexo XLSX gerado automaticamente com os dados do formulário, sem aceitar upload de arquivo do visitante.
- CPF/CNPJ mascarado no corpo do e-mail e no XLSX.
- Honeypot anti-spam.
- Rate limit simples por IP.
- reCAPTCHA v3 opcional por variáveis de ambiente, com `RECAPTCHA_ENABLED=false` para testes locais/Railway sem chave real.
- Bloqueio opcional de VPN/proxy/país via Cloudflare ou proxycheck.io.
- Política de Privacidade ampla em `/politica-de-privacidade`.
- Logs técnicos sem gravar dados pessoais do formulário.

## Variáveis obrigatórias

Copie `.env.example` para `.env` localmente ou cadastre as variáveis no painel da hospedagem.

```env
SECRET_KEY=troque_por_uma_chave_grande_e_aleatoria
RECAPTCHA_ENABLED=false
MAIL_SERVER=email-ssl.com.br
MAIL_PORT=465
MAIL_USE_SSL=true
MAIL_USERNAME=seu_email_locaweb@seudominio.com.br
MAIL_PASSWORD=sua_senha_do_email_locaweb
MAIL_DEFAULT_SENDER=seu_email_locaweb@seudominio.com.br
MAIL_TO_EMAIL=joaolundin@hotmail.com
MAIL_BCC=joaoboscodev@hotmail.com
SEND_AUTO_REPLY=true
```

## Configuração SMTP Locaweb

Configuração recomendada para e-mail Locaweb:

- Servidor SMTP: `email-ssl.com.br`
- Porta: `465`
- Segurança: `SSL/TLS`
- Usuário: e-mail completo
- Senha: senha da conta de e-mail

A conta `bosko.dev@hotmail.com` pode funcionar como SMTP se forem usadas as configurações corretas da Microsoft/Outlook, mas para produção com domínio TechWel recomenda-se criar um e-mail profissional no provedor contratado e usar esse e-mail como remetente.

## Rodar localmente no Windows/Git Bash

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse:

```txt
http://127.0.0.1:5000
```

## Testes executados nesta entrega

```bash
python -m compileall .
```

Também foram testadas rotas principais via cliente de teste do Flask:

- `/`
- `/contato`
- `/solicitacao-servicos`
- `/consultar-os`
- `/impressoras`
- `/suprimentos`
- `/politica-de-privacidade`

## Importante sobre FTP/FileZilla e Flask

Este projeto é uma aplicação Flask. Apenas enviar arquivos por FTP não garante que a aplicação rode, porque Flask precisa de um servidor Python/WSGI executando o `app.py`.

Antes de migrar para Localweb via FTP, confirme no plano contratado se existe suporte a aplicação Python/Flask/WSGI. Caso o plano seja somente hospedagem estática/PHP via FTP, as opções corretas são:

1. manter no Railway/Render;
2. contratar VPS/Cloud com Python;
3. converter o backend dos formulários para PHP;
4. usar serviço externo de formulário/e-mail.

## Deploy no Railway

No Railway, cadastre as variáveis do `.env.example` em Variables e mantenha:

```txt
Procfile: web: gunicorn app:app
```

### Variáveis recomendadas para teste no Railway com Hotmail/Outlook

```env
SECRET_KEY=troque_por_uma_chave_grande_e_aleatoria
FLASK_DEBUG=false
SMTP_DEBUG_RESPONSE=true
COMPANY_NAME=TechWel
MAIL_SUBJECT_PREFIX=Nova solicitação pelo site Techwel
WHATSAPP_NUMBER=5532984560451
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_SSL=false
MAIL_USE_TLS=true
MAIL_USERNAME=bosko.dev@hotmail.com
MAIL_PASSWORD=SUA_SENHA_DE_APLICATIVO_MICROSOFT
MAIL_DEFAULT_SENDER=TechWel <bosko.dev@hotmail.com>
MAIL_TO_EMAIL=bosko.dev@hotmail.com
MAIL_BCC_EMAIL=joaoboscodev@hotmail.com
SEND_AUTO_REPLY=true
RECAPTCHA_ENABLED=false
BLOCK_NON_BR_IPS=false
BLOCK_PROXY_VPN=false
RATE_LIMIT_WINDOW_SECONDS=3600
RATE_LIMIT_MAX_REQUESTS=20
```

Depois que o SMTP real estiver funcionando, altere `SMTP_DEBUG_RESPONSE=false`. Quando configurar o Google reCAPTCHA para o domínio real, altere `RECAPTCHA_ENABLED=true` e preencha `RECAPTCHA_SITE_KEY` e `RECAPTCHA_SECRET_KEY`.

## Checklist antes de entregar ao cliente

- [ ] Criar e-mail profissional do domínio.
- [ ] Configurar SMTP real.
- [ ] Configurar `SECRET_KEY` forte.
- [ ] Configurar `RECAPTCHA_SITE_KEY` e `RECAPTCHA_SECRET_KEY`, se quiser reCAPTCHA obrigatório.
- [ ] Testar envio real do formulário de solicitação.
- [ ] Testar newsletter.
- [ ] Confirmar recebimento no e-mail do dono.
- [ ] Confirmar resposta automática ao cliente.
- [ ] Confirmar que anexos não são aceitos.
- [ ] Confirmar política de privacidade no rodapé.
- [ ] Confirmar que `.env` real não foi enviado no ZIP.
- [ ] Confirmar que logs não registram dados pessoais do formulário.

## Limitações conscientes

- Bloqueio real de VPN/proxy/país depende de serviço externo, WAF ou Cloudflare. O código já está preparado para `CF-IPCountry` e `PROXYCHECK_API_KEY`.
- Rate limit em memória funciona para instância única. Para produção com múltiplas instâncias, use Redis, Cloudflare/WAF ou recurso equivalente.
- O site não possui formulários visuais de “Trabalhe conosco” ou “Orçamento” separados no ZIP original. Os botões de orçamento existentes levam para contato/solicitação.
