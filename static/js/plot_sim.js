// bokeh_plot.js

// Ensure BokehJS is loaded
if (typeof Bokeh === 'undefined') {
    alert("BokehJS is not loaded. Make sure the CDN is included before this script.");
}

(function() {
    const MONTHS_IN_YEAR = 12;

    // Create ColumnDataSources
    const source_balances = new Bokeh.ColumnDataSource({data: {month: [], year: [], balance: []}});
    const source_earnings = new Bokeh.ColumnDataSource({data: {yield_term: [], earning: []}});

    // Create plots
    const plot_e = new Bokeh.Plotting.figure({
        title: "Earnings Over Time",
        height: 285,
        width: 800,
        x_axis_label: "Yield Term",
        y_axis_label: "Earning (€)"
    });
    plot_e.line({x: {field: 'yield_term'}, y: {field: 'earning'}, source: source_earnings, line_width: 2, line_color: "green"});

    const plot_b = new Bokeh.Plotting.figure({
        title: "Balance Over Time",
        height: 285,
        width: 800,
        x_axis_label: "Month",
        y_axis_label: "Balance (€)"
    });
    plot_b.line({x: {field: 'month'}, y: {field: 'balance'}, source: source_balances, line_width: 2, line_color: "navy"});

    // Sliders and Select
    const s_principal = new Bokeh.Slider({title: "Initial Amount (€)", start: 0, end: 100000, step: 1000, value: 10000});
    const s_roi = new Bokeh.Slider({title: "Annual ROI", start: 0.0, end: 0.15, step: 0.005, value: 0.05});
    const s_duration = new Bokeh.Slider({title: "Investment Duration (Years)", start: 1, end: 60, step: 1, value: 40});
    const s_frequency = new Bokeh.Slider({title: "Payment Frequency (Months)", start: 1, end: 12, step: 1, value: 12});
    const s_contribution = new Bokeh.Slider({title: "Annual Contribution (€)", start: 0, end: 50000, step: 500, value: 1200});
    const s_inc_contribution = new Bokeh.Slider({title: "Increment Contribution Rate", start: 0.0, end: 1.0, step: 0.01, value: 0.01});
    const s_inflation = new Bokeh.Slider({title: "Inflation Rate", start: 0.0, end: 1.0, step: 0.01, value: 0.02});
    const s_retirement_income = new Bokeh.Slider({title: "Monthly Retirement Income (€)", start: 0, end: 5000, step: 100, value: 500});
    const s_retirement_at = new Bokeh.Slider({title: "Retirement At (Years)", start: 0, end: 60, step: 1, value: 30});
    const select_tax = new Bokeh.Select({title: "Tax (Fixed Rate)", value: "0.21", options: ["0.15", "0.21", "0.30"]});

    function getInflationAmount(amount, nYields, inflation, years = 1) {
        let adjusted = inflation / nYields;
        if (!(adjusted > 0.0 && adjusted < 1.0)) adjusted = 0.02 / nYields;
        return amount * (1 - 1 / Math.pow(1 + adjusted, years));
    }

    function getContributionInc(monthlyContribution, monthlyIncrement) {
        if (monthlyIncrement > 0 && monthlyContribution > 0) {
            return monthlyIncrement * monthlyContribution;
        }
        return 0;
    }

    function getTaxAmount(earnings, nYields, rate) {
        return parseFloat(rate) * earnings / nYields;
    }

    function simulate() {
        const params = {
            principal: s_principal.value,
            annual_roi: s_roi.value,
            yield_frequency: s_frequency.value,
            annual_contribution: s_contribution.value,
            inc_contribution_rate: s_inc_contribution.value,
            investment_duration: s_duration.value,
            retirement_at: s_retirement_at.value,
            monthly_retirement_income: s_retirement_income.value,
            inflation_rate: s_inflation.value,
            tax_rate: select_tax.value
        };

        const nYieldsPerYear = Math.floor(MONTHS_IN_YEAR / params.yield_frequency);
        const periodicROI = params.annual_roi / nYieldsPerYear;
        const retirementStart = params.retirement_at * MONTHS_IN_YEAR;
        let monthlyContribution = params.annual_contribution / MONTHS_IN_YEAR;
        const monthlyInc = params.inc_contribution_rate / MONTHS_IN_YEAR;

        let currentBalance = params.principal;
        let time = 0;
        let onRetirement = false;
        let earningsWindow = [];
        let balances = [], earnings = [];

        for (let y = 0; y < params.investment_duration; y++) {
            for (let m = 1; m <= MONTHS_IN_YEAR; m++) {
                const yieldPeriod = (m % params.yield_frequency === 0) && currentBalance > 0;
                if (yieldPeriod) {
                    const gross = currentBalance * periodicROI;
                    const infl = getInflationAmount(gross, nYieldsPerYear, params.inflation_rate);
                    const net = gross - infl;
                    currentBalance += gross;
                    earningsWindow.push(net);
                    if (earningsWindow.length > nYieldsPerYear) earningsWindow.shift();
                    const tax = getTaxAmount(net, nYieldsPerYear, params.tax_rate);
                    earnings.push(net - tax);
                }
                if (!onRetirement && time >= retirementStart) {
                    onRetirement = true;
                    monthlyContribution = 0;
                }
                const outflow = onRetirement ? params.monthly_retirement_income : 0;
                currentBalance += monthlyContribution - outflow;
                currentBalance -= getInflationAmount(currentBalance, MONTHS_IN_YEAR, params.inflation_rate);
                if (!onRetirement) monthlyContribution += getContributionInc(monthlyContribution, monthlyInc);
                balances.push(currentBalance);
                time++;
            }
            if (params.tax_rate !== "") {
                const sumEarnings = earningsWindow.reduce((a, b) => a + b, 0);
                currentBalance -= getTaxAmount(sumEarnings, 1, params.tax_rate);
            }
        }

        source_balances.data = {
            month: Array.from({length: balances.length}, (_, i) => i),
            year: Array.from({length: balances.length}, (_, i) => Math.floor(i / 12)),
            balance: balances
        };
        source_earnings.data = {
            yield_term: Array.from({length: earnings.length}, (_, i) => i),
            earning: earnings
        };
        source_balances.change.emit();
        source_earnings.change.emit();
    }

    [s_principal, s_roi, s_duration, s_frequency, s_contribution,
     s_inc_contribution, s_inflation, s_retirement_income,
     s_retirement_at, select_tax].forEach(w => w.connect(w.change, simulate));

    simulate();

    const controls = Bokeh.layouts.column(
        s_principal, s_roi, s_duration, s_frequency,
        s_contribution, s_inc_contribution, s_inflation,
        s_retirement_income, s_retirement_at, select_tax
    );

    const layout = Bokeh.layouts.row(controls, Bokeh.layouts.column(plot_e, plot_b));

    Bokeh.Plotting.show(layout, document.getElementById("bokeh-container"));
})();
