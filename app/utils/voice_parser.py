import re
from datetime import datetime

class VoiceParser:
    """
    Parses voice commands and extracts structured data
    Example: "Ramesh reti tractor 6 trip 1200 udhar"
    Extracts: party, material, vehicle, quantity, rate, payment_status
    """
    
    MATERIALS = {
        'reti': 'reti',
        'balu': 'balu',
        'mitti': 'mitti',
        'stone': 'stone',
        'cement': 'cement',
        'brick': 'brick',
        'sand': 'balu',
        'gravel': 'stone',
    }
    
    VEHICLES = {
        'tractor': 'tractor',
        'truck': 'truck',
        'tempo': 'tempo',
        'chhota': 'chhota truck',
        'bada': 'bada truck',
    }
    
    PAYMENT_STATUS = {
        'udhar': 'pending',
        'upfront': 'pending',
        'advance': 'partial',
        'paid': 'paid',
        'paya': 'paid',
    }
    
    def __init__(self, materials=None, vehicles=None):
        self.extracted_data = {}
        # Dynamic fallback to original dictionary if None provided (for backwards compatibility/tests)
        self.materials_map = {k.lower(): k for k in materials} if materials else self.MATERIALS
        self.vehicles_map = {k.lower(): k for k in vehicles} if vehicles else self.VEHICLES
    
    def parse(self, voice_text):
        """
        Parse voice command and extract relevant data
        """
        try:
            text = voice_text.lower().strip()
            self.extracted_data = {
                'raw_text': voice_text,
                'party': None,
                'material': None,
                'vehicle': None,
                'quantity': None,
                'rate': None,
                'trips': 1,
                'payment_status': 'pending',
                'notes': text
            }
            
            # Extract party name (usually first word or proper noun)
            party = self._extract_party(text)
            if party:
                self.extracted_data['party'] = party
            
            # Extract material
            material = self._extract_material(text)
            if material:
                self.extracted_data['material'] = material
            
            # Extract vehicle
            vehicle = self._extract_vehicle(text)
            if vehicle:
                self.extracted_data['vehicle'] = vehicle
            
            # Extract numbers (quantity, rate, trips)
            numbers = self._extract_numbers(text)
            if numbers:
                if len(numbers) >= 2:
                    self.extracted_data['quantity'] = numbers[0]
                    self.extracted_data['rate'] = numbers[-1]
                    if len(numbers) == 3:
                        self.extracted_data['trips'] = numbers[1]
                elif len(numbers) == 1:
                    self.extracted_data['rate'] = numbers[0]
            
            # Extract payment status
            status = self._extract_payment_status(text)
            if status:
                self.extracted_data['payment_status'] = status
            
            # Extract trips if mentioned with "trip" keyword
            trips = self._extract_trips(text)
            if trips:
                self.extracted_data['trips'] = trips
            
            return self.extracted_data
        
        except Exception as e:
            self.extracted_data['error'] = str(e)
            return self.extracted_data
    
    def _extract_party(self, text):
        """Extract party name from voice text"""
        # Look for capitalized words (assuming party names are capitalized)
        words = text.split()
        for word in words:
            # Exclude common keywords
            if word not in ['trip', 'trips'] and len(word) > 1:
                if word.isalnum() and not any(char.isdigit() for char in word):
                    return word.capitalize()
        return None
    
    def _extract_material(self, text):
        """Extract material name"""
        for key, value in self.materials_map.items():
             if key in text:
                 return value
        return None
    
    def _extract_vehicle(self, text):
        """Extract vehicle type"""
        for key, value in self.vehicles_map.items():
             if key in text:
                 return value
        return None
    
    def _extract_numbers(self, text):
        """Extract all numbers from text"""
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        return [float(n) for n in numbers]
    
    def _extract_payment_status(self, text):
        """Extract payment status"""
        for key, value in self.PAYMENT_STATUS.items():
            if key in text:
                return value
        return 'pending'
    
    def _extract_trips(self, text):
        """Extract number of trips"""
        match = re.search(r'(\d+)\s*trip', text)
        if match:
            return int(match.group(1))
        return 1
    
    def validate(self):
        """Validate extracted data"""
        errors = []
        
        if not self.extracted_data.get('party'):
            errors.append('Party name not found')
        
        if not self.extracted_data.get('material'):
            errors.append('Material not found')
        
        if not self.extracted_data.get('rate'):
            errors.append('Rate not found')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'data': self.extracted_data if len(errors) == 0 else None
        }


# Test examples
def test_parser():
    parser = VoiceParser()
    
    test_cases = [
        "Ramesh reti tractor 6 trip 1200 udhar",
        "Amit balu truck 10 trip 800 paid",
        "Priya stone tractor 5 1500 advance",
    ]
    
    for test_case in test_cases:
        result = parser.parse(test_case)
        validation = parser.validate()
        print(f"\nInput: {test_case}")
        print(f"Parsed: {result}")
        print(f"Valid: {validation}")


if __name__ == '__main__':
    test_parser()
