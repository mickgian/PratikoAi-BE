"""
CCNL Calculator Demo Script

This script demonstrates the comprehensive CCNL calculation engine capabilities
with realistic examples from different sectors.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any

from app.models.ccnl_data import *
from app.services.ccnl_calculator_engine import EnhancedCCNLCalculator, CalculationPeriod


def create_metalmeccanici_ccnl() -> CCNLAgreement:
    """Create a comprehensive Metalmeccanici CCNL for demonstration."""
    ccnl = CCNLAgreement(
        sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        name="CCNL Metalmeccanici Industria 2024-2026",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31),
        signatory_unions=["FIOM-CGIL", "FIM-CISL", "UILM-UIL"],
        signatory_employers=["Federmeccanica", "Assistal"]
    )
    
    # Job levels
    ccnl.job_levels = [
        JobLevel("C1", "Operaio Comune", WorkerCategory.OPERAIO, 
                minimum_experience_months=0, description="Operaio addetto a mansioni generiche"),
        JobLevel("C2", "Operaio Qualificato", WorkerCategory.OPERAIO,
                minimum_experience_months=12, description="Operaio con qualifica specifica"),
        JobLevel("B1", "Operaio Specializzato", WorkerCategory.OPERAIO,
                minimum_experience_months=36, description="Operaio altamente specializzato"),
        JobLevel("5", "Impiegato", WorkerCategory.IMPIEGATO,
                minimum_experience_months=0, description="Impiegato amministrativo"),
        JobLevel("6", "Impiegato Senior", WorkerCategory.IMPIEGATO,
                minimum_experience_months=24, description="Impiegato con responsabilità"),
        JobLevel("Q", "Quadro", WorkerCategory.QUADRO,
                minimum_experience_months=60, description="Quadro dirigenziale")
    ]
    
    # Salary tables with geographic variations
    salary_data = [
        ("C1", GeographicArea.NAZIONALE, Decimal('1750.00')),
        ("C1", GeographicArea.NORD, Decimal('1820.00')),
        ("C1", GeographicArea.CENTRO, Decimal('1780.00')),
        ("C1", GeographicArea.SUD, Decimal('1720.00')),
        ("C2", GeographicArea.NAZIONALE, Decimal('1950.00')),
        ("C2", GeographicArea.NORD, Decimal('2050.00')),
        ("C2", GeographicArea.CENTRO, Decimal('1980.00')),
        ("C2", GeographicArea.SUD, Decimal('1920.00')),
        ("B1", GeographicArea.NAZIONALE, Decimal('2250.00')),
        ("B1", GeographicArea.NORD, Decimal('2380.00')),
        ("5", GeographicArea.NAZIONALE, Decimal('2100.00')),
        ("5", GeographicArea.NORD, Decimal('2200.00')),
        ("6", GeographicArea.NAZIONALE, Decimal('2650.00')),
        ("6", GeographicArea.NORD, Decimal('2780.00')),
        ("Q", GeographicArea.NAZIONALE, Decimal('3500.00')),
        ("Q", GeographicArea.NORD, Decimal('3700.00'))
    ]
    
    for level, area, salary in salary_data:
        ccnl.salary_tables.append(SalaryTable(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            level_code=level,
            base_monthly_salary=salary,
            geographic_area=area,
            thirteenth_month=True,
            fourteenth_month=True,
            company_size_adjustments={
                CompanySize.LARGE: Decimal('80.00'),
                CompanySize.MEDIUM: Decimal('50.00'),
                CompanySize.SMALL: Decimal('20.00')
            }
        ))
    
    # Working hours
    ccnl.working_hours = WorkingHours(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        ordinary_weekly_hours=40,
        maximum_weekly_hours=48,
        flexible_hours_allowed=True,
        shift_work_allowed=True,
        night_shift_allowance=Decimal('120.00')
    )
    
    # Overtime rules
    ccnl.overtime_rules = OvertimeRules(
        ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
        daily_overtime_rate=Decimal('1.25'),
        weekend_rate=Decimal('1.50'),
        holiday_rate=Decimal('2.00'),
        maximum_daily_overtime=3,
        maximum_weekly_overtime=12,
        maximum_annual_overtime=250
    )
    
    # Leave entitlements
    ccnl.leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.FERIE,
            base_annual_days=26,
            seniority_bonus_schedule={60: 2, 120: 4, 240: 6}  # 5, 10, 20 years
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.ROL_EX_FESTIVITA,
            base_annual_hours=32
        ),
        LeaveEntitlement(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            leave_type=LeaveType.PERMESSI_RETRIBUITI,
            base_annual_hours=72
        )
    ]
    
    # Notice periods
    ccnl.notice_periods = [
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO, 0, 60, 15),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO, 60, 120, 30),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.OPERAIO, 120, 999, 45),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 0, 24, 30),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 24, 120, 60),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.IMPIEGATO, 120, 999, 90),
        NoticePerioD(CCNLSector.METALMECCANICI_INDUSTRIA, WorkerCategory.QUADRO, 0, 999, 180)
    ]
    
    # Special allowances
    ccnl.special_allowances = [
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.BUONI_PASTO,
            amount=Decimal('7.50'),
            frequency="daily"
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TRASPORTO,
            amount=Decimal('120.00'),
            frequency="monthly",
            geographic_areas=[GeographicArea.NORD, GeographicArea.CENTRO]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_TURNO,
            amount=Decimal('180.00'),
            frequency="monthly",
            job_levels=["C2", "B1", "5", "6"]
        ),
        SpecialAllowance(
            ccnl_sector=CCNLSector.METALMECCANICI_INDUSTRIA,
            allowance_type=AllowanceType.INDENNITA_RISCHIO,
            amount=Decimal('250.00'),
            frequency="monthly",
            job_levels=["B1", "5", "6", "Q"]
        )
    ]
    
    return ccnl


def create_commercio_ccnl() -> CCNLAgreement:
    """Create a Commerce CCNL for comparison."""
    ccnl = CCNLAgreement(
        sector=CCNLSector.COMMERCIO_TERZIARIO,
        name="CCNL Commercio e Terziario 2024-2026",
        valid_from=date(2024, 1, 1),
        valid_to=date(2026, 12, 31)
    )
    
    # Simplified job levels for comparison
    ccnl.job_levels = [
        JobLevel("1", "Impiegato I livello", WorkerCategory.IMPIEGATO),
        JobLevel("2", "Impiegato II livello", WorkerCategory.IMPIEGATO),
        JobLevel("3", "Impiegato III livello", WorkerCategory.IMPIEGATO),
        JobLevel("Q", "Quadro", WorkerCategory.QUADRO)
    ]
    
    # Salary tables (generally lower than manufacturing)
    ccnl.salary_tables = [
        SalaryTable(CCNLSector.COMMERCIO_TERZIARIO, "1", Decimal('1650.00'), 
                   GeographicArea.NAZIONALE, thirteenth_month=True, fourteenth_month=False),
        SalaryTable(CCNLSector.COMMERCIO_TERZIARIO, "2", Decimal('1850.00'), 
                   GeographicArea.NAZIONALE, thirteenth_month=True, fourteenth_month=False),
        SalaryTable(CCNLSector.COMMERCIO_TERZIARIO, "3", Decimal('2150.00'), 
                   GeographicArea.NAZIONALE, thirteenth_month=True, fourteenth_month=False),
        SalaryTable(CCNLSector.COMMERCIO_TERZIARIO, "Q", Decimal('3200.00'), 
                   GeographicArea.NAZIONALE, thirteenth_month=True, fourteenth_month=False)
    ]
    
    # Different leave entitlements
    ccnl.leave_entitlements = [
        LeaveEntitlement(
            ccnl_sector=CCNLSector.COMMERCIO_TERZIARIO,
            leave_type=LeaveType.FERIE,
            base_annual_days=24,  # Less than metalworkers
            seniority_bonus_schedule={60: 2, 120: 3}
        )
    ]
    
    # Notice periods
    ccnl.notice_periods = [
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO, 0, 24, 15),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO, 24, 120, 30),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.IMPIEGATO, 120, 999, 45),
        NoticePerioD(CCNLSector.COMMERCIO_TERZIARIO, WorkerCategory.QUADRO, 0, 999, 90)
    ]
    
    return ccnl


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")


def format_currency(amount: float) -> str:
    """Format currency for display."""
    return f"€ {amount:,.2f}"


def format_compensation_breakdown(breakdown: Dict[str, Any]) -> str:
    """Format compensation breakdown for display."""
    result = []
    result.append(f"Base Salary: {format_currency(breakdown['base_salary'])}")
    result.append(f"13th Month: {format_currency(breakdown['thirteenth_month'])}")
    result.append(f"14th Month: {format_currency(breakdown['fourteenth_month'])}")
    
    if breakdown['allowances']:
        result.append("Allowances:")
        for name, amount in breakdown['allowances'].items():
            result.append(f"  • {name}: {format_currency(amount)}")
    
    if breakdown['overtime'] > 0:
        result.append(f"Overtime: {format_currency(breakdown['overtime'])}")
    
    result.append(f"GROSS TOTAL: {format_currency(breakdown['gross_total'])}")
    result.append(f"NET TOTAL: {format_currency(breakdown['net_total'])}")
    
    return "\n".join(result)


def demo_basic_calculations():
    """Demonstrate basic calculation capabilities."""
    print_section_header("BASIC CALCULATION DEMONSTRATIONS")
    
    # Create CCNL and calculator
    ccnl = create_metalmeccanici_ccnl()
    calculator = EnhancedCCNLCalculator(ccnl)
    
    print_subsection("1. Annual Compensation for C2 Metalworker")
    compensation = calculator.calculate_comprehensive_compensation(
        level_code="C2",
        seniority_months=36,
        geographic_area=GeographicArea.NORD,
        company_size=CompanySize.LARGE,
        include_allowances=True
    )
    print(format_compensation_breakdown(compensation.to_dict()))
    
    print_subsection("2. Monthly vs Annual Comparison")
    monthly_comp = calculator.calculate_comprehensive_compensation(
        level_code="C2",
        period=CalculationPeriod.MONTHLY
    )
    annual_comp = calculator.calculate_comprehensive_compensation(
        level_code="C2",
        period=CalculationPeriod.ANNUAL
    )
    print(f"Monthly Gross: {format_currency(monthly_comp.gross_total)}")
    print(f"Annual Gross: {format_currency(annual_comp.gross_total)}")
    print(f"Calculated Monthly from Annual: {format_currency(annual_comp.gross_total / 12)}")
    
    print_subsection("3. Leave Entitlements by Seniority")
    seniority_levels = [12, 60, 120, 240]  # 1, 5, 10, 20 years
    for months in seniority_levels:
        years = months // 12
        balances = calculator.calculate_leave_balances(seniority_months=months)
        vacation = next(b for b in balances if b.leave_type == LeaveType.FERIE)
        print(f"After {years} years: {vacation.annual_entitlement} vacation days")
    
    print_subsection("4. Notice Periods by Category and Seniority")
    categories = [WorkerCategory.OPERAIO, WorkerCategory.IMPIEGATO, WorkerCategory.QUADRO]
    seniority_examples = [12, 72, 144]  # 1, 6, 12 years
    
    for category in categories:
        print(f"\n{category.italian_name()}:")
        for months in seniority_examples:
            years = months // 12
            benefits = calculator.calculate_seniority_benefits(
                worker_category=category,
                hire_date=date.today() - timedelta(days=365*years)
            )
            print(f"  {years} years: {benefits.notice_period_days} days notice")


def demo_geographic_differences():
    """Demonstrate geographic salary differences."""
    print_section_header("GEOGRAPHIC SALARY DIFFERENCES")
    
    ccnl = create_metalmeccanici_ccnl()
    calculator = EnhancedCCNLCalculator(ccnl)
    
    print_subsection("C2 Operaio Salary by Region")
    differences = calculator.calculate_geographic_differences(
        level_code="C2",
        base_area=GeographicArea.NAZIONALE
    )
    
    base_salary = ccnl.get_salary_for_level("C2", GeographicArea.NAZIONALE)
    print(f"Base (Nazionale): {format_currency(float(base_salary.base_monthly_salary))}")
    
    for area, diff_data in differences.items():
        print(f"{area.replace('_', ' ').title()}: {format_currency(diff_data['monthly_salary'])} "
              f"({diff_data['percentage_difference']:+.1f}%)")


def demo_overtime_scenarios():
    """Demonstrate overtime calculations."""
    print_section_header("OVERTIME CALCULATION SCENARIOS")
    
    ccnl = create_metalmeccanici_ccnl()
    calculator = EnhancedCCNLCalculator(ccnl)
    
    base_salary = Decimal('2000.00')
    scenarios = calculator.calculate_overtime_scenarios(base_salary)
    
    print_subsection("Overtime Rates and Examples")
    for scenario_type, data in scenarios.items():
        if scenario_type == "limits":
            continue
        
        print(f"\n{scenario_type.replace('_', ' ').title()}:")
        print(f"  Rate: {data['rate_multiplier']}x")
        print(f"  Hourly Rate: {format_currency(data['hourly_rate'])}")
        print(f"  Examples:")
        for hours, pay in data['examples'].items():
            print(f"    {hours.replace('_', ' ')}: {format_currency(pay)}")
    
    if "limits" in scenarios:
        print_subsection("Overtime Limits")
        limits = scenarios["limits"]
        print(f"Daily Maximum: {limits['daily_max']} hours")
        print(f"Weekly Maximum: {limits['weekly_max']} hours")
        print(f"Annual Maximum: {limits['annual_max']} hours")


def demo_career_progression():
    """Demonstrate career progression calculations."""
    print_section_header("CAREER PROGRESSION ANALYSIS")
    
    ccnl = create_metalmeccanici_ccnl()
    calculator = EnhancedCCNLCalculator(ccnl)
    
    # Typical career progression
    progression_path = [
        ("C1", 24),  # 2 years as C1
        ("C2", 36),  # 3 years as C2
        ("B1", 60),  # 5 years as B1
        ("5", 60),   # 5 years as Impiegato
        ("6", 120)   # 10 years as Senior Impiegato
    ]
    
    result = calculator.calculate_career_progression(
        starting_level="C1",
        progression_path=progression_path,
        starting_date=date(2004, 1, 1)
    )
    
    print_subsection("25-Year Career Path in Metalmeccanici")
    print(f"Total Career Length: {result['total_months']} months ({result['total_months']//12} years)")
    print(f"Total Career Earnings: {format_currency(result['total_earnings'])}")
    print(f"Average Monthly Salary: {format_currency(result['average_monthly'])}")
    
    print("\nDetailed Progression:")
    for level_data in result['progression_path']:
        years = level_data['months'] // 12
        remaining_months = level_data['months'] % 12
        period_str = f"{years} years" + (f", {remaining_months} months" if remaining_months else "")
        
        print(f"  {level_data['level']}: {period_str}")
        print(f"    Monthly Salary: {format_currency(level_data['monthly_salary'])}")
        print(f"    Period Earnings: {format_currency(level_data['period_earnings'])}")


def demo_ccnl_comparison():
    """Demonstrate CCNL sector comparison."""
    print_section_header("CCNL SECTOR COMPARISON")
    
    # Create both CCNLs
    metalmeccanici = create_metalmeccanici_ccnl()
    commercio = create_commercio_ccnl()
    
    calculator = EnhancedCCNLCalculator(metalmeccanici)
    
    print_subsection("Metalmeccanici vs Commercio - Impiegato Comparison")
    
    # Compare similar levels
    comparisons = calculator.compare_with_other_ccnl(
        commercio,
        level_code="5",  # Impiegato in metalmeccanici
        comparison_aspects=["salary", "leave"]
    )
    
    # Find salary comparison
    for comp in comparisons:
        if "Salary" in comp.aspect:
            better = "Metalmeccanici" if comp.favors_ccnl == 1 else "Commercio"
            print(f"Monthly Base Salary:")
            print(f"  Metalmeccanici: {format_currency(comp.ccnl1_value)}")
            print(f"  Commercio: {format_currency(comp.ccnl2_value)}")
            print(f"  Difference: {format_currency(abs(comp.difference))} in favor of {better}")
            print(f"  Percentage: {abs(comp.percentage_difference):.1f}%")
        
        elif "Ferie" in comp.aspect:
            better = "Metalmeccanici" if comp.favors_ccnl == 1 else "Commercio"
            print(f"\nVacation Days (Ferie):")
            print(f"  Metalmeccanici: {comp.ccnl1_value} days")
            print(f"  Commercio: {comp.ccnl2_value} days")
            print(f"  {better} offers {abs(comp.difference)} more days")


def demo_complex_query():
    """Demonstrate answering complex queries."""
    print_section_header("COMPLEX QUERY DEMONSTRATION")
    
    ccnl = create_metalmeccanici_ccnl()
    calculator = EnhancedCCNLCalculator(ccnl)
    
    print_subsection('Query: "What would be the total compensation for a C2 level metalworker in Northern Italy with 5 years of experience including all allowances and leave entitlements?"')
    
    result = calculator.answer_complex_query(
        level_code="C2",
        worker_category=WorkerCategory.OPERAIO,
        geographic_area=GeographicArea.NORD,
        seniority_years=5,
        include_all_benefits=True
    )
    
    print("\n📊 COMPREHENSIVE ANALYSIS RESULTS")
    print("\n1. COMPENSATION BREAKDOWN:")
    comp = result['compensation']
    print(f"   Annual Gross Total: {format_currency(comp['gross_total'])}")
    print(f"   Annual Net Total: {format_currency(comp['net_total'])}")
    print(f"   Monthly Gross: {format_currency(comp['gross_total']/12)}")
    print(f"   Monthly Net: {format_currency(comp['net_total']/12)}")
    
    print("\n   Components:")
    print(f"   • Base Salary: {format_currency(comp['base_salary'])}")
    print(f"   • 13th Month: {format_currency(comp['thirteenth_month'])}")
    print(f"   • 14th Month: {format_currency(comp['fourteenth_month'])}")
    
    if comp['allowances']:
        print(f"   • Allowances:")
        for name, amount in comp['allowances'].items():
            print(f"     - {name}: {format_currency(amount)}")
    
    print("\n2. LEAVE ENTITLEMENTS:")
    for leave in result['leave_entitlements']:
        if leave['leave_type'] == 'ferie':
            print(f"   • Vacation: {leave['annual_entitlement']} days/year")
        elif leave['leave_type'] == 'permessi_retribuiti':
            print(f"   • Paid Leave: {leave['annual_entitlement']} hours/year")
        elif leave['leave_type'] == 'rol_ex_festivita':
            print(f"   • ROL: {leave['annual_entitlement']} hours/year")
    
    print("\n3. SENIORITY BENEFITS:")
    seniority = result['seniority_benefits']
    print(f"   • Years of Service: {seniority['seniority_years']}")
    print(f"   • Notice Period: {seniority['notice_period_days']} days")
    print(f"   • Severance Pay: {seniority['severance_pay_months']} months salary")
    print(f"   • Additional Leave from Seniority: {seniority['additional_leave_days']} days")
    
    print("\n4. WORKING CONDITIONS:")
    if result['working_hours']:
        wh = result['working_hours']
        print(f"   • Weekly Hours: {wh['weekly_hours']} hours")
        print(f"   • Daily Hours: {wh['daily_hours']:.1f} hours")
        print(f"   • Flexible Hours: {'Yes' if wh['flexible_hours'] else 'No'}")
    
    print(f"\n5. SUMMARY:")
    summary = result['summary']
    print(f"   This C2 metalworker in Northern Italy with 5 years experience would receive:")
    print(f"   • {format_currency(summary['annual_gross_total'])} gross annually")
    print(f"   • {format_currency(summary['monthly_gross'])} gross monthly")
    print(f"   • {summary['total_leave_days']} total leave days per year")
    print(f"   • {summary['notice_period_days']} days notice period for termination")


def demo_all():
    """Run all demonstrations."""
    print("🇮🇹 CCNL CALCULATION ENGINE DEMONSTRATION")
    print("=" * 60)
    print("This demo showcases the comprehensive CCNL calculation capabilities")
    print("for Italian Collective Labor Agreements")
    
    demo_basic_calculations()
    demo_geographic_differences()
    demo_overtime_scenarios()
    demo_career_progression()
    demo_ccnl_comparison()
    demo_complex_query()
    
    print_section_header("DEMONSTRATION COMPLETE")
    print("The CCNL calculation engine provides comprehensive support for:")
    print("✅ Salary calculations with geographic and company size adjustments")
    print("✅ Leave entitlements with seniority bonuses")
    print("✅ Notice periods and severance calculations")
    print("✅ Overtime scenarios and limits")
    print("✅ Career progression analysis")
    print("✅ Cross-sector comparisons")
    print("✅ Complex query answering")
    print("\nThis enables answering complex labor law questions with precise,")
    print("legally compliant calculations based on official CCNL provisions.")


if __name__ == "__main__":
    demo_all()