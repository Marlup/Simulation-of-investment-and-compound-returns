import json
from typing import List

from src.static.constants import (
    DEFAULT_TAX_RATE, 
    DEFAULT_INFLATION_RATE,
    MONTHS_IN_YEAR,
)


class TaxCalculator:
    def __init__(self, json_path: str = "tax_brackets.json"):
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            self.tax_data = data.get("countries", {})

    def compute_taxes_by_country(
            self, 
            earnings: float, 
            n_yields: int = 1, 
            country: str = "spain"
            ) -> float:
        if n_yields < 1:
            n_yields = 1
        
        if country == "":
            # Special case for Spain with single yield
            return DEFAULT_TAX_RATE * earnings / n_yields
        
        country_key = country.lower()
        if country_key not in self.tax_data:
            raise ValueError(f"No tax brackets defined for country: {country}")

        brackets: List[dict] = self.tax_data[country_key]["tax_brackets"]
        tax_value = 0.0
        lower_limit = 0.0

        for bracket in brackets:
            upper_limit = bracket["upper_limit"] if bracket["upper_limit"] is not None else float("inf")
            rate = bracket["rate"]
            if earnings > lower_limit:
                taxable = min(earnings, upper_limit) - lower_limit
                tax_value += taxable * rate
                lower_limit = upper_limit
            else:
                break

        return tax_value / n_yields
    
    @staticmethod
    def compute_default_taxes(earnings: float, n_yields: int, tax_rate: float):
        if n_yields < 1:
            return DEFAULT_TAX_RATE * earnings / 1
        # Default case
        return DEFAULT_TAX_RATE * earnings / n_yields

def get_inflation_amount(amount: float, n_yields: int=1, inflation: float=0.02, years: int=1):
    adjusted_inflation = inflation / n_yields
    if not (0.0 < adjusted_inflation < 1.0):
        adjusted_inflation = DEFAULT_INFLATION_RATE / n_yields
    return amount * (1 - 1 / (1 + adjusted_inflation) ** years)

def is_retirement(counter: int, retirement_month: int, on_retirement: bool):
    if not on_retirement and counter >= retirement_month:
        return True
    return False

def adjust_for_inflation(balance: float, inflation_rate: float):
    return balance - get_inflation_amount(balance, MONTHS_IN_YEAR, inflation_rate)