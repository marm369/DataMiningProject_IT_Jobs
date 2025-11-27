import os
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
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

def search_offers(token, keyword, max_results=150):
    """Rechercher des offres par mot-clé avec gestion des erreurs améliorée"""
    url = f"{API_BASE_URL}/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    all_offers = []
    range_start = 0
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    print(f"🔍 Recherche des offres pour le mot-clé: '{keyword}'")

    while range_start < max_results and consecutive_errors < max_consecutive_errors:
        params = {
            "motsCles": keyword,
            "range": f"{range_start}-{range_start + 9}",
            "rome": "M18"  # Domaine informatique
        }
        
        try:
            # Ajout d'un timeout pour éviter les blocages
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"  ➜ Requête {range_start}-{range_start+9}: {response.status_code}")
            
            if response.status_code in [200, 206]:
                data = response.json()
                offers = data.get("resultats", [])
                if not offers:
                    print(f"  ➤ Plus d'offres disponibles pour '{keyword}'")
                    break
                
                for offer in offers:
                    offer["metier_recherche"] = keyword
                all_offers.extend(offers)
                
                # Réinitialiser le compteur d'erreurs en cas de succès
                consecutive_errors = 0
                
                if len(all_offers) >= max_results:
                    break
                range_start += 10
                
                # Pause entre les requêtes pour éviter le rate limiting
                time.sleep(1)
                
            elif response.status_code == 429:  # Too Many Requests
                print("  Rate limiting détecté, pause de 30 secondes...")
                time.sleep(30)
                consecutive_errors += 1
                
            else:
                print(f" Erreur API: {response.status_code}")
                consecutive_errors += 1
                # Pause plus longue en cas d'erreur
                time.sleep(5)
                
        except requests.exceptions.Timeout:
            print("  Timeout de la requête, nouvelle tentative...")
            consecutive_errors += 1
            time.sleep(5)
            
        except requests.exceptions.ConnectionError as e:
            print(f"  Erreur de connexion: {e}")
            consecutive_errors += 1
            print("  Pause de 10 secondes avant nouvelle tentative...")
            time.sleep(10)
            
        except Exception as e:
            print(f"  Erreur inattendue: {e}")
            consecutive_errors += 1
            time.sleep(5)
    
    if consecutive_errors >= max_consecutive_errors:
        print(f"  Arrêt après {max_consecutive_errors} erreurs consécutives")
    
    return all_offers[:max_results]

def extract_teletravail(description, deplacement_libelle):
    """Détecter la possibilité de télétravail"""
    if not description:
        description = ""
    if not deplacement_libelle:
        deplacement_libelle = ""
    
    text_to_search = (description + " " + deplacement_libelle).lower()
    
    teletravail_keywords = ['télétravail', 'teletravail', 'remote', 'télé travail', 'home office', 'travail à distance']
    for keyword in teletravail_keywords:
        if keyword in text_to_search:
            return "Oui"
    return "Non"

def extract_seniorite(qualification_libelle, experience_libelle):
    """Extraire le niveau de séniorité"""
    if experience_libelle:
        experience_lower = experience_libelle.lower()
        if "débutant" in experience_lower or "junior" in experience_lower:
            return "Junior"
        elif "expérimenté" in experience_lower or "confirmé" in experience_lower:
            return "Confirmé"
        elif "senior" in experience_lower:
            return "Senior"
    
    if qualification_libelle:
        qualification_lower = qualification_libelle.lower()
        if "cadre" in qualification_lower:
            return "Senior"
        elif "technicien" in qualification_lower or "technique" in qualification_lower:
            return "Confirmé"
    
    return "Non spécifié"

