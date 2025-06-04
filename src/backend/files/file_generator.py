import os
import json
from bokeh.embed import server_document
from flask import (
    Flask,
    render_template,
    send_from_directory,
    redirect,
    url_for,
    request,
    send_file
)

from src.compound.compound import run_simulation 

app = Flask(__name__)

@app.route("/")
def index():
    bokeh_script = server_document("http://localhost:5006/")
    return render_template("index.html", bokeh_script=bokeh_script)

@app.route("/download")
def download():
    with open("./static/sim_params.json", "r") as sim_params:
        params = json.load(sim_params)
    
    if not params:
        return "No parameters found", 400
    
    balances, gross_earnings, net_earnings, tax_from_earnings = run_simulation(**params)

    download_type = request.args.get("file")

    if download_type == "balance":
        data = balances
    elif download_type == "gross_earning":
        data = gross_earnings
    elif download_type == "net_earning":
        data = net_earnings
    elif download_type == "tax_earning":
        data = tax_from_earnings

    filename = f"sim_{download_type}.txt"
    file_path = os.path.join("static", filename)
    with open(file_path, "w") as f:
        f.writelines(f"{item}\n" for item in data)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename  # Optional: sets the name shown in the download dialog
        )

if __name__ == "__main__":
    app.run(debug=True)
