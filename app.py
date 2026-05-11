from flask import Flask, render_template

app = Flask(__name__)


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


@app.route("/impressoras")
def impressoras():
    return render_template("impressoras.html")


@app.route("/suprimentos")
def suprimentos():
    return render_template("suprimentos.html")


if __name__ == "__main__":
    app.run(debug=True)