def extract_competences(description):
    """Extraire les compétences techniques de la description"""
    if not description:
        return []
    
    competences_techniques = [
        'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin',
        'scala', 'r', 'matlab', 'perl', 'dart',
        'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind', 'jquery',
        'react', 'angular', 'vue', 'ember', 'svelte',
        'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'symfony', 'ruby on rails',
        'asp.net', 'nestjs', 'fastapi',
        'sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite', 'mongodb', 'redis',
        'cassandra', 'elasticsearch', 'kibana', 'mariaDB', 'dynamodb', 'firebase',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'heroku', 'digital ocean', 'terraform',
        'ansible', 'jenkins', 'gitlab', 'github actions', 'circleci',
        'git', 'linux', 'windows', 'macos', 'bash', 'powershell', 'vim', 'vscode',
        'agile', 'scrum', 'kanban', 'jira', 'confluence', 'ci/cd', 'tdd', 'bdd',
        'rest api', 'graphql', 'soap', 'microservices', 'serverless', 'lambda',
        'machine learning', 'deep learning', 'ai', 'artificial intelligence',
        'data science', 'big data', 'hadoop', 'spark', 'kafka', 'tableau', 'power bi',
        'computer vision', 'nlp', 'natural language processing',
        'cybersecurity', 'cryptography', 'penetration testing', 'ethical hacking',
        'owasp', 'vpn', 'firewall',
        'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic',
        'blockchain', 'iot', 'ar/vr', 'augmented reality', 'virtual reality'
    ]
    
    competences_trouvees = []
    desc_lower = description.lower()
    for competence in competences_techniques:
        if competence in desc_lower:
            competences_trouvees.append(competence)
    
    return competences_trouvees

def filter_offers_by_period(offers, days_back=120):
    """Filtrer les offres par période"""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    filtered_offers = []
    
    for offer in offers:
        date_creation = offer.get("dateCreation")
        if date_creation:
            try:
                # Convertir la date de l'API en objet datetime
                offer_date = datetime.fromisoformat(date_creation.replace('Z', '+00:00'))
                if offer_date >= cutoff_date:
                    filtered_offers.append(offer)
            except:
                # Si la conversion échoue, garder l'offre par défaut
                filtered_offers.append(offer)
        else:
            # Si pas de date, garder l'offre
            filtered_offers.append(offer)
    
    return filtered_offers

