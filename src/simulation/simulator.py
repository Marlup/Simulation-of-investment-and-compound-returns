from itertools import product
from collections import deque
from typing import List

from src.taxes.taxes import (
    TaxCalculator,
    get_inflation_amount, 
    adjust_for_inflation,
    is_retirement,
)

from src.compound.compound import (
    get_incremented_contribution,
    check_retirement,
    get_contribution_inc,
    update_balance_from_flows,
    compute_gross_interest
)

from src.static.constants import (
    MONTHS_IN_YEAR,
    TAX_DATA_FILE,
)


tax_calculator = TaxCalculator(TAX_DATA_FILE)

class CompoundReturnSimulator:
    def __init__(
        self,
        principal: float,
        annual_roi: float=0.05,
        yield_frequency: int=12,
        annual_contribution: float=100.0,
        inc_contribution_rate: float=0.0,
        investment_duration: int=60,
        retirement_at: int=30,
        monthly_retirement_income: float=500.0,
        inflation_rate: float=0.02,
        tax: str | float="",
        return_series: bool=False,
        verbose: bool=False,
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
        self.adjusted_roi = self.annual_roi / self.n_yields_per_year
        self.retirement_start_month = self.retirement_at * MONTHS_IN_YEAR
        self.monthly_contribution = self.annual_contribution / MONTHS_IN_YEAR
        self.adjusted_inc_contribution_rate = self.inc_contribution_rate / MONTHS_IN_YEAR

        self.balance = principal
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
        year_month_periods = product(
            range(self.investment_duration),
            range(1, MONTHS_IN_YEAR + 1)
        )
        for year, month in year_month_periods:
            is_yield_period = (month % self.yield_frequency == 0) and self.balance > 0
            
            self._update_period(is_yield_period)

        self._finalize_results()
        return self.get_result()

    def _update_period(self, is_yield_period: bool):
        """Update the simulator state for a single period."""
        if is_yield_period:
            self._update_interest_data_from_yield()

        self._is_retirement()

        self._update_balance_from_flows()

        self._update_balance_from_taxes()

        self._update_balance_from_inflation()

        if self.return_series:
            self._track_series_data(is_yield_period)

        self._update_contribution()

        self._increment_time_counter()

    def _is_retirement(self):
        ok = is_retirement(
            self.time_counter,
            self.retirement_start_month,
            self.on_retirement,
        )
        if self.verbose:
            print(f"Max monthly contribution reached: {self.monthly_contribution}")
        if ok:
            self.on_retirement = True
            self.monthly_contribution = 0.0

    def _update_interest_data_from_yield(self):
        #gross_amount, inflation_amount, net_amount = compute_interest_data_from_yield(self.balance, self.adjusted_roi, self.inflation_rate, self.n_yields_per_year)
        gross_interest = compute_gross_interest(self.balance, self.adjusted_roi)
        interest_inflation_amount = get_inflation_amount(gross_interest, self.n_yields_per_year, self.inflation_rate)
        net_interest_after_inflation = gross_interest - interest_inflation_amount
    
        # Update earnings window with net amount after inflation
        self.earnings_window.append(net_interest_after_inflation)
        self.balance += gross_interest
        self.last_gross = gross_interest
        self.last_net = net_interest_after_inflation
        self.last_inflation = interest_inflation_amount

    def _update_balance_from_flows(self):
        retirement_outflow = self.monthly_retirement_income if self.on_retirement else 0.0
        contribution_inflow = self.monthly_contribution
        
        self.balance = update_balance_from_flows(
            self.balance,
            contribution_inflow,
            self.on_retirement,
            retirement_outflow
        )

    def _update_balance_from_inflation(self):
        if self.inflation_rate > 0.0:
            self.balance -= get_inflation_amount(self.balance, MONTHS_IN_YEAR, self.inflation_rate)

    def _update_balance_from_taxes(self):
        if self.earnings_window and self.tax:
            self.balance -= get_tax_amount_from_window(self.earnings_window, 1, self.tax)

    def _update_contribution(self):
        if not self.on_retirement \
        and self.adjusted_inc_contribution_rate > 0.0 \
        and self.balance > 0.0:
            self.monthly_contribution += get_contribution_inc(
                self.monthly_contribution, 
                self.adjusted_inc_contribution_rate
                )

    def _increment_time_counter(self):
        self.time_counter += 1

    def _track_series_data(self, is_yield_period: bool):
        if is_yield_period or self.on_retirement:
            tax_amount = get_tax_amount_from_total(self.last_net, self.n_yields_per_year, self.tax)
            self.gross_earnings.append(self.last_gross)
            self.net_earnings.append(self.last_net - tax_amount)
            self.inflation_from_earnings.append(self.last_inflation)
            self.tax_from_earnings.append(tax_amount)

        self.balances.append(self.balance)
        self.contributions.append(self.monthly_contribution)

        if self.on_retirement and not self.before_retirement_contributions:
            self.before_retirement_contributions = self.contributions.copy()

    def _finalize_results(self):
        if self.return_series:
            self.info.update(
                {
                    "contributions": self.contributions,
                    "before_retirement_contributions": self.before_retirement_contributions,
                    "gross_earnings": self.gross_earnings,
                    "net_earnings": self.net_earnings,
                    "balances": self.balances,
                    "tax_from_earnings": self.tax_from_earnings,
                    "inflation_from_earnings": self.inflation_from_earnings
                }
            )
        if len(self.earnings_window) >= 2:
            self.info["stable_yield"] = self.earnings_window[0] < self.earnings_window[-1]

    def get_result(self):
        return self.balance, self.info

def simulate_compound_return(
    principal: float,
    annual_roi: float=0.05,
    yield_frequency: float=12,
    annual_contribution: float=100.0,
    inc_contribution_rate: float=0.0,
    investment_duration: int=60,
    retirement_at: int=30,
    monthly_retirement_income: float=500.0,
    inflation_rate: float=0.02,
    tax_rate: str | float="",
    return_series: bool=False,
    check_sustained_yield: bool=True,
    verbose: bool=False
):
    if not isinstance(yield_frequency, int) or yield_frequency < 1:
        print(f"Yield frequency changed from {yield_frequency} to 1")
        yield_frequency = 1

    if investment_duration <= retirement_at:
        print("\nArgument warning: 'investment_duration' must be greater than 'retirement_at'. retirement_at will be ignored\n")
        retirement_at = investment_duration

    n_yields_per_year = MONTHS_IN_YEAR // yield_frequency
    adjusted_roi = annual_roi / n_yields_per_year
    retirement_start_month = retirement_at * MONTHS_IN_YEAR
    monthly_contribution = annual_contribution / MONTHS_IN_YEAR
    adjusted_inc_contribution_rate = inc_contribution_rate / MONTHS_IN_YEAR

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
                #gross_amount, inflation_amount, net_tax_amount = compute_interest_data_from_yield(
                #    current_balance, adjusted_roi, inflation_rate, n_yields_per_year
                #    #, earnings_window
                #)
                gross_interest = compute_gross_interest(current_balance, adjusted_roi)
                interest_inflation_amount = get_inflation_amount(gross_interest, n_yields_per_year, inflation_rate)
                net_interest_after_inflation = gross_interest - interest_inflation_amount
    
                # Update earnings window with net amount after inflation
                current_balance += gross_interest
            
            on_retirement, monthly_contribution = check_retirement(
                time_counter, retirement_start_month, on_retirement, monthly_contribution, verbose
            )

            current_balance = update_balance_from_flows(
                current_balance, monthly_contribution, on_retirement, monthly_retirement_income
            )

            current_balance = adjust_for_inflation(current_balance, inflation_rate)

            if not on_retirement:
                monthly_contribution = get_incremented_contribution(
                    monthly_contribution, adjusted_inc_contribution_rate
                )

            if return_series:
                if is_yield_period or on_retirement:
                    tax_amount = get_tax_amount_from_total(net_interest_after_inflation, n_yields_per_year, tax_rate)
                    net = net_interest_after_inflation - tax_amount

                    #gross_earnings.append(current_balance * adjusted_roi)
                    gross_earnings.append(gross_interest)
                    net_earnings.append(net)
                    #inflation_from_earnings.append(get_inflation_amount(current_balance * adjusted_roi, n_yields_per_year, inflation_rate))
                    inflation_from_earnings.append(interest_inflation_amount)
                    tax_from_earnings.append(tax_amount)

                balances.append(current_balance)
                contributions.append(monthly_contribution)

                if on_retirement and not before_retirement_contributions:
                    before_retirement_contributions = contributions.copy()

            time_counter += 1

        if tax_rate:
            current_balance -= get_tax_amount_from_window(earnings_window, 1, tax_rate)

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

def simulate_scenarios(
    initial_amounts: List[float],
    rois: List[float],
    investment_durations: List[int],
    terms: List[int],
    contributions: List[float],
    inc_contributions: List[float],
    inflation_rates: List[float],
    monthly_retirement_incomes: List[float],
    retirement_ats: List[float]=[20],
    tax_rates: List[float]=[0.25]
):
    accumulated_amount = {}
    combs = product(
        initial_amounts, 
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

def get_tax_amount_from_total(
        earnings: float,
        n_yields: int,
        tax_rate: float
        ) -> float:
    if isinstance(tax_rate, (int, float)):
        return tax_calculator.compute_default_taxes(
            earnings, 
            n_yields, 
            tax_rate
            )
    elif isinstance(tax_rate, str):
        return tax_calculator.compute_taxes_by_country(
            earnings, 
            n_yields, 
            tax_rate
            ) 

def get_tax_amount_from_window(
        earnings_window: List[float],
        n_yields: int,
        tax_rate: float
        ) -> float:
    return get_tax_amount_from_total(
        earnings=sum(earnings_window),
        n_yields=n_yields, 
        tax_rate=tax_rate
        )

# Función wrapper de la simulación
def run_simulation(**kwargs) -> tuple[list[float], list[float], list[float], list[float]]:
    sim = CompoundReturnSimulator(**kwargs, return_series=True)
    _, result = sim.simulate()
    return result["balances"], result["net_earnings"], result["gross_earnings"], result["tax_from_earnings"]