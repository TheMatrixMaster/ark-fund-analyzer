from flask import Flask
from flask import (
    request,
    render_template,
)

import pandas

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('input.html')


@app.route('/', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    print(uploaded_file.filename)
    return "I received the file"


@app.route('/report')
def show_report():
    return 'Report for several stocks'


if __name__ == '__main__':
    app.run(debug=True)
