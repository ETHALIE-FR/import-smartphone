import streamlit as st
import pdfplumber
import pandas as pd
import re

st.title("📱 Import Smartphones → Odoo")

uploaded_file = st.file_uploader("Importer un PDF fournisseur", type=["pdf"])

def detect_brand(name):
    n = name.lower()
    if "iphone" in n:
        return "Apple"
    if "samsung" in n or "galaxy" in n:
        return "Samsung"
    return ""

def clean_product_name(name):
    n = name.lower()

    # iPhone (uniformisation)
    if "iphone" in n:
        m = re.search(r"(iphone\s\d+\s?(pro|max|plus)?)", n)
        if m:
            return "iPhone " + m.group(1).split()[1].capitalize() + (" " + m.group(2).capitalize() if m.group(2) else "")

    # Galaxy sans Samsung
    if "galaxy" in n:
        m = re.search(r"(galaxy\s?[a-z0-9\s]+ultra)", n)
        if m:
            return m.group(1).title().replace("Samsung ", "")

    return name.split("(")[0].strip()

if uploaded_file:

    rows = []

    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

        imeis = re.findall(r"\b\d{15}\b", text)
        eans = re.findall(r"EAN\s*:\s*(\d+)", text)
        warranties = re.findall(r"Garantie\s*:\s*([^\(]+)", text)
        products = re.findall(r"(\d{6})\s(.+?)\s(\d+)\s(\d+,\d+)€", text)

        index = 0

        for sku, product, qty, price in products:

            qty = int(qty)
            price = float(price.replace(",", "."))

            brand = detect_brand(product)

            storage_match = re.search(r"(\d+\s?Go)", product)
            storage = storage_match.group(1) if storage_match else ""

            grade_match = re.search(r"Grade\s([A-Z])", product)
            grade = grade_match.group(1) if grade_match else ""

            color_match = re.search(r"Go\s([A-Za-z]+)", product)
            color = color_match.group(1) if color_match else ""

            defect_match = re.search(r"\(([^)]*HS[^)]*)\)", product)
            defect = defect_match.group(1) if defect_match else ""

            etat = "OK"
            if defect:
                etat = "A réparer"

            product_clean = clean_product_name(product)

            for i in range(qty):
                if index >= len(imeis):
                    break

                rows.append({
                    "IMEI": imeis[index],
                    "SKU": sku,
                    "EAN": eans[0] if eans else "",
                    "Marque": brand,
                    "Produit": product_clean,
                    "Stockage": storage,
                    "Couleur": color,
                    "Grade": grade,
                    "Etat technique": etat,
                    "Défaut réparation": defect,
                    "Garantie": warranties[0] if warranties else "",
                    "Prix achat": price
                })

                index += 1

    df = pd.DataFrame(rows)

    st.success(f"{len(df)} téléphones détectés")

    st.dataframe(df)

    csv = df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="📥 Télécharger le CSV pour Odoo",
        data=csv,
        file_name="import_smartphones_odoo.csv",
        mime="text/csv"
    )
