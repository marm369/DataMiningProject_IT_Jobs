import os
import requests
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# ============================================================== 
#  Chargement des identifiants depuis le fichier .env  
# ============================================================== 
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SCOPE = os.getenv("SCOPE", "api_offresdemploiv2 o2dsoffre")

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
API_BASE_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2"

# ============================================================== 
#  Fonctions utilitaires 
# ============================================================== 

def get_token():
    """Obtenir le token d'accès OAuth2"""
    params = {"realm": "/partenaire"}
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    print("🔐 Authentification en cours...")
    try:
        response = requests.post(TOKEN_URL, params=params, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(" Authentification réussie !")
            return response.json()["access_token"]
        else:
            print(f" Erreur d'authentification ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f" Erreur de connexion: {e}")
        return None

def get_single_offer_sample(token):
    """Récupérer une seule offre pour analyser la structure"""
    url = f"{API_BASE_URL}/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "="*60)
    print(" TENTATIVE DE RÉCUPÉRATION D'UNE OFFRE POUR ANALYSE")
    print("="*60)
    
    # Essayer avec différents paramètres
    test_params = [
        {"motsCles": "développeur", "range": "0-1"},
        {"motsCles": "informatique", "range": "0-1"},
        {"range": "0-1"},  # Sans mot-clé
    ]
    
    for i, params in enumerate(test_params, 1):
        print(f"\n Essai {i}/3 avec params: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f" Statut HTTP: {response.status_code}")
            
            # Le code 206 est NORMAL pour l'API France Travail (contenu partiel)
            if response.status_code in [200, 206]:
                data = response.json()
                offers = data.get("resultats", [])
                
                if offers:
                    print(f" SUCCÈS! {len(offers)} offre(s) récupérée(s)")
                    return offers[0]  # Retourner la première offre
                else:
                    print(" Aucune offre dans la réponse")
                    print(f" Contenu de la réponse: {data}")
            else:
                print(f" Erreur API: {response.status_code}")
                print(f" Réponse: {response.text[:200]}...")
                
        except Exception as e:
            print(f" Erreur lors de la requête: {e}")
    
    return None

def analyze_offer_structure(offer):
    """Analyser la structure d'une offre"""
    print("\n" + "="*60)
    print("ANALYSE DE LA STRUCTURE D'UNE OFFRE")
    print("="*60)
    
    if not offer:
        print("Aucune offre à analyser")
        return
    
    all_keys = set()
    nested_structures = {}
    
    def extract_keys(obj, prefix="", depth=0):
        if depth > 3:  # Limite de profondeur
            return
            
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                all_keys.add(full_key)
                
                if isinstance(value, (dict, list)):
                    if full_key not in nested_structures:
                        nested_structures[full_key] = set()
                    
                    if isinstance(value, dict):
                        extract_keys(value, full_key, depth + 1)
                        nested_structures[full_key].add("object")
                    elif isinstance(value, list) and value:
                        if isinstance(value[0], dict):
                            extract_keys(value[0], full_key, depth + 1)
                            nested_structures[full_key].add(f"array[object]")
                        else:
                            nested_structures[full_key].add(f"array[{type(value[0]).__name__}]")
                else:
                    nested_structures[full_key] = type(value).__name__
    
    extract_keys(offer)
    
    # Afficher les colonnes principales
    print("\n COLONNES PRINCIPALES DISPONIBLES:")
    print("-" * 40)
    base_keys = [k for k in sorted(all_keys) if '.' not in k]
    for key in base_keys:
        value_type = nested_structures.get(key, "unknown")
        sample_value = str(offer.get(key, ""))[:50] + "..." if len(str(offer.get(key, ""))) > 50 else offer.get(key, "")
        print(f"  - {key}: {value_type}")
        print(f"    Exemple: {sample_value}")
    
    # Afficher les objets imbriqués
    print("\n STRUCTURES IMBRIQUÉES:")
    print("-" * 40)
    nested_keys = [k for k in sorted(all_keys) if '.' in k]
    for key in nested_keys[:20]:  # Limiter l'affichage
        value_type = nested_structures.get(key, "unknown")
        print(f"  - {key}: {value_type}")
    
    if len(nested_keys) > 20:
        print(f"  ... et {len(nested_keys) - 20} autres colonnes imbriquées")
    
    return all_keys, nested_structures

def save_analysis_results(offer, all_keys, nested_structures):
    """Sauvegarder les résultats de l'analyse"""
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, "data", "api_analysis")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Sauvegarder l'exemple complet
    example_path = os.path.join(DATA_DIR, 'exemple_offre_complete.json')
    with open(example_path, 'w', encoding='utf-8') as f:
        json.dump(offer, f, ensure_ascii=False, indent=2)
    
    # Sauvegarder la liste des colonnes
    structure_path = os.path.join(DATA_DIR, 'structure_colonnes_detaille.json')
    structure_data = {
        "date_analyse": datetime.now().isoformat(),
        "total_colonnes": len(all_keys),
        "colonnes_principales": sorted([k for k in all_keys if '.' not in k]),
        "colonnes_imbriquees": sorted([k for k in all_keys if '.' in k]),
        "types_colonnes": {k: str(v) for k, v in nested_structures.items()},
        "exemple_valeurs": {k: str(offer.get(k, ""))[:100] for k in all_keys if '.' not in k and k in offer}
    }
    
    with open(structure_path, 'w', encoding='utf-8') as f:
        json.dump(structure_data, f, ensure_ascii=False, indent=2)
    
    # Sauvegarder en CSV pour Excel
    csv_data = []
    for key in sorted(all_keys):
        csv_data.append({
            "colonne": key,
            "type": str(nested_structures.get(key, "unknown")),
            "niveau": "principal" if '.' not in key else "imbriqué"
        })
    
    csv_path = os.path.join(DATA_DIR, 'liste_colonnes.csv')
    df = pd.DataFrame(csv_data)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"\n RÉSULTATS SAUVEGARDÉS:")
    print(f"  - {example_path}")
    print(f"  - {structure_path}")
    print(f"  - {csv_path}")

def display_statistics(all_keys, nested_structures):
    """Afficher les statistiques de la structure"""
    print("\n" + "="*60)
    print(" STATISTIQUES DE LA STRUCTURE")
    print("="*60)
    
    base_keys = [k for k in all_keys if '.' not in k]
    nested_keys = [k for k in all_keys if '.' in k]
    
    print(f" COLONNES TOTALES: {len(all_keys)}")
    print(f"  - Principales: {len(base_keys)}")
    print(f"  - Imbriquées: {len(nested_keys)}")
    
    # Analyser les types de données
    type_count = {}
    for key, type_info in nested_structures.items():
        type_str = str(type_info)
        type_count[type_str] = type_count.get(type_str, 0) + 1
    
    print(f"\n RÉPARTITION DES TYPES:")
    for type_name, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {type_name}: {count} colonnes")
    
    # Afficher les colonnes les plus importantes
    important_columns = ['id', 'intitule', 'description', 'entreprise', 'lieuTravail', 'salaire', 'typeContrat', 'dureeTravailLibelle']
    print(f"\n COLONNES IMPORTANTES TROUVÉES:")
    for col in important_columns:
        found = any(col in key for key in all_keys)
        status = "✅" if found else "❌"
        print(f"  {status} {col}")

# ============================================================== 
#  Programme principal 
# ============================================================== 

def main():
    print("DÉMARRAGE DE L'ANALYSE DE LA STRUCTURE DE L'API")
    
    # 1️⃣ Authentification
    token = get_token()
    if not token:
        print(" Arrêt du programme - Token non obtenu")
        return

    # 2️⃣ Récupérer un échantillon d'offre
    offer_sample = get_single_offer_sample(token)
    
    if offer_sample:
        # 3️⃣ Analyser la structure
        all_keys, nested_structures = analyze_offer_structure(offer_sample)
        
        # 4️⃣ Sauvegarder les résultats
        save_analysis_results(offer_sample, all_keys, nested_structures)
        
        # 5️⃣ Afficher les statistiques
        display_statistics(all_keys, nested_structures)
        
        print("\n" + "="*60)
        print(" ANALYSE RÉUSSIE!")
        print("="*60)
        print(" Les fichiers ont été sauvegardés dans data/api_analysis/")
        print(" Vous pouvez maintenant voir toutes les colonnes disponibles")
    else:
        print("\n IMPOSSIBLE DE RÉCUPÉRER UN ÉCHANTILLON")
        print(" Suggestions:")
        print("  - Vérifiez votre connexion Internet")
        print("  - Vérifiez que vos identifiants API sont valides")
        print("  - Essayez avec d'autres paramètres de recherche")

if __name__ == "__main__":
    main()