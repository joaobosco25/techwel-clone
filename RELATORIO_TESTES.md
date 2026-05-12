# Relatório de testes — TechWel

Data: 12/05/2026

## Problemas encontrados no ZIP anterior

1. `RECAPTCHA_ENABLED=false` não existia no backend. Resultado: mesmo em teste local/Railway, o formulário podia continuar bloqueando por reCAPTCHA.
2. O rate limit era contabilizado antes do envio real. Resultado: várias tentativas inválidas podiam gerar “Muitos envios em pouco tempo”.
3. `MAIL_DEFAULT_SENDER=TechWel <bosko.dev@hotmail.com>` podia gerar cabeçalho de remetente inválido em algumas configurações, porque o código montava o `From` manualmente.
4. O backend aceitava somente `MAIL_BCC`, mas no passo a passo anterior também foi usado `MAIL_BCC_EMAIL`. Agora os dois funcionam.
5. O erro 500 continuava genérico demais. Agora, quando `FLASK_DEBUG=true` ou `SMTP_DEBUG_RESPONSE=true`, a resposta informa a classe do erro técnico para diagnóstico de SMTP.

## Correções aplicadas

- Adicionado suporte a `RECAPTCHA_ENABLED=false`.
- reCAPTCHA fica liberado automaticamente quando as chaves estão vazias ou com placeholder.
- Rate limit movido para depois de validação/reCAPTCHA, evitando bloqueio por tentativas inválidas.
- Remetente agora é formatado com `email.utils.parseaddr/formataddr`.
- `MAIL_BCC` e `MAIL_BCC_EMAIL` são aceitos.
- Logs de erro SMTP agora usam `logging.exception`, registrando stack trace técnico no arquivo de log, sem gravar dados pessoais do formulário.
- `.env.example` atualizado com configuração de teste para Hotmail/Outlook e Localweb.

## Testes executados

### 1. Compilação Python

Comando:

```bash
python -m compileall -q app.py
```

Resultado: aprovado.

### 2. Instalação de dependências em ambiente limpo

Comandos:

```bash
python -m venv /mnt/data/techwel_testvenv
source /mnt/data/techwel_testvenv/bin/activate
pip install -r requirements.txt
```

Resultado: aprovado.

### 3. Teste de rotas Flask

Rotas testadas com `app.test_client()`:

- `/` → 200
- `/contato` → 200
- `/solicitacao-servicos` → 200
- `/consultar-os` → 200
- `/politica-de-privacidade` → 200

Resultado: aprovado.

### 4. Teste de validação do formulário

Foi enviado POST inválido para `/api/formulario`.

Resultado esperado: erro 400.

Resultado obtido: erro 400, sem disparar SMTP e sem erro 500.

### 5. Teste de envio com SMTP simulado

Foi enviado POST válido para `/api/formulario`, com SMTP simulado em memória.

Validações confirmadas:

- retorno HTTP 200;
- `ok=true`;
- e-mail principal gerado para o destinatário;
- resposta automática gerada para o cliente;
- `Reply-To` configurado com o e-mail do cliente;
- remetente `TechWel <bosko.dev@hotmail.com>` formatado corretamente;
- anexo XLSX gerado.

Resultado: aprovado.

## Teste SMTP real

O envio SMTP real não foi executado porque o ZIP não contém senha real, por segurança. No Railway, o teste real depende das variáveis:

```env
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_SSL=false
MAIL_USE_TLS=true
MAIL_USERNAME=bosko.dev@hotmail.com
MAIL_PASSWORD=SENHA_DE_APLICATIVO_DA_MICROSOFT
MAIL_DEFAULT_SENDER=TechWel <bosko.dev@hotmail.com>
MAIL_TO_EMAIL=bosko.dev@hotmail.com
MAIL_BCC_EMAIL=joaoboscodev@hotmail.com
RECAPTCHA_ENABLED=false
SMTP_DEBUG_RESPONSE=true
```

Se ainda aparecer erro 500 com SMTP real, a causa restante estará fora da lógica do formulário e será uma destas:

- senha de aplicativo incorreta;
- SMTP AUTH bloqueado na conta Microsoft;
- autenticação de segurança da Microsoft exigindo nova permissão;
- bloqueio temporário por tentativa suspeita;
- configuração TLS/SSL divergente;
- Railway bloqueando conexão externa temporariamente;
- remetente diferente do usuário autenticado.