def transform_to_target_columns(offers):
    """Transformer les données brutes en colonnes cibles"""
    transformed_offers = []
    
    for offer in offers:
        transformed_offer = {
            # Informations de base
            "intitule_poste": offer.get("intitule", ""),
            "nom_entreprise": offer.get("entreprise", {}).get("nom", ""),
            "ville_region": offer.get("lieuTravail", {}).get("libelle", ""),
            "date_publication": offer.get("dateCreation", ""),
            "type_contrat": offer.get("typeContratLibelle", ""),
            
            # Expérience et séniorité
            "experience_demandee": offer.get("experienceLibelle", ""),
            "niveau_seniorite": extract_seniorite(
                offer.get("qualificationLibelle", ""),
                offer.get("experienceLibelle", "")
            ),
            
            # Description et source
            "description_poste": offer.get("description", ""),
            "source_offre": offer.get("origineOffre", {}).get("urlOrigine", ""),
            
            # Télétravail
            "teletravail": extract_teletravail(
                offer.get("description", ""),
                offer.get("deplacementLibelle", "")
            ),
            
            # Compétences
            "competences_mentionnees": extract_competences(offer.get("description", "")),
            
            # Salaire
            "fourchette_salaire": offer.get("salaire", {}).get("libelle", ""),
            
            # Métadonnées
            "metier_recherche": offer.get("metier_recherche", ""),
            "id_offre": offer.get("id", "")
        }
        transformed_offers.append(transformed_offer)
    
    return transformed_offers

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

    # 3️⃣ Collecte brute avec gestion des erreurs améliorée
    all_offers = []
    comptage_par_metier = {}
    
    print(f" Recherche sur {len(metiers_it)} métiers IT\n")
    
    for i, metier in enumerate(metiers_it, 1):
        print(f"[{i}/{len(metiers_it)}] ", end="")
        offers = search_offers(token, metier, max_results=150)
        if offers:
            all_offers.extend(offers)
            comptage_par_metier[metier] = len(offers)
            print(f"✅ {len(offers)} offres collectées pour '{metier}'")
        else:
            comptage_par_metier[metier] = 0
            print(f" Aucune offre trouvée pour '{metier}'")
        
        # Pause entre les métiers pour éviter le rate limiting
        if i < len(metiers_it):  # Pas de pause après le dernier métier
            print("   Pause de 3 secondes entre les métiers...")
            time.sleep(3)

    # 4️⃣ POST-TRAITEMENT : Filtrer et transformer les données
    print("\n🔄 Post-traitement des données...")
    
    # Filtrer par période (120 jours)
    offers_120_days = filter_offers_by_period(all_offers, days_back=120)
    
    # Compter par métier après filtrage
    comptage_120_jours = {}
    for offer in offers_120_days:
        metier = offer.get("metier_recherche")
        comptage_120_jours[metier] = comptage_120_jours.get(metier, 0) + 1
    
    print(f" Offres des 120 derniers jours: {len(offers_120_days)}/{len(all_offers)}")
    
    # Transformer en colonnes cibles
    transformed_offers = transform_to_target_columns(offers_120_days)
    print(f" Données transformées: {len(transformed_offers)} offres")

    # 5️⃣ Sauvegarde des données brutes ET transformées
    if all_offers:
        # Détecter le répertoire racine du projet
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Dossiers à la racine du projet
        DATA_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
        DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
        os.makedirs(DATA_RAW_DIR, exist_ok=True)
        os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
        
        # === SAUVEGARDE BRUTE (votre format original) ===
        json_path_brut = os.path.join(DATA_RAW_DIR, 'offres_it_brutes_france_travail.json')
        csv_path_brut = os.path.join(DATA_RAW_DIR, 'offres_it_brutes_france_travail.csv')

        with open(json_path_brut, 'w', encoding='utf-8') as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=2)

        df_brut = pd.DataFrame(all_offers)
        df_brut.to_csv(csv_path_brut, index=False, encoding='utf-8')

        # Métadonnées de collecte
        metadata = {
            "date_collecte": datetime.now().isoformat(),
            "total_offres_brutes": len(all_offers),
            "total_offres_120_jours": len(offers_120_days),
            "metiers_recherches": metiers_it,
            "comptage_par_metier_brut": comptage_par_metier,
            "comptage_par_metier_120_jours": comptage_120_jours
        }
        
        meta_path = os.path.join(DATA_RAW_DIR, 'metadata_collecte.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # === SAUVEGARDE TRANSFORMÉE (vos colonnes cibles) ===
        json_path_cible = os.path.join(DATA_PROCESSED_DIR, 'offres_it_ciblees_france_travail.json')
        csv_path_cible = os.path.join(DATA_PROCESSED_DIR, 'offres_it_ciblees_france_travail.csv')

        with open(json_path_cible, 'w', encoding='utf-8') as f:
            json.dump(transformed_offers, f, ensure_ascii=False, indent=2)

        # Sauvegarde CSV - avec traitement pour les compétences
        df_cible = pd.DataFrame(transformed_offers)
        df_cible['competences_mentionnees'] = df_cible['competences_mentionnees'].apply(lambda x: ', '.join(x) if x else '')
        df_cible.to_csv(csv_path_cible, index=False, encoding='utf-8')

        print("\n" + "="*60)
        print(" DONNÉES SAUVEGARDÉES")
        print("="*60)
        print(f" DONNÉES BRUTES ({DATA_RAW_DIR}):")
        print(f"   - {json_path_brut}")
        print(f"   - {csv_path_brut}")
        print(f"   - {meta_path}")
        
        print(f"\n DONNÉES CIBLÉES ({DATA_PROCESSED_DIR}):")
        print(f"   - {json_path_cible}")
        print(f"   - {csv_path_cible}")
        
        print(f"\n STATISTIQUES:")
        print(f"   - Total brut: {len(all_offers)} offres")
        print(f"   - 120 derniers jours: {len(offers_120_days)} offres")
        print(f"   - Colonnes cibles: {len(transformed_offers[0].keys()) if transformed_offers else 0}")
    else:
        print(" Aucune offre collectée.")

if __name__ == "__main__":
    main()