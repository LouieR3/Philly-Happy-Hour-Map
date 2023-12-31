import fitz  # PyMuPDF
import requests
from io import BytesIO
import pandas as pd
import re

# ------------------------------------------------
# This script does = just to test scraping pdf
# ------------------------------------------------

def try_pdf(pdf_path):
    def extract_drinks_from_pdf(pdf_path):
        try:
            response = requests.get(pdf_path)
            print(response)
            # print(response.content)
            if response.status_code == 200:
                pdf_data = BytesIO(response.content)
                pdf_document = fitz.open(stream=pdf_data, filetype="pdf") # type: ignore
                # print(pdf_document)
                text = ""
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    text += page.get_text()
                pdf_document.close()
                return text
            else:
                print("Failed to fetch PDF from URL.")
        except Exception as e:
            print("An error occurred:", e)
        return None

    def extract_alcohol_percentage(drink_name):
        match = re.search(r'\((\d+\.\d+)\%\)', drink_name)
        if match:
            return match.group(1)
        return None

    def create_dataframe_from_text(text):
        drinks = []
        
        lines = text.split('\n')
        drink_name = ""
        drink_price = ""
        
        for line in lines:
            if line.strip() and line.isascii():
                if "$" in line:
                    components = line.split()
                    for component in components:
                        if '$' in component:
                            drink_price = component
                            price = float(drink_price.replace("$", ""))

                            drink_name = re.sub(r'\(.+?\)', '', drink_name).strip()

                            if drink_name and drink_price and price < 24:
                                drinks.append((drink_name.strip(), drink_price.strip()))
                            drink_name = ""
                            break
                        else:
                            drink_name += component + " "
                    
        df = pd.DataFrame(drinks, columns=["Drink", "Price"])
        bar_name = "Barbuzzo"
        df.insert(0, "Bar", bar_name)
        return df
    
    extracted_text = extract_drinks_from_pdf(pdf_path)
    if extracted_text:
        print(extracted_text)
        menu_df = create_dataframe_from_text(extracted_text)
        return menu_df
    else:
        print("Failed to extract text from PDF.")
        return None

if __name__ == "__main__":
    # "http://www.barbuzzo.com///Pdfs/menubrunch12_2_21.pdf""http://www.barbuzzo.com/Pdfs/barbuzzoBEVERAGE_MENU.pdf"
    # pdf_path = "https://www.hardrockcafe.com/location/philadelphia/files/5463/23-HRC-03255_-_Summer_Beverage_LTO_T3_1.pdf"
    # pdf_path = "https://centercityphila.org/uploads/attachments/clkjrtuzr9mfdm8qd9woymj2v-ancientdinner.pdf"
    # pdf_path = "https://centercityphila.org/uploads/attachments/cllgspi5hasp4m8qd12vpri4h-bank-bourbondinner.pdf"
    pdf_path = "https://centercityphila.org/uploads/attachments/clle1p8a8anenomqd0zww53ap-barbuzzo.pdf"
    # pdf_path = "https://centercityphila.org/uploads/attachments/clmgcy1f5d4rc0vqd015d322u-bucadinner.pdf"
    # pdf_path = "https://centercityphila.org/uploads/attachments/cllntmgoqb021saqdx4mq8n1m-butcher.pdf"
    # pdf_path = "https://centercityphila.org/uploads/attachments/clmcvj2l5c6gjypqd2aw9cx6l-conmurphy-dinner.pdf"
    menu_df = try_pdf(pdf_path)
    
    print(menu_df)
    