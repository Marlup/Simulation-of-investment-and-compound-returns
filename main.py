import json

from bokeh.plotting import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, Select
from bokeh.models.tools import HoverTool, Span
from bokeh.plotting import figure
import numpy as np

from src.compound.compound import run_simulation

# Valores iniciales
initial_params = dict(
    principal=10000,
    annual_roi=0.05,
    investment_duration=40,
    yield_frequency=12,
    annual_contribution=1200,
    inc_contribution_rate=0.02,
    inflation_rate=0.02,
    monthly_retirement_income=500,
    retirement_at=30,
    tax="spain"
)

# Primer resultado
initial_balances, initial_earnings, _, _ = run_simulation(**initial_params)

source_earnings = ColumnDataSource(data=dict(
    yield_term=np.arange(len(initial_earnings)),
    earning=initial_earnings
))

source_balances = ColumnDataSource(data=dict(
    month=np.arange(len(initial_balances)),
    year=np.arange(len(initial_balances)) // 12,
    balance=initial_balances
))

# Gráficas
plot_e = figure(title="Earnings Over Time", height=285, width=800, x_axis_label="Yield Term", y_axis_label="Earning (€)")
plot_e.line(x='yield_term', y='earning', source=source_earnings, line_width=2, color="green")

plot_b = figure(title="Balance Over Time", height=285, width=800, x_axis_label="Month", y_axis_label="Balance (€)")
plot_b.line(x='month', y='balance', source=source_balances, line_width=2, color="navy")

# Sliders
s_principal = Slider(start=0, end=100_000, value=initial_params["principal"], step=1000, title="Initial Amount (€)")
s_roi = Slider(start=0.0, end=0.15, value=initial_params["annual_roi"], step=0.005, title="Annual ROI")
s_duration = Slider(start=1, end=60, value=initial_params["investment_duration"], step=1, title="Investment Duration (Years)")
s_frequency = Slider(start=1, end=12, value=initial_params["yield_frequency"], step=1, title="Payment Frequency (Months)")
s_contribution = Slider(start=0, end=50_000, value=initial_params["annual_contribution"], step=500, title="Annual Contribution (€)")
s_inc_contribution = Slider(start=0.0, end=1.0, value=initial_params["inc_contribution_rate"], step=0.01, title="Increment Contribution Rate")
s_inflation = Slider(start=0.0, end=1.0, value=initial_params["inflation_rate"], step=0.01, title="Inflation Rate")
s_retirement_income = Slider(start=0, end=5000, value=initial_params["monthly_retirement_income"], step=100, title="Monthly Retirement Income (€)")
s_retirement_at = Slider(start=0, end=60, value=initial_params["retirement_at"], step=1, title="Retirement At (Years)")
select_tax = Select(title="Tax (Country or Fixed Rate)", value="spain", options=["spain", "france", "germany", "italy", "portugal", "belgium", "netherlands", 
    "sweden", "norway", "denmark", "finland", "ireland", "greece", "switzerland", 
    "austria", "poland", "czech_republic", "hungary", "romania", "bulgaria", 
    "croatia", "slovakia", "slovenia", "estonia", "latvia", "lithuania", 
    "cyprus", "luxembourg", "malta", "0.15", "0.25", "0.30"])

# Callback
def update(attr, old, new):
    try:
        new_tax = float(select_tax.value) if select_tax.value.replace('.', '', 1).isdigit() else select_tax.value
        new_params = dict(
            principal=s_principal.value,
            annual_roi=s_roi.value,
            investment_duration=s_duration.value,
            yield_frequency=s_frequency.value,
            annual_contribution=s_contribution.value,
            inc_contribution_rate=s_inc_contribution.value,
            inflation_rate=s_inflation.value,
            monthly_retirement_income=s_retirement_income.value,
            retirement_at=s_retirement_at.value,
            tax=new_tax
        )
        balances, gross_earnings, net_earnings, tax_from_earnings = run_simulation(**new_params)
        with open("./static/sim_params.json", "w") as sim_params:
            json.dump(new_params, sim_params)

        source_earnings.data = dict(
            yield_term=np.arange(len(net_earnings)),
            earning=net_earnings
        )
        source_balances.data = dict(
            month=np.arange(len(balances)),
            year=np.arange(len(balances)) // 12,
            balance=balances
        )
    except Exception as e:
        print("Simulation error:", e)

# Asignar callback a todos los widgets
for widget in [s_principal, s_roi, s_duration, s_frequency, s_contribution,
               s_inc_contribution, s_inflation, s_retirement_income,
               s_retirement_at, select_tax]:
    widget.on_change('value', update)

# Layout
controls = column(s_principal, s_roi, s_duration, s_frequency, s_contribution,
                  s_inc_contribution, s_inflation, s_retirement_income,
                  s_retirement_at, select_tax)

layout = row(controls, column(plot_e, plot_b))
curdoc().add_root(layout)
curdoc().title = "Compound Return Simulator"
