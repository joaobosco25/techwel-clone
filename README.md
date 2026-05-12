# TechWel - Flask + envio de formulários por e-mail

Projeto Flask preservando o frontend existente e adicionando backend para envio dos formulários por SMTP, sem banco de dados dedicado.

Consulte `README_ENTREGA.md` para configuração completa, Localweb, Railway, SMTP, LGPD e checklist de entrega.

## Rodar localmente

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Acesse: http://127.0.0.1:5000
