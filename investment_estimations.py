import numpy as np
import pandas as pd
import polars as pl
from matplotlib import pyplot as plt
import seaborn as sns
import scipy

DEFAULT_RETIREMENT_YEARS = 30
MONTHS_IN_YEAR = 12

def calculate_accumulated_return(principal, yearly_contributions, annual_roi, years, compounding_frequency, return_acum_roi=False):
    # Calculate the ROI for each compounding period
    term_roi = annual_roi / compounding_frequency
    # Calculate the periodic contribution
    periodic_contribution = yearly_contributions / compounding_frequency

    # Calculate the accumulated ROI over the specified number of years
    accumulated_roi = (1 + term_roi) ** (years * compounding_frequency)

    # Calculate the principal amount after the specified number of years
    principal_term = principal * accumulated_roi

    # Calculate the contribution term
    contribution_term = (periodic_contribution * (accumulated_roi - 1)) / term_roi

    # Calculate the total amount after the specified number of years
    total_amount = principal_term + contribution_term

    if return_acum_roi:
        return round(total_amount, 2), round(accumulated_roi, 2)
    return round(total_amount, 2)

def adjust_for_inflation(amount, inflation_rate=0.02, years=1):
    if not (0 < inflation_rate < 1):
        inflation_rate = 0.02
    return amount / ((1 + inflation_rate) ** years)

def calculate_return_on_investment(principal,
                                   annual_roi=0.01,
                                   compounding_frequency=12,
                                   annual_contribution=0.0,
                                   investment_duration=5,
                                   min_investment_amount=0.0,
                                   retirement_duration=5,
                                   retirement_income=0.0,
                                   retirement_contribution=1200,
                                   inflation_rate=0.0,
                                   tax_percentage=0.0):

    on_retirement = False
    current_balance = principal
    earned_interest = 0
    annual_earnings = []

    if (compounding_frequency is None) or (compounding_frequency < 1):
        compounding_frequency = 1

    if retirement_income > 0.0 and investment_duration <= retirement_duration:
        retirement_duration = DEFAULT_RETIREMENT_YEARS
        investment_duration = 2 * DEFAULT_RETIREMENT_YEARS

    retirement_months = retirement_duration * MONTHS_IN_YEAR
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    monthly_roi = annual_roi / compounding_frequency
    month_counter = 0
    time_counter = 0

    for year in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            if month_counter % (12 // compounding_frequency) == 0:
                interest_earned = current_balance * monthly_roi
                annual_earnings.append(interest_earned)
                earned_interest += interest_earned

            current_balance += monthly_contribution

            if earned_interest >= min_investment_amount and earned_interest > 0:
                current_balance += earned_interest
                earned_interest = 0.0

            if on_retirement or time_counter >= retirement_months:
                if not on_retirement:
                    on_retirement = True
                    monthly_contribution = retirement_contribution / MONTHS_IN_YEAR
                current_balance -= retirement_income
            else:
                time_counter += 1

            month_counter += 1

        if inflation_rate != 0.0:
            current_balance = adjust_for_inflation(current_balance, inflation_rate)

        if tax_percentage != 0.0:
            yearly_earnings = sum(annual_earnings[-MONTHS_IN_YEAR:])
            current_balance -= yearly_earnings * tax_percentage

    return current_balance, annual_earnings

def define_scenario(initial_amounts,
                    rois,
                    years,
                    terms,
                    contributions,
                    inflation_rates,
                    retir_years=20,
                    retir_incomes=1000,
                    retir_contribs_ratio=0.5,
                    min_investment=10):
    
    accumulated_money = {}

    for initial_amount in initial_amounts:
        for roi in rois:
            for term in terms:
                for contribution in contributions:
                    for year in years:
                        for retir_income in retir_incomes:
                            for inflation_rate in inflation_rates:
                                total_money, _ = calculate_return_on_investment(
                                    principal=initial_amount,
                                    annual_roi=roi,
                                    compounding_frequency=term,
                                    annual_contribution=contribution,
                                    investment_duration=year,
                                    min_investment_amount=min_investment,
                                    retirement_duration=retir_years,
                                    retirement_income=retir_income,
                                    retirement_contribution=contribution * retir_contribs_ratio,
                                    inflation_rate=inflation_rate
                                )
                                scenario_key = (
                                    initial_amount, roi, term, contribution, inflation_rate, year, retir_income
                                )
                                accumulated_money[scenario_key] = total_money

    return accumulated_money


def build_dataframe(data):
  index = pd.MultiIndex.from_tuples(list(data.keys()))
  df = pd.DataFrame(list(data.values()), index=index)

  df = df.reset_index()
  df.columns = ['initial_amount', 
                'roi', 
                'term', 
                'contrib', 
                'inflation', 
                'year', 
                'retir_income', 
                'amount']
  return df