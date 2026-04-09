import spacy
from rapidfuzz import process, fuzz
import re
from datetime import datetime

class SmartParser:
    def __init__(self):
        # Try to load SpaCy, fallback to simple extraction if missing
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.has_nlp = True
        except:
            print("⚠️ SpaCy model 'en_core_web_sm' not found. Using basic fallback.")
            self.has_nlp = False

    def extract_entities(self, query):
        """Extracts Names, Dates, Quantities"""
        entities = {"PERSON": None, "DATE": None, "QUANTITY": None, "ITEM": None}
        
        if self.has_nlp:
            doc = self.nlp(query)
            for ent in doc.ents:
                if ent.label_ == "PERSON": entities["PERSON"] = ent.text
                elif ent.label_ == "DATE" or ent.label_ == "TIME": entities["DATE"] = ent.text
                elif ent.label_ == "CARDINAL" or ent.label_ == "QUANTITY": entities["QUANTITY"] = ent.text
        
        # Fallback / Enhancement with Regex
        if not entities["QUANTITY"]:
            qty_match = re.search(r'\b\d+\b', query)
            if qty_match: entities["QUANTITY"] = qty_match.group()

        return entities

    def fuzzy_extract_item(self, query, item_list):
        """Finds the closest matching inventory item name in the query"""
        # Remove common action words to isolate the item name
        clean_q = query.lower()
        for word in ["add", "stock", "update", "how", "many", "check", "inventory"]:
            clean_q = clean_q.replace(word, "")
        
        match = process.extractOne(clean_q.strip(), item_list, scorer=fuzz.partial_ratio)
        if match and match[1] > 60: # Confidence threshold
            return match[0]
        return None
