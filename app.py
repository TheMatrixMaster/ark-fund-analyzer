from flask import Flask
from flask import (
    url_for,
    request,
    redirect,
    render_template,
)

import pandas
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/ARK.db'
db = SQLAlchemy(app)

@app.route('/', defaults={'update': 'No updates'})
@app.route('/<update>')
def index(update):
    data = db.session.query(ARK).group_by(ARK.date, ARK.fund).all()
    funds = list(set([ark.fund for ark in data]))

    mixed = [
        {"fund": val.fund, "date": val.date, "timestamp": val.uploaded_at}
        for val in data
    ]

    final = [{
        "fund": fund,
        "data": [val for val in mixed if val['fund'] == fund]
    } for fund in funds]

    final.append({"fund": 'All funds', "data": mixed})

    return render_template('input.html', update=update, data=final)


@app.route('/delete_data', defaults={'fund': 'All funds'})
@app.route('/delete_data/<fund>', methods=['GET'])
def delete_data(fund):
    if fund == 'All funds':
        db.drop_all()
        db.create_all()
    else:
        stmt = ARK.__table__.delete().where(ARK.fund == fund)
        db.engine.execute(stmt)

    return redirect(url_for('index', update='Data was successfully deleted'))


@app.route('/input', methods=['POST'])
def manage_data():
    uploaded_file = request.files['file']
    df = pandas.read_csv(uploaded_file, header=0, index_col="date", parse_dates=True)

    df.index = pandas.to_datetime(df.index, format="%m/%d/%Y", errors='coerce')
    df = df.dropna()

    df['weighted_avg_price'] = df['market value($)'] / df['shares']

    for date, row in df.iterrows():
        check = ARK.query.filter_by(
            date=date,
            fund=str(row['fund']),
            cusIp=str(row['cusip'])
        ).first()

        if check is not None:
            continue

        try:
            data = ARK(
                date=date,
                cusIp=str(row['cusip']),
                fund=str(row['fund']),
                ticker=str(row['ticker']),
                company=str(row['company']),
                marketValue=float(row['market value($)']),
                weight=float(row['weight(%)']),
                shares=int(row['shares']),
                weighted_avg_price=round(float(row['market value($)']) / int(row['shares']))
            )

            db.session.add(data)
            db.session.commit()
        except ValueError as error:
            print(date, error)

    return redirect(url_for('index', update='Data was successfully saved!'))


@app.route('/generate_report', defaults={'fund': 'All funds'})
@app.route('/generate_report/<fund>', methods=['GET'])
def gen_report(fund):
    if fund == 'All funds':
        data = ARK.query.all()
    else:
        data = ARK.query.filter_by(fund=fund).all()

    stocks = list(set([d.ticker for d in data]))

    metrics = [
        {"name": 'Market Value', "metric": "marketValue"},
        {"name": "Shares", "metric": "shares"},
        {"name": "Weight", "metric": "weight"},
        {"name": "Weighted Average Price", "metric": "weighted_avg_price"}
    ]

    timestamps = [d.date for d in data]
    start = min(timestamps)
    end = max(timestamps)

    range_ = [d.strftime("%d/%m/%Y") for d
              in pandas.date_range(start, end, freq='d')]

    final = [
        {
            "id": m["metric"],
            "name": m["name"],
            "type": "line",
            "labels": range_,
            "data": [{
                "label": stock,
                "data": [{
                    "x": dp.date.strftime("%d/%m/%Y"),
                    "y": dp.__dict__[m["metric"]],
                } for dp in data if dp.ticker == stock]
            } for stock in stocks]
        }
        for m in metrics
    ]

    return render_template('report.html', fund=fund, data=final)


class ARK(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cusIp = db.Column(db.String(40), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    fund = db.Column(db.String(10), nullable=False)
    company = db.Column(db.String(100))
    ticker = db.Column(db.String(5), nullable=False)

    marketValue = db.Column(db.Float)
    shares = db.Column(db.Integer)
    weight = db.Column(db.Float)
    weighted_avg_price = db.Column(db.Float)

    uploaded_at = db.Column(db.DateTime(timezone=True),
                            nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return '<%r, shares %r>' % (self.ticker, self.shares)


if __name__ == '__main__':
    app.run(debug=True)
