import pandas as pd
from bokeh import plotting as bk
from bokeh.models import Span, HoverTool, ColumnDataSource
import numpy as np
from itertools import product
from collections import deque


DEFAULT_RETIREMENT_YEARS = 30
MONTHS_IN_YEAR = 12
CURRENCY = "€"

INT_TO_TERM_NAME = {
    1: "monthly",
    2: "bi-monthly",
    3: "every-three-months",
    4: "quarterly",
    6: "semi-annual",
    12: "annual"
}

from collections import deque

MONTHS_IN_YEAR = 12

from collections import deque

class CompoundReturnSimulator:
    def __init__(
        self,
        principal,
        annual_roi=0.05,
        yield_frequency=12,
        annual_contribution=100.0,
        inc_contribution_rate=0.0,
        investment_duration=60,
        retirement_at=30,
        monthly_retirement_income=500.0,
        inflation_rate=0.02,
        tax="",
        return_series=False,
        verbose=False,
    ):
        self.principal = principal
        self.annual_roi = annual_roi
        self.yield_frequency = max(1, yield_frequency)
        self.annual_contribution = annual_contribution
        self.inc_contribution_rate = inc_contribution_rate
        self.investment_duration = investment_duration
        self.retirement_at = min(retirement_at, investment_duration)
        self.monthly_retirement_income = monthly_retirement_income
        self.inflation_rate = inflation_rate
        self.tax = tax
        self.return_series = return_series
        self.verbose = verbose

        self.n_yields_per_year = MONTHS_IN_YEAR // self.yield_frequency
        self.periodic_roi = self.annual_roi / self.n_yields_per_year
        self.retirement_start_month = self.retirement_at * MONTHS_IN_YEAR
        self.monthly_contribution = self.annual_contribution / MONTHS_IN_YEAR
        self.monthly_increment = self.inc_contribution_rate / MONTHS_IN_YEAR

        self.current_balance = principal
        self.time_counter = 0
        self.on_retirement = False
        self.earnings_window = deque(maxlen=self.n_yields_per_year)

        self.info = {}
        if self.return_series:
            self._init_series_storage()

    def _init_series_storage(self):
        self.contributions = []
        self.before_retirement_contributions = []
        self.gross_earnings = []
        self.net_earnings = []
        self.inflation_from_earnings = []
        self.tax_from_earnings = []
        self.balances = []

    def simulate(self):
        for year in range(self.investment_duration):
            for month in range(1, MONTHS_IN_YEAR + 1):
                is_yield_period = (month % self.yield_frequency == 0) and self.current_balance > 0

                if is_yield_period:
                    self._apply_yield()

                self._check_retirement()

                self._process_contributions_and_retirement()

                self._apply_inflation_to_balance()

                if not self.on_retirement:
                    self._increment_contribution()

                if self.return_series:
                    self._track_series_data(is_yield_period)

                self.time_counter += 1

            if self.tax:
                self.current_balance -= get_tax_amount(sum(self.earnings_window), 1, self.tax)

        self._finalize_results()
        return self.get_result()

    def _apply_yield(self):
        gross = self.current_balance * self.periodic_roi
        inflation = get_inflation_amount(gross, self.n_yields_per_year, self.inflation_rate)
        net = gross - inflation
        self.earnings_window.append(net)
        self.current_balance += gross
        self.last_gross = gross
        self.last_net = net
        self.last_inflation = inflation

    def _check_retirement(self):
        if not self.on_retirement and self.time_counter >= self.retirement_start_month:
            if self.verbose:
                print(f"Max monthly contribution reached: {self.monthly_contribution}")
            self.on_retirement = True
            self.monthly_contribution = 0.0

    def _process_contributions_and_retirement(self):
        retirement_outflow = self.monthly_retirement_income if self.on_retirement else 0.0
        self.current_balance += self.monthly_contribution - retirement_outflow

    def _apply_inflation_to_balance(self):
        if self.inflation_rate > 0.0:
            self.current_balance -= get_inflation_amount(self.current_balance, MONTHS_IN_YEAR, self.inflation_rate)

    def _increment_contribution(self):
        if self.monthly_increment > 0.0 and self.current_balance > 0.0:
            self.monthly_contribution += get_contribution_inc(self.monthly_contribution, self.monthly_increment)

    def _track_series_data(self, is_yield_period):
        if is_yield_period or self.on_retirement:
            tax_amount = get_tax_amount(self.last_net, self.n_yields_per_year, self.tax)
            self.gross_earnings.append(self.last_gross)
            self.net_earnings.append(self.last_net - tax_amount)
            self.inflation_from_earnings.append(self.last_inflation)
            self.tax_from_earnings.append(tax_amount)

        self.balances.append(self.current_balance)
        self.contributions.append(self.monthly_contribution)

        if self.on_retirement and not self.before_retirement_contributions:
            self.before_retirement_contributions = self.contributions.copy()

    def _finalize_results(self):
        if self.return_series:
            self.info.update({
                "contributions": self.contributions,
                "before_retirement_contributions": self.before_retirement_contributions,
                "gross_earnings": self.gross_earnings,
                "net_earnings": self.net_earnings,
                "balances": self.balances,
                "tax_from_earnings": self.tax_from_earnings,
                "inflation_from_earnings": self.inflation_from_earnings
            })
        if len(self.earnings_window) >= 2:
            self.info["stable_yield"] = self.earnings_window[0] < self.earnings_window[-1]

    def get_result(self):
        return self.current_balance, self.info

