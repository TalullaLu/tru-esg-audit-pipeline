import pandas as pd

def generate_csv():
    data = [
        {"ticket_id": 1, "employee_id": "EMP_001", "route": "SYD-AKL", "booked_class": "Economy", "ticket_price_aud": 450.0},
        {"ticket_id": 2, "employee_id": "EMP_002", "route": "SYD-LHR", "booked_class": "Business", "ticket_price_aud": 8500.0}
    ]
    
    file_name = "fact_travel_expense.csv"
    pd.DataFrame(data).to_csv(file_name, index=False)
    print(f"SUCCESS: Generated {file_name} in current directory.")

if __name__ == "__main__":
    generate_csv()