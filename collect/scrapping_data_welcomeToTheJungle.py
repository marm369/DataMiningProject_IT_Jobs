from bs4 import BeautifulSoup
import requests
import json
import re
from datetime import datetime
import os
import time
from collections import Counter

# Configuration des chemins
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)

def get_wttj_job_details(link):
    """Récupère les détails d'une offre Welcome to the Jungle"""
    try:
        page = requests.get(link)
        soup = BeautifulSoup(page.text, "lxml")
        
        # Entreprise
        try:
            company = soup.find('h3', attrs={'class': "sc-12bzhsi-11 jhkNVT"}).string
        except:
            company = "Non spécifié"
        
        # Titre du poste
        try:
            title = soup.find('h1', attrs={'class': "sc-12bzhsi-3 kuNRyl"}).string
        except:
            title = "Non spécifié"
        
        # Localisation
        try:
            lieu = soup.find('span', attrs={'class': "sc-16yjgsd-3 cToOtz"}).string
        except:
            lieu = "Non spécifié"
        
        # Type de contrat
        try:
            contrat = soup.find('span', attrs={'class': "sc-16yjgsd-3 bCCdzk"}).span.string
        except:
            contrat = "CDI"  # Par défaut
        
        # Éducation et expérience
        education = "Non spécifié"
        experience = "Non spécifié"
        try:
            spans = soup.find_all('span', class_="sc-16yjgsd-3 eJxlVj")
            if len(spans) > 0:
                education = spans[0].find_next("span").find_next("span").string
            if len(spans) > 1:
                experience = spans[1].find_next("span").find_next("span").string
        except:
            pass
        
        # Date de publication
        try:
            if soup.find("time").has_attr('datetime'):
                debut = soup.find("time").string
            else:
                debut = "Non trouvé"
        except:
            debut = "Non trouvé"
        
        # Domaine et taille entreprise
        domaine = "Non spécifié"
        taille = "Non spécifié"
        try:
            col = soup.find_all('ul', attrs={'class': "sc-16yjgsd-4 gbiZfI"})
            for c in col:
                domaine_elem = c.find_next('span', class_="sc-16yjgsd-3 eJxlVj")
                if domaine_elem:
                    domaine = domaine_elem.string
                taille_elem = c.find_next('span', class_="sc-16yjgsd-3 cToOtz")
                if taille_elem:
                    taille = taille_elem.string
        except:
            pass
        
        # Description complète
        description = ""
        try:
            description_div = soup.find("div", class_="itvpid-1 erXZUZ")
            if description_div:
                description = description_div.text
        except:
            pass
        
        # Maintenant formater selon votre structure
        return format_wttj_to_target_structure(
            company, title, lieu, contrat, education, experience, 
            debut, domaine, taille, description, link
        )
        
    except Exception as e:
        print(f"Erreur lors du scraping de {link}: {e}")
        return None

def format_wttj_to_target_structure(company, title, lieu, contrat, education, experience, 
                                   debut, domaine, taille, description, link):
    """Formate les données WTTJ vers la structure cible"""
    
    # Métier recherché
    metier_recherche = determine_metier_recherche(title)
    
    # Niveau de séniorité
    niveau_seniorite = determine_seniority(title, description)
    
    # Expérience demandée
    experience_demandee = determine_experience(experience, title, description)
    
    # Compétences techniques
    competences_mentionnees = extract_skills_from_text(title + " " + description)
    
    # Télétravail
    teletravail = determine_telework(title, description, lieu)
    
    # Fourchette salariale (estimée basée sur le métier et l'expérience)
    fourchette_salaire = estimate_realistic_salary(metier_recherche, niveau_seniorite, lieu)
    
    # Formatage de la région
    ville_region = format_region(lieu)
    
    # ID de l'offre
    id_offre = extract_offer_id(link)
    
    # Date de publication (format ISO)
    date_publication = parse_wttj_date(debut)
    
    return {
        "intitule_poste": title,
        "nom_entreprise": company,
        "ville_region": ville_region,
        "date_publication": date_publication,
        "type_contrat": contrat,
        "experience_demandee": experience_demandee,
        "niveau_seniorite": niveau_seniorite,
        "description_poste": description,
        "source_offre": link,
        "teletravail": teletravail,
        "competences_mentionnees": competences_mentionnees,
        "fourchette_salaire": fourchette_salaire,
        "metier_recherche": metier_recherche,
        "id_offre": id_offre
    }