def simulate_compound_return(
    principal,
    annual_roi=0.05,
    yield_frequency=12,
    annual_contribution=100.0,
    inc_contribution_rate=0.0,
    investment_duration=60,
    retirement_at=30,
    monthly_retirement_income=500.0,
    inflation_rate=0.02,
    tax_rate="",
    return_series=False,
    check_sustained_yield=True,
    verbose=False
):
    if not isinstance(yield_frequency, int) or yield_frequency < 1:
        print(f"Yield frequency changed from {yield_frequency} to 1")
        yield_frequency = 1

    if investment_duration <= retirement_at:
        print("\nArgument warning: 'investment_duration' must be greater than 'retirement_at'. retirement_at will be ignored\n")
        retirement_at = investment_duration

    n_yields_per_year = MONTHS_IN_YEAR // yield_frequency
    periodic_roi = annual_roi / n_yields_per_year
    retirement_start_month = retirement_at * MONTHS_IN_YEAR
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    monthly_increment = inc_contribution_rate / MONTHS_IN_YEAR

    current_balance = principal
    time_counter = 0
    on_retirement = False
    earnings_window = deque(maxlen=n_yields_per_year)

    info = {}
    if return_series:
        contributions = []
        before_retirement_contributions = []
        gross_earnings = []
        net_earnings = []
        inflation_from_earnings = []
        tax_from_earnings = []
        balances = []

    for year in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            is_yield_period = (month % yield_frequency == 0) and current_balance > 0

            if is_yield_period:
                current_balance, earning_after_inflation = apply_yield(
                    current_balance, periodic_roi, inflation_rate, n_yields_per_year, earnings_window
                )

            on_retirement, monthly_contribution = check_retirement(
                time_counter, retirement_start_month, on_retirement, monthly_contribution, verbose
            )

            current_balance = process_contribution_and_retirement(
                current_balance, monthly_contribution, on_retirement, monthly_retirement_income
            )

            current_balance = adjust_for_inflation(current_balance, inflation_rate)

            if not on_retirement:
                monthly_contribution = increment_contribution(
                    monthly_contribution, monthly_increment, current_balance
                )

            if return_series:
                if is_yield_period or on_retirement:
                    tax_amount = get_tax_amount(earning_after_inflation, n_yields_per_year, tax_rate)
                    net = earning_after_inflation - tax_amount

                    gross_earnings.append(current_balance * periodic_roi)
                    net_earnings.append(net)
                    inflation_from_earnings.append(get_inflation_amount(current_balance * periodic_roi, n_yields_per_year, inflation_rate))
                    tax_from_earnings.append(tax_amount)

                balances.append(current_balance)
                contributions.append(monthly_contribution)

                if on_retirement and not before_retirement_contributions:
                    before_retirement_contributions = contributions.copy()

            time_counter += 1

        if tax_rate:
            current_balance -= get_tax_amount(sum(earnings_window), 1, tax_rate)

    info["stable_yield"] = earnings_window[0] < earnings_window[-1] if check_sustained_yield and len(earnings_window) > 1 else None

    if return_series:
        info.update({
            "contributions": contributions,
            "before_retirement_contributions": before_retirement_contributions,
            "gross_earnings": gross_earnings,
            "net_earnings": net_earnings,
            "balances": balances,
            "tax_from_earnings": tax_from_earnings,
            "inflation_from_earnings": inflation_from_earnings
        })

    return current_balance, info

