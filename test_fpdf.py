try:
    from fpdf import FPDF
    print("FPDF imported successfully!")
except ModuleNotFoundError as e:
    print(f"Error: {e}")