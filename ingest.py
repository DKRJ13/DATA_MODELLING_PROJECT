"""
STEP 3 (SNOMED + Owlready2): XML → RDF Ingestion & Automated Reasoning
====================================================================
Architecture:
  - ontology_A.ttl    = Hospital A's local schema (EHR)
  - ontology_B.ttl    = Hospital B's local schema (Clinical)
  - snomed_core.ttl   = SNOMED CT subset (Global Standard)
  - snomed_mapping.ttl= Integration rules & OWL reasoning logic

What this script does:
  1. Uses rdflib to parse the XML files and map them to SNOMED codes.
  2. Saves a RAW un-reasoned graph.
  3. Uses owlready2 (and its built-in HermiT reasoner) to automatically 
     infer interactions based purely on the OWL files, without manual logic!
"""

import xml.etree.ElementTree as ET
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from pathlib import Path
import re
from owlready2 import get_ontology, sync_reasoner

# ─────────────────────────────────────────────────────────────
#  SETUP: Paths and Namespaces
# ─────────────────────────────────────────────────────────────

BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
ONTO_DIR   = BASE_DIR / "ontology"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Vocabularies
EHR  = Namespace("http://hospital-a.org/ehr#")
CLIN = Namespace("http://hospital-b.org/clinical#")
SCT  = Namespace("http://snomed.info/id/")

# Patient Instance Namespaces
HOSP_A_INST = Namespace("http://hospital-a.org/patient#")
HOSP_B_INST = Namespace("http://hospital-b.org/patient#")


# ─────────────────────────────────────────────────────────────
#  DRUG/DISEASE LOOKUP TABLES (Mapping to Local Local URIs)
#  (The snomed_mapping.ttl file links these to SNOMED codes)
# ─────────────────────────────────────────────────────────────

DRUG_MAP_A = {
    "warfarin": EHR.Warfarin, "metformin": EHR.Metformin, "aspirin": EHR.Aspirin,
    "ibuprofen": EHR.Ibuprofen, "lisinopril": EHR.Lisinopril, "salbutamol": EHR.Salbutamol,
}
DISEASE_MAP_A = {
    "diabetes type 2": EHR.DiabetesType2, "hypertension": EHR.Hypertension,
    "chronic kidney disease": EHR.ChronicKidneyDisease, "asthma": EHR.Asthma,
    "huntington's chorea (disorder)": EHR.Huntingtons,
}

DRUG_MAP_B = {
    "metformin hydrochloride": CLIN.MetforminHydrochloride, "acetylsalicylic acid": CLIN.AcetylsalicylicAcid,
    "ibuprofen": CLIN.Ibuprofen, "lisinopril": CLIN.Lisinopril,
    "salbutamol sulfate": CLIN.SalbutamolSulfate, "amlodipine": CLIN.Amlodipine,
}
DISEASE_MAP_B = {
    "e11": CLIN.AdultOnsetDiabetes, "i10": CLIN.EssentialHypertension,
    "n18": CLIN.ChronicRenalFailure, "j45": CLIN.BronchialAsthma,
    "g10": CLIN.HuntingtonsDisease,
}
FOOD_MAP_B = {
    "grapefruit": CLIN.Grapefruit, "grapefruit juice": CLIN.GrapefruitJuice,
}


def normalize(text: str) -> str: return text.strip().lower()
def safe_uri(name: str) -> str: return re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())

# ─────────────────────────────────────────────────────────────
#  PHASE 1: Raw Ingestion (Using RDFlib)
# ─────────────────────────────────────────────────────────────

