import json

def debug_filtering(fda_data_file="data/fda_pma_comprehensive.json"):
    print(f"Loading {fda_data_file}...")
    try:
        with open(fda_data_file, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            results = data
        else:
            results = data.get('results', [])
            
        print(f"Loaded {len(results)} records.")
    except Exception as e:
        print(f"Error: {e}")
        return

    # Define keywords/patterns exactly as in the main script
    surgical_specialties = {
        'cardiac_surgery': ['cardiac', 'heart', 'cardiovascular', 'coronary', 'valve', 'pacemaker', 'defibrillator', 'stent', 'catheter', 'angioplasty', 'bypass'],
        'orthopedic_surgery': ['orthopedic', 'orthopaedic', 'joint', 'knee', 'hip', 'shoulder', 'spine', 'prosthesis', 'implant', 'fixation', 'plate', 'screw', 'rod'],
        'neurosurgery': ['neurological', 'brain', 'spinal', 'neurostimulator', 'deep brain', 'neuromodulation', 'stereotactic', 'neurovascular'],
        'general_surgery': ['surgical', 'laparoscopic', 'endoscopic', 'robotic', 'surgical robot', 'minimally invasive', 'surgical instrument', 'surgical tool'],
        'plastic_surgery': ['cosmetic', 'plastic', 'reconstructive', 'breast', 'facial', 'aesthetic'],
        'ophthalmology': ['ophthalmic', 'eye', 'retinal', 'cataract', 'glaucoma', 'corneal', 'intraocular', 'ophthalmology'],
        'urology': ['urological', 'urology', 'prostate', 'bladder', 'kidney', 'urinary', 'nephrology', 'dialysis'],
        'gynecology': ['gynecological', 'gynecology', 'obstetric', 'uterine', 'ovarian', 'hysterectomy', 'endometrial'],
        'dental_surgery': ['dental', 'oral', 'maxillofacial', 'dental implant', 'orthodontic', 'periodontal', 'endodontic'],
        'vascular_surgery': ['vascular', 'arterial', 'venous', 'peripheral', 'vascular graft', 'aneurysm', 'thrombectomy']
    }
    
    exclusion_patterns = [
        'diagnostic', 'diagnosis', 'test', 'assay', 'analyzer', 'monitor', 'detector',
        'imaging', 'scanner', 'x-ray', 'mri', 'ct scan', 'ultrasound', 'fluoroscopy',
        'laboratory', 'lab', 'in vitro', 'ivd', 'reagent', 'calibrator', 'control',
        'software', 'app', 'application', 'database', 'system software',
        'bandage', 'dressing', 'gauze', 'tape', 'adhesive', 'wound care',
        'supplement', 'vitamin', 'nutrition', 'dietary',
        'drug', 'pharmaceutical', 'medication', 'therapy drug',
        'disposable', 'single use', 'sterile', 'packaging'
    ]

    surgery_keywords = []
    for specialty, keywords in surgical_specialties.items():
        surgery_keywords.extend(keywords)
    
    specific_surgical_terms = [
        'surgery', 'surgical', 'surgical robot', 'surgical instrument', 'surgical tool',
        'operation', 'operative', 'procedure', 'implant', 'prosthesis', 'prosthetic',
        'robotic surgery', 'laparoscopic', 'endoscopic', 'minimally invasive',
        'surgical system', 'surgical platform', 'surgical device'
    ]
    surgery_keywords.extend(specific_surgical_terms)

    stats = {
        'total': len(results),
        'excluded_pattern': 0,
        'no_keyword_match': 0,
        'passed_first_filter': 0,
        'failed_specific_filter': 0,
        'final_passed': 0
    }
    
    excluded_samples = []
    failed_specific_samples = []
    passed_devices = []

    for row in results:
        openfda = row.get('openfda', {})
        if not isinstance(openfda, dict):
            openfda = {}
            
        device_name = str(openfda.get('device_name', '')).lower()
        generic_name = str(row.get('generic_name', '')).lower()
        trade_name = str(row.get('trade_name', '')).lower()
        product_code = str(row.get('product_code', '')).lower()
        all_text = f"{device_name} {generic_name} {trade_name} {product_code}"
        
        # Check exclusions
        excluded = False
        reason = ""
        for exclusion in exclusion_patterns:
            if exclusion in all_text:
                if 'surgical' in all_text or 'surgery' in all_text:
                    if exclusion in ['diagnostic', 'monitor']:
                        continue
                excluded = True
                reason = exclusion
                break
        
        if excluded:
            stats['excluded_pattern'] += 1
            if len(excluded_samples) < 10:
                excluded_samples.append(f"{reason} | {all_text[:100]}")
            continue
            
        # Check keywords
        keyword_match = False
        for keyword in surgery_keywords:
            if keyword.lower() in all_text:
                keyword_match = True
                break
        
        if not keyword_match:
            stats['no_keyword_match'] += 1
            continue
            
        stats['passed_first_filter'] += 1
        
        # Second filter: Specific terms
        # Replicates has_specific_surgical_term
        has_specific = False
        
        specialty_keywords = []
        for _, keywords in surgical_specialties.items():
            specialty_keywords.extend(keywords)
            
        text_for_specific = f"{device_name} {generic_name} {trade_name}" # Note: excluding product_code here as per original code
        
        for keyword in specialty_keywords:
            if keyword.lower() in text_for_specific:
                has_specific = True
                break
        
        if not has_specific:
            if any(term in text_for_specific for term in ['surgical robot', 'robotic surgery', 'da vinci', 'mako', 'rosa']):
                has_specific = True
        
        if not has_specific:
            stats['failed_specific_filter'] += 1
            if len(failed_specific_samples) < 10:
                failed_specific_samples.append(text_for_specific[:100])
            continue
            
        stats['final_passed'] += 1
        passed_devices.append(text_for_specific[:50])

    print("\n--- STATISTICS ---")
    print(json.dumps(stats, indent=2))
    
    print("\n--- EXCLUDED BY PATTERN (SAMPLE) ---")
    for s in excluded_samples:
        print(f"Excluded: {s}")
        
    print("\n--- FAILED SPECIFIC FILTER (SAMPLE) ---")
    for s in failed_specific_samples:
        print(f"Failed Specific: {s}")

    print("\n--- PASSED (SAMPLE) ---")
    for s in passed_devices[:10]:
        print(f"Passed: {s}")

if __name__ == "__main__":
    debug_filtering()
