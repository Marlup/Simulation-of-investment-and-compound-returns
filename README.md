# Return on Investment Calculator

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python script to calculate the return on investment (ROI) for a given principal amount over a specified investment duration, considering various parameters such as compounding frequency, contributions, inflation, and taxes.

## Table of Contents
- [Introduction](#introduction)
- [Usage](#usage)
- [Parameters](#parameters)
- [Examples](#examples)
- [License](#license)

## Introduction

This Python script calculates the return on investment (ROI) for a given principal amount over a specified investment duration, taking into account various financial parameters. It provides a flexible tool for analyzing investment strategies by allowing you to customize factors such as compounding frequency, contributions, inflation, and taxes.

## Usage

To use this script, simply import the `calculate_return_on_investment` function and provide the required parameters. You can then call the function to obtain the final balance and a list of periodic earnings.

```python
from investment_calculator import calculate_return_on_investment

# Example usage
principal = 10000  # Initial principal amount
annual_roi = 0.05  # Annual return on investment (as a decimal)
terms = 12 # Months taken until the next earning is yield
annual_contribution = 1200 # Annual contribution amount for further investing 
investment_duration = 10  # Investment duration in years

# Call the function
final_balance, periodic_earnings = simulate_compound_return(
    principal,
    annual_roi,
    terms,
    annual_contribution,
    investment_duration
)
# Print the results
print(f"Final Balance: ${final_balance:.2f}")
print("Periodic Earnings:", periodic_earnings)
```

## Parameters
+ **principal** (float): The initial principal amount.
+ **annual_roi** (float, default: 0.01): Annual return on investment as a decimal (e.g., 0.05 for 5%).
+ **compounding_frequency** (int, default: 12): Number of times interest is compounded per year.
+ **annual_contribution** (float, default: 0.0): Annual contribution amount to the investment.
+ **investment_duration** (int, default: 5): Investment duration in years.
+ **retirement_at** (int, default: 0): Number of years until retirement (0 for no retirement).
+ **retirement_income** (float, default: 0.0): Monthly retirement income (if retirement_at > 0).
+ **retirement_contribution** (float, default: 1200): Monthly contribution during retirement (if retirement_at > 0).
+ **inflation_rate** (float, default: 0.0): Annual inflation rate as a decimal (e.g., 0.03 for 3%).
+ **tax_percentage** (float, default: 0.0): Annual tax rate on earnings as a decimal (e.g., 0.2 for 20%).

## Examples

You can find example usage of this script in the examples directory. There is one example that demonstrates an investment scenario and provides detailed usage instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.


