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
    response = requests.post(TOKEN_URL, params=params, data=data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Authentification réussie !")
        return response.json()["access_token"]
    else:
        print(f"❌ Erreur d'authentification ({response.status_code}): {response.text}")
        return None

def search_offers(token, keyword, max_results=50):
    """Rechercher des offres par mot-clé"""
    url = f"{API_BASE_URL}/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    all_offers = []
    range_start = 0
    
    print(f"🔍 Recherche des offres pour le mot-clé: '{keyword}'")

    while range_start < max_results:
        params = {
            "motsCles": keyword,
            "range": f"{range_start}-{range_start + 9}",
            "rome": "M18"  # Domaine informatique
        }
        response = requests.get(url, headers=headers, params=params)
        print(f"  ➜ Requête {range_start}-{range_start+9}: {response.status_code}")
        
        if response.status_code in [200, 206]:
            data = response.json()
            offers = data.get("resultats", [])
            if not offers:
                break
            for offer in offers:
                offer["metier_recherche"] = keyword
            all_offers.extend(offers)
            if len(all_offers) >= max_results:
                break
            range_start += 10
        else:
            print(f"❌ Erreur API: {response.status_code}")
            break
    return all_offers[:max_results]

# ============================================================== 
#  Programme principal 
# ============================================================== 

def main():
    print("DÉMARRAGE DE LA COLLECTE DES OFFRES (brutes)")

    # 1️⃣ Authentification
    token = get_token()
    if not token:
        return

    # 2️⃣ Liste des métiers IT à rechercher
    metiers_it = [
        "développeur", "développeur fullstack", "développeur backend", "développeur frontend",
        "développeur mobile", "développeur web", "ingénieur logiciel", "ingénieur informatique",
        "data scientist", "data analyst", "analyste données", "ingénieur data", "data engineer",
        "machine learning", "deep learning", "intelligence artificielle", "analyste big data",
        "architecte data", "scientifique des données",
        "administrateur système", "administrateur réseau", "devops", "ingénieur devops",
        "cloud engineer", "ingénieur cloud", "spécialiste cloud", "architecte cloud",
        "administrateur cloud",
        "cybersécurité", "analyste sécurité", "ingénieur sécurité", "responsable sécurité informatique",
        "ethical hacker", "pentester",
        "webmaster", "designer UX/UI", "intégrateur web", "développeur javascript",
        "développeur python", "développeur java", "développeur c#", "développeur php",
        "administrateur base de données", "DBA", "ingénieur systèmes", "technicien informatique",
        "support technique", "helpdesk",
        "chef de projet informatique", "consultant informatique", "product owner", "scrum master",
        "analyste fonctionnel", "testeur QA", "ingénieur qualité logiciel"
    ]

    # 3️⃣ Collecte brute
    all_offers = []
    for metier in metiers_it:
        offers = search_offers(token, metier, max_results=50)
        if offers:
            all_offers.extend(offers)
            print(f"✅ {len(offers)} offres collectées pour '{metier}'")
        else:
            print(f"⚠ Aucune offre trouvée pour '{metier}'")

    # 4️⃣ Sauvegarde brute
    if all_offers:
        os.makedirs('data/raw', exist_ok=True)  # Créer le dossier si nécessaire

        json_path = 'data/raw/offres_it_brutes.json'
        csv_path = 'data/raw/offres_it_brutes.csv'

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=2)

        df = pd.DataFrame(all_offers)
        df.to_csv(csv_path, index=False, encoding='utf-8')

        # Métadonnées de collecte
        metadata = {
            "date_collecte": datetime.now().isoformat(),
            "total_offres": len(df),
            "metiers_recherches": metiers_it
        }
        with open('data/raw/metadata_collecte.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print("\n💾 Données brutes sauvegardées:")
        print(f"   - {json_path}")
        print(f"   - {csv_path}")
        print("   - data/raw/metadata_collecte.json")
    else:
        print("❌ Aucune offre collectée.")

if __name__ == "__main__":
    main()
