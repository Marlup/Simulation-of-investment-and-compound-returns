import numpy as np
import pandas as pd
import polars as pl
from matplotlib import pyplot as plt
import seaborn as sns
import scipy

DEFAULT_RETIREMENT_YEARS = 30
MONTHS_IN_YEAR = 12

def calculate_accumulated_return(principal, 
                                 annual_roi,
                                 compounding_frequency,
                                 annual_contribution, 
                                 investment_duration, 
                                 return_accum_roi=False):
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

def adjust_for_inflation(amount, inflation_rate=0.02, years=1):
    if not (0 < inflation_rate < 1):
        inflation_rate = 0.02
    return amount / ((1 + inflation_rate) ** years)

def calculate_return_on_investment(principal,
                                   annual_roi=0.01,
                                   compounding_frequency=12,
                                   annual_contribution=0.0,
                                   investment_duration=5,
                                   retirement_at=0,
                                   retirement_income=0.0,
                                   retirement_contribution=1200,
                                   inflation_rate=0.0,
                                   tax_percentage=0.0):
    if not isinstance(compounding_frequency, int) or (compounding_frequency < 1):
        compounding_frequency = 1
    n_compounds = MONTHS_IN_YEAR // compounding_frequency
    periodic_roi = annual_roi / n_compounds
    retirement_at_months = MONTHS_IN_YEAR * retirement_at
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    time_counter = 0
    on_retirement = False
    current_balance = principal
    periodic_earnings = []
    for year in range(investment_duration):
        for month in range(1, MONTHS_IN_YEAR + 1):
            if month % compounding_frequency == 0:
                interest_earned = current_balance * periodic_roi
                periodic_earnings.append(interest_earned)
                current_balance += interest_earned
            
            current_balance += monthly_contribution
            
            if not on_retirement and retirement_at_months > 0:
                if time_counter >= retirement_at_months:
                    if not on_retirement:
                        on_retirement = True
                        monthly_contribution = retirement_contribution / MONTHS_IN_YEAR
                else:
                    time_counter += 1
            else:
                current_balance -= retirement_income
        
        if inflation_rate != 0.0:
            current_balance = adjust_for_inflation(current_balance, inflation_rate)

        if tax_percentage != 0.0:
            yearly_earnings = sum(periodic_earnings[-n_compounds:])
            current_balance -= yearly_earnings * tax_percentage

    return current_balance, periodic_earnings
def define_scenario(initial_amounts,
                    rois,
                    years,
                    terms,
                    contributions,
                    inflation_rates,
                    retir_years=20,
                    retir_incomes=1000,
                    retir_contribs_ratio=0.5
                   ):
    
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