def build_raw_graph():
    """Parses XML and loads the ontologies to build the baseline triples."""
    g = Graph()
    
    # Load all 4 ontologies
    print("[1/4] Loading Ontologies into RDFlib...")
    files = ["ontology_A.ttl", "ontology_B.ttl", "snomed_core.ttl", "snomed_mapping.ttl"]
    for f in files:
        g.parse(str(ONTO_DIR / f), format="turtle")

    patient_index_A = {}

    # Ingest Hospital A
    print("[2/4] Parsing Hospital A XML...")
    tree = ET.parse(DATA_DIR / "hospital_A.xml")
    for record in tree.getroot().findall("EHR_Record"):
        pid = record.get("id")
        full_name = record.findtext("FullName", "").strip()
        patient_uri = HOSP_A_INST[safe_uri(pid)]

        g.add((patient_uri, RDF.type, EHR.EHR_Record))
        g.add((patient_uri, EHR.FullName, Literal(full_name)))

        for cond in record.findall("Condition"):
            uri = DISEASE_MAP_A.get(normalize(cond.text))
            if uri: g.add((patient_uri, EHR.hasCondition, uri))

        for gcond in record.findall("GeneticCondition"):
            uri = DISEASE_MAP_A.get(normalize(gcond.text))
            if uri: g.add((patient_uri, EHR.hasGeneticCondition, uri))

        for parent in record.findall("ParentID"):
            p_uri = HOSP_A_INST[safe_uri(parent.text)]
            g.add((patient_uri, EHR.hasParent, p_uri))

        for rx in record.findall("Prescription"):
            uri = DRUG_MAP_A.get(normalize(rx.findtext("DrugName", "")))
            if uri: g.add((patient_uri, EHR.hasPrescription, uri))

        patient_index_A[normalize(full_name)] = patient_uri

    # Ingest Hospital B
    print("[3/4] Parsing Hospital B XML...")
    tree = ET.parse(DATA_DIR / "hospital_B.xml")
    for record in tree.getroot().findall("ClinicalRecord"):
        ref = record.get("ref")
        name_raw = record.findtext("Patient_Name", "").strip()
        dob = record.findtext("DOB", "").strip()
        sex = record.findtext("Sex", "").strip()
        bmi = record.findtext("BMI", "").strip()
        
        parts = [p.strip() for p in name_raw.split(",")]
        full_name = f"{parts[1]} {parts[0]}" if "," in name_raw else name_raw
        
        patient_uri = HOSP_B_INST[safe_uri(ref)]
        g.add((patient_uri, RDF.type, CLIN.ClinicalSubject))
        g.add((patient_uri, CLIN.Subject_Ref, Literal(ref)))
        g.add((patient_uri, CLIN.Patient_Name, Literal(full_name)))
        g.add((patient_uri, CLIN.DOB, Literal(dob)))
        g.add((patient_uri, CLIN.Sex, Literal(sex)))
        
        if bmi:
            g.add((patient_uri, CLIN.BMI, Literal(float(bmi), datatype=XSD.float)))

        # Entity Resolution via owl:sameAs
        norm_name = normalize(full_name)
        if norm_name in patient_index_A:
            g.add((patient_uri, OWL.sameAs, patient_index_A[norm_name]))

        for diag in record.findall("Diagnosis"):
            uri = DISEASE_MAP_B.get(diag.get("code", "").lower())
            if uri: g.add((patient_uri, CLIN.hasDiagnosis, uri))

        for gdiag in record.findall("GeneticDiagnosis"):
            uri = DISEASE_MAP_B.get(gdiag.get("code", "").lower())
            if uri: g.add((patient_uri, CLIN.hasGeneticDiagnosis, uri))

        for parent in record.findall("BiologicalParent"):
            p_uri = HOSP_B_INST[safe_uri(parent.text)]
            g.add((patient_uri, CLIN.hasBiologicalParent, p_uri))

        for med in record.findall("Medication"):
            uri = DRUG_MAP_B.get(normalize(med.findtext("GenericName", "")))
            if uri: g.add((patient_uri, CLIN.onMedication, uri))

        for food in record.findall("NutritionLog"):
            uri = FOOD_MAP_B.get(normalize(food.findtext("FoodItem", "")))
            if uri: g.add((patient_uri, CLIN.hasNutritionEntry, uri))

        officer = record.findtext("ClinicalOfficer", "").strip()
        if officer:
            if "," in officer:
                parts = officer.split(",")
                phys_name = f"Dr. {parts[1].replace(' MD','').strip()} {parts[0].strip()}"
            else:
                phys_name = officer
            doctor_uri = CLIN[safe_uri(phys_name)]
            g.add((doctor_uri, RDF.type, CLIN.ClinicalOfficer))
            g.add((patient_uri, CLIN.underCareOf, doctor_uri))
            
            for peer in record.findall("DoctorConsultsWith"):
                p_name = peer.text.strip()
                if "," in p_name:
                    p_parts = p_name.split(",")
                    p_name = f"Dr. {p_parts[1].replace(' MD','').strip()} {p_parts[0].strip()}"
                peer_uri = CLIN[safe_uri(p_name)]
                g.add((doctor_uri, CLIN.consultsWith, peer_uri))
                
        for friend in record.findall("FriendOfPatient"):
            friend_uri = HOSP_B_INST[safe_uri(friend.text.strip())]
            g.add((friend_uri, RDF.type, CLIN.ClinicalSubject))
            g.add((patient_uri, CLIN.knowsPatient, friend_uri))

    # Remove owl:imports because all triples are already merged in this graph
    # (owlready2 will try to download the fake URLs from the internet otherwise)
    g.remove((None, OWL.imports, None))

    # Save to a temporary raw file (Owlready2 prefers RDF/XML format)
    raw_path = OUTPUT_DIR / "merged_raw.owl"
    g.serialize(destination=str(raw_path), format="xml")
    print(f"      → Saved raw graph: {len(g)} triples.")
    return raw_path


# ─────────────────────────────────────────────────────────────
#  PHASE 2: Automated Reasoning (Using Owlready2 / HermiT)
# ─────────────────────────────────────────────────────────────

def run_reasoner(raw_path: Path):
    """Loads the raw graph into Owlready2 and runs the HermiT Java Reasoner."""
    print("\n[4/4] Starting Owlready2 Automated Reasoner...")
    print("      (This uses HermiT to evaluate the SNOMED rules logically)")

    # Owlready2 needs a clean slate or specifically formatted URIs
    # Load the ontology we just wrote
    onto = get_ontology(f"file://{raw_path}").load()

    # THE MAGIC HAPPENS HERE:
    # We do NOT write any custom SPARQL for interaction alerts.
    # HermiT reads snomed_mapping.ttl and executes the math automatically.
    with onto:
        # sync_reasoner() automatically infers all subclasses and equivalent classes
        sync_reasoner(infer_property_values=True)

    reasoned_path = OUTPUT_DIR / "merged_reasoned.owl"
    onto.save(file=str(reasoned_path), format="rdfxml")
    print(f"      → Reasoning complete! Result saved globally to {reasoned_path.name}")
    return reasoned_path


def main():
    print("=" * 60)
    print("  SNOMED CT Integration & Automated Reasoning Pipeline")
    print("=" * 60)

    # 1. Parse XML and ontologies into raw triples
    raw_path = build_raw_graph()

    # 2. Let the machine deduce the clinical interactions
    # (Requires Java installed for HermiT)
    reasoned_path = run_reasoner(raw_path)

    print("=" * 60)
    print(f"✅ Success! You can now query {reasoned_path.name} with SPARQL.")

if __name__ == "__main__":
    main()