def determine_metier_recherche(title):
    """Détermine le métier recherché basé sur le titre"""
    title_lower = title.lower()
    
    metiers = {
        'développeur': ['développeur', 'developer', 'dev ', 'software', 'ingénieur développement', 'programmeur'],
        'data scientist': ['data scientist', 'data science', 'machine learning', 'ai engineer', 'artificial intelligence'],
        'data analyst': ['data analyst', 'analyste données', 'business intelligence', 'bi analyst'],
        'devops': ['devops', 'sre', 'site reliability', 'infrastructure'],
        'cybersécurité': ['cybersécurité', 'cybersecurity', 'sécurité', 'security engineer', 'soc analyst'],
        'frontend': ['frontend', 'front-end', 'react', 'angular', 'vue', 'javascript'],
        'backend': ['backend', 'back-end', 'java', 'python', 'node', 'api'],
        'fullstack': ['fullstack', 'full-stack'],
        'mobile': ['mobile', 'android', 'ios', 'react native', 'flutter'],
        'cloud': ['cloud', 'aws', 'azure', 'gcp', 'cloud engineer']
    }
    
    for metier, keywords in metiers.items():
        if any(keyword in title_lower for keyword in keywords):
            return metier
    
    return 'développeur'

def determine_seniority(title, description=""):
    """Détermine le niveau de séniorité"""
    text = (title + " " + description).lower()
    
    if any(word in text for word in ['senior', 'sr.', 'experimenté', '5+ years', '5 ans', '7 ans', '10 ans']):
        return "Senior"
    elif any(word in text for word in ['mid-level', 'mid level', 'confirmé', '3 ans', '4 ans', '3+ years']):
        return "Confirmé"
    elif any(word in text for word in ['junior', 'débutant', 'entry level', '0-2 years', '1 an', '2 ans']):
        return "Junior"
    else:
        return "Non spécifié"

def determine_experience(experience_text, title="", description=""):
    """Détermine l'expérience demandée"""
    if experience_text and experience_text != "Non spécifié":
        return experience_text
    
    text = (title + " " + description).lower()
    
    if any(word in text for word in ['5+ years', '5 ans', '7 ans', '10 ans']):
        return "5+ ans"
    elif any(word in text for word in ['3 ans', '4 ans', '3+ years']):
        return "3-4 ans"
    elif any(word in text for word in ['0-2 years', '1 an', '2 ans']):
        return "0-2 ans"
    elif any(word in text for word in ['débutant accepté', 'junior']):
        return "Débutant accepté"
    else:
        return "Non spécifié"

def extract_skills_from_text(text):
    """Extrait les compétences techniques du texte"""
    text_lower = text.lower()
    skills_found = set()
    
    technical_skills = [
        'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'go', 'rust', 
        'php', 'ruby', 'scala', 'kotlin', 'swift', 'dart',
        'react', 'angular', 'vue', 'svelte', 'next.js', 'nuxt.js', 'html', 'css', 'sass',
        'node.js', 'express', 'django', 'flask', 'spring', 'spring boot', 'laravel', 
        'symfony', 'asp.net', 'ruby on rails',
        'react native', 'flutter', 'android', 'ios', 'xamarin',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sql server',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible', 
        'jenkins', 'gitlab', 'github actions',
        'agile', 'scrum', 'kanban', 'devops', 'ci/cd',
        'machine learning', 'deep learning', 'ai', 'tensorflow', 'pytorch', 
        'data science', 'big data', 'spark', 'tableau', 'power bi',
        'cybersecurity', 'cybersécurité', 'sécurité', 'siem'
    ]
    
    for skill in technical_skills:
        if skill in text_lower:
            skills_found.add(skill)
    
    return list(skills_found)

