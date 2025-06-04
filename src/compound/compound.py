from typing import List

from taxes.taxes import TaxCalculator

from taxes.taxes import (
    get_inflation_amount, 
)

from src.static.constants import (
    INT_TO_TERM_NAME, 
    DEFAULT_CURRENCY,
    MONTHS_IN_YEAR,
    DEFAULT_RETIREMENT_YEARS
)


def compute_interest_data_from_yield(
        balance: float, 
        roi: float,
        inflation_rate: float, 
        n_yields: int, 
        #earnings_window: List[int]
        ):
    gross_interest = compute_gross_interest(balance, roi)
    inflation_amount = get_inflation_amount(gross_interest, n_yields, inflation_rate)
    net_interest_after_inflation = gross_interest - inflation_amount
    
    return gross_interest, inflation_amount, net_interest_after_inflation

def compute_gross_interest(balance, roi):
    if roi < 0.0:
        raise ValueError("ROI must be a non-negative value.")
    return balance * roi

def check_retirement(
        counter: int, 
        retirement_month: int, 
        on_retirement: bool, 
        contribution: float, 
        verbose: bool
        ) -> tuple[bool, float]:
    if not on_retirement and counter >= retirement_month:
        if verbose:
            print(f"Max monthly contribution reached: {contribution}")
        return True, 0.0
    return on_retirement, contribution

def update_balance_from_flows(
        balance: float, 
        contribution: float, 
        on_retirement: bool, 
        retirement_income: float
        ):
    outflow = retirement_income if on_retirement else 0.0
    inflow = contribution
    return balance + inflow - outflow

def adjust_for_inflation(balance, inflation_rate):
    return balance - get_inflation_amount(balance, MONTHS_IN_YEAR, inflation_rate)

def increment_contribution(contribution: float, increment: float, balance: float):
    if increment > 0.0 and balance > 0.0:
        return contribution + (increment * contribution)
    return contribution

def get_contribution_inc(monthly_contribution: float, monthly_increment: float):
    if monthly_increment > 0.0 and monthly_contribution > 0.0:
        return monthly_increment * monthly_contribution
    return 0.0