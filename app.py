import csv
import io
import json
import logging
import os
import re
import smtplib
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from openpyxl import Workbook

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "techwel_app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "troque_essa_chave_em_producao")
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024  # sem anexos; evita abuso de payload

WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "5532984560451")
COMPANY_NAME = os.getenv("COMPANY_NAME", "TechWel")
MAIL_SUBJECT_PREFIX = os.getenv("MAIL_SUBJECT_PREFIX", "Nova solicitação pelo site Techwel")
FORM_RECIPIENT = os.getenv("MAIL_TO_EMAIL", "joaolundin@hotmail.com")
MAIL_BCC = os.getenv("MAIL_BCC") or os.getenv("MAIL_BCC_EMAIL", "joaoboscodev@hotmail.com")

# Rate limit simples em memória. Em produção multi-instância, use Redis/WAF.
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "5"))
_RATE_BUCKET: Dict[str, List[float]] = {}

FIELD_LABELS = {
    "form_type": "Tipo do formulário",
    "cep": "CEP",
    "rua": "Rua",
    "numero": "Número",
    "nome_completo": "Nome completo",
    "email": "E-mail",
    "tipo_cliente": "Situação do cliente",
    "descricao": "Descrição do problema",
    "cidade": "Cidade",
    "estado": "Estado",
    "endereco": "Endereço",
    "seja_tecnico": "Seja um técnico / Trabalhe conosco",
    "solicitacao_servicos": "Solicitação de serviços",
    "newsletter": "Newsletter",
    "consulta_os": "Consulta de OS",
    "consulta": "Consulta",
    "origem": "Origem",
}

FORM_FIELD_ORDER = {
    "solicitacao_servicos": ["cep", "rua", "numero", "nome_completo", "email", "tipo_cliente", "descricao", "form_type", "origem"],
    "newsletter": ["email", "form_type", "origem"],
    "consulta_os": ["consulta", "form_type", "origem"],
    "seja_tecnico": ["nome_completo", "cep", "cidade", "estado", "endereco", "form_type", "origem"],
}

REQUIRED_FIELDS = {
    "solicitacao_servicos": ["cep", "rua", "numero", "nome_completo", "email", "tipo_cliente", "descricao", "lgpd_consent"],
    "newsletter": ["email", "lgpd_consent"],
    "consulta_os": ["consulta"],
    "seja_tecnico": ["nome_completo", "cep", "cidade", "estado", "endereco", "lgpd_consent"],
}