def determine_telework(title, description="", location=""):
    """Détermine si le poste est en télétravail"""
    text = (title + " " + description + " " + location).lower()
    telework_indicators = ['télétravail', 'remote', 'full remote', 'télé travail', 'teletravail', 'hybride']
    return "Oui" if any(indicator in text for indicator in telework_indicators) else "Non"

def estimate_realistic_salary(metier, niveau, location):
    """Estimation réaliste basée sur le marché français 2024"""
    base_salaries = {
        'développeur': {
            'Junior': (35000, 42000),
            'Confirmé': (42000, 55000),
            'Senior': (50000, 65000)
        },
        'data scientist': {
            'Junior': (40000, 48000),
            'Confirmé': (48000, 60000),
            'Senior': (58000, 75000)
        },
        'data analyst': {
            'Junior': (35000, 42000),
            'Confirmé': (42000, 52000),
            'Senior': (50000, 62000)
        },
        'devops': {
            'Junior': (38000, 45000),
            'Confirmé': (45000, 58000),
            'Senior': (55000, 70000)
        },
        'cybersécurité': {
            'Junior': (38000, 46000),
            'Confirmé': (46000, 60000),
            'Senior': (58000, 75000)
        },
        'frontend': {
            'Junior': (35000, 42000),
            'Confirmé': (42000, 52000),
            'Senior': (50000, 62000)
        },
        'backend': {
            'Junior': (35000, 42000),
            'Confirmé': (42000, 54000),
            'Senior': (52000, 65000)
        },
        'fullstack': {
            'Junior': (36000, 43000),
            'Confirmé': (43000, 55000),
            'Senior': (52000, 68000)
        }
    }
    
    # Ajustement pour Paris
    if 'paris' in location.lower() or '75' in location:
        adjust_factor = 1.15
    elif 'lyon' in location.lower() or '69' in location:
        adjust_factor = 1.05
    else:
        adjust_factor = 1.0
    
    metier_data = base_salaries.get(metier, base_salaries['développeur'])
    niveau_data = metier_data.get(niveau, metier_data['Confirmé'])
    
    min_sal = int(niveau_data[0] * adjust_factor)
    max_sal = int(niveau_data[1] * adjust_factor)
    
    return f"Annuel de {min_sal} Euros à {max_sal} Euros sur 12.0 mois"

def format_region(location):
    """Formate la région française avec code postal"""
    regions = {
        'paris': '75 - Paris',
        'lyon': '69 - Lyon', 
        'marseille': '13 - Marseille',
        'toulouse': '31 - Toulouse',
        'nantes': '44 - Nantes',
        'bordeaux': '33 - Bordeaux',
        'lille': '59 - Lille',
        'strasbourg': '67 - Strasbourg',
        'nice': '06 - Nice',
        'rennes': '35 - Rennes',
        'montpellier': '34 - Montpellier',
        'grenoble': '38 - Grenoble'
    }
    
    location_lower = location.lower()
    for city, code in regions.items():
        if city in location_lower:
            return code
    
    return location

def extract_offer_id(link):
    """Extrait l'ID de l'offre depuis l'URL"""
    match = re.search(r'jobs/([a-zA-Z0-9_-]+)', link)
    return match.group(1) if match else f"wttj_{hash(link)}"

def parse_wttj_date(date_string):
    """Parse la date WTTJ en format ISO"""
    if date_string == "Non trouvé" or not date_string:
        return datetime.now().isoformat()
    
    try:
        # WTTJ utilise souvent des dates relatives comme "Il y a 2 jours"
        if 'il y a' in date_string.lower():
            days_match = re.search(r'(\d+)\s+jour', date_string)
            if days_match:
                days = int(days_match.group(1))
                return (datetime.now() - timedelta(days=days)).isoformat()
    except:
        pass
    
    return datetime.now().isoformat()

