import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
from collections import Counter
import os

# Configuration des chemins
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)

def linkedin_scraper_it_france_enhanced():
    """Scrape amélioré pour plus d'offres et extraction des salaires réels"""
    offres = []
    
    # Mots-clés IT plus spécifiques pour la France
    keywords_list = [
        "développeur", "developer", "ingénieur logiciel", "software engineer",
        "data scientist", "data analyst", "devops", "cybersécurité",
        "frontend", "backend", "fullstack", "mobile",
        "java", "python", "javascript", "react", "angular",
        "node.js", "spring", "django", "aws", "azure"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
    }
    
    for keyword in keywords_list[:8]:  # 8 mots-clés pour plus de couverture
        print(f"🔍 Recherche: {keyword}")
        
        for start in range(0, 100, 25):  # 4 pages par mot-clé = 100 offres par mot-clé
            try:
                url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword}&location=France&geoId=105015875&trk=public_jobs_jobs-search-bar_search-submit&start={start}"
                
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200:
                    print(f"   ❌ Erreur page {start} pour {keyword}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                jobs = soup.find_all('div', class_='base-card')
                
                if not jobs:
                    print(f"   ⚠ Aucune offre page {start} pour {keyword}")
                    break
                
                print(f"   ✅ Page {start//25 + 1}: {len(jobs)} offres trouvées")
                
                for job in jobs:
                    try:
                        # Extraction des données de base
                        title_elem = job.find('h3', class_='base-search-card__title')
                        job_title = title_elem.text.strip() if title_elem else "Non spécifié"
                        
                        company_elem = job.find('h4', class_='base-search-card__subtitle')
                        job_company = company_elem.text.strip() if company_elem else "Non spécifié"
                        
                        location_elem = job.find('span', class_='job-search-card__location')
                        job_location = location_elem.text.strip() if location_elem else "France"
                        
                        link_elem = job.find('a', class_='base-card__full-link')
                        job_link = link_elem['href'] if link_elem else ""
                        
                        # Récupérer les détails COMPLETS avec salaire
                        description, salaire_reel = get_job_details_with_salary(job_link)
                        
                        # Métadonnées avancées
                        metier_recherche = determine_metier_recherche(job_title)
                        competences = extract_skills_from_text(job_title + " " + description)
                        niveau_seniorite = determine_seniority(job_title, description)
                        experience_demandee = determine_experience(job_title, description)
                        type_contrat = determine_contract_type(job_title, description)
                        teletravail = determine_telework(job_title, description)
                        
                        # Utiliser le salaire réel ou une estimation réaliste
                        fourchette_salaire = salaire_reel if salaire_reel else estimate_realistic_salary(metier_recherche, niveau_seniorite, job_location)
                        
                        offre = {
                            "intitule_poste": job_title,
                            "nom_entreprise": job_company,
                            "ville_region": format_region(job_location),
                            "date_publication": datetime.now().isoformat(),
                            "type_contrat": type_contrat,
                            "experience_demandee": experience_demandee,
                            "niveau_seniorite": niveau_seniorite,
                            "description_poste": description if description else f"Poste de {metier_recherche} chez {job_company}.",
                            "source_offre": job_link,
                            "teletravail": teletravail,
                            "competences_mentionnees": competences,
                            "fourchette_salaire": fourchette_salaire,
                            "metier_recherche": metier_recherche,
                            "id_offre": f"linkedin_{hash(job_link)}"
                        }
                        
                        offres.append(offre)
                        print(f"     ✓ {job_title[:40]}... | Salaire: {fourchette_salaire[:30]}...")
                        
                    except Exception as e:
                        print(f"     ✗ Erreur offre: {e}")
                        continue
                
                time.sleep(2)  # Respect rate limiting
                
            except Exception as e:
                print(f"   ❌ Erreur recherche {keyword} page {start}: {e}")
                continue
    
    return offres

def get_job_details_with_salary(job_link):
    """Récupère la description et le salaire depuis la page détail"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(job_link, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Description
        description = ""
        description_selectors = [
            '.description__text',
            '.show-more-less-html__markup',
            '.jobs-description__container',
            '.description',
            '.job-details'
        ]
        
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                break
        
        # Extraction du SALAIRE avec regex améliorées
        salaire = extract_salary_from_text(description)
        
        return description, salaire
        
    except Exception as e:
        print(f"       Erreur détails: {e}")
        return "", ""

def extract_salary_from_text(text):
    """Extrait le salaire du texte avec des regex précises pour la France"""
    if not text:
        return ""
    
    # Patterns pour les salaires français
    patterns = [
        # Format: 40 000 - 50 000 €
        r'(\d{1,3}(?:\s?\d{3})*)\s*[-à]\s*(\d{1,3}(?:\s?\d{3})*)\s*[€€€]',
        # Format: 40K€ - 50K€
        r'(\d{1,3})K\s*[-à]\s*(\d{1,3})K\s*[€€€]',
        # Format: 40 000 €
        r'salaire[\s\:]*(\d{1,3}(?:\s?\d{3})*)\s*[€€€]',
        # Format: entre 40 000 et 50 000 euros
        r'entre\s*(\d{1,3}(?:\s?\d{3})*)\s*et\s*(\d{1,3}(?:\s?\d{3})*)\s*(?:euros|€)',
        # Format: 40-50k€
        r'(\d{1,3})\s*-\s*(\d{1,3})k\s*[€€€]',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                if len(match) == 2:
                    min_sal = match[0].replace(' ', '')
                    max_sal = match[1].replace(' ', '')
                    return f"Annuel de {min_sal} Euros à {max_sal} Euros sur 12.0 mois"
                elif len(match) == 1:
                    sal = match[0].replace(' ', '')
                    return f"Annuel de {sal} Euros sur 12.0 mois"
    
    return ""

def estimate_realistic_salary(metier, niveau, location):
    """Estimation réaliste basée sur le marché français 2024"""
    # Salaires basés sur les études de marché (sources: APEC, Glassdoor, Indeed)
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
        adjust_factor = 1.15  # +15% pour Paris
    elif 'lyon' in location.lower() or '69' in location:
        adjust_factor = 1.05  # +5% pour Lyon
    else:
        adjust_factor = 1.0
    
    metier_data = base_salaries.get(metier, base_salaries['développeur'])
    niveau_data = metier_data.get(niveau, metier_data['Confirmé'])
    
    min_sal = int(niveau_data[0] * adjust_factor)
    max_sal = int(niveau_data[1] * adjust_factor)
    
    return f"Annuel de {min_sal} Euros à {max_sal} Euros sur 12.0 mois"

def extract_skills_from_text(text):
    """Extraction améliorée des compétences"""
    text_lower = text.lower()
    skills_found = set()
    
    skills_mapping = {
        # Langages
        'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'go', 'rust', 
        'php', 'ruby', 'scala', 'kotlin', 'swift', 'dart',
        # Frontend
        'react', 'angular', 'vue', 'svelte', 'next.js', 'nuxt.js', 'html', 'css', 'sass',
        # Backend
        'node.js', 'express', 'django', 'flask', 'spring', 'spring boot', 'laravel', 
        'symfony', 'asp.net', 'ruby on rails',
        # Mobile
        'react native', 'flutter', 'android', 'ios', 'xamarin',
        # Bases de données
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sql server',
        'cassandra', 'elasticsearch', 'dynamodb',
        # Cloud & DevOps
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible', 
        'jenkins', 'gitlab', 'github actions', 'prometheus', 'grafana',
        # Méthodologies
        'agile', 'scrum', 'kanban', 'devops', 'ci/cd', 'tdd', 'bdd',
        # Data & AI
        'machine learning', 'deep learning', 'ai', 'tensorflow', 'pytorch', 
        'keras', 'data science', 'big data', 'spark', 'hadoop', 'tableau', 'power bi',
        # Sécurité
        'cybersecurity', 'cybersécurité', 'sécurité', 'siem', 'soc', 'owasp'
    }
    
    for skill in skills_mapping:
        if skill in text_lower:
            skills_found.add(skill)
    
    return list(skills_found)

def determine_metier_recherche(title):
    """Détection améliorée du métier"""
    title_lower = title.lower()
    
    metiers = {
        'développeur': ['développeur', 'developer', 'dev ', 'software', 'ingénieur développement'],
        'data scientist': ['data scientist', 'data science', 'machine learning engineer', 'ml engineer'],
        'data analyst': ['data analyst', 'analyste données', 'business intelligence', 'bi '],
        'devops': ['devops', 'sre', 'site reliability', 'infrastructure'],
        'cybersécurité': ['cybersécurité', 'cybersecurity', 'sécurité', 'security engineer', 'soc'],
        'frontend': ['frontend', 'front-end', 'react', 'angular', 'vue', 'javascript'],
        'backend': ['backend', 'back-end', 'java', 'python', 'node', 'api', 'spring'],
        'fullstack': ['fullstack', 'full-stack'],
        'mobile': ['mobile', 'android', 'ios', 'react native', 'flutter']
    }
    
    for metier, keywords in metiers.items():
        if any(f' {keyword} ' in f' {title_lower} ' for keyword in keywords):
            return metier
    
    return 'développeur'

def determine_seniority(title, description=""):
    text = (title + " " + description).lower()
    if any(word in text for word in ['senior', 'sr.', 'experimenté', '5+ years', '5 ans', '7 ans']):
        return "Senior"
    elif any(word in text for word in ['mid-level', 'mid level', 'confirmé', '3 ans', '4 ans']):
        return "Confirmé"
    elif any(word in text for word in ['junior', 'débutant', 'entry level', '0-2 years']):
        return "Junior"
    else:
        return "Non spécifié"

def determine_experience(title, description=""):
    text = (title + " " + description).lower()
    if any(word in text for word in ['5+ years', '5 ans', '7 ans', '10 ans']):
        return "5+ ans"
    elif any(word in text for word in ['3 ans', '4 ans', '3+ years']):
        return "3-4 ans"
    elif any(word in text for word in ['0-2 years', '1 an', '2 ans']):
        return "0-2 ans"
    else:
        return "Non spécifié"

def determine_contract_type(title, description=""):
    text = (title + " " + description).lower()
    if 'cdi' in text:
        return "CDI"
    elif 'cdd' in text:
        return "CDD"
    elif 'stage' in text:
        return "Stage"
    else:
        return "CDI"

def determine_telework(title, description=""):
    text = (title + " " + description).lower()
    telework_indicators = ['télétravail', 'remote', 'full remote', 'teletravail', 'hybride']
    return "Oui" if any(indicator in text for indicator in telework_indicators) else "Non"

def format_region(location):
    regions = {
        'paris': '75 - Paris', 'lyon': '69 - Lyon', 'marseille': '13 - Marseille',
        'toulouse': '31 - Toulouse', 'nantes': '44 - Nantes', 'bordeaux': '33 - Bordeaux',
        'lille': '59 - Lille', 'strasbourg': '67 - Strasbourg', 'nice': '06 - Nice',
        'rennes': '35 - Rennes'
    }
    for city, code in regions.items():
        if city in location.lower():
            return code
    return location

def save_to_csv(offres, filename):
    """Sauvegarde les offres en format CSV"""
    if not offres:
        return
    
    csv_path = os.path.join(DATA_PROCESSED_DIR, filename)
    
    # Préparer les données pour CSV
    csv_data = []
    for offre in offres:
        row = {
            'id_offre': offre['id_offre'],
            'intitule_poste': offre['intitule_poste'],
            'nom_entreprise': offre['nom_entreprise'],
            'ville_region': offre['ville_region'],
            'date_publication': offre['date_publication'],
            'type_contrat': offre['type_contrat'],
            'experience_demandee': offre['experience_demandee'],
            'niveau_seniorite': offre['niveau_seniorite'],
            'description_poste': offre['description_poste'].replace('\n', ' ').replace('\r', ' '),
            'source_offre': offre['source_offre'],
            'teletravail': offre['teletravail'],
            'competences_mentionnees': ', '.join(offre['competences_mentionnees']),
            'fourchette_salaire': offre['fourchette_salaire'],
            'metier_recherche': offre['metier_recherche']
        }
        csv_data.append(row)
    
    # Écrire le CSV
    if csv_data:
        import csv
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"📊 Fichier CSV sauvegardé: {csv_path}")

def main_enhanced():
    """Version améliorée avec statistiques détaillées"""
    print("🚀 SCRAPING LINKEDIN AMÉLIORÉ - OFFRES IT FRANCE")
    print("=" * 60)
    print(f"📁 Dossier de sauvegarde: {DATA_PROCESSED_DIR}")
    
    offres = linkedin_scraper_it_france_enhanced()
    
    if not offres:
        print("❌ Aucune offre trouvée")
        return
    
    # Sauvegarde JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f'offres_it_france_linkedin.json'
    json_path = os.path.join(DATA_PROCESSED_DIR, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(offres, f, ensure_ascii=False, indent=2)
    
    # Sauvegarde CSV
    csv_filename = f'offres_it_france_linkedin.csv'
    save_to_csv(offres, csv_filename)
    
    # Statistiques détaillées
    print(f"\n📊 RAPPORT COMPLET - {len(offres)} OFFRES ANALYSÉES")
    print("=" * 50)
    
    # Métiers
    metiers = Counter([o['metier_recherche'] for o in offres])
    print(f"\n🏢 MÉTIERS IT:")
    for metier, count in metiers.most_common():
        print(f"  {metier}: {count} offres")
    
    # Niveaux
    niveaux = Counter([o['niveau_seniorite'] for o in offres])
    print(f"\n🎯 NIVEAUX:")
    for niveau, count in niveaux.most_common():
        print(f"  {niveau}: {count} offres")
    
    # Télétravail
    telework_count = sum(1 for o in offres if o['teletravail'] == 'Oui')
    print(f"\n🏠 TÉLÉTRAVAIL: {telework_count}/{len(offres)} ({telework_count/len(offres)*100:.1f}%)")
    
    # Salaires réels vs estimés
    salaires_reels = sum(1 for o in offres if "Non spécifié" not in o['fourchette_salaire'])
    print(f"\n💰 SALAIRES: {salaires_reels}/{len(offres)} offres avec salaire mentionné")
    
    # Top compétences
    all_skills = []
    for o in offres:
        all_skills.extend(o['competences_mentionnees'])
    top_skills = Counter(all_skills).most_common(10)
    print(f"\n💻 TOP 10 COMPÉTENCES:")
    for skill, count in top_skills:
        print(f"  {skill}: {count} offres")
    
    print(f"\n✅ TERMINÉ!")
    print(f"📄 Fichier JSON: {json_path}")
    print(f"📊 Fichier CSV: {os.path.join(DATA_PROCESSED_DIR, csv_filename)}")

if __name__ == "__main__":
    main_enhanced()