LINK_REGEX = re.compile(r"(https?://|www\.|\.com\b|\.net\b|\.org\b|\.br\b)", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CEP_REGEX = re.compile(r"^\d{5}-?\d{3}$")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


@app.context_processor
def inject_public_settings():
    return {
        "recaptcha_site_key": os.getenv("RECAPTCHA_SITE_KEY", ""),
        "whatsapp_link": make_whatsapp_link("Olá, preciso de atendimento da TechWel pelo site."),
    }


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def normalize_cep(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 8:
        return sanitize(value, 20)
    return f"{digits[:5]}-{digits[5:]}"


def is_valid_cep(value: str) -> bool:
    cep = re.sub(r"\D", "", value or "")
    if len(cep) != 8 or len(set(cep)) == 1:
        return False

    # Validação real via ViaCEP. Se o serviço estiver indisponível, mantém validação estrutural
    # para não derrubar o formulário por falha de terceiros.
    if not env_bool("VALIDATE_CEP_ONLINE", True):
        return True

    try:
        with urllib.request.urlopen(f"https://viacep.com.br/ws/{cep}/json/", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return not payload.get("erro")
    except Exception as exc:
        logging.warning("cep_validation_unavailable ip=%s error=%s", client_ip(), exc.__class__.__name__)
        return True


def sanitize(value: str, limit: int = 1000) -> str:
    value = (value or "").replace("\x00", "").strip()
    return value[:limit]


def collect_form_data() -> Dict[str, str]:
    ignored = {"website", "g-recaptcha-response", "recaptcha_token", "lgpd_consent"}
    data = {}
    for key, value in request.form.items():
        if key in ignored:
            continue
        data[key] = sanitize(value)
    data["origem"] = request.headers.get("Referer", request.path)
    return data


def validate_payload(form_type: str, data: Dict[str, str]) -> List[str]:
    errors: List[str] = []
    required = REQUIRED_FIELDS.get(form_type, [])

    for field in required:
        if field == "lgpd_consent":
            if request.form.get(field) not in {"1", "on", "true", "sim"}:
                errors.append("Confirme o consentimento de privacidade antes de enviar.")
            continue
        if not sanitize(request.form.get(field, "")):
            errors.append(f"Preencha o campo obrigatório: {FIELD_LABELS.get(field, field)}.")

    email = sanitize(request.form.get("email", ""))
    if email and not EMAIL_REGEX.match(email):
        errors.append("Informe um e-mail válido.")

    if form_type in {"solicitacao_servicos", "seja_tecnico"}:
        cep = sanitize(request.form.get("cep", ""), 20)
        if cep and (not CEP_REGEX.match(cep) or not is_valid_cep(cep)):
            errors.append("Informe um CEP válido.")

    if form_type == "solicitacao_servicos":
        tipo_cliente = sanitize(request.form.get("tipo_cliente", ""), 40)
        if tipo_cliente and tipo_cliente not in {"Cliente com contrato", "Cliente sem contrato"}:
            errors.append("Selecione uma situação de cliente válida.")

    if form_type == "seja_tecnico":
        estado = sanitize(request.form.get("estado", ""), 2).upper()
        if estado and not re.match(r"^[A-Z]{2}$", estado):
            errors.append("Informe a UF do estado com 2 letras. Exemplo: MG.")

    if request.files:
        errors.append("Este formulário não aceita anexos. Envie a solicitação sem arquivos.")

    for key, value in data.items():
        if key in {"descricao", "consulta", "nome_completo", "rua", "endereco", "cidade"} and LINK_REGEX.search(value):
            errors.append("Remova links dos campos do formulário para evitar bloqueio anti-spam.")
            break

    if request.form.get("website"):
        errors.append("Envio bloqueado pela proteção anti-spam.")

    return errors


def rate_limited(ip: str) -> bool:
    now = time.time()
    bucket = _RATE_BUCKET.setdefault(ip, [])
    bucket[:] = [timestamp for timestamp in bucket if now - timestamp < RATE_LIMIT_WINDOW_SECONDS]
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return True
    bucket.append(now)
    return False


def verify_recaptcha() -> bool:
    # Permite desligar o reCAPTCHA em ambiente local/teste via .env.
    # Em produção, deixe RECAPTCHA_ENABLED=true e cadastre chaves reais do Google.
    if not env_bool("RECAPTCHA_ENABLED", True):
        return True

    secret = os.getenv("RECAPTCHA_SECRET_KEY", "").strip()
    site_key = os.getenv("RECAPTCHA_SITE_KEY", "").strip()

    # Se as chaves não foram configuradas, não bloqueia o formulário.
    # Isso evita erro 400 em testes locais/Railway antes de cadastrar o domínio no Google.
    if not secret or not site_key or "COLOCAREMOS_DEPOIS" in secret.upper():
        return True

    token = request.form.get("recaptcha_token") or request.form.get("g-recaptcha-response")
    if not token:
        return False

    payload = urllib.parse.urlencode({
        "secret": secret,
        "response": token,
        "remoteip": client_ip(),
    }).encode()

    try:
        req = urllib.request.Request("https://www.google.com/recaptcha/api/siteverify", data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=6) as response:
            result = json.loads(response.read().decode("utf-8"))
        minimum_score = float(os.getenv("RECAPTCHA_MIN_SCORE", "0.5"))
        if result.get("success") is not True:
            return False
        if "score" in result and float(result.get("score", 0)) < minimum_score:
            return False
        return True
    except Exception as exc:  # não registra token nem dados pessoais
        logging.warning("recaptcha_error ip=%s error=%s", client_ip(), exc.__class__.__name__)
        return False

def verify_geo_proxy_rules() -> Tuple[bool, str]:
    """Bloqueio opcional. Funciona melhor com Cloudflare ou proxycheck.io configurado."""
    ip = client_ip()
    block_non_br = env_bool("BLOCK_NON_BR_IPS", True)
    block_proxy = env_bool("BLOCK_PROXY_VPN", True)

    cf_country = request.headers.get("CF-IPCountry", "").upper()
    if block_non_br and cf_country and cf_country != "BR":
        return False, "Acesso permitido apenas para o Brasil."

    api_key = os.getenv("PROXYCHECK_API_KEY", "").strip()
    if api_key and (block_non_br or block_proxy):
        try:
            url = f"https://proxycheck.io/v2/{urllib.parse.quote(ip)}?vpn=1&asn=1&key={urllib.parse.quote(api_key)}"
            with urllib.request.urlopen(url, timeout=6) as response:
                payload = json.loads(response.read().decode("utf-8"))
            ip_info = payload.get(ip, {})
            if block_proxy and str(ip_info.get("proxy", "no")).lower() == "yes":
                return False, "Envio bloqueado por uso de proxy/VPN."
            if block_non_br and str(ip_info.get("isocode", "BR")).upper() != "BR":
                return False, "Acesso permitido apenas para o Brasil."
        except Exception as exc:
            logging.warning("proxycheck_error ip=%s error=%s", ip, exc.__class__.__name__)
            # Falha do serviço externo não derruba o formulário.
            return True, ""

    return True, ""


def iter_ordered_fields(data: Dict[str, str]):
    used = set()
    form_type = data.get("form_type", "")
    for key in FORM_FIELD_ORDER.get(form_type, []):
        if key in data:
            used.add(key)
            value = normalize_cep(data[key]) if key == "cep" else data[key]
            yield key, value
    for key, value in data.items():
        if key not in used:
            yield key, normalize_cep(value) if key == "cep" else value


def create_xlsx_attachment(data: Dict[str, str]) -> bytes:
    wb = Workbook()
    ws = wb.active
    sheet_title = re.sub(r"[\\/*?:\[\]]", "-", FIELD_LABELS.get(data.get("form_type", ""), "Formulario"))[:31]
    ws.title = sheet_title or "Formulario"
    ws.append(["Campo", "Valor"])

    for key, value in iter_ordered_fields(data):
        label = FIELD_LABELS.get(key, key.replace("_", " ").title())
        ws.append([label, value])

    ws.append(["Data de recebimento", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")])

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def format_plain_email(data: Dict[str, str]) -> str:
    lines = [
        f"{MAIL_SUBJECT_PREFIX}",
        "",
        "Dados recebidos pelo site:",
        "",
    ]
    for key, value in iter_ordered_fields(data):
        label = FIELD_LABELS.get(key, key.replace("_", " ").title())
        lines.append(f"{label}: {value or '-'}")
    lines.extend([
        "",
        "Observação LGPD: os dados são usados exclusivamente para atendimento da solicitação e não são gravados em banco de dados dedicado.",
    ])
    return "\n".join(lines)


def mail_sender_header() -> str:
    raw_sender = os.getenv("MAIL_DEFAULT_SENDER", "").strip() or os.getenv("MAIL_USERNAME", "").strip()
    parsed_name, parsed_email = parseaddr(raw_sender)
    sender_email = parsed_email or raw_sender
    sender_name = parsed_name or COMPANY_NAME
    return formataddr((sender_name, sender_email))


def mail_bcc_list() -> str:
    return ", ".join([email.strip() for email in (MAIL_BCC or "").split(",") if email.strip()])


def smtp_debug_enabled() -> bool:
    return env_bool("SMTP_DEBUG_RESPONSE", False) or env_bool("FLASK_DEBUG", False)


def smtp_configured() -> bool:
    return all(os.getenv(name) for name in ["MAIL_SERVER", "MAIL_PORT", "MAIL_USERNAME", "MAIL_PASSWORD"])


def send_mail(subject: str, body: str, to_email: str, reply_to: str = "", attachment: bytes | None = None, include_bcc: bool = True) -> None:
    if not smtp_configured():
        raise RuntimeError("SMTP não configurado. Preencha o .env.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_sender_header()
    msg["To"] = to_email
    bcc = mail_bcc_list() if include_bcc else ""
    if bcc:
        msg["Bcc"] = bcc
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    if attachment:
        msg.add_attachment(
            attachment,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"techwel-formulario-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx",
        )

    server = os.getenv("MAIL_SERVER", "email-ssl.com.br")
    port = int(os.getenv("MAIL_PORT", "465"))
    username = os.getenv("MAIL_USERNAME", "")
    password = os.getenv("MAIL_PASSWORD", "")
    use_ssl = env_bool("MAIL_USE_SSL", True)
    use_tls = env_bool("MAIL_USE_TLS", False)

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(server, port, context=context, timeout=20) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(server, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(username, password)
            smtp.send_message(msg)


def send_auto_reply(data: Dict[str, str]) -> None:
    email = data.get("email", "")
    if not email or not EMAIL_REGEX.match(email):
        return
    subject = "Recebemos sua solicitação - TechWel"
    body = (
        "Olá!\n\n"
        "Recebemos sua solicitação pelo site da TechWel. Nossa equipe analisará as informações enviadas "
        "e retornará em breve pelos canais informados.\n\n"
        "Se precisar de atendimento imediato, fale conosco pelo WhatsApp: (32) 98456-0451.\n\n"
        "Atenciosamente,\nTechWel"
    )
    send_mail(subject, body, email)


def make_whatsapp_link(text: str) -> str:
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(text)}"


def log_submission(form_type: str, status: str) -> None:
    logging.info(
        "form_submission form_type=%s status=%s ip=%s user_agent=%s",
        form_type,
        status,
        client_ip(),
        sanitize(request.headers.get("User-Agent", ""), 180),
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/contato")
def contato():
    return render_template("contato.html")


@app.route("/solicitacao-servicos")
def solicitacao_servicos():
    return render_template("solicitacao-servicos.html")


@app.route("/consultar-os")
def consultar_os():
    return render_template("consultar-os.html")


@app.route("/seja-um-tecnico")
def seja_um_tecnico():
    return render_template("seja-um-tecnico.html")


@app.route("/impressoras")
def impressoras():
    return render_template("impressoras.html")


@app.route("/suprimentos")
def suprimentos():
    return render_template("suprimentos.html")


@app.route("/politica-de-privacidade")
def politica_privacidade():
    return render_template("politica-de-privacidade.html")


@app.route("/api/formulario", methods=["POST"])
def api_formulario():
    form_type = sanitize(request.form.get("form_type", "solicitacao_servicos"), 80)
    ip = client_ip()

    ok_geo, geo_message = verify_geo_proxy_rules()
    if not ok_geo:
        log_submission(form_type, "blocked_geo_proxy")
        return jsonify({"ok": False, "message": geo_message, "whatsapp": make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel.")}), 403

    data = collect_form_data()
    data["form_type"] = form_type
    errors = validate_payload(form_type, data)
    if errors:
        log_submission(form_type, "validation_error")
        return jsonify({"ok": False, "message": " ".join(errors), "whatsapp": make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel.")}), 400

    if not verify_recaptcha():
        log_submission(form_type, "recaptcha_error")
        return jsonify({"ok": False, "message": "Não foi possível validar o reCAPTCHA. Tente novamente.", "whatsapp": make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel.")}), 400

    if rate_limited(ip):
        log_submission(form_type, "rate_limited")
        return jsonify({"ok": False, "message": "Muitos envios em pouco tempo. Aguarde e tente novamente.", "whatsapp": make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel.")}), 429

    try:
        body = format_plain_email(data)
        xlsx = create_xlsx_attachment(data)
        send_mail(
            subject=f"{MAIL_SUBJECT_PREFIX} - {FIELD_LABELS.get(form_type, form_type)}",
            body=body,
            to_email=FORM_RECIPIENT,
            reply_to=data.get("email", ""),
            attachment=xlsx,
            include_bcc=(form_type != "seja_tecnico"),
        )
        if env_bool("SEND_AUTO_REPLY", True):
            send_auto_reply(data)
        log_submission(form_type, "sent")
        return jsonify({"ok": True, "message": "Solicitação enviada com sucesso. A TechWel retornará em breve."})
    except Exception as exc:
        log_submission(form_type, "smtp_error")
        logging.exception("smtp_error form_type=%s ip=%s error=%s", form_type, ip, exc.__class__.__name__)
        message = "Não foi possível enviar agora. Tente novamente ou fale conosco pelo WhatsApp."
        if smtp_debug_enabled():
            message = f"Erro técnico de envio: {exc.__class__.__name__}. Verifique SMTP, usuário, senha de aplicativo, TLS/SSL e remetente."
        return jsonify({
            "ok": False,
            "message": message,
            "whatsapp": make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel."),
        }), 500


@app.route("/formulario", methods=["POST"])
def formulario_post_fallback():
    """Fallback simples para POST tradicional sem JavaScript."""
    result = api_formulario()
    status_code = result[1] if isinstance(result, tuple) else getattr(result, "status_code", 200)
    if status_code == 200:
        return redirect(url_for("solicitacao_servicos", enviado="1"))
    return redirect(make_whatsapp_link("Não consegui enviar o formulário pelo site da TechWel."))


if __name__ == "__main__":
    debug = env_bool("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)
