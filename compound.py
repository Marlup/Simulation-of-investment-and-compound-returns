import pandas as pd
from bokeh import plotting as bk
from bokeh.models import Span, HoverTool, ColumnDataSource
import numpy as np
from itertools import product

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
    monthly_retirement_income=500.0,
    inflation_rate=0.02,
    tax_rate=0.2,
    return_time_yields=False,
    verbose=False
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
    
    periodic_earnings = []
    time_counter = 0
    default_retirement_contribution = 0.0
    on_retirement = False
    on_yield = False
    current_balance = principal
    
    if return_time_yields:
    #    periodic_balances = [current_balance]
    #    periodic_earnings = [0.0]
        periodic_balances = []
        periodic_earnings = []
        info = {}
        info['contributions'] = []
        info['before_retirement_contributions'] = []
    
    for _ in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            if month % compounding_frequency == 0 and current_balance > 0:
                interest_earned = current_balance * periodic_roi
                current_balance += interest_earned
                on_yield = True
            
            # Update balance with retirement income
            if on_retirement:
                current_balance -= monthly_retirement_income
            else:
            # Check may retire and on retirement
                if retirement_at_months != 0 and time_counter >= retirement_at_months:
                    if verbose:
                        print(f"Max monthly contribution {monthly_contribution}")
                    if not on_retirement:
                        on_retirement = True
                        
                        monthly_contribution = default_retirement_contribution
                        current_balance -= monthly_retirement_income
            # Increment monthly contribution
                else:
                    time_counter += 1
                    monthly_contribution = (1 + monthly_inc_contribution_rate) * monthly_contribution

            # Update balance with contribution
            current_balance += monthly_contribution

            if return_time_yields:
                periodic_balances.append(current_balance)
                if on_yield or on_retirement:
                    periodic_earnings.append(interest_earned)
                    on_yield = False
            
                info['contributions'].append(monthly_contribution)
                if on_retirement and not info['before_retirement_contributions']:
                    info['before_retirement_contributions'] = info['contributions']
            
        if inflation_rate != 0.0:
            current_balance = adjust_by_inflation(current_balance, inflation_rate)
        
        if tax_rate != 0.0 and isinstance(tax_rate, (int, float)):
            current_balance -=  tax_rate * sum(periodic_earnings[-n_compounds:])
        elif tax_rate != 0.0 and isinstance(tax_rate, (str, )):
            current_balance -= apply_taxes(sum(periodic_earnings[-n_compounds:]), tax_rate)
            
    if return_time_yields:
        info['balances'] = periodic_balances
        info['earnings'] = periodic_earnings
        
        return current_balance, info
    return current_balance

# Tax function
def apply_taxes(earnings: float, country: str="spain"):
    tax_value = 0.0
    if country == "spain":
        if earnings >= 200_000.0:
            tax_value += 0.19 * 5_999.99
            tax_value += 0.21 * 43_999.99
            tax_value += 0.23 * 149_999.99
            return tax_value + 0.26 * (earnings - 199_999.99)
        if earnings >= 50_000.0:
            tax_value += 0.19 * 5_999.99
            tax_value += 0.21 * 43_999.99
            return tax_value + 0.23 * (earnings - 49_999.9)
        if earnings >= 6_000.0:
            tax_value += 0.19 * 5_999.99
            return tax_value + 0.21 * (earnings - 5_999.99)
        else:
            return 0.19 * earnings
    else:
        return 0.21 * earnings

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
        total_amount = simulate_compound_return(
          principal=i_a,
          annual_roi=roi,
          compounding_frequency=t,
          annual_contribution=c,
          inc_contribution_rate=i_c,
          investment_duration=in_d,
          retirement_at=r_a,
          monthly_retirement_income=m_r_i,
          inflation_rate=i_r,
          tax_rate=t_r,
          return_time_yields=False
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
          t_r
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
      'monthly_retirement_income', 
      'retirement_at',
      'tax_rate',
      'total_amount'
    ]
    return df