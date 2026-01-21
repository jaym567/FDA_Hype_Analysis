import pandas as pd
import re
import config
import sys
from pathlib import Path

def is_surgical_device(row):
    """
    Determine if a device is truly surgical based on multiple criteria.
    
    Surgical devices are those used IN surgery (implants, instruments, grafts),
    NOT diagnostic devices, electronics, or non-invasive tools.
    """
    
    trade_name = str(row.get('trade_name', '')).upper()
    generic_name = str(row.get('generic_name', '')).upper()
    product_code = str(row.get('product_code', '')).upper()
    
    # Combine all text fields for searching
    text = f"{trade_name} {generic_name}"
    
    # --- EXCLUSIONS (Non-surgical devices) ---
    
    # Electronics & Stimulators
    exclude_keywords = [
        'PACEMAKER', 'DEFIBRILLATOR', 'ICD', 'STIMULATOR', 'PULSE GENERATOR',
        'NEUROSTIMULATOR', 'LEAD', 'ELECTRODE', 'PROGRAMMER',
        
        # Ophthalmic non-surgical
        'CONTACT LENS', 'LASER SYSTEM', 'EXCIMER', 'LASIK', 'VITRECTOMY SYSTEM',
        'PHACOEMULSIFICATION',
        
        # Cardiovascular non-surgical/minimally invasive
        'STENT', 'CATHETER', 'GUIDEWIRE', 'CLOSURE DEVICE', 'OCCLUDER',
        'BALLOON', 'ANGIOPLASTY',
        
        # Diagnostic/Monitoring
        'MONITOR', 'SENSOR', 'RECORDER', 'ANALYZER', 'METER',
        
        # Drug delivery
        'PUMP', 'INFUSION',
        
        # Dental (often not considered "surgical" in medical sense)
        'DENTAL', 'ORTHODONTIC', 'TOOTH'
    ]
    
    for keyword in exclude_keywords:
        if keyword in text:
            return False
    
    # --- INCLUSIONS (Surgical devices) ---
    
    # Implants (structural, not electronic)
    surgical_keywords = [
        # Orthopedic
        'JOINT', 'HIP', 'KNEE', 'SHOULDER', 'SPINE', 'FUSION CAGE', 
        'SPINAL', 'VERTEBRAL', 'DISC', 'PROSTHESIS', 'ARTHROPLASTY',
        'BONE GRAFT', 'FRACTURE', 'PLATE', 'SCREW', 'ROD', 'NAIL',
        
        # General/Plastic Surgery
        'BREAST IMPLANT', 'MAMMARY', 'TISSUE EXPANDER', 'MESH',
        'HERNIA', 'SUTURE', 'STAPLER', 'CLIP', 'ANASTOMOSIS',
        'GRAFT', 'SKIN SUBSTITUTE', 'WOUND', 'HEMOSTAT', 'SEALANT',
        
        # Cardiovascular surgical
        'HEART VALVE', 'VALVE PROSTHESIS', 'ANNULOPLASTY', 'VASCULAR GRAFT',
        'AORTIC', 'MITRAL', 'TRICUSPID', 'PULMONARY VALVE',
        
        # GI/Urology surgical
        'SPHINCTER', 'CONTINENCE', 'BLADDER', 'URETHRAL SLING',
        'PENILE PROSTHESIS', 'TESTICULAR',
        
        # ENT surgical
        'COCHLEAR IMPLANT', 'OSSICULAR', 'TYMPANIC',
        
        # OB/GYN surgical
        'INTRAUTERINE', 'IUD', 'CONTRACEPTIVE IMPLANT', 'FALLOPIAN'
    ]
    
    for keyword in surgical_keywords:
        if keyword in text:
            return True
    
    # --- Panel-based heuristics ---
    
    panel = row.get('advisory_panel', '')
    
    # Orthopedic: Most are surgical (except stimulators already excluded)
    if panel == 'Orthopedic':
        return True
    
    # General, Plastic Surgery: Most are surgical
    if panel == 'General, Plastic Surgery':
        return True
    
    # Gastroenterology, Urology: Check for surgical keywords
    if panel == 'Gastroenterology, Urology':
        # Many GI/Uro devices are diagnostic (scopes, etc.)
        # Only include if has surgical keywords
        return any(kw in text for kw in ['SPHINCTER', 'SLING', 'PROSTHESIS', 'IMPLANT'])
    
    # Cardiovascular: Very mixed - default to False unless surgical keyword matched above
    if panel == 'Cardiovascular':
        return False  # Already checked for valves above
    
    # Ophthalmic: Mostly non-surgical (lenses, lasers)
    if panel == 'Ophthalmic':
        # Only IOLs are surgical
        return 'INTRAOCULAR' in text or 'IOL' in text
    
    # Neurology: Mostly stimulators (excluded above)
    if panel == 'Neurology':
        return False
    
    # Dental: Generally not "surgical" in medical device sense
    if panel == 'Dental':
        return False
    
    # OB/GYN: Mixed
    if panel == 'Obstetrics/Gynecology':
        return any(kw in text for kw in ['IMPLANT', 'IUD', 'INTRAUTERINE'])
    
    # ENT: Check for implants
    if panel == 'Ear, Nose, Throat':
        return 'COCHLEAR' in text or 'IMPLANT' in text
    
    # Default: Not surgical
    return False


if __name__ == "__main__":
    # Load devices
    input_path = config.PROCESSED_DIR / "devices.csv"
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        sys.exit(1)
        
    df = pd.read_csv(input_path)
    
    print(f"Total devices: {len(df)}")
    
    # Apply filter
    df['is_surgical'] = df.apply(is_surgical_device, axis=1)
    
    # Statistics
    surgical_count = df['is_surgical'].sum()
    print(f"\nSurgical devices: {surgical_count} ({surgical_count/len(df)*100:.1f}%)")
    print(f"Non-surgical devices: {len(df) - surgical_count} ({(len(df)-surgical_count)/len(df)*100:.1f}%)")
    
    print("\n=== Breakdown by Panel ===")
    breakdown = df.groupby('advisory_panel')['is_surgical'].agg(['sum', 'count'])
    breakdown['pct'] = (breakdown['sum'] / breakdown['count'] * 100).round(1)
    breakdown.columns = ['Surgical', 'Total', 'Pct_Surgical']
    print(breakdown.sort_values('Surgical', ascending=False))
    
    # Save updated devices.csv with flag
    df.to_csv(input_path, index=False)
    print(f"\n✅ Updated devices.csv with 'is_surgical' flag")
    
    # Save surgical-only subset
    surgical_out_path = config.PROCESSED_DIR / "devices_surgical.csv"
    surgical_df = df[df['is_surgical']].copy()
    surgical_df.to_csv(surgical_out_path, index=False)
    print(f"✅ Created devices_surgical.csv ({len(surgical_df)} devices)")
    
    # Show sample surgical devices
    print("\n=== Sample Surgical Devices ===")
    for panel in surgical_df['advisory_panel'].unique()[:5]:
        print(f"\n{panel}:")
        samples = surgical_df[surgical_df['advisory_panel']==panel]['trade_name'].head(5).tolist()
        for s in samples:
            print(f"  - {s}")