def apply_yield(balance, roi, inflation_rate, n_yields, earnings_window):
    gross = balance * roi
    inflation = get_inflation_amount(gross, n_yields, inflation_rate)
    net_after_inflation = gross - inflation
    earnings_window.append(net_after_inflation)
    balance += gross
    return balance, net_after_inflation


def check_retirement(counter, retirement_month, on_retirement, contribution, verbose):
    if not on_retirement and counter >= retirement_month:
        if verbose:
            print(f"Max monthly contribution reached: {contribution}")
        return True, 0.0
    return on_retirement, contribution


def process_contribution_and_retirement(balance, contribution, on_retirement, retirement_income):
    outflow = retirement_income if on_retirement else 0.0
    return balance + contribution - outflow


def adjust_for_inflation(balance, inflation_rate):
    return balance - get_inflation_amount(balance, MONTHS_IN_YEAR, inflation_rate)


def increment_contribution(contribution, increment, balance):
    if increment > 0.0 and balance > 0.0:
        return contribution + (increment * contribution)
    return contribution


def get_inflation_amount(amount: float, n_yields: int=1, inflation: float=0.02, years: int=1):
    adjusted_inflation = inflation / n_yields
    if not (0.0 < adjusted_inflation < 1.0):
        adjusted_inflation = 0.02 / n_yields
    return amount * (1 - 1 / (1 + adjusted_inflation) ** years)


def get_tax_amount(earnings, n_yields, tax_rate):
    if isinstance(tax_rate, (int, float)):
        return tax_rate * earnings / n_yields
    elif isinstance(tax_rate, str):
        return _compute_taxes(earnings, n_yields, tax_rate)

def _compute_taxes(earnings: float, n_yields: int, country: str="spain"):
    tax_value = 0.0
    if country == "spain":
        if earnings >= 200_000.0:
            tax_value += 0.19 * 5_999.99
            tax_value += 0.21 * 43_999.99
            tax_value += 0.23 * 149_999.99
            return (tax_value + 0.26 * (earnings - 199_999.99)) / n_yields
        if earnings >= 50_000.0:
            tax_value += 0.19 * 5_999.99
            tax_value += 0.21 * 43_999.99
            return (tax_value + 0.23 * (earnings - 49_999.9)) / n_yields
        if earnings >= 6_000.0:
            tax_value += 0.19 * 5_999.99
            return (tax_value + 0.21 * (earnings - 5_999.99)) / n_yields
        else:
            return 0.19 * earnings / n_yields
    return 0.21 * earnings / n_yields