def get_wttj_job_links(base_url, pages=3):
    """Récupère les liens d'offres depuis les pages de liste"""
    jobs_list = []
    
    for i in range(1, pages + 1):
        try:
            url = f"{base_url}?page={i}"
            page = requests.get(url)
            soup = BeautifulSoup(page.text, 'html.parser')
            
            # Sélecteur pour les cartes d'offres
            divs = soup.find_all('div', class_="sc-1peil1v-4 tRoQI")
            
            for div in divs:
                a = div.find("a")
                if a and a.get("href") and "/fr/companies" in a["href"]:
                    full_link = "https://www.welcometothejungle.com" + a["href"]
                    if full_link not in jobs_list:
                        jobs_list.append(full_link)
            
            print(f"Page {i}: {len(divs)} offres trouvées")
            time.sleep(1)  # Respect rate limiting
            
        except Exception as e:
            print(f"Erreur page {i}: {e}")
            continue
    
    return list(set(jobs_list))  # Supprimer les doublons

def scrape_wttj_companies(companies, pages_per_company=2):
    """Scrape plusieurs entreprises sur WTTJ"""
    all_offres = []
    base_url = "https://www.welcometothejungle.com/fr/companies"
    
    for company in companies:
        print(f"\n🔍 Scraping entreprise: {company}")
        company_url = f"{base_url}/{company}/jobs"
        
        try:
            job_links = get_wttj_job_links(company_url, pages=pages_per_company)
            print(f"   {len(job_links)} offres trouvées pour {company}")
            
            for i, link in enumerate(job_links):
                print(f"   Traitement offre {i+1}/{len(job_links)}...")
                offre = get_wttj_job_details(link)
                if offre:
                    all_offres.append(offre)
                    print(f"     ✓ {offre['intitule_poste'][:40]}...")
                
                time.sleep(0.5)  # Respect rate limiting
                
        except Exception as e:
            print(f"   Erreur entreprise {company}: {e}")
            continue
    
    return all_offres

def main():
    """Fonction principale"""
    print("SCRAPING WELCOME TO THE JUNGLE")
    print("=" * 50)
    
    # Liste d'entreprises IT françaises populaires sur WTTJ
    companies = [
        "datascientest", "mantu", "amaris", "soprasteria", "capgemini",
        "orange", "bnp-paribas", "societe-generale", "decathlon", "carrefour",
        "alan", "doctolib", "blablacar", "backmarket", "manomano"
    ]
    
    # Récupérer les offres
    offres = scrape_wttj_companies(companies[:5], pages_per_company=2)  # Limiter à 5 entreprises pour l'exemple
    
    if not offres:
        print(" Aucune offre trouvée")
        return
    
    # Sauvegarde JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f'offres_wttj_{timestamp}.json'
    json_path = os.path.join(DATA_PROCESSED_DIR, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(offres, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ SCRAPING TERMINÉ")
    print(f" Fichier JSON: {json_path}")
    print(f" {len(offres)} offres sauvegardées")
    
    # Statistiques
    print(f"\n STATISTIQUES:")
    print("=" * 30)
    
    metiers = Counter([o['metier_recherche'] for o in offres])
    print(f"\n MÉTIERS:")
    for metier, count in metiers.most_common():
        print(f"  {metier}: {count} offres")
    
    niveaux = Counter([o['niveau_seniorite'] for o in offres])
    print(f"\n NIVEAUX:")
    for niveau, count in niveaux.most_common():
        print(f"  {niveau}: {count} offres")
    
    teletravail_count = sum(1 for o in offres if o['teletravail'] == 'Oui')
    print(f"\n TÉLÉTRAVAIL: {teletravail_count}/{len(offres)} offres")
    
    # Afficher un exemple
    if offres:
        print(f"\n EXEMPLE D'OFFRE:")
        print("=" * 30)
        exemple = offres[0]
        print(json.dumps(exemple, ensure_ascii=False, indent=2))

# Correction pour l'import manquant
from datetime import timedelta

if __name__ == "__main__":
    main()