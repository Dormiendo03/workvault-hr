"""
Philippine Payroll Calculator
Based on DOLE Labor Code, SSS, PhilHealth, Pag-IBIG, and BIR TRAIN Law
"""

from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

class PHPayrollCalculator:
    """Philippine payroll computation following DOLE standards"""
    
    # Constants
    WORKING_DAYS_PER_MONTH = 22
    HOURS_PER_DAY = 8
    MINUTES_PER_HOUR = 60
    GRACE_PERIOD_MINUTES = 10  # Standard grace period
    
    # Standard work schedule
    STANDARD_TIME_IN = time(8, 0)  # 8:00 AM
    STANDARD_TIME_OUT = time(17, 0)  # 5:00 PM
    
    def __init__(self, monthly_salary):
        """
        Initialize calculator with monthly salary
        
        Args:
            monthly_salary (float): Monthly basic salary
        """
        self.monthly_salary = Decimal(str(monthly_salary))
        self.daily_rate = self._calculate_daily_rate()
        self.hourly_rate = self._calculate_hourly_rate()
        self.per_minute_rate = self._calculate_per_minute_rate()
    
    def _calculate_daily_rate(self):
        """Calculate daily rate: Monthly Salary ÷ 22"""
        return (self.monthly_salary / Decimal(self.WORKING_DAYS_PER_MONTH)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def _calculate_hourly_rate(self):
        """Calculate hourly rate: Daily Rate ÷ 8"""
        return (self.daily_rate / Decimal(self.HOURS_PER_DAY)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def _calculate_per_minute_rate(self):
        """Calculate per-minute rate: Hourly Rate ÷ 60"""
        return (self.hourly_rate / Decimal(self.MINUTES_PER_HOUR)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    def calculate_tardiness_deduction(self, late_minutes):
        """
        Calculate tardiness deduction
        
        Args:
            late_minutes (int): Number of minutes late
            
        Returns:
            Decimal: Deduction amount
        """
        if late_minutes <= self.GRACE_PERIOD_MINUTES:
            return Decimal('0.00')
        
        actual_late = late_minutes - self.GRACE_PERIOD_MINUTES
        deduction = (Decimal(str(actual_late)) * self.per_minute_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return deduction
    
    def calculate_undertime_deduction(self, undertime_hours):
        """
        Calculate undertime deduction
        
        Args:
            undertime_hours (float): Number of hours undertime
            
        Returns:
            Decimal: Deduction amount
        """
        deduction = (Decimal(str(undertime_hours)) * self.hourly_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return deduction
    
    def calculate_absent_deduction(self, absent_days):
        """
        Calculate absent deduction (No-Work, No-Pay Rule)
        
        Args:
            absent_days (int): Number of absent days
            
        Returns:
            Decimal: Deduction amount
        """
        deduction = (Decimal(str(absent_days)) * self.daily_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return deduction
    
    def calculate_overtime_pay(self, ot_hours, ot_type='regular'):
        """
        Calculate overtime pay
        
        Args:
            ot_hours (float): Number of overtime hours
            ot_type (str): 'regular' (1.5x time-and-a-half)
            
        Returns:
            Decimal: Overtime pay amount
        """
        # Standard overtime rate: 1.5x (time-and-a-half)
        rate_multiplier = Decimal('1.5')
        
        ot_pay = (Decimal(str(ot_hours)) * self.hourly_rate * rate_multiplier).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return ot_pay
    
    def calculate_sss_contribution(self):
        """
        Calculate SSS employee contribution (5% of MSC)
        Simplified calculation - actual uses contribution table
        
        Returns:
            Decimal: SSS contribution amount
        """
        # Simplified: 5% of salary, max ₱1,500
        msc = min(self.monthly_salary, Decimal('30000'))
        msc = max(msc, Decimal('4000'))
        
        contribution = (msc * Decimal('0.05')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return min(contribution, Decimal('1500.00'))
    
    def calculate_philhealth_contribution(self):
        """
        Calculate PhilHealth employee contribution (2.5% of monthly basic salary)
        Employee share is 2.5% (not 5%)
        
        Returns:
            Decimal: PhilHealth contribution amount (monthly)
        """
        # Floor: ₱10,000, Ceiling: ₱100,000
        bms = min(self.monthly_salary, Decimal('100000'))
        bms = max(bms, Decimal('10000'))
        
        # Employee share: 2.5% of monthly basic salary
        contribution = (bms * Decimal('0.025')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Maximum contribution: ₱2,500/month
        return min(contribution, Decimal('2500.00'))
    
    def calculate_pagibig_contribution(self):
        """
        Calculate Pag-IBIG employee contribution
        Rate: 1% (salary ≤ ₱1,500) or 2% (salary > ₱1,500)
        Maximum: ₱100 per MONTH (RA 9679 ceiling)
        
        Returns:
            Decimal: Pag-IBIG contribution amount (monthly)
        """
        if self.monthly_salary <= Decimal('1500'):
            rate = Decimal('0.01')
        else:
            rate = Decimal('0.02')
        
        # Calculate contribution (no ceiling on base, only on contribution)
        contribution = (self.monthly_salary * rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # RA 9679: ₱100/month is the hard ceiling
        return min(contribution, Decimal('100.00'))
    
    def calculate_withholding_tax(self, taxable_income):
        """
        Calculate withholding tax based on TRAIN Law (RA 10963)
        
        TRAIN Law exemption: Annualized compensation ≤ ₱250,000 = ZERO tax
        Monthly equivalent: ≤ ₱20,833.33
        
        Args:
            taxable_income (Decimal): Monthly taxable income after deductions
            
        Returns:
            Decimal: Withholding tax amount
        """
        # TRAIN Law: ₱250,000 annual (₱20,833.33 monthly) and below = TAX EXEMPT
        if taxable_income <= Decimal('20833'):
            return Decimal('0.00')
        elif taxable_income <= Decimal('33332'):
            # Above ₱250K to ₱400K annual: 20% of excess over ₱250K
            excess = taxable_income - Decimal('20833')
            tax = (excess * Decimal('0.20')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif taxable_income <= Decimal('66666'):
            # ₱400K to ₱800K: ₱30K + 25% of excess
            excess = taxable_income - Decimal('33333')
            tax = Decimal('2500') + (excess * Decimal('0.25')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif taxable_income <= Decimal('166666'):
            # ₱800K to ₱2M: ₱130K + 30% of excess
            excess = taxable_income - Decimal('66667')
            tax = Decimal('10833') + (excess * Decimal('0.30')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        elif taxable_income <= Decimal('666666'):
            # ₱2M to ₱8M: ₱490K + 32% of excess
            excess = taxable_income - Decimal('166667')
            tax = Decimal('40833') + (excess * Decimal('0.32')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            # Above ₱8M: ₱2.41M + 35% of excess
            excess = taxable_income - Decimal('666667')
            tax = Decimal('200833') + (excess * Decimal('0.35')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_semi_monthly_payroll(self, 
                                       worked_days=11,
                                       late_minutes=0,
                                       undertime_hours=0,
                                       absent_days=0,
                                       ot_hours=0,
                                       ot_type='regular',
                                       other_deductions=0):
        """
        Calculate complete semi-monthly payroll
        
        Args:
            worked_days (int): Number of days worked in period (default 11 for semi-monthly)
            late_minutes (int): Total late minutes
            undertime_hours (float): Total undertime hours
            absent_days (int): Number of absent days
            ot_hours (float): Overtime hours
            ot_type (str): Type of overtime
            other_deductions (float): Other deductions (loans, etc.)
            
        Returns:
            dict: Complete payroll breakdown
        """
        # Basic pay (semi-monthly)
        basic_pay = (self.monthly_salary / Decimal('2')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Overtime pay
        ot_pay = self.calculate_overtime_pay(ot_hours, ot_type)
        
        # Gross earnings
        gross_earnings = basic_pay + ot_pay
        
        # Deductions
        tardiness_deduction = self.calculate_tardiness_deduction(late_minutes)
        undertime_deduction = self.calculate_undertime_deduction(undertime_hours)
        absent_deduction = self.calculate_absent_deduction(absent_days)
        
        # Government contributions (semi-monthly = monthly ÷ 2)
        sss = (self.calculate_sss_contribution() / Decimal('2')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        philhealth = (self.calculate_philhealth_contribution() / Decimal('2')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        pagibig = (self.calculate_pagibig_contribution() / Decimal('2')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Taxable income
        taxable_income = self.monthly_salary - self.calculate_sss_contribution() - \
                        self.calculate_philhealth_contribution() - self.calculate_pagibig_contribution()
        
        withholding_tax = (self.calculate_withholding_tax(taxable_income) / Decimal('2')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Total deductions
        total_deductions = (
            tardiness_deduction +
            undertime_deduction +
            absent_deduction +
            sss +
            philhealth +
            pagibig +
            withholding_tax +
            Decimal(str(other_deductions))
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Net pay with floor at ₱0 (cannot go negative)
        # Philippine labor law: Employee cannot owe the company
        net_pay_calculated = gross_earnings - total_deductions
        net_pay = max(Decimal('0.00'), net_pay_calculated).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Log deficit for potential recovery in next period
        deficit = Decimal('0.00')
        if net_pay_calculated < Decimal('0.00'):
            deficit = abs(net_pay_calculated)
            print(f"WARNING: Payroll deficit of ₱{deficit} - deductions exceed earnings")
        
        return {
            'basic_pay': float(basic_pay),
            'overtime_pay': float(ot_pay),
            'gross_earnings': float(gross_earnings),
            'tardiness_deduction': float(tardiness_deduction),
            'undertime_deduction': float(undertime_deduction),
            'absent_deduction': float(absent_deduction),
            'sss_contribution': float(sss),
            'philhealth_contribution': float(philhealth),
            'pagibig_contribution': float(pagibig),
            'withholding_tax': float(withholding_tax),
            'other_deductions': float(other_deductions),
            'total_deductions': float(total_deductions),
            'net_pay': float(net_pay),
            'deficit': float(deficit),  # Track any deficit
            'daily_rate': float(self.daily_rate),
            'hourly_rate': float(self.hourly_rate),
            'per_minute_rate': float(self.per_minute_rate)
        }
    
    def calculate_13th_month_pay(self, total_basic_salary_ytd):
        """
        Calculate 13th month pay
        
        Args:
            total_basic_salary_ytd (float): Total basic salary earned year-to-date
            
        Returns:
            Decimal: 13th month pay amount
        """
        thirteenth_month = (Decimal(str(total_basic_salary_ytd)) / Decimal('12')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return float(thirteenth_month)


def calculate_late_minutes(scheduled_time_in, actual_time_in):
    """
    Calculate late minutes from time objects
    
    Args:
        scheduled_time_in (time): Scheduled time in (e.g., 8:00 AM)
        actual_time_in (time): Actual time in
        
    Returns:
        int: Number of minutes late (0 if early/on-time)
    """
    if actual_time_in <= scheduled_time_in:
        return 0
    
    # Convert to datetime for calculation
    today = datetime.today().date()
    scheduled_dt = datetime.combine(today, scheduled_time_in)
    actual_dt = datetime.combine(today, actual_time_in)
    
    diff = actual_dt - scheduled_dt
    minutes = int(diff.total_seconds() / 60)
    
    return max(0, minutes)


def calculate_undertime_hours(scheduled_time_out, actual_time_out):
    """
    Calculate undertime hours from time objects
    
    Args:
        scheduled_time_out (time): Scheduled time out (e.g., 5:00 PM)
        actual_time_out (time): Actual time out
        
    Returns:
        float: Number of hours undertime (0 if overtime/on-time)
    """
    if actual_time_out >= scheduled_time_out:
        return 0.0
    
    # Convert to datetime for calculation
    today = datetime.today().date()
    scheduled_dt = datetime.combine(today, scheduled_time_out)
    actual_dt = datetime.combine(today, actual_time_out)
    
    diff = scheduled_dt - actual_dt
    hours = diff.total_seconds() / 3600
    
    return max(0.0, hours)