# Plot earning and contribution evolutions
def plot_scenario_bokeh(earnings, balances, w= 400, h=300):
    plot_e = bk.figure(width=w,
                       height=h,
                       title='Evolution of yields',
                       #tools='hover'
                       )

    ## Earning plot
    source_e = ColumnDataSource(
        data=dict(yield_term=np.arange(len(earnings)),
                  earning=earnings
                  )
    )

    curve_e = plot_e.line(x='yield_term',
                          y='earning',
                          source=source_e)

    # zero-earnings baseline
    hline_e = Span(location=earnings[0],
                   dimension='width',
                   line_color='red',
                   line_width=1,
                   line_dash='dashed')
    plot_e.add_layout(hline_e)

    #plot.renderers.extend([curve, hline])

    # Annotations
    plot_e.xaxis.axis_label = "yield_term"
    plot_e.yaxis.axis_label = "earning (€)"

    # hover tools for earning curve
    hover_e = HoverTool(
        tooltips=[
            ('yield_term',  '@yield_term'),
            ('earning-yield', '€ @earning{%0.2f}'), # use @{ } for field names with spaces
        ],

        formatters={
            '@yield_term': 'printf', # use default 'numeral' formatter for other fields
            '@earning': 'printf',   # use 'printf' formatter for '@{adj close}' field
        },
        # display a tooltip whenever the cursor is vertically in line with a glyph
        mode='vline'
    )
    plot_e.add_tools(hover_e)

    ## Balance plot

    plot_b = bk.figure(width=w,
                       height=h,
                       title='Evolution of balance',
                       #tools='hover'
                      )

    source_b = ColumnDataSource(
        data=dict(month=np.arange(len(balances)),
                  year=np.arange(len(balances)) // 12,
                  balance=balances
                  )

        )
    curve_b = plot_b.line(x='month',
                          y='balance',
                          source=source_b)

    # zero-balance baseline
    hline_b = Span(location=earnings[0],
                   dimension='width',
                   line_color='red',
                   line_width=1,
                   line_dash='dashed')
    plot_b.add_layout(hline_b)
    
    # Annotations
    plot_b.xaxis.axis_label = "month"
    plot_b.yaxis.axis_label = "balance (€)"
    
    # hover tools for balance curve
    hover_b = HoverTool(
        tooltips=[
            ('year', '@year (month @month)'),
            ('balance', '€ @balance{%0.2f}'), # use @{ } for field names with spaces
        ],
        formatters={
            '@month': 'printf', # use default 'numeral' formatter for other fields
            '@balance': 'printf',   # use 'printf' formatter for '@{adj close}' field
        },
        # display a tooltip whenever the cursor is vertically in line with a glyph
        mode='vline'
    )
    plot_b.add_tools(hover_b)

    return plot_e, plot_b

def define_scenario(
    initial_amounts,
    rois,
    investment_durations,
    terms,
    contributions,
    inc_contributions,
    inflation_rates,
    monthly_retirement_incomes,
    retirement_ats=[20],
    tax_rates=[0.25]
):
    accumulated_amount = {}
    combs = product(initial_amounts, 
                    rois,
                    investment_durations,
                    terms,
                    contributions,
                    inc_contributions,
                    inflation_rates,
                    monthly_retirement_incomes,
                    retirement_ats,
                    tax_rates
                   )
    for (i_a, roi, in_d, t, c, i_c, i_r, m_r_i, r_a, t_r) in combs:
        total_amount, info = simulate_compound_return(
          principal=i_a,
          annual_roi=roi,
          yield_frequency=t,
          annual_contribution=c,
          inc_contribution_rate=i_c,
          investment_duration=in_d,
          retirement_at=r_a,
          monthly_retirement_income=m_r_i,
          inflation_rate=i_r,
          tax_rate=t_r,
          return_series=False
        )
        scenario_key = (
          i_a, 
          roi, 
          in_d,
          t, 
          c, 
          i_c,
          i_r, 
          m_r_i,
          r_a,
          t_r,
          info["stable_yield"],
        )

        accumulated_amount[scenario_key] = total_amount

    return accumulated_amount

def build_dataframe(data):
    index = pd.MultiIndex.from_tuples(list(data.keys()))
    df = pd.DataFrame(list(data.values()), index=index)

    df = df.reset_index()
    df.columns = [
      'initial_amount', 
      'roi', 
      'duration',
      'frequency',
      'contribution', 
      'inc_contribution',
      'inflation_rate',
      'monthly_retirement_income', 
      'retirement_at',
      'tax_rate',
      'stable_yield',
      'total_amount'
    ]
    return df