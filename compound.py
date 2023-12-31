import pandas as pd
from bokeh import plotting as bk
from bokeh.models import Span, HoverTool, ColumnDataSource
import numpy as np

DEFAULT_RETIREMENT_YEARS = 30
MONTHS_IN_YEAR = 12

def get_compound_return(
    principal, 
    annual_roi,
    compounding_frequency,
    annual_contribution, 
    investment_duration, 
    return_accum_roi=False
):
    # Calculate the ROI for each compounding period
    term_roi = annual_roi / compounding_frequency
    # Calculate the periodic contribution
    periodic_contribution = annual_contribution / compounding_frequency

    # Calculate the accumulated ROI over the specified number of years
    accumulated_roi = (1 + term_roi) ** (investment_duration * compounding_frequency)

    # Calculate the principal amount after the specified number of years
    principal_term = principal * accumulated_roi

    # Calculate the contribution term
    contribution_term = (periodic_contribution * (accumulated_roi - 1)) / term_roi

    # Calculate the total amount after the specified number of years
    total_amount = principal_term + contribution_term

    if return_accum_roi:
        return round(total_amount, 2), round(accumulated_roi, 2)
    return round(total_amount, 2)

def adjust_by_inflation(amount, inflation_rate=0.02, years=1):
    if not (0.0 < inflation_rate < 1.0):
        inflation_rate = 0.02
    return amount / ((1 + inflation_rate) ** years)

def simulate_compound_return(
    principal,
    annual_roi=0.05,
    compounding_frequency=12,
    annual_contribution=100.0,
    inc_contribution_rate=0.0,
    investment_duration=60,
    retirement_at=30,
    retirement_income=500.0,
    retirement_contribution=1200,
    inflation_rate=0.02,
    tax_rate=0.19,
    return_time_yields=False
):
    if not isinstance(compounding_frequency, int) or (compounding_frequency < 1):
        compounding_frequency = 1
    # How many yielding events we have to take to compute taxes. For example: c_f = 1 -> 12 events
    n_compounds = MONTHS_IN_YEAR // compounding_frequency
    periodic_roi = annual_roi / n_compounds
    if investment_duration <= retirement_at:
        raise Exception("Argument error: 'investment_duration' must be greater than 'retirement_at'.")
    retirement_at_months = MONTHS_IN_YEAR * retirement_at
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    monthly_inc_contribution_rate = inc_contribution_rate / MONTHS_IN_YEAR
    # Calculate 'effective retirement income', i.e. retirement income 
    # minus contribution commited for investment during retirement 
    eff_retirement_income = retirement_income - retirement_contribution / MONTHS_IN_YEAR
    
    periodic_earnings = []
    time_counter = 0
    on_retirement = False
    on_yield = False
    current_balance = principal
    
    if return_time_yields:
    #    periodic_balances = [current_balance]
    #    periodic_earnings = [0.0]
        periodic_balances = []
        periodic_earnings = []
    
    for year in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            if month % compounding_frequency == 0 and current_balance > 0:
                interest_earned = current_balance * periodic_roi
                current_balance += interest_earned
                on_yield = True
                
            current_balance += monthly_contribution
            
            if not on_retirement:
                if retirement_at_months !=0 and time_counter >= retirement_at_months:
                    if not on_retirement:
                        print(f"Max monthly contribution {monthly_contribution}")
                        on_retirement = True
                        monthly_contribution = retirement_contribution / MONTHS_IN_YEAR
                        current_balance -= eff_retirement_income
                else:
                    time_counter += 1
                    monthly_contribution = (1 + monthly_inc_contribution_rate) * monthly_contribution
            else:
                current_balance -= retirement_income - monthly_contribution
            if return_time_yields:
                periodic_balances.append(current_balance)
                if on_yield or on_retirement:
                    periodic_earnings.append(interest_earned)
                    on_yield = False
        if inflation_rate != 0.0:
            current_balance = adjust_by_inflation(current_balance, inflation_rate)

        if tax_rate != 0.0:
            yearly_earnings = sum(periodic_earnings[-n_compounds:])
            current_balance -= yearly_earnings * tax_rate
            
    if return_time_yields:
    #    periodic_balances.append(current_balance)
    #    periodic_earnings.append(interest_earned)
        return current_balance, periodic_earnings, periodic_balances
    return current_balance

# Plot earning and contribution evolutions
def plot_scenario_bokeh(earnings, balances, principal, w= 400, h=300):
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
            ('year',  '@year (month @month)'),
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
    retirement_at=20,
    retirement_incomes=1000,
    retirement_contrib_ratio=0.5,
    tax_rate=0.25
):
    
    accumulated_amount = {}

    for initial_amount in initial_amounts:
        for roi in rois:
            for investment_duration in investment_durations:
                for term in terms:
                    for contribution in contributions:
                        for inflation_rate in inflation_rates:
                            for retirement_income in retirement_incomes:
                                for inc_contribution in inc_contributions:
                                    retirement_contribution = contribution * retirement_contrib_ratio

                                    total_amount = simulate_compound_return(
                                      principal=initial_amount,
                                      annual_roi=roi,
                                      compounding_frequency=term,
                                      annual_contribution=contribution,
                                      inc_contribution_rate=inc_contribution,
                                      investment_duration=investment_duration,
                                      retirement_at=retirement_at,
                                      retirement_income=retirement_income,
                                      retirement_contribution=contribution * retirement_contrib_ratio,
                                      inflation_rate=inflation_rate,
                                      tax_rate=tax_rate,
                                      return_time_yields=False
                                    )
                                    scenario_key = (
                                      initial_amount, 
                                      roi, 
                                      investment_duration,
                                      term, 
                                      contribution, 
                                      inc_contribution,
                                      inflation_rate, 
                                      retirement_income,
                                      retirement_contribution
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
      'term',
      'contribution', 
      'inc_contribution',
      'inflation_rate',
      'retirement_income', 
      'retirement_contribution',
      'total_amount'
    ]
    return df
