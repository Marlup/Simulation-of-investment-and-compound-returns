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

def get_compound_return(
    principal, 
    annual_roi,
    yield_frequency,
    annual_contribution, 
    investment_duration, 
    return_accum_roi=False
):
    # Calculate the ROI for each compounding period
    term_roi = annual_roi / yield_frequency
    # Calculate the periodic contribution
    periodic_contribution = annual_contribution / yield_frequency

    # Calculate the accumulated ROI over the specified number of years
    accumulated_roi = (1 + term_roi) ** (investment_duration * yield_frequency)

    # Calculate the principal amount after the specified number of years
    principal_term = principal * accumulated_roi

    # Calculate the contribution term
    contribution_term = (periodic_contribution * (accumulated_roi - 1)) / term_roi

    # Calculate the total amount after the specified number of years
    total_amount = principal_term + contribution_term

    if return_accum_roi:
        return round(total_amount, 2), round(accumulated_roi, 2)
    return round(total_amount, 2)

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
    tax="",
    return_series=False,
    check_sustained_yield=True,
    verbose=False
):
    """
    Note. The criteria 'taxes after inflation' is applied.
    """
    if not isinstance(yield_frequency, int) or (yield_frequency < 1):
        print(f"Yield frequency changed from {yield_frequency} to 1")
        yield_frequency = 1
    if investment_duration <= retirement_at:
        #raise Exception("Argument error: 'investment_duration' must be greater than 'retirement_at'.")
        print("\nArgument warning: 'investment_duration' must be greater than 'retirement_at'. retirement_at \
will be ignored (retirement_at = investment_duration) \n")
        retirement_at = investment_duration
    # Annual yields in yield_frequency
    n_annual_yields =  MONTHS_IN_YEAR // yield_frequency
        
    periodic_roi = annual_roi / n_annual_yields
    retirement_at_months = MONTHS_IN_YEAR * retirement_at
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    monthly_inc_contribution_rate = inc_contribution_rate / MONTHS_IN_YEAR
    time_counter = 0
    default_retirement_contribution = 0.0
    on_retirement = False
    current_balance = principal
    deque_earnings = deque(maxlen=n_annual_yields)
    
    info = {}
    if return_series:
        contributions = []
        before_retirement_contributions = []
        gross_earnings = []
        net_earnings = []
        earnings_after_inflation = []
        tax_from_earnings = []
        periodic_balances = []
    for year in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            #print(f"year {year} - month {month} : {monthly_contribution}")
            
            on_yield = month % yield_frequency == 0 and current_balance > 0
            if on_yield:
                
                gross_earning = current_balance * periodic_roi
                #print(f"\n\tyear {year} - month {month}: {earning}")
                inflation_from_earning = get_inflation_amount(gross_earning, 
                                                              n_annual_yields, 
                                                              inflation_rate
                                                             )
                # Compute and store annual earning after inflation
                earning_after_inflation = gross_earning - inflation_from_earning
                deque_earnings.append(earning_after_inflation)
                
                # Update balance by gross earning (We update the balance with gross earning,
                # after that the taxes and inflation reduction will be applied)
                current_balance += gross_earning
            
            if not on_retirement:
                # Check start of retirement
                if retirement_at_months != 0 and time_counter >= retirement_at_months:
                    if verbose:
                        print(f"Max monthly contribution {monthly_contribution}")
                    if not on_retirement:
                        on_retirement = True
                        monthly_contribution = default_retirement_contribution
                else:
                    time_counter += 1

            # Update balance by contribution and retirement income
            retirement_income = int(on_retirement) * monthly_retirement_income
            current_balance += monthly_contribution - retirement_income
            
            # Update balance by inflation
            if inflation_rate > 0.0:
                current_balance -= get_inflation_amount(current_balance, 
                                                        MONTHS_IN_YEAR, 
                                                        inflation_rate
                                                       )
            # Update monthly contribution by increment
            if monthly_inc_contribution_rate > 0.0 and current_balance > 0.0:
                monthly_contribution += get_contribution_inc(monthly_contribution, 
                                                             monthly_inc_contribution_rate
                                                            )
            # Term based storage
            if not return_series:
                continue
            if on_yield or on_retirement:
                tax_from_earning = get_tax_amount(earning_after_inflation, 
                                                  n_annual_yields,
                                                  tax
                                                 )
                # Store earning types:
                # Gross earnings
                gross_earnings.append(gross_earning)
                # Net earnings
                net_earning = earning_after_inflation - tax_from_earning
                net_earnings.append(net_earning)
                # Inflation from earnings
                earnings_after_inflation.append(inflation_from_earning)
                # Taxes from earnings
                tax_from_earnings.append(tax_from_earning)
            
            # Net balance
            periodic_balances.append(current_balance)
            # Contribution
            contributions.append(monthly_contribution)
            
            if on_retirement and not before_retirement_contributions:
                before_retirement_contributions = contributions
                
        # Apply taxes at the end of the year
        if tax:
            current_balance -= get_tax_amount(sum(deque_earnings), 
                                              1, 
                                              tax
                                             )
    if deque_earnings[0] < deque_earnings[-1]:
        info["stable_yield"] = True
    else:
        info["stable_yield"] = False
    info['contributions'] = contributions
    info['before_retirement_contributions'] = before_retirement_contributions
    if return_series:
        info['gross_earnings'] = gross_earnings
        info['net_earnings'] = net_earnings
        info['balances'] = periodic_balances
        info['tax_from_earnings'] = tax_from_earnings
        info['inflation_from_earnings'] = inflation_from_earning
    return current_balance, info

def get_inflation_amount(amount: float, n_yields: int=1, inflation: float=0.02, years: int=1):
    adjusted_inflation = inflation / n_yields
    if not (0.0 < adjusted_inflation < 1.0):
        adjusted_inflation = 0.02 / n_yields
    return amount * (1 - 1 / (1 + adjusted_inflation) ** years)

# Tax function
def get_tax_amount(earnings, n_yields, tax):
    if isinstance(tax, (int, float)):
        #return tax_rate * sum(earnings[-compunds:])
        return tax * earnings / n_yields
    elif isinstance(tax, (str, )):
        #return _compute_taxes(sum(earnings[-compunds:]), tax_rate)
        return _compute_taxes(earnings, n_yields, tax)
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
            return tax_value + 0.23 * (earnings - 49_999.9) / n_yields
        if earnings >= 6_000.0:
            tax_value += 0.19 * 5_999.99
            return tax_value + 0.21 * (earnings - 5_999.99) / n_yields
        else:
            return 0.19 * earnings / n_yields
    else:
        return 0.21 * earnings / n_yields

def get_contribution_inc(contribution, increment_rate):
    return increment_rate * contribution

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